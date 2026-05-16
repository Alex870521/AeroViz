"""
Tests for TEOM (Tapered Element Oscillating Microbalance) reader.

Test Scenarios:
- normal/: Standard TEOM files (remote download format)
- usb_format/: USB download format (Date + Time columns)
- status_errors/: Files with non-zero status codes
"""
import pandas as pd
import pytest

from .base import BaseReaderTest


@pytest.mark.teom
class TestTEOMReader(BaseReaderTest):
    """Test TEOM reader functionality."""

    INSTRUMENT = 'TEOM'
    STATUS_COLUMN = 'status'

    EXPECTED_COLUMNS = [
        'PM_NV', 'PM_Total', 'Volatile_Fraction',
    ]

    def test_volatile_fraction(self, data_path, date_range, temp_output_dir):
        """Test that Volatile_Fraction is calculated correctly."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        if 'Volatile_Fraction' in df.columns:
            valid_vf = df['Volatile_Fraction'].dropna()
            if len(valid_vf) > 0:
                # Volatile fraction should be between 0 and 1
                assert valid_vf.min() >= 0, "Volatile_Fraction should be >= 0"
                assert valid_vf.max() <= 1, "Volatile_Fraction should be <= 1"

    def test_raw_data_has_all_columns(self, data_path, date_range, temp_output_dir):
        """Test that raw pickle preserves all original columns (PM + metadata)."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        self.read_data(normal_path, date_range)

        output_dir = normal_path / 'teom_outputs'
        raw_pkl = output_dir / '_read_teom_raw.pkl'
        if raw_pkl.exists():
            raw_data = pd.read_pickle(raw_pkl)
            # Should have PM columns
            for col in ['PM_NV', 'PM_Total']:
                assert col in raw_data.columns, f"{col} not found in raw data"

            # Should have metadata columns (temperatures, flow rates, etc.)
            metadata_cols = [c for c in raw_data.columns if c not in ['PM_NV', 'PM_Total']]
            assert len(metadata_cols) > 2, f"Expected metadata columns, got only {metadata_cols}"

    def test_usb_format(self, data_path, date_range, temp_output_dir):
        """Test reading USB download format (Date + Time columns)."""
        usb_path = data_path / 'usb_format'
        if not usb_path.exists():
            pytest.skip('TEOM usb_format test data not available')

        df = self.read_data(usb_path, date_range)
        assert df is not None
        assert not df.empty
