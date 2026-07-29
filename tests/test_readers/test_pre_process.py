"""
Tests for the Ångström calculations in ``rawDataReader.core.pre_process``.

These are pure-function tests: synthetic data is built to follow the power law
X(λ) = X(λ_ref)·(λ/λ_ref)^(-AE) exactly, so both the fitted exponent and the
extrapolated coefficient have a known closed-form answer.
"""
import numpy as np
import pandas as pd
import pytest

from AeroViz.rawDataReader.core.pre_process import _absCoe, _scaCoe

# (instrument, wavelengths, mass absorption efficiencies) — mirrors the reader config
ABS_INSTRUMENTS = [
    ('AE33', [370, 470, 520, 590, 660, 880, 950],
     [18.47, 14.54, 13.14, 11.58, 10.35, 7.77, 7.19]),
    ('BC1054', [370, 430, 470, 525, 565, 590, 660, 700, 880, 950],
     [18.48, 15.90, 14.55, 13.02, 12.10, 11.59, 10.36, 9.77, 7.77, 7.20]),
    ('MA350', [375, 470, 528, 625, 880],
     [24.069, 19.070, 17.028, 14.091, 10.120]),
]

SCA_INSTRUMENTS = [
    ('NEPH', [450, 550, 700]),
    ('Aurora', [450, 525, 635]),
]

INDEX = pd.date_range('2024-01-01', periods=3, freq='h')


def _power_law(band, ae, ref_wl=550, ref_value=10.0):
    """Values following X(λ) = ref_value·(λ/ref_wl)^(-AE)."""
    return ref_value * (np.asarray(band, dtype=float) / ref_wl) ** (-ae)


def _bc_frame(band, mae, ae):
    """BC concentrations that reproduce a known absorption power law."""
    bc = _power_law(band, ae) / (np.asarray(mae) * 1e-3)
    return pd.DataFrame([bc] * len(INDEX),
                        columns=[f'BC{i + 1}' for i in range(len(band))], index=INDEX)


def _bgr_frame(band, ae):
    return pd.DataFrame([_power_law(band, ae, ref_value=100.0)] * len(INDEX),
                        columns=['B', 'G', 'R'], index=INDEX)


@pytest.mark.parametrize('instru, band, mae', ABS_INSTRUMENTS)
@pytest.mark.parametrize('ae', [0.9, 1.3, 2.0])
def test_abs_aae_is_positive_and_exact(instru, band, mae, ae):
    """AAE follows the positive convention and recovers the true exponent."""
    out = _absCoe(_bc_frame(band, mae, ae), instru=instru, specified_band=[550])

    assert np.allclose(out['AAE'], ae)


@pytest.mark.parametrize('instru, band, mae', ABS_INSTRUMENTS)
@pytest.mark.parametrize('ae', [0.9, 1.3, 2.0])
def test_abs_extrapolation_follows_power_law(instru, band, mae, ae):
    """abs_550 is interpolated in the right direction (it used to be inverted)."""
    out = _absCoe(_bc_frame(band, mae, ae), instru=instru, specified_band=[550])

    # The synthetic data is anchored at 550 nm with a value of 10.0
    assert np.allclose(out['abs_550'], 10.0)

    # Absorption must decrease monotonically with wavelength for a positive AAE
    abs_cols = [f'abs_{wl}' for wl in band]
    assert np.all(np.diff(out[abs_cols].iloc[0].values) < 0)


@pytest.mark.parametrize('instru, band, mae', ABS_INSTRUMENTS)
def test_abs_measured_band_is_not_round_tripped(instru, band, mae):
    """A requested wavelength the instrument measures is taken directly."""
    out = _absCoe(_bc_frame(band, mae, 1.3), instru=instru, specified_band=[band[-1]])

    assert list(out.columns).count(f'abs_{band[-1]}') == 1
    assert np.allclose(out[f'abs_{band[-1]}'], _power_law([band[-1]], 1.3)[0])


@pytest.mark.parametrize('instru, band, mae', ABS_INSTRUMENTS)
def test_abs_repeated_specified_band(instru, band, mae):
    """Repeating a wavelength must not create duplicate columns."""
    out = _absCoe(_bc_frame(band, mae, 1.3), instru=instru, specified_band=[550, 550])

    assert list(out.columns).count('abs_550') == 1


def test_abs_rejects_wrong_column_count():
    band, mae = ABS_INSTRUMENTS[0][1], ABS_INSTRUMENTS[0][2]
    df = _bc_frame(band, mae, 1.3)

    with pytest.raises(ValueError, match='expects 7 BC columns'):
        _absCoe(df[['BC1', 'BC2']], instru='AE33', specified_band=[550])


def test_abs_rejects_unknown_instrument():
    band, mae = ABS_INSTRUMENTS[0][1], ABS_INSTRUMENTS[0][2]

    with pytest.raises(KeyError, match='Unknown aethalometer'):
        _absCoe(_bc_frame(band, mae, 1.3), instru='AE31', specified_band=[550])


def test_abs_all_nan_input_returns_nan_columns():
    band, mae = ABS_INSTRUMENTS[0][1], ABS_INSTRUMENTS[0][2]
    df = _bc_frame(band, mae, 1.3)
    df.loc[:, :] = np.nan

    out = _absCoe(df, instru='AE33', specified_band=[550])

    assert out['AAE'].isna().all()
    assert out['abs_550'].isna().all()


@pytest.mark.parametrize('instru, band', SCA_INSTRUMENTS)
@pytest.mark.parametrize('ae', [0.5, 1.5, 2.5])
def test_sca_sae_is_positive_and_exact(instru, band, ae):
    out = _scaCoe(_bgr_frame(band, ae), instru=instru, specified_band=[550])

    assert np.allclose(out['SAE'], ae)
    assert np.allclose(out['sca_550'], 100.0)


@pytest.mark.parametrize('name', ['NEPH', 'Neph', 'neph'])
def test_neph_band_dispatch_is_case_insensitive(name):
    """NEPH must use the TSI wavelengths whatever the spelling of its name."""
    df = _bgr_frame([450, 550, 700], 1.5)

    out = _scaCoe(df, instru=name, specified_band=[550])

    # 550 nm is measured directly by the TSI, so sca_550 is the G channel as-is
    assert np.allclose(out['sca_550'], df['G'])
    assert np.allclose(out['SAE'], 1.5)


def test_sca_extrapolation_follows_power_law():
    """sca at an unmeasured wavelength decreases with λ for a positive SAE."""
    band, ae = [450, 550, 700], 1.5
    out = _scaCoe(_bgr_frame(band, ae), instru='NEPH', specified_band=[600])

    assert np.allclose(out['sca_600'], _power_law([600], ae, ref_value=100.0)[0])
    assert (out['sca_600'] < out['G']).all()


def test_sca_rejects_unknown_instrument():
    with pytest.raises(KeyError, match='Unknown nephelometer'):
        _scaCoe(_bgr_frame([450, 550, 700], 1.5), instru='Aurora4000', specified_band=[550])


def test_sca_all_nan_input_returns_nan_columns():
    df = _bgr_frame([450, 550, 700], 1.5)
    df.loc[:, :] = np.nan

    out = _scaCoe(df, instru='NEPH', specified_band=[550])

    assert out['SAE'].isna().all()
    assert out['sca_550'].isna().all()
