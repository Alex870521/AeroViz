"""Top-level size-distribution functions; convenience wrappers — see `AeroViz.dataProcess.SizeDistr.*` for full algorithm details."""

from AeroViz.dataProcess.SizeDistr._size_dist import SizeDist
from AeroViz.dataProcess.SizeDistr.merge import merge_v1, merge_v2, merge_v3, merge_v4

__all__ = ['psd_stats', 'psd_distributions', 'merge_psd']


def psd_stats(df, hybrid_bin_start_loc=None, unit='nm', bin_range=(11.8, 19810), input_type='dlogdp'):
    """
    Compute mode statistics for a particle size distribution.

    Convenience wrapper around the logic in
    ``AeroViz.dataProcess.SizeDistr.SizeDistr.basic``. Builds a ``SizeDist``
    from the input DataFrame, computes per-bin ``dlogdp``, and returns the
    mode statistics (with the ``'statistics'`` key renamed to ``'other'``
    for backward compatibility).

    Parameters
    ----------
    df : DataFrame
        Raw particle size distribution data. Column labels must be
        diameters convertible to ``float``.
    hybrid_bin_start_loc : int, optional
        Column index where the bin spacing changes (for hybrid instruments
        such as merged SMPS+APS). If ``None``, a single mean ``dlogdp`` is
        used for all bins.
    unit : {'nm', 'um'}, default 'nm'
        Unit of the diameter columns.
    bin_range : tuple of float, default (11.8, 19810)
        Inclusive ``(min, max)`` diameter range (in ``unit``) to keep.
    input_type : {'dlogdp', 'norm', 'raw'}, default 'dlogdp'
        ``'dlogdp'``/``'norm'`` — input is already normalized (dN/dlogDp).
        Anything else — input is raw counts and will be divided by
        ``dlogdp``.

    Returns
    -------
    dict
        Distributions and statistics by weighting (keys include
        ``'number'``, ``'surface'``, ``'volume'``, ``'other'``).
    """
    import numpy as np

    # Prepare data
    data = df.copy()
    data.columns = data.keys().to_numpy(float)

    # Filter by size range
    cols = data.keys()[(data.keys() >= bin_range[0]) & (data.keys() <= bin_range[-1])]
    data = data[cols].copy()

    dp = data.keys().to_numpy()

    # Calculate dlogdp
    if hybrid_bin_start_loc is None:
        dlog_dp = np.full(dp.size, np.diff(np.log10(dp)).mean())
    else:
        dlog_dp = np.ones(dp.size)
        dlog_dp[:hybrid_bin_start_loc] = np.diff(np.log10(dp[:hybrid_bin_start_loc])).mean()
        dlog_dp[hybrid_bin_start_loc:] = np.diff(np.log10(dp[hybrid_bin_start_loc:])).mean()

    # Handle normalization
    if input_type in ('dlogdp', 'norm'):
        data_norm = data
    else:
        data_norm = data / dlog_dp

    # Create SizeDist and calculate
    psd = SizeDist(data_norm, state='dlogdp', weighting='n')
    psd.dlogdp = dlog_dp

    out = psd.mode_statistics(unit=unit)

    # Rename for backward compatibility
    out['other'] = out.pop('statistics')

    return out


def psd_distributions(df_pnsd):
    """
    Compute number / surface / volume distributions and their properties.

    Convenience wrapper around the logic in
    ``AeroViz.dataProcess.SizeDistr.SizeDistr.distributions``.

    Parameters
    ----------
    df_pnsd : DataFrame
        Particle number size distribution (dN/dlogDp). Column labels must be
        diameters in nm.

    Returns
    -------
    dict
        ``{'number', 'surface', 'volume', 'properties'}`` — the first three
        are DataFrames keyed by diameter; ``'properties'`` concatenates the
        per-distribution properties (GMD, GSD, mode, etc.).
    """
    from pandas import concat

    psd = SizeDist(df_pnsd, weighting='n')

    number = psd.data
    surface = psd.to_surface()
    volume = psd.to_volume()

    # Calculate properties for each distribution type
    props_n = psd.properties()
    props_s = SizeDist(surface, weighting='s').properties()
    props_v = SizeDist(volume, weighting='v').properties()

    return {
        'number': number,
        'surface': surface,
        'volume': volume,
        'properties': concat([props_n, props_s, props_v], axis=1),
    }


def merge_psd(df_smps, df_aps, *, version: int = 4, df_pm25=None,
              aps_unit: str = 'um',
              smps_overlap_lowbound: float = 500,
              aps_fit_highbound: float = 1000,
              shift_mode: str = 'mobility',
              dndsdv_alg: bool = True,
              density_range: tuple = (0.6, 2.6),
              times_range: tuple = (0.8, 1.25, 0.05)):
    """
    Merge SMPS and APS particle size distributions into a continuous PSD.

    Parameters
    ----------
    df_smps, df_aps : DataFrame
        SMPS and APS particle size distributions. Columns are diameters
        (SMPS in nm; APS in µm if ``aps_unit='um'``, else nm).
    version : {1, 2, 3, 4}, default 4
        Algorithm version:
          1 — Original power-law fit with ``shift_mode`` parameter.
          2 — Simplified output, no QC filtering.
          3 — Multiprocessing + dN/dS/dV correlation algorithm.
          4 — PM2.5 fitness function + SMPS times correction (RECOMMENDED).
    df_pm25 : DataFrame, optional
        PM2.5 reference for fitness. **Required when ``version=4``.**
    aps_unit : {'um', 'nm'}, default 'um'
        Unit of the APS diameter columns.
    smps_overlap_lowbound : float, default 500
        SMPS bin lower bound for the overlap region (nm).
    aps_fit_highbound : float, default 1000
        APS bin upper bound for the power-law fit region (nm).
    shift_mode : {'mobility', 'aerodynamic'}, default 'mobility'
        Only used when ``version=1``.
    dndsdv_alg : bool, default True
        Apply dN/dS/dV correlation refinement. Only used when
        ``version >= 3``.
    density_range : tuple of float, default (0.6, 2.6)
        Plausible effective-density range (g/cm³) for quality control.
        Each timestamp's shift² is its estimated effective density;
        timestamps outside this range are dropped (set to NaN). Widen for
        looser QC (e.g. ``(0.3, 2.6)``), narrow for stricter. Applied in
        every version.
    times_range : tuple of 3 floats, default (0.8, 1.25, 0.05)
        ``(start, stop, step)`` for the SMPS-times grid search. Only used
        when ``version=4``.

    Returns
    -------
    dict
        Every version returns a dict keyed consistently. Two keys are always
        present:

        - ``'data'``    : the recommended merged dN/dlogDp (diameters in nm as
          columns). v1 → the single power-law merge; v2 → mobility merge;
          v3/v4 → the APS-corrected dN/dS/dV merge (``cor_dndsdv``).
        - ``'density'`` : estimated effective density (g/cm³).

        Version-specific extras:

        - v2 : ``'data_aero'`` (aerodynamic-diameter merge).
        - v3 : ``'data_dn'``, ``'data_dndsdv'``, ``'data_cor_dn'`` (the other
          algorithm variants); ``'density'`` has one column per variant.
        - v4 : same variants as v3 plus ``'times'`` (the chosen SMPS-times
          multiplier per algorithm).

    Raises
    ------
    ValueError
        If ``version`` is not in ``{1, 2, 3, 4}``, or ``version=4`` is used
        without ``df_pm25``.
    """
    if version == 1:
        return merge_v1(df_smps, df_aps, aps_unit, shift_mode,
                        smps_overlap_lowbound, aps_fit_highbound, density_range)
    if version == 2:
        return merge_v2(df_smps, df_aps, aps_unit,
                        smps_overlap_lowbound, aps_fit_highbound, density_range)
    if version == 3:
        return merge_v3(df_smps, df_aps, aps_unit,
                        smps_overlap_lowbound, aps_fit_highbound, dndsdv_alg, density_range)
    if version == 4:
        if df_pm25 is None:
            raise ValueError(
                "merge_psd(version=4) requires df_pm25 (PM2.5 reference DataFrame)."
            )
        return merge_v4(df_smps, df_aps, df_pm25, aps_unit,
                        smps_overlap_lowbound, aps_fit_highbound,
                        dndsdv_alg, density_range, times_range)

    raise ValueError(f"version must be one of {{1, 2, 3, 4}}, got {version}.")
