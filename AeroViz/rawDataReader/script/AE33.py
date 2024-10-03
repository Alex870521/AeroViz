from pandas import read_table

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'AE33'

    def _raw_reader(self, file):
        if file.stat().st_size / 1024 < 550:
            print('\t It may not be a whole daily data.')

        _df = read_table(file, parse_dates={'time': [0, 1]}, index_col='time',
                         delimiter=r'\s+', skiprows=5, usecols=range(67))
        _df.columns = _df.columns.str.strip(';')

        # remove data without Status=0, 128 (Not much filter tape), 256 (Not much filter tape)
        if self.meta.get('error_state', False):
            _df = _df.where(~_df['Status'].isin(self.meta['error_state'])).copy()

        _df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7']]

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        # remove negative value
        _df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7']].mask((_df < 0).copy())

        # QC data in 1h
        return _df.resample('1h').apply(self.n_sigma_QC).resample(self.meta.get("freq")).mean()
