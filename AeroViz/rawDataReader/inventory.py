"""``inventory()`` — what is in a raw-data folder, without parsing it.

``RawDataReader`` answers "what do these files say"; this answers "what files
are these" — cheaply enough to run on a whole archive. For every regular file
it reports size, mtime, whether the instrument's glob would pick it up, the
date encoded in the file name, and whatever the reader can tell from the first
lines (SMPS: AIM version, bin grid, row- or column-oriented export; AE33:
backfill dumps; OCEC: results files with no samples). Those are exactly the
things that, left unnoticed, make a read silently wrong: a stray file in the
wrong grid, a transposed export the parser skips, a backfill that fails every
run.

Returns a DataFrame (one row per file) with a summary in ``df.attrs``.
"""
from __future__ import annotations

import fnmatch
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from AeroViz.rawDataReader.config.supported_instruments import meta

__all__ = ['inventory']

#: Date patterns seen in instrument file names, tried in order.
_NAME_DATES = (
    (re.compile(r'(?<!\d)(20\d{2})[-_]?(\d{2})[-_]?(\d{2})(?!\d)'), '%Y%m%d'),   # 20250305, 2025-03-05
    (re.compile(r'(?<!\d)(\d{2})(\d{2})(\d{2})(?!\d)'), '%y%m%d'),               # 250107 (AIM short form)
)


def _date_from_name(name: str):
    for pattern, fmt in _NAME_DATES:
        m = pattern.search(name)
        if not m:
            continue
        try:
            return datetime.strptime(''.join(m.groups()), fmt).date()
        except ValueError:
            continue
    return None


def _matches(name: str, patterns) -> bool:
    return any(fnmatch.fnmatch(name, p) or fnmatch.fnmatch(name.lower(), p.lower())
               for p in patterns)


def _reader_class(instrument: str):
    import AeroViz.rawDataReader.script as script_module
    if instrument not in meta or not hasattr(script_module, instrument):
        raise KeyError(f"Instrument name '{instrument}' is not valid. Must be one of: {sorted(meta)}")
    return getattr(script_module, instrument).Reader


def inventory(instrument: str, path: Path | str) -> pd.DataFrame:
    """Describe the files in ``path`` for ``instrument`` without parsing them.

    Parameters
    ----------
    instrument : str
        Reader name, as for ``RawDataReader``.
    path : Path or str
        Folder of raw files (not recursive — neither is the reader).

    Returns
    -------
    DataFrame
        One row per regular file, sorted by name: ``file``, ``matched`` (the
        reader's glob would read it), ``size_bytes``, ``modified``,
        ``date_in_name``, plus reader-specific columns from its sniff hook
        (e.g. SMPS ``format`` / ``layout`` / ``bins`` / ``grid``).
        ``df.attrs['summary']`` holds the totals: file counts, bytes, the span
        of dates in the names, the distinct-day count, and the value counts of
        every sniffed column.
    """
    path = Path(path)
    if not path.is_dir():
        raise FileNotFoundError(f"{path} is not a directory")
    cls = _reader_class(instrument)
    patterns = meta[instrument]['pattern']
    sniff = getattr(cls, '_inventory_sniff', None)

    rows = []
    for f in sorted(p for p in path.iterdir() if p.is_file() and not p.name.startswith('.')):
        st = f.stat()
        row = {
            'file': f.name,
            'matched': _matches(f.name, patterns),
            'size_bytes': st.st_size,
            'modified': datetime.fromtimestamp(st.st_mtime),
            'date_in_name': _date_from_name(f.name),
        }
        if row['matched'] and sniff is not None:
            try:
                row.update(sniff(f) or {})
            except Exception as e:  # a sniff must never break the inventory
                row['note'] = f'sniff failed: {e}'
        rows.append(row)

    df = pd.DataFrame(rows)
    base_cols = ['file', 'matched', 'size_bytes', 'modified', 'date_in_name']
    if df.empty:
        df = pd.DataFrame(columns=base_cols)
    extra = [c for c in df.columns if c not in base_cols]

    matched = df[df['matched']] if not df.empty else df
    dates = matched['date_in_name'].dropna() if not df.empty else pd.Series(dtype=object)
    summary = {
        'instrument': instrument,
        'path': str(path),
        'n_files': int(len(df)),
        'n_matched': int(matched.shape[0]),
        'n_unmatched': int(len(df) - matched.shape[0]),
        'total_bytes': int(matched['size_bytes'].sum()) if not df.empty else 0,
        'date_min': str(dates.min()) if len(dates) else None,
        'date_max': str(dates.max()) if len(dates) else None,
        'distinct_days': int(dates.nunique()) if len(dates) else 0,
        'variants': {c: {str(k): int(v) for k, v in matched[c].value_counts(dropna=True).items()}
                     for c in extra if c != 'note' and not matched.empty},
    }
    df.attrs['summary'] = summary
    return df
