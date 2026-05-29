import numpy as np
from pandas import to_datetime, read_csv, to_numeric, Series

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder


class Reader(AbstractReader):
    """OC/EC (Organic Carbon/Elemental Carbon) Analyzer Data Reader

    A specialized reader for OC/EC analyzer data files, which measure carbonaceous
    aerosol composition using thermal and optical methods.

    See full documentation at docs/source/instruments/OCEC.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'OCEC'

    # =========================================================================
    # Column Definitions
    # =========================================================================
    OUTPUT_COLUMNS = ['Thermal_OC', 'Thermal_EC', 'Optical_OC', 'Optical_EC', 'TC',
                      'OC1', 'OC2', 'OC3', 'OC4', 'PC']

    # =========================================================================
    # QC Thresholds
    # =========================================================================
    MIN_VALUE = -5       # Minimum valid value (ugC/m3)
    MAX_VALUE = 100      # Maximum valid value (ugC/m3)

    # Detection limits (MDL) for each carbon fraction
    MDL = {
        'Thermal_OC': 0.3,
        'Optical_OC': 0.3,
        'Thermal_EC': 0.015,
        'Optical_EC': 0.015
    }

    # =========================================================================
    # Firmware-version reconciliation
    # =========================================================================
    # Sunset RTCalc firmware re-labels the same carbon-fraction columns between
    # releases and only the post-2018 RTCalc802+ stream populates the per-peak
    # OCPk*-ug C columns. We apply BOTH alias maps unconditionally — only the
    # keys that actually exist in the file are renamed — and only attempt the
    # OC1..OC4 derivation when the source columns are present. RTCalc705 files
    # carry no OCPk* columns, so OC1..OC4 land as NaN (preserves schema).
    METADATA_ALIASES_RTCALC705 = {
        'Thermal/Optical OC (ugC/LCm^3)': 'Thermal_OC',
        'Thermal/Optical EC (ugC/LCm^3)': 'Thermal_EC',
        'OC=TC-BC (ugC/LCm^3)':           'Optical_OC',
        'BC (ugC/LCm^3)':                 'Optical_EC',
        'TC (ugC/LCm^3)':                 'TC',
    }
    METADATA_ALIASES_RTCALC802 = {
        'OC ugC/m^3 (Thermal/Optical)': 'Thermal_OC',
        'EC ugC/m^3 (Thermal/Optical)': 'Thermal_EC',
        'OC by diff ugC (TC-OptEC)':    'Optical_OC',
        'OptEC ugC/m^3':                'Optical_EC',
        'TC ugC/m^3':                   'TC',
    }
    # Shared columns + per-peak / pyrolyzed columns (present only on newer firmware).
    METADATA_ALIASES_SHARED = {
        'Sample Volume Local Condition Actual m^3': 'Sample_Volume',
        'OCPk1-ug C': 'OC1_raw',
        'OCPk2-ug C': 'OC2_raw',
        'OCPk3-ug C': 'OC3_raw',
        'OCPk4-ug C': 'OC4_raw',
        'Pyrolized C ug': 'PC_raw',
        'ECPk1-ug C': 'EC1_raw',
        'ECPk2-ug C': 'EC2_raw',
        'ECPk3-ug C': 'EC3_raw',
        'ECPk4-ug C': 'EC4_raw',
        'ECPk5-ug C': 'EC5_raw',
    }

    # Date formats Sunset exports have been observed using, tried in order.
    # Each fallback is logged so a third format surfaces early instead of
    # silently producing all-NaN timestamps -> empty file.
    DATE_FORMATS = [
        '%m/%d/%Y %I:%M:%S %p',   # 12-hour AM/PM (RTCalc705 default, observed)
        '%m/%d/%Y %H:%M:%S',      # 24-hour fallback
    ]

    def _raw_reader(self, file):
        """
        Read and parse raw OC/EC data files.

        Parameters
        ----------
        file : Path or str
            Path to the OC/EC data file.

        Returns
        -------
        pandas.DataFrame
            Processed OC/EC data with datetime index and carbon fraction columns.
        """
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            _df = read_csv(f, skiprows=3, on_bad_lines='skip')

            _df['Start Date/Time'] = _df['Start Date/Time'].str.strip()

            # Try each known date format in turn. The first one whose result
            # isn't all-NaN wins, and we log which won so anomalies in a batch
            # ("why did this file go quiet?") are easy to triage.
            _df['time'] = None
            used_fmt = None
            for fmt in self.DATE_FORMATS:
                parsed = to_datetime(_df['Start Date/Time'], format=fmt, errors='coerce')
                if not parsed.isna().all():
                    _df['time'] = parsed
                    used_fmt = fmt
                    break
                self.logger.debug(f"{file.name}: date format {fmt!r} matched nothing, trying next")

            if used_fmt is None:
                self.logger.warning(
                    f"{file.name}: none of the known date formats matched any row "
                    f"({self.DATE_FORMATS}). Sample value: "
                    f"{_df['Start Date/Time'].iloc[0]!r}. Returning empty frame; "
                    f"add the new format to DATE_FORMATS to fix.")
            else:
                self.logger.debug(f"{file.name}: parsed dates using format {used_fmt!r}")

            _df = _df.set_index('time')

            _df = _df.loc[~_df.index.duplicated() & _df.index.notna()]

            _df.index = _df.index.round('1h')

            # Apply all three alias maps unconditionally — only the keys that
            # exist in this file's columns will rename, the rest are inert.
            _df = _df.rename(columns={
                **self.METADATA_ALIASES_RTCALC705,
                **self.METADATA_ALIASES_RTCALC802,
                **self.METADATA_ALIASES_SHARED,
            })

            # Firmware-detect post-rename: presence of OCPk-derived columns
            # (now `OC1_raw`..`OC4_raw`) is the clearest signal. Log it so a
            # mixed-firmware batch surfaces in the log without spelunking files.
            has_per_peak = any(f'OC{i}_raw' in _df.columns for i in (1, 2, 3, 4))
            self.logger.debug(
                f"{file.name}: Sunset firmware appears to be "
                f"{'RTCalc802+ (per-peak OC fractions present)' if has_per_peak else 'RTCalc705/older (no per-peak fractions)'}"
            )

            _df = _df.apply(to_numeric, errors='coerce')

            # Per-peak fractions only exist on newer firmware (RTCalc802+); older
            # files (RTCalc705) don't have OCPk*-ug C columns — leave NaN. Also
            # guard `Sample_Volume`: if a future export drops it the division
            # would KeyError, so fall back to NaN with a one-time warning.
            sample_vol = _df['Sample_Volume'] if 'Sample_Volume' in _df.columns else None
            if sample_vol is None:
                self.logger.warning(
                    f"{file.name}: `Sample Volume Local Condition Actual m^3` "
                    f"missing — OC1..OC4 will be NaN.")
            for i in (1, 2, 3, 4):
                src = f'OC{i}_raw'
                if src in _df.columns and sample_vol is not None:
                    _df[f'OC{i}'] = _df[src] / sample_vol
                else:
                    _df[f'OC{i}'] = float('nan')

            if all(f'OC{i}' in _df.columns and _df[f'OC{i}'].notna().any() for i in (1, 2, 3, 4)):
                _df['PC'] = _df['Thermal_OC'] - _df['OC1'] - _df['OC2'] - _df['OC3'] - _df['OC4']
            else:
                _df['PC'] = float('nan')

            # `Sample_Volume` may not exist on a malformed export — keep it
            # optional in the slice so we don't KeyError on legitimate input.
            wanted = ['Thermal_OC', 'Thermal_EC', 'Optical_OC', 'Optical_EC', 'TC',
                      'OC1', 'OC2', 'OC3', 'OC4', 'PC']
            if 'Sample_Volume' in _df.columns:
                wanted.insert(5, 'Sample_Volume')
            _df = _df[wanted]

            return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on OC/EC data.

        QC Rules Applied
        ----------------
        1. Invalid Carbon  : Carbon value outside valid range (-5-100 ugC/m3)
        2. Below MDL       : Value below method detection limit
        3. Spike           : Sudden value change (vectorized spike detection)
        4. Missing OC      : Thermal_OC or Optical_OC is missing
        """
        _index = _df.index.copy()
        df_qc = _df.copy()

        # Pre-calculate MDL mask (below detection limit)
        mdl_mask = Series(False, index=df_qc.index)
        for col, threshold in self.MDL.items():
            if col in df_qc.columns:
                mdl_mask = mdl_mask | (df_qc[col] <= threshold)

        # Build QC rules declaratively
        qc = QCFlagBuilder()
        qc.add_rules([
            QCRule(
                name='Invalid Carbon',
                condition=lambda df: ((df[self.OUTPUT_COLUMNS] <= self.MIN_VALUE) |
                                      (df[self.OUTPUT_COLUMNS] > self.MAX_VALUE)).any(axis=1),
                description=f'Carbon value outside valid range ({self.MIN_VALUE}-{self.MAX_VALUE} ugC/m3)'
            ),
            QCRule(
                name='Below MDL',
                condition=lambda df: mdl_mask.reindex(df.index).fillna(False),
                description='Value below method detection limit'
            ),
            QCRule(
                name='Spike',
                condition=lambda df: self.QC_control().spike_detection(
                    df[['Thermal_OC', 'Thermal_EC', 'Optical_OC', 'Optical_EC']],
                    max_change_rate=3.0
                ),
                description='Sudden unreasonable value change detected'
            ),
            QCRule(
                name='Missing OC',
                condition=lambda df: df['Thermal_OC'].isna() | df['Optical_OC'].isna(),
                description='Missing Thermal_OC or Optical_OC'
            ),
        ])

        # Apply all QC rules and get flagged DataFrame
        df_qc = qc.apply(df_qc)

        # Log QC summary
        summary = qc.get_summary(df_qc)
        self.logger.info(f"{self.nam} QC Summary:")
        for _, row in summary.iterrows():
            self.logger.info(f"  {row['Rule']}: {row['Count']} ({row['Percentage']})")

        return df_qc[self.OUTPUT_COLUMNS + ['QC_Flag']].reindex(_index)
