"""SMPS/APS exports in a unit other than dN/dlogDp must be skipped, not misread.

Every step after parsing treats the size bins as dN/dlogDp. AIM can also export
Raw Counts, dN ("Concentration (dW)"), % concentration, or surface/volume
weighting; the TCLab Raw Data Repository holds a few dozen of each, and they
used to be read as dN/dlogDp — off by the channel width or a different moment.
"""
import shutil

import pytest

from AeroViz.rawDataReader.script import APS, SMPS


def _copy(src, tmp_path, old, new, count=-1):
    if not src.exists():
        pytest.skip(f'fixture {src.name} not available')
    text = src.read_text(encoding='utf-8', errors='ignore')
    assert old in text, f'fixture {src.name} no longer contains {old!r}'
    dst = tmp_path / src.name
    dst.write_text(text.replace(old, new, count), encoding='utf-8')
    return dst


@pytest.mark.parametrize('unit', ['Raw Counts', 'dN', '%dN'])
def test_aps_non_dndlogdp_export_is_skipped(raw_data_path, tmp_path, unit):
    src = raw_data_path / 'APS' / 'normal' / '20251117.TXT'
    f = _copy(src, tmp_path, '\tdN/dlogDp\t', f'\t{unit}\t')
    assert APS.Reader(tmp_path, quiet=True)._raw_reader(f) is None


def test_aps_dndlogdp_export_still_reads(raw_data_path, tmp_path):
    src = raw_data_path / 'APS' / 'normal' / '20251117.TXT'
    if not src.exists():
        pytest.skip('APS fixture not available')
    f = tmp_path / src.name
    shutil.copy(src, f)
    df = APS.Reader(tmp_path, quiet=True)._raw_reader(f)
    assert df is not None and not df.empty


def test_aps_drops_only_the_rows_in_a_foreign_unit(raw_data_path, tmp_path):
    """One corrupted unit cell (seen in the field as `dN/dlggDp`) costs that row,
    not the whole day."""
    src = raw_data_path / 'APS' / 'normal' / '20251117.TXT'
    if not src.exists():
        pytest.skip('APS fixture not available')
    clean = tmp_path / 'clean'
    clean.mkdir()
    shutil.copy(src, clean / src.name)
    full = APS.Reader(clean, quiet=True)._raw_reader(clean / src.name)

    f = _copy(src, tmp_path, '\tdN/dlogDp\t', '\tdN/dlggDp\t', count=1)   # first row only
    df = APS.Reader(tmp_path, quiet=True)._raw_reader(f)

    assert df is not None
    assert len(df) == len(full) - 1
    assert df.index[0] == full.index[1]


def test_aps_merged_export_with_repeated_header_still_reads(raw_data_path, tmp_path):
    """A merged export repeats its `Sample #` header mid-file; that row's unit
    cell reads `Aerodynamic Diameter`, which must not count as a foreign unit."""
    src = raw_data_path / 'APS' / 'normal' / '20251117.TXT'
    if not src.exists():
        pytest.skip('APS fixture not available')
    lines = src.read_text(encoding='utf-8', errors='ignore').splitlines(keepends=True)
    header = next(i for i, l in enumerate(lines) if l.startswith('Sample #'))
    mid = header + 1 + (len(lines) - header - 1) // 2
    f = tmp_path / src.name
    f.write_text(''.join(lines[:mid] + [lines[header]] + lines[mid:]), encoding='utf-8')
    df = APS.Reader(tmp_path, quiet=True)._raw_reader(f)
    assert df is not None and not df.empty


@pytest.mark.parametrize('old, new', [
    ('Units\tdw/dlogDp', 'Units\tConcentration (dW)'),   # dN
    ('Units\tdw/dlogDp', 'Units\t% Concentration'),
    ('Weight\tNumber', 'Weight\tSurface'),
    ('Weight\tNumber', 'Weight\tVolume'),
])
def test_smps_txt_non_number_dndlogdp_export_is_skipped(raw_data_path, tmp_path, old, new):
    src = raw_data_path / 'SMPS' / 'status_errors' / '250107-2.txt'
    f = _copy(src, tmp_path, old, new)
    assert SMPS.Reader(tmp_path, quiet=True)._raw_reader(f) is None


def test_smps_csv_dn_export_is_skipped(raw_data_path, tmp_path):
    src = raw_data_path / 'SMPS' / 'csv_format' / 'SMPS_3082001426002_20260205_174800.csv'
    f = _copy(src, tmp_path, 'Units,dW/dlogDp', 'Units,Concentration (dW)')
    assert SMPS.Reader(tmp_path, quiet=True)._raw_reader(f) is None


@pytest.mark.parametrize('rel', [
    'status_errors/250107-2.txt',                         # Units dw/dlogDp (lower-case w)
    'csv_format/SMPS_3082001426002_20260205_174800.csv',  # Units dW/dlogDp
])
def test_smps_dndlogdp_exports_still_read(raw_data_path, tmp_path, rel):
    src = raw_data_path / 'SMPS' / rel
    if not src.exists():
        pytest.skip(f'fixture {rel} not available')
    f = tmp_path / src.name
    shutil.copy(src, f)
    df = SMPS.Reader(tmp_path, quiet=True)._raw_reader(f)
    assert df is not None and not df.empty
