"""The Mie kernel paths that integrate with the trapezoid rule.

numpy 2.4 removed ``np.trapz``. The size-distribution kernels only reach the
integrator on ``SMPS=False`` and on the ``'total'`` normalisation of the
scattering functions, neither of which the existing tests exercised -- so the
suite stayed green while both raised AttributeError. Pin them.
"""
import numpy as np
import pytest

from AeroViz.dataProcess.Optical import mie_kernels as mk

M = 1.5 + 0.02j
DP = np.array([100.0, 200.0, 300.0, 500.0])
NDP = np.array([1e3, 5e2, 1e2, 1e1])


def test_mie_sd_continuous_path_integrates():
    out = mk.Mie_SD(M, 550, DP, NDP, SMPS=False)
    assert len(out) == 7 and all(np.isfinite(out))
    bext, bsca = out[0], out[1]
    assert bext > bsca > 0


def test_mie_sd_continuous_matches_manual_trapezoid():
    from scipy.integrate import trapezoid
    q = np.array([mk.AutoMieQ(M, 550, d, 1.0) for d in DP])
    asdn = np.pi * (DP / 2) ** 2 * NDP * 1e-6
    expected = trapezoid(q[:, 0] * asdn, DP)
    assert mk.Mie_SD(M, 550, DP, NDP, SMPS=False)[0] == pytest.approx(expected)


@pytest.mark.parametrize('normalization', ['t', 'total'])
def test_scattering_function_total_normalisation(normalization):
    theta, sl, sr, su = mk.ScatteringFunction(M, 550, 200, normalization=normalization)
    from scipy.integrate import trapezoid
    assert trapezoid(su, theta) == pytest.approx(1.0)


def test_sf_sd_total_normalisation():
    theta, sl, sr, su = mk.SF_SD(M, 550, DP, NDP, normalization='t')
    assert np.all(np.isfinite(su)) and su.max() > 0
