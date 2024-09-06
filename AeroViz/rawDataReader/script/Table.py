# read meteorological data from google sheet

from pandas import read_csv, to_datetime

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'Table'

    def _raw_reader(self, file):
        with file.open('r', encoding='utf-8-sig', errors='ignore') as f:
            _df = read_csv(f, low_memory=False, index_col=0)

            _df.index = to_datetime(_df.index, errors='coerce')
            _df.index.name = 'time'

            _df.columns = _df.keys().str.strip(' ')

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        # remove negative value
        _df = _df.mask((_df < 0).copy())

        # QC data in 6h
        return _df.resample('6h').apply(self.basic_QC).resample(self.meta.get("freq")).mean()
