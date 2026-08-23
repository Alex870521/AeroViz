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
        """Test that AAE is calculated, positive by convention."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        assert 'AAE' in df.columns, "AAE column not found"
        valid_aae = df['AAE'].dropna()
        if len(valid_aae) > 0:
            assert valid_aae.min() > 0, "AAE should be positive"
            assert valid_aae.max() < 5, "AAE seems unreasonably high"

    def test_ebc_calculation(self, data_path, date_range, temp_output_dir):
        """Test that eBC (equivalent Black Carbon) is calculated."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        assert 'eBC' in df.columns, "eBC column not found"

    def test_delta_c_calculation(self, data_path, date_range, temp_output_dir):
        """Delta-C = BC1 − BC6 (370 nm − 880 nm), NaN where either band is NaN."""
        import numpy as np

        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        assert 'Delta-C' in df.columns, "Delta-C column not found"
        expected = df['BC1'] - df['BC6']
        valid = expected.notna()
        assert valid.any(), "fixture should yield at least one valid Delta-C"
        # Hourly output is rounded, so mean(BC1 − BC6) and mean(BC1) − mean(BC6)
        # can differ by one unit in the last kept decimal; native-freq is exact.
        np.testing.assert_allclose(df.loc[valid, 'Delta-C'], expected[valid], atol=1e-3)
        assert df.loc[~valid, 'Delta-C'].isna().all()

    def test_k_columns_passthrough(self, data_path, date_range, temp_output_dir):
        """K1–K7 (dual-spot loading-compensation k) are passed through."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        for i in range(1, 8):
            assert f'K{i}' in df.columns, f"K{i} column not found"
        k = df[[f'K{i}' for i in range(1, 8)]].dropna(how='all')
        assert len(k) > 0, "fixture should yield some K values"
        # Sanity: k is a small dimensionless number, |k| well below 0.1
        assert (k.abs() < 0.1).all().all()
