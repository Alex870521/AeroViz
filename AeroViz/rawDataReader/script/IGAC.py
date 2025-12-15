# read meteorological data from google sheet


from pandas import read_csv, to_numeric, Series

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder


class Reader(AbstractReader):
    """IGAC (In-situ Gas and Aerosol Composition) Monitor Data Reader

    This class handles the reading and parsing of IGAC monitor data files,
    which provide real-time measurements of water-soluble inorganic ions in
    particulate matter.

    See full documentation at docs/source/instruments/IGAC.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'IGAC'

    # =========================================================================
    # Column Definitions
    # =========================================================================
    CATION_COLUMNS = ['Na+', 'NH4+', 'K+', 'Mg2+', 'Ca2+']
    ANION_COLUMNS = ['Cl-', 'NO2-', 'NO3-', 'PO43-', 'SO42-']
    MAIN_IONS = ['SO42-', 'NO3-', 'NH4+']

    # =========================================================================
    # Detection Limits (MDL) in ug/m3
    # =========================================================================
    MDL = {
        'Na+': 0.06,
        'NH4+': 0.05,
        'K+': 0.05,
        'Mg2+': 0.12,
        'Ca2+': 0.07,
        'Cl-': 0.07,
        'NO2-': 0.05,
        'NO3-': 0.11,
        'SO42-': 0.08,
    }

    def _raw_reader(self, file):
        """
        Read and parse raw IGAC monitor data files.

        Parameters
        ----------
        file : Path or str
            Path to the IGAC data file.

        Returns
        -------
        pandas.DataFrame
            Processed IGAC data with datetime index and ion concentration columns.
        """
        with file.open('r', encoding='utf-8-sig', errors='ignore') as f:
            _df = read_csv(f, parse_dates=True, index_col=0, na_values='-')

            _df.columns = _df.keys().str.strip(' ')
            _df.index.name = 'time'

            _df = _df.apply(to_numeric, errors='coerce')

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on IGAC ion composition data.

        QC Rules Applied
        ----------------
        1. Mass Closure    : Total ion mass > PM2.5 mass
        2. Missing Main    : Main ions (NH4+, SO42-, NO3-) not present
        3. Below MDL       : Ion concentration below detection limit
        4. Ion Balance     : Cation/Anion ratio outside valid range
        """
        _index = _df.index.copy()

        # Get ion columns that exist in the data
        ion_columns = [col for col in self.MDL.keys() if col in _df.columns]
        df_qc = _df[ion_columns].copy()

        # Calculate total ion mass for mass closure check
        total_ions = df_qc.sum(axis=1, min_count=1)
        pm25 = _df['PM2.5'] if 'PM2.5' in _df.columns else Series(float('inf'), index=_df.index)

        # Calculate cation/anion ratio for ion balance check
        cation_cols = [c for c in self.CATION_COLUMNS if c in df_qc.columns]
        anion_cols = [c for c in self.ANION_COLUMNS if c in df_qc.columns]
        cation_sum = df_qc[cation_cols].sum(axis=1, min_count=1) if cation_cols else Series(0, index=df_qc.index)
        anion_sum = df_qc[anion_cols].sum(axis=1, min_count=1) if anion_cols else Series(1, index=df_qc.index)
        ca_ratio = cation_sum / anion_sum.replace(0, float('nan'))

        # Calculate IQR bounds for ion balance
        q1, q3 = ca_ratio.quantile(0.25), ca_ratio.quantile(0.75)
        iqr = q3 - q1
        ca_lower, ca_upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr

        # Build QC rules declaratively
        qc = QCFlagBuilder()
        qc.add_rules([
            QCRule(
                name='Mass Closure',
                condition=lambda df: total_ions > pm25,
                description='Total ion mass exceeds PM2.5 mass'
            ),
            QCRule(
                name='Missing Main',
                condition=lambda df: df[self.MAIN_IONS].isna().any(axis=1) if all(
                    c in df.columns for c in self.MAIN_IONS) else Series(False, index=df.index),
                description='Missing main ions (NH4+, SO42-, NO3-)'
            ),
            QCRule(
                name='Below MDL',
                condition=lambda df: Series(
                    [any(df.loc[idx, col] < self.MDL.get(col, 0)
                         for col in ion_columns if col in df.columns and not Series(df.loc[idx, col]).isna().any())
                     for idx in df.index],
                    index=df.index
                ),
                description='Ion concentration below detection limit'
            ),
            QCRule(
                name='Ion Balance',
                condition=lambda df: (ca_ratio < ca_lower) | (ca_ratio > ca_upper) | ca_ratio.isna(),
                description='Cation/Anion ratio outside valid range'
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
