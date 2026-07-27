"""
Tests for BC1054 Black Carbon Monitor reader.

Test Scenarios:
- normal/: Standard BC1054 files with status=0
- status_errors/: Files with non-zero status codes (4096, 65536, 4128)
"""
from datetime import datetime

import pandas as pd
import pytest

from .base import BaseReaderTest


@pytest.mark.bc1054
class TestBC1054Reader(BaseReaderTest):
    INSTRUMENT = 'BC1054'
    STATUS_COLUMN = 'Status'

    # Fixture spans 2025-01-01 → 2025-02-03
    DATE_RANGE_START = datetime(2025, 1, 1)
    DATE_RANGE_END = datetime(2025, 2, 28, 23, 59, 59)

    EXPECTED_COLUMNS = [
        'BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7', 'BC8', 'BC9', 'BC10',
        'abs_370', 'abs_880', 'AAE', 'eBC',
    ]

    def test_raw_data_has_all_columns(self, data_path, date_range, temp_output_dir):
        """Test that raw pickle preserves all original columns (BC + metadata)."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        self.read_data(normal_path, date_range)

        output_dir = normal_path / 'bc1054_outputs'
        raw_pkl = output_dir / '_read_bc1054_raw.pkl'
        if raw_pkl.exists():
            raw_data = pd.read_pickle(raw_pkl)
            # Should have BC columns
            for col in ['BC1', 'BC10']:
                assert col in raw_data.columns, f"{col} not found in raw data"

            # Should have metadata columns (Flow, AT, RH, BP, etc.)
            bc_cols = ['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7', 'BC8', 'BC9', 'BC10']
            metadata_cols = [c for c in raw_data.columns
                           if c not in bc_cols and c != 'Status']
            assert len(metadata_cols) > 0, "Expected metadata columns in raw data"

    def test_absorption_columns(self, data_path, date_range, temp_output_dir):
        """Test that absorption coefficients are calculated."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        for col in ['abs_370', 'abs_880', 'AAE', 'eBC']:
            assert col in df.columns, f"{col} not found"


@pytest.mark.bc1054
class TestTwoClocks:
    """A BC1054 file can carry two different clocks.

    `Time` is the manual's own field — "the date and timestamp for the data
    record ... end of the minute" — and comes from the instrument's internal RTC,
    which an operator sets by hand (manual 3.5.7 SET CLOCK) and which can
    therefore be wrong. `Raw_Time` appears nowhere in the manual, so it comes from
    whatever logged the file, on that host's clock.

    The index stays on `Raw_Time`: the measurement happened at the wall-clock
    instant whatever the instrument believed, and in the corpus it is the
    well-behaved column. But the instrument's timestamp is evidence about the
    instrument, so it is kept rather than dropped.
    """

    class _Recorder:
        def __init__(self):
            self.messages = []

        def warning(self, msg):
            self.messages.append(msg)

        def info(self, msg):
            pass

        def debug(self, msg):
            pass

    @staticmethod
    def _reader(tmp_path):
        from AeroViz.rawDataReader.script.BC1054 import Reader

        return Reader(path=tmp_path, qc=False, quiet=True)

    def _read(self, path, tmp_path):
        reader = self._reader(tmp_path)
        reader.logger = self._Recorder()
        return reader._raw_reader(path), reader.logger.messages

    @pytest.mark.parametrize('scenario', ['normal', 'status_errors'])
    def test_instrument_clock_is_kept(self, scenario, raw_data_path, tmp_path):
        src = next((raw_data_path / 'BC1054' / scenario).glob('raw_*.csv'), None)
        if src is None:
            pytest.skip(f'BC1054 {scenario} fixture not available')

        df, _ = self._read(src, tmp_path)

        assert 'Instrument_Time' in df.columns, 'the instrument clock must not be dropped'
        assert 'Time' not in df.columns, 'renamed, so it cannot be confused with the index'

    def test_index_uses_the_logger_clock(self, raw_data_path, tmp_path):
        """`Raw_Time` is the well-behaved one: strictly increasing, no repeats."""
        src = next((raw_data_path / 'BC1054' / 'normal').glob('raw_*.csv'), None)
        if src is None:
            pytest.skip('BC1054 fixture not available')

        df, _ = self._read(src, tmp_path)

        assert df.index.is_monotonic_increasing
        assert df.index.is_unique

    def test_twelve_hour_offset_is_reported(self, raw_data_path, tmp_path):
        """The status_errors fixture sits a constant 12 h 04 m behind for all 1440
        rows of a day — an RTC set to the wrong AM/PM, plus drift. That used to
        vanish with the dropped column."""
        src = next((raw_data_path / 'BC1054' / 'status_errors').glob('raw_*.csv'), None)
        if src is None:
            pytest.skip('BC1054 status_errors fixture not available')

        _, messages = self._read(src, tmp_path)

        assert len(messages) == 1
        assert '12h04m' in messages[0]
        assert 'behind' in messages[0]
        assert 'SET CLOCK' in messages[0], 'the message should say how to fix it'

    def test_small_offsets_stay_quiet(self, tmp_path):
        """The manual labels records at the end of the minute, so a minute of
        slack is expected bookkeeping rather than a fault."""
        import pandas as pd

        reader = self._reader(tmp_path)
        reader.logger = self._Recorder()
        idx = pd.date_range('2025-02-03 14:00', periods=5, freq='1min')
        df = pd.DataFrame({'Instrument_Time': idx - pd.Timedelta(seconds=60)}, index=idx)

        reader._check_clock_offset(df, tmp_path / 'x.csv')

        assert reader.logger.messages == []

    def test_offset_formatting(self):
        from AeroViz.rawDataReader.script.BC1054 import Reader

        assert Reader._format_offset(45) == '45s'
        assert Reader._format_offset(180) == '3m'
        assert Reader._format_offset(43440) == '12h04m'
