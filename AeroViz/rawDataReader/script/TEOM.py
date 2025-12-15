from pandas import to_datetime, read_csv, to_numeric, Series, concat

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder


class Reader(AbstractReader):
    """TEOM Output Data Formats Reader

    A specialized reader for TEOM (Tapered Element Oscillating Microbalance)
    particulate matter data files with support for multiple file formats and
    comprehensive quality control.

    See full documentation at docs/source/instruments/TEOM.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'TEOM'

    # =========================================================================
    # Column Definitions
    # =========================================================================
    PM_COLUMNS = ['PM_NV', 'PM_Total']
    OUTPUT_COLUMNS = ['PM_NV', 'PM_Total', 'Volatile_Fraction']

    # =========================================================================
    # QC Thresholds
    # =========================================================================
    MAX_NOISE = 0.01    # Maximum acceptable noise level

    # Status Flag
    STATUS_COLUMN = 'status'
    STATUS_OK = 0  # Status code 0 means normal operation

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._status_data = None  # Store status flag data separately

    def _raw_reader(self, file):
        """
        Read and parse raw TEOM data files in various formats.

        Handles multiple TEOM data formats and standardizes them to a consistent
        structure with uniform column names and datetime index.

        Parameters
        ----------
        file : Path or str
            Path to the TEOM data file.

        Returns
        -------
        pandas.DataFrame
            Processed raw TEOM data with datetime index and standardized columns.

        Raises
        ------
        NotImplementedError
            If the file format is not recognized as a supported TEOM data format.
        """
        _df = read_csv(file, skiprows=3, index_col=False)

        # Chinese month name conversion dictionary
        _time_replace = {'十一月': '11', '十二月': '12', '一月': '01', '二月': '02', '三月': '03', '四月': '04',
                         '五月': '05', '六月': '06', '七月': '07', '八月': '08', '九月': '09', '十月': '10'}

        # Try both naming conventions (will ignore columns that don't exist)
        _df = _df.rename(columns={
            # Remote download format
            'Time Stamp': 'time',
            'System status': 'status',
            'PM-2.5 base MC': 'PM_NV',
            'PM-2.5 MC': 'PM_Total',
            'PM-2.5 TEOM noise': 'noise',
            # USB/auto export format
            'time_stamp': 'time',
            'tmoStatusCondition_0': 'status',
            'tmoTEOMABaseMC_0': 'PM_NV',
            'tmoTEOMAMC_0': 'PM_Total',
            'tmoTEOMANoise_0': 'noise'
        })

        # Handle different time formats
        if 'time' in _df.columns:  # Remote download or auto export with time column
            _tm_idx = _df.time
            # Convert Chinese month names if present
            for _ori, _rpl in _time_replace.items():
                _tm_idx = _tm_idx.str.replace(_ori, _rpl)

            _df = _df.set_index(to_datetime(_tm_idx, errors='coerce', format='%d - %m - %Y %X'))

        elif 'Date' in _df.columns and 'Time' in _df.columns:  # USB download format
            _df['time'] = to_datetime(_df['Date'] + ' ' + _df['Time'],
                                      errors='coerce', format='%Y-%m-%d %H:%M:%S')
            _df.drop(columns=['Date', 'Time'], inplace=True)
            _df.set_index('time', inplace=True)

        else:
            raise NotImplementedError("Unsupported TEOM data format")

        _df = _df[['PM_NV', 'PM_Total', 'noise', 'status']].apply(to_numeric, errors='coerce')

        # Remove duplicates and NaN indices
        _df = _df.loc[~_df.index.duplicated() & _df.index.notna()]

        # Store status data separately
        if self.STATUS_COLUMN in _df.columns:
            status_col = _df[self.STATUS_COLUMN].astype('Int64')

            # Accumulate status data
            if self._status_data is None:
                self._status_data = status_col
            else:
                self._status_data = concat([self._status_data, status_col])

        return _df

    def _QC(self, _df):
        """
        Perform quality control on TEOM particulate matter data.

        QC Rules Applied
        ----------------
        1. Status Error         : Non-zero status code indicates instrument error
        2. High Noise           : noise >= 0.01
        3. Non-positive         : PM_NV <= 0 OR PM_Total <= 0
        4. NV > Total           : PM_NV > PM_Total (physically impossible)
        5. Invalid Vol Frac     : Volatile_Fraction outside valid range (0-1)
        6. Spike                : Sudden value change (vectorized spike detection)
        7. Insufficient         : Less than 50% hourly data completeness
        """
        _index = _df.index.copy()

        # Get status flag from instance variable (populated during _raw_reader)
        status_flag = None
        if self._status_data is not None:
            # Align status data with current dataframe index
            status_flag = self._status_data.reindex(_df.index)

        # Pre-process: calculate Volatile_Fraction
        _df['Volatile_Fraction'] = ((_df['PM_Total'] - _df['PM_NV']) / _df['PM_Total']).__round__(4)
        df_qc = _df.copy()

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
                name='High Noise',
                condition=lambda df: df['noise'] >= self.MAX_NOISE,
                description=f'Noise level >= {self.MAX_NOISE}'
            ),
            QCRule(
                name='Non-positive',
                condition=lambda df: (df[self.PM_COLUMNS] <= 0).any(axis=1),
                description='PM_NV or PM_Total <= 0 (non-positive value)'
            ),
            QCRule(
                name='NV > Total',
                condition=lambda df: df['PM_NV'] > df['PM_Total'],
                description='PM_NV exceeds PM_Total (physically impossible)'
            ),
            QCRule(
                name='Invalid Vol Frac',
                condition=lambda df: (df['Volatile_Fraction'] < 0) | (df['Volatile_Fraction'] > 1),
                description='Volatile_Fraction outside 0-1 range'
            ),
            QCRule(
                name='Spike',
                condition=lambda df: self.QC_control().spike_detection(
                    df[self.PM_COLUMNS], max_change_rate=3.0
                ),
                description='Sudden unreasonable value change detected'
            ),
            QCRule(
                name='Insufficient',
                condition=lambda df: self.QC_control().hourly_completeness_QC(
                    df[self.PM_COLUMNS], freq=self.meta['freq']
                ),
                description='Less than 50% hourly data completeness'
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
