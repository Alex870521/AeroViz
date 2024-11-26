from pandas import read_table, to_numeric

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'AE33'

    def _raw_reader(self, file):
        if file.stat().st_size / 1024 < 550:
            self.logger.warning(f'\t {file.name} may not be a whole daily data. Make sure the file is correct.')

        _df = read_table(file, parse_dates={'time': [0, 1]}, index_col='time',
                         delimiter=r'\s+', skiprows=5, usecols=range(67))
        _df.columns = _df.columns.str.strip(';')

        # remove data without Status=0, 128 (Not much filter tape), 256 (Not much filter tape)
        if self.meta.get('error_state', False):
            _df = _df.where(~_df['Status'].isin(self.meta['error_state'])).copy()

        _df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7']].apply(to_numeric, errors='coerce')

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        _index = _df.index.copy()

        # remove negative value
        _df = _df.mask((_df <= 0) | (_df > 20000))

        # use IQR_QC
        _df = self.time_aware_IQR_QC(_df, time_window='1h')

        # make sure all columns have values, otherwise set to nan
        return _df.dropna(how='any').reindex(_index)
