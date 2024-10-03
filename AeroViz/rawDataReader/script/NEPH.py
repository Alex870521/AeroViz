from pandas import to_datetime, read_csv, DataFrame

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'NEPH'

    def _raw_reader(self, file):
        with file.open('r', encoding='utf-8', errors='ignore') as f:
            _df = read_csv(f, header=None, names=range(11))

            _df_grp = _df.groupby(0)

            # T : time
            _idx_tm = to_datetime(
                _df_grp.get_group('T')[[1, 2, 3, 4, 5, 6]]
                .map(lambda x: f"{int(x):02d}")
                .agg(''.join, axis=1),
                format='%Y%m%d%H%M%S'
            )

            # D : data
            # col : 3~8 B G R BB BG BR
            # 1e6
            try:
                _df_dt = _df_grp.get_group('D')[[1, 2, 3, 4, 5, 6, 7, 8]].set_index(_idx_tm)

                try:
                    _df_out = (_df_dt.groupby(1).get_group('NBXX')[[3, 4, 5, 6, 7, 8]] * 1e6).reindex(_idx_tm)
                except KeyError:
                    _df_out = (_df_dt.groupby(1).get_group('NTXX')[[3, 4, 5, 6, 7, 8]] * 1e6).reindex(_idx_tm)

                _df_out.columns = ['B', 'G', 'R', 'BB', 'BG', 'BR']
                _df_out.index.name = 'Time'

                # Y : state
                # col : 5 RH
                _df_st = _df_grp.get_group('Y')
                _df_out['RH'] = _df_st[5].values
                _df_out['status'] = _df_st[9].values

                _df_out.mask(_df_out['status'] != 0)  # 0000 -> numeric to 0

                _df = _df_out[['B', 'G', 'R', 'BB', 'BG', 'BR', 'RH']]

                return _df.loc[~_df.index.duplicated() & _df.index.notna()]

            except ValueError:
                # Define valid groups and find invalid indices
                invalid_indices = _df[~_df[0].isin({'B', 'G', 'R', 'D', 'T', 'Y', 'Z'})].index
                print("Invalid values and their indices:")
                print("\n".join([f"Index: {idx}, Value: {_df.at[idx, 0]}" for idx in invalid_indices]))

                # Return an empty DataFrame with specified columns if there's a length mismatch
                _df_out = DataFrame(index=_idx_tm, columns=['B', 'G', 'R', 'BB', 'BG', 'BR', 'RH'])
                _df_out.index.name = 'Time'
                print(f'\n\t\t\t Length mismatch in {file} data. Returning an empty DataFrame.')
                return _df_out

    # QC data
    def _QC(self, _df):
        # remove negative value
        _df = _df.mask((_df <= 5).copy())

        # total scattering is larger than back scattering
        _df = _df[(_df['BB'] < _df['B']) & (_df['BG'] < _df['G']) & (_df['BR'] < _df['R'])]

        # QC data in 1h
        return _df.resample('1h').apply(self.n_sigma_QC).resample(self.meta.get("freq")).mean()
