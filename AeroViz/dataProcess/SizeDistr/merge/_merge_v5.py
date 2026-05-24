"""v5 — mass-anchored SMPS-APS merge.  ⚠️ EXPERIMENTAL / 測試中 ⚠️

NOT production-ready: API, outputs and defaults may change without notice.

Rationale (why v5 differs from v1-v4)
-------------------------------------
v1-v4 derive the effective density from the SMPS-APS *overlap* (matching
dN/dlogDp magnitudes after a diameter shift). That problem is **degenerate**:
the shift absorbs both the true density AND any APS/SMPS counting difference,
so the recovered density is weakly constrained and biased low (typically lands
near ~1 g/cm³ even for ambient aerosol that is ~1.3-1.8). The dN/dS/dV
correlation objective used by v3/v4 is, additionally, numerically jagged.

v5 instead **anchors the density to an independent mass measurement** (PM1)
via mass closure, aggregated to a daily scale (effective density is a
slowly-varying property, so daily aggregation removes hour-to-hour noise):

    ρ_eff = PM1 / V(D ≤ 1 µm)        (iterated to self-consistency)

The diameter shift is then fixed by that density (shift = √ρ), and the
SMPS-APS overlap is used only for the *APS counting correction* (the two
previously-confounded unknowns are decoupled).

Caveat: the absolute density is only as good as the PM1 mass — TEOM volatile
loss (PM_Total vs PM_NV) is the dominant remaining uncertainty; prefer a
volatile-corrected (e.g. FDMS) PM1.
"""
import numpy as np
from pandas import Series, DataFrame

from ._core import merge_data

__all__ = ['merge_SMPS_APS']


def _volume_below_1um(data):
    """Particle volume concentration for D ≤ 1 µm (µm³/cm³) from a dN/dlogDp frame."""
    dp = data.columns.astype(float)
    dlogdp = np.diff(np.log10(dp)).mean()
    sub = dp <= 1000
    return (data.loc[:, sub] * dlogdp * (np.pi / 6) * (dp[sub] / 1000.0) ** 3).sum(axis=1, min_count=1)


def merge_SMPS_APS(df_smps, df_aps, df_pm1, aps_unit='um', smps_overlap_lowbound=500,
                   aps_fit_highbound=1000, density_range=(0.5, 3.0), n_iter=3,
                   mass_rel_unc=None):
    """EXPERIMENTAL mass-anchored merge. Requires a PM1 mass reference.

    Parameters
    ----------
    df_smps, df_aps : DataFrame
        SMPS / APS dN/dlogDp (diameters as columns; APS in µm if aps_unit='um').
    df_pm1 : Series or DataFrame
        PM1 mass concentration (µg/m³), same time index. Drives the density via
        mass closure. **Prefer a volatile-corrected PM1.**
    density_range : tuple, default (0.5, 3.0)
        Physical clip for the effective density (g/cm³).
    n_iter : int, default 3
        Mass-closure fixed-point iterations (V(<1µm) depends weakly on the shift).
    mass_rel_unc : Series, optional
        Per-timestamp relative mass uncertainty (e.g. volatile fraction). Used
        only to propagate into ``density_unc``; defaults to 0.1.

    Returns
    -------
    dict
        ``data`` (merged dN/dlogDp), ``density`` (daily effective density),
        ``density_hourly`` (raw hourly mass-closure density) and ``density_unc``.
    """
    smps, aps = df_smps.copy(), df_aps.copy()
    smps.columns = smps.keys().to_numpy(float)
    aps.columns = aps.keys().to_numpy(float)
    if aps_unit == 'um':
        aps.columns = aps.keys() * 1e3

    pm1 = (df_pm1.squeeze() if hasattr(df_pm1, 'squeeze') else df_pm1).astype(float)
    idx = smps.index

    # --- density from PM1 mass closure, daily, iterated to self-consistency ---
    rho_daily = Series(np.mean(density_range), index=idx)
    rho_h = rho_daily
    for _ in range(max(1, n_iter)):
        shift = np.sqrt(rho_daily.clip(*density_range)).to_frame()
        data, _, _ = merge_data(smps, aps, shift, smps_overlap_lowbound, aps_fit_highbound, 'mobility')
        rho_h = (pm1 / _volume_below_1um(data)).reindex(idx).clip(*density_range)
        rho_daily = rho_h.resample('1D').median().reindex(idx, method='ffill').bfill()

    # --- final merge at the daily density + decoupled APS counting correction ---
    shift = np.sqrt(rho_daily.clip(*density_range)).to_frame()
    _, _, _corr = merge_data(smps, aps, shift, smps_overlap_lowbound, aps_fit_highbound, 'mobility')
    corr = _corr.resample('1d').mean().reindex(idx).ffill()
    corr = corr.mask(corr < 1, 1)
    aps_c = aps.copy()
    aps_c.loc[:, corr.keys()] *= corr
    data, _, _ = merge_data(smps, aps_c, shift, smps_overlap_lowbound, aps_fit_highbound, 'mobility')

    # --- uncertainty: daily spread of hourly density + propagated mass uncertainty ---
    half_iqr = (rho_h.resample('1D').agg(lambda x: x.quantile(.75) - x.quantile(.25))
                .reindex(idx, method='ffill').bfill() / 2)
    rel = (mass_rel_unc.reindex(idx).fillna(0.1) if mass_rel_unc is not None else 0.1)
    unc = np.sqrt(half_iqr ** 2 + (rho_daily * rel) ** 2)

    return {
        'data': data,
        'density': rho_daily.rename('density').to_frame(),
        'density_hourly': rho_h.rename('density_hourly').to_frame(),
        'density_unc': unc.rename('density_unc').to_frame(),
    }
