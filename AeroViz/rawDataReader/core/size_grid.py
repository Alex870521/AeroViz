"""
Size-channel lattice for TSI SMPS exports.

Every AIM export at a given channels-per-decade resolution reports its size
bins on **one fixed logarithmic lattice**: channel ``k`` spans
``10**(k/cpd) .. 10**((k+1)/cpd)`` nm and is labelled by its geometric
midpoint ``10**((k+0.5)/cpd)``. Changing the sheath flow, the DMA, the scan
range or the AIM version only selects a different *window* of that lattice —
it never moves the bins. Checked against every distinct header in the TCLab
archive (2017-2026, five stations, long and nano DMAs, AIM <=10.2 / 10.3 /
11.x): 1.02-982.2 nm, all on the lattice.

What does change is how many digits the software prints:

==========  =====================  =========================
AIM         label for channel 73   rule
==========  =====================  =========================
<= 10.3     ``16.8``               2 decimals below 10 nm, else 1
11.x        ``16.85``              always 2 decimals
==========  =====================  =========================

so the *printed* diameter is not a stable identity for a bin, and it cannot be
made one by rounding: ``round(16.85, 1)`` is 16.9 (or 16.8 for the float just
below it), while AIM 10.3 printed 16.8 from the unrounded 16.849.

Identity is therefore the channel index. This module converts printed
diameters to channel indices and back to one canonical label per channel — the
AIM <= 10.3 convention, which is what a decade of exports and every downstream
table already use. The measured values are never touched: aligning a file to
the lattice only renames its columns.
"""
from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

__all__ = ['DEFAULT_CHANNELS_PER_DECADE', 'channel_index', 'channel_midpoint',
           'channel_label', 'lattice_channels', 'label_range']

#: TSI's standard multichannel resolution, and the only one given canonical
#: labels here.
DEFAULT_CHANNELS_PER_DECADE = 64

#: Largest tolerated distance, in channels, between a printed diameter and the
#: midpoint of the channel it falls in. Three-significant-digit labels
#: (``2.02``) sit up to 0.12 channels off; a 128-channel/decade export sits
#: exactly 0.25 off, so the limit has to stay below that.
LATTICE_TOLERANCE = 0.2


def channel_index(dp_nm: float, channels_per_decade: float = DEFAULT_CHANNELS_PER_DECADE) -> int:
    """Lattice channel containing ``dp_nm``. Midpoints sit at ``k + 0.5``, so
    ``floor`` is stable against the rounding of the printed label."""
    return math.floor(channels_per_decade * math.log10(dp_nm))


def channel_midpoint(k: int, channels_per_decade: float = DEFAULT_CHANNELS_PER_DECADE) -> float:
    """Exact geometric midpoint (nm) of channel ``k``."""
    return 10 ** ((k + 0.5) / channels_per_decade)


def channel_label(k: int, channels_per_decade: float = DEFAULT_CHANNELS_PER_DECADE) -> float:
    """Canonical column label for channel ``k``: its midpoint, rounded the way
    AIM <= 10.3 prints it (half-up; 2 decimals below 10 nm, 1 decimal above).

    Reproduces every AIM <= 10.3 header in the archive exactly, so relabelling
    one of those files is a no-op.
    """
    mid = channel_midpoint(k, channels_per_decade)
    quantum = Decimal('0.01') if mid < 10 else Decimal('0.1')
    return float(Decimal(repr(mid)).quantize(quantum, rounding=ROUND_HALF_UP))


def lattice_channels(diameters_nm, channels_per_decade: float = DEFAULT_CHANNELS_PER_DECADE,
                     tolerance: float = LATTICE_TOLERANCE) -> list[int] | None:
    """Channel index of every diameter, or ``None`` if the set is not a clean
    window of the lattice.

    ``None`` when any diameter is non-positive, sits further than
    ``tolerance`` channels from a channel midpoint, or two diameters land in
    the same channel — the caller then keeps the file's own labels and treats
    its grid as foreign.
    """
    channels = []
    for dp in diameters_nm:
        if not (dp > 0 and math.isfinite(dp)):
            return None
        position = channels_per_decade * math.log10(dp)
        k = math.floor(position)
        if abs(position - (k + 0.5)) > tolerance:
            return None
        channels.append(k)
    if len(set(channels)) != len(channels):
        return None
    return channels


def label_range(labels) -> str:
    """``'11.8–593.5 nm'`` for a collection of bin labels (for log lines)."""
    labels = list(labels)
    return f'{min(labels):g}–{max(labels):g} nm' if labels else 'no bins'
