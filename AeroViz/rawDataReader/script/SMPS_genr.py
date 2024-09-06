from pandas import to_datetime, read_table, to_numeric

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'SMPS_genr'

    def _raw_reader(self, file):
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:

            skiprows = 0
            for _line in f:

                if _line.split('\t')[0] == 'Sample #':
                    f.seek(0)
                    break

                skiprows += 1

            _df = read_table(f, skiprows=skiprows)
            _tm_idx = to_datetime(_df['Date'] + _df['Start Time'], format='%m/%d/%y%X', errors='coerce')

            # index
            _df = _df.set_index(_tm_idx).loc[_tm_idx.dropna()]

            # keys
            _key = to_numeric(_df.keys(), errors='coerce')
            _df.columns = _key
            _df = _df.loc[:, ~_key.isna()]

        return _df.apply(to_numeric, errors='coerce')

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
