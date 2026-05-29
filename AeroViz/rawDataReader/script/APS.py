import numpy as np
from pandas import to_datetime, read_table, Series, concat

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder
from AeroViz.rawDataReader.script._size_dist_output import finalize_size_dist


class Reader(AbstractReader):
    """APS (Aerodynamic Particle Sizer) Data Reader

    A specialized reader for APS data files, which measure particle size distributions
    in the range of 542-1981 nm (aerodynamic diameter).

    See full documentation at docs/source/instruments/APS.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'APS'

    # =========================================================================
    # QC Thresholds
    # =========================================================================
    MIN_HOURLY_COUNT = 5  # Minimum measurements per hour
    MIN_TOTAL_CONC = 1  # Minimum total concentration (#/cm³)
    MAX_TOTAL_CONC = 700  # Maximum total concentration (#/cm³)

    # Status Flags column name
    STATUS_COLUMN = 'Status Flags'
    # All zeros status means no error
    STATUS_OK = '0000 0000 0000 0000'

    # APS Status Flag bit definitions (from TSI RF command)
    # Format: bit_position: description
    ERROR_STATES = {
        0: 'Laser fault',
        1: 'Total Flow out of range',
        2: 'Sheath Flow out of range',
        3: 'Excessive sample concentration',
        4: 'Accumulator clipped',
        5: 'Autocal failed',
        6: 'Internal temperature < 10°C',
        7: 'Internal temperature > 40°C',
        8: 'Detector voltage out of range',
        # 9: Reserved (unused)
    }

    # Date formats observed across the corpus, tried in order. The first
    # non-all-NaN result wins and is logged so a future firmware that
    # introduces a third shape surfaces a warning instead of silently
    # producing an empty frame.
    DATE_FORMATS = ['%m/%d/%y %H:%M:%S', '%m/%d/%Y %H:%M:%S']

    # Expected APS bin grid (TSI Model 3321/3320 factory-fixed) — used as a
    # sanity tripwire. An 8-year × 4-station audit of 1485 files showed zero
    # drift, but a future firmware change WOULD trigger the same NaN-poison
    # concat bug we fixed in SMPS. Loud warning, no rejection.
    EXPECTED_BIN_GRID = (0.542, 19.81, 51)  # (min nm, max nm, count)

    def __call__(self, start=None, end=None, mean_freq=None):
        """Return the dN/dlogDp distribution; write S/V + a stats sidecar.

        The parent pipeline produces the QC-applied, resampled dN/dlogDp frame
        (diameters in µm as columns) and stamps ``df.attrs``. We then write the
        number / surface / volume distributions and a QC-aligned statistics file
        next to the main output. Pass ``append_stats=True`` to also append the
        statistics columns to the returned frame (default keeps it a clean PSD
        matrix for ``psd_stats`` / ``merge_psd`` / ``SizeDist``).
        """
        dist = super().__call__(start, end, mean_freq)
        return finalize_size_dist(self, dist, unit='um')

    def _raw_reader(self, file):
        """Read and parse raw APS data files.

        Returns all columns from the raw file. Column selection is deferred
        to _QC() and _process() stages.

        Handles files with multiple concatenated headers (when multiple APS export
        files are merged into one). Header rows are identified and filtered out.
        """
        import csv

        def find_header_row(file_obj, delimiter):
            csv_reader = csv.reader(file_obj, delimiter=delimiter)
            for skip, row in enumerate(csv_reader):
                if row and row[0] == 'Sample #':
                    return skip
            raise ValueError("Header row not found")

        def parse_date(df, date_format):
            if 'Date' in df.columns and 'Start Time' in df.columns:
                return to_datetime(df['Date'] + ' ' + df['Start Time'], format=date_format, errors='coerce')
            else:
                raise ValueError("Expected date columns not found")

        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            delimiter = '\t'

            skip = find_header_row(f, delimiter)
            f.seek(0)

            _df = read_table(f, sep=delimiter, skiprows=skip, low_memory=False)

            # Some APS exports come transposed: `Sample #` lives as a row
            # rather than a column header. Try the rotation; raise with the
            # original cause attached (instead of swallowing it) so a future
            # third layout doesn't hide behind a misleading NotImplementedError.
            if 'Date' not in _df.columns:
                try:
                    _df = _df.set_index('Sample #').T
                    _df.columns.name = None
                    _df = _df.reset_index(drop=True)
                except (KeyError, AttributeError, ValueError) as exc:
                    self.logger.error(
                        f"{file.name}: missing `Date` column AND transpose "
                        f"fallback failed ({type(exc).__name__}: {exc}). "
                        f"Cols seen: {list(_df.columns[:8])}...")
                    raise NotImplementedError(
                        f"Unsupported APS data layout in {file.name}") from exc

            # Parse date — log which format won so a third shape surfaces early.
            used_fmt = None
            for date_format in self.DATE_FORMATS:
                _time_index = parse_date(_df, date_format)
                if not _time_index.isna().all():
                    used_fmt = date_format
                    break
                self.logger.debug(
                    f"{file.name}: date format {date_format!r} matched nothing, trying next")
            if used_fmt is None:
                raise ValueError(
                    f"{file.name}: none of the known date formats matched "
                    f"({self.DATE_FORMATS}). Add the new format to DATE_FORMATS.")
            else:
                self.logger.debug(f"{file.name}: parsed dates using format {used_fmt!r}")

            # Set time index
            _df.index = _time_index
            _df.index.name = 'time'
            _df = _df.loc[_df.index.dropna().copy()]

            # Identify size bin columns (numeric, in APS range 0.5-20 μm)
            numeric_cols = []
            for col in _df.columns:
                col_str = str(col).strip()
                try:
                    val = float(col_str)
                    if 0.5 <= val <= 20:
                        numeric_cols.append(col)
                except (ValueError, TypeError):
                    pass
            numeric_cols.sort(key=lambda x: float(str(x).strip()))

            # Bin-grid sanity tripwire: TSI Model 3321/3320 has factory-fixed
            # 51 channels (0.542-19.81 µm). An 8-year audit across 4 stations
            # showed zero drift, but firmware change would trigger the same
            # NaN-poison concat bug we fixed in SMPS — warn loudly so the
            # operator can investigate before silent data loss.
            if numeric_cols:
                exp_min, exp_max, exp_n = self.EXPECTED_BIN_GRID
                actual_min = round(float(str(numeric_cols[0]).strip()), 3)
                actual_max = round(float(str(numeric_cols[-1]).strip()), 3)
                actual_n = len(numeric_cols)
                if (actual_min, actual_max, actual_n) != (exp_min, exp_max, exp_n):
                    self.logger.warning(
                        f"{file.name}: APS bin grid deviates from expected. "
                        f"Got ({actual_min}, {actual_max}, {actual_n} bins), "
                        f"expected {self.EXPECTED_BIN_GRID}. If this is a real "
                        f"firmware change, concat with other files will create "
                        f"NaN-poisoned columns — see SMPS `_partition_compatible_scans`.")

            # Rename size bin columns to float values
            bin_rename = {col: round(float(str(col).strip()), 4) for col in numeric_cols}
            _df = _df.rename(columns=bin_rename)

            # Drop columns already consumed for the time index
            index_cols = ['Date', 'Start Time', 'Sample #', 'Aerodynamic Diameter']
            _df = _df.drop(columns=[c for c in index_cols if c in _df.columns], errors='ignore')

            return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on APS data.

        QC Rules Applied
        ----------------
        1. Status Error   : Non-zero status flags indicate instrument error
        2. Insufficient   : Less than 5 measurements per hour
        3. Invalid Number Conc : Total number concentration outside valid range (1-700 #/cm³)
        """
        _df = _df.copy()
        _index = _df.index.copy()

        # Filter to numeric columns only (exclude Status Flags)
        numeric_cols = [col for col in _df.columns if isinstance(col, (int, float))]
        df_numeric = _df[numeric_cols]

        # Calculate total concentration
        dlogDp = np.diff(np.log(df_numeric.columns.to_numpy(float))).mean()
        total_conc = df_numeric.sum(axis=1, min_count=1) * dlogDp

        # Build QC rules declaratively
        qc = QCFlagBuilder()

        qc.add_rules([
            QCRule(
                name='Status Error',
                condition=lambda df: self.QC_control().filter_error_status(
                    _df, status_column=self.STATUS_COLUMN, status_type='binary_string'
                ),
                description='Non-zero status flags indicate instrument error'
            ),
            QCRule(
                name='Insufficient',
                condition=lambda df: self.QC_control().hourly_completeness_QC(
                    df[df_numeric.columns], freq=self.meta['freq']
                ),
                description='Less than 50% hourly data completeness'
            ),
            QCRule(
                name='Invalid Number Conc',
                condition=lambda df, tc=total_conc: Series(
                    (tc < self.MIN_TOTAL_CONC) | (tc > self.MAX_TOTAL_CONC),
                    index=df.index
                ).fillna(True),
                description=f'Total number concentration outside valid range ({self.MIN_TOTAL_CONC}-{self.MAX_TOTAL_CONC} #/cm³)'
            ),
        ])

        # Apply all QC rules
        df_qc = qc.apply(_df)

        # Store QC summary for combined output in _process()
        self._qc_summary = qc.get_summary(df_qc)

        return df_qc.reindex(_index)

    def _process(self, _df):
        """Return the QC'd dN/dlogDp size bins (plus ``QC_Flag``).

        The size distribution itself is the canonical APS product. Summary
        statistics (total per size cut, GMD / GSD / mode) and the surface and
        volume distributions are *derived* quantities — compute them on demand
        with :func:`AeroViz.psd_stats` / :func:`AeroViz.psd_distributions`
        rather than baking them into the reader output. This keeps the reader's
        return type a plain dN/dlogDp DataFrame (diameters in µm as columns),
        which is exactly what ``psd_stats`` / ``merge_psd`` / ``SizeDist`` consume.
        """
        _index = _df.index.copy()

        qc_flag = _df['QC_Flag'].copy() if 'QC_Flag' in _df.columns else Series('Valid', index=_df.index)
        bin_cols = [col for col in _df.columns if isinstance(col, (int, float))]

        # Log the QC summary collected in _QC()
        if getattr(self, '_qc_summary', None) is not None:
            self.logger.info(f"{self.nam} QC Summary:")
            for _, row in self._qc_summary.iterrows():
                self.logger.info(f"  {row['Rule']}: {row['Count']} ({row['Percentage']})")

        # Keep only the size bins + QC_Flag (drop the raw Status Flags column)
        return concat([_df[bin_cols], qc_flag], axis=1).reindex(_index)
