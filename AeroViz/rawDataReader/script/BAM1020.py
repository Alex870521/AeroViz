from pandas import read_csv, to_numeric, NA

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder


class Reader(AbstractReader):
    """BAM1020 (Beta Attenuation Monitor) Data Reader

    A specialized reader for BAM1020 data files, which measure PM2.5 mass concentration
    using beta attenuation technology.

    See ``docs/api/instruments/mass/BAM1020.md`` for usage and
    ``docs/guide/instrument-qc.md`` for the
    file layout, status codes and QC rules.
    """
    nam = 'BAM1020'

    # =========================================================================
    # QC Thresholds
    # =========================================================================
    MIN_CONC = 0       # Minimum PM2.5 concentration (ug/m3)
    MAX_CONC = 500     # Maximum PM2.5 concentration (ug/m3)

    def _raw_reader(self, file):
        """
        Read and parse raw BAM1020 data files.

        Parameters
        ----------
        file : Path or str
            Path to the BAM1020 data file.

        Returns
        -------
        pandas.DataFrame
            Processed BAM1020 data with datetime index and PM2.5 concentration column.
        """
        PM = 'Conc'

        _df = read_csv(file, parse_dates=True, index_col=0, usecols=range(0, 21))
        _df.rename(columns={'Conc (mg/m3)': PM}, inplace=True)

        # remove data when Conc = 1 or 0
        _df[PM] = _df[PM].replace(1, NA)

        # Keep every column (R1) — the BAM writes flow, RH, ambient temperature
        # and status alongside the concentration, and those are what explain a
        # suspect reading. Only the columns that convert cleanly are coerced, so
        # textual metadata survives.
        for column in _df.columns:
            converted = to_numeric(_df[column], errors='coerce')
            if converted.notna().any() or _df[column].isna().all():
                _df[column] = converted

        # Convert ONLY the concentration from mg/m3 to ug/m3. This used to
        # multiply the whole frame, which was harmless only because the frame had
        # been narrowed to that single column first.
        _df[PM] = _df[PM] * 1000

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on BAM1020 data.

        QC Rules Applied
        ----------------
        1. Invalid Conc    : Concentration outside valid range (0-500 ug/m3)
        2. Spike           : Sudden value change (vectorized spike detection)
        """
        _index = _df.index.copy()
        df_qc = _df.copy()

        # Build QC rules declaratively
        qc = self.qc_builder()
        qc.add_rules([
            QCRule(
                name='Invalid Conc',
                condition=lambda df: (df['Conc'] <= self.MIN_CONC) | (df['Conc'] > self.MAX_CONC),
                description=f'Concentration outside valid range ({self.MIN_CONC}-{self.MAX_CONC} ug/m3)'
            ),
            QCRule(
                name='Spike',
                condition=lambda df: self.QC_control().spike_detection(
                    df[['Conc']], max_change_rate=3.0
                ),
                description='Sudden unreasonable value change detected'
            ),
        ])

        # Apply all QC rules and get flagged DataFrame
        df_qc = qc.apply(df_qc)

        # Log QC summary
        self.log_qc_summary(qc.get_summary(df_qc))

        return df_qc.reindex(_index)
