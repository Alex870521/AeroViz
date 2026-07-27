#!/usr/bin/env python3
"""Emit a pip constraints file pinning every runtime dependency to the exact
lower bound pyproject declares for it.

A floor like ``pandas>=2.2.0`` is a *claim*, and pip only ever resolves the
newest version that satisfies it — so the floor is the one version that never
gets installed, let alone tested. Claims nobody exercises drift into being
false: ``pandas>=2.2.0`` was unsatisfiable next to ``numpy>=2.0.0``, because
pandas capped ``numpy<2`` until 2.2.2. It went unnoticed for as long as the
declaration existed, because every real install landed on 2.2.3.

Feeding this file to ``pip install -c`` turns the claims into an installable
set, so CI answers two questions at once: can the declared floors be resolved
together at all, and does the code still work down there.

Usage::

    python .github/scripts/floor_constraints.py > floors.txt
    pip install ".[test]" -c floors.txt

Deliberately stdlib-only and regex-based rather than ``tomllib``: this runs on
the floor job, whose interpreter may predate 3.11.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# `dependencies = [` appears once at the top level of [project]. The extras
# live under a [project.optional-dependencies] table whose keys are `test = [`
# / `dev = [` / `docs = [`, and the build backend's list is `requires = [`, so
# neither collides with this anchor.
DEPENDENCIES_BLOCK = re.compile(r'^dependencies = \[(.*?)^\]', re.MULTILINE | re.DOTALL)
QUOTED = re.compile(r'"([^"]+)"')

# name, optional [extras], then the specifier set.
REQUIREMENT = re.compile(r'^([A-Za-z0-9._-]+)\s*(?:\[[^\]]*\])?\s*(.*)$')
# `~=13.9.4` states a floor just as `>=` does (it only adds a ceiling on top),
# so both open a range downwards and both are honoured here.
LOWER_BOUND = re.compile(r'(?:>=|~=|==)\s*([0-9][0-9A-Za-z.*+!-]*)')


def main(argv: list[str]) -> int:
    # Defaults to the repo's own pyproject; the optional argument exists so the
    # guards below can be exercised against a fixture instead of only firing
    # for the first person to add an unbounded dependency.
    pyproject = Path(argv[0]) if argv else Path(__file__).resolve().parents[2] / 'pyproject.toml'
    text = pyproject.read_text(encoding='utf-8')

    block = DEPENDENCIES_BLOCK.search(text)
    if block is None:
        print(f'error: no top-level `dependencies = [...]` in {pyproject}', file=sys.stderr)
        return 1

    requirements = QUOTED.findall(block.group(1))
    if not requirements:
        print(f'error: `dependencies` in {pyproject} is empty', file=sys.stderr)
        return 1

    lines, unbounded = [], []
    for requirement in requirements:
        parsed = REQUIREMENT.match(requirement.strip())
        if parsed is None:
            print(f'error: cannot parse dependency {requirement!r}', file=sys.stderr)
            return 1

        name, specifiers = parsed.groups()
        bound = LOWER_BOUND.search(specifiers)
        if bound is None:
            unbounded.append(requirement)
            continue

        lines.append(f'{name}=={bound.group(1)}')

    # An unbounded dependency is not a gap this script can paper over: there is
    # no floor to pin, so the floor job would silently stop covering it. Say so
    # and fail, rather than quietly shrinking what CI checks.
    if unbounded:
        print('error: these dependencies declare no lower bound, so their floor '
              'cannot be tested:', file=sys.stderr)
        for requirement in unbounded:
            print(f'  {requirement}', file=sys.stderr)
        return 1

    print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
