"""
Tests for APS (Aerodynamic Particle Sizer) reader.

Test Scenarios:
- normal/: Standard APS export files
- multi_header/: Files with multiple concatenated headers
- status_errors/: Files with non-zero status flags
"""
from datetime import datetime

import pandas as pd
import pytest

from .base import BaseReaderTest


@pytest.mark.aps
class TestAPSReader(BaseReaderTest):
    """Test APS reader functionality."""

    INSTRUMENT = 'APS'
    STATUS_COLUMN = 'Status Flags'

    # APS normal is a single day in Nov 2025; status_errors spans Apr–Jun
    # 2025. Tight ranges per scenario keep each reindexed pickle small.
    DATE_RANGE_START = datetime(2025, 11, 1)   # default = "normal" scenario
    DATE_RANGE_END = datetime(2025, 11, 30, 23, 59, 59)

    SCENARIO_DATE_RANGES = {
        'status_errors': {
            'start': datetime(2025, 4, 1),
            'end': datetime(2025, 6, 30, 23, 59, 59),
        },
    }

    # The reader returns the dN/dlogDp size distribution (diameters in µm as
    # float columns); summary statistics are derived on demand via psd_stats().
    EXPECTED_COLUMNS = None

    def test_returns_size_distribution(self, data_path, date_range, temp_output_dir):
        """Reader returns dN/dlogDp with float-diameter columns (no stats baked in)."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)

        assert len(df.columns) > 0
        # Every column is a numeric particle diameter (µm)
        assert all(isinstance(c, (int, float)) for c in df.columns), \
            f"Expected float-diameter columns, got {list(df.columns[:5])}"
        # Statistics are no longer baked into the reader output
        assert 'total_num_all' not in df.columns

    def test_statistics_via_psd_stats(self, data_path, date_range, temp_output_dir):
        """psd_stats() derives the size-distribution statistics from the reader output."""
        from AeroViz import psd_stats

        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        df = self.read_data(normal_path, date_range)
        stats = psd_stats(df, unit='um')['other']

        assert any('total_num' in str(c) for c in stats.columns), "total_num stat not found"

    def test_output_files_written(self, data_path, date_range, temp_output_dir):
        """Reader writes N/S/V distribution files + a statistics sidecar."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        self.read_data(normal_path, date_range)

        out = normal_path / 'aps_outputs'
        for name in ('output_aps_dNdlogDp.csv', 'output_aps_dSdlogDp.csv',
                     'output_aps_dVdlogDp.csv', 'output_aps_stats.csv'):
            assert (out / name).exists(), f"{name} not written"

    def test_append_stats(self, data_path, date_range, temp_output_dir):
        """append_stats=True appends stat columns; default keeps a clean PSD matrix."""
        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        clean = self.read_data(normal_path, date_range)
        fat = self.read_data(normal_path, date_range, append_stats=True)

        assert all(isinstance(c, (int, float)) for c in clean.columns)
        assert any(isinstance(c, (int, float)) for c in fat.columns)
        assert any(isinstance(c, str) and 'total_num' in c for c in fat.columns)

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

    def test_date_format_logged(self, data_path, date_range, temp_output_dir, caplog):
        """Reader emits a debug-level message naming which DATE_FORMATS entry
        matched the file. A future firmware that introduces a third format
        will surface a warning instead of silently producing empty data.

        Bypasses the shared reader cache so the log actually emits.
        """
        import logging
        from AeroViz import RawDataReader
        from AeroViz.rawDataReader.script.APS import Reader

        normal_path = data_path / 'normal'
        if not normal_path.exists():
            normal_path = data_path

        with caplog.at_level(logging.DEBUG, logger='APS'):
            RawDataReader(
                'APS', normal_path,
                start=self.DATE_RANGE_START, end=self.DATE_RANGE_END,
                reset=True, mean_freq='1h',
                save_pkl=False, save_intermediate_csv=False, save_report=False,
                quiet=True, log_level='DEBUG',
            )

        msgs = [r.getMessage() for r in caplog.records if r.name == 'APS']
        assert any('parsed dates using format' in m for m in msgs), (
            f"Expected date-format detection log, got: {msgs[-5:]}"
        )
        # The matched format string is one of the documented DATE_FORMATS.
        assert any(any(fmt in m for fmt in Reader.DATE_FORMATS) for m in msgs)

    def test_expected_bin_grid_constant(self):
        """`EXPECTED_BIN_GRID` is documented and matches the TSI 3321/3320
        factory grid. If a real fixture drifts, this constant — not the test
        — is the right place to update."""
        from AeroViz.rawDataReader.script.APS import Reader
        assert isinstance(Reader.EXPECTED_BIN_GRID, tuple)
        assert len(Reader.EXPECTED_BIN_GRID) == 3
        grid_min, grid_max, grid_n = Reader.EXPECTED_BIN_GRID
        assert 0.5 <= grid_min < grid_max <= 20
        assert grid_n > 0

    def test_bin_grid_drift_warning(self, caplog):
        """Drifted bin grid triggers a loud warning (early tripwire for the
        SMPS-style NaN-poison concat bug if APS firmware ever changes)."""
        import logging
        import tempfile
        from pathlib import Path
        from AeroViz import RawDataReader

        # Take the normal fixture and rewrite one bin endpoint to simulate drift.
        normal_dir = Path('tests/fixtures/raw_data/APS/normal')
        normal_files = [p for p in normal_dir.iterdir() if p.suffix.lower() == '.txt']
        if not normal_files:
            pytest.skip('No APS normal fixture available')
        src = normal_files[0]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_dir = Path(tmpdir)
            dst = tmp_dir / src.name
            text = src.read_text(encoding='utf-8', errors='ignore')
            # Replace the canonical '0.542' bin with a clearly drifted value.
            # The synthetic file becomes invalid TSI output but exercises the warn path.
            assert '\t0.542\t' in text, "fixture sanity: expected 0.542 column"
            drifted = text.replace('\t0.542\t', '\t0.999\t', 1)
            dst.write_text(drifted, encoding='utf-8')

            with caplog.at_level(logging.WARNING, logger='APS'):
                RawDataReader(
                    'APS', tmp_dir,
                    start=self.DATE_RANGE_START, end=self.DATE_RANGE_END,
                    reset=True, mean_freq='1h',
                    save_pkl=False, save_intermediate_csv=False, save_report=False,
                    quiet=True, log_level='WARNING',
                )

        msgs = [r.getMessage() for r in caplog.records if r.name == 'APS']
        assert any('bin grid deviates from expected' in m for m in msgs), (
            f"Drifted bin endpoint should trigger warning. Got: {msgs}"
        )
