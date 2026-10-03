"""Cross-check the Mie kernel against an independent Bohren & Huffman (1983)
implementation built on SciPy's half-integer Bessel functions.

AeroViz's `calculate_mie_coefficients` is the PyMieScatt lineage (downward
recurrence for the logarithmic derivative). The oracle below is the Mätzler
(2002) MATLAB formulation — an and bn straight from spherical Bessel
functions — ported from the author's 2022 Mie code. Two formulations agreeing
to 1e-6 over the sizes an SMPS/APS covers is what lets the rest of the optical
module be trusted.
"""
import numpy as np
import pytest
import scipy.special as sp

from AeroViz.dataProcess.Optical.mie import calculate_mie_efficiencies

pytestmark = [pytest.mark.dataprocess, pytest.mark.optical]


def _bh_mie_abcd(m, x):
    nmax = int(np.round(2 + x + 4 * x ** (1 / 3)))
    n = np.arange(1, nmax + 1)
    nu = n + 0.5
    z = m * x
    m2 = m * m
    sqx, sqz = np.sqrt(0.5 * np.pi / x), np.sqrt(0.5 * np.pi / z)
    bx, bz, yx = sp.jv(nu, x) * sqx, sp.jv(nu, z) * sqz, sp.yv(nu, x) * sqx
    hx = bx + 1j * yx
    b1x = np.concatenate(([np.sin(x) / x], bx[:nmax - 1]))
    b1z = np.concatenate(([np.sin(z) / z], bz[:nmax - 1]))
    y1x = np.concatenate(([-np.cos(x) / x], yx[:nmax - 1]))
    h1x = b1x + 1j * y1x
    ax, az, ahx = x * b1x - n * bx, z * b1z - n * bz, x * h1x - n * hx
    an = (m2 * bz * ax - bx * az) / (m2 * bz * ahx - hx * az)
    bn = (bz * ax - bx * az) / (bz * ahx - hx * az)
    return n, an, bn


def bh_efficiencies(m, x):
    """(Q_ext, Q_sca) from Bohren & Huffman eqs 4.61–4.62."""
    n, an, bn = _bh_mie_abcd(m, x)
    cn = 2 * n + 1
    q_ext = 2 / x ** 2 * np.sum(cn * (an.real + bn.real))
    q_sca = 2 / x ** 2 * np.sum(cn * (np.abs(an) ** 2 + np.abs(bn) ** 2))
    return q_ext, q_sca


@pytest.mark.parametrize('m', [1.33 + 0j, 1.55 + 0.01j, 1.8 + 0.1j, 1.95 + 0.79j])
@pytest.mark.parametrize('dp_nm', [20, 100, 300, 1000, 3000, 10000])
def test_kernel_matches_bohren_huffman(m, dp_nm):
    wavelength = 550.0
    x = np.pi * dp_nm / wavelength
    q_ext_ref, q_sca_ref = bh_efficiencies(m, x)
    eff = calculate_mie_efficiencies(np.array([m]), wavelength, np.array([float(dp_nm)]))
    # 1e-6: at x ≈ 57 the two recurrences differ in the last digits of a
    # 100-term sum; anything looser than 1e-4 would hide a real formula error.
    assert eff['Q_ext'][0, 0] == pytest.approx(q_ext_ref, rel=1e-6, abs=1e-12)
    assert eff['Q_sca'][0, 0] == pytest.approx(q_sca_ref, rel=1e-6, abs=1e-12)


def test_oracle_itself_is_sane():
    # Large non-absorbing sphere: Q_ext → 2 (extinction paradox), Q_abs = 0.
    q_ext, q_sca = bh_efficiencies(1.33 + 0j, 500.0)
    assert q_ext == pytest.approx(2.0, abs=0.05)
    assert q_ext == pytest.approx(q_sca, rel=1e-9)
