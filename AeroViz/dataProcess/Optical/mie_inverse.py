# -*- coding: utf-8 -*-
"""
Inverse Mie Problem Solvers — Retrieve Refractive Index from Optical Measurements

This module implements two complementary approaches to the aerosol inverse
Mie problem: given measured bulk optical coefficients (extinction Bext,
scattering Bsca, absorption Babs) and a known particle size distribution,
recover the complex refractive index ``m = n + ik``.

Approaches
----------
1. **Newton-Raphson style iterative inversion** (``iterative_inversion`` /
   ``iterative_inversion_sd``) — uses ``scipy.optimize.least_squares`` to
   minimise the residual between predicted and measured optical
   coefficients. Fast and accurate when a reasonable starting guess is
   available.

2. **Contour intersection method** (``contour_intersection``) — evaluates
   the forward Mie problem on a coarse (n, k) grid, extracts a contour
   for each measurement where predicted equals measured, and returns the
   intersection of these contours as the retrieved RI. More robust to
   poor initial guesses but limited by grid resolution.

This is a Python port (and small refactor) of the inverse module
distributed with PyMieScatt.

References
----------
Sumlin, B. J., Heinson, W. R., & Chakrabarty, R. K. (2018). Retrieving
the aerosol complex refractive index using PyMieScatt: A survey of
radiative properties of secondary organic aerosol aged in the presence
of NO\\ :sub:`x`. *Journal of Quantitative Spectroscopy and Radiative
Transfer*, 205, 127–134. https://doi.org/10.1016/j.jqsrt.2017.10.012

See Also
--------
AeroViz.dataProcess.Optical.mie : Forward Mie problem.
AeroViz.dataProcess.Optical._retrieve_RI : Two-stage grid-search RI
    retrieval (legacy approach).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from .mie import Mie_SD, mie_lognormal

__all__ = [
    'iterative_inversion',
    'iterative_inversion_sd',
    'contour_intersection',
]


# =============================================================================
# Internal helpers
# =============================================================================

def _validate_measurements(
    b_ext: float | None,
    b_sca: float | None,
    b_abs: float | None,
) -> tuple[list[str], np.ndarray]:
    """Validate the input measurements and return the list of active
    quantities plus their numeric values.

    At least two of ``(b_ext, b_sca, b_abs)`` must be supplied (a finite,
    non-NaN float). ``None``, ``NaN`` and ``inf`` are all treated as
    "missing".

    Parameters
    ----------
    b_ext, b_sca, b_abs : float or None
        Measured extinction, scattering and absorption coefficients
        (Mm⁻¹).

    Returns
    -------
    keys : list[str]
        The active measurement names, in canonical order
        ``['ext', 'sca', 'abs']``.
    values : np.ndarray
        The numeric values for each active measurement (same order).

    Raises
    ------
    ValueError
        If fewer than two valid measurements are provided.
    """
    keys: list[str] = []
    values: list[float] = []
    for name, val in (('ext', b_ext), ('sca', b_sca), ('abs', b_abs)):
        if val is None:
            continue
        try:
            f = float(val)
        except (TypeError, ValueError):
            continue
        if not np.isfinite(f):
            continue
        keys.append(name)
        values.append(f)

    if len(keys) < 2:
        raise ValueError(
            f"At least two of (b_ext, b_sca, b_abs) must be provided as "
            f"finite floats; got {len(keys)} valid measurement(s)."
        )
    return keys, np.asarray(values, dtype=float)


def _validate_lognormal_params(params: dict) -> dict:
    """Validate the lognormal-PSD parameter dict and return a clean copy.

    Required keys: ``geo_mean`` (nm), ``geo_std`` (dimensionless),
    ``total_number`` (#/cm³).
    """
    if not isinstance(params, dict):
        raise ValueError(
            "lognormal_params must be a dict with keys "
            "'geo_mean', 'geo_std', 'total_number'."
        )
    required = {'geo_mean', 'geo_std', 'total_number'}
    missing = required - set(params)
    if missing:
        raise ValueError(
            f"lognormal_params is missing required key(s): {sorted(missing)}. "
            f"Expected {sorted(required)}."
        )
    out = {
        'geo_mean': float(params['geo_mean']),
        'geo_std': float(params['geo_std']),
        'total_number': float(params['total_number']),
    }
    if out['geo_mean'] <= 0 or out['geo_std'] <= 1 or out['total_number'] <= 0:
        raise ValueError(
            "lognormal_params must satisfy geo_mean > 0, geo_std > 1, "
            f"total_number > 0; got {out}."
        )
    return out


def _forward_lognormal(
    n: float,
    k: float,
    lognormal_params: dict,
    wavelength: float,
) -> dict:
    """Run the forward Mie problem for a single (n, k) on a lognormal
    PSD. Returns a dict with keys ``ext``, ``sca``, ``abs`` (Mm⁻¹)."""
    m = complex(n, k)
    return mie_lognormal(m, wavelength, **lognormal_params)


def _forward_sd(
    n: float,
    k: float,
    dp: np.ndarray,
    ndp: np.ndarray,
    wavelength: float,
) -> dict:
    """Run the forward Mie problem for a single (n, k) on an explicit
    size distribution (``dp``, ``ndp``). Returns a dict with keys
    ``ext``, ``sca``, ``abs`` (Mm⁻¹)."""
    m = complex(n, k)
    psd = pd.DataFrame([ndp], columns=dp)
    result = Mie_SD(np.array([m]), wavelength, psd, psd_type='dNdlogDp')
    return {
        'ext': float(result['ext'].iloc[0]),
        'sca': float(result['sca'].iloc[0]),
        'abs': float(result['abs'].iloc[0]),
    }


def _residual_factory(
    forward_fn,
    keys: list[str],
    measured: np.ndarray,
):
    """Build a residual function ``f(params) -> residuals`` for
    ``scipy.optimize.least_squares``.

    The residuals are normalised by the magnitude of the measured value
    (with a small floor) so the optimiser weights all measurements
    similarly regardless of their absolute scale.
    """
    scale = np.maximum(np.abs(measured), 1e-12)

    def _residuals(params: np.ndarray) -> np.ndarray:
        n, k = params
        # Clip k to be non-negative — non-physical otherwise.
        k = max(k, 0.0)
        forward = forward_fn(n, k)
        predicted = np.array([forward[key] for key in keys], dtype=float)
        return (predicted - measured) / scale

    return _residuals


def _run_least_squares(
    forward_fn,
    keys: list[str],
    measured: np.ndarray,
    n_initial: float,
    k_initial: float,
) -> dict:
    """Drive ``scipy.optimize.least_squares`` and package the result.

    Returns a dict with keys ``n``, ``k``, ``iterations``, ``converged``,
    ``residuals``.
    """
    residual_fn = _residual_factory(forward_fn, keys, measured)

    # Bounds: n in [1.0, 3.0] (physical), k in [0, 1.5] (broad upper
    # bound that comfortably covers BC and all aerosol-relevant species).
    bounds = ([1.0, 0.0], [3.0, 1.5])

    x0 = np.array([n_initial, max(k_initial, 1e-6)], dtype=float)

    try:
        result = least_squares(
            residual_fn,
            x0,
            bounds=bounds,
            method='trf',
            xtol=1e-10,
            ftol=1e-10,
            gtol=1e-10,
        )
    except Exception as exc:  # pragma: no cover - safeguard
        raise RuntimeError(
            f"least_squares solver failed to evaluate the residual: {exc}"
        ) from exc

    converged = bool(result.success) and (
        np.max(np.abs(result.fun)) < 1e-3
    )

    # Re-compute the (un-normalised) residuals on the absolute scale so
    # the caller can inspect them directly.
    n_final = float(result.x[0])
    k_final = float(max(result.x[1], 0.0))
    forward_final = forward_fn(n_final, k_final)
    abs_residuals = {
        key: float(forward_final[key] - val)
        for key, val in zip(keys, measured)
    }

    if not converged:
        raise RuntimeError(
            f"Iterative inversion failed to converge. "
            f"status={result.status}, message='{result.message}', "
            f"final residuals (Mm⁻¹)={abs_residuals}, "
            f"final (n, k)=({n_final:.4f}, {k_final:.4f})."
        )

    return {
        'n': n_final,
        'k': k_final,
        'iterations': int(result.nfev),
        'converged': converged,
        'residuals': abs_residuals,
    }


# =============================================================================
# Public API: iterative inversion (lognormal PSD)
# =============================================================================

def iterative_inversion(
    b_ext: float | None,
    b_sca: float | None,
    b_abs: float | None,
    lognormal_params: dict,
    wavelength: float = 550,
    n_initial: float = 1.5,
    k_initial: float = 0.01,
) -> dict:
    """
    Retrieve the complex refractive index from bulk optical measurements
    using Newton-Raphson style iterative inversion (least-squares).

    Given measured bulk coefficients ``(Bext, Bsca, Babs)`` and a known
    lognormal particle size distribution, this function finds the
    ``m = n + ik`` whose forward Mie prediction best matches the
    measurements. At least two of the three optical coefficients must be
    provided.

    Parameters
    ----------
    b_ext : float or None
        Measured extinction coefficient (Mm⁻¹). Use ``None`` (or
        ``NaN``) to omit.
    b_sca : float or None
        Measured scattering coefficient (Mm⁻¹).
    b_abs : float or None
        Measured absorption coefficient (Mm⁻¹).
    lognormal_params : dict
        Lognormal-PSD parameters with keys ``geo_mean`` (nm),
        ``geo_std`` (dimensionless), and ``total_number`` (#/cm³).
    wavelength : float, default 550
        Wavelength of incident light in nm.
    n_initial : float, default 1.5
        Initial guess for the real part of the refractive index.
    k_initial : float, default 0.01
        Initial guess for the imaginary part of the refractive index.

    Returns
    -------
    dict
        Result dictionary with the following keys:

        * ``n``         — retrieved real refractive index component
        * ``k``         — retrieved imaginary refractive index component
        * ``iterations`` — number of function evaluations performed
        * ``converged`` — bool, ``True`` if the solver met the
          convergence tolerance
        * ``residuals`` — dict mapping each provided measurement key
          (``'ext'``, ``'sca'``, ``'abs'``) to its final residual
          (predicted − measured), in Mm⁻¹

    Raises
    ------
    ValueError
        If fewer than two valid measurements are provided, or if
        ``lognormal_params`` is malformed.
    RuntimeError
        If the solver fails to converge within tolerance.

    Notes
    -----
    Uses ``scipy.optimize.least_squares`` with the Trust Region
    Reflective algorithm and physical bounds ``n ∈ [1.0, 3.0]``,
    ``k ∈ [0, 1.5]``. Residuals are normalised by the measurement
    magnitude so the optimiser treats all measurements with comparable
    weight regardless of their absolute scale.

    Examples
    --------
    >>> from AeroViz.dataProcess.Optical.mie import mie_lognormal
    >>> lognormal = {'geo_mean': 200, 'geo_std': 2.0, 'total_number': 1e4}
    >>> ref = mie_lognormal(complex(1.55, 0.02), 550, **lognormal)
    >>> out = iterative_inversion(ref['ext'], ref['sca'], ref['abs'],
    ...                            lognormal, wavelength=550)
    >>> round(out['n'], 3), round(out['k'], 3)
    (1.55, 0.02)
    """
    keys, measured = _validate_measurements(b_ext, b_sca, b_abs)
    params = _validate_lognormal_params(lognormal_params)

    def forward(n: float, k: float) -> dict:
        return _forward_lognormal(n, k, params, wavelength)

    return _run_least_squares(forward, keys, measured, n_initial, k_initial)


# =============================================================================
# Public API: iterative inversion (explicit size distribution)
# =============================================================================

def iterative_inversion_sd(
    b_ext: float | None,
    b_sca: float | None,
    b_abs: float | None,
    dp: np.ndarray,
    ndp: np.ndarray,
    wavelength: float = 550,
    n_initial: float = 1.5,
    k_initial: float = 0.01,
) -> dict:
    """
    Retrieve the complex refractive index from bulk optical measurements
    using Newton-Raphson style iterative inversion, with an explicitly
    supplied particle size distribution.

    Same approach as :func:`iterative_inversion` but accepts a measured
    PSD (``dp``, ``ndp``) instead of lognormal parameters. Useful when
    real SMPS / APS data is available and a parametric fit isn't
    appropriate.

    Parameters
    ----------
    b_ext : float or None
        Measured extinction coefficient (Mm⁻¹). Use ``None`` (or
        ``NaN``) to omit.
    b_sca : float or None
        Measured scattering coefficient (Mm⁻¹).
    b_abs : float or None
        Measured absorption coefficient (Mm⁻¹).
    dp : np.ndarray
        Particle diameters in nm. Shape ``(n_bins,)``.
    ndp : np.ndarray
        Number concentration ``dN/dlogDp`` for each diameter bin
        (#/cm³). Same length as ``dp``.
    wavelength : float, default 550
        Wavelength of incident light in nm.
    n_initial : float, default 1.5
        Initial guess for the real part of the refractive index.
    k_initial : float, default 0.01
        Initial guess for the imaginary part of the refractive index.

    Returns
    -------
    dict
        Same shape as :func:`iterative_inversion` — keys ``n``, ``k``,
        ``iterations``, ``converged``, ``residuals``.

    Raises
    ------
    ValueError
        If fewer than two valid measurements are provided, or ``dp`` and
        ``ndp`` have mismatched / empty shapes.
    RuntimeError
        If the solver fails to converge within tolerance.

    Examples
    --------
    >>> from AeroViz.dataProcess.Optical.mie import generate_lognormal_psd, Mie_SD
    >>> dp, ndp = generate_lognormal_psd(geometric_mean=200, geometric_std=2.0,
    ...                                  total_number=1e4)
    >>> import pandas as pd, numpy as np
    >>> psd = pd.DataFrame([ndp], columns=dp)
    >>> ref = Mie_SD(np.array([complex(1.55, 0.02)]), 550, psd,
    ...              psd_type='dNdlogDp').iloc[0]
    >>> out = iterative_inversion_sd(ref['ext'], ref['sca'], ref['abs'],
    ...                               dp, ndp, wavelength=550)
    >>> round(out['n'], 3), round(out['k'], 3)
    (1.55, 0.02)
    """
    keys, measured = _validate_measurements(b_ext, b_sca, b_abs)

    dp = np.asarray(dp, dtype=float)
    ndp = np.asarray(ndp, dtype=float)
    if dp.ndim != 1 or ndp.ndim != 1:
        raise ValueError(
            f"dp and ndp must be 1-D arrays; got shapes {dp.shape} and "
            f"{ndp.shape}."
        )
    if dp.size == 0 or dp.size != ndp.size:
        raise ValueError(
            f"dp and ndp must have matching, non-empty length; got "
            f"{dp.size} and {ndp.size}."
        )

    def forward(n: float, k: float) -> dict:
        return _forward_sd(n, k, dp, ndp, wavelength)

    return _run_least_squares(forward, keys, measured, n_initial, k_initial)


# =============================================================================
# Public API: contour intersection
# =============================================================================

def _extract_zero_contour(
    n_grid: np.ndarray,
    k_grid: np.ndarray,
    field: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract the zero-level contour from a 2-D scalar field defined on
    a grid ``(n_grid, k_grid)`` indexed as ``field[i, j]`` with
    ``i`` over ``n_grid`` and ``j`` over ``k_grid``.

    We scan each row and column for sign changes and linearly interpolate
    to find the zero crossing — a lightweight stand-in for
    ``skimage.measure.find_contours`` that avoids an extra dependency.

    Returns
    -------
    n_contour : np.ndarray
        ``n`` coordinates of points on the zero contour.
    k_contour : np.ndarray
        Corresponding ``k`` coordinates.
    """
    n_pts: list[float] = []
    k_pts: list[float] = []

    # Sign-change scan along k (within each fixed n row)
    for i in range(field.shape[0]):
        row = field[i, :]
        signs = np.sign(row)
        # Treat exact zeros as positive so they're not duplicated.
        signs = np.where(signs == 0, 1, signs)
        changes = np.where(np.diff(signs) != 0)[0]
        for j in changes:
            f1, f2 = row[j], row[j + 1]
            if f1 == f2:
                continue
            t = f1 / (f1 - f2)
            k_cross = k_grid[j] + t * (k_grid[j + 1] - k_grid[j])
            n_pts.append(n_grid[i])
            k_pts.append(k_cross)

    # Sign-change scan along n (within each fixed k column)
    for j in range(field.shape[1]):
        col = field[:, j]
        signs = np.sign(col)
        signs = np.where(signs == 0, 1, signs)
        changes = np.where(np.diff(signs) != 0)[0]
        for i in changes:
            f1, f2 = col[i], col[i + 1]
            if f1 == f2:
                continue
            t = f1 / (f1 - f2)
            n_cross = n_grid[i] + t * (n_grid[i + 1] - n_grid[i])
            n_pts.append(n_cross)
            k_pts.append(k_grid[j])

    return np.asarray(n_pts, dtype=float), np.asarray(k_pts, dtype=float)


def _intersect_contours(
    contours: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[float, float]:
    """Find the (n, k) point that minimises the total distance to all
    contour-point sets.

    For each pair of contours we locate the pair of closest points (one
    from each) and take their midpoint as a candidate intersection.
    With more than two contours we average the candidate from each pair.

    Returns
    -------
    n, k : float
        Best-estimate intersection coordinates.
    """
    if len(contours) < 2:
        raise ValueError("Need at least two contours to compute an intersection.")

    candidates: list[tuple[float, float]] = []
    for i in range(len(contours)):
        for j in range(i + 1, len(contours)):
            n_a, k_a = contours[i]
            n_b, k_b = contours[j]
            if n_a.size == 0 or n_b.size == 0:
                continue
            # Pairwise distance matrix (broadcast).
            d2 = (n_a[:, None] - n_b[None, :]) ** 2 + (k_a[:, None] - k_b[None, :]) ** 2
            ia, ib = np.unravel_index(np.argmin(d2), d2.shape)
            candidates.append((
                0.5 * (n_a[ia] + n_b[ib]),
                0.5 * (k_a[ia] + k_b[ib]),
            ))

    if not candidates:
        raise RuntimeError(
            "Unable to locate a contour intersection — none of the "
            "supplied contours have points. Try a wider (n_range, "
            "k_range) or a finer grid."
        )

    arr = np.asarray(candidates, dtype=float)
    return float(arr[:, 0].mean()), float(arr[:, 1].mean())


def contour_intersection(
    b_ext: float | None,
    b_sca: float | None,
    b_abs: float | None,
    lognormal_params: dict,
    wavelength: float = 550,
    n_range: tuple = (1.3, 2.0),
    k_range: tuple = (0.0, 0.5),
    grid: int = 51,
) -> dict:
    """
    Retrieve the complex refractive index by intersecting iso-measurement
    contours in (n, k) space.

    The forward Mie problem is evaluated on a ``grid × grid`` mesh of
    ``(n, k)`` values. For each supplied measurement we extract the
    zero-level contour of ``(predicted − measured)`` — every point on
    this curve is an ``(n, k)`` that reproduces that single measurement.
    The intersection of two (or three) such curves is the retrieved
    refractive index.

    Parameters
    ----------
    b_ext : float or None
        Measured extinction coefficient (Mm⁻¹). At least two of the
        three must be supplied.
    b_sca : float or None
        Measured scattering coefficient (Mm⁻¹).
    b_abs : float or None
        Measured absorption coefficient (Mm⁻¹).
    lognormal_params : dict
        Lognormal-PSD parameters with keys ``geo_mean`` (nm),
        ``geo_std`` (dimensionless), and ``total_number`` (#/cm³).
    wavelength : float, default 550
        Wavelength of incident light in nm.
    n_range : tuple, default (1.3, 2.0)
        ``(n_min, n_max)`` search bounds for the real RI.
    k_range : tuple, default (0.0, 0.5)
        ``(k_min, k_max)`` search bounds for the imaginary RI.
    grid : int, default 51
        Number of grid points along each axis. The total number of
        forward-Mie evaluations is ``grid**2``.

    Returns
    -------
    dict
        Result dictionary with the following keys:

        * ``n``, ``k`` — intersection-point estimate of the refractive
          index
        * ``contour_ext``, ``contour_sca``, ``contour_abs`` — dicts with
          keys ``n_contour`` and ``k_contour`` (arrays describing the
          iso-measurement contour). Entries are ``None`` for any
          measurement that was not supplied.

    Raises
    ------
    ValueError
        If fewer than two valid measurements are provided, or
        ``lognormal_params`` is malformed, or ``grid < 3``.
    RuntimeError
        If no contour intersection can be located within the search
        window.

    Notes
    -----
    Accuracy is bounded by the grid resolution: typical absolute error
    is on the order of ``(n_range_width + k_range_width) / grid``. For a
    high-precision answer, follow this method with
    :func:`iterative_inversion` using the contour-intersection result as
    the initial guess.

    Examples
    --------
    >>> from AeroViz.dataProcess.Optical.mie import mie_lognormal
    >>> lognormal = {'geo_mean': 200, 'geo_std': 2.0, 'total_number': 1e4}
    >>> ref = mie_lognormal(complex(1.55, 0.02), 550, **lognormal)
    >>> out = contour_intersection(ref['ext'], ref['sca'], ref['abs'],
    ...                             lognormal, wavelength=550)
    >>> abs(out['n'] - 1.55) < 0.05, abs(out['k'] - 0.02) < 0.05
    (True, True)
    """
    if grid < 3:
        raise ValueError(f"grid must be >= 3; got {grid}.")
    if n_range[0] >= n_range[1] or k_range[0] >= k_range[1]:
        raise ValueError(
            f"n_range and k_range must each be (low, high) with low < high; "
            f"got n_range={n_range}, k_range={k_range}."
        )

    keys, measured = _validate_measurements(b_ext, b_sca, b_abs)
    params = _validate_lognormal_params(lognormal_params)

    n_grid = np.linspace(n_range[0], n_range[1], grid)
    k_grid = np.linspace(k_range[0], k_range[1], grid)

    # Evaluate the forward Mie problem on the full mesh in a single
    # vectorised call by handing the entire complex-RI array to
    # mie_lognormal via Mie_SD (multi_ri_per_psd).
    from .mie import generate_lognormal_psd  # local import keeps API tidy

    dp, ndp = generate_lognormal_psd(
        geometric_mean=params['geo_mean'],
        geometric_std=params['geo_std'],
        total_number=params['total_number'],
    )
    psd = pd.DataFrame([ndp], columns=dp)

    # Build flat array of complex RIs covering the whole grid.
    nn, kk = np.meshgrid(n_grid, k_grid, indexing='ij')
    ri_flat = (nn + 1j * kk).reshape(-1)

    multi = Mie_SD(
        ri_flat, wavelength, psd, psd_type='dNdlogDp',
        multi_ri_per_psd=True,
    )
    # multi['ext'] is a DataFrame with one row (the single PSD) and one
    # column per RI; pull the values out and reshape onto the grid.
    ext_field = multi['ext'].values.reshape(grid, grid)
    sca_field = multi['sca'].values.reshape(grid, grid)
    abs_field = multi['abs'].values.reshape(grid, grid)

    field_map = {'ext': ext_field, 'sca': sca_field, 'abs': abs_field}
    measured_map = dict(zip(keys, measured))

    contours: list[tuple[np.ndarray, np.ndarray]] = []
    contour_results: dict[str, dict | None] = {
        'contour_ext': None,
        'contour_sca': None,
        'contour_abs': None,
    }

    for key in ('ext', 'sca', 'abs'):
        if key not in measured_map:
            continue
        residual_field = field_map[key] - measured_map[key]
        n_c, k_c = _extract_zero_contour(n_grid, k_grid, residual_field)
        if n_c.size == 0:
            # No zero crossing inside the window — skip but warn the
            # user via the contour entry.
            contour_results[f'contour_{key}'] = {
                'n_contour': n_c, 'k_contour': k_c,
            }
            continue
        contour_results[f'contour_{key}'] = {
            'n_contour': n_c, 'k_contour': k_c,
        }
        contours.append((n_c, k_c))

    if len(contours) < 2:
        raise RuntimeError(
            "Could not extract zero contours for at least two "
            "measurements within the (n_range, k_range) window. Widen "
            "the search range or increase 'grid'."
        )

    n_est, k_est = _intersect_contours(contours)

    return {
        'n': n_est,
        'k': k_est,
        **contour_results,
    }
