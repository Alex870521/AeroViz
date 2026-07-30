"""QC flag severity: invalidating vs advisory.

Before severity existed, *any* non-``Valid`` flag NaN'd the whole row. That
deleted measurements for circumstances that were not failures — a value below a
detection limit, a vendor "warning"-class alarm — and took every other species
measured in the same row with it.

A rule now declares ``severity='error'`` (default) or ``severity='warning'``.
Both are recorded in ``QC_Flag``; only ``'error'`` sets ``QC_Invalid``, and only
``QC_Invalid`` drives masking.
"""
from datetime import datetime

import pandas as pd
import pytest

from AeroViz import RawDataReader
from AeroViz.rawDataReader.core import AbstractReader, QCFlagBuilder, QCRule

FLAG = QCFlagBuilder.FLAG_COLUMN
INVALID = QCFlagBuilder.INVALID_COLUMN


@pytest.fixture
def frame():
    return pd.DataFrame(
        {'value': [1.0, 2.0, 3.0, 4.0]},
        index=pd.date_range('2024-01-01', periods=4, freq='1h'),
    )


def _rule(name, rows, severity='error'):
    """A rule that fires on the given positional rows."""
    return QCRule(
        name=name,
        condition=lambda df, rows=rows: pd.Series(
            [i in rows for i in range(len(df))], index=df.index),
        description=f'test rule {name}',
        severity=severity,
    )


# =============================================================================
# QCRule / QCFlagBuilder
# =============================================================================

class TestSeverityDeclaration:
    def test_defaults_to_error(self):
        """A rule that does not say otherwise is invalidating — new rules are
        conservative until someone classifies them."""
        assert QCRule('x', lambda df: pd.Series(False, index=df.index)).severity == 'error'

    def test_rejects_unknown_severity(self):
        with pytest.raises(ValueError, match='severity'):
            QCRule('x', lambda df: None, severity='fatal')


class TestBuilderVerdict:
    def test_advisory_flag_is_recorded_but_not_invalidating(self, frame):
        qc = QCFlagBuilder().add_rule(_rule('Advisory', [1], severity='warning'))
        out = qc.apply(frame)

        assert out[FLAG].iloc[1] == 'Advisory'   # recorded
        assert not out[INVALID].iloc[1]          # but the row survives
        assert out[FLAG].iloc[0] == 'Valid'

    def test_error_flag_invalidates(self, frame):
        qc = QCFlagBuilder().add_rule(_rule('Broken', [2]))
        out = qc.apply(frame)

        assert out[FLAG].iloc[2] == 'Broken'
        assert out[INVALID].iloc[2]

    def test_both_flags_on_one_row(self, frame):
        """The record keeps both names; the verdict is driven by the error one."""
        qc = (QCFlagBuilder()
              .add_rule(_rule('Advisory', [0, 1], severity='warning'))
              .add_rule(_rule('Broken', [1])))
        out = qc.apply(frame)

        assert out[FLAG].iloc[0] == 'Advisory'
        assert not out[INVALID].iloc[0]
        assert out[FLAG].iloc[1] == 'Advisory, Broken'
        assert out[INVALID].iloc[1]

    def test_no_rules_still_produces_both_columns(self, frame):
        out = QCFlagBuilder().apply(frame)

        assert (out[FLAG] == 'Valid').all()
        assert not out[INVALID].any()


class TestSummary:
    def test_reports_severity_and_both_totals(self, frame):
        qc = (QCFlagBuilder()
              .add_rule(_rule('Advisory', [0, 1], severity='warning'))
              .add_rule(_rule('Broken', [3])))
        summary = qc.get_summary(frame).set_index('Rule')

        assert summary.loc['Advisory', 'Severity'] == 'warning'
        assert summary.loc['Broken', 'Severity'] == 'error'
        # Valid = passed everything (row 2 only). Usable = nothing invalidating
        # (rows 0, 1, 2). The gap is exactly the advisory-only rows.
        assert summary.loc['Valid', 'Count'] == 1
        assert summary.loc['Usable', 'Count'] == 3


class TestOverrides:
    def test_promote_advisory_to_error(self, frame):
        qc = QCFlagBuilder({'Advisory': 'error'}).add_rule(
            _rule('Advisory', [1], severity='warning'))
        out = qc.apply(frame)

        assert out[INVALID].iloc[1]

    def test_demote_error_to_advisory(self, frame):
        qc = QCFlagBuilder({'Broken': 'warning'}).add_rule(_rule('Broken', [1]))
        out = qc.apply(frame)

        assert out[FLAG].iloc[1] == 'Broken'
        assert not out[INVALID].iloc[1]

    def test_rejects_unknown_override(self, frame):
        qc = QCFlagBuilder({'Broken': 'nope'}).add_rule(_rule('Broken', [1]))
        with pytest.raises(ValueError, match='severity override'):
            qc.apply(frame)


class _StubReader(AbstractReader):
    """The bare bones of a reader, enough to exercise the late-flag path.

    Skips the base ``__init__`` (which wants a real data directory) and sets only
    what `update_qc_flag` reads.
    """

    nam = 'Stub'
    LATE_QC_FLAGS = ('Invalid AAE',)

    def __init__(self, overrides=None):
        self.qc_severity_overrides = dict(overrides or {})
        self.logger = None

    def _raw_reader(self, file):  # pragma: no cover - never called
        raise NotImplementedError

    def _QC(self, df):  # pragma: no cover - never called
        raise NotImplementedError


def _late_flagger(overrides=None):
    return _StubReader(overrides)


class TestUpdateQCFlag:
    """`_process` adds late rules (e.g. Invalid AAE) through this path."""

    def test_error_marks_invalid(self, frame):
        df = QCFlagBuilder().apply(frame)
        mask = pd.Series([False, True, False, False], index=df.index)
        out = _late_flagger().update_qc_flag(df, mask, 'Late Error')

        assert out[FLAG].iloc[1] == 'Late Error'
        assert out[INVALID].iloc[1]

    def test_warning_records_only(self, frame):
        df = QCFlagBuilder().apply(frame)
        mask = pd.Series([False, True, False, False], index=df.index)
        out = _late_flagger().update_qc_flag(df, mask, 'Late Note', severity='warning')

        assert out[FLAG].iloc[1] == 'Late Note'
        assert not out[INVALID].iloc[1]

    def test_appends_to_existing_flag(self, frame):
        df = QCFlagBuilder().add_rule(_rule('First', [1])).apply(frame)
        mask = pd.Series([False, True, False, False], index=df.index)
        out = _late_flagger().update_qc_flag(df, mask, 'Second')

        assert out[FLAG].iloc[1] == 'First, Second'

    def test_flag_severity_demotes_a_late_flag(self, frame):
        """The whole point: `Invalid AAE` used to be un-reclassifiable."""
        df = QCFlagBuilder().apply(frame)
        mask = pd.Series([False, True, False, False], index=df.index)
        stub = _late_flagger({'Invalid AAE': 'warning'})

        out = stub.update_qc_flag(df, mask, 'Invalid AAE')

        assert out[FLAG].iloc[1] == 'Invalid AAE'
        assert not out[INVALID].iloc[1], 'demoted flag must keep the measurement'

    def test_flag_severity_promotes_a_late_flag(self, frame):
        df = QCFlagBuilder().apply(frame)
        mask = pd.Series([False, True, False, False], index=df.index)
        stub = _late_flagger({'Late Note': 'error'})

        out = stub.update_qc_flag(df, mask, 'Late Note', severity='warning')

        assert out[INVALID].iloc[1]

    def test_rejects_a_bad_override_value(self, frame):
        df = QCFlagBuilder().apply(frame)
        mask = pd.Series([False, True, False, False], index=df.index)
        stub = _late_flagger({'Late Note': 'nope'})

        with pytest.raises(ValueError, match='severity override'):
            stub.update_qc_flag(df, mask, 'Late Note')


class TestOverrideNamesAreChecked:
    """An override naming no rule used to be silently ignored."""

    def test_unknown_name_raises(self, frame):
        qc = QCFlagBuilder({'Invald AAE': 'warning'}).add_rule(_rule('Spike', [1]))

        with pytest.raises(ValueError, match='names no QC rule'):
            qc.apply(frame)

    def test_message_lists_the_available_names(self, frame):
        qc = QCFlagBuilder({'Nope': 'warning'}).add_rule(_rule('Spike', [1]))

        with pytest.raises(ValueError, match='Spike'):
            qc.apply(frame)

    def test_known_rule_name_is_accepted(self, frame):
        qc = QCFlagBuilder({'Spike': 'warning'}).add_rule(_rule('Spike', [1]))

        assert not qc.apply(frame)[INVALID].any()

    def test_late_flag_name_is_accepted(self, frame):
        """`Invalid AAE` is not a rule here, but naming it is still legitimate."""
        qc = QCFlagBuilder({'Invalid AAE': 'warning'},
                           extra_flags=('Invalid AAE',)).add_rule(_rule('Spike', [1]))

        assert qc.apply(frame)[INVALID].iloc[1]

    def test_qc_builder_carries_the_readers_late_flags(self, frame):
        """`qc_builder()` must hand `LATE_QC_FLAGS` to the builder, or naming a
        late flag would be rejected as unknown before it is ever raised."""
        qc = _late_flagger({'Invalid AAE': 'warning'}).qc_builder()
        qc.add_rule(_rule('Spike', [1]))

        assert 'Invalid AAE' in qc.known_flags()
        qc.apply(frame)  # must not raise

    def test_aethalometers_declare_their_late_flag(self):
        from AeroViz.rawDataReader.script.AE33 import Reader as AE33
        from AeroViz.rawDataReader.script.AE43 import Reader as AE43
        from AeroViz.rawDataReader.script.BC1054 import Reader as BC1054
        from AeroViz.rawDataReader.script.MA350 import Reader as MA350

        for reader in (AE33, AE43, BC1054, MA350):
            assert 'Invalid AAE' in reader.LATE_QC_FLAGS


# =============================================================================
# Per-reader classification
# =============================================================================

@pytest.mark.ocec
class TestOCECBelowMDL:
    """OCEC's `Below MDL` was the headline case: `value <= MDL` over four carbon
    fractions wiped clean-air periods wholesale."""

    @staticmethod
    def _reader(tmp_path, **kw):
        from AeroViz.rawDataReader.script.OCEC import Reader

        return Reader(path=tmp_path, qc=True, quiet=True, **kw)

    @staticmethod
    def _frame():
        # Row 1 is clean air: every fraction under its MDL but perfectly valid.
        # Row 2 is genuinely broken: a carbon value past the range limit.
        idx = pd.date_range('2024-01-01', periods=3, freq='1h')
        return pd.DataFrame(
            {'Thermal_OC': [2.0, 0.1, 5.0],
             'Thermal_EC': [0.5, 0.001, 0.6],
             'Optical_OC': [2.1, 0.1, 200.0],
             'Optical_EC': [0.5, 0.001, 0.6],
             'TC': [2.6, 0.11, 5.6],
             'OC1': [0.5, 0.02, 1.0], 'OC2': [0.5, 0.02, 1.0],
             'OC3': [0.5, 0.02, 1.0], 'OC4': [0.5, 0.02, 1.0],
             'PC': [0.1, 0.01, 0.2]},
            index=idx,
        )

    def test_clean_air_row_is_flagged_but_kept(self, tmp_path):
        out = self._reader(tmp_path)._QC(self._frame())

        assert 'Below MDL' in out[FLAG].iloc[1]
        assert not out[INVALID].iloc[1], 'clean air must survive into the output'

    def test_genuinely_bad_row_still_invalidated(self, tmp_path):
        out = self._reader(tmp_path)._QC(self._frame())

        assert 'Invalid Carbon' in out[FLAG].iloc[2]
        assert out[INVALID].iloc[2]

    def test_override_restores_the_old_strictness(self, tmp_path):
        reader = self._reader(tmp_path, flag_severity={'Below MDL': 'error'})
        out = reader._QC(self._frame())

        assert out[INVALID].iloc[1]


@pytest.mark.xact
class TestXactUpscaleWarning:
    """The instrument itself separates errors (ALARM 100-110) from warnings
    (200-203). Treating a warning as fatal deleted the row's 45 element
    concentrations over what the vendor calls a near-full-scale notice."""

    @staticmethod
    def _reader(tmp_path, **kw):
        from AeroViz.rawDataReader.script.Xact import Reader

        return Reader(path=tmp_path, qc=True, quiet=True, **kw)

    @staticmethod
    def _frame():
        # Row 0 normal, row 1 an upscale *warning* (203), row 2 a real
        # instrument *error* (104 = tape). Nb is held constant so the internal
        # standard rule stays quiet and each row carries one flag only.
        idx = pd.date_range('2025-01-01', periods=3, freq='1h')
        return pd.DataFrame(
            {'Fe': [500.0, 520.0, 510.0],
             'Pb': [10.0, 11.0, 10.5],
             'Nb': [5.0, 5.0, 5.0],
             'ALARM': [0, 203, 104],
             'SAMPLE_TYPE': [1, 1, 1]},
            index=idx,
        )

    def test_warning_row_is_flagged_but_kept(self, tmp_path):
        out = self._reader(tmp_path)._QC(self._frame())

        assert out[FLAG].iloc[1] == 'Upscale Warning'
        assert not out[INVALID].iloc[1], 'a vendor warning must not delete 45 elements'

    def test_error_row_is_invalidated(self, tmp_path):
        out = self._reader(tmp_path)._QC(self._frame())

        assert out[FLAG].iloc[2] == 'Instrument Error'
        assert out[INVALID].iloc[2]

    def test_override_restores_the_old_strictness(self, tmp_path):
        reader = self._reader(tmp_path, flag_severity={'Upscale Warning': 'error'})
        out = reader._QC(self._frame())

        assert out[INVALID].iloc[1]

    def test_values_survive_into_the_public_output(self, raw_data_path, tmp_path):
        """End-to-end on the ALARM=203 fixture: the reader keeps the row.

        (That row also trips `Internal Std Drift`, an error-severity rule, so the
        check is on the flag record and verdict column rather than on the values.)
        """
        import shutil

        src = raw_data_path / 'Xact' / 'status_errors'
        if not src.exists():
            pytest.skip('Xact status_errors fixture not available')
        dst = tmp_path / 'Xact'
        shutil.copytree(src, dst)

        RawDataReader('Xact', dst, reset=True, quiet=True, fill_missing=False)
        qc = pd.read_pickle(dst / 'xact_outputs' / '_read_xact_qc.pkl')

        warned = qc[FLAG].str.contains('Upscale Warning', na=False)
        assert warned.any(), 'fixture should contain ALARM 200-203 rows'
        # Upscale Warning alone never sets the verdict; only co-occurring
        # error-severity rules do.
        warning_only = warned & ~qc[FLAG].str.contains(
            'Instrument Error|Invalid Value|Calibration Mode|Internal Std Drift', na=False)
        assert not qc.loc[warning_only, INVALID].any()


# =============================================================================
# The verdict must survive every reader's column narrowing
# =============================================================================

@pytest.mark.parametrize('instrument', ['AE33', 'APS', 'BAM1020', 'OCEC', 'SMPS', 'TEOM', 'Xact'])
def test_qc_pickle_carries_both_columns(instrument, raw_data_path, tmp_path):
    """Readers that slice to a fixed column list must keep `QC_Invalid` as well
    as `QC_Flag` — dropping it would silently make every flag fatal again."""
    import shutil

    src = raw_data_path / instrument / 'normal'
    if not src.exists():
        src = raw_data_path / instrument
    if not src.exists() or not any(src.iterdir()):
        pytest.skip(f'{instrument} fixture not available')

    dst = tmp_path / instrument
    shutil.copytree(src, dst)
    # fill_missing=False keeps the frame at the fixture's own coverage — this
    # test only inspects columns, and padding 4 years of 1-min data is slow.
    RawDataReader(instrument, dst, reset=True, quiet=True, fill_missing=False)

    qc = pd.read_pickle(dst / f'{instrument.lower()}_outputs' / f'_read_{instrument.lower()}_qc.pkl')
    assert FLAG in qc.columns
    assert INVALID in qc.columns
    assert qc[INVALID].dtype == bool


def test_public_output_never_exposes_qc_columns(raw_data_path, tmp_path):
    import shutil

    src = raw_data_path / 'OCEC' / 'normal'
    if not src.exists():
        pytest.skip('OCEC fixture not available')
    dst = tmp_path / 'OCEC'
    shutil.copytree(src, dst)

    df = RawDataReader('OCEC', dst, reset=True, quiet=True,
                       start=datetime(2023, 12, 1), end=datetime(2023, 12, 31))

    assert not [c for c in df.columns if str(c).startswith('QC_')]


def test_coverage_ignores_the_boolean_verdict(raw_data_path, tmp_path):
    """`QC_Invalid` is boolean, so False is not null: if `data_coverage` counted
    it, every padded row would look like real data."""
    import shutil

    src = raw_data_path / 'OCEC' / 'normal'
    if not src.exists():
        pytest.skip('OCEC fixture not available')
    dst = tmp_path / 'OCEC'
    shutil.copytree(src, dst)

    df = RawDataReader('OCEC', dst, reset=True, quiet=True,
                       start=datetime(2023, 1, 1), end=datetime(2023, 12, 31))

    span = df.attrs['coverage_end'] - df.attrs['coverage_start']
    assert span < pd.Timedelta(days=30), 'coverage must reflect the files, not the padding'


class TestRuleFailureIsVisible:
    """A rule that raises is disabled for that run, which weakens QC silently.
    It used to `print`; it now goes through the reader's logger."""

    def test_failure_is_logged_not_printed(self, frame, caplog):
        broken = QCRule('Broken Rule', lambda df: 1 / 0, description='raises')

        class Recorder:
            def __init__(self):
                self.messages = []

            def warning(self, msg):
                self.messages.append(msg)

        recorder = Recorder()
        out = QCFlagBuilder(logger=recorder).add_rule(broken).apply(frame)

        assert any('Broken Rule' in m and 'skipped' in m for m in recorder.messages)
        assert any('passing QC unchecked' in m for m in recorder.messages)
        # The read still completes, with the rule treated as "did not fire".
        assert (out[FLAG] == 'Valid').all()

    def test_reader_builder_wires_its_logger(self, tmp_path):
        from AeroViz.rawDataReader.script.TEOM import Reader

        reader = Reader(path=tmp_path, qc=True, quiet=True)

        assert reader.qc_builder().logger is reader.logger


def test_completeness_accepts_a_bare_pandas_freqstr():
    """`hourly_completeness_QC` must cope with 'min' / 'h' as well as '1min'."""
    from AeroViz.rawDataReader.core.qc import QualityControl

    idx = pd.date_range('2024-01-01 00:00', periods=40, freq='1min')
    df = pd.DataFrame({'v': range(40)}, index=idx)

    for freq in ('min', '1min'):
        mask = QualityControl.hourly_completeness_QC(df, freq=freq)
        # 40 of 60 expected minutes present -> above the 50% threshold
        assert not mask.any(), freq
