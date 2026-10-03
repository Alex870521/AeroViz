"""`qc_config=` — thresholds, whitelists, severities and outlier windows from one
document, with precedence defaults < instrument < station < explicit kwargs,
and `write_qc_report` rendering what a run did from `df.attrs`."""
import shutil

import pandas as pd
import pytest

from AeroViz import RawDataReader, write_qc_report
from AeroViz.rawDataReader.core.qc_config import apply_qc_config, load_qc_config, resolve_qc_config
from AeroViz.rawDataReader.script import AE33, OCEC

CONFIG = {
    'defaults': {'flag_severity': {'Insufficient': 'warning'}},
    'AE33': {
        'thresholds': {'MAX_BC': 15000},
        'ignored_status_errors': [16],
        'flag_severity': {'Invalid BC': 'warning'},
        'outliers': [['2025-03-05 00:00', '2025-03-05 23:59']],
        'stations': {
            'NZ': {'thresholds': {'MAX_BC': 9000}, 'ignored_status_errors': [32]},
        },
    },
}


# --------------------------------------------------------------------------- #
# resolve: precedence and validation
# --------------------------------------------------------------------------- #
def test_station_overrides_instrument_overrides_defaults():
    r = resolve_qc_config(CONFIG, 'AE33', 'NZ')
    assert r['thresholds'] == {'MAX_BC': 9000}
    assert r['ignored_status_errors'] == [16, 32]            # whitelists accumulate
    assert r['flag_severity'] == {'Insufficient': 'warning', 'Invalid BC': 'warning'}
    assert r['outliers'] == [['2025-03-05 00:00', '2025-03-05 23:59']]


def test_other_station_gets_only_the_instrument_section():
    assert resolve_qc_config(CONFIG, 'AE33', 'FS')['thresholds'] == {'MAX_BC': 15000}


def test_other_instrument_gets_only_defaults():
    assert resolve_qc_config(CONFIG, 'SMPS', 'NZ') == {'flag_severity': {'Insufficient': 'warning'}}


def test_unknown_section_key_is_rejected():
    with pytest.raises(ValueError, match='unknown keys'):
        resolve_qc_config({'AE33': {'threshold': {'MAX_BC': 1}}}, 'AE33', 'NZ')


def test_yaml_and_json_files_load(tmp_path):
    y = tmp_path / 'qc.yaml'
    y.write_text('AE33:\n  thresholds: {MAX_BC: 12345}\n', encoding='utf-8')
    j = tmp_path / 'qc.json'
    j.write_text('{"AE33": {"thresholds": {"MAX_BC": 12345}}}', encoding='utf-8')
    for src in (y, j, str(y)):
        assert load_qc_config(src)['AE33']['thresholds']['MAX_BC'] == 12345
    assert load_qc_config(None) == {}
    with pytest.raises(FileNotFoundError):
        load_qc_config(tmp_path / 'missing.yaml')


# --------------------------------------------------------------------------- #
# apply: thresholds shadow class constants on the instance only
# --------------------------------------------------------------------------- #
def test_thresholds_become_instance_attributes_without_touching_the_class(tmp_path):
    reader = AE33.Reader(path=tmp_path, reset=True, qc=True, quiet=True)
    before = AE33.Reader.MAX_BC
    applied = apply_qc_config(reader, {'thresholds': {'MAX_BC': 123}, 'outliers': [['2025-01-01', '2025-01-02']]})
    assert reader.MAX_BC == 123 and AE33.Reader.MAX_BC == before
    assert reader._config_outliers == [('2025-01-01', '2025-01-02')]
    assert applied['thresholds'] == {'MAX_BC': 123} and applied['source'] == 'dict'


def test_unknown_or_lowercase_threshold_is_an_error(tmp_path):
    reader = OCEC.Reader(path=tmp_path, reset=True, qc=True, quiet=True)
    with pytest.raises(ValueError, match="no constant 'MAX_BC'"):
        apply_qc_config(reader, {'thresholds': {'MAX_BC': 1}})
    with pytest.raises(ValueError, match='no constant'):
        apply_qc_config(reader, {'thresholds': {'nam': 'x'}})      # not a threshold


def test_malformed_outlier_window_is_an_error(tmp_path):
    reader = AE33.Reader(path=tmp_path, reset=True, qc=True, quiet=True)
    with pytest.raises(ValueError, match='outliers'):
        apply_qc_config(reader, {'outliers': ['2025-01-01']})


# --------------------------------------------------------------------------- #
# end to end on the AE33 fixture
# --------------------------------------------------------------------------- #
START, END = '2025-03-01', '2025-03-31'


@pytest.fixture
def ae33(raw_data_path, tmp_path):
    src = raw_data_path / 'AE33' / 'normal'
    if not src.exists() or not any(src.iterdir()):
        pytest.skip('AE33/normal fixture not available')
    dst = tmp_path / 'NZ_AE33'                      # station comes from the folder name
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('*_outputs'))
    return dst


def _read(path, **kw):
    return RawDataReader('AE33', path, start=START, end=END, reset=True, quiet=True, save_csv=False, **kw)


def test_config_tightens_the_threshold_and_is_recorded(ae33):
    base = _read(ae33)
    tight = _read(ae33, qc_config={'AE33': {'thresholds': {'MAX_BC': 1}}})   # everything is "too high"
    assert tight['BC6'].notna().sum() < base['BC6'].notna().sum()
    assert tight.attrs['qc_config']['thresholds'] == {'MAX_BC': 1}
    assert 'qc_config' not in base.attrs          # None values are not stamped


def test_station_section_applies_by_folder_prefix(ae33):
    df = _read(ae33, qc_config={'AE33': {'thresholds': {'MAX_BC': 20000},
                                         'stations': {'NZ': {'thresholds': {'MAX_BC': 1}}}}})
    assert df.attrs['qc_config']['thresholds'] == {'MAX_BC': 1}


def test_config_outlier_window_is_masked_on_top_of_outlier_json(ae33):
    base = _read(ae33)
    day = base['BC6'].dropna().index[0].normalize()
    window = [str(day), str(day + pd.Timedelta(hours=23, minutes=59))]
    df = _read(ae33, qc_config={'AE33': {'outliers': [window]}})
    assert df.loc[window[0]:window[1], 'BC6'].isna().all()
    assert df['BC6'].notna().sum() < base['BC6'].notna().sum()
    assert df.attrs['qc_config']['outliers'] == [window]


def test_explicit_kwargs_win_over_the_document(ae33):
    df = _read(ae33, qc_config={'AE33': {'flag_severity': {'Invalid BC': 'warning'}}},
               flag_severity={'Invalid BC': 'error'})
    rule = next(r for r in df.attrs['qc_rules'] if r['rule'] == 'Invalid BC')
    assert rule['severity'] == 'error'


def test_invalid_severity_from_the_document_is_still_validated(ae33):
    with pytest.raises(ValueError, match='flag_severity'):
        _read(ae33, qc_config={'defaults': {'flag_severity': {'Invalid BC': 'maybe'}}})


# --------------------------------------------------------------------------- #
# write_qc_report
# --------------------------------------------------------------------------- #
def test_qc_report_renders_from_attrs(ae33, tmp_path):
    df = _read(ae33, qc_config={'AE33': {'thresholds': {'MAX_BC': 15000}}})
    out = write_qc_report(df, tmp_path / 'reports' / 'ae33.md')
    text = out.read_text(encoding='utf-8')
    assert text.startswith('# NZ AE33 — QC report')
    for heading in ('## Rates', '## QC rules', '## Availability by month', '## QC configuration applied'):
        assert heading in text
    assert '| Invalid BC |' in text and '"MAX_BC": 15000' in text
    assert '| 2025-03 |' in text


def test_qc_report_on_a_plain_frame_has_no_qc_sections(tmp_path):
    df = pd.DataFrame({'x': [1.0, None]}, index=pd.date_range('2025-01-01', periods=2, freq='h'))
    text = write_qc_report(df, tmp_path / 'r.md', title='plain').read_text()
    assert text.startswith('# plain') and '## QC rules' not in text and '| 2025-01 |' in text
