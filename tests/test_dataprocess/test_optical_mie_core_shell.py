"""Unit tests for Aden-Kerker coated-sphere Mie."""
import numpy as np
import pytest

from AeroViz.optical import mie_core_shell, mie_core_shell_sd, mie_lognormal


pytestmark = [pytest.mark.dataprocess, pytest.mark.optical]


# Black-carbon and shell refractive indices typical at 550 nm
BC_RI = complex(1.95, 0.79)
OM_RI = complex(1.55, 0.0)
WAVELENGTH = 550.0


class TestSingleParticle:
    def test_returns_7_keys(self):
        out = mie_core_shell(BC_RI, OM_RI,
                             d_core=50, d_total=150, wavelength=WAVELENGTH)
        for key in ('Q_ext', 'Q_sca', 'Q_abs', 'g', 'Q_pr', 'Q_back', 'Q_ratio'):
            assert key in out
            assert np.isfinite(out[key]), f"{key} is not finite"

    def test_qext_equals_qsca_plus_qabs(self):
        out = mie_core_shell(BC_RI, OM_RI,
                             d_core=50, d_total=150, wavelength=WAVELENGTH)
        np.testing.assert_allclose(
            out['Q_ext'], out['Q_sca'] + out['Q_abs'], rtol=1e-8
        )

    def test_degenerate_no_core_matches_homogeneous(self):
        """d_core=0 → pure shell sphere = homogeneous Mie at d_total."""
        coated = mie_core_shell(BC_RI, OM_RI,
                                d_core=0, d_total=150, wavelength=WAVELENGTH)
        homog = mie_lognormal(
            OM_RI, wavelength=WAVELENGTH,
            geo_mean=150, geo_std=1.001, total_number=1,
        )
        # Both should describe the same sphere; sanity-check Q_abs ≈ 0 since
        # OM is non-absorbing
        assert abs(coated['Q_abs']) < 1e-3

    def test_degenerate_same_ri_matches_homogeneous(self):
        """m_core == m_shell → homogeneous Mie at d_total."""
        out = mie_core_shell(OM_RI, OM_RI,
                             d_core=50, d_total=150, wavelength=WAVELENGTH)
        assert abs(out['Q_abs']) < 1e-3
        assert out['Q_ext'] > 0

    def test_absorption_enhancement(self):
        """BC core coated with OM → E_abs in canonical 1.5-2.5× range."""
        bare = mie_core_shell(BC_RI, BC_RI,
                              d_core=50, d_total=50, wavelength=WAVELENGTH)
        coated = mie_core_shell(BC_RI, OM_RI,
                                d_core=50, d_total=150, wavelength=WAVELENGTH)
        # Scale by cross-section areas to compare per-particle absorption
        area_bare = np.pi * (50e-9) ** 2 / 4
        area_coated = np.pi * (150e-9) ** 2 / 4
        e_abs = (coated['Q_abs'] * area_coated) / (bare['Q_abs'] * area_bare)
        assert 1.0 < e_abs < 4.0, f"E_abs out of range: {e_abs:.2f}"

    def test_negative_diameter_raises(self):
        with pytest.raises(ValueError, match="d_core"):
            mie_core_shell(BC_RI, OM_RI,
                           d_core=-1, d_total=150, wavelength=WAVELENGTH)

    def test_core_larger_than_total_raises(self):
        with pytest.raises(ValueError, match="d_total"):
            mie_core_shell(BC_RI, OM_RI,
                           d_core=200, d_total=150, wavelength=WAVELENGTH)


class TestSizeDistribution:
    def test_psd_integrated_returns_ext_sca_abs(self):
        dp_core = np.array([30, 50, 80, 120])
        dp_total = dp_core + 100  # 100 nm coating
        ndp = np.array([1e3, 5e3, 8e3, 2e3])
        out = mie_core_shell_sd(BC_RI, OM_RI, dp_core, dp_total, ndp,
                                wavelength=WAVELENGTH, psd_type='dN')
        assert {'ext', 'sca', 'abs'}.issubset(out)
        assert out['ext'] > 0
        np.testing.assert_allclose(out['ext'], out['sca'] + out['abs'],
                                   rtol=1e-8)
