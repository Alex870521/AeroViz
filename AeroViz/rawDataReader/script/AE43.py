from pandas import read_csv

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

        _df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7']]

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    # QC data
    def _QC(self, _df):
        # remove negative value
        _df = _df.mask((_df < 0).copy())

        # QC data in 1h
        return _df.resample('1h').apply(self.n_sigma_QC).resample(self.meta.get("freq")).mean()
