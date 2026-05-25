"""Smoke tests for the IMPROVE extinction reconstruction."""
import numpy as np
import pandas as pd
import pytest

from AeroViz.optical import improve, gas_extinction


pytestmark = [pytest.mark.dataprocess, pytest.mark.optical]


@pytest.fixture
def mass_df():
    n = 12
    return pd.DataFrame(
        {
            'AS': np.full(n, 2.0),
            'AN': np.full(n, 1.5),
            'OM': np.full(n, 3.0),
            'Soil': np.full(n, 0.5),
            'SS': np.full(n, 0.3),
            'EC': np.full(n, 0.5),
        },
        index=pd.date_range('2024-01-01', periods=n, freq='h'),
    )


def test_revised_returns_dry_total(mass_df):
    out = improve(mass_df, method='revised')
    assert 'dry' in out
    assert 'total' in out['dry'].columns
    assert (out['dry']['total'] > 0).all()


def test_modified_returns_dry_total(mass_df):
    out = improve(mass_df, method='modified')
    assert 'dry' in out
    assert (out['dry']['total'] > 0).all()


def test_wet_extinction_exceeds_dry(mass_df):
    # The underlying revised()/modified() routines expect an RH Series
    # (used directly as a fRH-table index).
    rh = pd.Series(np.full(len(mass_df), 80.0), index=mass_df.index, name='RH')
    out = improve(mass_df, df_RH=rh, method='revised')
    assert 'wet' in out and 'fRH' in out
    # Hygroscopic growth at 80% RH should boost extinction
    assert (out['wet']['total'] >= out['dry']['total']).all()
    assert (out['fRH'].dropna() >= 1.0).all()


def test_df_RH_accepts_single_column_dataframe(mass_df):
    """A 1-column RH DataFrame is accepted and matches the Series result."""
    rh_series = pd.Series(np.full(len(mass_df), 80.0), index=mass_df.index, name='RH')
    rh_frame = rh_series.to_frame()

    out_series = improve(mass_df, df_RH=rh_series, method='revised')
    out_frame = improve(mass_df, df_RH=rh_frame, method='revised')

    np.testing.assert_allclose(
        out_frame['wet']['total'].to_numpy(),
        out_series['wet']['total'].to_numpy(),
    )


def test_df_RH_multicolumn_raises(mass_df):
    """A multi-column RH DataFrame fails with a clear message (not an opaque index error)."""
    bad_rh = pd.DataFrame(
        {'RH': np.full(len(mass_df), 80.0), 'RH2': np.full(len(mass_df), 70.0)},
        index=mass_df.index,
    )
    with pytest.raises(ValueError, match="single RH column"):
        improve(mass_df, df_RH=bad_rh, method='revised')


def test_invalid_method_raises(mass_df):
    with pytest.raises(ValueError, match="method must be"):
        improve(mass_df, method='bogus')


def test_localized_requires_df_ext(mass_df):
    df_mass = mass_df.assign(POC=mass_df['OM'] * 0.6, SOC=mass_df['OM'] * 0.4)
    with pytest.raises(ValueError, match="requires df_ext"):
        improve(df_mass, method='localized')


def test_gas_extinction_columns():
    n = 6
    no2 = pd.DataFrame({'NO2': np.full(n, 5.0)})
    temp = pd.DataFrame({'temp': np.full(n, 20.0)})
    out = gas_extinction(no2, temp)
    for col in ('ScatteringByGas', 'AbsorptionByGas', 'ExtinctionByGas'):
        assert col in out.columns
    assert (out['ExtinctionByGas'] > 0).all()
