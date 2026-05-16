"""
Tests for APS (Aerodynamic Particle Sizer) reader.

Test Scenarios:
- normal/: Standard APS export files
- multi_header/: Files with multiple concatenated headers
- status_errors/: Files with non-zero status flags
"""
import pandas as pd
import pytest

from .base import BaseReaderTest


@pytest.mark.aps
class TestAPSReader(BaseReaderTest):
    """Test APS reader functionality."""

    INSTRUMENT = 'APS'
    STATUS_COLUMN = 'Status Flags'

    # APS __call__ filters out size bins, returning only statistics
    EXPECTED_COLUMNS = [
        'total_num_all', 'GMD_num', 'GSD_num',
        'total_surf_all', 'GMD_surf', 'GSD_surf',
        'total_vol_all', 'GMD_vol', 'GSD_vol',
    ]

    def test_statistics_calculated(self, data_path, date_range, temp_output_dir):
        """Test that size distribution statistics are calculated."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        for stat in ['total_num_all', 'GMD_num', 'GSD_num']:
            assert stat in df.columns, f"{stat} column not found"

    def test_raw_data_has_all_columns(self, data_path, date_range, temp_output_dir):
        """Test that raw pickle preserves all original columns (size bins + metadata)."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        self.read_data(normal_path, date_range)

        output_dir = normal_path / 'aps_outputs'
        raw_pkl = output_dir / '_read_aps_raw.pkl'
        if raw_pkl.exists():
            raw_data = pd.read_pickle(raw_pkl)
            # Should have size bins (float columns)
            bin_cols = [c for c in raw_data.columns if isinstance(c, (int, float))]
            assert len(bin_cols) >= 20, f"Expected ~52 size bins, got {len(bin_cols)}"

            # Should also have metadata columns (string columns)
            meta_cols = [c for c in raw_data.columns if isinstance(c, str)]
            assert len(meta_cols) > 0, "Expected metadata columns in raw data"

    def test_binary_status_flags(self, data_path, date_range, temp_output_dir):
        """Test that binary status flags are correctly detected in QC data."""
        status_error_path = data_path / 'status_errors'
        if not status_error_path.exists():
            pytest.skip('APS status_errors test data not available')

        self.read_data(status_error_path, date_range, qc=True)

        output_dir = status_error_path / 'aps_outputs'
        qc_pkl = output_dir / '_read_aps_qc.pkl'
        if qc_pkl.exists():
            qc_data = pd.read_pickle(qc_pkl)
            assert 'QC_Flag' in qc_data.columns
            status_errors = qc_data['QC_Flag'].str.contains('Status Error', na=False)
            assert status_errors.any(), "Binary status flags not detected"
