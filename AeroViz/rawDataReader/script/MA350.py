from pandas import read_csv, to_numeric

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'MA350'

    def _raw_reader(self, file):
        _df = read_csv(file, parse_dates=['Date / time local'], index_col='Date / time local').rename_axis(
            "Time")

        _df = _df.rename(columns={
            'UV BCc': 'BC1',
            'Blue BCc': 'BC2',
            'Green BCc': 'BC3',
            'Red BCc': 'BC4',
            'IR BCc': 'BC5',
            'Biomass BCc  (ng/m^3)': 'BB mass',
            'Fossil fuel BCc  (ng/m^3)': 'FF mass',
            'Delta-C  (ng/m^3)': 'Delta-C',
            'AAE': 'AAE',
            'BB (%)': 'BB',
        })

        # if self.meta.get('error_state', False):
        #     _df = _df.where(~_df['Status'].isin(self.meta['error_state'])).copy()

        _df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BB mass', 'FF mass', 'Delta-C', 'AAE', 'BB']].apply(to_numeric,
                                                                                                           errors='coerce')

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    # QC data
    def _QC(self, _df):
        _index = _df.index.copy()

        # remove negative value
        _df = _df.mask(
            (_df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5']] <= 0) | (_df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5']] > 20000))

        # use IQR_QC
        _df = self.time_aware_IQR_QC(_df, time_window='1h')

        # make sure all columns have values, otherwise set to nan
        return _df.dropna(how='any').reindex(_index)
