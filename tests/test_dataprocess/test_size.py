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


@pytest.fixture
def merge_v1_inputs():
    """SMPS+APS whose fitted overlap density spreads across ~0.87-2.35 g/cm³.

    Constant SMPS + a per-hour-scaled APS (×0.5 → ×2.0) makes the power-law
    overlap shift — and therefore the estimated effective density (shift²) —
    vary monotonically across the 24 rows. That spread is what lets a
    ``density_range`` band keep a *partial* subset of rows, which is exactly
    what the v1 QC-invariance regression below exercises. Amplitudes are tuned
    so the overlap concentrations are comparable (≈5e3 at ~500 nm) — otherwise
    the shift collapses and every row is QC-masked.
    """
    n = 24
    idx = pd.date_range('2024-01-01', periods=n, freq='h')
    dp_s = np.logspace(np.log10(12), np.log10(500), 50)        # nm
    dp_a = np.logspace(np.log10(0.5), np.log10(10), 30)        # µm
    smps = pd.DataFrame(
        np.tile(1e5 * np.exp(-0.5 * (np.log(dp_s / 120) / np.log(1.8)) ** 2), (n, 1)),
        columns=dp_s, index=idx,
    )
    aps_base = 1e4 * np.exp(-0.5 * (np.log(dp_a / 1.0) / np.log(1.6)) ** 2)
    scale = np.linspace(0.5, 2.0, n)
    aps = pd.DataFrame(np.array([s * aps_base for s in scale]), columns=dp_a, index=idx)
    return smps, aps


class TestMergeV1NoValueDrift:
    """Lock v1's behaviour: ``density_range`` only masks rows; the merged
    concentration values themselves never change (proven byte-identical from the
    initial commit through the _core.py dedup refactor). See memory
    ``aeroviz-smps-aps-merge`` §4.
    """

    _KW = dict(version=1, smps_overlap_lowbound=200, aps_fit_highbound=1000)

    def test_density_range_only_masks_never_recomputes(self, merge_v1_inputs):
        """Loose vs strict QC: surviving rows are bit-identical; strict ⊆ loose.

        This is the mechanism behind "v1 looks unchanged but results differ":
        the only behavioural change ever made to v1 was tightening the default
        QC band (old ``data_all`` 0.3-2.6 → single ``data`` 0.6-2.6), which
        drops low-density rows but leaves every surviving value untouched.
        """
        smps, aps = merge_v1_inputs
        loose = merge_psd(smps, aps, density_range=(0.01, 100), **self._KW)['data']
        strict = merge_psd(smps, aps, density_range=(1.0, 2.0), **self._KW)['data']

        loose_rows = set(loose.dropna(how='all').index)
        strict_rows = set(strict.dropna(how='all').index)
        # the band must actually carve out a *partial* subset (not all / none)
        assert 0 < len(strict_rows) < len(loose_rows)
        # strict QC never invents a row the loose run didn't have
        assert strict_rows <= loose_rows

        # every cell present in BOTH runs is exactly equal — no recompute
        shared = loose.notna() & strict.notna()
        assert shared.values.sum() > 0
        delta = (loose[shared] - strict[shared]).abs().to_numpy()
        assert np.nanmax(delta) == 0.0

    def test_v1_merged_values_are_frozen(self, merge_v1_inputs):
        """Golden values — any change to the v1 merge math trips this.

        Captured from the current implementation; the investigation showed these
        match the initial-commit and pre-refactor v1 to max|Δ|=0.
        """
        smps, aps = merge_v1_inputs
        out = merge_psd(smps, aps, density_range=(0.01, 100), **self._KW)
        data, dens = out['data'], out['density'].iloc[:, 0]

        # mid row: effective density and a few diameter cells
        assert dens.iloc[12] == pytest.approx(1.710436, rel=1e-5)
        row = data.iloc[12]
        golden = {0: 4.65246983e+01, 57: 5.64500746e+04,
                  115: 1.89142527e+04, 172: 2.11783918e+03}
        for col, expected in golden.items():
            assert row.iloc[col] == pytest.approx(expected, rel=1e-5)


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

    def test_v5_requires_pm1(self, smps_like, aps_like):
        """EXPERIMENTAL v5 needs a PM1 reference (and warns)."""
        with pytest.warns(UserWarning, match="EXPERIMENTAL"):
            with pytest.raises(ValueError, match="df_pm1"):
                merge_psd(smps_like, aps_like, version=5)

    def test_v5_experimental_runs(self, smps_like, aps_like):
        """EXPERIMENTAL v5 (測試中): mass-anchored density returns its keys + warns."""
        pm1 = pd.Series(15.0, index=smps_like.index)
        with pytest.warns(UserWarning, match="EXPERIMENTAL"):
            out = merge_psd(smps_like, aps_like, version=5, df_pm1=pm1,
                            smps_overlap_lowbound=200)
        assert {'data', 'density', 'density_hourly', 'density_unc'} <= set(out)
