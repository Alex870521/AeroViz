"""QC configuration — thresholds, whitelists, severities and outlier windows
from one file instead of per-call kwargs and code edits.

Why a file: a station's QC is a set of decisions (which status tokens are
benign on *this* CPC, what the realistic BC ceiling is, when the dryer fell
off) that today live in three places — reader class constants, `RawDataReader`
kwargs and an `outlier.json` next to the raw files. A YAML/JSON document keeps
them together, under version control, and lets a pipeline apply the same
decisions on every run. The resolved result is stamped into ``df.attrs``.

Schema (every key optional)::

    defaults:                        # applies to every instrument
      flag_severity: {Insufficient: warning}
    SMPS:                            # per instrument
      thresholds: {MAX_TOTAL_CONC: 5.0e5}      # reader class constants
      ignored_status_errors: [Low aerosol flow]
      flag_severity: {Spike: warning}
      outliers:                                 # masked like outlier.json
        - ["2026-01-26 00:00", "2026-02-02 23:59"]
      stations:                                 # per station, deepest wins
        TP: {ignored_status_errors: [Low aerosol flow, Neutralizer not active]}

Precedence: ``defaults`` < instrument < instrument.stations[<station>] <
explicit ``RawDataReader`` kwargs. The station is the first two letters of
the folder name (``NZ_SMPS`` → ``NZ``), the same rule ``df.attrs['station']``
uses. ``thresholds`` names must be existing upper-case constants of the reader
class (``MAX_BC``, ``MIN_TOTAL_CONC``, …); anything else is an error, so a typo
cannot look applied.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = ['load_qc_config', 'resolve_qc_config', 'apply_qc_config', 'QC_CONFIG_KEYS']

#: Keys a resolved section may contain.
QC_CONFIG_KEYS = ('thresholds', 'ignored_status_errors', 'flag_severity', 'outliers')


def load_qc_config(source) -> dict:
    """A dict passes through; a path is read as JSON or YAML by extension."""
    if source is None:
        return {}
    if isinstance(source, dict):
        return source
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"qc_config file not found: {path}")
    text = path.read_text(encoding='utf-8')
    if path.suffix.lower() in ('.yaml', '.yml'):
        import yaml  # PyYAML is a declared dependency
        return yaml.safe_load(text) or {}
    return json.loads(text) if text.strip() else {}


def _merge(base: dict, over: dict) -> dict:
    out = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v)
           for k, v in base.items()}
    for key, value in (over or {}).items():
        if key == 'stations':
            continue
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = {**out[key], **value}
        elif isinstance(value, list) and isinstance(out.get(key), list) and key != 'outliers':
            # whitelists accumulate; outlier windows are replaced per level
            out[key] = list(dict.fromkeys([*out[key], *value]))
        else:
            out[key] = value
    return out


def resolve_qc_config(config: dict, instrument: str, station: str | None) -> dict:
    """``defaults`` → instrument → instrument.stations[station], merged."""
    if not config:
        return {}
    unknown = set(config.get('defaults', {})) - set(QC_CONFIG_KEYS)
    if unknown:
        raise ValueError(f"qc_config.defaults: unknown keys {sorted(unknown)}; allowed {QC_CONFIG_KEYS}")
    resolved = _merge({}, config.get('defaults', {}))
    section = config.get(instrument) or {}
    unknown = set(section) - set(QC_CONFIG_KEYS) - {'stations'}
    if unknown:
        raise ValueError(f"qc_config.{instrument}: unknown keys {sorted(unknown)}; allowed {QC_CONFIG_KEYS + ('stations',)}")
    resolved = _merge(resolved, section)
    if station and isinstance(section.get('stations'), dict):
        resolved = _merge(resolved, section['stations'].get(station) or {})
    return {k: v for k, v in resolved.items() if v not in (None, {}, [])}


def apply_qc_config(reader, resolved: dict, source: Any = None) -> dict:
    """Push the resolved section onto a reader instance.

    Thresholds become instance attributes shadowing the class constants the
    reader's ``_QC`` reads through ``self.X``; outlier windows are kept for
    ``_outlier_process``. Whitelist and severities are merged into kwargs by
    the factory *before* construction, so here they are only recorded.
    Returns the record that goes into ``df.attrs['qc_config']``.
    """
    applied = {'source': str(source) if source is not None and not isinstance(source, dict) else 'dict'}
    thresholds = resolved.get('thresholds') or {}
    for name, value in thresholds.items():
        if not (name.isupper() and hasattr(type(reader), name)):
            known = sorted(n for n in dir(type(reader)) if n.isupper() and not n.startswith('_'))
            raise ValueError(f"qc_config thresholds: {type(reader).nam} has no constant {name!r}; known: {known}")
        setattr(reader, name, value)
    if thresholds:
        applied['thresholds'] = dict(thresholds)
    outliers = []
    for window in resolved.get('outliers') or []:
        if not (isinstance(window, (list, tuple)) and len(window) == 2):
            raise ValueError(f"qc_config outliers: each entry must be [start, end]; got {window!r}")
        outliers.append((str(window[0]), str(window[1])))
    reader._config_outliers = outliers
    if outliers:
        applied['outliers'] = [list(w) for w in outliers]
    for key in ('ignored_status_errors', 'flag_severity'):
        if resolved.get(key):
            applied[key] = resolved[key]
    reader._qc_config_applied = applied
    return applied
