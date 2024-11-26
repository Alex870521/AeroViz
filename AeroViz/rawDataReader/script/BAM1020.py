from pandas import read_csv, to_numeric, NA

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'BAM1020'

    def _raw_reader(self, file):
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
        _index = _df.index.copy()

        # remove negative value
        _df = _df.mask((_df <= 0) | (_df > 500))

        # use IQR_QC
        _df = self.time_aware_IQR_QC(_df, time_window='1h')

        # make sure all columns have values, otherwise set to nan
        return _df.dropna(how='any').reindex(_index)
