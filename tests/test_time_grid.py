"""Unit tests for the time-grid helpers (frequency detection, mixed-resolution
reconciliation, off-grid snapping, and grid placement)."""
import pandas as pd
import pytest

from AeroViz.rawDataReader.core.time_grid import (
    detect_freq,
    detect_isolated_dates,
    resolve_freq,
    snap_to_grid,
    to_grid,
)


# ---------------------------------------------------------------- detect_freq
class TestDetectFreq:
    @pytest.mark.parametrize('freq', ['1min', '5min', '6min', '1h', '30min'])
    def test_regular_index(self, freq):
        idx = pd.date_range('2024-01-01', periods=20, freq=freq)
        # to_offset normalises ('1h' -> 'h', '1min' -> 'min'); compare via offset
        assert pd.tseries.frequencies.to_offset(detect_freq(idx)) == pd.tseries.frequencies.to_offset(freq)

    def test_single_row_returns_none(self):
        assert detect_freq(pd.DatetimeIndex(['2024-01-01'])) is None

    def test_empty_returns_none(self):
        assert detect_freq(pd.DatetimeIndex([])) is None

    def test_jittery_gappy_uses_median(self):
        # ~6 min cadence with jitter and a gap -> median wins
        idx = pd.DatetimeIndex([
            '2024-01-01 00:00', '2024-01-01 00:05:50',
            '2024-01-01 00:12', '2024-01-01 01:00',
        ])
        assert detect_freq(idx) == '6min'


    def test_sub_minute_period_survives_with_enough_samples(self):
        """An instrument whose period is not a whole number of minutes must get a
        grid that matches it. The APS samples every 115 s (`Sample Time 115`);
        rounding that to a 2-minute grid drifts 5 s per scan until two land in one
        bin and one is dropped — ~3% of a day, silently."""
        import numpy as np

        rng = np.random.default_rng(0)
        deltas = rng.choice([115, 130], size=700, p=[0.73, 0.27])
        idx = pd.DatetimeIndex(
            pd.Timestamp('2025-11-17') + pd.to_timedelta(np.cumsum(deltas), unit='s'))

        assert detect_freq(idx) == '115s'

    def test_small_samples_still_round_to_minutes(self):
        """With a handful of intervals the median is noise, not precision: three
        intervals of a 6-minute instrument can median to 370 s."""
        idx = pd.DatetimeIndex([
            '2024-01-01 00:00', '2024-01-01 00:05:50',
            '2024-01-01 00:12', '2024-01-01 01:00',
        ])

        assert detect_freq(idx) == '6min'

    def test_whole_minute_periods_stay_in_minutes(self):
        """Second-precision must not make readable grids ugly: 360 s is '6min'."""
        import numpy as np

        rng = np.random.default_rng(1)
        deltas = rng.choice([358, 360, 362], size=200)
        idx = pd.DatetimeIndex(
            pd.Timestamp('2024-01-01') + pd.to_timedelta(np.cumsum(deltas), unit='s'))

        assert detect_freq(idx) == '6min'


# --------------------------------------------------------------- resolve_freq
    @pytest.mark.parametrize('freq,expected', [
        ('1min', '1min'), ('6min', '6min'), ('1h', '1h'), ('5min', '5min'),
    ])
    def test_multiplier_is_always_explicit(self, freq, expected):
        """pandas omits the multiplier when it is 1 (`inferred_freq` -> 'min'),
        but `pd.Timedelta('min')` raises "unit abbreviation w/o a number". Any
        consumer measuring a duration from this string would break, and the
        hourly-completeness rule did exactly that — silently, because a QC rule
        that raises is caught and treated as "did not fire"."""
        idx = pd.date_range('2024-01-01', periods=12, freq=freq)

        detected = detect_freq(idx)

        assert detected == expected
        assert pd.Timedelta(detected) == pd.Timedelta(freq)


class TestResolveFreq:
    def test_unanimous(self):
        assert resolve_freq({'a': '6min', 'b': '6min'}) == ('6min', False)

    def test_override_wins(self):
        assert resolve_freq({'a': '1min'}, override='1h') == ('1h', False)

    def test_none_detected_uses_fallback(self):
        assert resolve_freq({'a': None, 'b': None}, fallback='5min') == ('5min', False)

    def test_mixed_picks_mode_and_flags(self):
        freq, mixed = resolve_freq({'a': '1min', 'b': '1min', 'c': '6min'})
        assert (freq, mixed) == ('1min', True)

    def test_mixed_warns(self):
        warnings = []

        class _Logger:
            def warning(self, msg):
                warnings.append(msg)

        resolve_freq({'a': '1min', 'b': '6min'}, logger=_Logger())
        assert warnings and 'Mixed time resolution' in warnings[0]


# ------------------------------------------------------- detect_isolated_dates
class TestDetectIsolatedDates:
    def _year(self, n=500, freq='6min'):
        return pd.date_range('2023-01-01', periods=n, freq=freq)

    def test_leading_stray_is_flagged(self):
        # The reported bug: one year-2000 row in front of a year of 6-min data.
        idx = pd.DatetimeIndex(['2000-01-01 00:00']).append(self._year())
        mask = detect_isolated_dates(idx)
        assert mask[0] and not mask[1:].any()

    def test_trailing_stray_is_flagged(self):
        idx = self._year().append(pd.DatetimeIndex(['2099-01-01 00:00']))
        mask = detect_isolated_dates(idx)
        assert mask[-1] and not mask[:-1].any()

    def test_clean_data_flags_nothing(self):
        assert not detect_isolated_dates(self._year()).any()

    def test_edges_of_evenly_spread_data_not_flagged(self):
        # Points at the extremes of a normal span score ~2 MADs, well under k=10.
        assert not detect_isolated_dates(self._year(n=2000)).any()

    def test_two_legit_clusters_not_flagged(self):
        # A 2019 campaign + a 2023 campaign (each substantial) is legitimately
        # wide data, not a stray — must be left alone.
        idx = pd.date_range('2019-01-01', periods=300, freq='1h').append(
            pd.date_range('2023-01-01', periods=300, freq='1h'))
        assert not detect_isolated_dates(idx).any()

    def test_too_few_rows_flags_nothing(self):
        idx = pd.DatetimeIndex(['2000-01-01', '2023-01-01', '2023-01-02'])
        assert not detect_isolated_dates(idx).any()

    def test_nat_rows_never_flagged(self):
        idx = pd.DatetimeIndex(['2000-01-01']).append(self._year()).append(
            pd.DatetimeIndex([pd.NaT]))
        mask = detect_isolated_dates(idx)
        assert mask[0] and not mask[-1]  # stray flagged, NaT left to the parser


# --------------------------------------------------------------- snap_to_grid
class TestSnapToGrid:
    def test_off_grid_point_lands_in_one_bin(self):
        # The duplicate-fill repro: a single 00:30 reading on a 1h grid must not
        # be duplicated into both 00:00 and 01:00.
        src = pd.DataFrame({'v': [42.0]}, index=pd.DatetimeIndex(['2024-01-01 00:30']))
        out = to_grid(src, '1h',
                      start=pd.Timestamp('2024-01-01 00:00'),
                      end=pd.Timestamp('2024-01-01 01:00'))
        assert out['v'].tolist() == [42.0] or pd.isna(out['v'].iloc[1])
        assert (out['v'] == 42.0).sum() == 1  # exactly one slot filled

    def test_preserves_rounding_intent(self):
        idx = pd.DatetimeIndex(['2024-01-01 08:20', '2024-01-01 08:40'])
        snapped = snap_to_grid(pd.DataFrame({'v': [1, 2]}, index=idx), '1h')
        assert list(snapped.index) == [pd.Timestamp('2024-01-01 08:00'),
                                       pd.Timestamp('2024-01-01 09:00')]

    def test_duplicate_bins_collapse_first_wins(self):
        idx = pd.DatetimeIndex(['2024-01-01 08:01', '2024-01-01 08:02'])
        snapped = snap_to_grid(pd.DataFrame({'v': [1, 2]}, index=idx), '1h')
        assert len(snapped) == 1
        assert snapped['v'].iloc[0] == 1  # keep='first'

    def test_empty_passthrough(self):
        empty = pd.DataFrame({'v': []}, index=pd.DatetimeIndex([]))
        assert snap_to_grid(empty, '1h').empty


# -------------------------------------------------------------------- to_grid
class TestToGrid:
    def _short(self):
        return pd.DataFrame({'v': [1.0, 2.0]},
                            index=pd.date_range('2024-03-05', periods=2, freq='1h'))

    def test_fill_missing_true_pads_to_request(self):
        out = to_grid(self._short(), '1h',
                      start=pd.Timestamp('2024-01-01'),
                      end=pd.Timestamp('2024-12-31'), fill_missing=True)
        assert out.index.min() == pd.Timestamp('2024-01-01')
        assert len(out) > 8000  # full-year hourly grid

    def test_fill_missing_false_clamps_to_coverage(self):
        out = to_grid(self._short(), '1h',
                      start=pd.Timestamp('2024-01-01'),
                      end=pd.Timestamp('2024-12-31'), fill_missing=False)
        assert len(out) == 2
        assert out.index.min() == pd.Timestamp('2024-03-05 00:00')
        assert out.index.max() == pd.Timestamp('2024-03-05 01:00')

    def test_false_never_larger_than_true(self):
        true_ = to_grid(self._short(), '1h', start=pd.Timestamp('2024-01-01'),
                        end=pd.Timestamp('2024-12-31'), fill_missing=True)
        false_ = to_grid(self._short(), '1h', start=pd.Timestamp('2024-01-01'),
                         end=pd.Timestamp('2024-12-31'), fill_missing=False)
        assert len(false_) <= len(true_)

    def test_request_outside_coverage_returns_empty(self):
        out = to_grid(self._short(), '1h',
                      start=pd.Timestamp('2025-01-01'),
                      end=pd.Timestamp('2025-02-01'), fill_missing=False)
        assert out.empty


class TestSnapCollisionIsReported:
    """Collapsing rows into an occupied bin is silent data loss when the grid does
    not match the instrument's true period."""

    class _Recorder:
        def __init__(self):
            self.messages = []

        def warning(self, msg):
            self.messages.append(msg)

    def _drifting(self):
        import numpy as np

        rng = np.random.default_rng(0)
        deltas = rng.choice([115, 130], size=700, p=[0.73, 0.27])
        idx = pd.DatetimeIndex(
            pd.Timestamp('2025-11-17') + pd.to_timedelta(np.cumsum(deltas), unit='s'))
        return pd.DataFrame({'v': range(len(idx))}, index=idx)

    def test_warns_when_rows_are_dropped(self):
        df = self._drifting()
        recorder = self._Recorder()

        out = snap_to_grid(df, '2min', logger=recorder)

        assert len(out) < len(df)
        assert len(recorder.messages) == 1
        assert 'already-occupied 2min bin' in recorder.messages[0]
        assert 'raw_freq=' in recorder.messages[0]

    def test_silent_when_the_grid_matches(self):
        df = self._drifting()
        recorder = self._Recorder()

        out = snap_to_grid(df, '115s', logger=recorder)

        assert len(out) == len(df), 'a matching grid must not drop anything'
        assert recorder.messages == []

    def test_no_logger_is_fine(self):
        """The helper is used outside the reader too."""
        assert len(snap_to_grid(self._drifting(), '2min')) < 700

    def test_genuine_duplicates_still_collapse(self):
        """The dedup itself is intended behaviour — two readings at the same
        timestamp must not occupy two slots."""
        idx = pd.DatetimeIndex(['2024-01-01 00:00', '2024-01-01 00:00',
                                '2024-01-01 00:06'])
        df = pd.DataFrame({'v': [1, 2, 3]}, index=idx)

        out = snap_to_grid(df, '6min')

        assert len(out) == 2
        assert out['v'].iloc[0] == 1, 'first wins'
