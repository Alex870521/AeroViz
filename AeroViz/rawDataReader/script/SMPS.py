import csv

import numpy as np

from AeroViz.dataProcess.SizeDistr._size_dist import bin_widths
from pandas import Series, read_csv, to_datetime, to_numeric

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder, WARNING
from AeroViz.rawDataReader.script._size_dist_output import finalize_size_dist


class Reader(AbstractReader):
    """SMPS (Scanning Mobility Particle Sizer) Data Reader

    A specialized reader for SMPS data files, which measure particle size distributions
    in the range of 11.8-593.5 nm.

    See ``docs/api/instruments/particle-sizers/SMPS.md`` for usage and
    ``docs/guide/instrument-qc.md`` for the
    file layout, status codes and QC rules.
    """
    nam = 'SMPS'

    # =========================================================================
    # QC Thresholds
    # =========================================================================
    # Hourly completeness is a *fraction* (`hourly_completeness_QC`'s
    # threshold=0.5), not a fixed count: the expected points per hour follow the
    # frequency detected from the files. A `MIN_HOURLY_COUNT = 5` constant used to
    # sit here, never read and true only for a 6-minute grid.
    # Plausibility bounds on the integrated total, in #/cm³. These are a coarse
    # backstop — the physical limit is per-bin and lives in `CPC Over-range`.
    # Both are overridable per run: `min_total_conc=` / `max_total_conc=`.
    #
    # ⚠️ `MIN_TOTAL_CONC` was 2000 until 2026-09-09, which made the reader
    # unusable at any clean site: EBAS background stations sit at 50–300 /cm³
    # (Zeppelin's median is 95), so 99–100% of their record was being rejected
    # as invalid. A minimum is there to catch "instrument off / no flow", which
    # reads ~0, not to encode an urban site's typical loading.
    #
    # ⚠️ `MAX_TOTAL_CONC` was 1e7, which caught 19% of the scans a five-station
    # TCLab audit found implausible; measured against the same set, 1e6 catches
    # 30% and is still above any credible ambient total (roadside peaks reach
    # 2–5e5). The rest is the CPC and shape rules' job, not this one's.
    MIN_TOTAL_CONC = 10
    MAX_TOTAL_CONC = 1e6
    MAX_LARGE_BIN_CONC = 4000      # Maximum concentration for >400nm bins (DMA water ingress indicator)
    LARGE_BIN_THRESHOLD = 400      # Size threshold for large bin filter (nm)

    # =========================================================================
    # Status columns across AIM versions
    # =========================================================================
    # The same information is reported under DIFFERENT COLUMN NAMES depending on
    # the host software, so the reader checks every dialect it knows and ORs the
    # error masks of whichever columns are present. Verified against the corpus:
    #
    #   AIM 10.3 (.TXT)          AIM 11.x (.CSV)         OK value
    #   ----------------------   ---------------------   -----------------------
    #   Status Flag              Detector Status         'Normal Scan' (positive
    #                                                    sentinel)
    #   Instrument Errors        Classifier Errors       empty; some sites write
    #                                                    'Normal Scan' instead
    #   —                        Communication Status    '0'
    #   —                        Neutralizer Status      'ON'
    #
    # Two shapes of value: a *positive sentinel* column, OK when it equals a
    # known-good string; and an *error-token* column, OK when empty, otherwise
    # carrying one or more comma-separated fault names ('Low aerosol flow',
    # 'Neutralizer not active'). Whitelist benign tokens per site with
    # `ignored_status_errors=[...]` rather than editing raw files.
    #
    # An AIM 11.x export has NEITHER of the 10.3 names, so before this list
    # existed its `Status Error` rule could never fire — every scan passed the
    # status check regardless of what the instrument reported.
    STATUS_SPECS = (
        # (column, ok_value, extra tokens always treated as OK)
        ('Status Flag', 'Normal Scan', ()),
        ('Instrument Errors', '', ('Normal Scan',)),
        ('Detector Status', 'Normal Scan', ()),
        ('Classifier Errors', '', ('Normal Scan',)),
        ('Communication Status', '0', ()),
        ('Neutralizer Status', 'ON', ()),
    )

    #: Metadata fields naming the CPC that did the counting. Captured from the
    #: block above the data header and reported in `df.attrs`; the CPC's cut-off
    #: sets how far the lowest size channels under-report.
    #: `CPC Model` is the AIM 10.3 spelling of `Detector Model`; without it the
    #: whole 10.3 dialect reported no detector at all, which also left the
    #: `CPC Over-range` rule below permanently inert on those files.
    DETECTOR_FIELDS = ('Detector Model', 'CPC Model', 'Detector S/N', 'Nano Enhancer')

    #: Rated maximum concentration per CPC model (#/cm³) — the top of the range
    #: over which the counter's accuracy is specified. Above it the coincidence
    #: correction is extrapolation, so a bin reading higher is not trustworthy.
    #:
    #: ⚠️ This is a *per-bin* limit, not a limit on the integrated total: the
    #: DMA passes one narrow mobility band at a time, so the counter only ever
    #: sees a slice of the distribution. Comparing it against the total is a
    #: category error — see `_cpc_bin_ceiling`.
    #:
    #: Models absent here leave the rule inert (logged, not silently skipped).
    #: Override or extend with `cpc_max_conc={'3022': 1e7}`.
    CPC_MAX_CONC = {
        '3772': 1e4,      # single-count only, no photometric mode
        '3787': 2.5e5,
        '3788': 4.0e5,
        '3022': 1.0e7,    # photometric above ~1e4; effectively unconstrained here
        '3022A': 1.0e7,
    }

    #: Air mean free path (nm) at the SMPS reference state (296.15 K,
    #: 101.3 kPa). Only used when a file does not record its own.
    REFERENCE_MEAN_FREE_PATH_NM = 67.3

    # Kept for backwards compatibility with callers that referenced these.
    STATUS_COLUMN = 'Status Flag'
    STATUS_OK = 'Normal Scan'
    SECONDARY_STATUS_COLUMN = 'Instrument Errors'

    # =========================================================================
    # AIM-version reconciliation (10.3 .TXT vs 11.x .CSV exports)
    # =========================================================================
    # The same physical SMPS can export at different size-bin grids depending
    # on the host software version (AIM 10.3: 11.8–593.5 nm; AIM 11.x:
    # 11.34–615.27 nm with shifted intermediate bins) AND re-labels many
    # metadata columns. Two separate problems:
    #
    # 1. Mixed-bin-grid in one folder — handled by `_partition_compatible_scans`
    #    (keep the dominant-row group, drop the minority with a warning).
    # 2. AIM-version metadata column drift — `METADATA_ALIASES` rewrites the
    #    AIM 11.x form to the AIM 10.3 form on every parsed file, so a folder
    #    of either version (or a partitioned-down folder) produces a
    #    consistent schema downstream. Only the unambiguous 1:1 physical
    #    quantities are renamed; AIM 11.x cuts that have NO 10.3 equivalent
    #    (4-way error split, granular DMA timings, etc.) are kept under their
    #    AIM 11.x names because collapsing them would lose information.
    METADATA_ALIASES = {
        # AIM 11.x name -> AIM 10.3 canonical
        'Total Concentration (#/cm³)': 'Total Conc. (#/cm)',
        'Aerosol Temperature (C)': 'Sample Temp (C)',
        'Aerosol Humidity (%)': 'Relative Humidity (%)',
        'Aerosol Density (g/cm³)': 'Density (g/cm)',
        'Impactor D50 (nm)': 'D50 (nm)',
        'Test Name': 'Title',
        'Geo. Std. Dev': 'Geo. Std. Dev.',                       # AIM 11.x drops the trailing period
        'DMA Column transit time Tf (s)': 'tf (s)',
        'DMA Exit to Optical Detector Td (s)': 'td + 0.5 (s)',   # AIM 10.3 also adds the +0.5 offset; treated as same quantity
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #: `{field: value}` scraped from the file metadata; see DETECTOR_FIELDS.
        self._detector = {}

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
        dist = finalize_size_dist(self, dist, unit='nm')

        # Which CPC counted these particles, for whoever reads the data later.
        if self._detector:
            dist.attrs.update({f'cpc_{k.lower().replace(" ", "_").replace("/", "_")}': v
                               for k, v in self._detector.items()})
        return dist

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
            """Locate the data header, capturing the detector metadata above it.

            The block before the header names the CPC doing the counting
            (`Detector Model`, `Nano Enhancer`). That decides where the counting
            efficiency rolls off, and therefore how far the lowest channels
            under-report — see `docs/guide/counting-efficiency.md`. The CPC is a
            separate instrument that can be swapped, so it is worth recording
            which one produced a given dataset rather than assuming.
            """
            csv_reader = csv.reader(file_obj, delimiter=delimiter)
            for skip, row in enumerate(csv_reader):
                if row and (row[0] in ['Sample #', 'Scan Number']):
                    return skip
                # AIM 11.x CSV puts one field per line; AIM 10.3 TXT packs
                # several key/value pairs onto one tab-separated line, so walk
                # the whole row rather than just its first cell.
                for key, value in zip(row[::2], row[1::2]):
                    if key.strip() in self.DETECTOR_FIELDS and value.strip():
                        self._detector.setdefault(key.strip(), value.strip())
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

            # AIM 11.x → AIM 10.3 metadata canonicalization so consumers see the
            # same column names regardless of which host software exported the
            # file. Only the unambiguous 1:1 physical quantities are renamed —
            # see `METADATA_ALIASES` docstring above. A pre-existing AIM 10.3
            # column with the same canonical name is rare in practice (the file
            # is one AIM version or the other), but if it happens we keep the
            # 10.3 form and drop the AIM 11.x duplicate.
            rename = {old: new for old, new in self.METADATA_ALIASES.items()
                      if old in _df.columns}
            if rename:
                drop_dup = [old for old, new in rename.items() if new in _df.columns]
                if drop_dup:
                    _df = _df.drop(columns=drop_dup)
                    rename = {k: v for k, v in rename.items() if k not in drop_dup}
                if rename:
                    _df = _df.rename(columns=rename)

            return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    @staticmethod
    def _bin_signature(df):
        """Stable fingerprint of a file's size-bin grid (sorted tuple of
        diameter columns, rounded to 2 decimals so trivial float jitter
        doesn't split otherwise-identical scans into different groups)."""
        return tuple(sorted(round(float(c), 2)
                            for c in df.columns if isinstance(c, (int, float))))

    def _partition_compatible_scans(self, df_list, files):
        """Keep files whose size-bin grid matches the dominant group; drop
        the rest so the concat sees one consistent schema.

        The grouping fingerprint is the file's sorted size-bin tuple. The
        "dominant" group is picked by total row count, not file count —
        this stops a swarm of tiny files from outvoting one large-but-typical
        file. The minority files are not silently discarded: every dropped
        file is named in a warning, so the user can re-run them in isolation
        (different folder, or with `size_range=`) if both grids are wanted.
        """
        if len(df_list) < 2:
            return df_list

        groups: dict = {}
        for f, df in zip(files, df_list):
            sig = self._bin_signature(df)
            groups.setdefault(sig, []).append((f, df))

        if len(groups) == 1:
            return df_list  # homogeneous folder — no isolation needed.

        # Pick the dominant group by total row count.
        def total_rows(items):
            return sum(len(df) for _, df in items)

        sigs_ranked = sorted(groups.items(), key=lambda kv: total_rows(kv[1]), reverse=True)
        dominant_sig, dominant_items = sigs_ranked[0]
        kept = [df for _, df in dominant_items]

        # Build a single readable warning naming every dropped file.
        for sig, items in sigs_ranked[1:]:
            dropped_names = [f.name for f, _ in items]
            n_rows = total_rows(items)
            shown = ', '.join(dropped_names[:5])
            if len(dropped_names) > 5:
                shown += f', ... (+{len(dropped_names) - 5} more)'
            d_min, d_max = (min(sig), max(sig)) if sig else (None, None)
            kept_min, kept_max = (min(dominant_sig), max(dominant_sig))
            self.logger.warning(
                f"Mixed-format SMPS folder: skipping {len(dropped_names)} "
                f"file(s) ({n_rows} rows) on a different size-bin grid "
                f"({d_min}–{d_max} nm, {len(sig)} bins) than the dominant "
                f"group ({kept_min}–{kept_max} nm, {len(dominant_sig)} bins). "
                f"Files: {shown}. "
                f"Move them to a separate folder (or pass `size_range=`) to "
                f"process them in their own run."
            )

        return kept

    @classmethod
    def _rated_max_conc(cls, model: str):
        """Look up a counter's rated maximum from a free-text model string.

        The field is whatever the operator's software wrote — `3772`,
        `3788 Low Flow`, `3022A` — so match on the longest known key contained
        in it rather than requiring equality. Longest-first matters: `3022A`
        must not be answered by the `3022` entry when both are listed.

        Returns ``None`` when nothing matches, which leaves the rule inert.
        """
        if not model:
            return None
        for key in sorted(cls.CPC_MAX_CONC, key=len, reverse=True):
            if key in model:
                return cls.CPC_MAX_CONC[key]
        return None

    def _cpc_bin_ceiling(self, dp, beta, cpc_max, mean_free_path_nm=None):
        """Highest credible ``dN/dlogDp`` per bin before the CPC is over-range.

        The DMA passes one narrow mobility band at a time, so the counter sees

            N_counted(Dp) ~ dN/dlogDp(Dp) x dlog10(Dp)_transfer

        and the rated maximum applies to *that*, not to the integrated total.
        Inverting gives the ceiling. The transfer function's width in mobility
        is ``beta = q_aerosol / q_sheath``; converting to diameter needs the
        local slope ``|dlnZ/dlnDp|``, which runs from ~2 in the free-molecular
        regime to ~1 in the continuum — so **the ceiling is a curve, not a
        constant**, about 40% lower at 600 nm than at 12 nm.

        A higher sheath ratio narrows the transfer function and therefore
        *raises* the ceiling: the same counter tolerates a denser aerosol when
        it only ever sees a thinner slice of it.

        Parameters
        ----------
        dp : ndarray
            Bin midpoints (nm).
        beta : float or ndarray
            Aerosol/sheath flow ratio. Scalar, or one value per scan.
        cpc_max : float
            Rated maximum concentration of the counter (#/cm³).
        mean_free_path_nm : float, optional
            Defaults to `REFERENCE_MEAN_FREE_PATH_NM`; pass the file's own
            ``Mean Free Path (m)`` when available.

        Returns
        -------
        ndarray
            Ceiling per bin — shape ``(len(dp),)`` for scalar ``beta``,
            ``(len(beta), len(dp))`` otherwise.
        """
        lam = mean_free_path_nm or self.REFERENCE_MEAN_FREE_PATH_NM
        dp = np.asarray(dp, dtype=float)

        def _log_mobility(d):
            kn = 2 * lam / d
            return np.log((1 + kn * (1.257 + 0.4 * np.exp(-1.1 / kn))) / d)

        h = 1e-4
        slope = np.abs((_log_mobility(dp * (1 + h)) - _log_mobility(dp * (1 - h))) / (2 * h))

        beta = np.asarray(beta, dtype=float)
        width = np.expand_dims(beta, -1) / (slope * np.log(10))   # dlog10(Dp) per band
        return cpc_max / width

    def _QC(self, _df):
        """
        Perform quality control on SMPS particle size distribution data.

        QC Rules Applied
        ----------------
        1. Status Error        : Non-empty status flag indicates instrument error
        2. Insufficient        : Less than 50% hourly data completeness (WARNING, not dropped)
        3. Invalid Number Conc : Total number concentration outside plausible range (10-1e6 #/cm³);
                                 total = sum(dN/dlogDp x dlogDp) with per-bin widths
        4. CPC Over-range      : A bin exceeds what the counter can count (per-instrument, from the file header)
        5. DMA Water Ingress   : Bins >400nm with concentration > 4000 dN/dlogDp (indicates water in DMA)
        """
        _df = _df.copy()
        _index = _df.index.copy()

        # Apply size range filter
        size_range = self.kwargs.get('size_range') or (11.8, 593.5)
        numeric_cols = [col for col in _df.columns if isinstance(col, (int, float))]
        df_numeric = _df[numeric_cols]
        size_mask = (df_numeric.columns.astype(float) >= size_range[0]) & (df_numeric.columns.astype(float) <= size_range[1])
        df_numeric = df_numeric.loc[:, size_mask]

        # Total number concentration for the QC checks below: sum of dN over
        # the bins, i.e. sum(dN/dlogDp x dlogDp).
        #
        # Two bugs lived here until 2026-09-09, and both made the
        # `Invalid Number Conc` thresholds mean something other than they say:
        #   1. `np.log` (natural) was used where the data is dN/dlog10Dp, so
        #      every total came out ln(10) = 2.303x too high. `MAX_TOTAL_CONC`
        #      of 1e7 was really 4.34e6 and `MIN_TOTAL_CONC` of 2000 was 868.
        #   2. `columns[:-1]` dropped a column before diffing, averaging over
        #      n-2 gaps instead of n-1.
        # Now uses the per-bin widths (`bin_widths`) rather than a single mean
        # step, which also makes the total correct on a non-uniform grid.
        # Verified against the instrument's own `Total Conc.` column: 0.996-0.999.
        dlogDp = bin_widths(df_numeric.columns.to_numpy(float))
        total_conc = (df_numeric * dlogDp).sum(axis=1, min_count=1)

        # Get large bins (>400nm)
        large_bins = df_numeric.columns[df_numeric.columns.astype(float) >= self.LARGE_BIN_THRESHOLD]

        min_total = self.kwargs.get('min_total_conc', self.MIN_TOTAL_CONC)
        max_total = self.kwargs.get('max_total_conc', self.MAX_TOTAL_CONC)

        # ---- CPC over-range: the counter's rated maximum, per bin -------------
        # Everything here is read from the file itself (detector model in the
        # header, flows in the data rows), so changing counter or sheath ratio
        # mid-record is picked up without configuration.
        cpc_model = str(self.kwargs.get('cpc_model')
                        or self._detector.get('CPC Model')
                        or self._detector.get('Detector Model') or '').strip()
        cpc_max = self.kwargs.get('cpc_max_conc')
        if cpc_max is None:
            cpc_max = self._rated_max_conc(cpc_model)

        beta = None
        if {'Aerosol Flow(lpm)', 'Sheath Flow(lpm)'} <= set(_df.columns):
            qa = to_numeric(_df['Aerosol Flow(lpm)'], errors='coerce')
            qsh = to_numeric(_df['Sheath Flow(lpm)'], errors='coerce')
            ratio = (qa / qsh).replace([np.inf, -np.inf], np.nan)
            if ratio.notna().any():
                beta = ratio.fillna(ratio.median()).to_numpy()

        lam_nm = None
        if 'Mean Free Path (m)' in _df.columns:
            lam = to_numeric(_df['Mean Free Path (m)'], errors='coerce').median()
            if np.isfinite(lam) and lam > 0:
                lam_nm = float(lam) * 1e9

        if cpc_max is None or beta is None:
            missing = 'detector model' if cpc_max is None else 'sheath/aerosol flow'
            self.logger.debug(
                f'CPC Over-range rule inert: {missing} unavailable '
                f'(model={cpc_model or "unknown"}). Supply `cpc_max_conc=` to enable.')
            cpc_over = Series(False, index=_df.index)
        else:
            ceiling = self._cpc_bin_ceiling(
                df_numeric.columns.to_numpy(float), beta, float(cpc_max), lam_nm)
            cpc_over = Series(
                (df_numeric.to_numpy(float) > ceiling).any(axis=1), index=_df.index)

        # Build QC rules declaratively
        qc = self.qc_builder()

        # Operator-supplied whitelist of benign status tokens (e.g.
        # 'Low aerosol flow' on a known-noisy instrument). Defaults to None
        # so existing pipelines see no behavioural change.
        ignored_status_errors = self.kwargs.get('ignored_status_errors') or None

        # Warn once if this export uses none of the dialects we know, since the
        # rule below would then be permanently silent.
        status_columns = self.check_status_columns(
            _df, [name for name, _, _ in self.STATUS_SPECS])
        if status_columns:
            self.logger.debug(f"SMPS status columns in use: {', '.join(status_columns)}")

        def _combined_status_error_mask(df):
            """OR the error masks of every status column this export provides.

            Each entry in `STATUS_SPECS` names a column, the value that means OK,
            and any extra tokens to treat as OK. A column that is absent is
            skipped, so one implementation covers AIM 10.3, AIM 11.x and any
            mixed folder without configuration.

            `'Normal Scan'` is never a real error in any column, so it is
            whitelisted on the error-token columns too: most sites leave those
            empty when healthy, but some write the positive sentinel there
            instead, and without this every scan from those sites would be
            flagged.
            """
            qc_ctrl = self.QC_control()
            mask = Series(False, index=_df.index)

            for column, ok_value, extra_ok in self.STATUS_SPECS:
                if column not in _df.columns:
                    continue
                ignored = list(ignored_status_errors or []) + list(extra_ok)
                mask = mask | qc_ctrl.filter_error_status(
                    _df, status_column=column, status_type='text',
                    ok_value=ok_value, ignored_values=ignored or None,
                )

            return mask.reindex(df.index).fillna(False)

        qc.add_rules([
            QCRule(
                name='Status Error',
                condition=_combined_status_error_mask,
                description=(
                    'Instrument reported a fault in '
                    + (', '.join(f'`{c}`' for c in status_columns) if status_columns
                       else 'no recognised status column (rule inert)')
                    + (f' (ignoring: {ignored_status_errors})' if ignored_status_errors else '')
                )
            ),
            QCRule(
                name='Insufficient',
                condition=lambda df: self.QC_control().hourly_completeness_QC(
                    df[df_numeric.columns], freq=self._resolved_freq or self.meta['freq']
                ),
                description='Less than 50% hourly data completeness',
                # Representativeness, not validity: the readings in a sparse
                # hour are fine, it is an average over that hour that would
                # misrepresent it. Users were losing the head and tail of
                # every read to this. Promote it per run with
                # flag_severity={'Insufficient': 'error'}.
                severity=WARNING,
            ),
            QCRule(
                name='Invalid Number Conc',
                condition=lambda df, tc=total_conc, lo=min_total, hi=max_total: Series(
                    (tc < lo) | (tc > hi), index=df.index
                ).fillna(True),
                description=f'Total number concentration outside plausible range ({min_total:g}-{max_total:.0e} #/cm³)'
            ),
            QCRule(
                name='CPC Over-range',
                condition=lambda df, m=cpc_over: m.reindex(df.index).fillna(False),
                description=(
                    f'A bin exceeded what a {cpc_model or "unknown"} CPC can count '
                    f'({cpc_max:,.0f} #/cm³) given the recorded sheath ratio'
                    if cpc_max is not None and beta is not None
                    else 'CPC over-range (rule inert: detector model or flows unavailable)'
                )
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

        bin_cols = [col for col in _df.columns if isinstance(col, (int, float))]

        # Log the QC summary collected in _QC()
        if getattr(self, '_qc_summary', None) is not None:
            self.log_qc_summary(self._qc_summary)

        # Keep only the size bins + QC bookkeeping (drop the raw status column)
        return _df[bin_cols + self.qc_columns(_df)].reindex(_index)
