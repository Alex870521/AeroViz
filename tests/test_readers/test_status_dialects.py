"""Status columns differ by host-software version — check every dialect.

`filter_error_status` returns all-False for a column it cannot find, so a renamed
status column degrades to "this instrument never reported an error", which looks
exactly like a healthy instrument. Two real cases were silently inert:

* **Aurora** — the production Ecotech export has no `Status`/`Error`/`Flag`
  column at all; the status is in `S1`.
* **SMPS** — AIM 11.x splits the same information across four differently-named
  columns, none of which is an AIM 10.3 name.
"""
import shutil
import tempfile

import pandas as pd
import pytest

from AeroViz.rawDataReader.core import QCFlagBuilder

FLAG = QCFlagBuilder.FLAG_COLUMN
INVALID = QCFlagBuilder.INVALID_COLUMN


# =============================================================================
# The generic guard: a missing status column must be announced
# =============================================================================

def test_missing_status_column_warns(caplog):
    """Silence was the bug: a renamed column has to surface in the log."""
    from AeroViz.rawDataReader.script.TEOM import Reader

    reader = Reader(path=tempfile.mkdtemp(), qc=True, quiet=True)
    frame = pd.DataFrame(
        {'PM_NV': [1.0, 2.0], 'PM_Total': [2.0, 3.0]},
        index=pd.date_range('2024-01-01', periods=2, freq='6min'),
    )

    with caplog.at_level('WARNING'):
        reader.check_status_columns(frame, ['status'])

    assert 'No status column found' in caplog.text
    assert 'cannot fire' in caplog.text


def test_present_status_column_does_not_warn(caplog):
    from AeroViz.rawDataReader.script.TEOM import Reader

    reader = Reader(path=tempfile.mkdtemp(), qc=True, quiet=True)
    frame = pd.DataFrame(
        {'status': [0, 0]}, index=pd.date_range('2024-01-01', periods=2, freq='6min'))

    with caplog.at_level('WARNING'):
        present = reader.check_status_columns(frame, ['status'])

    assert present == ['status']
    assert 'No status column found' not in caplog.text


# =============================================================================
# Aurora: status lives in S1
# =============================================================================

@pytest.mark.aurora
class TestAuroraS1:
    """`S1 == 4` marks the zero/span check — the instrument is sampling filtered
    air, so those rows are not ambient data. In the fixture they are 17 contiguous
    minutes whose scattering decays 185 -> 0.78 Mm⁻¹, all of which passed the
    0-2000 range check and were averaged into the ambient mean."""

    @pytest.fixture
    def aurora_dir(self, raw_data_path, tmp_path):
        src = raw_data_path / 'Aurora' / 'normal'
        if not src.exists():
            pytest.skip('Aurora fixture not available')
        dst = tmp_path / 'Aurora'
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns('aurora_outputs'))
        return dst

    def test_s1_is_recognised_as_the_status_column(self, aurora_dir):
        from AeroViz.rawDataReader.script.Aurora import Reader

        reader = Reader(path=aurora_dir, qc=True, quiet=True)
        raw = reader._raw_reader(next(aurora_dir.glob('*.csv')))

        assert 'Status' in raw.columns, 'S1 should be normalised to Status'
        assert 'S1' not in raw.columns

    def test_zero_check_rows_are_flagged(self, aurora_dir):
        from AeroViz.rawDataReader.script.Aurora import Reader

        reader = Reader(path=aurora_dir, qc=True, quiet=True)
        raw = reader._raw_reader(next(aurora_dir.glob('*.csv')))
        out = reader._QC(raw)

        zero_check = raw['Status'] != 0
        assert zero_check.sum() == 17, 'fixture should contain the 17-row zero check'
        assert out.loc[zero_check, FLAG].str.contains('Status Error').all()
        assert out.loc[zero_check, INVALID].all()

    def test_ambient_rows_are_unaffected(self, aurora_dir):
        from AeroViz.rawDataReader.script.Aurora import Reader

        reader = Reader(path=aurora_dir, qc=True, quiet=True)
        raw = reader._raw_reader(next(aurora_dir.glob('*.csv')))
        out = reader._QC(raw)

        ambient = raw['Status'] == 0
        assert not out.loc[ambient, FLAG].str.contains('Status Error').any()

    def test_filtered_air_no_longer_biases_the_mean(self, aurora_dir):
        """The point of the fix: the zero-check minutes must not drag the average
        down once QC is applied."""
        from AeroViz import RawDataReader

        df = RawDataReader('Aurora', aurora_dir, reset=True, quiet=True,
                           fill_missing=False)
        raw = pd.read_pickle(aurora_dir / 'aurora_outputs' / '_read_aurora_raw.pkl')

        unfiltered = raw['G'].mean()
        after_qc = df['G'].mean()
        assert after_qc > unfiltered, (
            'dropping filtered-air rows should raise the ambient mean '
            f'(raw {unfiltered:.1f} -> QC {after_qc:.1f})')


# =============================================================================
# SMPS: AIM 10.3 vs AIM 11.x
# =============================================================================

@pytest.mark.smps
class TestSMPSDialects:
    @staticmethod
    def _reader(tmp_path, **kw):
        from AeroViz.rawDataReader.script.SMPS import Reader

        return Reader(path=tmp_path, qc=True, quiet=True, **kw)

    @staticmethod
    def _frame(**status_columns):
        """A two-row frame with a few size bins plus whichever status columns.

        Three bins, not two: the reader derives dlogDp from ``columns[:-1]``, so
        two bins leave a single diameter, ``np.diff`` returns an empty array and
        the mean of it is NaN — harmless for these assertions but it fills the
        log with `Mean of empty slice`.
        """
        idx = pd.date_range('2024-01-01', periods=2, freq='6min')
        data = {11.8: [3000.0, 3100.0], 15.0: [3500.0, 3600.0], 20.0: [4000.0, 4100.0]}
        data.update(status_columns)
        return pd.DataFrame(data, index=idx)

    def test_aim_103_error_token_column(self, tmp_path):
        out = self._reader(tmp_path)._QC(
            self._frame(**{'Instrument Errors': ['', 'Low aerosol flow']}))

        assert 'Status Error' not in out[FLAG].iloc[0]
        assert 'Status Error' in out[FLAG].iloc[1]

    def test_aim_11x_detector_status_is_the_status_flag_equivalent(self, tmp_path):
        """AIM 11.x renames the positive-sentinel column to `Detector Status`."""
        out = self._reader(tmp_path)._QC(
            self._frame(**{'Detector Status': ['Normal Scan', 'Conditioner Temperature Error']}))

        assert 'Status Error' not in out[FLAG].iloc[0]
        assert 'Status Error' in out[FLAG].iloc[1]

    def test_aim_11x_classifier_errors_is_the_instrument_errors_equivalent(self, tmp_path):
        out = self._reader(tmp_path)._QC(
            self._frame(**{'Classifier Errors': ['', 'Low aerosol flow']}))

        assert 'Status Error' not in out[FLAG].iloc[0]
        assert 'Status Error' in out[FLAG].iloc[1]

    def test_aim_11x_extra_columns(self, tmp_path):
        """`Communication Status` (OK '0') and `Neutralizer Status` (OK 'ON') have
        no AIM 10.3 equivalent and are checked on their own terms."""
        reader = self._reader(tmp_path)

        comms = reader._QC(self._frame(**{'Communication Status': ['0', '3']}))
        assert 'Status Error' not in comms[FLAG].iloc[0]
        assert 'Status Error' in comms[FLAG].iloc[1]

        neutralizer = reader._QC(self._frame(**{'Neutralizer Status': ['ON', 'OFF']}))
        assert 'Status Error' not in neutralizer[FLAG].iloc[0]
        assert 'Status Error' in neutralizer[FLAG].iloc[1]

    def test_normal_scan_sentinel_never_counts_as_an_error(self, tmp_path):
        """Some sites write the positive sentinel into the error-token column."""
        out = self._reader(tmp_path)._QC(
            self._frame(**{'Classifier Errors': ['Normal Scan', 'Normal Scan']}))

        assert not out[FLAG].str.contains('Status Error').any()

    def test_masks_are_ord_across_dialects(self, tmp_path):
        """A mixed folder may carry both dialects; either one firing is enough."""
        out = self._reader(tmp_path)._QC(self._frame(**{
            'Detector Status': ['Normal Scan', 'Normal Scan'],
            'Classifier Errors': ['', 'Low aerosol flow'],
        }))

        assert 'Status Error' not in out[FLAG].iloc[0]
        assert 'Status Error' in out[FLAG].iloc[1]

    def test_whitelist_still_applies(self, tmp_path):
        reader = self._reader(tmp_path, ignored_status_errors=['Low aerosol flow'])
        out = reader._QC(self._frame(**{'Classifier Errors': ['', 'Low aerosol flow']}))

        assert not out[FLAG].str.contains('Status Error').any()

    def test_real_aim_11x_export_is_no_longer_inert(self, raw_data_path, tmp_path):
        """End-to-end: the CSV fixture's `Classifier Errors` = 'Low aerosol flow'
        on every scan. Before the dialect was known, `Status Error` never fired."""
        src = raw_data_path / 'SMPS' / 'csv_format'
        if not src.exists():
            pytest.skip('SMPS csv_format fixture not available')
        dst = tmp_path / 'SMPS'
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns('smps_outputs'))

        from AeroViz import RawDataReader
        RawDataReader('SMPS', dst, reset=True, quiet=True, fill_missing=False)
        qc = pd.read_pickle(dst / 'smps_outputs' / '_read_smps_qc.pkl')

        assert qc[FLAG].str.contains('Status Error').any()

    def test_whitelist_recovers_the_aim_11x_export(self, raw_data_path, tmp_path):
        """...and the operator escape hatch works on the new columns too."""
        src = raw_data_path / 'SMPS' / 'csv_format'
        if not src.exists():
            pytest.skip('SMPS csv_format fixture not available')
        dst = tmp_path / 'SMPS'
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns('smps_outputs'))

        from AeroViz import RawDataReader
        RawDataReader('SMPS', dst, reset=True, quiet=True, fill_missing=False,
                      ignored_status_errors=['Low aerosol flow'])
        qc = pd.read_pickle(dst / 'smps_outputs' / '_read_smps_qc.pkl')

        assert not qc[FLAG].str.contains('Status Error').any()


# =============================================================================
# P1-c: completeness against the detected frequency
# =============================================================================

def test_completeness_uses_the_detected_frequency(tmp_path):
    """The config frequency is a fallback, not the truth. The APS fixture samples
    every 115 s while its config says 6 min — a 3x understatement that made the
    hourly-completeness threshold far too lenient."""
    from AeroViz.rawDataReader.script.APS import Reader

    reader = Reader(path=tmp_path, qc=True, quiet=True)
    # 10 rows spread across a whole hour, so the coverage-scaled expectation is a
    # full hour either way: complete on a 6-min grid (10 of 10), a third full on
    # a 2-min one (10 of 30).
    idx = pd.date_range('2024-01-01 00:00', periods=10, freq='6min')
    frame = pd.DataFrame({0.542: [50.0] * 10, 1.0: [40.0] * 10}, index=idx)

    reader._resolved_freq = None                      # fall back to config: 6min
    assert not reader._QC(frame)[FLAG].str.contains('Insufficient').any()

    reader._resolved_freq = '2min'                    # the real sampling rate
    assert reader._QC(frame)[FLAG].str.contains('Insufficient').all()


# =============================================================================
# P1-d: mean_freq on the qc=False branch
# =============================================================================

@pytest.mark.ocec
def test_mean_freq_applies_without_qc(raw_data_path, tmp_path):
    """`qc=False, mean_freq='1D'` used to return native-resolution data that
    looked daily-averaged."""
    from AeroViz import RawDataReader

    src = raw_data_path / 'OCEC' / 'normal'
    if not src.exists():
        pytest.skip('OCEC fixture not available')
    dst = tmp_path / 'OCEC'
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('ocec_outputs'))

    native = RawDataReader('OCEC', dst, reset=True, quiet=True, qc=False,
                           fill_missing=False)
    daily = RawDataReader('OCEC', dst, reset=True, quiet=True, qc=False,
                          mean_freq='1D', fill_missing=False)

    assert len(daily) < len(native)
    assert daily.attrs['mean_freq'] == '1D'
    assert native.attrs.get('mean_freq') is None


# =============================================================================
# P1-f: AE33 and AE43 agree on the shared status register
# =============================================================================

def test_ae33_and_ae43_error_states_match():
    """Same instrument family, same register, same manual — 384 was on one list
    only. 128/256 are tape-LOW warnings and their sum must not be an error."""
    from AeroViz.rawDataReader.script.AE33 import Reader as AE33
    from AeroViz.rawDataReader.script.AE43 import Reader as AE43

    assert AE33.ERROR_STATES == AE43.ERROR_STATES
    for code in (128, 256, 384):
        assert code not in AE43.ERROR_STATES
