"""
Tests for AE33 Aethalometer reader.

Test Scenarios:
- normal/: Standard AE33 .dat files
- status_errors/: Files with error status codes
"""
from datetime import datetime

import pytest

from .base import BaseReaderTest


@pytest.mark.ae33
class TestAE33Reader(BaseReaderTest):
    """Test AE33 reader functionality."""

    INSTRUMENT = 'AE33'
    STATUS_COLUMN = 'Status'

    # Fixture spans 2025-03-04 → 2025-03-05
    DATE_RANGE_START = datetime(2025, 3, 1)
    DATE_RANGE_END = datetime(2025, 3, 31, 23, 59, 59)

    # AE33 outputs BC at 7 wavelengths + derived parameters (QC_Flag is dropped after resample)
    EXPECTED_COLUMNS = [
        'BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7',
    ]

    def test_wavelength_columns(self, data_path, date_range, temp_output_dir):
        """Test that all 7 wavelength BC columns are present."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        for i in range(1, 8):
            assert f'BC{i}' in df.columns, f"BC{i} column not found"

    def test_absorption_columns(self, data_path, date_range, temp_output_dir):
        """Test that absorption coefficient columns are calculated."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        for wl in [370, 470, 520, 590, 660, 880, 950]:
            assert f'abs_{wl}' in df.columns, f"abs_{wl} column not found"

    def test_aae_calculation(self, data_path, date_range, temp_output_dir):
        """Test that AAE is calculated.

        Note: AE33 stores AAE as negative values (convention), so we check abs(AAE).
        """
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        assert 'AAE' in df.columns, "AAE column not found"
        valid_aae = df['AAE'].dropna().abs()
        if len(valid_aae) > 0:
            assert valid_aae.min() > 0, "AAE absolute value should be positive"
            assert valid_aae.max() < 5, "AAE seems unreasonably high"

    def test_ebc_calculation(self, data_path, date_range, temp_output_dir):
        """Test that eBC (equivalent Black Carbon) is calculated."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        assert 'eBC' in df.columns, "eBC column not found"
