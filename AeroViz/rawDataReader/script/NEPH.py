from pandas import to_datetime, read_csv, DataFrame

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
	nam = 'NEPH'

	def _raw_reader(self, _file):
		with _file.open('r', encoding='utf-8', errors='ignore') as f:
			_df = read_csv(f, header=None, names=range(11))

			_df_grp = _df.groupby(0)

			# T : time
			_df_tm = _df_grp.get_group('T')[[1, 2, 3, 4, 5, 6]].astype(int)

			for _k in [2, 3, 4, 5, 6]:
				_df_tm[_k] = _df_tm[_k].astype(int).map('{:02d}'.format).copy()
			_df_tm = _df_tm.astype(str)

			_idx_tm = to_datetime((_df_tm[1] + _df_tm[2] + _df_tm[3] + _df_tm[4] + _df_tm[5] + _df_tm[6]),
								  format='%Y%m%d%H%M%S')

			# D : data
			# col : 3~8 B G R BB BG BR
			# 1e6
			try:
				_df_dt = _df_grp.get_group('D')[[1, 2, 3, 4, 5, 6, 7, 8]].set_index(_idx_tm)
				_df_out = (_df_dt.groupby(1).get_group('NBXX')[[3, 4, 5, 6, 7, 8]] * 1e6).reindex(_idx_tm)
				_df_out.columns = ['B', 'G', 'R', 'BB', 'BG', 'BR']
				_df_out.index.name = 'Time'

				# Y : state
				# col : 5 RH
				_df_st = _df_grp.get_group('Y')
				_df_out['RH'] = _df_st[5].values
				_df_out['status'] = _df_st[9].values

				_df_out.mask(_df_out['status'] != 0)  # 0000 -> numeric to 0

				return _df_out[['B', 'G', 'R', 'BB', 'BG', 'BR', 'RH']]

			except ValueError:
				group_sizes = _df_grp.size()
				print(group_sizes)
				# Define the valid groups
				valid_groups = {'B', 'G', 'R', 'D', 'T', 'Y', 'Z'}

				# Find the rows where the value in the first column is not in valid_groups
				invalid_indices = _df[~_df[0].isin(valid_groups)].index

				# Print the invalid indices and their corresponding values
				invalid_values = _df.loc[invalid_indices, 0]
				print("Invalid values and their indices:")
				for idx, value in zip(invalid_indices, invalid_values):
					print(f"Index: {idx}, Value: {value}")

				# If there's a length mismatch, return an empty DataFrame with the same index and column names
				columns = ['B', 'G', 'R', 'BB', 'BG', 'BR', 'RH']
				_df_out = DataFrame(index=_idx_tm, columns=columns)
				_df_out.index.name = 'Time'
				print(f'\n\t\t\t Length mismatch in {_file} data. Returning an empty DataFrame.')
				return _df_out

	# QC data
	def _QC(self, _df):
		# remove negative value
		_df = _df.mask((_df <= 0).copy())

		# call by _QC function
		# QC data in 1 hr
		def _QC_func(_df_1hr):
			_df_ave = _df_1hr.mean()
			_df_std = _df_1hr.std()
			_df_lowb, _df_highb = _df_1hr < (_df_ave - _df_std * 1.5), _df_1hr > (_df_ave + _df_std * 1.5)

			return _df_1hr.mask(_df_lowb | _df_highb).copy()

		return _df.resample('1h', group_keys=False).apply(_QC_func)
