from pandas import read_csv, to_numeric, concat, Series

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder
from AeroViz.rawDataReader.core.pre_process import _absCoe


class Reader(AbstractReader):
    """MA350 Aethalometer Data Reader

    A specialized reader for MA350 Aethalometer data files, which measure
    black carbon at multiple wavelengths and provide source apportionment.

    See full documentation at docs/source/instruments/MA350.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'MA350'

    # =========================================================================
    # Column Definitions
    # =========================================================================
    BC_COLUMNS = ['BC1', 'BC2', 'BC3', 'BC4', 'BC5']
    ABS_COLUMNS = ['abs_375', 'abs_470', 'abs_528', 'abs_625', 'abs_880']
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
        1,       # Power Failure
        2,       # Start up
        4,       # Tape advance
        16,      # Optical saturation
        32,      # Sample timing error
        128,     # Flow unstable
        256,     # Pump drive limit
        2048,    # System busy
        8192,    # Tape jam
        16384,   # Tape at end
        32768,   # Tape not ready
        65536,   # Tape transport not ready
        262144,  # Invalid date/time
        524288,  # Tape error
    ]

    def _raw_reader(self, file):
        """
        Read and parse raw MA350 Aethalometer data files.

        Parameters
        ----------
        file : Path or str
            Path to the MA350 data file.

        Returns
        -------
        pandas.DataFrame
            Processed MA350 data with datetime index and standardized black carbon
            and source apportionment columns.
        """
        _df = read_csv(file, parse_dates=['Date / time local'], index_col='Date / time local').rename_axis(
            "Time")

        _df = _df.rename(columns={
            'UV BCc': 'BC1',
            'Blue BCc': 'BC2',
            'Green BCc': 'BC3',
            'Red BCc': 'BC4',
            'IR BCc': 'BC5',
            'Biomass BCc  (ng/m^3)': 'BB mass',
            'Fossil fuel BCc  (ng/m^3)': 'FF mass',
            'Delta-C  (ng/m^3)': 'Delta-C',
            'AAE': 'AAE_ref',
            'BB (%)': 'BB',
        })

        _df = _df[
            ['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BB mass', 'FF mass', 'Delta-C', 'AAE_ref', 'BB', 'Status']].apply(
            to_numeric,
            errors='coerce')

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on MA350 Aethalometer raw data.

        QC Rules Applied (raw data only)
        ---------------------------------
        1. Status Error   : Invalid instrument status codes
        2. Invalid BC     : BC concentration outside 0-20000 ng/m³
        3. Insufficient   : Less than 50% hourly data completeness

        Note: AAE validation is done in _process() after calculation.
        """
        _index = _df.index.copy()
        df_qc = _df.copy()

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
