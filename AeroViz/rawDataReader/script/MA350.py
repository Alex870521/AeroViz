from pandas import read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'MA350'

    def _raw_reader(self, file):
        _df = read_csv(file, parse_dates=['Date / time local'], index_col='Date / time local').rename_axis("Time")

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

        _df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BB mass', 'FF mass', 'Delta-C', 'AAE', 'BB']]

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    # QC data
    def _QC(self, _df):
        # remove negative value
        _df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BB mass', 'FF mass', 'AAE', 'BB']].mask((_df < 0).copy())

        # QC data in 1h
        return _df.resample('1h').apply(self.n_sigma_QC).resample(self.meta.get("freq")).mean()
