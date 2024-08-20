import pickle as pkl
from datetime import datetime as dtm
from pathlib import Path

from pandas import concat


class Writer:

    def __init__(self, path_out=None, excel=True, csv=False):
        self.path_out = Path(path_out) if path_out is not None else path_out
        self.excel = excel
        self.csv = csv

    @staticmethod
    def pre_process(_out):
        if isinstance(_out, dict):
            for _ky, _df in _out.items():
                _df.index.name = 'time'
        else:
            _out.index.name = 'time'

        return _out

    def save_out(self, _nam, _out):
        _check = True
        while _check:

            try:
                if self.path_out is not None:
                    self.path_out.mkdir(exist_ok=True, parents=True)
                    with (self.path_out / f'{_nam}.pkl').open('wb') as f:
                        pkl.dump(_out, f, protocol=pkl.HIGHEST_PROTOCOL)

                    if self.excel:
                        from pandas import ExcelWriter
                        with ExcelWriter(self.path_out / f'{_nam}.xlsx') as f:
                            if type(_out) == dict:
                                for _key, _val in _out.items():
                                    _val.to_excel(f, sheet_name=f'{_key}')
                            else:
                                _out.to_excel(f, sheet_name=f'{_nam}')

                    if self.csv:
                        if isinstance(_out, dict):
                            _path_out = self.path_out / _nam
                            _path_out.mkdir(exist_ok=True, parents=True)

                            for _key, _val in _out.items():
                                _val.to_csv(_path_out / f'{_key}.csv')
                        else:
                            _out.to_csv(self.path_out / f'{_nam}.csv')

                _check = False

            except PermissionError as _err:
                print('\n', _err)
                input('\t\t\33[41m Please Close The File And Press "Enter" \33[0m\n')


def run_process(*_ini_set):
    def _decorator(_prcs_fc):
        def _wrap(*arg, **kwarg):
            _fc_name, _nam = _ini_set

            if kwarg.get('nam') is not None:
                _nam = kwarg.pop('nam')

            print(f"\n\t{dtm.now().strftime('%m/%d %X')} : Process \033[92m{_fc_name}\033[0m -> {_nam}")

            _class, _out = _prcs_fc(*arg, **kwarg)
            _out = _class.pre_process(_out)

            _class.save_out(_nam, _out)

            return _out

        return _wrap

    return _decorator


def union_index(*_df_arg):
    _idx = concat(_df_arg, axis=1).index

    return [_df.reindex(_idx) if _df is not None else None for _df in _df_arg]
