from pandas import read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'BC1054'

    def _raw_reader(self, file):
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            _df = read_csv(f, parse_dates=True, index_col=0)

            _df.columns = _df.columns.str.replace(' ', '')

            _df = _df.rename(columns={
                'BC1(ng/m3)': 'BC1',
                'BC2(ng/m3)': 'BC2',
                'BC3(ng/m3)': 'BC3',
                'BC4(ng/m3)': 'BC4',
                'BC5(ng/m3)': 'BC5',
                'BC6(ng/m3)': 'BC6',
                'BC7(ng/m3)': 'BC7',
                'BC8(ng/m3)': 'BC8',
                'BC9(ng/m3)': 'BC9',
                'BC10(ng/m3)': 'BC10'
            })

            # remove data without Status=1, 8, 16, 32 (Automatic Tape Advance), 65536 (Tape Move)
            if self.meta.get('error_state', False):
                _df = _df[~_df['Status'].isin(self.meta.get('error_state'))]

            _df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7', 'BC8', 'BC9', 'BC10']]

            return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    # QC data
    def _QC(self, _df):
        # remove negative value
        _df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7', 'BC8', 'BC9', 'BC10']].mask((_df < 0).copy())

        # QC data in 1h
        return _df.resample('1h').apply(self.n_sigma_QC).resample(self.meta.get("freq")).mean()
