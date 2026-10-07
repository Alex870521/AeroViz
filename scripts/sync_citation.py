"""Sync CITATION.cff's version and date-released with the release being cut.

Runs as a commitizen pre_bump_hook (see [tool.commitizen] in pyproject.toml):
`cz bump` sets CZ_PRE_NEW_VERSION, and the bump commit is made with `git commit -a`,
so the edited CITATION.cff lands in the same commit as the new version and tag.
Without the env var it falls back to pyproject's version, so it can also be run by
hand. tests/test_citation.py fails CI if the two ever disagree.
"""
import datetime
import os
import pathlib
import re
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFF = ROOT / 'CITATION.cff'


def main() -> None:
    version = os.environ.get('CZ_PRE_NEW_VERSION') or tomllib.loads(
        (ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()

    text = CFF.read_text(encoding='utf-8')
    for key, value in (('version', version), ('date-released', today)):
        text, n = re.subn(rf'^{key}:.*$', f'{key}: {value}', text, flags=re.M)
        if n != 1:
            raise SystemExit(f'CITATION.cff: expected one top-level "{key}:" line, found {n}')
    CFF.write_text(text, encoding='utf-8')
    print(f'CITATION.cff -> version {version}, date-released {today}')


if __name__ == '__main__':
    main()
