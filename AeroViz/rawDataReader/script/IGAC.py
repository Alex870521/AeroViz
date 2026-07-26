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

    # Detection limits (MDL) and measurement ranges (MR) come from the vendor
    # specification recorded in `config/supported_instruments.py` — the single
    # source of truth. Species whose entry is ``None`` are not measured by this
    # instrument and are skipped everywhere below.

    @property
    def MDL(self) -> dict:
        """Method detection limits (µg/m³) for the species this instrument measures."""
        return {k: v for k, v in (self.meta.get('MDL') or {}).items() if v is not None}

    @property
    def MR(self) -> dict:
        """Upper measurement range (µg/m³) per species."""
        return {k: v for k, v in (self.meta.get('MR') or {}).items() if v is not None}

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
        Perform quality control on IGAC ion and gas composition data.

        QC Rules Applied
        ----------------
        1. Mass Closure    : Total ion mass > PM2.5 mass
        2. Missing Main    : Main ions (NH4+, SO42-, NO3-) not present
        3. Above MR        : Concentration above the instrument's measurement range
        4. Ion Balance     : Cation/Anion ratio outside valid range

        Detection limits are reported per species in the log (how much of each
        sits below its MDL) rather than as a row-level flag. A below-MDL value is
        a *valid measurement of a low concentration*, not a broken row — and
        because a non-`Valid` flag NaNs the whole row downstream, flagging it
        would delete every other species measured in that same hour. Above-MR is
        different: it is outside what the instrument can report, so it is flagged.
        """
        _index = _df.index.copy()

        # Species this instrument measures (ions + gases), per the vendor spec in
        # the config. Gases (HCl, HNO3, NH3, …) used to be dropped here.
        mdl = self.MDL
        species = [col for col in mdl if col in _df.columns]
        df_qc = _df[species].copy()

        # Calculate total ion mass for mass closure check (aerosol ions only —
        # gases are not part of the PM2.5 mass budget)
        ion_columns = [c for c in self.CATION_COLUMNS + self.ANION_COLUMNS if c in df_qc.columns]
        total_ions = df_qc[ion_columns].sum(axis=1, min_count=1) if ion_columns else Series(0.0, index=df_qc.index)
        pm25 = _df['PM2.5'] if 'PM2.5' in _df.columns else Series(float('inf'), index=_df.index)

        # Calculate cation/anion ratio for ion balance check
        cation_cols = [c for c in self.CATION_COLUMNS if c in df_qc.columns]
        anion_cols = [c for c in self.ANION_COLUMNS if c in df_qc.columns]
        cation_sum = df_qc[cation_cols].sum(axis=1, min_count=1) if cation_cols else Series(0, index=df_qc.index)
        anion_sum = df_qc[anion_cols].sum(axis=1, min_count=1) if anion_cols else Series(1, index=df_qc.index)
        ca_ratio = cation_sum / anion_sum.replace(0, float('nan'))

        # Flag ratios outside 1.5*IQR via the shared helper. iqr() masks
        # outliers to NaN, so .isna() == (out of bounds) | (already missing) —
        # exactly the previous (ca < lower) | (ca > upper) | isna condition.
        ca_outlier = self.QC_control().iqr(ca_ratio.to_frame('ca'))['ca'].isna()

        # Vectorised over-range mask from the config measurement ranges.
        mr = {k: v for k, v in self.MR.items() if k in df_qc.columns}
        above_mr = (df_qc[list(mr)] > Series(mr)).any(axis=1) if mr else Series(False, index=df_qc.index)

        # Build QC rules declaratively
        qc = self.qc_builder()
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
                name='Above MR',
                condition=lambda df: above_mr.reindex(df.index).fillna(False),
                description='Concentration above the instrument measurement range'
            ),
            QCRule(
                name='Ion Balance',
                condition=lambda df: ca_outlier,
                description='Cation/Anion ratio outside valid range'
            ),
        ])

        # Apply all QC rules and get flagged DataFrame
        df_qc = qc.apply(df_qc)

        # Log QC summary
        self.log_qc_summary(qc.get_summary(df_qc))

        self.log_below_mdl(df_qc, mdl)

        return df_qc.reindex(_index)
