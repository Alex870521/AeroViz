"""Top-level optical-processing functions; convenience wrappers — see
`AeroViz.dataProcess.Optical.*` for full algorithm details."""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = [
    'optical_basic',
    'improve',
    'gas_extinction',
    'retrieve_ri',
    'brown_carbon',
    'mie',
]


def optical_basic(df_sca, df_abs, df_mass=None, df_no2=None, df_temp=None):
    """Compute basic optical properties (extinction, SSA, MEE/MSE/MAE, Ångström
    exponents) from measured scattering and absorption.

    Parameters
    ----------
    df_sca : DataFrame
        Scattering coefficient (Mm⁻¹).
    df_abs : DataFrame
        Absorption coefficient (Mm⁻¹).
    df_mass : DataFrame, optional
        PM mass concentration (μg/m³), used for mass efficiencies.
    df_no2 : DataFrame, optional
        NO2 concentration (ppb), used to subtract gas absorption.
    df_temp : DataFrame, optional
        Ambient temperature (°C), used in gas-extinction correction.

    Returns
    -------
    DataFrame
        Derived optical properties.
    """
    from AeroViz.dataProcess.Optical._extinction import _basic
    return _basic(df_sca, df_abs, df_mass, df_no2, df_temp)


def improve(df_mass, df_RH=None, method='revised', df_nh4_status=None,
            df_ext=None, oa_oc_ratio=1.8, upper_bounds=None):
    """Calculate extinction using the IMPROVE equation.

    Parameters
    ----------
    df_mass : DataFrame
        Reconstructed mass concentrations. Required columns depend on `method`:
        - 'revised' / 'modified': AS, AN, OM, Soil, SS, EC
        - 'localized':            AS, AN, POC, SOC, Soil, SS, EC
    df_RH : DataFrame, optional
        Relative humidity (%).
    method : {'revised', 'modified', 'localized'}, default 'revised'
        IMPROVE variant.
    df_nh4_status : DataFrame, optional
        NH4 status from chemistry reconstruction; rows flagged
        'Deficiency' are excluded.
    df_ext : DataFrame, optional
        Measured extinction with 'Scattering' and 'Absorption' columns
        (Mm⁻¹). Required for method='localized'.
    oa_oc_ratio : float, default 1.8
        OA/OC conversion ratio (method='localized' only).
    upper_bounds : dict, optional
        Upper bounds for MLR coefficients (method='localized' only).

    Returns
    -------
    dict
        Keys include 'dry', 'wet', 'ALWC', 'fRH'; method='localized'
        adds 'coefficients' and 'regression'.
    """
    from AeroViz.dataProcess.Optical._IMPROVE import revised, modified, localized

    if method == 'revised':
        return revised(df_mass, df_RH, df_nh4_status)
    if method == 'modified':
        return modified(df_mass, df_RH, df_nh4_status)
    if method == 'localized':
        if df_ext is None:
            raise ValueError(
                "method='localized' requires df_ext with 'Scattering' and "
                "'Absorption' columns to fit POA/SOA mass scattering "
                "efficiencies via MLR."
            )
        return localized(df_mass, df_ext, df_RH, df_nh4_status,
                         oa_oc_ratio=oa_oc_ratio, upper_bounds=upper_bounds)
    raise ValueError(
        f"method must be 'revised', 'modified', or 'localized', got '{method}'"
    )


def gas_extinction(df_no2, df_temp):
    """Calculate gas contribution to extinction (Rayleigh + NO2 absorption).

    Parameters
    ----------
    df_no2 : DataFrame
        NO2 concentration (ppb).
    df_temp : DataFrame
        Ambient temperature (°C).

    Returns
    -------
    DataFrame
        Columns: ScatteringByGas, AbsorptionByGas, ExtinctionByGas (Mm⁻¹).
    """
    from AeroViz.dataProcess.Optical._IMPROVE import gas_extinction as _gas_ext
    return _gas_ext(df_no2, df_temp)


def retrieve_ri(df_optical, df_pnsd, dlogdp=0.014, wavelength=550):
    """Retrieve complex refractive index from co-located optical and PSD data.

    Parameters
    ----------
    df_optical : DataFrame
        Optical data with Extinction, Scattering, and Absorption columns.
    df_pnsd : DataFrame
        Particle number size distribution.
    dlogdp : float, default 0.014
        Logarithmic bin width.
    wavelength : float, default 550
        Wavelength in nm.

    Returns
    -------
    DataFrame
        Retrieved RI with `re_real` and `re_imaginary` columns.
    """
    from AeroViz.dataProcess.Optical._retrieve_RI import retrieve_RI
    return retrieve_RI(df_optical, df_pnsd, dlogdp, wavelength)


def brown_carbon(df_abs, wavelengths=None, ref_wavelength=880, aae_bc=1.0):
    """Separate BC and BrC absorption using the AAE approach.

    Parameters
    ----------
    df_abs : DataFrame
        Absorption coefficients at multiple wavelengths (Mm⁻¹), with
        columns named like 'abs_370', 'abs_470', ..., 'abs_880'.
    wavelengths : list[int], optional
        Wavelengths to compute BrC for. Default: [370, 470, 520, 590, 660].
    ref_wavelength : int, default 880
        Reference wavelength assumed to be pure-BC absorption.
    aae_bc : float, default 1.0
        AAE assumed for Black Carbon.

    Returns
    -------
    DataFrame
        BC/BrC absorption, BrC fraction at each wavelength, and AAE_BrC.
    """
    from AeroViz.dataProcess.Optical._derived import calculate_BrC_absorption
    return calculate_BrC_absorption(
        df_abs=df_abs,
        wavelengths=wavelengths,
        ref_wavelength=ref_wavelength,
        aae_bc=aae_bc,
    )


# =============================================================================
# Mie consolidation
# =============================================================================

def _is_mixing_table(ri: pd.DataFrame) -> bool:
    """Return True iff `ri` is a DataFrame with at least one
    `*_volume_ratio` column."""
    return isinstance(ri, pd.DataFrame) and any(
        str(c).endswith('_volume_ratio') for c in ri.columns
    )


def _mixing_table_to_complex_ri(ri_table: pd.DataFrame,
                                wavelength: float) -> np.ndarray:
    """Compute an effective complex RI per row by volume-weighted average
    of the species refractive indices for the given mixing table."""
    from AeroViz.dataProcess.core import REFRACTIVE_INDEX

    # Pick the wavelength key whose value is numerically closest to the
    # requested wavelength so that 450/550 nm constants are reused naturally.
    available = {int(k): k for k in REFRACTIVE_INDEX}
    key = available[min(available, key=lambda w: abs(w - wavelength))]
    species_ri = REFRACTIVE_INDEX[key]

    eff = np.zeros(len(ri_table), dtype=complex)
    for col in ri_table.columns:
        col = str(col)
        if not col.endswith('_volume_ratio'):
            continue
        species = col[: -len('_volume_ratio')]
        if species not in species_ri:
            continue
        eff = eff + species_ri[species] * ri_table[col].values
    return eff


def mie(df_psd, ri, wavelength=550, mixing=None, distribution=False):
    """Compute Mie optical properties from a particle size distribution.

    Parameters
    ----------
    df_psd : DataFrame
        PSD with rows = time, columns = diameters (nm).
    ri : Series of complex | DataFrame
        Refractive index. EITHER:
          - Series of complex numbers, one per row → single-material Mie
          - DataFrame with columns ending in '_volume_ratio' → species mixing
            table (one column per species, values in [0, 1])
    wavelength : float, default 550
        Wavelength in nm.
    mixing : {'internal', 'external', 'both'}, optional
        Only used when ri is a mixing table.
        - 'internal' (default if not given): all species mixed within
          each particle
        - 'external': each species contributes independently
        - 'both': compute and return both
    distribution : bool, default False
        False → return total ext/sca/abs (Mm⁻¹) per row.
        True  → return per-bin dExt/dSca/dAbs (Mm⁻¹) distributions.

    Returns
    -------
    DataFrame | dict
        - mixing in (None/'internal'/'external'): DataFrame
        - mixing == 'both': dict {'internal': DataFrame, 'external': DataFrame}
    """
    from AeroViz.dataProcess.Optical.mie import (
        Mie_SD,
        internal_mixing,
        external_mixing,
        calculate_extinction_distribution,
    )

    if mixing is not None and mixing not in ('internal', 'external', 'both'):
        raise ValueError(
            f"mixing must be one of None, 'internal', 'external', 'both'; "
            f"got '{mixing}'"
        )

    # --- Detect single-material vs mixing-table ---
    if _is_mixing_table(ri):
        # Mixing-table dispatch
        if distribution:
            raise NotImplementedError(
                "distribution=True with a mixing-table RI is not yet "
                "supported. Reduce the table to a single complex RI per "
                "row (e.g. volume-weighted) and pass it as a Series."
            )

        chosen = mixing or 'internal'

        if chosen == 'internal':
            eff_ri = _mixing_table_to_complex_ri(ri, wavelength)
            return internal_mixing(
                df_psd,
                pd.Series(eff_ri, index=ri.index),
                wavelength=wavelength,
            )

        # external_mixing expects volume-fraction columns WITHOUT the
        # '_volume_ratio' suffix — strip it for the call.
        stripped = ri.rename(
            columns={
                c: str(c)[: -len('_volume_ratio')]
                for c in ri.columns
                if str(c).endswith('_volume_ratio')
            }
        )

        if chosen == 'external':
            return external_mixing(df_psd, stripped, wavelength=wavelength)

        # chosen == 'both'
        eff_ri = _mixing_table_to_complex_ri(ri, wavelength)
        internal_df = internal_mixing(
            df_psd, pd.Series(eff_ri, index=ri.index), wavelength=wavelength,
        )
        external_df = external_mixing(df_psd, stripped, wavelength=wavelength)
        return {'internal': internal_df, 'external': external_df}

    # --- Single-material path ---
    if mixing is not None:
        raise ValueError(
            "mixing= is only valid when ri is a mixing table (DataFrame "
            "with '*_volume_ratio' columns)."
        )

    # Accept Series-of-complex, or 1-column complex DataFrame, or numpy array
    if isinstance(ri, pd.DataFrame):
        if ri.shape[1] != 1 or not np.issubdtype(
            ri.iloc[:, 0].dtype, np.complexfloating
        ):
            raise ValueError(
                "Single-material RI must be a Series of complex numbers "
                "(or a single-column DataFrame of complex dtype). For a "
                "species mixing table, use columns ending in "
                "'_volume_ratio'."
            )
        ri_array = ri.iloc[:, 0].values
    elif isinstance(ri, pd.Series):
        ri_array = ri.values
    else:
        ri_array = np.asarray(ri)

    if distribution:
        # calculate_extinction_distribution returns dict with 'ext','sca',
        # 'abs','diameter' as numpy arrays. Wrap into a tidy DataFrame
        # keyed by diameter and named by quantity, matching the
        # "per-bin dExt/dSca/dAbs distributions" contract.
        diameter = df_psd.columns.values.astype(float)
        result = calculate_extinction_distribution(
            refractive_index=ri_array,
            wavelength=wavelength,
            diameter=diameter,
            number_conc=df_psd.values,
        )

        # 1D PSD (single row) → squeeze yields (n_bins,)
        # 2D PSD → (n_times, n_bins). For consistency, always return a
        # dict of DataFrames keyed by quantity with rows=time, cols=Dp.
        ext_arr = np.atleast_2d(result['ext'])
        sca_arr = np.atleast_2d(result['sca'])
        abs_arr = np.atleast_2d(result['abs'])

        index = df_psd.index
        cols = diameter

        return {
            'ext': pd.DataFrame(ext_arr, index=index, columns=cols),
            'sca': pd.DataFrame(sca_arr, index=index, columns=cols),
            'abs': pd.DataFrame(abs_arr, index=index, columns=cols),
        }

    # Scalar ext/sca/abs per row via Mie_SD
    return Mie_SD(ri_array, wavelength, df_psd)
