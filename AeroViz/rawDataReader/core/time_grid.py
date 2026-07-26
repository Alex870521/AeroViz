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

import numpy as np
import pandas as pd

__all__ = ['detect_freq', 'resolve_freq', 'detect_isolated_dates', 'snap_to_grid', 'to_grid']


def _with_multiplier(offset) -> str:
    """``freqstr`` with an explicit count: ``'1min'``, not ``'min'``.

    pandas omits the multiplier when it is 1, but ``pd.Timedelta('min')`` raises
    ("unit abbreviation w/o a number") — so a bare ``freqstr`` is unsafe to hand to
    any consumer that measures a duration, which is exactly what the completeness
    QC does. Normalising here keeps ``df.attrs['raw_freq']`` readable too.
    """
    return f'{offset.n}{offset.base.freqstr}'


def _freqstr_from_seconds(seconds: int) -> str:
    """Express a whole number of seconds in its largest exact unit.

    ``3600 -> '1h'``, ``360 -> '6min'``, ``115 -> '115s'``. Exact only: a period
    that is not a whole number of minutes stays in seconds rather than being
    rounded to a "nicer" one, because rounding the grid away from the true
    sampling period is what silently drops rows (see ``snap_to_grid``).
    """
    if seconds % 3600 == 0:
        return f'{seconds // 3600}h'
    if seconds % 60 == 0:
        return f'{seconds // 60}min'
    return f'{seconds}s'


#: How many intervals the median needs before second-level precision is
#: believable. Below this the median is dominated by sampling noise — three
#: intervals of a 6-minute instrument can easily median to 370 s — so the
#: estimate is rounded to the nearest minute, as it always was. Above it, jitter
#: is symmetric and the median converges on the true period, which is where the
#: extra precision earns its keep.
_SECONDS_PRECISION_MIN_INTERVALS = 30


def detect_freq(index) -> str | None:
    """Infer a frequency string (e.g. ``'6min'``, ``'115s'``, ``'1h'``) from an index.

    Tries ``inferred_freq`` first (only works for a perfectly regular index),
    then falls back to the median timestamp delta — robust to gaps and jitter.
    Returns ``None`` when the index has fewer than two valid timestamps.

    The fallback resolves to the **nearest second** once there are enough
    intervals to trust that precision, and to the nearest minute below that.
    Rounding everything to a minute — the old behaviour — quietly discarded data
    for any instrument whose period is not a whole number of minutes: an APS
    sampling every 115 s (its `Sample Time` metadata says so) jitters enough to
    miss the ``inferred_freq`` path, so it was gridded at ``'2min'``, and each
    reading drifted 5 s further from its bin until two fell into one and
    ``snap_to_grid`` kept only the first — about 3 % of a day's scans, silently.

    Neither rounding is safe in general (a grid of 370 s against a true 360 s
    drifts just as badly the other way), which is why ``snap_to_grid`` now warns
    whenever rows are actually lost to a collision.
    """
    try:
        idx = pd.DatetimeIndex(pd.to_datetime(index, errors='coerce')).dropna().sort_values()
    except (TypeError, ValueError):
        return None
    if len(idx) < 2:
        return None

    inferred = idx.inferred_freq
    if inferred:
        return _with_multiplier(pd.tseries.frequencies.to_offset(inferred))

    deltas = pd.Series(idx).diff().dropna()
    median = deltas.median()
    if pd.isna(median):
        return None

    seconds = median.total_seconds()
    if len(deltas) < _SECONDS_PRECISION_MIN_INTERVALS:
        return f'{max(1, round(seconds / 60))}min'
    return _freqstr_from_seconds(max(1, round(seconds)))


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


def detect_isolated_dates(index, *, k: float = 10.0,
                          max_frac: float = 0.05,
                          min_rows: int = 10) -> np.ndarray:
    """Flag timestamps sitting far outside the bulk of ``index``.

    A single bad row — e.g. a ``2000-01-01`` stamp in otherwise-2023 data —
    would stretch the native grid across the whole bogus span, ballooning the
    canonical/cached frame into millions of NaN rows even when the caller only
    asked for 2023. This finds such strays with a median / MAD score (robust to
    the strays themselves, unlike a mean or a quantile at small ``n``): a point
    is flagged when its distance from the median timestamp exceeds ``k`` MADs.
    For data spread evenly over a span the edge points score ~2, so the default
    ``k=10`` only trips on genuinely detached stamps.

    Returns a boolean ``np.ndarray`` aligned to ``index`` (True = outlier).
    Flags **nothing** (all-False) when there are too few rows to judge
    (``< min_rows``), when the spread is degenerate, or when the flagged set
    would exceed ``max_frac`` of all rows — that last case being ambiguous
    (legitimately wide or multi-cluster data, not a stray), so it is left alone.
    """
    idx = pd.DatetimeIndex(pd.to_datetime(index, errors='coerce'))
    valid = np.asarray(idx.notna())
    n = int(valid.sum())
    no_outliers = np.zeros(len(idx), dtype=bool)
    if n < min_rows:
        return no_outliers

    vals = idx.asi8.astype('float64')  # ns since epoch (NaT -> sentinel, masked out)
    med = np.median(vals[valid])
    mad = np.median(np.abs(vals[valid] - med))
    if mad <= 0:
        return no_outliers

    score = np.zeros(len(idx), dtype='float64')
    score[valid] = np.abs(vals[valid] - med) / mad
    mask = score > k

    if not mask.any() or mask.sum() > max_frac * n:
        return no_outliers
    return mask


def snap_to_grid(df: pd.DataFrame, freq: str, *, logger=None) -> pd.DataFrame:
    """Round each row's timestamp to the ``freq`` grid and drop duplicate bins.

    Deterministic many-to-one: rows sharing a bin collapse (first wins); a row
    never fans out to multiple bins. Replaces both the legacy ``floor('1min')``
    dedup and the ``reindex(method='nearest')`` snap.

    Collapsing is *usually* what you want — a duplicated or slightly-late reading
    should not occupy two slots. But when the grid does not match the instrument's
    true period, every reading drifts a little further from its bin until two
    land in the same one, and the collapse becomes steady data loss: a 115 s
    instrument on a 2-minute grid loses roughly one scan in twenty-four. That is
    worth a warning rather than silence, so ``logger`` is used to report the
    count and point at ``raw_freq=``.
    """
    if df.empty:
        return df
    out = df.copy()
    out.index = pd.DatetimeIndex(out.index).round(freq)

    collisions = int(out.index.duplicated(keep='first').sum())
    if collisions and logger is not None:
        logger.warning(
            f"{collisions} of {len(out)} rows ({collisions / len(out):.1%}) fell into "
            f"an already-occupied {freq} bin and were dropped (first wins). If the "
            f"instrument's true sampling period is not {freq}, the grid is drifting "
            f"against the data and this loss will continue — pass raw_freq= with the "
            f"real period to stop it.")

    out = out[~out.index.duplicated(keep='first')]
    return out.sort_index()


def to_grid(df: pd.DataFrame, freq: str, *,
            start=None, end=None, fill_missing: bool = True,
            logger=None) -> pd.DataFrame:
    """Snap ``df`` to a regular ``freq`` grid, then place it on a date range.

    ``fill_missing=True`` (default) extends the grid to the requested
    ``[start, end]`` — the historical behaviour, which can pad a short file out
    to a huge mostly-NaN frame. ``fill_missing=False`` clamps the grid to the
    data's own coverage, so the output never extends past what the files
    actually contain (no NaN blow-up) while staying a regular grid.
    """
    df = snap_to_grid(df, freq, logger=logger)
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
