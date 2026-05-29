"""
Tests for TEOM (Tapered Element Oscillating Microbalance) reader.

Test Scenarios:
- normal/: Standard TEOM files (remote download format)
- usb_format/: USB download format (Date + Time columns)
- status_errors/: Files with non-zero status codes
"""
from datetime import datetime

import pandas as pd
import pytest

from .base import BaseReaderTest


@pytest.mark.teom
class TestTEOMReader(BaseReaderTest):
    """Test TEOM reader functionality."""

    INSTRUMENT = 'TEOM'
    STATUS_COLUMN = 'status'

    # Three scenarios in distinct months — use per-scenario ranges.
    DATE_RANGE_START = datetime(2025, 6, 1)   # default = "normal" scenario
    DATE_RANGE_END = datetime(2025, 6, 30, 23, 59, 59)

    SCENARIO_DATE_RANGES = {
        'status_errors': {
            'start': datetime(2025, 10, 1),
            'end': datetime(2025, 10, 31, 23, 59, 59),
        },
        'usb_format': {
            'start': datetime(2025, 1, 1),
            'end': datetime(2025, 1, 7, 23, 59, 59),
        },
    }

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

    def test_metadata_alias_maps_split(self):
        """Both alias maps are present as class attrs and converge on the same
        short canonical names — so applying them together is safe.
        """
        from AeroViz.rawDataReader.script.TEOM import Reader
        # Each map exists, is non-empty, and uses the same canonical targets.
        assert Reader.METADATA_ALIASES_REMOTE
        assert Reader.METADATA_ALIASES_USB
        # No key overlap between the two maps (would silently collide).
        overlap = set(Reader.METADATA_ALIASES_REMOTE) & set(Reader.METADATA_ALIASES_USB)
        assert not overlap, f"Remote and USB alias maps share keys: {overlap}"
        # Both maps target the same canonical short-name vocabulary.
        canonical = set(Reader.METADATA_ALIASES_REMOTE.values()) | set(Reader.METADATA_ALIASES_USB.values())
        for required in ('time', 'status', 'PM_NV', 'PM_Total'):
            assert required in canonical, f"Canonical name {required!r} missing from alias maps"

    def test_format_detection_logged(self, data_path, date_range, temp_output_dir, caplog):
        """Reader emits a debug-level message naming the detected format. Useful
        when a mixed-source batch needs triaging — operators can grep the log
        for which file in a batch is on which format.

        Bypasses the shared `_cached_reader_call` (which would short-circuit a
        repeat read and emit no log) by going through `RawDataReader` directly.
        """
        import logging
        from AeroViz import RawDataReader

        usb_path = data_path / 'usb_format'
        if not usb_path.exists():
            pytest.skip('TEOM usb_format test data not available')

        scenario = self.SCENARIO_DATE_RANGES.get('usb_format', date_range)
        with caplog.at_level(logging.DEBUG, logger='TEOM'):
            RawDataReader(
                'TEOM', usb_path,
                start=scenario['start'], end=scenario['end'],
                reset=True, mean_freq='1h',
                save_pkl=False, save_intermediate_csv=False, save_report=False,
                quiet=True, log_level='DEBUG',
            )

        msgs = [r.getMessage() for r in caplog.records if r.name == 'TEOM']
        assert any('USB-export format' in m for m in msgs), (
            f"Expected USB format detection log, got: {msgs[-5:]}"
        )
