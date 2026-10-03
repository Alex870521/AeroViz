"""A lognormal mode specified by volume or mass instead of number, and the
Hatch–Choate conversions behind it."""
import numpy as np
import pytest
from scipy.integrate import trapezoid

from AeroViz import hatch_choate, mie_lognormal, mie_multimodal
from AeroViz.dataProcess.Optical.mie import generate_lognormal_psd
from AeroViz.dataProcess.SizeDistr._lognormal import lognormal_number_from_volume, lognormal_total_volume

pytestmark = [pytest.mark.dataprocess, pytest.mark.optical]

WIDE = dict(dp_range=(1, 50000), n_bins=2000)      # wide enough that the tails carry nothing


def _volume_of(dp, ndp):
    """µm³/cm³ by integrating (π/6) d³ dN/dlogDp over log10 d."""
    return trapezoid(np.pi / 6 * (dp / 1000) ** 3 * ndp, np.log10(dp))


def _number_of(dp, ndp):
    return trapezoid(ndp, np.log10(dp))


def test_hatch_choate_round_trip_and_known_value():
    vmd = hatch_choate(100, 2.0)                                   # exp(3 ln²2) = 4.2097
    assert vmd == pytest.approx(100 * np.exp(3 * np.log(2.0) ** 2))
    assert hatch_choate(vmd, 2.0, from_='volume', to='number') == pytest.approx(100)
    assert hatch_choate(100, 2.0, to='surface') < vmd              # 2nd moment sits between
    assert hatch_choate(100, 1.0) == 100                           # monodisperse: all medians coincide
    with pytest.raises(ValueError, match='weighting'):
        hatch_choate(100, 2.0, to='area')


def test_total_volume_formula_matches_numerical_integral():
    dp, ndp = generate_lognormal_psd(150, 1.8, total_number=5e3, **WIDE)
    assert _volume_of(dp, ndp) == pytest.approx(lognormal_total_volume(5e3, 150, 1.8), rel=1e-6)
    assert lognormal_number_from_volume(lognormal_total_volume(5e3, 150, 1.8), 150, 1.8) == pytest.approx(5e3)


def test_mode_by_volume_holds_that_volume():
    dp, ndp = generate_lognormal_psd(200, 2.0, total_volume=12.5, **WIDE)
    assert _volume_of(dp, ndp) == pytest.approx(12.5, rel=1e-6)


def test_mode_by_mass_is_volume_times_density():
    # 30 µg/m³ at 1.85 g/cm³ → 16.216 µm³/cm³ (µg/m³ ÷ g/cm³ is µm³/cm³ numerically)
    dp, ndp = generate_lognormal_psd(150, 1.6, total_mass=30, density=1.85, **WIDE)
    assert _volume_of(dp, ndp) == pytest.approx(30 / 1.85, rel=1e-6)


def test_volume_mode_median_is_converted_to_the_number_mode():
    # geo_mean given as VMD: the number mode must peak at VMD·exp(−3 ln²σ)
    dp, ndp = generate_lognormal_psd(421.0, 2.0, total_number=1e3, mode='volume', **WIDE)
    assert dp[np.argmax(ndp)] == pytest.approx(100, rel=0.02)
    assert _number_of(dp, ndp) == pytest.approx(1e3, rel=1e-6)


def test_number_mode_integrates_to_total_number():
    """Regression: the builder wrote dN/dlnDp but everything integrates over
    log10 Dp, so a 1e6 mode held 4.3e5 particles."""
    dp, ndp = generate_lognormal_psd(200, 2.0, total_number=1e6, **WIDE)
    assert _number_of(dp, ndp) == pytest.approx(1e6, rel=1e-6)


def test_default_amount_is_unchanged():
    dp, a = generate_lognormal_psd(200, 2.0)
    _, b = generate_lognormal_psd(200, 2.0, total_number=1e6)
    np.testing.assert_allclose(a, b)


@pytest.mark.parametrize('bad', [dict(total_number=1, total_volume=1),
                                 dict(total_mass=1),                       # no density
                                 dict(mode='area')])
def test_conflicting_or_incomplete_amounts_raise(bad):
    with pytest.raises(ValueError):
        generate_lognormal_psd(200, 2.0, **bad)


def test_mie_lognormal_by_mass_equals_by_converted_number():
    n = lognormal_number_from_volume(10 / 1.8, 150, 1.6)
    by_mass = mie_lognormal(1.95 + 0.79j, 880, geo_mean=150, geo_std=1.6, total_mass=10, density=1.8)
    by_number = mie_lognormal(1.95 + 0.79j, 880, geo_mean=150, geo_std=1.6, total_number=n)
    for k in ('ext', 'sca', 'abs'):
        assert by_mass[k] == pytest.approx(by_number[k], rel=1e-9)
    # Mie spheres give BC a MAC of roughly 3–5 m²/g at 880 nm (below the
    # 7.77 the AE33 assumes — the known compact-sphere underestimate), so
    # 10 µg/m³ absorbs a few tens of Mm⁻¹.
    assert 20 < by_mass['abs'] < 80


def test_mie_multimodal_by_mass_is_additive_and_matches_single_modes():
    modes = [(80, 1.5, 5.0), (300, 1.8, 20.0)]
    both = mie_multimodal(1.55 + 0.01j, 550, modes=modes, amount='mass', density=1.5)
    parts = [mie_lognormal(1.55 + 0.01j, 550, geo_mean=g, geo_std=s, total_mass=m_, density=1.5)
             for g, s, m_ in modes]
    for k in ('ext', 'sca', 'abs'):
        assert both[k] == pytest.approx(sum(p[k] for p in parts), rel=1e-9)
    with pytest.raises(ValueError, match='amount'):
        mie_multimodal(1.55 + 0.01j, 550, modes=modes, amount='count')
