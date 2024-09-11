import numpy as np
from pandas import to_datetime, read_table

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'APS_3321'

    def _raw_reader(self, file):
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            _df = read_table(f, skiprows=6, parse_dates={'Time': ['Date', 'Start Time']}).set_index('Time')
            _key = list(_df.keys()[3:54])  ## 542 ~ 1981

            # create new keys
            _newkey = {}
            for _k in _key:
                _newkey[_k] = float(_k).__round__(4)
            # _newkey['Mode(m)'] = 'mode'

            # get new dataframe
            _df = _df[_newkey.keys()].rename(_newkey, axis=1)
            # df['total'] = _df[list(_newkey.values())[:-1]].sum(axis=1)*(n.diff(n.log(_df.keys()[:-1].to_numpy(float))).mean()).copy()

            _df_idx = to_datetime(_df.index, errors='coerce')

        return _df.set_index(_df_idx).loc[_df_idx.dropna()]

    # QC data
    def _QC(self, _df):
        # mask out the data size lower than 7
        _df['total'] = _df.sum(axis=1, min_count=1) * (np.diff(np.log(_df.keys().to_numpy(float)))).mean()
        _df_size = _df['total'].dropna().resample('1h').size().resample(_df.index.freq).ffill()
        _df = _df.mask(_df_size < 7)

        # remove total conc. lower than 700
        _df = _df.mask(_df['total'] > 700)

        # not confirmed
        """
        ## remove the bin over 4000 nm which num. conc. larger than 1
        # _df_remv_ky = _df.keys()[:-2][_df.keys()[:-2]>=4.]

        # _df_1hr[_df_remv_ky] = _df_1hr[_df_remv_ky].copy().mask(_df_1hr[_df_remv_ky]>1.)
        # """

        return _df[_df.keys()[:-1]]
