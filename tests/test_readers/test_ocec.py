"""Tests for OCEC (Sunset OC/EC Analyzer) reader.

Test Scenarios:
- normal/: RTCalc802 firmware — has OCPk1..4-ug C per-peak fractions
- legacy_rtcalc705/: older RTCalc705 firmware — no per-peak fractions
"""
from datetime import datetime

import pandas as pd
import pytest

from .base import BaseReaderTest


@pytest.mark.ocec
class TestOCECReader(BaseReaderTest):
    """Test OCEC reader functionality.

    Two fixtures pulled from real-world Sunset OC/EC exports verify both
    firmware paths through `_raw_reader`. The output schema is uniform
    regardless of firmware (OC1..OC4 are present but NaN on RTCalc705).
    """

    INSTRUMENT = 'OCEC'
    # The reader's public output drops `QC_Flag` (intermediate-only) and
    # leaves the OUTPUT_COLUMNS as the user-facing schema.
    EXPECTED_COLUMNS = ['Thermal_OC', 'Thermal_EC', 'Optical_OC', 'Optical_EC', 'TC',
                        'OC1', 'OC2', 'OC3', 'OC4', 'PC']

    # The two fixture scenarios live in different months / years; each gets
    # a tight 1-month window so the raw pickle stays small.
    DATE_RANGE_START = datetime(2023, 12, 1)   # default = "normal" (RTCalc802)
    DATE_RANGE_END = datetime(2023, 12, 31, 23, 59, 59)

    SCENARIO_DATE_RANGES = {
        'legacy_rtcalc705': {
            'start': datetime(2022, 12, 1),
            'end': datetime(2022, 12, 31, 23, 59, 59),
        },
    }

    def test_rtcalc802_per_peak_columns_present(self, data_path, date_range, temp_output_dir):
        """RTCalc802 input populates the OC1..OC4 per-peak columns with
        finite values (not all-NaN), confirming the per-peak derivation runs
        when the source `OCPk*-ug C` columns exist."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            pytest.skip('OCEC normal (RTCalc802) fixture not available')

        df = self.read_data(normal_path, date_range)
        # On RTCalc802, at least one OC{i} column must carry a real value.
        per_peak_any = any(
            (col in df.columns) and df[col].notna().any()
            for col in ('OC1', 'OC2', 'OC3', 'OC4')
        )
        assert per_peak_any, (
            "RTCalc802 fixture should produce non-empty per-peak columns "
            f"(OC1-OC4). Got non-null counts: "
            f"{[(c, df[c].notna().sum() if c in df.columns else 'missing') for c in ('OC1','OC2','OC3','OC4')]}"
        )

    def test_rtcalc705_schema_uniform_with_nan_per_peak(self, data_path, date_range, temp_output_dir):
        """RTCalc705 fixture lacks `OCPk*-ug C` source columns, but the
        output schema must still expose OC1..OC4 (all-NaN) so downstream
        consumers see one shape regardless of firmware."""
        legacy_path = data_path / 'legacy_rtcalc705'
        if not legacy_path.exists():
            pytest.skip('OCEC legacy_rtcalc705 fixture not available')

        df = self.read_data(legacy_path, date_range)
        for col in ('OC1', 'OC2', 'OC3', 'OC4'):
            assert col in df.columns, (
                f"{col} should still appear in the output frame even when "
                f"RTCalc705 input lacks the source `OCPk{col[2]}-ug C` column"
            )
            assert df[col].isna().all(), (
                f"{col} should be all-NaN on RTCalc705 (no per-peak source); "
                f"got {df[col].notna().sum()} non-null values"
            )

    def test_firmware_detection_logged(self, data_path, date_range, temp_output_dir, caplog):
        """Reader emits a debug-level message naming which firmware variant
        produced the file. Helps triage mixed-firmware batches without
        spelunking individual CSVs. Bypasses the shared reader cache (which
        would short-circuit a repeat read and emit no log).
        """
        import logging
        from AeroViz import RawDataReader

        normal_path = data_path / 'normal'
        if not normal_path.exists():
            pytest.skip('OCEC normal fixture not available')

        with caplog.at_level(logging.DEBUG, logger='OCEC'):
            RawDataReader(
                'OCEC', normal_path,
                start=self.DATE_RANGE_START, end=self.DATE_RANGE_END,
                reset=True, mean_freq='1h',
                save_pkl=False, save_intermediate_csv=False, save_report=False,
                quiet=True, log_level='DEBUG',
            )

        msgs = [r.getMessage() for r in caplog.records if r.name == 'OCEC']
        assert any('RTCalc802+' in m for m in msgs), (
            f"Expected RTCalc802+ firmware detection log, got: {msgs[-5:]}"
        )

    def test_metadata_alias_maps_split(self):
        """Both firmware alias maps are present as class attrs and converge
        on the same short canonical names. The shared map covers Sample_Volume
        + per-peak source columns."""
        from AeroViz.rawDataReader.script.OCEC import Reader
        for attr in ('METADATA_ALIASES_RTCALC705',
                     'METADATA_ALIASES_RTCALC802',
                     'METADATA_ALIASES_SHARED'):
            assert getattr(Reader, attr), f"{attr} missing or empty"

        # No key overlap between the firmware-specific maps (would collide).
        overlap = set(Reader.METADATA_ALIASES_RTCALC705) & set(Reader.METADATA_ALIASES_RTCALC802)
        assert not overlap, f"RTCalc705 and RTCalc802 alias maps share keys: {overlap}"

        # Both firmware maps target the same canonical short-name vocabulary.
        canonical_705 = set(Reader.METADATA_ALIASES_RTCALC705.values())
        canonical_802 = set(Reader.METADATA_ALIASES_RTCALC802.values())
        assert canonical_705 == canonical_802, (
            f"Firmware alias maps target different canonical names: "
            f"705-only={canonical_705 - canonical_802}, 802-only={canonical_802 - canonical_705}"
        )
