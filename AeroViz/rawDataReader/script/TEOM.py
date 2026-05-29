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

    # Status condition register
    # -------------------------------------------------------------------------
    # The `status` column (raw `tmoStatusCondition_0` / `System status`) is a
    # 32-bit BITFIELD, not a flat code: the instrument OR-sums the active
    # warning bits and reports the decimal sum (TEOM 1405 / 1405-F manual,
    # Appendix A, Table A-1). So QC must test it bitwise — `ignored_status_errors`
    # can then whitelist an individual condition (e.g. a known dryer warning)
    # by its decimal value regardless of which other bits are co-set.
    #
    # Documented bit meanings (Table A-1; "A"/"B" = FDMS dual-channel sides):
    #   bit 30 (1073741824) %RH High Side A (>=98%)   bit 22 (4194304) %RH High Side B
    #   bit 29 (536870912)  Dryer A (>2)              bit 21 (2097152) Dryer B
    #   bit 28 (268435456)  Cooler A (>0.5C dev)      bit 20 (1048576) Cooler B
    #   bit 27 (134217728)  Exchange Filter A (>90)   bit 19 (524288)  Exchange Filter B
    #   bit 26 (67108864)   Flow A (>10% dev)         bit 18 (262144)  Flow B
    #   bit 25 (33554432)   Heaters Side A (>2% dev)  bit 17 (131072)  Heaters Side B
    #   bit 24 (16777216)   Mass Transducer A (<10Hz) bit 16 (65536)   Mass Transducer B
    #   bit 14 (16384) User I/O   bit 13 (8192) FDMS Device   bit 12 (4096) Head 1
    #   bit 11 (2048)  Head 0     bit 10 (1024) MFC 1         bit 9  (512)  MFC 0
    #   bit 8  (256)   System Bus bit 7  (128)  Vacuum Pressure (<0.1 atm)
    #   bit 6  (64)    Case/Cap Heater (>2% dev)      bit 5 (32) FDMS Valve
    #   bit 4  (16)    Bypass Flow (>10% dev)         bit 3 (8)  Ambient RH&Temp sensor
    #   bit 2  (4)     Database (log failure)         bit 2 (2)  Enclosure Temp (>60C)
    #   bit 0  (1)     Power Failure
    STATUS_COLUMN = 'status'
    STATUS_OK = 0  # 0 = no condition set ("Normal status")
    # Every set bit counts as an error by default (== the old `status != 0`
    # numeric behaviour), but bitwise mode lets a benign condition be cleared
    # per-bit via `ignored_status_errors`. Narrow this list once a site decides
    # which conditions are advisory vs data-invalidating.
    ERROR_STATES = [1 << b for b in range(32)]

    # =========================================================================
    # Format-specific column alias maps
    # =========================================================================
    # The 4M Series Open Path / 1405 / 1405-DF TEOMs share data but ship with
    # very different host software (operator-friendly remote-download GUI vs
    # raw USB SNMP-like export). Both alias maps are applied unconditionally
    # to every file — real-world exports frequently mix the two naming styles
    # within a single CSV (e.g. a remote-download file that carries a stray
    # `tmoTEOMAMC12Hr_0` column from a firmware that pre-populates SNMP names).
    # All keys map to the SAME short canonical names so downstream QC sees one
    # schema regardless of source.
    METADATA_ALIASES_REMOTE = {
        # Remote download / GUI export — Chinese month support, friendly names
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
    }
    METADATA_ALIASES_USB = {
        # USB / auto-export — SNMP-style `tmoXxx_0` names, ISO-ish timestamps
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
    }
    # Chinese month names (remote-download GUI sometimes localizes them).
    _CHINESE_MONTHS = {'十一月': '11', '十二月': '12',
                       '一月': '01', '二月': '02', '三月': '03', '四月': '04',
                       '五月': '05', '六月': '06', '七月': '07', '八月': '08',
                       '九月': '09', '十月': '10'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _raw_reader(self, file):
        """Read and parse raw TEOM data files in various formats.

        Returns all columns from the raw file. Column selection is deferred
        to _QC() and _process() stages.

        Supported formats (auto-detected and logged):
        - 'remote': Time Stamp with Chinese month names, columns like 'PM-2.5 base MC'
        - 'usb':    Date + Time columns, columns like 'tmoTEOMABaseMC_0'
        """
        _df = read_csv(file, skiprows=3, index_col=False)

        # Apply BOTH alias maps — real-world TEOM exports often mix conventions
        # (one file can carry both 'PM-2.5 base MC' and a leftover SNMP column).
        # Either key, if present, lands on the same short canonical name.
        _df = _df.rename(columns={**self.METADATA_ALIASES_REMOTE,
                                  **self.METADATA_ALIASES_USB})

        # Detect format from post-rename column presence and log it so a
        # mixed-source batch can be diagnosed without spelunking individual files.
        if 'time' in _df.columns:
            fmt = 'remote'
            self.logger.debug(f"{file.name}: TEOM remote-download/auto-export format")
            _tm_idx = _df.time
            for _ori, _rpl in self._CHINESE_MONTHS.items():
                _tm_idx = _tm_idx.str.replace(_ori, _rpl)
            _df = _df.set_index(to_datetime(_tm_idx, errors='coerce', format='%d - %m - %Y %X'))

        elif 'Date' in _df.columns and 'Time' in _df.columns:
            fmt = 'usb'
            self.logger.debug(f"{file.name}: TEOM USB-export format")
            _df['time'] = to_datetime(_df['Date'] + ' ' + _df['Time'], errors='coerce')
            _df.drop(columns=['Date', 'Time'], inplace=True)
            _df.set_index('time', inplace=True)

        else:
            # Loud, file-named error — easier to triage than the original
            # bare NotImplementedError because the operator can grep the log
            # for which file in a batch is the troublemaker.
            self.logger.error(
                f"{file.name}: unrecognized TEOM column layout — neither "
                f"`Time Stamp` (remote) nor `Date`+`Time` (USB) found after "
                f"rename. Cols seen: {list(_df.columns[:10])}...")
            raise NotImplementedError(
                f"Unsupported TEOM data format in {file.name}")

        _df.index.name = 'time'

        # Drop the 'time' column if it remains after set_index
        _df = _df.drop(columns=['time'], errors='ignore')

        # Remove duplicates and NaN indices
        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

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
                    _df, error_codes=self.ERROR_STATES, status_column=self.STATUS_COLUMN,
                    status_type='bitwise',
                    ignored_values=self.kwargs.get('ignored_status_errors')
                ),
                description='Status condition register has a non-whitelisted warning bit set'
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
