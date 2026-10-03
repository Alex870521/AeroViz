"""``write_qc_report`` — a human-readable QC report from a reader result.

Everything it needs is already on ``df.attrs``: provenance, the overall rates,
which rules fired and how often (``qc_rules``), which status conditions were
set (``status_conditions``) and the QC configuration that was applied. The
report adds a month-by-month availability table computed from the frame. It
is Markdown — readable raw, pasteable into an issue, renderable anywhere.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

__all__ = ['write_qc_report', 'qc_report_markdown']


def _pct(x):
    return '—' if x is None or (isinstance(x, float) and pd.isna(x)) else f'{float(x):.1f}%'


def _table(rows: list[dict], columns: list[str], headers: list[str]) -> str:
    out = ['| ' + ' | '.join(headers) + ' |', '|' + '|'.join('---' for _ in headers) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(r.get(c, '') if r.get(c) is not None else '') for c in columns) + ' |')
    return '\n'.join(out)


def qc_report_markdown(df: pd.DataFrame, title: str | None = None) -> str:
    a = df.attrs
    inst, station = a.get('instrument', '?'), a.get('station', '?')
    lines = [f"# {title or f'{station} {inst} — QC report'}", '']
    lines += [
        f"- Source: `{a.get('source_path', '?')}` ({a.get('n_files', '?')} files)",
        f"- Requested: {a.get('requested_start')} → {a.get('requested_end')}",
        f"- Coverage: {a.get('coverage_start')} → {a.get('coverage_end')}",
        f"- Native frequency: {a.get('raw_freq')}" + (" (mixed)" if a.get('freq_mixed') else '')
        + f"; output: {a.get('mean_freq') or 'native'}",
        f"- AeroViz {a.get('aeroviz_version')} · processed {a.get('processed_at')}",
        '',
    ]
    if a.get('qc_applied'):
        lines += ['## Rates', '',
                  f"- Acquisition: {_pct(a.get('acquisition_rate'))}",
                  f"- Yield (passed QC of acquired): {_pct(a.get('yield_rate'))}",
                  f"- Total (valid of requested): {_pct(a.get('total_rate'))}", '']
    rules = a.get('qc_rules') or []
    if rules:
        lines += ['## QC rules', '',
                  _table([{**r, 'percentage': _pct(r.get('percentage'))} for r in rules],
                         ['rule', 'severity', 'count', 'percentage', 'description'],
                         ['Rule', 'Severity', 'Rows', 'Share', 'Description']), '']
    conds = a.get('status_conditions')
    if conds:
        cols = list(conds[0].keys())
        lines += ['## Instrument status conditions', '',
                  _table([{**c, 'percentage': _pct(c.get('percentage'))} if 'percentage' in c else c for c in conds],
                         cols, [c.replace('_', ' ').title() for c in cols]), '']
    # Month-by-month availability from the frame itself
    numeric = df.select_dtypes('number')
    if isinstance(df.index, pd.DatetimeIndex) and not numeric.empty:
        has = numeric.notna().any(axis=1)
        by_month = has.groupby(df.index.to_period('M'))
        rows = [{'month': str(m), 'rows': int(g.size), 'with_data': int(g.sum()),
                 'share': _pct(100 * g.mean() if g.size else None)} for m, g in by_month]
        lines += ['## Availability by month', '',
                  _table(rows, ['month', 'rows', 'with_data', 'share'], ['Month', 'Rows', 'With data', 'Share']), '']
    cfg = a.get('qc_config')
    if cfg:
        lines += ['## QC configuration applied', '', '```json', json.dumps(cfg, indent=2, default=str, ensure_ascii=False), '```', '']
    return '\n'.join(lines).rstrip() + '\n'


def write_qc_report(df: pd.DataFrame, path: Path | str, title: str | None = None) -> Path:
    """Write the Markdown QC report for ``df`` (a ``RawDataReader`` result) to ``path``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(qc_report_markdown(df, title), encoding='utf-8')
    return path
