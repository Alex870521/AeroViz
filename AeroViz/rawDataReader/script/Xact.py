from pandas import read_csv, to_datetime, to_numeric, Series

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder


class Reader(AbstractReader):
    """Xact 625i XRF Analyzer Data Reader

    A specialized reader for Xact 625i continuous XRF analyzer data files,
    which measure elemental composition of particulate matter.
    """
    nam = 'Xact'

    # Element symbols with atomic numbers (extracted from column headers)
    ELEMENTS = [
        'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe',
        'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo',
        'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Cs', 'Ba', 'La', 'Ce',
        'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu',
        'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Th', 'Pa', 'U'
    ]

    # Environmental/status columns to keep
    ENV_COLUMNS = [
        'AT', 'SAMPLE_T', 'BP', 'TAPE', 'FLOW_25', 'FLOW_ACT', 'FLOW_STD', 'VOLUME',
        'TUBE_T', 'ENCLOSURE_T', 'FILAMENT_V', 'SDD_T', 'DPP_T', 'RH',
        'WIND', 'WIND_DIR', 'SAMPLE_TIME', 'ALARM'
    ]

    # =========================================================================
    # Alarm Code Definitions
    # =========================================================================
    # Error codes (100-110) - indicate instrument malfunction, invalidate data
    ERROR_CODES = {
        100: 'Xray Voltage Error',
        101: 'Xray Current Error',
        102: 'Tube Temperature Error',
        103: 'Enclosure Temperature Error',
        104: 'Tape Error',
        105: 'Pump Error',
        106: 'Filter Wheel Error',
        107: 'Dynamic Rod Error',
        108: 'Nozzle Error',
        109: 'Energy Calibration Error',
        110: 'Software Error',
    }

    # Warning codes (200-203) - indicate upscale warnings
    WARNING_CODES = {
        200: 'Upscale Cr Warning',
        201: 'Upscale Pb Warning',
        202: 'Upscale Cd Warning',
        203: 'Upscale Nb Warning',
    }

    # =========================================================================
    # QC Thresholds
    # =========================================================================
    MIN_VALUE = 0
    MAX_VALUE = 100000  # ng/m3

    def _raw_reader(self, file):
        """Read and parse raw Xact 625i XRF data files."""
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            f.readline()  # skip row 0 (element names)
            headers = f.readline().strip().split(',')
            headers.append('_extra_')  # data has one extra field at end
            _df = read_csv(f, names=headers, on_bad_lines='skip')

        # Parse time column
        _df['time'] = to_datetime(_df['TIME'], format='%m/%d/%Y %H:%M:%S', errors='coerce')
        _df = _df.set_index('time')
        _df = _df.loc[~_df.index.duplicated() & _df.index.notna()]
        _df.index = _df.index.round('1h')

        # Rename environmental/status columns
        rename_map = {
            'AT (C)': 'AT',
            'SAMPLE (C)': 'SAMPLE_T',
            'BP (mmHg)': 'BP',
            'TAPE (mmHg)': 'TAPE',
            'FLOW 25 (slpm)': 'FLOW_25',
            'FLOW ACT (lpm)': 'FLOW_ACT',
            'FLOW STD (slpm)': 'FLOW_STD',
            'VOLUME (L)': 'VOLUME',
            'TUBE (C)': 'TUBE_T',
            'ENCLOSURE (C)': 'ENCLOSURE_T',
            'FILAMENT (V)': 'FILAMENT_V',
            'SDD (C)': 'SDD_T',
            'DPP (C)': 'DPP_T',
            'RH (%)': 'RH',
            'WIND (m/s)': 'WIND',
            'WIND DIR (deg)': 'WIND_DIR',
            'SAMPLE TIME (min)': 'SAMPLE_TIME',
            'ALARM': 'ALARM',
        }

        # Build element column rename map
        for col in _df.columns:
            for elem in self.ELEMENTS:
                # Match pattern like "Mg 12 (ng/m3)" or " K 19 (ng/m3)" for concentration
                if f'{elem} ' in col and '(ng/m3)' in col and 'uncert' not in col.lower():
                    rename_map[col] = elem
                # Match pattern like "Al Uncert (ng/m3)" or "Mg uncert (ng/m3)" for uncertainty
                elif f'{elem} ' in col and 'uncert' in col.lower():
                    rename_map[col] = f'{elem}_uncert'

        _df = _df.rename(columns=rename_map)

        # Select columns to keep (elements + uncertainties + environmental)
        keep_cols = []
        for elem in self.ELEMENTS:
            if elem in _df.columns:
                keep_cols.append(elem)
            if f'{elem}_uncert' in _df.columns:
                keep_cols.append(f'{elem}_uncert')
        for env_col in self.ENV_COLUMNS:
            if env_col in _df.columns:
                keep_cols.append(env_col)

        _df = _df[[col for col in keep_cols if col in _df.columns]]
        _df = _df.apply(to_numeric, errors='coerce')

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """Perform quality control on Xact XRF data.

        QC Rules Applied
        ----------------
        1. Instrument Error  : ALARM code 100-110 indicates instrument error
        2. Upscale Warning   : ALARM code 200-203 indicates upscale warning
        3. Invalid Value     : Element concentration outside valid range (0-100000 ng/m3)
        4. High Uncertainty  : Measurement uncertainty > 50% of value
        """
        _index = _df.index.copy()
        df_qc = _df.copy()

        # Get element columns (exclude uncertainty and environmental columns)
        element_cols = [col for col in df_qc.columns if col in self.ELEMENTS]

        # Build QC rules declaratively
        qc = QCFlagBuilder()

        # Add Instrument Error rule (ALARM codes 100-110)
        if 'ALARM' in df_qc.columns:
            qc.add_rules([
                QCRule(
                    name='Instrument Error',
                    condition=lambda df: df['ALARM'].isin(list(self.ERROR_CODES.keys())),
                    description='Instrument error detected (ALARM code 100-110)'
                ),
                QCRule(
                    name='Upscale Warning',
                    condition=lambda df: df['ALARM'].isin(list(self.WARNING_CODES.keys())),
                    description='Upscale warning detected (ALARM code 200-203)'
                ),
            ])

        # Add Invalid Value rule
        if element_cols:
            qc.add_rules([
                QCRule(
                    name='Invalid Value',
                    condition=lambda df, cols=element_cols: (
                            (df[cols] < self.MIN_VALUE) | (df[cols] > self.MAX_VALUE)
                    ).any(axis=1),
                    description=f'Concentration outside valid range ({self.MIN_VALUE}-{self.MAX_VALUE} ng/m3)'
                ),
            ])

        # Add High Uncertainty rule
        uncert_cols = [f'{elem}_uncert' for elem in element_cols if f'{elem}_uncert' in df_qc.columns]
        if uncert_cols:
            qc.add_rules([
                QCRule(
                    name='High Uncertainty',
                    condition=lambda df, elems=element_cols: self._check_high_uncertainty(df, elems),
                    description='Measurement uncertainty > 50% of value'
                ),
            ])

        # Apply all QC rules and get flagged DataFrame
        df_qc = qc.apply(df_qc)

        # Log QC summary
        summary = qc.get_summary(df_qc)
        self.logger.info(f"{self.nam} QC Summary:")
        for _, row in summary.iterrows():
            self.logger.info(f"  {row['Rule']}: {row['Count']} ({row['Percentage']})")

        # Get output columns: elements + uncertainties + environmental + QC_Flag
        output_cols = element_cols + uncert_cols + [c for c in self.ENV_COLUMNS if c in df_qc.columns] + ['QC_Flag']
        return df_qc[[c for c in output_cols if c in df_qc.columns]].reindex(_index)

    def _check_high_uncertainty(self, df, element_cols):
        """Check if uncertainty is > 50% of measured value."""
        mask = Series(False, index=df.index)
        for elem in element_cols:
            uncert_col = f'{elem}_uncert'
            if uncert_col in df.columns and elem in df.columns:
                # Flag if uncertainty > 50% of value (and value > 0)
                mask = mask | ((df[uncert_col] > 0.5 * df[elem]) & (df[elem] > 0))
        return mask

    def decode_alarm(self, alarm_code):
        """Decode ALARM code to human-readable message.

        Parameters
        ----------
        alarm_code : int
            The ALARM code from the Xact data

        Returns
        -------
        str
            Human-readable description of the alarm
        """
        if alarm_code == 0:
            return 'Normal'
        elif alarm_code in self.ERROR_CODES:
            return self.ERROR_CODES[alarm_code]
        elif alarm_code in self.WARNING_CODES:
            return self.WARNING_CODES[alarm_code]
        else:
            return f'Unknown Alarm ({alarm_code})'
