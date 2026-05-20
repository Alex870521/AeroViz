"""Unit tests for RI inversion (mie_inverse)."""
import numpy as np
import pytest

from AeroViz.optical import (
    mie_lognormal,
    iterative_inversion,
    iterative_inversion_sd,
    contour_intersection,
)


pytestmark = [pytest.mark.dataprocess, pytest.mark.optical]


LOGNORMAL = {'geo_mean': 200, 'geo_std': 2.0, 'total_number': 1e4}
WAVELENGTH = 550.0


@pytest.fixture(scope='module')
def synthetic_optics():
    """Forward-compute (Bext, Bsca, Babs) for a known RI."""
    n_true, k_true = 1.55, 0.02
    ref = mie_lognormal(complex(n_true, k_true), wavelength=WAVELENGTH,
                        **LOGNORMAL)
    return {'n': n_true, 'k': k_true,
            'ext': ref['ext'], 'sca': ref['sca'], 'abs': ref['abs']}


class TestIterativeInversion:
    def test_round_trip_recovers_ri(self, synthetic_optics):
        out = iterative_inversion(
            synthetic_optics['ext'],
            synthetic_optics['sca'],
            synthetic_optics['abs'],
            LOGNORMAL, wavelength=WAVELENGTH,
        )
        assert out['converged']
        assert abs(out['n'] - synthetic_optics['n']) < 1e-3
        assert abs(out['k'] - synthetic_optics['k']) < 1e-3

    def test_two_of_three_measurements_sufficient(self, synthetic_optics):
        """Only Bext + Babs (no Bsca) should still converge."""
        out = iterative_inversion(
            synthetic_optics['ext'], None, synthetic_optics['abs'],
            LOGNORMAL, wavelength=WAVELENGTH,
        )
        assert abs(out['n'] - synthetic_optics['n']) < 1e-2
        assert abs(out['k'] - synthetic_optics['k']) < 1e-2

    def test_one_measurement_raises(self):
        with pytest.raises(ValueError):
            iterative_inversion(100.0, None, None, LOGNORMAL,
                                wavelength=WAVELENGTH)

    def test_residuals_returned(self, synthetic_optics):
        out = iterative_inversion(
            synthetic_optics['ext'], synthetic_optics['sca'],
            synthetic_optics['abs'], LOGNORMAL, wavelength=WAVELENGTH,
        )
        assert 'residuals' in out
        # Residuals should be tiny for a perfect-data round trip
        for v in out['residuals'].values():
            assert abs(v) < 1e-4


class TestIterativeInversionSD:
    def test_recovers_ri_with_explicit_psd(self):
        # Build a lognormal PSD explicitly
        dp = np.logspace(np.log10(20), np.log10(2000), 80)
        n_true, k_true = 1.55, 0.02
        # dN/dlogDp lognormal
        ln_sigma = np.log(2.0)
        ndp = (1e4 / (np.sqrt(2 * np.pi) * ln_sigma) *
               np.exp(-0.5 * (np.log(dp / 200) / ln_sigma) ** 2))
        # Forward via lognormal shortcut (analytic on identical params)
        ref = mie_lognormal(complex(n_true, k_true), wavelength=WAVELENGTH,
                            **LOGNORMAL)
        out = iterative_inversion_sd(ref['ext'], ref['sca'], ref['abs'],
                                     dp, ndp, wavelength=WAVELENGTH)
        # PSD discretisation introduces a small bias relative to the analytic
        # lognormal; require recovery to within 5%.
        assert abs(out['n'] - n_true) < 0.05
        assert abs(out['k'] - k_true) < 0.05


class TestContourIntersection:
    def test_recovers_ri_from_synthetic(self, synthetic_optics):
        out = contour_intersection(
            synthetic_optics['ext'], synthetic_optics['sca'],
            synthetic_optics['abs'], LOGNORMAL, wavelength=WAVELENGTH,
            n_range=(1.4, 1.7), k_range=(0.0, 0.1), grid=31,
        )
        # contour method is grid-based — looser tolerance than least-squares
        assert abs(out['n'] - synthetic_optics['n']) < 0.05
        assert abs(out['k'] - synthetic_optics['k']) < 0.02
