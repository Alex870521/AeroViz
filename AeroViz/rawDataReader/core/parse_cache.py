"""Per-file parse cache — the incremental half of ``RawDataReader``.

``_read_raw_files`` parses every raw file in the folder on every run. For a
folder that only grows (a station uploading one file a day) that re-parses a
year of history to pick up one new file. This cache remembers each file's
parsed frame, keyed by what would make the parse different, so a later run
parses only files that are new or changed and loads the rest.

What it is **not**: it does not cache the merged frame, QC, gridding or
resampling — those still run on the full series every call (they are cheap,
and QC rules are row-wise, so the result is identical to a cold parse). The
whole-frame pkl under ``{instrument}_outputs/`` is a separate, older layer.

Layout::

    <cache_dir>/<INSTRUMENT>/<source-folder hash>/<entry hash>.pkl

One sub-folder per source folder so pruning (dropping entries whose raw file
disappeared or changed) never touches another dataset's entries. Entries are
pandas pickles of the per-file frame; the frame's ``attrs['parse_meta']`` holds
whatever the reader wants restored on a hit (SMPS: the CPC detector fields).

Entries are pickles written by this process into a directory the caller
owns (a local scratch path). Loading a pickle runs code, so ``cache_dir``
must never point at a location other people write to.

Invalidation is by key, not by time: file name, size, mtime_ns, the reader
class, the installed AeroViz version, ``PARSE_CACHE_FORMAT`` and a reader-
supplied salt (parse-affecting kwargs). Any of those changing is a miss.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from AeroViz.rawDataReader.core.metadata import aeroviz_version

#: Bump when the cached per-file frame's layout or meaning changes.
PARSE_CACHE_FORMAT = 1


class ParseCache:
    """Per-file cache for one reader over one source folder."""

    def __init__(self, root: Path | str, reader_name: str, source: Path, salt: str = ''):
        self.root = Path(root)
        self.reader_name = reader_name
        self.source = Path(source).resolve()
        self.salt = salt
        self._version = aeroviz_version() or 'unknown'
        folder_tag = hashlib.sha1(str(self.source).encode()).hexdigest()[:12]
        self.dir = self.root / reader_name / folder_tag
        self.hits = 0
        self.parsed = 0
        self._used: set[Path] = set()

    # ---- keys -------------------------------------------------------------
    def key(self, file: Path) -> Optional[str]:
        try:
            st = file.stat()
        except OSError:
            return None
        raw = '|'.join((
            file.name, str(st.st_size), str(st.st_mtime_ns),
            self.reader_name, self._version, str(PARSE_CACHE_FORMAT), self.salt,
        ))
        return hashlib.sha1(raw.encode()).hexdigest()

    def path_for(self, file: Path) -> Optional[Path]:
        k = self.key(file)
        return None if k is None else self.dir / f'{k}.pkl'

    # ---- read / write -----------------------------------------------------
    def load(self, file: Path) -> Optional[pd.DataFrame]:
        """The cached frame for ``file`` if its key still matches, else None."""
        p = self.path_for(file)
        if p is None or not p.is_file():
            return None
        try:
            df = pd.read_pickle(p)
        except Exception:
            # A damaged entry is just a miss; the re-parse overwrites it.
            return None
        self._used.add(p)
        self.hits += 1
        return df

    def store(self, file: Path, df: pd.DataFrame, meta: Optional[dict] = None) -> None:
        p = self.path_for(file)
        if p is None:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        if meta:
            df.attrs['parse_meta'] = meta
        tmp = p.with_suffix('.pkl.tmp')
        df.to_pickle(tmp)
        os.replace(tmp, p)
        self._used.add(p)
        self.parsed += 1

    def prune(self) -> int:
        """Delete entries this run did not touch (raw file gone or changed)."""
        if not self.dir.is_dir():
            return 0
        removed = 0
        for p in self.dir.glob('*.pkl'):
            if p not in self._used:
                try:
                    p.unlink()
                    removed += 1
                except OSError:
                    pass
        return removed

    def summary(self) -> dict:
        return {'hits': self.hits, 'parsed': self.parsed, 'dir': str(self.dir)}
