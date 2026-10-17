"""The terminal view of a read: a header before it, one grouped summary after.

During the read the console shows only the header and the progress bar. Every
message the reader logs still goes to ``{instrument}.log`` as it happens; the
console copies are held back (``ReaderLogger.records``) and rendered here in
fixed sections, each saying what it counts:

- **Files**   how many files, how many used / skipped / converted, one line
  per kind of problem with the files it concerns (full list in the log);
- **QC**      over all scans read: valid share, then the rules that hit;
- **Coverage** over the requested period: rates, timeline, longest gaps;
- **Output**  the files this run wrote, as clickable links.

Messages tagged with ``group=`` (see ``ReaderLogger.info/warning``) are folded
by group; anything else at WARNING or above is listed under *Notes*.
"""
from __future__ import annotations

import logging
from collections import OrderedDict
from pathlib import Path

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text

__all__ = ['print_header', 'print_summary']

LABEL = 12          # width of the section label column
SHOWN_FILES = 3     # file names listed per group before "+N more"
SHOWN_EVENTS = 3    # longest downtime events listed
SHOWN_NOTES = 5


def _console() -> Console:
    return Console(highlight=False)


def _section(console: Console, label: str, text: str = '') -> None:
    console.print(f'[bold cyan]{label:<{LABEL}}[/bold cyan]{text}', soft_wrap=True)


def _indent(console: Console, text: str, depth: int = 1) -> None:
    console.print(' ' * (2 * depth) + text, soft_wrap=True)


def _n(count: int, word: str) -> str:
    """``_n(1, 'file')`` → ``'1 file'``; ``_n(3, 'file')`` → ``'3 files'``."""
    return f'{count:,} {word}' + ('' if count == 1 else 's')


def _file_link(folder: Path, name: str) -> str:
    path = (Path(folder) / name).resolve()
    return f'[link={path.as_uri()}]{escape(name)}[/link]'


def _files(folder: Path, names: list[str]) -> str:
    shown = ', '.join(_file_link(folder, n) for n in names[:SHOWN_FILES])
    more = len(names) - SHOWN_FILES
    return shown + (f' [dim]+{more} more (see log)[/dim]' if more > 0 else '')


def print_header(instrument: str, path: Path, start=None, end=None) -> None:
    """Printed before the read starts, above the progress bar."""
    def fmt(t):
        return 'start' if t is None else str(t)[:16].replace('T', ' ')
    path = Path(path)
    console = _console()
    console.print()
    console.print(Panel(Text(f'{fmt(start)} → {fmt(end)}'),
                        title=f'[bold]{escape(instrument)}[/bold] · {escape(path.name)}',
                        title_align='left', expand=False, padding=(0, 2)))


# ---- grouping the held-back messages ----------------------------------------

def _grouped(records: list[logging.LogRecord]):
    groups: dict[str, list[dict]] = OrderedDict()
    notes: list[logging.LogRecord] = []
    for r in records:
        notice = getattr(r, 'notice', None)
        if notice and notice.get('group'):
            groups.setdefault(notice['group'], []).append(notice)
        elif r.levelno >= logging.WARNING:
            notes.append(r)
    return groups, notes


def _names(notice: dict) -> list[str]:
    if notice.get('items'):
        return list(notice['items'])
    return [notice['item']] if notice.get('item') else []


def _items(notices: list[dict]) -> list[str]:
    return list(OrderedDict.fromkeys(name for n in notices for name in _names(n)))


def _by_detail(notices: list[dict]) -> 'OrderedDict[str, list[str]]':
    by = OrderedDict()
    for n in notices:
        names = _names(n)
        by.setdefault(n.get('detail') or '', []).extend(names)
    return OrderedDict((k, list(OrderedDict.fromkeys(v))) for k, v in by.items())


def _files_section(console, reader, groups, notes) -> None:
    folder = reader.path
    grid_skipped = _items(groups.get('grid_skipped', []))
    unit_skipped = _items(groups.get('unit_skipped', []))
    read_error = _items(groups.get('read_error', []))
    excluded = _items(groups.get('excluded', []))      # by design, e.g. calibration samples
    empty = list(getattr(reader, '_empty_files', []) or [])
    # An empty result from a file that was skipped or excluded for a reason is not "empty".
    empty = [n for n in empty if n not in set(unit_skipped) | set(read_error) | set(excluded)]
    skipped = set(grid_skipped) | set(unit_skipped) | set(read_error) | set(empty)
    converted = _items(groups.get('converted', []))

    n_files = getattr(reader, '_n_files', None)
    if n_files is None:
        summary = 'read from cache'
    else:
        parts = [_n(n_files, 'file'), f'{n_files - len(skipped) - len(excluded):,} used']
        if excluded:
            parts.append(f'{len(excluded):,} excluded')
        if skipped:
            parts.append(f'[yellow]{len(skipped):,} skipped[/yellow]')
        if converted:
            parts.append(f'{len(converted)} converted')
        summary = ' · '.join(parts)
    _section(console, 'Files', summary)

    def block(icon, title, by_detail):
        _indent(console, f'{icon} {title}')
        width = max((len(d) for d in by_detail), default=0)
        for detail, names in by_detail.items():
            _indent(console, f'[dim]{escape(detail):<{width}}[/dim]  {_files(folder, names)}', depth=3)

    if grid_skipped:
        block('[yellow]⚠[/yellow]', f'skipped {_n(len(grid_skipped), "file")} on a different size-bin grid '
              '[dim](read them alone with size_range=)[/dim]', _by_detail(groups['grid_skipped']))
    if unit_skipped:
        block('[yellow]⚠[/yellow]', f'skipped {_n(len(unit_skipped), "file")} whose unit cannot be '
              'converted to dN/dlogDp [dim](re-export from AIM)[/dim]', _by_detail(groups['unit_skipped']))
    if read_error:
        block('[red]✗[/red]', f'{_n(len(read_error), "file")} could not be read', _by_detail(groups['read_error']))
    if groups.get('rows_dropped'):
        dropped = groups['rows_dropped']
        _indent(console, f'[yellow]⚠[/yellow] dropped rows that cannot be converted in {_n(len(dropped), "file")}')
        for n in dropped[:SHOWN_FILES]:
            _indent(console, f'{_file_link(folder, n["item"])}  [dim]{escape(n.get("detail", ""))}[/dim]', depth=3)
        if len(dropped) > SHOWN_FILES:
            _indent(console, f'[dim]+{len(dropped) - SHOWN_FILES} more (see log)[/dim]', depth=3)
    if converted:
        block('[cyan]ℹ[/cyan]', f'converted {_n(len(converted), "file")} to dN/dlogDp',
              OrderedDict((f'from {d}', v) for d, v in _by_detail(groups['converted']).items()))
    off_grid = [n for n in groups.get('grid', []) if n.get('item') not in set(grid_skipped)]
    if off_grid:
        expected = off_grid[0].get('expected', '')
        block('[cyan]ℹ[/cyan]', f'{_n(len(off_grid), "file")} on a grid other than {expected} (kept)',
              _by_detail(off_grid))
    if excluded:
        block('[dim]·[/dim]', f'excluded {_n(len(excluded), "file")} by design',
              _by_detail(groups['excluded']))
    if empty:
        _indent(console, f'[dim]· {_n(len(empty), "file")} held no data: {_files(folder, empty)}[/dim]')

    if notes:
        unique = list(OrderedDict.fromkeys(r.getMessage() for r in notes))
        _section(console, 'Notes')
        for msg in unique[:SHOWN_NOTES]:
            icon = '[red]✗[/red]' if any(r.levelno >= logging.ERROR and r.getMessage() == msg for r in notes) \
                else '[yellow]⚠[/yellow]'
            _indent(console, f'{icon} {escape(msg)}')
        if len(unique) > SHOWN_NOTES:
            _indent(console, f'[dim]+{len(unique) - SHOWN_NOTES} more (see log)[/dim]')


# ---- QC ---------------------------------------------------------------------

def _pct(value) -> float | None:
    try:
        return float(str(value).rstrip('%'))
    except (TypeError, ValueError):
        return None


def _qc_section(console, reader) -> None:
    from AeroViz.rawDataReader.core.qc import WARNING
    summary = getattr(reader, '_qc_summary_final', None)
    if summary is None or summary.empty:
        return
    rows = summary.to_dict('records')
    total = next((round(int(r['Count']) * 100 / p) for r in rows
                  if int(r['Count']) > 0 and (p := _pct(r['Percentage']))), None)
    by_rule = {r['Rule']: r for r in rows}
    _section(console, 'QC', f'[dim]all scans read{f" ({total:,})" if total else ""}[/dim]')

    def line(name, count, pct, note='', style=''):
        bar = '█' * max(1, round(pct / 5)) if pct and count else ''
        text = f'{escape(name):<22}{count:>9,}  {pct:5.1f}%  [{style or "dim"}]{bar}[/{style or "dim"}]'
        _indent(console, text + (f'  [dim]{note}[/dim]' if note else ''))

    valid = by_rule.get('Valid')
    if valid is not None:
        line('Valid', int(valid['Count']), _pct(valid['Percentage']) or 0, style='green')
    hits = sorted((r for r in rows if r['Rule'] not in ('Valid', 'Usable') and int(r['Count']) > 0),
                  key=lambda r: -int(r['Count']))
    for r in hits:
        advisory = r.get('Severity') == WARNING
        line(r['Rule'], int(r['Count']), _pct(r['Percentage']) or 0,
             note='advisory, data kept' if advisory else '', style='yellow' if advisory else 'red')
    usable = by_rule.get('Usable')
    if usable is not None and valid is not None and int(usable['Count']) != int(valid['Count']):
        line('Usable', int(usable['Count']), _pct(usable['Percentage']) or 0,
             note='valid + advisory only', style='green')
    silent = sum(1 for r in rows if r['Rule'] not in ('Valid', 'Usable') and int(r['Count']) == 0)
    if silent:
        _indent(console, f"[dim]{silent} rule{'s' if silent != 1 else ''} with no hits not shown[/dim]")


# ---- coverage ---------------------------------------------------------------

def _coverage_section(console, reader, mean_freq) -> None:
    from AeroViz.rawDataReader.core.report import timeline_summary
    rates = getattr(reader, 'overall_rates', None)
    timeline = getattr(reader, '_timeline', None)
    if not rates and not timeline:
        return
    report = getattr(reader, 'report_dict', {}) or {}
    period = f"{report.get('startDate', '?')} → {report.get('endDate', '?')}"
    _section(console, 'Coverage', f'[dim]{escape(period)}, hourly[/dim]')
    if rates:
        _indent(console, f"Acquisition {rates.get('acquisition_rate', 0):.1f}%   "
                         f"Yield {rates.get('yield_rate', 0):.1f}%   "
                         f"Total [bold]{rates.get('total_rate', 0):.1f}%[/bold]")
    width = max(20, min(60, console.width - 2 * 2 - 14))
    tl = timeline_summary(timeline, report.get('startDate'), report.get('endDate'), width=width) \
        if timeline else None
    if tl is None:
        return
    bar = Text('  ')
    bar.append(tl['start'].strftime('%m/%d') + ' ', style='dim')
    bar.append_text(tl['bar'])
    bar.append(' ' + tl['end'].strftime('%m/%d'), style='dim')
    console.print(bar, soft_wrap=True)
    events = tl['down_events']
    # The same glyphs and colours as the bar, so the line doubles as its legend.
    _indent(console, f"[green]█[/green] up {tl['operational_hours']:,.0f} h · "
                     f"[red]░[/red] down {tl['down_hours']:,.0f} h"
                     f" in {len(events)} event{'s' if len(events) != 1 else ''}")
    if events:
        def hours(e):
            return (_when(e['end']) - _when(e['start'])).total_seconds()
        longest = sorted(events, key=hours, reverse=True)[:SHOWN_EVENTS]
        title = 'longest gap' if len(events) == 1 else f'longest {len(longest)} gaps'
        _indent(console, f'[dim]{title}:[/dim]')
        for e in longest:
            _indent(console, f"{e['start']} → {e['end']}  [bold]{escape(str(e.get('duration') or ''))}[/bold]"
                             f"  [dim]{escape(str(e.get('reason') or ''))}[/dim]", depth=2)
        if len(events) > SHOWN_EVENTS:
            _indent(console, f'[dim]+{len(events) - SHOWN_EVENTS} more in report.json[/dim]', depth=2)


def _when(text: str):
    from datetime import datetime
    for fmt in ('%Y/%m/%d %H:%M', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f'unrecognised timeline time {text!r}')


# ---- entry point --------------------------------------------------------------

def print_summary(reader, *, started: float, mean_freq=None, failed: bool = False) -> None:
    """Render the held-back messages and the run's results (after the read).

    With ``failed`` (the read raised), only what was gathered up to the failure
    is shown — the files section and notes — so the error has its context.
    """
    from AeroViz.rawDataReader.core.output_links import print_output_files

    console = _console()
    records = getattr(reader.logger, 'records', [])
    groups, notes = _grouped(records)
    console.print()
    _files_section(console, reader, groups, notes)
    if failed:
        console.print()
        records.clear()
        return
    if getattr(reader, 'qc', False):
        console.print()
        _qc_section(console, reader)
        console.print()
        _coverage_section(console, reader, mean_freq)
    print_output_files(reader._output_folder, since=started, console=console)
    records.clear()
