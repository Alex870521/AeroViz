import pandas as pd
from pandas import to_datetime, read_csv, to_numeric, Series

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder
from AeroViz.rawDataReader.core.pre_process import _scaCoe


class Reader(AbstractReader):
    """Nephelometer (NEPH) Data Reader

    A specialized reader for integrating nephelometer data files, which measure
    light scattering properties of aerosols at multiple wavelengths.

    See full documentation at docs/source/instruments/NEPH.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'NEPH'

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
    STATUS_COLUMN = 'status'
    STATUS_OK = 0  # Status code 0 means normal operation

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._status_data = None  # Store status flag data separately

    def _raw_reader(self, file):
        """
        Read and parse raw Nephelometer data files.

        Parameters
        ----------
        file : Path or str
            Path to the Nephelometer data file.

        Returns
        -------
        pandas.DataFrame
            Processed Nephelometer data with datetime index and scattering coefficient columns.
        """
        _df = read_csv(file, header=None, names=range(11))

        _df_grp = _df.groupby(0)

        # T : time
        _idx_tm = to_datetime(
            _df_grp.get_group('T')[[1, 2, 3, 4, 5, 6]]
            .map(lambda x: f"{int(x):02d}")
            .agg(''.join, axis=1),
            format='%Y%m%d%H%M%S'
        )

        # D : data
        # col : 3~8 B G R BB BG BR
        # 1e6
        try:
            _df_dt = _df_grp.get_group('D')[[1, 2, 3, 4, 5, 6, 7, 8]].set_index(_idx_tm)

            try:
                _df_out = (_df_dt.groupby(1).get_group('NBXX')[[3, 4, 5, 6, 7, 8]] * 1e6).reindex(_idx_tm)
            except KeyError:
                _df_out = (_df_dt.groupby(1).get_group('NTXX')[[3, 4, 5, 6, 7, 8]] * 1e6).reindex(_idx_tm)

            _df_out.columns = ['B', 'G', 'R', 'BB', 'BG', 'BR']
            _df_out.index.name = 'Time'

            # Y : state
            # col : 5 RH, col : 9 status
            _df_st = _df_grp.get_group('Y')
            _df_out['RH'] = _df_st[5].values
            status_values = to_numeric(_df_st[9].values, errors='coerce').astype('Int64')

            _df = _df_out[['B', 'G', 'R', 'BB', 'BG', 'BR', 'RH']].apply(to_numeric, errors='coerce')
            _df = _df.loc[~_df.index.duplicated() & _df.index.notna()]

            # Store status data separately (aligned with filtered index)
            status_col = pd.Series(status_values, index=_df_out.index, name=self.STATUS_COLUMN)
            status_col = status_col.reindex(_df.index)

            # Accumulate status data
            if self._status_data is None:
                self._status_data = status_col
            else:
                self._status_data = pd.concat([self._status_data, status_col])

            return _df

        except ValueError:  # Define valid groups and find invalid indices
            invalid_indices = _df[~_df[0].isin({'B', 'G', 'R', 'D', 'T', 'Y', 'Z'})].index
            self.logger.warning(
                f"\tInvalid values in {file.name}: {', '.join(f'{_}:{_df.at[_, 0]}' for _ in invalid_indices)}."
                f" Skipping file.")

            return None

    def _QC(self, _df):
        """
        Perform quality control on Nephelometer raw data.

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

        # Combine with RH and QC_Flag
        if 'RH' in _df.columns:
            df_out = pd.concat([_df_cal, _df[['RH', 'QC_Flag']]], axis=1)
        else:
            df_out = pd.concat([_df_cal, _df[['QC_Flag']]], axis=1)

        # Log QC summary
        if hasattr(self, '_qc_summary') and self._qc_summary is not None:
            self.logger.info(f"{self.nam} QC Summary:")
            for _, row in self._qc_summary.iterrows():
                self.logger.info(f"  {row['Rule']}: {row['Count']} ({row['Percentage']})")

        return df_out.reindex(_index)
