from pandas import to_datetime, read_csv, Series

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder


class Reader(AbstractReader):
    """ GRIMM Aerosol Spectrometer Data Reader

    A specialized reader for GRIMM data files, which measure particle size distributions
    in the range of 0.25-32 μm.

    See ``docs/api/instruments/particle-sizers/GRIMM.md`` and
    ``docs/api/instruments/raw-formats-and-status.md`` for the file layout and QC
    procedure.
    """
    nam = 'GRIMM'

    def _raw_reader(self, file):
        """
        Read and parse raw GRIMM data files.

        Parameters
        ----------
        file : Path or str
            Path to the GRIMM data file.

        Returns
        -------
        pandas.DataFrame or None
            Processed GRIMM data with datetime index and size channels as columns.
            Returns None if the file is empty.
        """
        _df = read_csv(file, header=233, delimiter='\t', index_col=0, parse_dates=[0], encoding='ISO-8859-1',
                       dayfirst=True).rename_axis("Time")
        _df.index = to_datetime(_df.index, format="%d/%m/%Y %H:%M:%S", dayfirst=True)

        if file.name.startswith("A407ST"):
            _df.drop(_df.columns[0:11].tolist() + _df.columns[128:].tolist(), axis=1, inplace=True)
        else:
            _df.drop(_df.columns[0:11].tolist() + _df.columns[-5:].tolist(), axis=1, inplace=True)

        if _df.empty:
            self.logger.warning(f"{file.name} is empty.")
            return None

        return _df / 0.035

    def _QC(self, _df):
        """
        Perform quality control on GRIMM size-distribution data.

        QC Rules Applied
        ----------------
        1. No Data        : every size channel is NaN
        2. Negative Conc  : any size channel is negative (physically impossible)
        3. Insufficient   : less than 50% hourly data completeness

        Notes
        -----
        Deliberately conservative. Concentration *range* limits (the equivalent
        of SMPS's ``MIN_TOTAL_CONC`` / ``APS``'s ``MAX_TOTAL_CONC``) are **not**
        applied: this reader has no sample corpus to calibrate a plausible range
        against, and a wrong threshold silently deletes good data. The three
        rules here need no site-specific tuning — a negative count is invalid
        under any configuration.

        Producing a ``QC_Flag`` at all is required by the pipeline contract (see
        ``docs/guide/data-levels.md``, rule R2): rates are computed by comparing
        the raw frame against the flag, so a reader without one leaves the
        report rate-less.
        """
        _index = _df.index.copy()
        df_qc = _df.copy()

        # Size channels are the numeric-valued measurement columns; the reader
        # already dropped the metadata columns in `_raw_reader`.
        channels = df_qc.select_dtypes(include='number').columns.tolist()

        qc = QCFlagBuilder()
        qc.add_rules([
            QCRule(
                name='No Data',
                condition=lambda df: (df[channels].isna().all(axis=1)
                                      if channels else Series(True, index=df.index)),
                description='All size channels are NaN'
            ),
            QCRule(
                name='Negative Conc',
                condition=lambda df: (df[channels] < 0).any(axis=1) if channels else Series(False, index=df.index),
                description='Negative concentration in at least one size channel'
            ),
            QCRule(
                name='Insufficient',
                condition=lambda df: (self.QC_control().hourly_completeness_QC(
                    df[channels], freq=self._resolved_freq or self.meta['freq'])
                    if channels else Series(False, index=df.index)),
                description='Less than 50% hourly data completeness'
            ),
        ])

        df_qc = qc.apply(df_qc)

        summary = qc.get_summary(df_qc)
        self.logger.info(f"{self.nam} QC Summary:")
        for _, row in summary.iterrows():
            self.logger.info(f"  {row['Rule']}: {row['Count']} ({row['Percentage']})")

        return df_qc.reindex(_index)
