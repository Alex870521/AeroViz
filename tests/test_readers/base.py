"""
Base test class and utilities for instrument reader tests.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from AeroViz import RawDataReader


# =============================================================================
# Session-level cache for RawDataReader results
# =============================================================================
#
# Most reader tests within the same class call RawDataReader with the SAME
# (instrument, scenario_path, kwargs) — for example 5+ tests all read
# ``normal/``. Caching the resulting DataFrame avoids the redundant I/O +
# QC + reindex passes. On-disk pickles still exist after the first call,
# so tests that inspect ``_read_*_qc.pkl`` artifacts still work.
#
# Measured impact (post-date_range tightening): 14 s with cache vs 34 s
# without. Worth keeping despite the narrower fixtures.
#
# Mutation safety: returns a ``.copy()`` per call (cheap relative to the
# reader pipeline).
# =============================================================================

_READER_CACHE: dict[tuple, pd.DataFrame] = {}


def _make_cache_key(instrument: str, path: Path, date_range: dict,
                    kwargs: dict) -> tuple:
    return (
        instrument,
        str(path.resolve()),
        date_range['start'].isoformat(),
        date_range['end'].isoformat(),
        # Use repr to handle non-hashable values (tuples are fine, but
        # ``size_range=(11.34, 615.27)`` is the common case).
        tuple(sorted((k, repr(v)) for k, v in kwargs.items())),
    )


def _cached_reader_call(instrument: str, path: Path, date_range: dict,
                        **kwargs) -> pd.DataFrame:
    key = _make_cache_key(instrument, path, date_range, kwargs)
    cached = _READER_CACHE.get(key)
    if cached is not None:
        return cached.copy()

    df = RawDataReader(
        instrument,
        path,
        start=date_range['start'],
        end=date_range['end'],
        reset=True,
        **kwargs,
    )
    _READER_CACHE[key] = df
    return df.copy()


class BaseReaderTest(ABC):
    """
    Base class for instrument reader tests.

    Subclasses should define:
    - INSTRUMENT: str - The instrument name
    - EXPECTED_COLUMNS: list[str] - Expected output columns (optional)
    - STATUS_COLUMN: str - Name of status column if applicable (optional)
    - DATE_RANGE_START / DATE_RANGE_END: datetime - tight window covering
      the actual fixture data. RawDataReader reindexes its raw pickle to
      the full requested range at the instrument's native frequency, so
      passing a 2-year window for one day of data inflates the pickle by
      ~700× (e.g. AE33 → 529 MB). Keep this just wide enough to contain
      every scenario the subclass exercises.
    """

    INSTRUMENT: str = None
    EXPECTED_COLUMNS: list[str] = None
    STATUS_COLUMN: str = None

    # Default window — kept intentionally wide as a safety net. Every
    # subclass below sets a tighter range matched to its fixtures.
    DATE_RANGE_START: datetime = datetime(2024, 1, 1)
    DATE_RANGE_END: datetime = datetime(2026, 12, 31, 23, 59, 59)

    # Per-scenario overrides for instruments whose scenarios span widely
    # separated months (e.g. SMPS has scenarios in Jan/Feb 2025 and
    # Feb/Mar 2026). Maps the scenario subdirectory name to a
    # ``{'start': datetime, 'end': datetime}`` dict.
    SCENARIO_DATE_RANGES: dict[str, dict] = {}

    @pytest.fixture
    def data_path(self, raw_data_path):
        """Get the data path for this instrument."""
        path = raw_data_path / self.INSTRUMENT
        if not path.exists() or not any(path.iterdir()):
            pytest.skip(f'{self.INSTRUMENT} test data not available')
        return path

    @pytest.fixture
    def date_range(self):
        """Date range used by the inherited test methods.

        Driven by class attributes ``DATE_RANGE_START`` /
        ``DATE_RANGE_END``; override either in a subclass to match its
        fixture span.
        """
        return {'start': self.DATE_RANGE_START, 'end': self.DATE_RANGE_END}

    def read_data(self, path: Path, date_range: dict, **kwargs) -> pd.DataFrame:
        """Helper to read data with common settings.

        Backed by a session-scoped cache keyed on
        ``(instrument, path, date_range, kwargs)`` — see the module
        docstring for the rationale. Tests that read the on-disk pickle
        artifacts (``_read_*_qc.pkl``, ``_read_*_raw.pkl``) still work
        because the first uncached call writes them.

        If the path's leaf name appears in ``SCENARIO_DATE_RANGES``, that
        override wins over the ``date_range`` argument — keeps the raw
        pickle tight for instruments whose scenarios span widely
        separated months.
        """
        effective_range = self.SCENARIO_DATE_RANGES.get(path.name, date_range)
        return _cached_reader_call(
            self.INSTRUMENT, path, effective_range, **kwargs,
        )

    # =========================================================================
    # Common Tests
    # =========================================================================

    def test_read_normal(self, data_path, date_range, temp_output_dir):
        """Test reading normal data files."""
        # Check if normal scenario exists
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            # Use root path if no normal subdirectory
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        # Basic assertions
        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_has_qc_flag(self, data_path, date_range, temp_output_dir):
        """Test that QC_Flag is generated in intermediate QC data.

        Note: QC_Flag is intentionally dropped from the final resampled output.
        We check the intermediate QC pickle file instead.
        """
        import pandas as pd

        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        self.read_data(normal_path, date_range, qc=True)

        # Check intermediate QC pkl for QC_Flag
        output_dir = normal_path / f'{self.INSTRUMENT.lower()}_outputs'
        qc_pkl = output_dir / f'_read_{self.INSTRUMENT.lower()}_qc.pkl'
        if qc_pkl.exists():
            qc_data = pd.read_pickle(qc_pkl)
            assert 'QC_Flag' in qc_data.columns, "QC_Flag not found in intermediate QC data"
            valid_flags = qc_data['QC_Flag'].dropna().unique()
            assert len(valid_flags) > 0

    def test_date_range_filter(self, data_path, date_range, temp_output_dir):
        """Test that data is filtered to the specified date range."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        if not df.empty:
            assert df.index.min() >= date_range['start']
            assert df.index.max() <= date_range['end']

    def test_no_duplicate_index(self, data_path, date_range, temp_output_dir):
        """Test that output has no duplicate timestamps."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        assert not df.index.duplicated().any(), "Output contains duplicate timestamps"

    def test_expected_columns(self, data_path, date_range, temp_output_dir):
        """Test that expected columns are present."""
        if self.EXPECTED_COLUMNS is None:
            pytest.skip(f'EXPECTED_COLUMNS not defined for {self.INSTRUMENT}')

        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        for col in self.EXPECTED_COLUMNS:
            assert col in df.columns, f"Expected column '{col}' not found"

    # =========================================================================
    # Edge Case Tests (override in subclass if instrument has specific cases)
    # =========================================================================

    def test_multi_header_files(self, data_path, date_range, temp_output_dir):
        """Test reading files with multiple embedded headers."""
        multi_header_path = data_path / 'multi_header'
        if not multi_header_path.exists():
            pytest.skip(f'{self.INSTRUMENT} multi_header test data not available')

        df = self.read_data(multi_header_path, date_range)

        assert df is not None
        assert not df.empty
        assert not df.index.duplicated().any()

    def test_transposed_format(self, data_path, date_range, temp_output_dir):
        """Test reading transposed format files."""
        transposed_path = data_path / 'transposed'
        if not transposed_path.exists():
            pytest.skip(f'{self.INSTRUMENT} transposed test data not available')

        df = self.read_data(transposed_path, date_range)

        assert df is not None
        assert not df.empty

    def test_duplicate_timestamps(self, data_path, date_range, temp_output_dir):
        """Test handling of files with duplicate timestamps."""
        dup_path = data_path / 'duplicate_timestamps'
        if not dup_path.exists():
            pytest.skip(f'{self.INSTRUMENT} duplicate_timestamps test data not available')

        df = self.read_data(dup_path, date_range)

        assert df is not None
        # Output should have duplicates removed
        assert not df.index.duplicated().any()

    def test_status_error_detection(self, data_path, date_range, temp_output_dir):
        """Test that status errors are properly detected in intermediate QC data."""
        import pandas as pd

        if self.STATUS_COLUMN is None:
            pytest.skip(f'{self.INSTRUMENT} does not have status column')

        status_error_path = data_path / 'status_errors'
        if not status_error_path.exists():
            pytest.skip(f'{self.INSTRUMENT} status_errors test data not available')

        self.read_data(status_error_path, date_range, qc=True)

        # Check intermediate QC pkl for Status Error flags
        output_dir = status_error_path / f'{self.INSTRUMENT.lower()}_outputs'
        qc_pkl = output_dir / f'_read_{self.INSTRUMENT.lower()}_qc.pkl'
        if qc_pkl.exists():
            qc_data = pd.read_pickle(qc_pkl)
            assert 'QC_Flag' in qc_data.columns
            status_errors = qc_data['QC_Flag'].str.contains('Status Error', na=False)
            assert status_errors.any(), "Expected Status Error flags not found"
