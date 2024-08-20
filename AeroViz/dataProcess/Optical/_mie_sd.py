# -*- coding: utf-8 -*-
# http://pymiescatt.readthedocs.io/en/latest/forward.html
import numpy as np
from pandas import concat, DataFrame
from scipy.integrate import trapezoid
from scipy.special import jv, yv


def coerceDType(d):
    if type(d) is not np.ndarray:
        return np.array(d)
    else:
        return d


def Mie_ab(m, x, nmax, df_n):
    nu = df_n.copy() + 0.5
    n1 = 2 * df_n.copy() + 1

    sx = np.sqrt(0.5 * np.pi * x)
    px = sx.reshape(-1, 1) * jv(nu, x.reshape(-1, 1))
    chx = -sx.reshape(-1, 1) * yv(nu, x.reshape(-1, 1))

    p1x = concat([DataFrame(np.sin(x)), px.mask(df_n == nmax.reshape(-1, 1))], axis=1)
    p1x.columns = np.arange(len(p1x.keys()))
    p1x = p1x[df_n.keys()]

    ch1x = concat([DataFrame(np.cos(x)), chx.mask(df_n == nmax.reshape(-1, 1))], axis=1)
    ch1x.columns = np.arange(len(ch1x.keys()))
    ch1x = ch1x[df_n.keys()]

    gsx = px - (0 + 1j) * chx
    gs1x = p1x - (0 + 1j) * ch1x

    mx = m.reshape(-1, 1) * x
    nmx = np.round(np.max(np.hstack([[nmax] * m.size, np.abs(mx)]).reshape(m.size, 2, -1), axis=1) + 16)

    df_qext = DataFrame(columns=m, index=df_n.index)
    df_qsca = DataFrame(columns=m, index=df_n.index)

    df_n /= x.reshape(-1, 1)
    for _bin_idx, (_nmx_ary, _mx, _nmax) in enumerate(zip(nmx.T, mx.T, nmax)):

        df_D = DataFrame(np.nan, index=np.arange(m.size), columns=df_n.keys())

        Dn_lst = []
        for _nmx, _uni_idx in DataFrame(_nmx_ary).groupby(0).groups.items():

            _inv_mx = 1 / _mx[_uni_idx]

            Dn = np.zeros((_uni_idx.size, int(_nmx)), dtype=complex)
            for _idx in range(int(_nmx) - 1, 1, -1):
                Dn[:, _idx - 1] = (_idx * _inv_mx) - (1 / (Dn[:, _idx] + _idx * _inv_mx))

            Dn_lst.append(Dn[:, 1: int(_nmax) + 1])
            df_D.loc[_uni_idx, 0: int(_nmax) - 1] = Dn[:, 1: int(_nmax) + 1]

        ## other parameter
        _df_n, _px, _p1x, _gsx, _gs1x, _n1 = df_n.loc[_bin_idx], px.loc[_bin_idx], p1x.loc[_bin_idx], gsx.loc[_bin_idx], \
            gs1x.loc[_bin_idx], n1.loc[_bin_idx].values

        _da = df_D / m.reshape(-1, 1) + _df_n
        _db = df_D * m.reshape(-1, 1) + _df_n

        _an = (_da * _px - _p1x) / (_da * _gsx - _gs1x)
        _bn = (_db * _px - _p1x) / (_db * _gsx - _gs1x)

        _real_an, _real_bn = np.real(_an), np.real(_bn)
        _imag_an, _imag_bn = np.imag(_an), np.imag(_bn)

        _pr_qext = np.nansum(_n1 * (_real_an + _real_bn), axis=1)
        _pr_qsca = np.nansum(_n1 * (_real_an ** 2 + _real_bn ** 2 + _imag_an ** 2 + _imag_bn ** 2), axis=1)

        df_qext.loc[_bin_idx] = _pr_qext
        df_qsca.loc[_bin_idx] = _pr_qsca

    return df_qext, df_qsca


def MieQ(m_ary, wavelength, diameter):
    #  http://pymiescatt.readthedocs.io/en/latest/forward.html#MieQ

    x = np.pi * diameter / wavelength

    nmax = np.round(2 + x + 4 * (x ** (1 / 3)))

    df_n = DataFrame([np.arange(1, nmax.max() + 1)] * nmax.size)
    df_n = df_n.mask(df_n > nmax.reshape(-1, 1))

    n1 = 2 * df_n + 1
    n2 = df_n * (df_n + 2) / (df_n + 1)
    n3 = n1 / (df_n * (df_n + 1))
    x2 = x ** 2

    _qext, _qsca = Mie_ab(m_ary, x, nmax, df_n)

    qext = (2 / x2).reshape(-1, 1) * _qext
    qsca = (2 / x2).reshape(-1, 1) * _qsca

    # return qext.astype(float).values.T, qsca.astype(float).values.T,
    return qext.values.T.astype(float), qsca.values.T.astype(float)


def Mie_SD(m_ary, wavelength, psd, multp_m_in1psd=False, dt_chunk_size=10, q_table=False):
    m_ary = coerceDType(m_ary)
    if type(psd) is not DataFrame:
        psd = DataFrame(psd).T

    if (len(m_ary) != len(psd)) & ~multp_m_in1psd:
        raise ValueError('"m array" size should be same as "psd" size')

    dp = psd.keys().values
    ndp = psd.values
    aSDn = np.pi * ((dp / 2) ** 2) * ndp * 1e-6

    if q_table:
        qext, qsca = q_table
    else:
        qext, qsca = MieQ(m_ary, wavelength, dp)

    if multp_m_in1psd:
        # print('\tcalculate ext')

        aSDn_all = np.repeat(aSDn, m_ary.size, axis=0).reshape(len(aSDn), m_ary.size, -1)

        qext_all = np.repeat(qext[np.newaxis, :, :], len(aSDn), axis=0).reshape(*aSDn_all.shape)
        qsca_all = np.repeat(qsca[np.newaxis, :, :], len(aSDn), axis=0).reshape(*aSDn_all.shape)

        df_ext = DataFrame(trapezoid(aSDn_all * qext_all), columns=m_ary, index=psd.index).astype(float)
        df_sca = DataFrame(trapezoid(aSDn_all * qsca_all), columns=m_ary, index=psd.index).astype(float)
        df_abs = df_ext - df_sca
        # print('\tdone')

        return dict(ext=df_ext, sca=df_sca, abs=df_abs)

    else:
        df_out = DataFrame(index=psd.index)
        df_out['ext'] = trapezoid(qext * aSDn).astype(float)
        df_out['sca'] = trapezoid(qsca * aSDn).astype(float)
        df_out['abs'] = df_out['ext'] - df_out['sca']

        return df_out
