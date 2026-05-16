"""
Base test class and utilities for instrument reader tests.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from AeroViz import RawDataReader


class BaseReaderTest(ABC):
    """
    Base class for instrument reader tests.

    Subclasses should define:
    - INSTRUMENT: str - The instrument name
    - EXPECTED_COLUMNS: list[str] - Expected output columns (optional)
    - STATUS_COLUMN: str - Name of status column if applicable (optional)
    """

    INSTRUMENT: str = None
    EXPECTED_COLUMNS: list[str] = None
    STATUS_COLUMN: str = None

    @pytest.fixture
    def data_path(self, raw_data_path):
        """Get the data path for this instrument."""
        path = raw_data_path / self.INSTRUMENT
        if not path.exists() or not any(path.iterdir()):
            pytest.skip(f'{self.INSTRUMENT} test data not available')
        return path

    @pytest.fixture
    def date_range(self):
        """Default date range - override in subclass if needed.

        Uses a narrow range around the test data to avoid slow reindexing.
        Covers 2025-01 to 2026-12 to include most fixture data.
        """
        return {
            'start': datetime(2025, 1, 1),
            'end': datetime(2026, 12, 31, 23, 59, 59)
        }

    def read_data(self, path: Path, date_range: dict, **kwargs) -> pd.DataFrame:
        """Helper to read data with common settings."""
        return RawDataReader(
            self.INSTRUMENT,
            path,
            start=date_range['start'],
            end=date_range['end'],
            reset=True,
            **kwargs
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
