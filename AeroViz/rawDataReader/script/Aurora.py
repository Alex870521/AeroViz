from pandas import to_datetime, read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'Aurora'

    def _raw_reader(self, file):
        with file.open('r', encoding='utf-8-sig', errors='ignore') as f:
            _df = read_csv(f, low_memory=False, index_col=0)

            _df.index = to_datetime(_df.index, errors='coerce')
            _df.index.name = 'time'

            _df.columns = _df.keys().str.strip(' ')

            # consider another csv format
            _df = _df.rename(columns={
                '0°σspB': 'B', '0°σspG': 'G', '0°σspR': 'R',
                '90°σspB': 'BB', '90°σspG': 'BG', '90°σspR': 'BR',
                'Blue': 'B', 'Green': 'G', 'Red': 'R',
                'B_Blue': 'BB', 'B_Green': 'BG', 'B_Red': 'BR',
                'RH': 'RH'
            })

            _df = _df[['B', 'G', 'R', 'BB', 'BG', 'BR', 'RH']]

            return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    # QC data
    def _QC(self, _df):
        # remove negative value
        _df = _df.mask((_df <= 0) | (_df > 2000)).copy()

        # total scattering is larger than back scattering
        _df = _df[(_df['BB'] < _df['B']) & (_df['BG'] < _df['G']) & (_df['BR'] < _df['R'])]

        # QC data in 1h
        return _df.resample('1h').apply(self.n_sigma_QC).resample(self.meta.get("freq")).mean()
