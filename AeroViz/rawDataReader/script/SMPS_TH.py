from pandas import to_datetime, read_table

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'SMPS_TH'

    def _raw_reader(self, file):
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            _df = read_table(f, skiprows=18, parse_dates={'Time': ['Date', 'Start Time']}).set_index('Time')
            _key = list(_df.keys()[6:-26])

            _newkey = {}
            for _k in _key:
                _newkey[_k] = float(_k).__round__(4)

            # _newkey['Total Conc.(#/cm)'] = 'total'
            # _newkey['Mode(nm)']	= 'mode'

            _df_idx = to_datetime(_df.index, errors='coerce')
        return _df[_newkey.keys()].rename(_newkey, axis=1).set_index(_df_idx).loc[_df_idx.dropna()]

    # QC data
    def _QC(self, _df):
        import numpy as n

        # mask out the data size lower than 7
        _df['total'] = _df.sum(axis=1, min_count=1) * (n.diff(n.log(_df.keys().to_numpy(float)))).mean()
        _df_size = _df['total'].dropna().resample('1h').size().resample(_df.index.freq).ffill()
        _df = _df.mask(_df_size < 7)

        # remove total conc. lower than 2000
        _df = _df.mask(_df['total'] < 2000)

        # remove the bin over 400 nm which num. conc. larger than 4000
        _df_remv_ky = _df.keys()[:-2][_df.keys()[:-2] >= 400.]

        _df[_df_remv_ky] = _df[_df_remv_ky].copy().mask(_df[_df_remv_ky] > 4000.)

        return _df[_df.keys()[:-1]]
