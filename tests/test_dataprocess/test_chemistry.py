"""Smoke tests for AeroViz.chemistry top-level functions."""
import numpy as np
import pandas as pd
import pytest

from AeroViz.chemistry import (
    reconstruct_mass,
    partition_ratios,
    volume_ri,
    growth_factor,
    kappa,
)


pytestmark = pytest.mark.dataprocess


@pytest.fixture
def chem_input():
    """Minimal NH4-sufficient chemical-composition input."""
    n = 24
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            'NH4+': rng.uniform(0.5, 2.0, n),
            'SO42-': rng.uniform(1.0, 5.0, n),
            'NO3-': rng.uniform(1.0, 4.0, n),
            'Fe': rng.uniform(0.05, 0.2, n),
            'Na+': rng.uniform(0.1, 0.5, n),
            'OC': rng.uniform(1.0, 4.0, n),
            'EC': rng.uniform(0.3, 1.5, n),
        },
        index=pd.date_range('2024-01-01', periods=n, freq='h'),
    )


class TestReconstructMass:
    def test_returns_expected_keys(self, chem_input):
        out = reconstruct_mass(chem_input)
        for key in ('mass', 'volume', 'NH4_status', 'RI_550', 'RI_450'):
            assert key in out, f"missing key: {key}"

    def test_mass_columns(self, chem_input):
        out = reconstruct_mass(chem_input)
        for col in ('AS', 'AN', 'OM', 'Soil', 'SS', 'EC'):
            assert col in out['mass'].columns

    def test_mass_non_negative(self, chem_input):
        out = reconstruct_mass(chem_input)
        for col in ('AS', 'AN', 'OM', 'Soil', 'SS', 'EC'):
            assert (out['mass'][col].dropna() >= 0).all(), f"{col} has negatives"


class TestPartitionRatios:
    def test_so2_so4_pair(self):
        n = 12
        df = pd.DataFrame(
            {
                'temp': np.full(n, 20.0),
                'SO42-': np.linspace(1, 6, n),
                'SO2': np.linspace(5, 1, n),
            }
        )
        out = partition_ratios(df)
        assert 'SOR' in out.columns
        # SOR = SO42-_mol / (SO42-_mol + SO2_mol) ∈ [0, 1]
        assert ((out['SOR'].dropna() >= 0) & (out['SOR'].dropna() <= 1)).all()


class TestVolumeRiAndGRH:
    @pytest.fixture
    def vol_df(self):
        n = 6
        return pd.DataFrame(
            {
                'AS_volume': np.full(n, 1.0),
                'AN_volume': np.full(n, 0.5),
                'OM_volume': np.full(n, 2.0),
                'Soil_volume': np.full(n, 0.1),
                'SS_volume': np.full(n, 0.1),
                'EC_volume': np.full(n, 0.2),
                'total_dry': np.full(n, 3.9),
            }
        )

    def test_volume_ri_dry(self, vol_df):
        out = volume_ri(vol_df)
        assert {'n_dry', 'k_dry'}.issubset(out.columns)
        # Real part of any reasonable aerosol RI ∈ (1.3, 1.7)
        assert ((out['n_dry'] > 1.3) & (out['n_dry'] < 1.7)).all()

    def test_growth_factor_increases_with_water(self, vol_df):
        alwc_low = pd.DataFrame({'ALWC': np.full(len(vol_df), 0.5)},
                                index=vol_df.index)
        alwc_high = pd.DataFrame({'ALWC': np.full(len(vol_df), 5.0)},
                                 index=vol_df.index)
        g_low = growth_factor(vol_df, alwc_low)['gRH']
        g_high = growth_factor(vol_df, alwc_high)['gRH']
        assert (g_high > g_low).all()


class TestKappa:
    def test_runs_and_returns_kappa_chem(self):
        n = 6
        df = pd.DataFrame(
            {
                'gRH': np.full(n, 1.5),
                'AT': np.full(n, 25.0),
                'RH': np.full(n, 80.0),
            }
        )
        out = kappa(df, diameter=0.5)
        assert 'kappa_chem' in out.columns
        assert out['kappa_chem'].notna().all()
