# -*- coding: utf-8 -*-
"""
Mie Scattering Calculation for Size Distribution Data

This module provides vectorized Mie scattering calculations optimized for
particle size distribution (PSD) data stored in pandas DataFrames.

Based on: http://pymiescatt.readthedocs.io/en/latest/forward.html

Theory:
    Mie theory describes the scattering of electromagnetic radiation by
    spherical particles. The key outputs are:
    - Q_ext: Extinction efficiency (scattering + absorption)
    - Q_sca: Scattering efficiency
    - Q_abs: Absorption efficiency (Q_ext - Q_sca)
"""

import warnings
import numpy as np
import pandas as pd
from scipy.integrate import trapezoid
from scipy.special import jv, yv  # Bessel functions


# =============================================================================
# PSD Type Detection and Integration
# =============================================================================

def _detect_psd_type(values: np.ndarray, diameter: np.ndarray) -> tuple[str, str]:
    """
    Auto-detect whether PSD data is dN/dlogDp or dN.

    Parameters
    ----------
    values : np.ndarray
        PSD values, shape (n_bins,) or (n_times, n_bins)
    diameter : np.ndarray
        Particle diameters in nm

    Returns
    -------
    psd_type : str
        'dNdlogDp' or 'dN'
    confidence : str
        'high', 'medium', or 'low'
    """
    log_dp = np.log10(diameter)
    dlogdp = np.diff(log_dp).mean()

    # Use mean values if 2D
    if values.ndim > 1:
        values_1d = np.nanmean(values, axis=0)
    else:
        values_1d = values

    # Calculate total N under both assumptions
    N_as_dNdlogDp = trapezoid(values_1d, x=log_dp)
    N_as_dN = np.nansum(values_1d)

    # Typical total particle number: 1e2 - 1e7 #/cm³
    typical_min, typical_max = 1e2, 1e7

    dNdlogDp_ok = typical_min <= N_as_dNdlogDp <= typical_max
    dN_ok = typical_min <= N_as_dN <= typical_max

    # Calculate the ratio (should be ~1/dlogDp if dNdlogDp)
    ratio = N_as_dN / N_as_dNdlogDp if N_as_dNdlogDp > 0 else float('inf')
    expected_ratio = 1 / dlogdp

    if dNdlogDp_ok and not dN_ok:
        return 'dNdlogDp', 'high'
    elif dN_ok and not dNdlogDp_ok:
        return 'dN', 'high'
    elif dNdlogDp_ok and dN_ok:
        # Both reasonable - check if ratio matches expected
        if 0.5 * expected_ratio < ratio < 2 * expected_ratio:
            return 'dNdlogDp', 'medium'
        else:
            return 'dN', 'medium'
    else:
        # Neither reasonable - default to dNdlogDp with warning
        return 'dNdlogDp', 'low'


def _integrate_psd(
    values: np.ndarray,
    diameter: np.ndarray,
    psd_type: str = 'dNdlogDp'
) -> np.ndarray:
    """
    Integrate over particle size distribution.

    Parameters
    ----------
    values : np.ndarray
        Integrand values, shape (n_times, n_bins)
    diameter : np.ndarray
        Particle diameters in nm
    psd_type : str
        'dNdlogDp' or 'dN'

    Returns
    -------
    result : np.ndarray
        Integrated values, shape (n_times,)
    """
    if psd_type == 'dNdlogDp':
        log_dp = np.log10(diameter)
        return trapezoid(values, x=log_dp, axis=-1)
    else:  # dN
        return np.sum(values, axis=-1)


def calculate_mie_coefficients(
    refractive_index: np.ndarray,
    size_parameter: np.ndarray,
    n_max: np.ndarray,
    n_terms: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calculate Mie scattering coefficients (a_n, b_n) for multiple particles.

    This implements the core Mie theory calculation using Bessel functions
    and the logarithmic derivative method for numerical stability.

    Parameters
    ----------
    refractive_index : np.ndarray
        Complex refractive index (m = n + ik) for each time point.
        Shape: (n_times,)
    size_parameter : np.ndarray
        Size parameter x = π * diameter / wavelength for each size bin.
        Shape: (n_bins,)
    n_max : np.ndarray
        Maximum number of terms needed for each size bin.
        Shape: (n_bins,)
    n_terms : pd.DataFrame
        Term indices for the series expansion.
        Shape: (n_bins, max_terms)

    Returns
    -------
    Q_ext : pd.DataFrame
        Extinction efficiency for each (size_bin, time_point).
    Q_sca : pd.DataFrame
        Scattering efficiency for each (size_bin, time_point).

    Notes
    -----
    The Mie coefficients a_n and b_n are calculated using:
    - Riccati-Bessel functions (ψ, χ)
    - Logarithmic derivative D_n(mx) computed via downward recurrence
    """
    m = refractive_index
    x = size_parameter
    n_bins = len(x)
    n_times = len(m)

    # Bessel function order: ν = n + 0.5
    nu = n_terms.copy() + 0.5

    # Coefficient for series summation: 2n + 1
    coeff_2n_plus_1 = 2 * n_terms.copy() + 1

    # === Calculate Riccati-Bessel functions ===
    # ψ_n(x) = sqrt(πx/2) * J_{n+1/2}(x)  [Bessel J]
    # χ_n(x) = -sqrt(πx/2) * Y_{n+1/2}(x) [Bessel Y]
    sqrt_factor = np.sqrt(0.5 * np.pi * x)

    psi_n = sqrt_factor.reshape(-1, 1) * jv(nu, x.reshape(-1, 1))
    chi_n = -sqrt_factor.reshape(-1, 1) * yv(nu, x.reshape(-1, 1))

    # ψ_{n-1}(x) and χ_{n-1}(x) with boundary conditions
    psi_n_minus_1 = pd.concat(
        [pd.DataFrame(np.sin(x)), psi_n.mask(n_terms == n_max.reshape(-1, 1))],
        axis=1
    )
    psi_n_minus_1.columns = np.arange(len(psi_n_minus_1.columns))
    psi_n_minus_1 = psi_n_minus_1[n_terms.columns]

    chi_n_minus_1 = pd.concat(
        [pd.DataFrame(np.cos(x)), chi_n.mask(n_terms == n_max.reshape(-1, 1))],
        axis=1
    )
    chi_n_minus_1.columns = np.arange(len(chi_n_minus_1.columns))
    chi_n_minus_1 = chi_n_minus_1[n_terms.columns]

    # Hankel function: ξ_n(x) = ψ_n(x) - i*χ_n(x)
    xi_n = psi_n - 1j * chi_n
    xi_n_minus_1 = psi_n_minus_1 - 1j * chi_n_minus_1

    # === Calculate logarithmic derivative D_n(mx) ===
    mx = m.reshape(-1, 1) * x  # Complex argument

    # Number of terms needed for downward recurrence
    nmx_array = np.round(
        np.max(
            np.hstack([[n_max] * n_times, np.abs(mx)]).reshape(n_times, 2, -1),
            axis=1
        ) + 16
    )

    # Initialize output DataFrames
    Q_ext = pd.DataFrame(columns=m.flatten(), index=n_terms.index)
    Q_sca = pd.DataFrame(columns=m.flatten(), index=n_terms.index)

    # Normalize n/x for later use
    n_over_x = n_terms / x.reshape(-1, 1)

    # === Main calculation loop over size bins ===
    for bin_idx, (nmx_values, mx_values, nmax_bin) in enumerate(
        zip(nmx_array.T, mx.T, n_max)
    ):
        # Logarithmic derivative D_n(mx) via downward recurrence
        D_n = pd.DataFrame(
            np.nan,
            index=np.arange(n_times),
            columns=n_terms.columns,
            dtype=complex
        )

        # Group by nmx value for efficient computation
        for nmx, time_indices in pd.DataFrame(nmx_values).groupby(0).groups.items():
            inv_mx = 1 / mx_values[time_indices]
            nmx_int = int(nmx)

            # Downward recurrence: D_{n-1} = n/mx - 1/(D_n + n/mx)
            D_recurrence = np.zeros((len(time_indices), nmx_int), dtype=complex)
            for idx in range(nmx_int - 1, 1, -1):
                D_recurrence[:, idx - 1] = (
                    idx * inv_mx - 1 / (D_recurrence[:, idx] + idx * inv_mx)
                )

            D_n.loc[time_indices, 0:int(nmax_bin) - 1] = D_recurrence[:, 1:int(nmax_bin) + 1]

        # Get values for this size bin
        n_x = n_over_x.loc[bin_idx]
        psi = psi_n.loc[bin_idx]
        psi_prev = psi_n_minus_1.loc[bin_idx]
        xi = xi_n.loc[bin_idx]
        xi_prev = xi_n_minus_1.loc[bin_idx]
        coeff = coeff_2n_plus_1.loc[bin_idx].values

        # === Calculate Mie coefficients a_n and b_n ===
        # a_n = (D_n/m + n/x) * ψ_n - ψ_{n-1}
        #       ─────────────────────────────────
        #       (D_n/m + n/x) * ξ_n - ξ_{n-1}
        numerator_a = D_n / m.reshape(-1, 1) + n_x
        a_n = (numerator_a * psi - psi_prev) / (numerator_a * xi - xi_prev)

        # b_n = (m*D_n + n/x) * ψ_n - ψ_{n-1}
        #       ─────────────────────────────────
        #       (m*D_n + n/x) * ξ_n - ξ_{n-1}
        numerator_b = D_n * m.reshape(-1, 1) + n_x
        b_n = (numerator_b * psi - psi_prev) / (numerator_b * xi - xi_prev)

        # === Calculate efficiencies ===
        # Q_ext = (2/x²) * Σ (2n+1) * Re(a_n + b_n)
        # Q_sca = (2/x²) * Σ (2n+1) * (|a_n|² + |b_n|²)
        real_a, real_b = np.real(a_n), np.real(b_n)
        imag_a, imag_b = np.imag(a_n), np.imag(b_n)

        Q_ext.loc[bin_idx] = np.nansum(coeff * (real_a + real_b), axis=1)
        Q_sca.loc[bin_idx] = np.nansum(
            coeff * (real_a**2 + real_b**2 + imag_a**2 + imag_b**2),
            axis=1
        )

    return Q_ext, Q_sca


def calculate_mie_efficiencies(
    refractive_index: np.ndarray,
    wavelength: float,
    diameter: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """
    Calculate Mie extinction and scattering efficiencies (Q).

    Parameters
    ----------
    refractive_index : np.ndarray
        Complex refractive index for each time point. Shape: (n_times,)
    wavelength : float
        Wavelength of incident light in nm.
    diameter : np.ndarray
        Particle diameters in nm. Shape: (n_bins,)

    Returns
    -------
    Q_ext : np.ndarray
        Extinction efficiency. Shape: (n_times, n_bins)
    Q_sca : np.ndarray
        Scattering efficiency. Shape: (n_times, n_bins)

    Notes
    -----
    Size parameter: x = π * d / λ
    The number of terms needed scales as: n_max ≈ 2 + x + 4*x^(1/3)
    """
    # Size parameter: x = πd/λ
    size_parameter = np.pi * diameter / wavelength

    # Maximum number of terms in series expansion
    n_max = np.round(2 + size_parameter + 4 * size_parameter**(1/3))

    # Create term index matrix (masked where n > n_max for each bin)
    max_terms = int(n_max.max())
    n_terms = pd.DataFrame([np.arange(1, max_terms + 1)] * len(n_max))
    n_terms = n_terms.mask(n_terms > n_max.reshape(-1, 1))

    # Calculate Mie coefficients
    Q_ext_raw, Q_sca_raw = calculate_mie_coefficients(
        refractive_index, size_parameter, n_max, n_terms
    )

    # Apply normalization factor: 2/x²
    norm_factor = (2 / size_parameter**2).reshape(-1, 1)
    Q_ext = (norm_factor * Q_ext_raw).values.T.astype(float)
    Q_sca = (norm_factor * Q_sca_raw).values.T.astype(float)

    return Q_ext, Q_sca


def Mie_SD(
    refractive_index: np.ndarray,
    wavelength: float,
    psd: pd.DataFrame,
    psd_type: str = 'auto',
    multi_ri_per_psd: bool = False,
    precomputed_Q: tuple = None
) -> pd.DataFrame | dict:
    """
    Calculate optical properties from particle size distribution using Mie theory.

    This function integrates Mie efficiencies over the particle size distribution
    to obtain bulk optical properties (extinction, scattering, absorption).

    Parameters
    ----------
    refractive_index : np.ndarray
        Complex refractive index (m = n + ik).
        - If multi_ri_per_psd=False: Shape (n_times,), one m per time point
        - If multi_ri_per_psd=True: Shape (n_ri,), multiple m tested per PSD
    wavelength : float
        Wavelength of incident light in nm.
    psd : pd.DataFrame
        Particle size distribution data.
        - Columns: particle diameters (nm)
        - Rows: time points
        - Values: dN/dlogDp or dN depending on psd_type
    psd_type : str, default='auto'
        Type of PSD input:
        - 'dNdlogDp': Number concentration per log bin width (#/cm³)
        - 'dN': Number concentration per bin (#/cm³/bin)
        - 'auto': Auto-detect with warning if uncertain
    multi_ri_per_psd : bool, default=False
        If True, calculate for multiple refractive indices per PSD row.
        Useful for refractive index retrieval.
    precomputed_Q : tuple, optional
        Pre-computed (Q_ext, Q_sca) to avoid recalculation.

    Returns
    -------
    pd.DataFrame or dict
        If multi_ri_per_psd=False:
            DataFrame with columns ['ext', 'sca', 'abs'] in Mm⁻¹
        If multi_ri_per_psd=True:
            dict with keys 'ext', 'sca', 'abs', each a DataFrame
            with refractive indices as columns

    Examples
    --------
    >>> import pandas as pd
    >>> import numpy as np
    >>>
    >>> # Create sample PSD data (100 time points, 50 size bins)
    >>> dp = np.logspace(1, 3, 50)  # 10-1000 nm
    >>> psd = pd.DataFrame(np.random.rand(100, 50) * 1000, columns=dp)
    >>>
    >>> # Refractive index for each time point
    >>> m = np.array([complex(1.5, 0.02)] * 100)
    >>>
    >>> # Calculate optical properties (explicit dN/dlogDp input)
    >>> result = Mie_SD(m, wavelength=550, psd=psd, psd_type='dNdlogDp')
    >>> print(result[['ext', 'sca', 'abs']].head())

    Notes
    -----
    The optical coefficients are calculated as:

    For dN/dlogDp input:
        b = ∫ Q(Dp) * π/4 * Dp² * (dN/dlogDp) * dlogDp

    For dN input:
        b = Σ Q(Dp) * π/4 * Dp² * dN

    Where:
        - Q: Mie efficiency (extinction, scattering, or absorption)
        - Dp: particle diameter
        - The factor 1e-6 converts from nm² to Mm⁻¹
    """
    # Ensure psd is a DataFrame
    if not isinstance(psd, pd.DataFrame):
        psd = pd.DataFrame(psd).T

    # Validate input dimensions
    if not multi_ri_per_psd and len(refractive_index) != len(psd):
        raise ValueError(
            f"Refractive index array length ({len(refractive_index)}) must match "
            f"PSD row count ({len(psd)}). Set multi_ri_per_psd=True for RI retrieval."
        )

    # Extract diameter and number concentration
    diameter = psd.columns.values.astype(float)  # nm
    number_conc = psd.values  # dN/dlogDp or dN

    # Auto-detect PSD type if needed
    if psd_type == 'auto':
        detected_type, confidence = _detect_psd_type(number_conc, diameter)
        psd_type = detected_type

        if confidence == 'low':
            warnings.warn(
                f"PSD type auto-detection has low confidence. "
                f"Assuming '{detected_type}'. Please specify psd_type explicitly "
                f"('dNdlogDp' or 'dN') to avoid incorrect results.",
                UserWarning
            )
        elif confidence == 'medium':
            warnings.warn(
                f"PSD type auto-detected as '{detected_type}' with medium confidence. "
                f"If results seem incorrect, try specifying psd_type explicitly.",
                UserWarning
            )
        # High confidence: no warning

    # Cross-sectional area × number concentration (scaled to Mm⁻¹)
    # π/4 * Dp² * N * 1e-6 (nm² to Mm⁻¹ conversion)
    cross_section_area = np.pi * (diameter / 2)**2 * number_conc * 1e-6

    # Get or calculate Mie efficiencies
    if precomputed_Q:
        Q_ext, Q_sca = precomputed_Q
    else:
        Q_ext, Q_sca = calculate_mie_efficiencies(
            refractive_index, wavelength, diameter
        )

    # === Integrate over size distribution ===
    if multi_ri_per_psd:
        # Multiple refractive indices per PSD (for RI retrieval)
        n_times = len(psd)
        n_ri = len(refractive_index)

        # Expand arrays for broadcasting
        area_expanded = np.repeat(
            cross_section_area, n_ri, axis=0
        ).reshape(n_times, n_ri, -1)

        Q_ext_expanded = np.repeat(
            Q_ext[np.newaxis, :, :], n_times, axis=0
        ).reshape(n_times, n_ri, -1)

        Q_sca_expanded = np.repeat(
            Q_sca[np.newaxis, :, :], n_times, axis=0
        ).reshape(n_times, n_ri, -1)

        # Integrate based on psd_type
        integrand_ext = area_expanded * Q_ext_expanded
        integrand_sca = area_expanded * Q_sca_expanded

        if psd_type == 'dNdlogDp':
            log_dp = np.log10(diameter)
            ext_values = trapezoid(integrand_ext, x=log_dp, axis=-1)
            sca_values = trapezoid(integrand_sca, x=log_dp, axis=-1)
        else:  # dN
            ext_values = np.sum(integrand_ext, axis=-1)
            sca_values = np.sum(integrand_sca, axis=-1)

        extinction = pd.DataFrame(
            ext_values, columns=refractive_index, index=psd.index
        ).astype(float)

        scattering = pd.DataFrame(
            sca_values, columns=refractive_index, index=psd.index
        ).astype(float)

        absorption = extinction - scattering

        return {'ext': extinction, 'sca': scattering, 'abs': absorption}

    else:
        # Standard mode: one RI per time point
        integrand_ext = Q_ext * cross_section_area
        integrand_sca = Q_sca * cross_section_area

        result = pd.DataFrame(index=psd.index)
        result['ext'] = _integrate_psd(integrand_ext, diameter, psd_type).astype(float)
        result['sca'] = _integrate_psd(integrand_sca, diameter, psd_type).astype(float)
        result['abs'] = result['ext'] - result['sca']

        return result


# =============================================================================
# Additional Functions: Distribution, Mass Efficiency, Mixing Models
# =============================================================================

def calculate_extinction_distribution(
    refractive_index: complex | np.ndarray,
    wavelength: float,
    diameter: np.ndarray,
    number_conc: np.ndarray,
) -> dict[str, np.ndarray]:
    """
    Calculate extinction/scattering/absorption distribution per size bin.

    Unlike Mie_SD which integrates over all sizes, this function returns
    the contribution from each size bin (dExt/dlogDp).

    Parameters
    ----------
    refractive_index : complex or np.ndarray
        Complex refractive index. Can be:
        - Single complex value (applied to all)
        - Array of complex values (one per row of number_conc)
    wavelength : float
        Wavelength of incident light in nm.
    diameter : np.ndarray
        Particle diameters in nm. Shape: (n_bins,)
    number_conc : np.ndarray
        Number concentration (dN/dlogDp). Shape: (n_bins,) or (n_times, n_bins)

    Returns
    -------
    dict
        Dictionary with keys:
        - 'ext': Extinction distribution (dExt/dlogDp) in Mm⁻¹
        - 'sca': Scattering distribution (dSca/dlogDp) in Mm⁻¹
        - 'abs': Absorption distribution (dAbs/dlogDp) in Mm⁻¹
        - 'diameter': Particle diameters (nm)

    Examples
    --------
    >>> dp = np.logspace(1, 3, 50)
    >>> ndp = np.random.rand(50) * 1000
    >>> m = complex(1.5, 0.02)
    >>> dist = calculate_extinction_distribution(m, 550, dp, ndp)
    >>> print(dist['ext'].shape)  # (50,)

    Notes
    -----
    Output is in dExt/dlogDp units. To get total extinction:
        total_ext = np.trapz(dist['ext'], np.log10(diameter))
    """
    # Handle input dimensions
    number_conc = np.atleast_2d(number_conc)
    if number_conc.shape[1] != len(diameter):
        number_conc = number_conc.T

    n_times = number_conc.shape[0]

    # Handle refractive index
    if isinstance(refractive_index, complex):
        ri_array = np.array([refractive_index] * n_times)
    else:
        ri_array = np.atleast_1d(refractive_index)
        if len(ri_array) == 1:
            ri_array = np.array([ri_array[0]] * n_times)

    # Calculate Mie efficiencies
    Q_ext, Q_sca = calculate_mie_efficiencies(ri_array, wavelength, diameter)

    # Cross-sectional area (π/4 * Dp²) in nm², scaled to Mm⁻¹
    cross_section = np.pi / 4 * diameter**2 * 1e-6

    # Calculate distributions: dX/dlogDp = Q * (π/4 * Dp²) * dN/dlogDp
    # Q_ext shape: (n_times, n_bins), cross_section shape: (n_bins,)
    # number_conc shape: (n_times, n_bins)
    ext_dist = Q_ext * cross_section * number_conc  # (n_times, n_bins)
    sca_dist = Q_sca * cross_section * number_conc

    abs_dist = ext_dist - sca_dist

    return {
        'ext': ext_dist.squeeze(),
        'sca': sca_dist.squeeze(),
        'abs': abs_dist.squeeze(),
        'diameter': diameter
    }


def calculate_mass_efficiency(
    refractive_index: complex,
    wavelength: float,
    diameter: np.ndarray,
    density: float
) -> dict[str, np.ndarray]:
    """
    Calculate mass extinction/scattering/absorption efficiency (MEE/MSE/MAE).

    Parameters
    ----------
    refractive_index : complex
        Complex refractive index (n + ik).
    wavelength : float
        Wavelength of incident light in nm.
    diameter : np.ndarray
        Particle diameters in nm.
    density : float
        Particle density in g/cm³.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'MEE': Mass extinction efficiency (m²/g)
        - 'MSE': Mass scattering efficiency (m²/g)
        - 'MAE': Mass absorption efficiency (m²/g)
        - 'diameter': Particle diameters (nm)

    Examples
    --------
    >>> dp = np.logspace(1, 3, 50)
    >>> result = calculate_mass_efficiency(
    ...     complex(1.5, 0.02), wavelength=550, diameter=dp, density=1.5
    ... )
    >>> print(f"MEE at 100nm: {result['MEE'][25]:.2f} m²/g")

    Notes
    -----
    MEE = (3/2) * Q / (ρ * Dp) * 1000

    Where:
    - Q: Mie efficiency
    - ρ: particle density (g/cm³)
    - Dp: particle diameter (nm)
    - Factor 1000 converts to m²/g
    """
    # Calculate Q for single refractive index
    ri_array = np.array([refractive_index])
    Q_ext, Q_sca = calculate_mie_efficiencies(ri_array, wavelength, diameter)
    # Q_ext shape: (1, n_bins), extract first row to get (n_bins,)

    # MEE = 3Q / (2ρDp) * 1000
    # Factor breakdown: 3/(2*ρ*Dp) where Dp in nm, ρ in g/cm³
    # Multiply by 1000 to get m²/g
    factor = 3 / (2 * density * diameter) * 1000

    MEE = Q_ext[0, :] * factor  # shape: (n_bins,)
    MSE = Q_sca[0, :] * factor
    MAE = MEE - MSE

    return {
        'MEE': MEE,
        'MSE': MSE,
        'MAE': MAE,
        'diameter': diameter
    }


# =============================================================================
# Mixing Models for Multi-Component Aerosols
# =============================================================================

# Default refractive indices for common aerosol species at 550 nm
DEFAULT_REFRACTIVE_INDICES = {
    'AS': complex(1.53, 0.00),      # Ammonium Sulfate
    'AN': complex(1.55, 0.00),      # Ammonium Nitrate
    'OM': complex(1.54, 0.00),      # Organic Matter
    'Soil': complex(1.56, 0.01),    # Soil/Dust
    'SS': complex(1.54, 0.00),      # Sea Salt
    'EC': complex(1.80, 0.54),      # Elemental Carbon
    'ALWC': complex(1.33, 0.00),    # Aerosol Liquid Water Content
}


def internal_mixing(
    psd: pd.DataFrame,
    refractive_index: pd.DataFrame | pd.Series,
    wavelength: float = 550,
    psd_type: str = 'auto',
) -> pd.DataFrame:
    """
    Calculate optical properties using internal mixing model.

    In internal mixing, all species are homogeneously mixed within each
    particle. The effective refractive index is the volume-weighted average.

    Parameters
    ----------
    psd : pd.DataFrame
        Particle size distribution.
        Columns: particle diameters (nm)
        Rows: time points
    refractive_index : pd.DataFrame or pd.Series
        Complex refractive index for each time point.
        Should have columns 'n' and 'k', or be complex values directly.
    wavelength : float, default=550
        Wavelength of incident light in nm.
    psd_type : str, default='auto'
        Type of PSD input:
        - 'dNdlogDp': Number concentration per log bin width (#/cm³)
        - 'dN': Number concentration per bin (#/cm³/bin)
        - 'auto': Auto-detect with warning if uncertain

    Returns
    -------
    pd.DataFrame
        Optical coefficients with columns: ext, sca, abs (Mm⁻¹)

    Examples
    --------
    >>> # PSD data
    >>> dp = np.logspace(1, 3, 50)
    >>> psd = pd.DataFrame(np.random.rand(10, 50) * 1000, columns=dp)
    >>>
    >>> # Refractive index (volume-weighted average)
    >>> ri = pd.DataFrame({'n': [1.52]*10, 'k': [0.01]*10})
    >>> result = internal_mixing(psd, ri, psd_type='dNdlogDp')
    """
    # Convert RI to complex array
    if isinstance(refractive_index, pd.DataFrame):
        if 'n' in refractive_index.columns and 'k' in refractive_index.columns:
            ri_array = (refractive_index['n'] + 1j * refractive_index['k']).values
        else:
            ri_array = refractive_index.iloc[:, 0].values
    else:
        ri_array = np.array(refractive_index)

    # Use standard Mie_SD calculation
    return Mie_SD(ri_array, wavelength, psd, psd_type=psd_type)


def external_mixing(
    psd: pd.DataFrame,
    volume_fractions: pd.DataFrame,
    wavelength: float = 550,
    refractive_indices: dict = None,
    psd_type: str = 'auto',
) -> pd.DataFrame:
    """
    Calculate optical properties using external mixing model.

    In external mixing, each species exists as separate particles.
    The total optical property is the sum of contributions from each species.

    Parameters
    ----------
    psd : pd.DataFrame
        Total particle size distribution.
        Columns: particle diameters (nm)
        Rows: time points
    volume_fractions : pd.DataFrame
        Volume fraction of each species. Columns should include:
        AS, AN, OM, Soil, SS, EC, (optional: ALWC)
    wavelength : float, default=550
        Wavelength of incident light in nm.
    refractive_indices : dict, optional
        Custom refractive indices for species. Default uses standard values.
    psd_type : str, default='auto'
        Type of PSD input:
        - 'dNdlogDp': Number concentration per log bin width (#/cm³)
        - 'dN': Number concentration per bin (#/cm³/bin)
        - 'auto': Auto-detect with warning if uncertain

    Returns
    -------
    pd.DataFrame
        Total optical coefficients with columns: ext, sca, abs (Mm⁻¹)

    Examples
    --------
    >>> dp = np.logspace(1, 3, 50)
    >>> psd = pd.DataFrame(np.random.rand(10, 50) * 1000, columns=dp)
    >>> vol_frac = pd.DataFrame({
    ...     'AS': [0.3]*10, 'AN': [0.2]*10, 'OM': [0.3]*10,
    ...     'Soil': [0.05]*10, 'SS': [0.05]*10, 'EC': [0.1]*10
    ... })
    >>> result = external_mixing(psd, vol_frac, psd_type='dNdlogDp')
    """
    if refractive_indices is None:
        refractive_indices = DEFAULT_REFRACTIVE_INDICES.copy()

    diameter = psd.columns.values.astype(float)
    n_times = len(psd)

    # Auto-detect PSD type if needed
    if psd_type == 'auto':
        detected_type, confidence = _detect_psd_type(psd.values, diameter)
        psd_type = detected_type

        if confidence == 'low':
            warnings.warn(
                f"PSD type auto-detection has low confidence. "
                f"Assuming '{detected_type}'. Please specify psd_type explicitly "
                f"('dNdlogDp' or 'dN') to avoid incorrect results.",
                UserWarning
            )
        elif confidence == 'medium':
            warnings.warn(
                f"PSD type auto-detected as '{detected_type}' with medium confidence. "
                f"If results seem incorrect, try specifying psd_type explicitly.",
                UserWarning
            )

    # Initialize result
    total_ext = np.zeros(n_times)
    total_sca = np.zeros(n_times)

    # Check for ALWC correction
    has_alwc = 'ALWC' in volume_fractions.columns
    if has_alwc:
        alwc_factor = 1 / (1 + volume_fractions['ALWC'].values)
    else:
        alwc_factor = np.ones(n_times)

    # Calculate contribution from each species
    for species, ri in refractive_indices.items():
        if species not in volume_fractions.columns:
            continue
        if species == 'ALWC':
            continue  # ALWC is handled separately

        vol_frac = volume_fractions[species].values

        # Species PSD = total PSD × volume fraction (with ALWC correction)
        species_psd = psd.values * (vol_frac * alwc_factor).reshape(-1, 1)

        # Calculate Mie for this species (single RI for all times)
        ri_array = np.array([ri] * n_times)
        Q_ext, Q_sca = calculate_mie_efficiencies(ri_array, wavelength, diameter)
        # Q_ext shape: (n_times, n_bins)

        # Cross-sectional area
        cross_section = np.pi * (diameter / 2)**2 * 1e-6  # shape: (n_bins,)

        # Integrate over diameter bins
        # species_psd shape: (n_times, n_bins)
        integrand_ext = Q_ext * cross_section * species_psd  # (n_times, n_bins)
        integrand_sca = Q_sca * cross_section * species_psd
        total_ext += _integrate_psd(integrand_ext, diameter, psd_type)
        total_sca += _integrate_psd(integrand_sca, diameter, psd_type)

    # Build result DataFrame
    result = pd.DataFrame(index=psd.index)
    result['ext'] = total_ext.astype(float)
    result['sca'] = total_sca.astype(float)
    result['abs'] = (total_ext - total_sca).astype(float)

    return result


def generate_lognormal_psd(
    geometric_mean: float = 200,
    geometric_std: float = 2.0,
    total_number: float = 1e6,
    dp_range: tuple = (1, 2500),
    n_bins: int = 167,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate a lognormal particle size distribution.

    Parameters
    ----------
    geometric_mean : float, default=200
        Geometric mean diameter in nm.
    geometric_std : float, default=2.0
        Geometric standard deviation.
    total_number : float, default=1e6
        Total number concentration (#/cm³).
    dp_range : tuple, default=(1, 2500)
        Diameter range (min, max) in nm.
    n_bins : int, default=167
        Number of size bins.

    Returns
    -------
    diameter : np.ndarray
        Particle diameters in nm.
    ndp : np.ndarray
        Number concentration (dN/dlogDp).

    Examples
    --------
    >>> dp, ndp = generate_lognormal_psd(geometric_mean=100, geometric_std=1.8)
    >>> print(f"Peak at {dp[np.argmax(ndp)]:.1f} nm")
    """
    diameter = np.logspace(np.log10(dp_range[0]), np.log10(dp_range[1]), n_bins)

    # Lognormal distribution: dN/dlogDp
    log_sigma = np.log(geometric_std)
    log_dp = np.log(diameter)
    log_mean = np.log(geometric_mean)

    ndp = total_number * (
        1 / (log_sigma * np.sqrt(2 * np.pi)) *
        np.exp(-(log_dp - log_mean)**2 / (2 * log_sigma**2))
    )

    return diameter, ndp


# =============================================================================
# Backward Compatibility Aliases
# =============================================================================

MieQ = calculate_mie_efficiencies
Mie_ab = calculate_mie_coefficients
Mie_PESD = calculate_extinction_distribution
Mie_MEE = calculate_mass_efficiency
