import pandas as pd
from pandas import Series, concat

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder
from AeroViz.rawDataReader.core.pre_process import _scaCoe


class Reader(AbstractReader):
    """Aurora Integrating Nephelometer Data Reader

    A specialized reader for Aurora nephelometer data files, which measure aerosol light
    scattering properties at multiple wavelengths.

    See full documentation at docs/source/instruments/Aurora.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'Aurora'

    # =========================================================================
    # Column Definitions
    # =========================================================================
    SCAT_COLUMNS = ['B', 'G', 'R', 'BB', 'BG', 'BR']
    CAL_COLUMNS = ['sca_550', 'SAE']

    # =========================================================================
    # QC Thresholds
    # =========================================================================
    MIN_SCAT_VALUE = 0       # Minimum scattering coefficient (Mm^-1)
    MAX_SCAT_VALUE = 2000    # Maximum scattering coefficient (Mm^-1)

    # Status Flag
    STATUS_COLUMN = 'Status'  # Common status column names to check
    STATUS_COLUMNS = ['Status', 'status', 'Error', 'error', 'Flag', 'flag']
    STATUS_OK = 0  # Status code 0 means normal operation

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._status_data = None  # Store status flag data separately

    def _raw_reader(self, file):
        """
        Read and parse raw Aurora nephelometer data files.

        Parameters
        ----------
        file : Path or str
            Path to the Aurora data file.

        Returns
        -------
        pandas.DataFrame
            Processed Aurora data with datetime index and standardized
            scattering coefficient columns.
        """
        _df = pd.read_csv(file, low_memory=False, index_col=0)

        _df.index = pd.to_datetime(_df.index, errors='coerce')
        _df.index.name = 'time'

        _df.columns = _df.keys().str.strip(' ')

        # consider another csv format
        _df = _df.rename(columns={
            '0°σspB': 'B',
            '0°σspG': 'G',
            '0°σspR': 'R',
            '90°σspB': 'BB',
            '90°σspG': 'BG',
            '90°σspR': 'BR',
            'Blue': 'B',
            'Green': 'G',
            'Red': 'R',
            'B_Blue': 'BB',
            'B_Green': 'BG',
            'B_Red': 'BR',
        })

        # Check for status column (try multiple common names)
        status_col_name = None
        for col_name in self.STATUS_COLUMNS:
            if col_name in _df.columns:
                status_col_name = col_name
                break

        _df_out = _df[['B', 'G', 'R', 'BB', 'BG', 'BR']].apply(pd.to_numeric, errors='coerce')
        _df_out = _df_out.loc[~_df_out.index.duplicated() & _df_out.index.notna()]

        # Store status data separately if available
        if status_col_name is not None:
            status_col = pd.to_numeric(_df[status_col_name], errors='coerce').astype('Int64')
            status_col = status_col.reindex(_df_out.index)

            # Accumulate status data
            if self._status_data is None:
                self._status_data = status_col
            else:
                self._status_data = concat([self._status_data, status_col])

        return _df_out

    def _QC(self, _df):
        """
        Perform quality control on Aurora nephelometer raw data.

        QC Rules Applied (raw data only)
        ---------------------------------
        1. Status Error      : Non-zero status code indicates instrument error
        2. No Data           : All scattering columns are NaN
        3. Invalid Scat Value: Scattering coefficient outside 0-2000 Mm^-1
        4. Invalid Scat Rel. : Wavelength dependence violation (B < G < R)
        5. Insufficient      : Less than 50% hourly data completeness

        Note: SAE calculation is done in _process() after QC.
        """
        _index = _df.index.copy()
        df_qc = _df.copy()

        # Get status flag from instance variable (populated during _raw_reader)
        status_flag = None
        if self._status_data is not None:
            # Align status data with current dataframe index
            status_flag = self._status_data.reindex(_df.index)

        # Identify rows with all data missing (handled separately)
        all_missing_mask = df_qc[self.SCAT_COLUMNS].isna().all(axis=1)

        # Build QC rules declaratively
        qc = QCFlagBuilder()

        # Add Status Error rule if status flag is available
        if status_flag is not None:
            # Use default argument to capture status_flag value for proper type inference
            qc.add_rules([
                QCRule(
                    name='Status Error',
                    condition=lambda df, sf=status_flag: Series(
                        (sf != self.STATUS_OK) & sf.notna(),
                        index=df.index
                    ).fillna(False),
                    description=f'Status code is not {self.STATUS_OK} (non-zero indicates error)'
                ),
            ])

        qc.add_rules([
            QCRule(
                name='No Data',
                condition=lambda df: Series(all_missing_mask, index=df.index),
                description='All scattering columns are NaN'
            ),
            QCRule(
                name='Invalid Scat Value',
                condition=lambda df: ((df[self.SCAT_COLUMNS] <= self.MIN_SCAT_VALUE) |
                                      (df[self.SCAT_COLUMNS] > self.MAX_SCAT_VALUE)).any(axis=1),
                description=f'Scattering coefficient outside {self.MIN_SCAT_VALUE}-{self.MAX_SCAT_VALUE} Mm^-1'
            ),
            QCRule(
                name='Invalid Scat Rel',
                condition=lambda df: (df['B'] < df['G']) & (df['G'] < df['R']),
                description='Wavelength dependence violation (Blue < Green < Red)'
            ),
            QCRule(
                name='Insufficient',
                condition=lambda df: self.QC_control().hourly_completeness_QC(
                    df[self.SCAT_COLUMNS], freq=self.meta['freq']
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
        Calculate scattering coefficients and SAE.

        Processing Steps
        ----------------
        1. Calculate scattering coefficient at 550nm
        2. Calculate SAE (Scattering Ångström Exponent)

        Parameters
        ----------
        _df : pd.DataFrame
            Quality-controlled DataFrame with scattering columns and QC_Flag

        Returns
        -------
        pd.DataFrame
            DataFrame with sca_550, SAE, and updated QC_Flag
        """
        _index = _df.index.copy()

        # Calculate SAE and scattering at 550nm
        _df_cal = _scaCoe(_df[self.SCAT_COLUMNS], instru=self.nam, specified_band=[550])

        # Combine with QC_Flag
        df_out = concat([_df_cal, _df[['QC_Flag']]], axis=1)

        # Log QC summary
        if hasattr(self, '_qc_summary') and self._qc_summary is not None:
            self.logger.info(f"{self.nam} QC Summary:")
            for _, row in self._qc_summary.iterrows():
                self.logger.info(f"  {row['Rule']}: {row['Count']} ({row['Percentage']})")

        return df_out.reindex(_index)
