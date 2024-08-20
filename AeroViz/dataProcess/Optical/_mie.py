# from PyMieScatt import Mie_SD

from ._mie_sd import Mie_SD


def _mie(_psd_ori, _RI_ori, _wave):
    _ori_idx = _psd_ori.index.copy()
    _cal_idx = _psd_ori.loc[_RI_ori.dropna().index].dropna(how='all').index

    _psd, _RI = _psd_ori.loc[_cal_idx], _RI_ori.loc[_cal_idx]

    _out = Mie_SD(_RI.values, 550, _psd)

    return _out.reindex(_ori_idx)
