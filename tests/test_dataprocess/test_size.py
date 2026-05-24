"""Smoke tests for the AeroViz.size top-level functions."""
import numpy as np
import pandas as pd
import pytest

from AeroViz.size import psd_stats, psd_distributions, merge_psd


pytestmark = pytest.mark.dataprocess


@pytest.fixture
def aps_like():
    """Simulated APS-like dN/dlogDp, 24 hours × 30 bins (0.5-10 µm)."""
    dp = np.logspace(np.log10(0.5), np.log10(10), 30)  # µm
    n_times = 24
    base = 50 * np.exp(-0.5 * (np.log(dp / 2.0) / np.log(1.6)) ** 2)
    return pd.DataFrame(
        np.tile(base, (n_times, 1)), columns=dp,
        index=pd.date_range('2024-01-01', periods=n_times, freq='h'),
    )


@pytest.fixture
def smps_like():
    """Simulated SMPS-like dN/dlogDp, 24 hours × 50 bins (12-500 nm)."""
    dp = np.logspace(np.log10(12), np.log10(500), 50)
    n_times = 24
    # Lognormal peak ~120 nm
    base = 1e5 * np.exp(-0.5 * (np.log(dp / 120) / np.log(1.8)) ** 2)
    return pd.DataFrame(
        np.tile(base, (n_times, 1)), columns=dp,
        index=pd.date_range('2024-01-01', periods=n_times, freq='h'),
    )


class TestPsdStats:
    def test_returns_weighting_keys(self, smps_like):
        out = psd_stats(smps_like, bin_range=(12, 500))
        assert {'number', 'surface', 'volume', 'other'}.issubset(out)

    def test_other_has_properties(self, smps_like):
        out = psd_stats(smps_like, bin_range=(12, 500))
        # 'other' wraps statistics — should be a DataFrame
        assert isinstance(out['other'], pd.DataFrame)


class TestPsdDistributions:
    def test_three_distributions(self, smps_like):
        out = psd_distributions(smps_like)
        for key in ('number', 'surface', 'volume', 'properties'):
            assert key in out
        # Surface/volume must be larger-diameter-weighted versions of number
        n_tot = out['number'].sum(axis=1).mean()
        v_tot = out['volume'].sum(axis=1).mean()
        assert v_tot > 0 and n_tot > 0


class TestMergePsd:
    def test_v4_requires_pm25(self, smps_like):
        with pytest.raises(ValueError, match="df_pm25"):
            merge_psd(smps_like, smps_like, version=4)

    def test_invalid_version(self, smps_like):
        with pytest.raises(ValueError, match="version must be one of"):
            merge_psd(smps_like, smps_like, version=99)

    def test_v1_unified_keys(self, smps_like, aps_like):
        """v1 returns the unified 'data' + 'density' keys (old all/qc removed)."""
        out = merge_psd(smps_like, aps_like, version=1,
                        smps_overlap_lowbound=200, aps_fit_highbound=1000)
        assert isinstance(out, dict)
        assert {'data', 'density'} <= set(out)
        # hard break: the old v1 keys are gone
        assert 'data_all' not in out and 'data_qc' not in out

    def test_density_range_accepted(self, smps_like, aps_like):
        """density_range is accepted (loose & strict) and keeps the contract."""
        for dr in [(0.3, 2.6), (0.6, 2.6)]:
            out = merge_psd(smps_like, aps_like, version=1,
                            smps_overlap_lowbound=200, density_range=dr)
            assert {'data', 'density'} <= set(out)
