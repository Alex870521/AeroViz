"""
Tests for SMPS (Scanning Mobility Particle Sizer) reader.

Test Scenarios:
- normal/: Standard SMPS export files (.txt)
- csv_format/: AIM 11.x CSV format files
- status_errors/: Files with non-Normal Scan status
"""
import pandas as pd
import pytest

from .base import BaseReaderTest


@pytest.mark.smps
class TestSMPSReader(BaseReaderTest):
    """Test SMPS reader functionality."""

    INSTRUMENT = 'SMPS'
    STATUS_COLUMN = 'Status Flag'

    # SMPS __call__ filters out size bins, returning only statistics
    EXPECTED_COLUMNS = [
        'total_num', 'GMD_num', 'GSD_num',
        'total_surf', 'GMD_surf', 'GSD_surf',
        'total_vol', 'GMD_vol', 'GSD_vol',
    ]

    def test_statistics_calculated(self, data_path, date_range, temp_output_dir):
        """Test that size distribution statistics are calculated."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        for stat in ['total_num', 'GMD_num', 'GSD_num', 'mode_num']:
            assert stat in df.columns, f"{stat} column not found"

        # total_num should be positive
        valid = df['total_num'].dropna()
        if len(valid) > 0:
            assert valid.min() > 0, "total_num should be positive"

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
