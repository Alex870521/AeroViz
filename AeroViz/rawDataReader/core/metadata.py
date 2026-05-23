"""
Reader metadata helpers — attach provenance / coverage / QC summary to a
returned DataFrame via ``df.attrs``.

Why ``attrs`` and why stamp only at the end
-------------------------------------------
``RawDataReader`` reindex-pads its output to the *requested* time range, so the
returned frame can be mostly NaN and the user has no direct way to learn what
the underlying files actually covered. ``df.attrs`` is the natural channel for
that out-of-band metadata: it survives ``to_pickle`` / ``read_pickle``,
``resample``, slicing, ``reindex`` and column selection in pandas >= 2.

The one operation that *drops* attrs is ``concat`` when the two frames carry
conflicting attrs (the append path concatenates old + new data with different
coverage). We therefore never try to thread attrs through the pipeline — we
compute everything once and stamp the final object right before returning.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

import pandas as pd

__all__ = ['data_coverage', 'stamp_attrs', 'aeroviz_version']


def aeroviz_version() -> str | None:
    """Installed AeroViz version, or ``None`` if it cannot be resolved."""
    try:
        return version('AeroViz')
    except PackageNotFoundError:
        return None


def data_coverage(df: pd.DataFrame) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    """First and last timestamps that actually carry data.

    Ignores the NaN reindex-padding and the ``QC_Flag`` column, so the result
    reflects the true span of the underlying files regardless of how wide a
    range the caller requested. Returns ``(None, None)`` for an empty frame or
    one with no non-null rows.
    """
    if df.empty:
        return None, None
    valid = df.drop(columns=['QC_Flag'], errors='ignore').dropna(how='all')
    if valid.empty:
        return None, None
    return valid.index.min(), valid.index.max()


def stamp_attrs(df: pd.DataFrame, **meta) -> pd.DataFrame:
    """Write reader metadata into ``df.attrs`` in place and return ``df``.

    ``None`` values are skipped so callers can pass optional fields
    unconditionally. Call this once, on the final object, after every
    transformation (resample / concat / reindex) is done.
    """
    df.attrs.update({key: value for key, value in meta.items() if value is not None})
    return df
