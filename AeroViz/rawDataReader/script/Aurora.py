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

    def _raw_reader(self, file):
        """Read and parse raw Aurora nephelometer data files.

        Returns all columns from the raw file. Column selection is deferred
        to _QC() and _process() stages.
        """
        _df = pd.read_csv(file, low_memory=False, index_col=0)

        _df.index = pd.to_datetime(_df.index, errors='coerce')
        _df.index.name = 'time'

        _df.columns = _df.keys().str.strip(' ')

        # Standardize column names across formats
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

        # Normalize status column name
        for col_name in self.STATUS_COLUMNS:
            if col_name in _df.columns and col_name != self.STATUS_COLUMN:
                _df = _df.rename(columns={col_name: self.STATUS_COLUMN})
                break

        # Drop redundant time column
        _df = _df.drop(columns=['Raw_Data_Time'], errors='ignore')

        _df = _df.loc[~_df.index.duplicated() & _df.index.notna()]

        return _df

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

        # Identify rows with all data missing (handled separately)
        all_missing_mask = df_qc[self.SCAT_COLUMNS].isna().all(axis=1)

        # Build QC rules declaratively
        qc = QCFlagBuilder()

        qc.add_rules([
            QCRule(
                name='Status Error',
                condition=lambda df: self.QC_control().filter_error_status(
                    _df, status_column=self.STATUS_COLUMN, status_type='numeric', ok_value=self.STATUS_OK,
                    ignored_values=self.kwargs.get('ignored_status_errors')
                ),
                description=f'Status code is not {self.STATUS_OK} (non-zero indicates error)'
            ),
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

        # Preserve all non-SCAT columns (T1, T2, RH, P, S1, S2, Status, QC_Flag, etc.)
        non_scat_cols = [c for c in _df.columns if c not in self.SCAT_COLUMNS]
        df_out = concat([_df_cal, _df[non_scat_cols]], axis=1)

        # Log QC summary
        if hasattr(self, '_qc_summary') and self._qc_summary is not None:
            self.logger.info(f"{self.nam} QC Summary:")
            for _, row in self._qc_summary.iterrows():
                self.logger.info(f"  {row['Rule']}: {row['Count']} ({row['Percentage']})")

        return df_out.reindex(_index)
