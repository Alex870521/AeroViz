"""
Tests for SMPS (Scanning Mobility Particle Sizer) reader.

Test Scenarios:
- normal/: Standard SMPS export files (.txt)
- csv_format/: AIM 11.x CSV format files
- status_errors/: Files with non-Normal Scan status
"""
from datetime import datetime

import pandas as pd
import pytest

from .base import BaseReaderTest


@pytest.mark.smps
class TestSMPSReader(BaseReaderTest):
    """Test SMPS reader functionality."""

    INSTRUMENT = 'SMPS'
    STATUS_COLUMN = 'Status Flag'

    # The four SMPS scenarios live in widely separated months — each
    # gets a tight 1-month window via SCENARIO_DATE_RANGES so the
    # reindexed raw pickle stays small.
    DATE_RANGE_START = datetime(2025, 2, 1)   # default = "normal" scenario
    DATE_RANGE_END = datetime(2025, 2, 28, 23, 59, 59)

    SCENARIO_DATE_RANGES = {
        'status_errors': {
            'start': datetime(2025, 1, 1),
            'end': datetime(2025, 1, 31, 23, 59, 59),
        },
        'csv_format': {
            'start': datetime(2026, 2, 1),
            'end': datetime(2026, 2, 28, 23, 59, 59),
        },
        'time_misalignment': {
            'start': datetime(2026, 3, 1),
            'end': datetime(2026, 3, 31, 23, 59, 59),
        },
    }

    # The reader returns the dN/dlogDp size distribution (diameters as float
    # columns); summary statistics are derived on demand via psd_stats().
    EXPECTED_COLUMNS = None

    def test_returns_size_distribution(self, data_path, date_range, temp_output_dir):
        """Reader returns dN/dlogDp with float-diameter columns (no stats baked in)."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        assert len(df.columns) > 0
        # Every column is a numeric particle diameter (nm)
        assert all(isinstance(c, (int, float)) for c in df.columns), \
            f"Expected float-diameter columns, got {list(df.columns[:5])}"
        # Statistics are no longer baked into the reader output
        assert 'total_num' not in df.columns

    def test_statistics_via_psd_stats(self, data_path, date_range, temp_output_dir):
        """psd_stats() derives the size-distribution statistics from the reader output."""
        from AeroViz import psd_stats

        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)
        stats = psd_stats(df)['other']

        assert any('total_num' in str(c) for c in stats.columns), "total_num stat not found"
        valid = stats.filter(like='total_num').dropna(how='all')
        if len(valid) > 0:
            assert (valid.fillna(0).to_numpy() >= 0).all(), "total_num should be non-negative"

    def test_output_files_written(self, data_path, date_range, temp_output_dir):
        """Reader writes N/S/V distribution files + a statistics sidecar."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        self.read_data(normal_path, date_range)

        out = normal_path / 'smps_outputs'
        for name in ('output_smps_dNdlogDp.csv', 'output_smps_dSdlogDp.csv',
                     'output_smps_dVdlogDp.csv', 'output_smps_stats.csv'):
            assert (out / name).exists(), f"{name} not written"

    def test_append_stats(self, data_path, date_range, temp_output_dir):
        """append_stats=True appends stat columns; default keeps a clean PSD matrix."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        clean = self.read_data(normal_path, date_range)
        fat = self.read_data(normal_path, date_range, append_stats=True)

        assert all(isinstance(c, (int, float)) for c in clean.columns)
        # Appended frame keeps the bins and gains string-named stat columns
        assert any(isinstance(c, (int, float)) for c in fat.columns)
        assert any(isinstance(c, str) and 'total_num' in c for c in fat.columns)

    def test_raw_data_has_all_columns(self, data_path, date_range, temp_output_dir):
        """Test that raw pickle preserves all original columns (size bins + metadata)."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        self.read_data(normal_path, date_range)

        output_dir = normal_path / 'smps_outputs'
        raw_pkl = output_dir / '_read_smps_raw.pkl'
        if raw_pkl.exists():
            raw_data = pd.read_pickle(raw_pkl)
            # Should have size bins (float columns)
            bin_cols = [c for c in raw_data.columns if isinstance(c, (int, float))]
            assert len(bin_cols) >= 100, f"Expected ~110 size bins, got {len(bin_cols)}"

            # Should also have metadata columns (string columns)
            meta_cols = [c for c in raw_data.columns if isinstance(c, str)]
            assert len(meta_cols) > 0, "Expected metadata columns in raw data"

    def test_time_misalignment(self, data_path, date_range, temp_output_dir):
        """Test reading files with misaligned timestamps (e.g., starts at :25, :32).

        Verifies that:
        - Multi-header files are parsed correctly
        - Time index is aligned to even grid despite odd start times
        - No duplicate timestamps in output
        - raw_freq override works
        """
        misalign_path = data_path / 'time_misalignment'
        if not misalign_path.exists():
            pytest.skip('SMPS time_misalignment test data not available')

        df = self.read_data(misalign_path, date_range, raw_freq='2min', size_range=(3.11, 105.5))

        assert df is not None
        assert not df.empty
        assert not df.index.duplicated().any(), "Output contains duplicate timestamps"

        # Verify grid alignment: all timestamps should be on even minutes
        minutes = df.index.minute
        assert (minutes % 2 == 0).all(), (
            f"Expected all timestamps on 2min grid, but found odd minutes: "
            f"{df.index[minutes % 2 != 0].tolist()[:5]}"
        )

    def test_csv_format(self, data_path, date_range, temp_output_dir):
        """Test reading AIM 11.x CSV format files.

        AIM 11.x has a different size range (11.34-615.27) than AIM 10.x (11.8-593.5).
        """
        csv_path = data_path / 'csv_format'
        if not csv_path.exists():
            pytest.skip('SMPS csv_format test data not available')

        df = self.read_data(csv_path, date_range, size_range=(11.34, 615.27))
        assert df is not None
        assert not df.empty
