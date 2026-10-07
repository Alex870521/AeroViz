"""CITATION.cff must describe the version pyproject.toml is about to publish.

scripts/sync_citation.py keeps them in step on `cz bump`; this catches a version
changed some other way (hand edit, a bump without the hook).
"""
import pathlib
import re
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_citation_version_matches_pyproject():
    pyproject = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    cff = (ROOT / 'CITATION.cff').read_text(encoding='utf-8')
    match = re.search(r'^version:\s*(\S+)\s*$', cff, flags=re.M)
    assert match, 'CITATION.cff has no top-level version'
    assert match.group(1) == pyproject['project']['version'], (
        'CITATION.cff version is stale — run `python scripts/sync_citation.py`')
