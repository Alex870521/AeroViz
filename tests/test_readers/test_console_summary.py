"""The terminal view of a read: per-file messages are held back during the read
and shown afterwards as one grouped summary (log file unchanged)."""
import re
from datetime import datetime

import pytest

from AeroViz import RawDataReader

ANSI = re.compile(r'\x1b\]8;[^\x1b]*\x1b\\|\x1b\[[0-9;?]*[a-zA-Z]')


def _plain(text):
    return ANSI.sub('', text)


@pytest.fixture
def smps_folder(raw_data_path, tmp_path):
    src = raw_data_path / 'SMPS' / 'normal' / '20250219.TXT'
    if not src.exists():
        pytest.skip('SMPS fixture not available')
    folder = tmp_path / 'NZ_SMPS'
    folder.mkdir()
    text = src.read_text(encoding='utf-8', errors='ignore')
    (folder / src.name).write_text(text, encoding='utf-8')
    (folder / '20250219_dN.TXT').write_text(
        text.replace('Units\tdw/dlogDp', 'Units\tConcentration (dW)'), encoding='utf-8')
    for i in range(2):
        (folder / f'20250219_pct{i}.TXT').write_text(
            text.replace('Units\tdw/dlogDp', 'Units\t% Concentration'), encoding='utf-8')
    return folder


def _read(folder, **kw):
    return RawDataReader('SMPS', folder, start=datetime(2025, 2, 19), end=datetime(2025, 2, 20),
                         mean_freq='1h', output_dir=folder.parent / 'out', log_level='INFO', **kw)


def test_summary_groups_per_file_messages(smps_folder, capsys):
    _read(smps_folder)
    out = _plain(capsys.readouterr().out)

    assert 'Files' in out and '4 files · 2 used' in out and '2 skipped' in out and '1 converted' in out
    # one line per kind, not one per file
    assert out.count('cannot be converted') == 1
    assert 'skipped 2 files whose unit cannot be converted' in out
    assert 'converted 1 file to dN/dlogDp' in out
    # the old per-file console lines are gone from the terminal ...
    assert 'Saved:' not in out and 'QC Summary' not in out
    # ... but every one of them is still in the log
    log = (smps_folder.parent / 'out' / 'SMPS.log').read_text()
    assert log.count('cannot be converted to dN/dlogDp') == 2
    assert 'converted dN to dN/dlogDp' in log


def test_qc_section_lists_only_rules_that_hit(smps_folder, capsys):
    _read(smps_folder)
    out = _plain(capsys.readouterr().out)
    qc = out[out.index('\nQC'):out.index('\nCoverage')]
    assert 'Valid' in qc and 'Status Error' in qc
    assert 'Insufficient' not in qc                      # 0 hits in this fixture
    assert re.search(r'\d+ rules? with no hits not shown', qc)
    for section in ('Coverage', 'Output'):
        assert f'\n{section}' in out


def test_quiet_prints_nothing(smps_folder, capsys):
    _read(smps_folder, quiet=True)
    assert capsys.readouterr().out == ''


def test_messages_are_shown_when_the_read_fails(smps_folder, capsys):
    """Only unconvertible files left: the read raises, but the console still
    says why each file was skipped."""
    for f in smps_folder.iterdir():
        if 'pct' not in f.name:
            f.unlink()
    with pytest.raises(ValueError):
        _read(smps_folder)
    out = _plain(capsys.readouterr().out)
    assert 'skipped 2 files whose unit cannot be converted' in out
