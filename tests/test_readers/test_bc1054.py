"""
Tests for BC1054 Black Carbon Monitor reader.

Test Scenarios:
- normal/: Standard BC1054 files with status=0
- status_errors/: Files with non-zero status codes (4096, 65536, 4128)
"""
import pandas as pd
import pytest

from .base import BaseReaderTest


@pytest.mark.bc1054
class TestBC1054Reader(BaseReaderTest):
    INSTRUMENT = 'BC1054'
    STATUS_COLUMN = 'Status'

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
