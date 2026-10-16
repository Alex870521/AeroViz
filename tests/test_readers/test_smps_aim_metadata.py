"""SMPS metadata columns read the same across AIM generations.

AIM ≤ 10.2 (`Sheath Flow(lpm)`), AIM 10.3 (`Sheath Flow (L/min)`) and AIM 11.x
(CSV, no `Aerosol Flow` column at all) name the same quantities differently.
The CPC over-range rule looked the flows up under the oldest spelling only, so
it never ran on AIM 10.3 / 11.x exports — every 2024–2026 file in the TCLab
repository among them.
"""
import shutil

import pytest

from AeroViz.rawDataReader.script import SMPS

FIXTURES = {
    'AIM <= 10.2 txt': 'status_errors/250107-2.txt',
    'AIM 10.3 txt': 'normal/20250219.TXT',
    'AIM 11.x csv': 'csv_format/SMPS_3082001426002_20260205_174800.csv',
}


def _parse(raw_data_path, tmp_path, rel):
    src = raw_data_path / 'SMPS' / rel
    if not src.exists():
        pytest.skip(f'fixture {rel} not available')
    f = tmp_path / src.name
    shutil.copy(src, f)
    reader = SMPS.Reader(tmp_path, quiet=True)
    return reader, reader._raw_reader(f)


@pytest.mark.parametrize('rel', FIXTURES.values(), ids=FIXTURES.keys())
def test_flow_ratio_is_available_for_every_aim_generation(raw_data_path, tmp_path, rel):
    reader, df = _parse(raw_data_path, tmp_path, rel)
    beta = reader._flow_ratio(df)
    assert beta is not None, f'no aerosol/sheath flow found in {sorted(map(str, df.columns))[:20]}'
    assert len(beta) == len(df)
    assert ((beta > 0) & (beta < 1)).all()


@pytest.mark.parametrize('rel', FIXTURES.values(), ids=FIXTURES.keys())
def test_shared_quantities_use_the_aim_10_3_names(raw_data_path, tmp_path, rel):
    _, df = _parse(raw_data_path, tmp_path, rel)
    cols = {c for c in df.columns if isinstance(c, str)}
    for name in ('Sheath Flow (L/min)', 'Median (nm)', 'Geo. Mean (nm)', 'Mode (nm)',
                 'D50 (nm)', 'Total Conc. (#/cm)', 'Density (g/cm)'):
        assert name in cols, f'{name!r} missing'
    assert not [c for c in cols if '(lpm)' in c], 'old AIM flow names survived'


def test_old_aim_names_are_renamed(raw_data_path, tmp_path):
    _, df = _parse(raw_data_path, tmp_path, FIXTURES['AIM <= 10.2 txt'])
    cols = set(df.columns)
    for old, new in [('Aerosol Flow(lpm)', 'Aerosol Flow (L/min)'),
                     ('CPC Inlet Flow(lpm)', 'Detector Inlet Flow (L/min)'),
                     ('Density(g/cc)', 'Density (g/cm)'),
                     ('Lower Size(nm)', 'Lower Size (nm)')]:
        assert old not in cols and new in cols, (old, new)


@pytest.mark.parametrize('spelling', [
    'Total Conc.(#/cm)', 'Total Conc.(#/cm?)', 'Total Conc.(#/cm )',
    'Total Conc. (#/cm?', 'Total Concentration(#/cm)',
])
def test_mangled_total_conc_header_is_canonicalised(raw_data_path, tmp_path, spelling):
    src = raw_data_path / 'SMPS' / FIXTURES['AIM <= 10.2 txt']
    if not src.exists():
        pytest.skip('fixture not available')
    text = src.read_text(encoding='utf-8', errors='ignore')
    current = next(s for s in ('Total Conc.(#/cm)', 'Total Concentration(#/cm)') if s in text)
    f = tmp_path / src.name
    f.write_text(text.replace(current, spelling), encoding='utf-8')
    df = SMPS.Reader(tmp_path, quiet=True)._raw_reader(f)
    assert 'Total Conc. (#/cm)' in df.columns
    assert spelling == 'Total Conc. (#/cm)' or spelling not in df.columns
