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
            _df['time'] = to_datetime(_df['Start Date/Time'], format='%m/%d/%Y %I:%M:%S %p', errors='coerce')

            if _df['time'].isna().all():
                _df['time'] = to_datetime(_df['Start Date/Time'], format='%m/%d/%Y %H:%M:%S', errors='coerce')

            _df = _df.set_index('time')

            _df = _df.loc[~_df.index.duplicated() & _df.index.notna()]

            _df.index = _df.index.round('1h')

            _df = _df.rename(columns={
                'Thermal/Optical OC (ugC/LCm^3)': 'Thermal_OC',
                'Thermal/Optical EC (ugC/LCm^3)': 'Thermal_EC',
                'OC=TC-BC (ugC/LCm^3)': 'Optical_OC',
                'BC (ugC/LCm^3)': 'Optical_EC',
                'TC (ugC/LCm^3)': 'TC',

                'OC ugC/m^3 (Thermal/Optical)': 'Thermal_OC',
                'EC ugC/m^3 (Thermal/Optical)': 'Thermal_EC',
                'OC by diff ugC (TC-OptEC)': 'Optical_OC',
                'OptEC ugC/m^3': 'Optical_EC',
                'TC ugC/m^3': 'TC',

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
            })

            _df = _df.apply(to_numeric, errors='coerce')

            _df['OC1'] = _df['OC1_raw'] / _df['Sample_Volume']
            _df['OC2'] = _df['OC2_raw'] / _df['Sample_Volume']
            _df['OC3'] = _df['OC3_raw'] / _df['Sample_Volume']
            _df['OC4'] = _df['OC4_raw'] / _df['Sample_Volume']

            _df['PC'] = _df['Thermal_OC'] - _df['OC1'] - _df['OC2'] - _df['OC3'] - _df['OC4']

            # _df['EC1'] = _df['EC1_raw'] / _df['Sample_Volume']
            # _df['EC2'] = _df['EC2_raw'] / _df['Sample_Volume']
            # _df['EC3'] = _df['EC3_raw'] / _df['Sample_Volume']
            # _df['EC4'] = _df['EC4_raw'] / _df['Sample_Volume']
            # _df['EC5'] = _df['EC5_raw'] / _df['Sample_Volume']

            _df = _df[['Thermal_OC', 'Thermal_EC', 'Optical_OC', 'Optical_EC', 'TC', 'Sample_Volume',
                       'OC1', 'OC2', 'OC3', 'OC4', 'PC']]

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
