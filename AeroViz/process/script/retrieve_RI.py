import numpy as np
from pandas import DataFrame

from AeroViz.process.core.SizeDist import SizeDist
from AeroViz.process.method import Mie_PESD


def retrieve_RI(_df: DataFrame,
                _PNSD: DataFrame,
                nMin: float = 1.33,
                nMax: float = 1.60,
                kMin: float = 0.00,
                kMax: float = 0.60,
                spaceSize: int = 31,
                dlogdp: float = 0.014
                ) -> DataFrame:
    nRange = np.linspace(nMin, nMax, num=spaceSize)
    kRange = np.linspace(kMin, kMax, spaceSize)
    Delta_array = np.zeros((spaceSize, spaceSize))
    # 同一時間除了折射率其餘數據皆相同 因此在折射率的迴圈外
    bext_mea, bsca_mea, babs_mea = _df['Extinction'], _df['Scattering'], _df['Absorption']

    dp = SizeDist(data=_PNSD).dp
    for ki, k in enumerate(kRange):
        for ni, n in enumerate(nRange):
            m = n + (1j * k)
            ndp = np.array(_df[3:])

            ext_dist, sca_dist, abs_dist = Mie_PESD(m, 550, dp, ndp)

            bext_cal = sum(ext_dist) * dlogdp
            bsca_cal = sum(sca_dist) * dlogdp
            babs_cal = sum(abs_dist) * dlogdp

            Delta_array[ni][ki] = ((babs_mea - babs_cal) / 18.23) ** 2 + ((bsca_mea - bsca_cal) / 83.67) ** 2

    min_delta = Delta_array.argmin()
    next_n = nRange[(min_delta // spaceSize)]
    next_k = kRange[(min_delta % spaceSize)]

    # 將網格變小
    nMin_small = next_n - 0.02 if next_n > 1.33 else 1.33
    nMax_small = next_n + 0.02
    kMin_small = next_k - 0.04 if next_k > 0.04 else 0
    kMax_small = next_k + 0.04
    spaceSize_small = 41

    nRange_small = np.linspace(nMin_small, nMax_small, spaceSize_small)
    kRange_small = np.linspace(kMin_small, kMax_small, spaceSize_small)
    Delta_array_small = np.zeros((spaceSize_small, spaceSize_small))
    # 所有數據與大網格一致所以使用上方便數即可
    for ki, k in enumerate(kRange_small):
        for ni, n in enumerate(nRange_small):
            m = n + (1j * k)
            ndp = np.array(_df[3:])
            ext_dist, sca_dist, abs_dist = Mie_PESD(m, 550, dp, ndp)

            bext_cal = sum(ext_dist) * dlogdp
            bsca_cal = sum(sca_dist) * dlogdp
            babs_cal = sum(abs_dist) * dlogdp

            Delta_array_small[ni][ki] = ((bext_mea - bext_cal) / 18.23) ** 2 + ((bsca_mea - bsca_cal) / 83.67) ** 2

    min_delta_small = Delta_array_small.argmin()
    _df['re_real'] = (nRange_small[(min_delta_small // spaceSize_small)])
    _df['re_imaginary'] = (kRange_small[(min_delta_small % spaceSize_small)])

    print(f'\t\tReal part:{_df['re_real']}\tIm part:{_df['re_imaginary']}', end='')
    return _df['re_real':]
