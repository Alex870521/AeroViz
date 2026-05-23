"""Unit tests for the time-grid helpers (frequency detection, mixed-resolution
reconciliation, off-grid snapping, and grid placement)."""
import pandas as pd
import pytest

from AeroViz.rawDataReader.core.time_grid import (
    detect_freq,
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


# --------------------------------------------------------------- resolve_freq
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
