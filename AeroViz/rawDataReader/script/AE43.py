from pandas import read_csv, to_numeric

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'AE43'

    def _raw_reader(self, file):
        _df = read_csv(file, parse_dates={'time': ['StartTime']}, index_col='time')
        _df_id = _df['SetupID'].iloc[-1]

        # get last SetupID data
        _df = _df.groupby('SetupID').get_group(_df_id)[
            ['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7', 'Status']].copy()

        # remove data without Status=0, 128 (Not much filter tape), 256 (Not much filter tape)
        if self.meta.get('error_state', False):
            _df = _df.where(~_df['Status'].isin(self.meta['error_state'])).copy()

        _df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7']].apply(to_numeric, errors='coerce')

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    # QC data
    def _QC(self, _df):
        _index = _df.index.copy()

        # remove negative value
        _df = _df.mask((_df <= 0) | (_df > 20000))

        # use IQR_QC
        _df = self.time_aware_IQR_QC(_df, time_window='1h')

        # make sure all columns have values, otherwise set to nan
        return _df.dropna(how='any').reindex(_index)
