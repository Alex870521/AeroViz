import numpy as np
from pandas import to_datetime, read_table

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'APS'

    def _raw_reader(self, file):
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            _df = read_table(f, skiprows=6, parse_dates={'Time': ['Date', 'Start Time']},
                             date_format='%m/%d/%y %H:%M:%S').set_index('Time')

            # 542 nm ~ 1981 nm
            _df = _df.iloc[:, 3:54].rename(columns=lambda x: round(float(x), 4))

            _df_idx = to_datetime(_df.index, format='%m/%d/%y %H:%M:%S', errors='coerce')

        return _df.set_index(_df_idx).loc[_df_idx.dropna()]

    # QC data
    def _QC(self, _df):
        _df = _df.copy()
        _index = _df.index.copy()

        # mask out the data size lower than 7
        _df.loc[:, 'total'] = _df.sum(axis=1, min_count=1) * (np.diff(np.log(_df.keys().to_numpy(float)))).mean()

        hourly_counts = (_df['total']
                         .dropna()
                         .resample('h')
                         .size()
                         .resample('6min')
                         .ffill()
                         .reindex(_df.index, method='ffill', tolerance='6min'))

        # Remove data with less than 6 data per hour
        _df = _df.mask(hourly_counts < 6)

        # remove total conc. lower than 700 or lower than 1
        _df = _df.mask((_df['total'] > 700) | (_df['total'] < 1))

        return _df[_df.keys()[:-1]]
