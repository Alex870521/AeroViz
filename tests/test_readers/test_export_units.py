"""SMPS/APS exports in units other than dN/dlogDp: convert what converts exactly,
skip what does not, and say which was which in ``df.attrs``.

Every step after parsing treats the size bins as dN/dlogDp. AIM can also export
per channel (dN, "Concentration (dW)"), or weighted by surface, volume or mass;
those convert exactly. Raw Counts and % concentration cannot be undone and are
skipped. The TCLab Raw Data Repository holds a few dozen of each; they used to
be read as dN/dlogDp — off by the channel width or a different moment.
"""
import shutil
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from AeroViz import RawDataReader
from AeroViz.dataProcess.SizeDistr._size_dist import bin_widths
from AeroViz.dataProcess.SizeDistr.units import DN_DLOGDP, FILE_UNIT_ATTR, SOURCE_UNIT_ATTR, UNIT_ATTR
from AeroViz.rawDataReader.script import APS, SMPS

APS_FIXTURE = ('APS', 'normal', '20251117.TXT')
SMPS_TXT = ('SMPS', 'status_errors', '250107-2.txt')                       # Channels/Decade 64
SMPS_CSV = ('SMPS', 'csv_format', 'SMPS_3082001426002_20260205_174800.csv')


def _src(raw_data_path, parts):
    src = raw_data_path.joinpath(*parts)
    if not src.exists():
        pytest.skip(f'fixture {src.name} not available')
    return src


def _copy(src, folder, old=None, new=None, count=-1):
    folder.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding='utf-8', errors='ignore')
    if old is not None:
        assert old in text, f'fixture {src.name} no longer contains {old!r}'
        text = text.replace(old, new, count)
    dst = folder / src.name
    dst.write_text(text, encoding='utf-8')
    return dst


def _bins(df):
    return df[[c for c in df.columns if isinstance(c, float)]].apply(pd.to_numeric, errors='coerce')


def _native(reader_cls, src, tmp_path):
    f = _copy(src, tmp_path / 'native')
    return _bins(reader_cls.Reader(f.parent, quiet=True)._raw_reader(f))


# ---- APS ---------------------------------------------------------------------

@pytest.mark.parametrize('unit', ['Raw Counts', '%dN'])
def test_aps_unconvertible_export_is_skipped(raw_data_path, tmp_path, unit):
    f = _copy(_src(raw_data_path, APS_FIXTURE), tmp_path, '\tdN/dlogDp\t', f'\t{unit}\t')
    assert APS.Reader(tmp_path, quiet=True)._raw_reader(f) is None


@pytest.mark.parametrize('label, factor', [
    ('dN', lambda dp: 1 / bin_widths(dp)),
    ('dS/dlogDp', lambda dp: 1 / (np.pi * dp ** 2)),
    ('dV/dlogDp', lambda dp: 1 / (np.pi / 6 * dp ** 3)),
    ('dM/dlogDp', lambda dp: 1e3 / (1.0 * np.pi / 6 * dp ** 3)),   # fixture Density = 1
])
def test_aps_export_is_converted(raw_data_path, tmp_path, label, factor):
    """Relabelling the unit leaves the numbers as they are, so the converted
    frame must be the native one times the conversion factor."""
    src = _src(raw_data_path, APS_FIXTURE)
    native = _native(APS, src, tmp_path)
    f = _copy(src, tmp_path / 'relabelled', '\tdN/dlogDp\t', f'\t{label}\t')
    df = APS.Reader(f.parent, quiet=True)._raw_reader(f)

    dp = np.asarray(native.columns, float)
    pd.testing.assert_frame_equal(_bins(df), native * factor(dp), check_dtype=False)
    assert df.attrs[FILE_UNIT_ATTR] == label


def test_aps_mixed_units_convert_row_by_row(raw_data_path, tmp_path):
    src = _src(raw_data_path, APS_FIXTURE)
    native = _native(APS, src, tmp_path)
    f = _copy(src, tmp_path / 'mixed', '\tdN/dlogDp\t', '\tdN\t', count=1)   # first row only
    df = _bins(APS.Reader(f.parent, quiet=True)._raw_reader(f))

    dp = np.asarray(native.columns, float)
    np.testing.assert_allclose(df.iloc[0], native.iloc[0] / bin_widths(dp))
    pd.testing.assert_frame_equal(df.iloc[1:], native.iloc[1:], check_dtype=False)


def test_aps_drops_only_the_rows_in_a_foreign_unit(raw_data_path, tmp_path):
    """One corrupted unit cell (seen in the field as `dN/dlggDp`) costs that row,
    not the whole day."""
    src = _src(raw_data_path, APS_FIXTURE)
    native = _native(APS, src, tmp_path)
    f = _copy(src, tmp_path / 'corrupt', '\tdN/dlogDp\t', '\tdN/dlggDp\t', count=1)
    df = APS.Reader(f.parent, quiet=True)._raw_reader(f)

    assert len(df) == len(native) - 1
    assert df.index[0] == native.index[1]


def test_aps_merged_export_with_repeated_header_still_reads(raw_data_path, tmp_path):
    """A merged export repeats its `Sample #` header mid-file; that row's unit
    cell reads `Aerodynamic Diameter`, which must not count as a foreign unit."""
    src = _src(raw_data_path, APS_FIXTURE)
    lines = src.read_text(encoding='utf-8', errors='ignore').splitlines(keepends=True)
    header = next(i for i, l in enumerate(lines) if l.startswith('Sample #'))
    mid = header + 1 + (len(lines) - header - 1) // 2
    f = tmp_path / src.name
    f.write_text(''.join(lines[:mid] + [lines[header]] + lines[mid:]), encoding='utf-8')
    df = APS.Reader(tmp_path, quiet=True)._raw_reader(f)
    assert df is not None and not df.empty
    assert df.attrs[FILE_UNIT_ATTR] == DN_DLOGDP


# ---- SMPS --------------------------------------------------------------------

@pytest.mark.parametrize('old, new', [
    ('Units\tdw/dlogDp', 'Units\t% Concentration'),
    ('Weight\tNumber', 'Weight\tMass'),     # no SMPS mass export to verify the unit against
])
def test_smps_unconvertible_export_is_skipped(raw_data_path, tmp_path, old, new):
    f = _copy(_src(raw_data_path, SMPS_TXT), tmp_path, old, new)
    assert SMPS.Reader(tmp_path, quiet=True)._raw_reader(f) is None


@pytest.mark.parametrize('replacements, label, factor', [
    ([('Units\tdw/dlogDp', 'Units\tConcentration (dW)')], 'dN', lambda dp: 64.0),
    ([('Weight\tNumber', 'Weight\tSurface')], 'dS/dlogDp', lambda dp: 1 / (np.pi * dp ** 2)),
    ([('Weight\tNumber', 'Weight\tVolume')], 'dV/dlogDp', lambda dp: 1 / (np.pi / 6 * dp ** 3)),
    ([('Units\tdw/dlogDp', 'Units\tConcentration (DW)'), ('Weight\tNumber', 'Weight\tSurface')],
     'dS', lambda dp: 64.0 / (np.pi * dp ** 2)),
])
def test_smps_txt_export_is_converted(raw_data_path, tmp_path, replacements, label, factor):
    src = _src(raw_data_path, SMPS_TXT)
    native = _native(SMPS, src, tmp_path)
    f = _copy(src, tmp_path / 'relabelled')
    text = f.read_text(encoding='utf-8')
    for old, new in replacements:
        assert old in text
        text = text.replace(old, new)
    f.write_text(text, encoding='utf-8')
    df = SMPS.Reader(f.parent, quiet=True)._raw_reader(f)

    dp = np.asarray(native.columns, float)
    pd.testing.assert_frame_equal(_bins(df), native * factor(dp), check_dtype=False)
    assert df.attrs[FILE_UNIT_ATTR] == label


def test_smps_csv_dn_export_is_converted(raw_data_path, tmp_path):
    src = _src(raw_data_path, SMPS_CSV)
    native = _native(SMPS, src, tmp_path)
    f = _copy(src, tmp_path / 'dn', 'Units,dW/dlogDp', 'Units,Concentration (dW)')
    df = SMPS.Reader(f.parent, quiet=True)._raw_reader(f)
    channels = float(next(l.split(',')[1] for l in src.read_text(errors='ignore').splitlines()
                          if l.startswith('Channels/Decade')))
    pd.testing.assert_frame_equal(_bins(df), native * channels, check_dtype=False)
    assert df.attrs[FILE_UNIT_ATTR] == 'dN'


@pytest.mark.parametrize('parts', [SMPS_TXT, SMPS_CSV])
def test_smps_dndlogdp_exports_still_read(raw_data_path, tmp_path, parts):
    f = _copy(_src(raw_data_path, parts), tmp_path)
    df = SMPS.Reader(tmp_path, quiet=True)._raw_reader(f)
    assert df is not None and not df.empty
    assert df.attrs[FILE_UNIT_ATTR] == DN_DLOGDP


# ---- what the returned frame says ----------------------------------------------

def _read_aps(folder):
    return RawDataReader('APS', folder, start=datetime(2025, 11, 1),
                         end=datetime(2025, 11, 30, 23, 59, 59), reset=True, mean_freq='1h',
                         save_pkl=False, save_intermediate_csv=False, save_report=False,
                         quiet=True, log_level='ERROR')


def test_output_records_its_unit_and_what_was_converted(raw_data_path, tmp_path):
    src = _src(raw_data_path, APS_FIXTURE)
    f = _copy(src, tmp_path / 'APS_dn', '\tdN/dlogDp\t', '\tdN\t')
    df = _read_aps(f.parent)
    assert df.attrs[UNIT_ATTR] == DN_DLOGDP
    assert df.attrs[SOURCE_UNIT_ATTR] == {'dN': [src.name]}


def test_output_without_conversions_has_no_source_units(raw_data_path, tmp_path):
    f = _copy(_src(raw_data_path, APS_FIXTURE), tmp_path / 'APS_native')
    df = _read_aps(f.parent)
    assert df.attrs[UNIT_ATTR] == DN_DLOGDP
    assert SOURCE_UNIT_ATTR not in df.attrs
    assert FILE_UNIT_ATTR not in df.attrs
