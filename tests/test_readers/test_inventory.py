"""`inventory()` — describe a folder without parsing it."""
import shutil

import pytest

from AeroViz import inventory

SMPS_TRANSPOSED = (
    "Sample File\tC:\\\\x\\\\07092024.15.S80\n"
    "Classifier Model\t3080\n"
    "DMA Model\t3085\n"
    "Detector Model\t3787\n"
    "Sample #\t1\t2\t3\n"
    "Date\t07/09/24\t07/09/24\t07/09/24\n"
    "Start Time\t18:47:32\t18:53:05\t18:58:35\n"
    "2.02\t10\t11\t12\n"
    "2.09\t13\t14\t15\n"
    "63.8\t1\t2\t3\n"
)


def test_smps_fixtures_are_described(raw_data_path, tmp_path):
    data = tmp_path / 'smps'
    data.mkdir()
    for scenario in ('normal', 'csv_format'):
        src = raw_data_path / 'SMPS' / scenario
        if not src.is_dir():
            pytest.skip('SMPS fixtures not available')
        for f in src.iterdir():
            if f.is_file() and not f.name.startswith('.'):
                shutil.copy2(f, data / f.name)
    (data / '20240709 (1).txt').write_text(SMPS_TRANSPOSED)
    (data / 'notes.md').write_text('not data')

    inv = inventory('SMPS', data)
    s = inv.attrs['summary']
    assert s['n_files'] == 4 and s['n_matched'] == 3 and s['n_unmatched'] == 1
    by = inv.set_index('file')
    assert by.loc['notes.md', 'matched'] is False or by.loc['notes.md', 'matched'] == False  # noqa: E712
    assert by.loc['20240709 (1).txt', 'layout'] == 'columns'
    assert by.loc['20240709 (1).txt', 'bins'] == 3 and by.loc['20240709 (1).txt', 'grid'] == '2.02-63.8'
    assert by.loc['20240709 (1).txt', 'detector'] == '3787'
    rows = by[(by['matched']) & (by['layout'] == 'rows')]
    assert set(rows['format']) == {'AIM 10.x TXT', 'AIM 11.x CSV'}
    assert (rows['bins'] > 50).all()
    assert s['variants']['layout'] == {'rows': 2, 'columns': 1}
    assert str(by.loc['20240709 (1).txt', 'date_in_name']) == '2024-07-09'


def test_ae33_backfill_and_ocec_header_only(tmp_path):
    ae = tmp_path / 'ae33'; ae.mkdir()
    (ae / 'AE33_AE33-S05-00503_20250305.dat').write_text('AETHALOMETER\nSerial number = x\n')
    (ae / 'AE33_AE33-S05-00503_backfill_1_20261002_212940.dat').write_text('# AE33 backfill (raw FETCH pipe-delimited)\n')
    inv = inventory('AE33', ae).set_index('file')
    assert inv.loc['AE33_AE33-S05-00503_20250305.dat', 'kind'] == 'daily log'
    assert inv.loc['AE33_AE33-S05-00503_backfill_1_20261002_212940.dat', 'kind'] == 'backfill dump'
    assert str(inv.loc['AE33_AE33-S05-00503_20250305.dat', 'date_in_name']) == '2025-03-05'

    oc = tmp_path / 'ocec'; oc.mkdir()
    (oc / 'SLI_OCEC_20260119_161952_LCRes.csv').write_text('h1\nh2\nh3\nSample ID,OC\n')
    (oc / 'SLI_OCEC_20260402_005250_LCRes.csv').write_text('h1\nh2\nh3\nSample ID,OC\nSC00028-4,9.07\nSC00028-4,8.1\n')
    inv = inventory('OCEC', oc).set_index('file')
    assert inv['samples'].to_dict() == {'SLI_OCEC_20260119_161952_LCRes.csv': 0, 'SLI_OCEC_20260402_005250_LCRes.csv': 2}
    assert inv.attrs['summary']['variants']['kind'] == {'results': 1, 'header only': 1}


def test_empty_folder_and_bad_instrument(tmp_path):
    inv = inventory('TEOM', tmp_path)
    assert inv.empty and inv.attrs['summary']['n_files'] == 0
    with pytest.raises(KeyError):
        inventory('NotAnInstrument', tmp_path)
    with pytest.raises(FileNotFoundError):
        inventory('TEOM', tmp_path / 'missing')
