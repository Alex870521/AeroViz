"""Smoke tests for the top-level :func:`AeroViz.optical.mie` API and
the lognormal shortcuts.

Light coverage only — the deeper numerical tests live in
``test_optical_mie_inverse.py`` (full round-trip) and the kernel-level
tests under ``AeroViz.dataProcess.Optical.mie_kernels``.
"""
import numpy as np
import pandas as pd
import pytest

from AeroViz.optical import mie, mie_lognormal, mie_multimodal


pytestmark = [pytest.mark.dataprocess, pytest.mark.optical]


@pytest.fixture
def psd_df():
    """Small lognormal-ish PSD (10 time rows × 30 size bins, dN/dlogDp)."""
    dp = np.logspace(np.log10(20), np.log10(1000), 30)
    n_times = 10
    rng = np.random.default_rng(42)
    # peak around 200nm
    centers = rng.uniform(150, 250, n_times)
    data = np.zeros((n_times, len(dp)))
    for i, c in enumerate(centers):
        data[i] = 1e4 * np.exp(-0.5 * (np.log(dp / c) / np.log(2.0)) ** 2)
    return pd.DataFrame(data, columns=dp,
                        index=pd.date_range('2024-01-01', periods=n_times, freq='h'))


def test_mie_returns_ext_sca_abs(psd_df):
    ri = pd.Series([complex(1.55, 0.02)] * len(psd_df), index=psd_df.index)
    out = mie(psd_df, ri, wavelength=550)
    assert {'ext', 'sca', 'abs'}.issubset(out.columns)
    # Ext = Sca + Abs by Mie definition
    np.testing.assert_allclose(
        out['ext'].values, (out['sca'] + out['abs']).values, rtol=1e-8
    )


def test_mie_nonabsorbing_has_zero_abs(psd_df):
    ri = pd.Series([complex(1.55, 0.0)] * len(psd_df), index=psd_df.index)
    out = mie(psd_df, ri, wavelength=550)
    # Pure-real RI → no absorption (to machine precision)
    assert (out['abs'].abs() < 1e-6).all()
    assert (out['sca'] > 0).all()


def test_mie_distribution_per_bin(psd_df):
    ri = pd.Series([complex(1.55, 0.02)] * len(psd_df), index=psd_df.index)
    out = mie(psd_df, ri, wavelength=550, distribution=True)
    # Three per-bin DataFrames, same shape as input
    for key in ('ext', 'sca', 'abs'):
        assert key in out
        assert out[key].shape == psd_df.shape


def test_mie_invalid_mixing_raises(psd_df):
    ri = pd.Series([complex(1.55, 0.02)] * len(psd_df), index=psd_df.index)
    with pytest.raises(ValueError, match="mixing"):
        mie(psd_df, ri, wavelength=550, mixing='bogus')


def test_mie_lognormal_returns_dict():
    out = mie_lognormal(complex(1.55, 0.02), wavelength=550,
                        geo_mean=200, geo_std=2.0, total_number=1e4)
    assert set(out) >= {'ext', 'sca', 'abs'}
    assert out['ext'] > 0
    np.testing.assert_allclose(out['ext'], out['sca'] + out['abs'], rtol=1e-8)


def test_mie_multimodal_additive():
    """Two-mode result ≈ sum of two single-mode results."""
    single1 = mie_lognormal(complex(1.55, 0.0), wavelength=550,
                            geo_mean=100, geo_std=1.6, total_number=1e4)
    single2 = mie_lognormal(complex(1.55, 0.0), wavelength=550,
                            geo_mean=500, geo_std=1.8, total_number=1e3)
    multi = mie_multimodal(
        complex(1.55, 0.0), wavelength=550,
        modes=[(100, 1.6, 1e4), (500, 1.8, 1e3)],
    )
    np.testing.assert_allclose(
        multi['ext'], single1['ext'] + single2['ext'], rtol=1e-2
    )
