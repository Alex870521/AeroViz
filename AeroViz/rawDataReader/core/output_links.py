"""List the files a read wrote, as clickable links in the terminal.

Paths in the TCLab repository carry spaces and CJK characters, so a terminal
that auto-detects paths stops at the first space. A ``file://`` URI wrapped in
an OSC 8 hyperlink (what ``rich`` emits for ``[link=...]``) opens the file or
folder on click in terminals that support it (iTerm2, VS Code, WezTerm,
Ghostty, ...); elsewhere the text still reads as a plain path.
"""
from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

__all__ = ['print_output_files']


def _size(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f'{n:.0f} {unit}' if unit == 'B' else f'{n:.1f} {unit}'
        n /= 1024
    return f'{n} B'


def print_output_files(folder: Path, since: float, console=None) -> list[Path]:
    """Print the files in ``folder`` written at or after ``since`` (epoch s).

    Products that were left untouched because their content had not changed
    (``output_split``) are not listed — only what this run wrote. The reader's
    intermediate files (``_read_*``) go on one line after the products.
    """
    from rich.console import Console
    from rich.markup import escape

    folder = Path(folder)
    if not folder.is_dir():
        return []
    written = sorted((p for p in folder.iterdir()
                      if p.is_file() and not p.name.startswith('.')
                      and p.stat().st_mtime >= since - 1),
                     key=lambda p: p.name.lower())
    products = [p for p in written if not p.name.startswith('_read_')]
    intermediate = [p for p in written if p.name.startswith('_read_')]

    console = console or Console(highlight=False)
    # macOS Terminal.app renders neither OSC 8 links nor a bare file:// URI as
    # clickable, so it gets a command to paste instead of a click hint.
    apple_terminal = os.environ.get('TERM_PROGRAM') == 'Apple_Terminal'
    # Underlined and coloured so a link looks like one; the hint says how to
    # open it (⌘ on macOS, Ctrl elsewhere).
    key = '⌘' if sys.platform == 'darwin' else 'Ctrl'
    console.print()
    hint = '' if apple_terminal else f'[dim]{key}+click to open[/dim]'
    console.print(f'[bold cyan]{"Output":<12}[/bold cyan]{hint}')
    console.print(f'  {_link(folder, str(folder))}', soft_wrap=True)
    if not written:
        console.print('  [dim](nothing written this run)[/dim]')
    for p in products:
        console.print(f'  {_link(p, p.name)}  [dim]{_size(p.stat().st_size)}[/dim]', soft_wrap=True)
    if intermediate:
        console.print('  [dim]intermediate:[/dim] '
                      + '  '.join(_link(p, p.name) for p in intermediate), soft_wrap=True)
    if apple_terminal:
        console.print(f'  [dim]open the folder:[/dim] open {escape(shlex.quote(str(folder)))}',
                      soft_wrap=True)
    console.print()
    return written


def _link(path: Path, text: str) -> str:
    from rich.markup import escape
    return f'[link={path.resolve().as_uri()}][underline cyan]{escape(text)}[/underline cyan][/link]'
