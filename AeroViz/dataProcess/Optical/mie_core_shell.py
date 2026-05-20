# -*- coding: utf-8 -*-
"""
Aden-Kerker Mie Scattering for Coated (Core-Shell) Spheres.

This module implements Mie theory for two-layer concentric spheres
(coated particles), which is the physically realistic model for aged
atmospheric aerosols where a hydrophobic black-carbon (BC) core is
coated by hygroscopic material (sulfate, nitrate, organics, or ALWC).

The expansion uses two size parameters,

    x = pi * d_core  / lambda
    y = pi * d_total / lambda

and three refractive indices (medium, core, shell). The Mie expansion
coefficients ``a_n`` and ``b_n`` follow the Aden-Kerker formulation,
expressed in terms of Riccati-Bessel functions psi_n and chi_n evaluated
at v = m_shell * x, w = m_shell * y, and y, and the logarithmic
derivatives D_n evaluated at u = m_core * x, v, w.

References
----------
- Aden, A. L. and Kerker, M. (1951). "Scattering of Electromagnetic
  Waves from Two Concentric Spheres", J. Appl. Phys. 22, 1242.
- Kerker, M. (1969). "The Scattering of Light and Other Electromagnetic
  Radiation", Academic Press, New York.
- Bohren, C. F. and Huffman, D. R. (1983). "Absorption and Scattering of
  Light by Small Particles", Wiley, Chapter 8 (Section 8.1).
- Sumlin, B. J., Heinson, W. R. and Chakrabarty, R. K. (2018).
  "Retrieving the aerosol complex refractive index using PyMieScatt",
  J. Quant. Spectrosc. Radiat. Transf. 205, 127.
"""

from __future__ import annotations

import numpy as np
from scipy.integrate import trapezoid
from scipy.special import jv, yv

__all__ = ["mie_core_shell", "mie_core_shell_sd"]


# =============================================================================
# Core Aden-Kerker expansion
# =============================================================================

def _core_shell_ab(
    m_core: complex,
    m_shell: complex,
    x: float,
    y: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute Aden-Kerker expansion coefficients ``a_n`` and ``b_n``
    for a concentric two-layer sphere.

    Parameters
    ----------
    m_core : complex
        Core refractive index (relative to the medium).
    m_shell : complex
        Shell refractive index (relative to the medium).
    x : float
        Core size parameter, ``pi * d_core / lambda``.
    y : float
        Total size parameter, ``pi * d_total / lambda``.

    Returns
    -------
    a_n, b_n : ndarray, complex
        Series coefficients of length ``n_max = round(2 + y + 4*y**(1/3))``.

    Notes
    -----
    Port of ``PyMieScatt.CoreShell.CoreShell_ab``. Variable names follow
    Bohren & Huffman §8.1 (and the PyMieScatt implementation):

        u = m_core  * x   (core arg, core index)
        v = m_shell * x   (core arg, shell index)
        w = m_shell * y   (total arg, shell index)
        m = m_shell / m_core

    The logarithmic derivatives ``D_n(u)``, ``D_n(v)``, ``D_n(w)`` are
    obtained by stable downward recurrence over ``n_mx`` terms.
    """
    m = m_shell / m_core
    u = m_core * x
    v = m_shell * x
    w = m_shell * y

    mx = max(np.abs(m_core * y), np.abs(m_shell * y))
    n_max = int(np.round(2 + y + 4 * (y ** (1 / 3))))
    n_mx = int(np.round(max(n_max, mx) + 16))
    n = np.arange(1, n_max + 1)
    nu = n + 0.5

    # Riccati-Bessel functions psi_n(z) = sqrt(pi*z/2) * J_{n+1/2}(z)
    # and chi_n(z) = -sqrt(pi*z/2) * Y_{n+1/2}(z), evaluated at v, w, y.
    sv = np.sqrt(0.5 * np.pi * v)
    sw = np.sqrt(0.5 * np.pi * w)
    sy = np.sqrt(0.5 * np.pi * y)

    pv = sv * jv(nu, v)
    pw = sw * jv(nu, w)
    py = sy * jv(nu, y)

    chv = -sv * yv(nu, v)
    chw = -sw * yv(nu, w)
    chy = -sy * yv(nu, y)

    # psi_{n-1}(y) and chi_{n-1}(y) with boundary conditions
    p1y = np.append([np.sin(y)], py[0:n_max - 1])
    ch1y = np.append([np.cos(y)], chy[0:n_max - 1])

    # Hankel functions xi_n(y) = psi_n(y) - i * chi_n(y)
    gsy = py - 1j * chy
    gs1y = p1y - 1j * ch1y

    # Logarithmic derivatives D_n via downward recurrence
    Dnu = np.zeros(n_mx, dtype=complex)
    Dnv = np.zeros(n_mx, dtype=complex)
    Dnw = np.zeros(n_mx, dtype=complex)
    for i in range(n_mx - 1, 1, -1):
        Dnu[i - 1] = i / u - 1 / (Dnu[i] + i / u)
        Dnv[i - 1] = i / v - 1 / (Dnv[i] + i / v)
        Dnw[i - 1] = i / w - 1 / (Dnw[i] + i / w)

    Du = Dnu[1:n_max + 1]
    Dv = Dnv[1:n_max + 1]
    Dw = Dnw[1:n_max + 1]

    # Aden-Kerker auxiliary terms (B&H 8.2)
    uu = m * Du - Dv
    vv = Du / m - Dv
    fv = pv / chv

    dns = ((uu * fv / pw) / (uu * (pw - chw * fv) + (pw / pv) / chv)) + Dw
    gns = ((vv * fv / pw) / (vv * (pw - chw * fv) + (pw / pv) / chv)) + Dw
    a1 = dns / m_shell + n / y
    b1 = m_shell * gns + n / y

    a_n = (py * a1 - p1y) / (gsy * a1 - gs1y)
    b_n = (py * b1 - p1y) / (gsy * b1 - gs1y)

    return a_n, b_n


# =============================================================================
# Public API: single coated particle
# =============================================================================

def mie_core_shell(
    m_core: complex,
    m_shell: complex,
    d_core: float,
    d_total: float,
    wavelength: float,
) -> dict[str, float]:
    """
    Compute Mie efficiencies for a single coated (core-shell) sphere.

    Implements the Aden-Kerker (1951) coated-sphere expansion. Typical
    use case in atmospheric science: hydrophobic black-carbon (BC) core
    coated by hygroscopic ammonium sulfate, organics, or aerosol liquid
    water — the physically realistic mixing model for aged aerosols.

    Parameters
    ----------
    m_core : complex
        Complex refractive index of the core
        (e.g. BC ~ ``complex(1.95, 0.79)`` at 550 nm).
    m_shell : complex
        Complex refractive index of the shell
        (e.g. ammonium sulfate ~ ``complex(1.53, 0.0)``;
        organic matter ~ ``complex(1.55, 0.0)``).
    d_core : float
        Core diameter in nm. Must satisfy ``0 <= d_core <= d_total``.
    d_total : float
        Total (core + shell) diameter in nm.
    wavelength : float
        Wavelength of incident light in nm.

    Returns
    -------
    dict
        Same keys as :func:`mie.calculate_mie_efficiencies` for a single
        particle (each value is a scalar ``float``):

        * ``Q_ext``   — extinction efficiency
        * ``Q_sca``   — scattering efficiency
        * ``Q_abs``   — absorption efficiency (= Q_ext − Q_sca)
        * ``g``       — asymmetry parameter (forward-scattering bias)
        * ``Q_pr``    — radiation-pressure efficiency (= Q_ext − g·Q_sca)
        * ``Q_back``  — backscatter efficiency
        * ``Q_ratio`` — backscatter ratio (= Q_back / Q_sca)

    Raises
    ------
    ValueError
        If ``d_total < d_core``, or any of ``d_core``, ``d_total``,
        ``wavelength`` is non-positive.

    Notes
    -----
    The efficiencies are normalised by ``y**2`` (where ``y = pi * d_total
    / lambda``) rather than by the core size parameter — this is the
    standard convention so that, in the degenerate case where shell and
    core are identical, the result reduces to homogeneous-sphere Mie
    theory evaluated at ``d_total``.

    Series truncation: ``n_max = round(2 + y + 4 * y**(1/3))`` (Wiscombe
    1980); logarithmic-derivative downward recurrence uses
    ``n_mx = round(max(n_max, |m·y|) + 16)``.

    Examples
    --------
    >>> # BC core coated by organic matter
    >>> out = mie_core_shell(
    ...     m_core=complex(1.95, 0.79),
    ...     m_shell=complex(1.55, 0.0),
    ...     d_core=50, d_total=150, wavelength=550,
    ... )
    >>> out['Q_abs']  # doctest: +SKIP
    0.6...
    """
    # === Input validation ===
    if wavelength <= 0:
        raise ValueError(f"wavelength must be positive (got {wavelength}).")
    if d_core < 0:
        raise ValueError(f"d_core must be non-negative (got {d_core}).")
    if d_total <= 0:
        raise ValueError(f"d_total must be positive (got {d_total}).")
    if d_total < d_core:
        raise ValueError(
            f"d_total ({d_total}) must be >= d_core ({d_core})."
        )

    m_core = complex(m_core)
    m_shell = complex(m_shell)

    x = np.pi * d_core / wavelength
    y = np.pi * d_total / wavelength

    # === Degenerate cases — delegate to homogeneous-sphere Mie ===
    # 1) pure shell (no core): treat as a homogeneous sphere of shell RI
    # 2) core == shell RI: treat as homogeneous sphere
    # 3) d_core == d_total: treat as homogeneous sphere of core RI
    if x == 0 or m_core == m_shell or x == y:
        from .mie_kernels import AutoMieQ
        m_use = m_shell if x == 0 else m_core
        Qe, Qs, Qa, g, Qpr, Qb, Qr = AutoMieQ(m_use, wavelength, d_total)
        return {
            "Q_ext": float(Qe), "Q_sca": float(Qs), "Q_abs": float(Qa),
            "g": float(g), "Q_pr": float(Qpr),
            "Q_back": float(Qb), "Q_ratio": float(Qr),
        }

    # === Aden-Kerker expansion ===
    a_n, b_n = _core_shell_ab(m_core, m_shell, x, y)

    n_max = len(a_n)
    n = np.arange(1, n_max + 1)
    n1 = 2 * n + 1
    n2 = n * (n + 2) / (n + 1)
    n3 = n1 / (n * (n + 1))
    y2 = y ** 2

    Q_ext = (2 / y2) * np.sum(n1 * (a_n.real + b_n.real))
    Q_sca = (2 / y2) * np.sum(
        n1 * (a_n.real ** 2 + a_n.imag ** 2 + b_n.real ** 2 + b_n.imag ** 2)
    )
    Q_abs = Q_ext - Q_sca

    # Asymmetry parameter g (B&H eq. 4.61) — same form as homogeneous Mie
    g1 = [
        np.append(a_n.real[1:n_max], 0.0),
        np.append(a_n.imag[1:n_max], 0.0),
        np.append(b_n.real[1:n_max], 0.0),
        np.append(b_n.imag[1:n_max], 0.0),
    ]
    g = (4 / (Q_sca * y2)) * np.sum(
        n2 * (a_n.real * g1[0] + a_n.imag * g1[1]
              + b_n.real * g1[2] + b_n.imag * g1[3])
        + n3 * (a_n.real * b_n.real + a_n.imag * b_n.imag)
    )

    Q_pr = Q_ext - Q_sca * g
    Q_back = (1 / y2) * (np.abs(np.sum(n1 * ((-1) ** n) * (a_n - b_n))) ** 2)
    Q_ratio = Q_back / Q_sca

    return {
        "Q_ext": float(Q_ext),
        "Q_sca": float(Q_sca),
        "Q_abs": float(Q_abs),
        "g": float(g),
        "Q_pr": float(Q_pr),
        "Q_back": float(Q_back),
        "Q_ratio": float(Q_ratio),
    }


# =============================================================================
# Public API: PSD-integrated coated particles
# =============================================================================

def mie_core_shell_sd(
    m_core: complex,
    m_shell: complex,
    dp_core: np.ndarray,
    dp_total: np.ndarray,
    ndp: np.ndarray,
    wavelength: float = 550,
    psd_type: str = "dNdlogDp",
) -> dict[str, float]:
    """
    Integrate coated-sphere Mie efficiencies over a particle size
    distribution to obtain bulk optical coefficients.

    Each PSD bin is described by a paired ``(d_core, d_total)``, so the
    caller can express any per-bin core-shell geometry — typical use is
    a constant coating-to-core thickness ratio, but variable shells
    (e.g. from inverse modeling) are equally supported.

    Parameters
    ----------
    m_core : complex
        Core complex refractive index (constant across the PSD).
    m_shell : complex
        Shell complex refractive index (constant across the PSD).
    dp_core : ndarray
        Core diameters per bin in nm. Shape ``(n_bins,)``.
    dp_total : ndarray
        Total (core + shell) diameters per bin in nm, same length as
        ``dp_core``. Must satisfy ``dp_total[i] >= dp_core[i]``.
    ndp : ndarray
        Number concentration per bin (``dN/dlogDp`` or ``dN`` depending
        on ``psd_type``). Shape ``(n_bins,)``.
    wavelength : float, default 550
        Wavelength of incident light in nm.
    psd_type : {'dNdlogDp', 'dN'}, default 'dNdlogDp'
        - ``'dNdlogDp'``: trapezoidal integration over ``log10(dp_total)``.
        - ``'dN'``: discrete summation over bins.

    Returns
    -------
    dict
        Bulk optical coefficients (each a scalar ``float``):

        * ``ext``    — extinction coefficient (Mm⁻¹)
        * ``sca``    — scattering coefficient (Mm⁻¹)
        * ``abs``    — absorption coefficient (Mm⁻¹) = ext − sca
        * ``g_eff``  — PSD-mean asymmetry parameter, ``Q_sca``-weighted

    Raises
    ------
    ValueError
        If arrays have mismatched lengths, any ``dp_total[i] < dp_core[i]``,
        or ``psd_type`` is unrecognised.

    Notes
    -----
    Cross-section per bin is taken at the *total* diameter:

        sigma_i = pi/4 * (dp_total_i)**2

    consistent with the convention used in :func:`mie_core_shell` (where
    efficiencies are normalised by ``y**2``).

    The effective asymmetry parameter is the scattering-weighted mean
    of the per-bin asymmetry values, which is what radiative-transfer
    codes expect when combining size bins.

    Examples
    --------
    >>> import numpy as np
    >>> dp_core = np.array([30., 50., 80.])
    >>> dp_total = dp_core * 2  # 2x core size
    >>> ndp = np.array([1e3, 5e2, 2e2])
    >>> out = mie_core_shell_sd(
    ...     complex(1.95, 0.79), complex(1.55, 0.0),
    ...     dp_core, dp_total, ndp, wavelength=550,
    ... )
    >>> out['ext']  # doctest: +SKIP
    0.1...
    """
    if psd_type not in ("dNdlogDp", "dN"):
        raise ValueError(
            f"psd_type must be 'dNdlogDp' or 'dN' (got {psd_type!r})."
        )

    dp_core = np.asarray(dp_core, dtype=float)
    dp_total = np.asarray(dp_total, dtype=float)
    ndp = np.asarray(ndp, dtype=float)

    if dp_core.shape != dp_total.shape or dp_core.shape != ndp.shape:
        raise ValueError(
            "dp_core, dp_total and ndp must have the same shape "
            f"(got {dp_core.shape}, {dp_total.shape}, {ndp.shape})."
        )
    if np.any(dp_total < dp_core):
        bad = np.where(dp_total < dp_core)[0]
        raise ValueError(
            f"dp_total must be >= dp_core in every bin; violated at "
            f"indices {bad.tolist()}."
        )

    n_bins = dp_total.size
    Q_ext = np.zeros(n_bins)
    Q_sca = np.zeros(n_bins)
    g_arr = np.zeros(n_bins)

    for i in range(n_bins):
        out = mie_core_shell(
            m_core, m_shell,
            float(dp_core[i]), float(dp_total[i]),
            wavelength,
        )
        Q_ext[i] = out["Q_ext"]
        Q_sca[i] = out["Q_sca"]
        g_arr[i] = out["g"]

    # Cross-sectional area in nm^2, scaled by 1e-6 to deliver Mm^-1.
    cross_section = np.pi * (dp_total / 2) ** 2 * 1e-6
    integrand_ext = Q_ext * cross_section * ndp
    integrand_sca = Q_sca * cross_section * ndp

    if psd_type == "dNdlogDp":
        log_dp = np.log10(dp_total)
        ext = trapezoid(integrand_ext, x=log_dp)
        sca = trapezoid(integrand_sca, x=log_dp)
        # Sca-weighted asymmetry parameter, integrated over log Dp
        sca_weight = trapezoid(Q_sca * cross_section * ndp, x=log_dp)
        g_num = trapezoid(g_arr * Q_sca * cross_section * ndp, x=log_dp)
    else:  # 'dN'
        ext = float(np.sum(integrand_ext))
        sca = float(np.sum(integrand_sca))
        sca_weight = float(np.sum(Q_sca * cross_section * ndp))
        g_num = float(np.sum(g_arr * Q_sca * cross_section * ndp))

    g_eff = g_num / sca_weight if sca_weight > 0 else 0.0

    return {
        "ext": float(ext),
        "sca": float(sca),
        "abs": float(ext - sca),
        "g_eff": float(g_eff),
    }
