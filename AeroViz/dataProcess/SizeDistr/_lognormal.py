"""Lognormal-mode arithmetic: Hatch–Choate moment conversions.

A lognormal number mode with count median diameter ``CMD`` and geometric
standard deviation ``σg`` has its volume (mass) mode at the same ``σg`` but a
larger median, and its total volume follows from the third moment
(Hatch & Choate 1929; Hinds 1999, §4.4)::

    VMD = CMD · exp(3 ln²σg)                      # volume median diameter
    V   = N · (π/6) · CMD³ · exp(4.5 ln²σg)       # total volume

These let a mode be specified by what is usually known — a mass loading and a
density — instead of a number concentration, and let a volume-mode fit be
turned back into the number mode the Mie integral needs.
"""
from __future__ import annotations

import numpy as np

__all__ = ['hatch_choate', 'lognormal_total_volume', 'lognormal_number_from_volume']

_MOMENT = {'number': 0, 'surface': 2, 'volume': 3, 'mass': 3}


def hatch_choate(geo_mean: float, geo_std: float, *, from_: str = 'number', to: str = 'volume') -> float:
    """Median diameter of one weighting from another, same ``geo_std``.

    ``d_to = d_from · exp((p_to − p_from) · ln²σg)`` with the moment order
    ``p`` = 0 / 2 / 3 for number / surface / volume (mass ≡ volume).
    """
    try:
        p_from, p_to = _MOMENT[from_], _MOMENT[to]
    except KeyError as e:
        raise ValueError(f"weighting must be one of {sorted(_MOMENT)}; got {e.args[0]!r}") from None
    return float(geo_mean * np.exp((p_to - p_from) * np.log(geo_std) ** 2))


def lognormal_total_volume(total_number: float, geo_mean_nm: float, geo_std: float) -> float:
    """Total volume (µm³/cm³) of a number mode: ``N (π/6) CMD³ exp(4.5 ln²σg)``."""
    cmd_um = geo_mean_nm / 1000.0
    return float(total_number * np.pi / 6 * cmd_um ** 3 * np.exp(4.5 * np.log(geo_std) ** 2))


def lognormal_number_from_volume(total_volume: float, geo_mean_nm: float, geo_std: float) -> float:
    """Number concentration (#/cm³) whose mode holds ``total_volume`` µm³/cm³."""
    return float(total_volume / lognormal_total_volume(1.0, geo_mean_nm, geo_std))
