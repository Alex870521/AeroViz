"""to_surface / to_volume / mode_statistics are vectorised; values must not move.

The per-row ``apply`` versions were the single biggest cost of a SMPS read
(~8 s of 13 s for a year of 6-minute scans). The replacements do the same
arithmetic per cell, so this pins them to the old formulas exactly, including
how rows with NaN are handled (left out of the maths, re-inserted as NaN).
"""
import numpy as np
import pandas as pd
import pytest

from AeroViz.dataProcess.SizeDistr._size_dist import SizeDist
from AeroViz.size import psd_stats


@pytest.fixture
def pnsd():
    rng = np.random.default_rng(1)
    dp = np.logspace(np.log10(11.8), np.log10(593.5), 110)
    n = 500
    idx = pd.date_range('2026-01-01', periods=n, freq='6min')
    gmd = rng.uniform(40, 120, n)[:, None]
    gsd = rng.uniform(1.6, 2.2, n)[:, None]
    tot = rng.uniform(2e3, 3e4, n)[:, None]
    df = pd.DataFrame(tot * np.exp(-0.5 * (np.log(dp / gmd) / np.log(gsd)) ** 2)
                      / (np.sqrt(2 * np.pi) * np.log(gsd)), index=idx, columns=dp)
    df.iloc[::25] = np.nan            # whole rows missing
    df.iloc[7, 3] = np.nan            # one cell missing → that row is dropped from the maths
    return df


def _old_apply(df, dp, factor):
    return df.dropna().apply(lambda col: factor * np.array(col), axis=1,
                             result_type='broadcast').reindex(df.index)


def test_surface_and_volume_match_the_row_wise_formula(pnsd):
    psd = SizeDist(pnsd, weighting='n')
    dp = psd._dp
    pd.testing.assert_frame_equal(psd.to_surface(), _old_apply(pnsd, dp, np.pi * dp ** 2))
    pd.testing.assert_frame_equal(psd.to_volume(), _old_apply(pnsd, dp, np.pi / 6 * dp ** 3))


def test_nan_handling_is_unchanged(pnsd):
    out = psd_stats(pnsd)
    all_nan = pnsd.isna().all(axis=1)
    some_nan = pnsd.isna().any(axis=1) & ~all_nan
    # Fully missing rows are NaN everywhere.
    assert out['surface'][all_nan].isna().all().all()
    assert out['other'].loc[all_nan].isna().all().all()
    # Pre-existing asymmetry, pinned so it does not move silently: a row with a
    # single NaN cell is dropped from the surface/volume products (dropna), but
    # its number statistics are still computed (pandas sums skip NaN).
    assert out['surface'][some_nan].isna().all().all()
    assert out['other'].loc[some_nan, 'total_num_all'].notna().all()
    assert out['other'].loc[some_nan, 'total_surf_all'].isna().all()
    assert out['other'].loc[~pnsd.isna().any(axis=1), 'total_num_all'].notna().all()


def test_statistics_frame_shape_and_columns(pnsd):
    stats = psd_stats(pnsd)['other']
    assert len(stats) == len(pnsd)
    for col in ('total_num_all', 'GMD_num_all', 'GSD_num_all', 'mode_num_all',
                'total_vol_Accumulation', 'mode_surf_Aitken'):
        assert col in stats.columns
    # mode columns hold diameters from the grid
    assert set(stats['mode_num_all'].dropna().unique()) <= set(pnsd.columns)


def test_geometric_mean_is_the_closed_form(pnsd):
    stats = psd_stats(pnsd)['other']
    row = pnsd.dropna().iloc[0]
    dp = row.index.to_numpy(float)
    dlogdp = np.gradient(np.log10(dp))
    dn = row.to_numpy() * dlogdp
    gmd = np.exp((dn * np.log(dp)).sum() / dn.sum())
    assert stats.loc[row.name, 'GMD_num_all'] == pytest.approx(gmd, rel=5e-2)
