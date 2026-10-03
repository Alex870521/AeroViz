"""``aeroviz`` — the reader from a terminal.

    aeroviz read SMPS /data/NZ_SMPS --start 2026-01-01 --end 2026-01-31 --freq 1h --out nz_smps.nc
    aeroviz inventory SMPS /data/NZ_SMPS
    aeroviz instruments

Everything is the Python API with a thin argparse front: ``read`` is
``RawDataReader``; the output format follows the ``--out`` suffix
(``.csv`` / ``.parquet`` / ``.nc`` / ``.pkl``); ``--report`` writes
``write_qc_report``; ``inventory`` prints the file table and its summary.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

__all__ = ['main', 'build_parser']


def build_parser() -> argparse.ArgumentParser:
    from AeroViz.rawDataReader.core.metadata import aeroviz_version

    p = argparse.ArgumentParser(prog='aeroviz', description=__doc__.split('\n\n')[0])
    p.add_argument('--version', action='version', version=f"AeroViz {aeroviz_version() or 'dev'}")
    sub = p.add_subparsers(dest='command', required=True)

    r = sub.add_parser('read', help='read, QC and resample one instrument folder')
    r.add_argument('instrument')
    r.add_argument('path', type=Path)
    r.add_argument('--start')
    r.add_argument('--end')
    r.add_argument('--freq', dest='mean_freq', help="output frequency, e.g. 1h (default: native)")
    r.add_argument('--no-qc', action='store_true', help='return the parsed L1 frame, no QC')
    mode = r.add_mutually_exclusive_group()
    mode.add_argument('--reset', action='store_true', help='re-parse everything (ignore caches)')
    mode.add_argument('--incremental', action='store_true',
                      help="parse only new/changed files (needs --cache-dir)")
    r.add_argument('--cache-dir', type=Path)
    r.add_argument('--qc-config', type=Path, help='YAML/JSON QC configuration')
    r.add_argument('--workers', type=int, help='threads for raw-file parsing')
    r.add_argument('--out', type=Path, help='write the frame: .csv / .parquet / .nc / .pkl')
    r.add_argument('--report', type=Path, help='write the Markdown QC report here')
    r.add_argument('--quiet', action='store_true', help='suppress the reader console output')

    i = sub.add_parser('inventory', help='list the files of a folder without parsing them')
    i.add_argument('instrument')
    i.add_argument('path', type=Path)
    i.add_argument('--out', type=Path, help='write the file table as .csv / .json')

    sub.add_parser('instruments', help='list the supported instrument names')
    return p


def _write_frame(df, out: Path) -> None:
    suffix = out.suffix.lower()
    out.parent.mkdir(parents=True, exist_ok=True)
    if suffix == '.csv':
        df.to_csv(out)
    elif suffix == '.parquet':
        # pandas stores df.attrs as JSON in the parquet schema; Timestamps and
        # the QC tables are not JSON-native, so hand it a serialisable copy.
        from AeroViz.rawDataReader.netcdf import _attr_value
        safe = df.copy(deep=False)
        safe.attrs = {k: v for k, v in ((k, _attr_value(v)) for k, v in df.attrs.items()) if v is not None}
        try:
            safe.to_parquet(out)
        except ImportError as e:
            raise SystemExit(f'.parquet needs pyarrow: pip install pyarrow ({e})')
    elif suffix == '.nc':
        from AeroViz.rawDataReader.netcdf import to_netcdf
        to_netcdf(df, out)
    elif suffix in ('.pkl', '.pickle'):
        df.to_pickle(out)
    else:
        raise SystemExit(f'unsupported --out suffix {out.suffix!r}; use .csv, .parquet, .nc or .pkl')


def _summary_lines(df) -> list[str]:
    a = df.attrs
    lines = [f"{a.get('station', '?')} {a.get('instrument', '?')}: {len(df)} rows × {df.shape[1]} columns",
             f"  files: {a.get('n_files')}  native: {a.get('raw_freq')}  output: {a.get('mean_freq') or 'native'}",
             f"  coverage: {a.get('coverage_start')} → {a.get('coverage_end')}"]
    if a.get('qc_applied'):
        lines.append(f"  rates: acquisition {a.get('acquisition_rate')}%  yield {a.get('yield_rate')}%  "
                     f"total {a.get('total_rate')}%")
    if a.get('parse_cache_hits') is not None:
        lines.append(f"  parse cache: {a.get('parse_cache_hits')} reused, {a.get('parse_cache_parsed')} parsed")
    return lines


def _cmd_read(ns) -> int:
    from AeroViz import RawDataReader, write_qc_report
    kwargs = dict(instrument=ns.instrument, path=ns.path, start=ns.start, end=ns.end,
                  mean_freq=ns.mean_freq, qc=not ns.no_qc, quiet=ns.quiet)
    if ns.reset:
        kwargs['reset'] = True
    elif ns.incremental:
        if not ns.cache_dir:
            raise SystemExit('--incremental needs --cache-dir')
        kwargs['reset'] = 'incremental'
    if ns.cache_dir:
        kwargs['cache_dir'] = ns.cache_dir
    if ns.qc_config:
        kwargs['qc_config'] = ns.qc_config
    if ns.workers:
        kwargs['parse_workers'] = ns.workers
    df = RawDataReader(**kwargs)
    print('\n'.join(_summary_lines(df)))
    if ns.out:
        _write_frame(df, ns.out)
        print(f'  wrote {ns.out}')
    if ns.report:
        write_qc_report(df, ns.report)
        print(f'  report {ns.report}')
    return 0


def _cmd_inventory(ns) -> int:
    from AeroViz import inventory
    df = inventory(ns.instrument, ns.path)
    summary = df.attrs.get('summary', {})
    show = df.drop(columns=['size_bytes'], errors='ignore').copy()
    if 'modified' in show:
        show['modified'] = show['modified'].astype(str).str.slice(0, 16)
    print(show.to_string(index=False, max_rows=200) if len(df) else f'no files in {ns.path}')
    print()
    for key, value in summary.items():
        print(f'{key}: {value}')
    if ns.out:
        ns.out.parent.mkdir(parents=True, exist_ok=True)
        if ns.out.suffix.lower() == '.json':
            ns.out.write_text(json.dumps({'files': json.loads(df.to_json(orient='records', date_format='iso')),
                                          'summary': summary}, indent=2, default=str), encoding='utf-8')
        else:
            df.to_csv(ns.out, index=False)
        print(f'wrote {ns.out}')
    return 0


def _cmd_instruments(ns) -> int:
    from AeroViz.rawDataReader.config.supported_instruments import meta
    for name, info in meta.items():
        print(f"{name:10s} {info.get('freq', ''):6s} {' '.join(info.get('pattern', []))}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)
    return {'read': _cmd_read, 'inventory': _cmd_inventory, 'instruments': _cmd_instruments}[ns.command](ns)


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
