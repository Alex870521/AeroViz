from pandas import read_csv, to_numeric, concat

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder
from AeroViz.rawDataReader.core.pre_process import _absCoe


class Reader(AbstractReader):
    """BC1054 Black Carbon Monitor Data Reader

    A specialized reader for BC1054 data files, which measure black carbon
    concentrations using light absorption at 10 wavelengths.

    See full documentation at docs/source/instruments/BC1054.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'BC1054'

    # =========================================================================
    # Column Definitions
    # =========================================================================
    BC_COLUMNS = ['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7', 'BC8', 'BC9', 'BC10']
    ABS_COLUMNS = ['abs_370', 'abs_430', 'abs_470', 'abs_525', 'abs_565',
                   'abs_590', 'abs_660', 'abs_700', 'abs_880', 'abs_950']
    CAL_COLUMNS = ['abs_550', 'AAE', 'eBC']

    # =========================================================================
    # QC Thresholds
    # =========================================================================
    MIN_BC = 0           # Minimum BC concentration (ng/m³)
    MAX_BC = 20000       # Maximum BC concentration (ng/m³)
    MIN_AAE = 0.7        # Minimum valid AAE (absolute value)
    MAX_AAE = 2.0        # Maximum valid AAE (absolute value)

    # =========================================================================
    # Status Error Codes (bitwise flags)
    # =========================================================================
    ERROR_STATES = [
        1,      # Power Failure
        2,      # Digital Sensor Link Failure
        4,      # Tape Move Failure
        8,      # Maintenance
        16,     # Flow Failure
        32,     # Automatic Tape Advance
        64,     # Detector Failure
        256,    # Sensor Range
        512,    # Nozzle Move Failure
        1024,   # SPI Link Failure
        2048,   # Calibration Audit
        65536,  # Tape Move
    ]

    def _raw_reader(self, file):
        """Read and parse raw BC1054 data files."""
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            _df = read_csv(f, parse_dates=True, index_col=0)
            _df.columns = _df.columns.str.replace(' ', '')

            _df = _df.rename(columns={
                'BC1(ng/m3)': 'BC1', 'BC2(ng/m3)': 'BC2', 'BC3(ng/m3)': 'BC3',
                'BC4(ng/m3)': 'BC4', 'BC5(ng/m3)': 'BC5', 'BC6(ng/m3)': 'BC6',
                'BC7(ng/m3)': 'BC7', 'BC8(ng/m3)': 'BC8', 'BC9(ng/m3)': 'BC9',
                'BC10(ng/m3)': 'BC10'
            })

            _df = _df[self.BC_COLUMNS + ['Status']].apply(to_numeric, errors='coerce')

            return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on BC1054 raw data.

        QC Rules Applied (raw data only)
        ---------------------------------
        1. Duplicate      : Consecutive duplicate rows removed
        2. Status Error   : Invalid instrument status codes
        3. Invalid BC     : BC concentration outside 0-20000 ng/m³
        4. Insufficient   : Less than 50% hourly data completeness

        Note: AAE validation is done in _process() after calculation.
        """
        _index = _df.index.copy()

        # Remove consecutive duplicate rows
        duplicate_rows = _df.eq(_df.shift()).all(axis=1) | _df.eq(_df.shift(-1)).all(axis=1)
        df_qc = _df[~duplicate_rows].copy()

        # Build QC rules declaratively
        qc = QCFlagBuilder()
        qc.add_rules([
            QCRule(
                name='Status Error',
                condition=lambda df: self.QC_control().filter_error_status(df, self.ERROR_STATES),
                description='Invalid instrument status code detected'
            ),
            QCRule(
                name='Invalid BC',
                condition=lambda df: ((df[self.BC_COLUMNS] <= self.MIN_BC) |
                                      (df[self.BC_COLUMNS] > self.MAX_BC)).any(axis=1),
                description=f'BC concentration outside valid range {self.MIN_BC}-{self.MAX_BC} ng/m³'
            ),
            QCRule(
                name='Insufficient',
                condition=lambda df: self.QC_control().hourly_completeness_QC(
                    df[self.BC_COLUMNS], freq=self.meta['freq']
                ),
                description='Less than 50% hourly data completeness'
            ),
        ])

        # Apply all QC rules and get flagged DataFrame
        df_qc = qc.apply(df_qc)

        # Store QC summary for combined output in _process()
        self._qc_summary = qc.get_summary(df_qc)

        return df_qc.reindex(_index)

    def _process(self, _df):
        """
        Calculate absorption coefficients and validate derived parameters.

        Processing Steps
        ----------------
        1. Calculate absorption coefficients at each wavelength
        2. Calculate AAE (Absorption Ångström Exponent)
        3. Calculate eBC (equivalent Black Carbon)
        4. Validate AAE range and update QC_Flag
        """
        _index = _df.index.copy()

        # Calculate absorption coefficients, AAE, and eBC
        _df_cal = _absCoe(_df[self.BC_COLUMNS], instru=self.nam, specified_band=[550])

        # Combine with Status and QC_Flag
        df_out = concat([_df_cal, _df[['Status', 'QC_Flag']]], axis=1)

        # Validate AAE and update QC_Flag
        invalid_aae = (-df_out['AAE'] < self.MIN_AAE) | (-df_out['AAE'] > self.MAX_AAE)
        df_out = self.update_qc_flag(df_out, invalid_aae, 'Invalid AAE')

        # Log combined QC summary with calculated info
        if hasattr(self, '_qc_summary') and self._qc_summary is not None:
            import pandas as pd
            # Add Invalid AAE row before Valid row
            total = len(df_out)
            invalid_aae_row = pd.DataFrame([{
                'Rule': 'Invalid AAE',
                'Count': invalid_aae.sum(),
                'Percentage': f'{invalid_aae.sum() / total * 100:.1f}%',
                'Description': f'AAE outside valid range {self.MIN_AAE}-{self.MAX_AAE}'
            }])
            # Insert before Valid row (last row)
            summary = pd.concat([self._qc_summary.iloc[:-1], invalid_aae_row, self._qc_summary.iloc[-1:]], ignore_index=True)
            self.logger.info(f"{self.nam} QC Summary:")
            for _, row in summary.iterrows():
                self.logger.info(f"  {row['Rule']}: {row['Count']} ({row['Percentage']})")

        # Reorder columns
        all_data_cols = self.BC_COLUMNS + self.ABS_COLUMNS + self.CAL_COLUMNS
        return df_out[all_data_cols + ['QC_Flag']].reindex(_index)
