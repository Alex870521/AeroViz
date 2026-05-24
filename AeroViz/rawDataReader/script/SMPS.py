import csv

import numpy as np
from pandas import to_datetime, read_csv, Series, concat

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder
from AeroViz.rawDataReader.script._size_dist_output import finalize_size_dist


class Reader(AbstractReader):
    """SMPS (Scanning Mobility Particle Sizer) Data Reader

    A specialized reader for SMPS data files, which measure particle size distributions
    in the range of 11.8-593.5 nm.

    See full documentation at docs/source/instruments/SMPS.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'SMPS'

    # =========================================================================
    # QC Thresholds
    # =========================================================================
    MIN_HOURLY_COUNT = 5           # Minimum measurements per hour
    MIN_TOTAL_CONC = 2000          # Minimum total concentration (#/cm³)
    MAX_TOTAL_CONC = 1e7           # Maximum total concentration (#/cm³)
    MAX_LARGE_BIN_CONC = 4000      # Maximum concentration for >400nm bins (DMA water ingress indicator)
    LARGE_BIN_THRESHOLD = 400      # Size threshold for large bin filter (nm)

    # Status Flag column name
    STATUS_COLUMN = 'Status Flag'
    STATUS_OK = 'Normal Scan'  # Normal status text

    def __call__(self, start=None, end=None, mean_freq=None):
        """Return the dN/dlogDp distribution; write S/V + a stats sidecar.

        The parent pipeline produces the QC-applied, resampled dN/dlogDp frame
        (diameters in nm as columns) and stamps ``df.attrs``. We then write the
        number / surface / volume distributions and a QC-aligned statistics file
        next to the main output. Pass ``append_stats=True`` to also append the
        statistics columns to the returned frame (default keeps it a clean PSD
        matrix for ``psd_stats`` / ``merge_psd`` / ``SizeDist``).
        """
        dist = super().__call__(start, end, mean_freq)
        return finalize_size_dist(self, dist, unit='nm')

    def _raw_reader(self, file):
        """Read and parse raw SMPS data files.

        Returns all columns from the raw file. Column selection is deferred
        to _QC() and _process() stages.

        Supported formats:
        - S80 TXT (AIM old): tab-separated, header at 'Sample #'
        - S82 TXT (AIM 10.3): tab-separated, header at 'Sample #'
        - CSV (AIM 11.x): comma-separated, header at 'Scan Number'
        """

        def find_header_row(file_obj, delimiter):
            csv_reader = csv.reader(file_obj, delimiter=delimiter)
            for skip, row in enumerate(csv_reader):
                if row and (row[0] in ['Sample #', 'Scan Number']):
                    return skip
            raise ValueError("Header row not found")

        def parse_date(df, date_format):
            if 'Date' in df.columns and 'Start Time' in df.columns:
                return to_datetime(df['Date'] + ' ' + df['Start Time'], format=date_format, errors='coerce')
            elif 'DateTime Sample Start' in df.columns:
                return to_datetime(df['DateTime Sample Start'], format=date_format, errors='coerce')
            else:
                raise ValueError("Expected date columns not found")

        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            if file.suffix.lower() == '.txt':
                # %Y/%m/%d for AIM 10.3+ which exports dates like "2021/1/3"
                delimiter, date_formats = '\t', ['%m/%d/%y %X', '%m/%d/%Y %X', '%Y/%m/%d %X']
            else:  # csv
                delimiter, date_formats = ',', ['%d/%m/%Y %X']

            skip = find_header_row(f, delimiter)
            f.seek(0)

            _df = read_csv(f, sep=delimiter, skiprows=skip, low_memory=False)
            if 'Date' not in _df.columns and 'DateTime Sample Start' not in _df.columns:
                try:
                    _df = _df.T
                    _df.columns = _df.iloc[0]
                    _df = _df.iloc[1:]
                    _df = _df.reset_index(drop=True)
                except:
                    raise NotImplementedError('Not supported date format')

            for date_format in date_formats:
                _time_index = parse_date(_df, date_format)
                if not _time_index.isna().all():
                    break
            else:
                raise ValueError("Unable to parse dates with given formats")

            # Check for comma decimal separator
            comma_decimal_cols = [col for col in _df.columns if isinstance(col, str) and ',' in col.strip()]
            if comma_decimal_cols:
                self.logger.warning(f"Detected {len(comma_decimal_cols)} columns using comma as decimal separator")
                _df.columns = _df.columns.str.replace(',', '.')

            # Identify size bin columns (numeric column names)
            numeric_cols = [col for col in _df.columns if isinstance(col, str) and col.strip().replace('.', '').isdigit()]
            numeric_cols.sort(key=lambda x: float(x.strip()))

            # Set time index
            _df.index = _time_index
            _df.index.name = 'time'
            _df = _df.loc[_df.index.dropna().copy()]

            # Rename size bin columns to float values
            bin_rename = {col: float(col.strip()) for col in numeric_cols}
            _df = _df.rename(columns=bin_rename)
            bin_cols = sorted(bin_rename.values())

            # Check size range — only reject when user explicitly requested a specific range.
            # Otherwise just warn so older instrument configs (e.g. 2017 with 18.8-914 nm)
            # still get parsed for coverage / time-index purposes.
            explicit_range = self.kwargs.get('size_range')
            size_range = explicit_range or (11.8, 593.5)
            if bin_cols[0] != size_range[0] or bin_cols[-1] != size_range[1]:
                self.logger.warning(f'SMPS file: {file.name} size range mismatch. '
                                    f'Expected {size_range}, got ({bin_cols[0]}, {bin_cols[-1]})')
                if explicit_range is not None:
                    return None

            # Drop columns already consumed for the time index
            index_cols = ['Date', 'Start Time', 'DateTime Sample Start',
                          'Sample #', 'Scan Number', 'Diameter Midpoint', 'Diameter Midpoint (nm)']
            _df = _df.drop(columns=[c for c in index_cols if c in _df.columns], errors='ignore')

            return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on SMPS particle size distribution data.

        QC Rules Applied
        ----------------
        1. Status Error        : Non-empty status flag indicates instrument error
        2. Insufficient        : Less than 5 measurements per hour
        3. Invalid Number Conc : Total number concentration outside valid range (2000-1e7 #/cm³)
        4. DMA Water Ingress   : Bins >400nm with concentration > 4000 dN/dlogDp (indicates water in DMA)
        """
        _df = _df.copy()
        _index = _df.index.copy()

        # Apply size range filter
        size_range = self.kwargs.get('size_range') or (11.8, 593.5)
        numeric_cols = [col for col in _df.columns if isinstance(col, (int, float))]
        df_numeric = _df[numeric_cols]
        size_mask = (df_numeric.columns.astype(float) >= size_range[0]) & (df_numeric.columns.astype(float) <= size_range[1])
        df_numeric = df_numeric.loc[:, size_mask]

        # Calculate total concentration for QC checks
        dlogDp = np.diff(np.log(df_numeric.columns[:-1].to_numpy(float))).mean()
        total_conc = df_numeric.sum(axis=1, min_count=1) * dlogDp

        # Get large bins (>400nm)
        large_bins = df_numeric.columns[df_numeric.columns.astype(float) >= self.LARGE_BIN_THRESHOLD]

        # Build QC rules declaratively
        qc = QCFlagBuilder()

        qc.add_rules([
            QCRule(
                name='Status Error',
                condition=lambda df: self.QC_control().filter_error_status(
                    _df, status_column=self.STATUS_COLUMN, status_type='text', ok_value=self.STATUS_OK
                ),
                description=f'Status flag is not "{self.STATUS_OK}"'
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
                description=f'Total number concentration outside valid range ({self.MIN_TOTAL_CONC}-{self.MAX_TOTAL_CONC:.0e} #/cm³)'
            ),
            QCRule(
                name='DMA Water Ingress',
                condition=lambda df: (df[large_bins] > self.MAX_LARGE_BIN_CONC).any(axis=1) if len(large_bins) > 0 else Series(False, index=df.index),
                description=f'Bins >{self.LARGE_BIN_THRESHOLD}nm with concentration > {self.MAX_LARGE_BIN_CONC} dN/dlogDp (water in DMA)'
            ),
        ])

        # Apply all QC rules
        df_qc = qc.apply(_df)

        # Store QC summary for combined output in _process()
        self._qc_summary = qc.get_summary(df_qc)

        return df_qc.reindex(_index)

    def _process(self, _df):
        """Return the QC'd dN/dlogDp size bins (plus ``QC_Flag``).

        The size distribution itself is the canonical SMPS product. Summary
        statistics (total / GMD / GSD / mode, mode fractions) and the surface
        and volume distributions are *derived* quantities — compute them on
        demand with :func:`AeroViz.psd_stats` / :func:`AeroViz.psd_distributions`
        rather than baking them into the reader output. This keeps the reader's
        return type a plain dN/dlogDp DataFrame (diameters as columns), which is
        exactly what ``psd_stats`` / ``merge_psd`` / ``SizeDist`` consume.
        """
        _index = _df.index.copy()

        qc_flag = _df['QC_Flag'].copy() if 'QC_Flag' in _df.columns else Series('Valid', index=_df.index)
        bin_cols = [col for col in _df.columns if isinstance(col, (int, float))]

        # Log the QC summary collected in _QC()
        if getattr(self, '_qc_summary', None) is not None:
            self.logger.info(f"{self.nam} QC Summary:")
            for _, row in self._qc_summary.iterrows():
                self.logger.info(f"  {row['Rule']}: {row['Count']} ({row['Percentage']})")

        # Keep only the size bins + QC_Flag (drop the raw Status Flag column)
        return concat([_df[bin_cols], qc_flag], axis=1).reindex(_index)
