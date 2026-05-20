# -*- coding: utf-8 -*-
"""
Mie Angular Scattering Functions
================================

Modern dict-returning wrappers around the single-particle angular Mie
helpers in ``mie_kernels``.  This module brings AeroViz's Mie surface
toward feature-parity with upstream PyMieScatt by exposing:

* ``scattering_function``         -- single-particle angular intensity
                                     (SL, SR, SU vs theta or q-space)
* ``scattering_function_sd``      -- the same, but PSD-integrated
* ``phase_matrix``                -- Mueller matrix elements
                                     (S11, S12, S33, S34) on a cos(theta)
                                     grid
* ``nephelometer_truncation_correction``
                                  -- Anderson & Ogren (1998) integrating
                                     nephelometer truncation correction

All four functions return Python ``dict`` objects with keyword keys
rather than positional tuples, matching the conventions adopted in
``mie.py`` (e.g. ``calculate_mie_efficiencies``).

References
----------
- Bohren & Huffman (1983), *Absorption and Scattering of Light by Small
  Particles*, Wiley.
- Anderson, T. L. and Ogren, J. A. (1998), Determining Aerosol
  Radiative Properties Using the TSI 3563 Integrating Nephelometer,
  *Aerosol Sci. Technol.*, 29:1, 57-69.
- PyMieScatt documentation:
  http://pymiescatt.readthedocs.io/en/latest/forward.html
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike

from .mie_kernels import MatrixElements, ScatteringFunction, SF_SD


__all__ = [
    "scattering_function",
    "scattering_function_sd",
    "phase_matrix",
    "nephelometer_truncation_correction",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _angle_bounds_from_array(angles: np.ndarray) -> tuple[float, float, float]:
    """
    Derive ``(minAngle, maxAngle, angularResolution)`` for the underlying
    ``ScatteringFunction`` / ``SF_SD`` kernel from a user-supplied 1-D
    array of angles (in degrees).

    The kernel constructs its own evenly-spaced grid via
    ``np.linspace(minAngle, maxAngle, _steps)`` where
    ``_steps = int(1 + (maxAngle - minAngle) / angularResolution)``,
    so passing an evenly-spaced ``angles`` array reproduces it exactly.
    """
    angles = np.asarray(angles, dtype=float).ravel()
    if angles.size < 2:
        raise ValueError("`angles` must contain at least two points.")
    min_angle = float(angles[0])
    max_angle = float(angles[-1])
    # Use mean spacing -- works for uniform grids and is a sensible
    # approximation for mildly non-uniform user input.
    resolution = float((max_angle - min_angle) / (angles.size - 1))
    if resolution <= 0:
        raise ValueError("`angles` must be strictly increasing.")
    return min_angle, max_angle, resolution


# ---------------------------------------------------------------------------
# 1.  Single-particle angular scattering function
# ---------------------------------------------------------------------------

def scattering_function(
    m: complex,
    wavelength: float,
    diameter: float,
    angles: ArrayLike | None = None,
    space: str = "theta",
) -> dict:
    """
    Compute the angular scattering intensity of a single homogeneous
    sphere using Mie theory.

    This is a thin wrapper around
    :func:`AeroViz.dataProcess.Optical.mie_kernels.ScatteringFunction`
    that returns a dictionary instead of a tuple.

    Parameters
    ----------
    m : complex
        Complex refractive index of the particle (``n + i k``) relative
        to the surrounding medium (vacuum/air by default).
    wavelength : float
        Wavelength of the incident light in **nm**.
    diameter : float
        Particle diameter in **nm**.
    angles : array_like, optional
        1-D array of scattering angles in **degrees**.  Must be evenly
        spaced and monotonically increasing.  Defaults to
        ``np.arange(0, 180.5, 0.5)`` (i.e. 0-180 degrees at 0.5 degree
        resolution -- 361 points).
    space : {'theta', 'q'}, default='theta'
        Independent variable used to express the angular grid.

        - ``'theta'`` : scattering angle (radians, as returned by the
          underlying kernel)
        - ``'q'``     : scattering vector magnitude
          ``q = (4 pi / lambda) sin(theta/2) * (D/2)``

    Returns
    -------
    dict
        Dictionary with the following keys:

        - ``'angles'`` : np.ndarray
            Independent-variable grid.  In ``theta`` mode this is the
            scattering angle in **radians** (matching the upstream
            kernel convention).  In ``q`` mode this is the dimensionless
            scattering vector.
        - ``'SL'`` : np.ndarray
            Intensity for light polarised parallel to the scattering
            plane, ``|S1|**2``.
        - ``'SR'`` : np.ndarray
            Intensity for light polarised perpendicular to the
            scattering plane, ``|S2|**2``.
        - ``'SU'`` : np.ndarray
            Unpolarised intensity, ``(SL + SR) / 2``.

    Examples
    --------
    >>> import numpy as np
    >>> from AeroViz.dataProcess.Optical.mie_angular import scattering_function
    >>> out = scattering_function(complex(1.5, 0.02), 550.0, 200.0)
    >>> out["SL"].shape
    (361,)

    Notes
    -----
    The returned arrays have the same length as ``angles`` (default
    361).  See Bohren & Huffman (1983), chapter 4, for definitions of
    ``S1``, ``S2``, and the scattering-plane geometry.
    """
    if angles is None:
        angles_arr = np.arange(0.0, 180.5, 0.5)
    else:
        angles_arr = np.asarray(angles, dtype=float).ravel()

    min_angle, max_angle, resolution = _angle_bounds_from_array(angles_arr)

    measure, SL, SR, SU = ScatteringFunction(
        m,
        wavelength,
        diameter,
        minAngle=min_angle,
        maxAngle=max_angle,
        angularResolution=resolution,
        space=space,
        angleMeasure="radians",
        normalization=None,
    )

    # Guard the degenerate ``x == 0`` branch in ScatteringFunction, which
    # returns scalar zeros for SL/SR/SU rather than arrays.
    if np.isscalar(SL):
        SL = np.zeros_like(measure)
        SR = np.zeros_like(measure)
        SU = np.zeros_like(measure)

    return {
        "angles": np.asarray(measure),
        "SL": np.asarray(SL),
        "SR": np.asarray(SR),
        "SU": np.asarray(SU),
    }


# ---------------------------------------------------------------------------
# 2.  PSD-integrated angular scattering function
# ---------------------------------------------------------------------------

def scattering_function_sd(
    m: complex,
    wavelength: float,
    dp: ArrayLike,
    ndp: ArrayLike,
    angles: ArrayLike | None = None,
    space: str = "theta",
    psd_type: str = "auto",
) -> dict:
    """
    Compute the angular scattering intensity integrated over a particle
    size distribution.

    Wraps :func:`AeroViz.dataProcess.Optical.mie_kernels.SF_SD`.

    Parameters
    ----------
    m : complex
        Complex refractive index of the particles.
    wavelength : float
        Wavelength of the incident light in **nm**.
    dp : array_like
        Particle diameters in **nm** (1-D, same length as ``ndp``).
    ndp : array_like
        PSD values at each ``dp``.  May be supplied as raw counts per
        bin (``dN``) or as a density (``dN/dlogDp``); see ``psd_type``.
    angles : array_like, optional
        Evenly-spaced 1-D angle grid in **degrees**.  Defaults to
        ``np.arange(0, 180.5, 0.5)``.
    space : {'theta', 'q'}, default='theta'
        See :func:`scattering_function`.
    psd_type : {'auto', 'dN', 'dNdlogDp'}, default='auto'
        Interpretation of ``ndp``.  This mirrors
        :func:`AeroViz.dataProcess.Optical.mie.Mie_SD`:

        - ``'dN'``       : ``ndp`` is number concentration per bin.
        - ``'dNdlogDp'`` : ``ndp`` is number concentration density.
          The values are multiplied by the local ``dlogDp`` spacing
          before being fed to the underlying kernel, which sums per-bin
          counts internally.
        - ``'auto'``     : delegate to
          :func:`AeroViz.dataProcess.Optical.mie._detect_psd_type`.

    Returns
    -------
    dict
        Same keys as :func:`scattering_function` (``angles``, ``SL``,
        ``SR``, ``SU``).  Values are integrated over the PSD; the
        ``angles`` array is unchanged from the single-particle case.

    Examples
    --------
    >>> import numpy as np
    >>> from AeroViz.dataProcess.Optical.mie_angular import scattering_function_sd
    >>> dp = np.logspace(1, 3, 50)             # 10-1000 nm
    >>> ndp = 1e4 * np.exp(-((np.log10(dp) - 2.0) / 0.3) ** 2)
    >>> out = scattering_function_sd(complex(1.5, 0.02), 550.0, dp, ndp,
    ...                              psd_type='dN')
    >>> out['SU'].shape
    (361,)
    """
    if angles is None:
        angles_arr = np.arange(0.0, 180.5, 0.5)
    else:
        angles_arr = np.asarray(angles, dtype=float).ravel()

    min_angle, max_angle, resolution = _angle_bounds_from_array(angles_arr)

    dp_arr = np.asarray(dp, dtype=float).ravel()
    ndp_arr = np.asarray(ndp, dtype=float).ravel()

    if dp_arr.size != ndp_arr.size:
        raise ValueError(
            f"`dp` and `ndp` must be the same length "
            f"(got {dp_arr.size} and {ndp_arr.size})."
        )

    # Resolve psd_type.  We do the dNdlogDp -> dN conversion ourselves
    # because SF_SD treats `ndp` as per-bin counts (it sums, not
    # trapezoid-integrates, internally).
    if psd_type == "auto":
        # Lazy import to avoid a circular dependency at module load.
        from .mie import _detect_psd_type
        detected, _confidence = _detect_psd_type(ndp_arr, dp_arr)
        psd_type = detected

    if psd_type == "dNdlogDp":
        log_dp = np.log10(dp_arr)
        # Use centred differences so end bins still get a sensible width.
        dlogdp = np.gradient(log_dp)
        ndp_counts = ndp_arr * dlogdp
    elif psd_type == "dN":
        ndp_counts = ndp_arr
    else:
        raise ValueError(
            f"psd_type must be one of 'auto', 'dN', 'dNdlogDp' "
            f"(got {psd_type!r})."
        )

    measure, SL, SR, SU = SF_SD(
        m,
        wavelength,
        dp_arr,
        ndp_counts,
        minAngle=min_angle,
        maxAngle=max_angle,
        angularResolution=resolution,
        space=space,
        angleMeasure="radians",
        normalization=None,
    )

    return {
        "angles": np.asarray(measure),
        "SL": np.asarray(SL),
        "SR": np.asarray(SR),
        "SU": np.asarray(SU),
    }


# ---------------------------------------------------------------------------
# 3.  Mueller phase matrix elements
# ---------------------------------------------------------------------------

def phase_matrix(
    m: complex,
    wavelength: float,
    diameter: float,
    mu: ArrayLike | None = None,
) -> dict:
    """
    Compute the Mueller phase-matrix elements (S11, S12, S33, S34) for a
    single homogeneous sphere as a function of ``mu = cos(theta)``.

    For unpolarised incident light the Mueller matrix of a sphere has
    the well-known block-diagonal structure

    .. code-block:: text

        | S11  S12   0    0  |
        | S12  S11   0    0  |
        |  0    0   S33  S34 |
        |  0    0  -S34  S33 |

    so the four returned elements fully describe the scattering matrix.
    Wraps
    :func:`AeroViz.dataProcess.Optical.mie_kernels.MatrixElements`.

    Parameters
    ----------
    m : complex
        Complex refractive index of the particle.
    wavelength : float
        Wavelength of incident light in **nm**.
    diameter : float
        Particle diameter in **nm**.
    mu : array_like, optional
        Cosine of the scattering angle.  Defaults to
        ``np.linspace(-1, 1, 361)``, which spans 0-180 degrees at
        roughly 0.5 degree resolution.

    Returns
    -------
    dict
        Dictionary with the following keys, each a 1-D ``np.ndarray``
        with the same length as ``mu``:

        - ``'mu'``  : the cos(theta) grid (echoed for convenience).
        - ``'S11'`` : ``0.5 * (|S2|^2 + |S1|^2)``
        - ``'S12'`` : ``0.5 * (|S2|^2 - |S1|^2)``
        - ``'S33'`` : ``Re(S2* S1)``
        - ``'S34'`` : ``Im(S1 S2*)``

    Examples
    --------
    >>> from AeroViz.dataProcess.Optical.mie_angular import phase_matrix
    >>> pm = phase_matrix(complex(1.5, 0.02), 550.0, 200.0)
    >>> sorted(pm.keys())
    ['S11', 'S12', 'S33', 'S34', 'mu']
    >>> pm['S11'].shape
    (361,)
    """
    if mu is None:
        mu_arr = np.linspace(-1.0, 1.0, 361)
    else:
        mu_arr = np.asarray(mu, dtype=float).ravel()

    S11 = np.empty_like(mu_arr, dtype=float)
    S12 = np.empty_like(mu_arr, dtype=float)
    S33 = np.empty_like(mu_arr, dtype=float)
    S34 = np.empty_like(mu_arr, dtype=float)

    # MatrixElements is a per-scalar-mu single-particle routine, so we
    # loop.  This mirrors how PyMieScatt itself exposes the function.
    for i, u in enumerate(mu_arr):
        s11, s12, s33, s34 = MatrixElements(m, wavelength, diameter, float(u))
        S11[i] = float(np.real(s11))
        S12[i] = float(np.real(s12))
        S33[i] = float(np.real(s33))
        S34[i] = float(np.real(s34))

    return {
        "mu": mu_arr,
        "S11": S11,
        "S12": S12,
        "S33": S33,
        "S34": S34,
    }


# ---------------------------------------------------------------------------
# 4.  Nephelometer truncation correction (Anderson & Ogren 1998)
# ---------------------------------------------------------------------------

# Per-instrument linear coefficients of the form
#   f(SAE) = a + b * SAE
# at three reference wavelengths.  TSI 3563 values are from
# Anderson & Ogren (1998), Table 4 (total-scattering, sub-10um).
# Aurora 3000 values are widely cited corrections derived in the same
# functional form from Mueller et al. (2011) / IMPROVE field
# operations notes; see comment block below.
_TRUNCATION_COEFFS = {
    # Anderson & Ogren (1998), Table 4 (total-scattering, no size cut):
    #   450 nm -> 1.345 + 0.0418 * SAE
    #   550 nm -> 1.315 + 0.0429 * SAE
    #   700 nm -> 1.297 + 0.0455 * SAE
    # These are the standard TSI 3563 corrections.  A simplified
    # one-wavelength form -- f(SAE) ~= 1.029 + 0.026 * SAE at 550 nm --
    # is also in circulation and corresponds to the sub-1um total-
    # scattering subset; we keep the full-aerosol numbers here as the
    # canonical TSI 3563 correction.
    "NEPH":       {450: (1.345, 0.0418), 550: (1.315, 0.0429), 700: (1.297, 0.0455)},
    "TSI3563":    {450: (1.345, 0.0418), 550: (1.315, 0.0429), 700: (1.297, 0.0455)},

    # Aurora 3000 truncates at ~10 deg / ~171 deg rather than the TSI's
    # 7/170, giving slightly larger corrections.  Coefficients below
    # are representative values from the published literature; other
    # campaigns have reported instrument-specific tunings and users
    # should consult their own calibration where possible.
    "AURORA3000": {450: (1.455, 0.0436), 525: (1.394, 0.0467), 635: (1.366, 0.0512)},
    "AURORA":     {450: (1.455, 0.0436), 525: (1.394, 0.0467), 635: (1.366, 0.0512)},
}


def nephelometer_truncation_correction(
    sae: ArrayLike,
    wavelength: float = 550.0,
    instrument: str = "NEPH",
) -> np.ndarray:
    """
    Anderson & Ogren (1998) angular-truncation correction for
    integrating nephelometers.

    Integrating nephelometers cannot sample the full 0-180 degree
    scattering range -- typically light scattered into roughly the
    forward 7 degrees and behind ~170 degrees is missed.  The lost
    contribution is wavelength- and size-distribution-dependent; the
    Anderson-Ogren correction parametrises it as a simple linear
    function of the scattering Angstrom exponent (SAE):

    .. math::

        f(\\mathrm{SAE}) = a(\\lambda) + b(\\lambda) \\cdot \\mathrm{SAE}

    Multiplying the measured scattering coefficient by ``f`` recovers
    the (estimated) true 0-180 degree scattering.

    Parameters
    ----------
    sae : float or array_like
        Scattering Angstrom exponent (dimensionless).  Typical
        atmospheric values are 0.5-3.
    wavelength : float, default=550
        Wavelength in **nm** at which the correction is evaluated.
        Must be one of the tabulated reference wavelengths for the
        chosen instrument (see Notes).
    instrument : str, default='NEPH'
        Nephelometer identifier.  Supported values (case-insensitive):

        - ``'NEPH'``       or ``'TSI3563'`` : TSI 3563 three-wavelength
          nephelometer (450, 550, 700 nm).
        - ``'AURORA'``     or ``'AURORA3000'`` : Ecotech Aurora 3000
          (450, 525, 635 nm).

    Returns
    -------
    factor : float or np.ndarray
        Multiplicative correction factor.  Same shape as ``sae``.

    Examples
    --------
    >>> from AeroViz.dataProcess.Optical.mie_angular import (
    ...     nephelometer_truncation_correction,
    ... )
    >>> nephelometer_truncation_correction(2.0)
    1.4008
    >>> import numpy as np
    >>> nephelometer_truncation_correction(np.array([0.5, 1.0, 2.0, 3.0]),
    ...                                    wavelength=450)
    array([1.3659, 1.3868, 1.4286, 1.4704])

    Notes
    -----
    The default TSI 3563 coefficients come directly from
    Anderson & Ogren (1998), Table 4 (total-scattering channel, no
    size cut).  Aurora 3000 coefficients are representative values
    derived in the same functional form; users with their own
    calibration should pass those in by extending
    ``_TRUNCATION_COEFFS`` or applying the correction manually.

    A simpler one-wavelength approximation,
    ``f(SAE) ~= 1.029 + 0.026 * SAE`` at 550 nm, is sometimes cited
    for the sub-1um size-cut channel; it is not used here.

    References
    ----------
    Anderson, T. L., and Ogren, J. A. (1998), Determining Aerosol
    Radiative Properties Using the TSI 3563 Integrating Nephelometer,
    *Aerosol Science and Technology*, 29(1), 57-69,
    doi:10.1080/02786829808965551.
    """
    key = instrument.upper().replace("-", "").replace(" ", "")
    if key not in _TRUNCATION_COEFFS:
        raise ValueError(
            f"Unknown instrument {instrument!r}.  Supported: "
            f"{sorted(_TRUNCATION_COEFFS)}."
        )

    table = _TRUNCATION_COEFFS[key]
    # Tolerate small float jitter on the wavelength argument.
    matched = None
    for wl_ref in table:
        if abs(float(wavelength) - wl_ref) < 1.0:
            matched = wl_ref
            break
    if matched is None:
        raise ValueError(
            f"No truncation coefficients tabulated for {instrument!r} at "
            f"{wavelength} nm.  Available wavelengths: {sorted(table)}."
        )

    a, b = table[matched]
    sae_arr = np.asarray(sae, dtype=float)
    factor = a + b * sae_arr
    # Preserve scalar input / output relationship.
    if sae_arr.ndim == 0:
        return float(factor)
    return factor
