
from pandas import read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'VOC'

    def _raw_reader(self, _file):
        with _file.open('r', encoding='utf-8-sig', errors='ignore') as f:
            _df = read_csv(f, parse_dates=[0], index_col=[0], na_values=('-', 'N.D.'))

            _df.columns = _df.keys().str.strip(' ')
            _df.index.name = 'time'

            try:
                _df = _df[self.meta["key"]].loc[_df.index.dropna()]

            except KeyError:
                _df = _df[self.meta["key_2"]].loc[_df.index.dropna()]

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        return _df
