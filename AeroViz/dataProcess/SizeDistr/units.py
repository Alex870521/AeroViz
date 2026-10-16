"""Size-distribution units: parse AIM export labels, convert to dN/dlogDp, and
check the unit a frame says it is in before computing with it.

Every size-distribution calculation in AeroViz assumes number concentration
normalised by the log10 bin width (dN/dlogDp). AIM can export the same scan in
other forms — per channel instead of per dlogDp, or weighted by surface,
volume or mass. Those convert exactly; Raw Counts (needs AIM's flow, dead-time
and Stokes corrections) and percentages (need the total) do not, so they are
left unsupported.

A frame carries its unit in ``df.attrs[UNIT_ATTR]`` (e.g. ``'dN/dlogDp'``).
Readers stamp it; ``check_unit`` is what calculations call first. A frame with
no unit recorded is taken to be in the unit the caller declares — that keeps
user-built DataFrames working — but a frame that *says* it is something else is
refused rather than silently computed on.
"""
from __future__ import annotations

import re

import numpy as np
from pandas import DataFrame

__all__ = ['UNIT_ATTR', 'SOURCE_UNIT_ATTR', 'FILE_UNIT_ATTR', 'DN_DLOGDP', 'ExportUnit',
           'parse_export_unit', 'to_dndlogdp', 'unit_label', 'check_unit']

#: ``df.attrs`` key holding the unit of a frame's size bins.
UNIT_ATTR = 'size_dist_unit'
#: ``df.attrs`` key on a reader's output: ``{export unit: [files]}`` for the
#: files it had to convert.
SOURCE_UNIT_ATTR = 'source_units'
#: ``df.attrs`` key on one parsed file's frame: the unit that file was exported
#: in. Internal to the readers; removed before the output is returned.
FILE_UNIT_ATTR = 'export_unit'
DN_DLOGDP = 'dN/dlogDp'

#: dM → dN scale by diameter unit: AIM APS mass is mg/m³ with Dp in µm.
#: No entry for nm — see `to_dndlogdp`.
MASS_SCALE = {'um': 1e3}

_WEIGHT_TO_MOMENT = {'number': 'N', 'surface': 'S', 'volume': 'V', 'mass': 'M'}


class ExportUnit(tuple):
    """``(moment, per_dlogdp)`` — moment in ``N S V M``; ``per_dlogdp`` False
    when the export is per channel (dN, dS ...) instead of per dlogDp."""

    def __new__(cls, moment: str, per_dlogdp: bool):
        return super().__new__(cls, (moment, per_dlogdp))

    @property
    def moment(self) -> str:
        return self[0]

    @property
    def per_dlogdp(self) -> bool:
        return self[1]

    @property
    def label(self) -> str:
        return unit_label(self.moment, self.per_dlogdp)


def unit_label(moment: str, per_dlogdp: bool = True) -> str:
    """``('S', True)`` → ``'dS/dlogDp'``; ``('N', False)`` → ``'dN'``."""
    return f'd{moment}/dlogDp' if per_dlogdp else f'd{moment}'


_APS_UNIT = re.compile(r'^d([NSVM])(/dlogDp)?$')


def parse_export_unit(units: str | None, weight: str | None = None) -> ExportUnit | None:
    """Read an AIM export unit; ``None`` when it cannot be converted exactly.

    Two spellings exist:

    - APS writes one token per row: ``dN/dlogDp``, ``dN``, ``dS/dlogDp``,
      ``dM`` ... (also ``Raw Counts``, ``%dN`` — unsupported).
    - SMPS writes ``Units`` + ``Weight`` in the preamble: ``dW/dlogDp`` or
      ``Concentration (dW)`` (W = whatever ``Weight`` says: Number, Surface,
      Volume, Mass), or ``% Concentration`` — unsupported.

    With neither given, the export is assumed to be dN/dlogDp.
    """
    if units is None and weight is None:
        return ExportUnit('N', True)
    u = (units or '').strip()
    if weight is None:
        m = _APS_UNIT.match(u)
        return ExportUnit(m.group(1), bool(m.group(2))) if m else None

    moment = _WEIGHT_TO_MOMENT.get(weight.strip().lower())
    if moment is None:
        return None
    lu = u.lower().replace(' ', '')
    if lu in ('', 'dw/dlogdp'):
        return ExportUnit(moment, True)
    if lu in ('concentration(dw)', 'dw'):
        return ExportUnit(moment, False)
    return None


def to_dndlogdp(bins: DataFrame, unit: ExportUnit, *, dp_unit: str,
                dlogdp=None, density=None) -> DataFrame:
    """Convert size bins exported as ``unit`` to dN/dlogDp.

    Parameters
    ----------
    bins : DataFrame
        Size bins only; columns are diameters in ``dp_unit``.
    unit : ExportUnit
        What ``bins`` holds (from ``parse_export_unit``).
    dp_unit : {'nm', 'um'}
        Diameter unit of the columns. AIM reports surface / volume in the same
        length unit (nm²/cm³ for SMPS, µm²/cm³ for APS), so only the mass
        conversion depends on it.
    dlogdp : float or array, optional
        log10 channel width, for per-channel exports. Defaults to
        ``bin_widths`` of the grid; pass ``1 / channels_per_decade`` when the
        file states it.
    density : float or array-like, optional
        Particle density in g/cm³, required for mass. Scalar, or one value
        per row (SMPS records it per scan).

    Notes
    -----
    ``dS = π Dp² dN``, ``dV = π/6 Dp³ dN`` — the inverse of what
    ``finalize_size_dist`` / ``SizeDist.to_surface`` write. AIM's APS mass is
    in mg/m³ with density in g/cm³ and Dp in µm, giving
    ``dN = 1e3 · dM / (ρ π/6 Dp³)``. That factor was checked against 11 days
    of paired TCLab exports (mass vs number of the same scans: ratio 1.000).
    There is no SMPS mass export to check against, so mass with Dp in nm is
    refused rather than converted on an assumed unit.
    """
    from AeroViz.dataProcess.SizeDistr._size_dist import bin_widths

    dp = np.asarray(bins.columns, dtype=float)
    out = bins.apply(_to_float)
    if unit.moment == 'S':
        out = out / (np.pi * dp ** 2)
    elif unit.moment == 'V':
        out = out / (np.pi / 6 * dp ** 3)
    elif unit.moment == 'M':
        if density is None:
            raise ValueError('mass-weighted export needs a particle density to convert')
        if dp_unit not in MASS_SCALE:
            raise ValueError(f'no verified mass unit for diameters in {dp_unit!r}')
        rho = np.asarray(density, dtype=float)
        scale = MASS_SCALE[dp_unit]
        per_particle = np.pi / 6 * dp ** 3
        out = out * scale / per_particle
        out = out.div(rho, axis=0) if rho.ndim else out / float(rho)
    if not unit.per_dlogdp:
        widths = bin_widths(dp) if dlogdp is None else dlogdp
        out = out / np.asarray(widths, dtype=float)
    return out


def _to_float(col):
    from pandas import to_numeric
    return to_numeric(col, errors='coerce')


def check_unit(df: DataFrame, expected: str, where: str) -> None:
    """Refuse to compute on a frame whose recorded unit is not ``expected``.

    A frame with no ``attrs[UNIT_ATTR]`` passes (it is taken to be in the
    caller's declared unit).
    """
    got = getattr(df, 'attrs', {}).get(UNIT_ATTR)
    if got is not None and got != expected:
        raise ValueError(
            f"\n{where} 需要 {expected},但資料的 attrs['{UNIT_ATTR}'] 是 {got!r}。\n"
            f"  {where} expects {expected}, but the frame is recorded as {got!r}.\n"
            f"  Convert it first, e.g. "
            f"`AeroViz.dataProcess.SizeDistr.units.to_dndlogdp`.")
