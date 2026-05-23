"""
Time-grid helpers — detect a file's native frequency, reconcile mixed
resolutions across files, and place off-grid timestamps onto a regular grid
without the duplicate-fill bug of ``reindex(method='nearest')``.

Why ``round`` instead of ``reindex(method='nearest')``
------------------------------------------------------
``reindex(method='nearest')`` is a *pull*: every target grid point independently
picks its nearest source, so when data is sparse or off-grid two adjacent grid
points can grab the **same** source row — one reading gets duplicated into two
slots. No ``tolerance`` value fixes this; it is inherent to the nearest pull.

``snap_to_grid`` is a *push*: each source row is ``round``-ed to its own nearest
grid bin, so it lands in exactly one slot. Many rows can collapse into one bin
(deduplicated), but one row can never fan out into many. Gaps stay NaN, and the
"08:20 -> 08:00" rounding intent is preserved.
"""
from __future__ import annotations

from collections import Counter

import pandas as pd

__all__ = ['detect_freq', 'resolve_freq', 'snap_to_grid', 'to_grid']


def detect_freq(index) -> str | None:
    """Infer a frequency string (e.g. ``'6min'``, ``'1h'``) from an index.

    Tries ``inferred_freq`` first (only works for a perfectly regular index),
    then falls back to the median timestamp delta rounded to the nearest
    minute — robust to gaps and jitter. Returns ``None`` when the index has
    fewer than two valid timestamps.
    """
    try:
        idx = pd.DatetimeIndex(pd.to_datetime(index, errors='coerce')).dropna().sort_values()
    except (TypeError, ValueError):
        return None
    if len(idx) < 2:
        return None

    inferred = idx.inferred_freq
    if inferred:
        return pd.tseries.frequencies.to_offset(inferred).freqstr

    median = pd.Series(idx).diff().dropna().median()
    if pd.isna(median):
        return None
    minutes = max(1, round(median.total_seconds() / 60))
    return f'{minutes}min'


def resolve_freq(per_file: dict[str, str | None], *,
                 override: str | None = None,
                 fallback: str | None = None,
                 logger=None) -> tuple[str | None, bool]:
    """Reconcile per-file detected frequencies into one grid frequency.

    Resolution order: ``override`` (user ``raw_freq``) > unanimous detection >
    most-common detection (mixed) > ``fallback`` (instrument config).

    Returns ``(freq, is_mixed)``. ``is_mixed`` is True only when files
    disagreed and the most-common one was chosen; in that case a warning
    listing the breakdown is logged.
    """
    if override:
        return override, False

    detected = {name: freq for name, freq in per_file.items() if freq is not None}
    distinct = set(detected.values())

    if not distinct:
        if logger is not None:
            logger.warning(
                f"Could not detect frequency from any file; using config fallback '{fallback}'.")
        return fallback, False

    if len(distinct) == 1:
        return distinct.pop(), False

    # Mixed resolutions — pick the most common, warn with the breakdown.
    counts = Counter(detected.values())
    chosen, _ = counts.most_common(1)[0]
    if logger is not None:
        breakdown = ', '.join(f'{n}× {fr}' for fr, n in counts.most_common())
        logger.warning(
            f"Mixed time resolution across files ({breakdown}); using most common "
            f"'{chosen}'. Pass raw_freq= to override.")
    return chosen, True


def snap_to_grid(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Round each row's timestamp to the ``freq`` grid and drop duplicate bins.

    Deterministic many-to-one: rows sharing a bin collapse (first wins); a row
    never fans out to multiple bins. Replaces both the legacy ``floor('1min')``
    dedup and the ``reindex(method='nearest')`` snap.
    """
    if df.empty:
        return df
    out = df.copy()
    out.index = pd.DatetimeIndex(out.index).round(freq)
    out = out[~out.index.duplicated(keep='first')]
    return out.sort_index()


def to_grid(df: pd.DataFrame, freq: str, *,
            start=None, end=None, fill_missing: bool = True) -> pd.DataFrame:
    """Snap ``df`` to a regular ``freq`` grid, then place it on a date range.

    ``fill_missing=True`` (default) extends the grid to the requested
    ``[start, end]`` — the historical behaviour, which can pad a short file out
    to a huge mostly-NaN frame. ``fill_missing=False`` clamps the grid to the
    data's own coverage, so the output never extends past what the files
    actually contain (no NaN blow-up) while staying a regular grid.
    """
    df = snap_to_grid(df, freq)
    if df.empty:
        return df

    d0, d1 = df.index[0], df.index[-1]
    if fill_missing:
        lo = pd.Timestamp(start) if start is not None else d0
        hi = pd.Timestamp(end) if end is not None else d1
    else:
        lo = max(pd.Timestamp(start), d0) if start is not None else d0
        hi = min(pd.Timestamp(end), d1) if end is not None else d1

    # Align grid origin to the freq so it lines up with the rounded data.
    lo = lo.floor(freq)
    if hi < lo:
        return df.reindex(pd.DatetimeIndex([], name='time'))

    grid = pd.date_range(lo, hi, freq=freq, name='time')
    return df.reindex(grid)
