from pandas import read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'VOC'

    def _raw_reader(self, file):
        with file.open('r', encoding='utf-8-sig', errors='ignore') as f:
            _df = read_csv(f, parse_dates=True, index_col=0, na_values=('-', 'N.D.'))

            _df.columns = _df.keys().str.strip(' ')
            _df.index.name = 'time'

            support_voc = set(self.meta["key"])

            valid_keys = [key for key in _df.keys() if key in support_voc]
            invalid_keys = [key for key in _df.keys() if key not in support_voc]

            if invalid_keys:
                self.logger.warning(f'{invalid_keys} are not supported keys.')
                print(f'\n\t{invalid_keys} are not supported keys.'
                      f'\n\tPlease check the\033[91m support_voc.md\033[0m file to use the correct name.')

            if valid_keys:
                return _df[valid_keys].loc[~_df.index.duplicated() & _df.index.notna()]
            else:
                self.logger.warning("沒有找到匹配的鍵。返回原始DataFrame並移除含NaN的行。")
                return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        return _df
