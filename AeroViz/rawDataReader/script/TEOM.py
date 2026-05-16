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

    def _raw_reader(self, file):
        """Read and parse raw TEOM data files in various formats.

        Returns all columns from the raw file. Column selection is deferred
        to _QC() and _process() stages.

        Supported formats:
        - Remote download: Time Stamp with Chinese month names, columns like 'PM-2.5 base MC'
        - USB/auto export: Date + Time columns, columns like 'tmoTEOMABaseMC_0'
        """
        _df = read_csv(file, skiprows=3, index_col=False)

        # Chinese month name conversion dictionary
        _time_replace = {'十一月': '11', '十二月': '12', '一月': '01', '二月': '02', '三月': '03', '四月': '04',
                         '五月': '05', '六月': '06', '七月': '07', '八月': '08', '九月': '09', '十月': '10'}

        # Standardize column names across formats
        _df = _df.rename(columns={
            # Remote download format
            'Time Stamp': 'time',
            'System status': 'status',
            'PM-2.5 base MC': 'PM_NV',
            'PM-2.5 reference MC': 'PM_ref',
            'PM-2.5 MC': 'PM_Total',
            'PM-2.5 1-Hr MC': 'PM_1Hr',
            'PM-2.5 24-Hr MC': 'PM_24Hr',
            'PM-2.5 TEOM frequency': 'frequency',
            'PM-2.5 TEOM noise': 'noise',
            'PM-2.5 TEOM filter load': 'filter_load',
            'PM-2.5 TEOM filter pressure': 'filter_pressure',
            'PM-2.5 vol. flow rate': 'flow_rate',
            'Bypass volumetric flow rate': 'bypass_flow',
            'PM-2.5 air tube temp': 'air_tube_temp',
            'Cap temperature': 'cap_temp',
            'Case temperature': 'case_temp',
            'PM-2.5 cooler temp': 'cooler_temp',
            'PM-2.5 dryer dew point': 'dryer_dew_point',
            'Ambient temperature': 'ambient_temp',
            'Ambient relative humidity': 'ambient_RH',
            'Ambient pressure': 'ambient_pressure',
            'Vacuum pump pressure': 'pump_pressure',
            # USB/auto export format
            'time_stamp': 'time',
            'tmoStatusCondition_0': 'status',
            'tmoTEOMABaseMC_0': 'PM_NV',
            'tmoTEOMARefMC_0': 'PM_ref',
            'tmoTEOMAMC_0': 'PM_Total',
            'tmoTEOMAMC1Hr_0': 'PM_1Hr',
            'tmoTEOMAMC12Hr_0': 'PM_12Hr',
            'tmoTEOMAFrequency_0': 'frequency',
            'tmoTEOMANoise_0': 'noise',
            'tmoTEOMAFilterLoad_0': 'filter_load',
            'tmoTEOMADryerDewPoint_0': 'dryer_dew_point',
            'tmoTEOMAFlowVolumetric_0': 'flow_rate',
            'tmoBypassFlowVolumetric_0': 'bypass_flow',
            'tmoTEOMAAirTubeHeatTemp_0': 'air_tube_temp',
            'tmoCapHeatTemp_0': 'cap_temp',
            'tmoCaseHeatTemp_0': 'case_temp',
            'tmoAmbientTemp_0': 'ambient_temp',
            'tmoAmbientRH_0': 'ambient_RH',
            'tmoVacPumpPressure_0': 'pump_pressure',
        })

        # Handle different time formats
        if 'time' in _df.columns:  # Remote download or auto export with time column
            _tm_idx = _df.time
            # Convert Chinese month names if present
            for _ori, _rpl in _time_replace.items():
                _tm_idx = _tm_idx.str.replace(_ori, _rpl)

            _df = _df.set_index(to_datetime(_tm_idx, errors='coerce', format='%d - %m - %Y %X'))

        elif 'Date' in _df.columns and 'Time' in _df.columns:  # USB download format
            _df['time'] = to_datetime(_df['Date'] + ' ' + _df['Time'], errors='coerce')
            _df.drop(columns=['Date', 'Time'], inplace=True)
            _df.set_index('time', inplace=True)

        else:
            raise NotImplementedError("Unsupported TEOM data format")

        _df.index.name = 'time'

        # Drop the 'time' column if it remains after set_index
        _df = _df.drop(columns=['time'], errors='ignore')

        # Remove duplicates and NaN indices
        _df = _df.loc[~_df.index.duplicated() & _df.index.notna()]

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
        5. Spike                : Sudden value change (vectorized spike detection)
        6. Insufficient         : Less than 50% hourly data completeness
        """
        _index = _df.index.copy()
        df_qc = _df.copy()

        # Build QC rules declaratively
        qc = QCFlagBuilder()

        qc.add_rules([
            QCRule(
                name='Status Error',
                condition=lambda df: self.QC_control().filter_error_status(
                    _df, status_column=self.STATUS_COLUMN, status_type='numeric', ok_value=self.STATUS_OK
                ),
                description=f'Status code is not {self.STATUS_OK} (non-zero indicates error)'
            ),
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

        return df_qc.reindex(_index)

    def _process(self, _df):
        """
        Calculate derived parameters from QC'd TEOM data.

        Calculates Volatile_Fraction = (PM_Total - PM_NV) / PM_Total.
        """
        _df = _df.copy()
        _df['Volatile_Fraction'] = ((_df['PM_Total'] - _df['PM_NV']) / _df['PM_Total']).__round__(4)
        return _df
