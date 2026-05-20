"""Unit tests for AeroViz.dataProcess.Optical.mie_angular."""
import numpy as np
import pytest

from AeroViz.optical import (
    scattering_function,
    scattering_function_sd,
    phase_matrix,
    nephelometer_truncation_correction,
)


pytestmark = [pytest.mark.dataprocess, pytest.mark.optical]


class TestScatteringFunction:
    def test_default_returns_361_points(self):
        out = scattering_function(complex(1.5, 0.02), 550.0, 200.0)
        assert set(out) >= {'angles', 'SL', 'SR', 'SU'}
        assert out['SL'].shape == (361,)

    def test_SU_is_mean_of_SL_SR(self):
        out = scattering_function(complex(1.5, 0.02), 550.0, 200.0)
        np.testing.assert_allclose(out['SU'], 0.5 * (out['SL'] + out['SR']),
                                   rtol=1e-10)

    def test_forward_peak_larger_than_backward(self):
        out = scattering_function(complex(1.5, 0.0), 550.0, 500.0)
        # For a moderately large sphere, forward scattering (small theta)
        # should significantly exceed backward (theta ~ pi)
        forward = out['SU'][:10].mean()
        backward = out['SU'][-10:].mean()
        assert forward > backward


class TestScatteringFunctionSD:
    def test_returns_same_keys_as_single_particle(self):
        dp = np.linspace(50, 500, 30)
        ndp = np.exp(-0.5 * (np.log(dp / 200) / np.log(2.0)) ** 2) * 1e4
        out = scattering_function_sd(complex(1.5, 0.02), 550, dp, ndp)
        assert set(out) >= {'angles', 'SL', 'SR', 'SU'}
        # Should have non-zero scattering
        assert out['SU'].max() > 0


class TestPhaseMatrix:
    def test_returns_four_elements(self):
        out = phase_matrix(complex(1.5, 0.0), 550, 200)
        for key in ('mu', 'S11', 'S12', 'S33', 'S34'):
            assert key in out

    def test_S11_non_negative(self):
        out = phase_matrix(complex(1.5, 0.0), 550, 200)
        # S11 = intensity element of Mueller matrix → must be non-negative
        assert (out['S11'] >= 0).all()


class TestNephelometerTruncation:
    def test_scalar_input_returns_float(self):
        f = nephelometer_truncation_correction(2.0)
        assert isinstance(f, float)
        # Anderson-Ogren (550 nm, TSI 3563): 1.315 + 0.0429·SAE
        assert abs(f - (1.315 + 0.0429 * 2.0)) < 1e-3

    def test_array_input_returns_array(self):
        sae = np.array([0.5, 1.0, 2.0, 3.0])
        out = nephelometer_truncation_correction(sae, wavelength=450)
        assert out.shape == sae.shape
        # Monotonic increase in SAE → monotonic increase in correction
        assert np.all(np.diff(out) > 0)

    def test_unknown_instrument_raises(self):
        with pytest.raises(ValueError, match="Unknown instrument"):
            nephelometer_truncation_correction(1.0, instrument='nope')

    def test_unsupported_wavelength_raises(self):
        with pytest.raises(ValueError, match="No truncation coefficients"):
            nephelometer_truncation_correction(1.0, wavelength=1234)

    def test_aurora_alias(self):
        # 'AURORA' and 'AURORA3000' should resolve to the same coefficients
        a = nephelometer_truncation_correction(1.5, wavelength=525,
                                               instrument='Aurora')
        b = nephelometer_truncation_correction(1.5, wavelength=525,
                                               instrument='Aurora3000')
        assert a == b
