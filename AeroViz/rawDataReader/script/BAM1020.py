from pandas import read_csv, to_numeric, NA

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    """ BAM1020 (Beta Attenuation Monitor) Data Reader

    A specialized reader for BAM1020 data files, which measure PM2.5 mass concentration
    using beta attenuation technology.

    See full documentation at docs/source/instruments/BAM1020.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'BAM1020'

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

        _df = _df[[PM]].apply(to_numeric, errors='coerce')

        # tranfer unit from mg/m3 to ug/m3
        _df = _df * 1000

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on BAM1020 data.

        Parameters
        ----------
        _df : pandas.DataFrame
            Raw BAM1020 data with datetime index and concentration column.

        Returns
        -------
        pandas.DataFrame
            Quality-controlled BAM1020 data with invalid measurements masked.

        Notes
        -----
        Applies the following QC filters:
        1. Value range: Valid PM2.5 concentrations between 0-500 μg/m³
        2. Time-based outlier detection: Uses 1-hour window for IQR-based filtering
        3. Complete record requirement: Removes rows with any missing values
        """
        _index = _df.index.copy()

        # remove negative value
        _df = _df.mask((_df <= 0) | (_df > 500))

        # use IQR_QC
        _df = self.time_aware_IQR_QC(_df, time_window='1h')

        # make sure all columns have values, otherwise set to nan
        return _df.dropna(how='any').reindex(_index)
