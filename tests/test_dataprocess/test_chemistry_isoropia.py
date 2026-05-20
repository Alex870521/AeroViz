"""Tests for the cross-platform ISORROPIA II native extension.

Validates that ``AeroViz.isoropia()`` produces physically reasonable
output (pH ranges, partitioning behaviour) using the f2py-bound
ISORROPIA II Fortran solver. Numerical reference values come from the
standalone Fortran demo runs verified against the legacy isrpia2.exe.
"""
import numpy as np
import pandas as pd
import pytest

from AeroViz import isoropia


pytestmark = pytest.mark.dataprocess


@pytest.fixture
def typical_urban_chem():
    """Three rows spanning low / medium / high NH3 — exercises the
    sulfate-rich → ammonia-rich transition the model handles."""
    return pd.DataFrame({
        'NH4+':  [0.0, 0.0, 0.0],   # all NH3 entered as gas via NH3 column
        'NH3':   [1.0, 3.5, 9.0],   # ug/m^3 — varying ammonia
        'HNO3':  [3.0, 3.0, 3.0],   # ug/m^3
        'NO3-':  [0.0, 0.0, 0.0],
        'HCl':   [0.2, 0.2, 0.2],
        'Cl-':   [0.0, 0.0, 0.0],
        'Na+':   [0.1, 0.1, 0.1],
        'SO42-': [5.0, 5.0, 5.0],   # ug/m^3
        'Ca2+':  [0.04, 0.04, 0.04],
        'K+':    [0.04, 0.04, 0.04],
        'Mg2+':  [0.01, 0.01, 0.01],
        'RH':    [80.0, 80.0, 80.0],
        'temp':  [25.0, 25.0, 25.0],
    }, index=pd.date_range('2024-01-01', periods=3, freq='h'))


class TestIsoropiaBasics:
    """End-to-end smoke tests for isoropia() on any platform."""

    def test_runs_cross_platform(self, typical_urban_chem):
        """Just running isoropia() shouldn't raise on macOS/Linux/Win."""
        result = isoropia(typical_urban_chem)
        assert isinstance(result, dict)
        assert {'input', 'output'} <= set(result)

    def test_output_columns_present(self, typical_urban_chem):
        out = isoropia(typical_urban_chem)['output']
        for col in ('pH', 'ALWC', 'NH3', 'HNO3', 'HCl',
                    'NH4+', 'NO3-', 'Cl-'):
            assert col in out.columns, f"missing column: {col}"

    def test_no_path_out_required(self, typical_urban_chem):
        """The native extension has no temp-file I/O, so path_out is now
        optional (kept for backward-compat)."""
        result_no_path = isoropia(typical_urban_chem)
        result_with_path = isoropia(typical_urban_chem, path_out=None)
        pd.testing.assert_frame_equal(
            result_no_path['output'], result_with_path['output']
        )

    def test_alwc_non_negative(self, typical_urban_chem):
        out = isoropia(typical_urban_chem)['output']
        assert (out['ALWC'].dropna() >= 0).all()


class TestIsoropiaChemistry:
    """Physically meaningful behaviour: more NH3 → higher pH, more nitrate
    in particle phase, etc."""

    def test_ph_increases_with_nh3(self, typical_urban_chem):
        ph = isoropia(typical_urban_chem)['output']['pH']
        valid = ph.dropna()
        assert len(valid) == 3, "all three rows should be in 20<=RH<=95"
        # Sulfate-rich → ammonia-rich progression must raise pH
        assert valid.iloc[0] < valid.iloc[1] < valid.iloc[2]

    def test_ph_in_atmospheric_range(self, typical_urban_chem):
        """Aerosol pH for these compositions should be roughly 0–4."""
        ph = isoropia(typical_urban_chem)['output']['pH'].dropna()
        assert (ph >= -1).all() and (ph <= 5).all(), \
            f"pH out of typical atmospheric range: {list(ph)}"

    def test_nitrate_partitioning_with_nh3(self, typical_urban_chem):
        """As NH3 rises, more nitrate moves into the particle phase
        (NO3- aerosol up, HNO3 gas down)."""
        out = isoropia(typical_urban_chem)['output']
        no3_aer = out['NO3-'].dropna()
        hno3_gas = out['HNO3'].dropna()
        # Monotonic shift: NO3- aerosol rises, HNO3 gas falls
        assert no3_aer.iloc[0] < no3_aer.iloc[2]
        assert hno3_gas.iloc[0] > hno3_gas.iloc[2]


class TestIsoropiaInputHandling:
    """Edge cases: NaN rows, RH outside the pH-defined window."""

    def test_nan_rows_dropped(self):
        """A NaN in a non-fillna column (RH / temp / SO4 / gas species)
        marks that row as invalid and produces NaN output."""
        df = pd.DataFrame({
            'NH4+':  [0.0, 0.0, 0.0],
            'NH3':   [3.5, np.nan, 3.5],   # gas phase NaN — not fillna'd
            'HNO3':  [3.0, 3.0, 3.0],
            'NO3-':  [0.0, 0.0, 0.0],
            'HCl':   [0.2, 0.2, 0.2],
            'Cl-':   [0.0, 0.0, 0.0],
            'Na+':   [0.1, 0.1, 0.1],
            'SO42-': [5.0, 5.0, 5.0],
            'Ca2+':  [0.04, 0.04, 0.04],
            'K+':    [0.04, 0.04, 0.04],
            'Mg2+':  [0.01, 0.01, 0.01],
            'RH':    [80.0, 80.0, 80.0],
            'temp':  [25.0, 25.0, 25.0],
        })
        out = isoropia(df)['output']
        # Middle row has NaN gas-phase input → no output for that row
        assert np.isnan(out['pH'].iloc[1])
        assert not np.isnan(out['pH'].iloc[0])
        assert not np.isnan(out['pH'].iloc[2])

    def test_nh4_nan_filled_as_zero(self):
        """Aerosol NH4+ is fillna'd to 0 (matches legacy convention):
        if only gas-phase NH3 is measured, we still get a valid result."""
        df = pd.DataFrame({
            'NH4+':  [np.nan],   # no aerosol NH4+ measurement
            'NH3':   [3.5],
            'HNO3':  [3.0],
            'NO3-':  [0.0],      # aerosol NO3-/Cl- still required
            'HCl':   [0.2],
            'Cl-':   [0.0],
            'Na+':   [0.1],
            'SO42-': [5.0],
            'Ca2+':  [0.04],
            'K+':    [0.04],
            'Mg2+':  [0.01],
            'RH':    [80.0],
            'temp':  [25.0],
        })
        out = isoropia(df)['output']
        assert not np.isnan(out['pH'].iloc[0])
        assert out['ALWC'].iloc[0] > 0

    def test_ph_masked_outside_rh_window(self):
        """pH is only defined for 20% ≤ RH ≤ 95% (the function clips)."""
        df = pd.DataFrame({
            'NH4+':  [0.0, 0.0],
            'NH3':   [3.5, 3.5],
            'HNO3':  [3.0, 3.0],
            'NO3-':  [0.0, 0.0],
            'HCl':   [0.2, 0.2],
            'Cl-':   [0.0, 0.0],
            'Na+':   [0.1, 0.1],
            'SO42-': [5.0, 5.0],
            'Ca2+':  [0.04, 0.04],
            'K+':    [0.04, 0.04],
            'Mg2+':  [0.01, 0.01],
            'RH':    [15.0, 80.0],   # first row out of window
            'temp':  [25.0, 25.0],
        })
        out = isoropia(df)['output']
        assert np.isnan(out['pH'].iloc[0])  # RH=15 → pH dropped
        assert not np.isnan(out['pH'].iloc[1])  # RH=80 → kept
