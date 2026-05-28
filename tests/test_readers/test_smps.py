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

    # The 'normal' fixture file (20250219.TXT) was captured with the TSI in
    # a known-noisy operating mode — every scan carries
    # 'Low aerosol flow,Neutralizer not active' in `Instrument Errors`. Our
    # SMPS QC now reads that column (`SECONDARY_STATUS_COLUMN`), so without a
    # whitelist every QC-running test would reject 100% of rows and assertions
    # against derived statistics / output frames would fail spuriously.
    NORMAL_FIXTURE_IGNORE = ['Low aerosol flow', 'Neutralizer not active']

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

        clean = self.read_data(normal_path, date_range, ignored_status_errors=self.NORMAL_FIXTURE_IGNORE)
        fat = self.read_data(normal_path, date_range, append_stats=True,
                             ignored_status_errors=self.NORMAL_FIXTURE_IGNORE)

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

    def test_partition_compatible_scans(self):
        """`_partition_compatible_scans` keeps the dominant grid and drops
        files on a different size-bin grid, so the concat downstream sees one
        consistent schema.

        Mixing AIM 10.3 (.TXT, bins 11.8/13.6/593.5) with AIM 11.x (.CSV,
        bins 11.34/13.10/615.27) in one folder is the failure mode this fix
        targets. The dominant group is picked by total row count, not file
        count, so a single large TXT export beats a swarm of tiny CSVs.
        """
        import pandas as pd
        from pathlib import Path
        from AeroViz.rawDataReader.script.SMPS import Reader

        # 3 AIM 10.3 .TXT files (50 rows each = 150 rows) + 3 AIM 11.x .CSV
        # files (10 rows each = 30 rows). TXT dominates by row count.
        txt_files = [Path(f"260{i:02d}.TXT") for i in (1, 2, 3)]
        csv_files = [Path(f"SMPS_3082001426002_2026020{i}.csv") for i in (5, 6, 7)]
        txt_dfs = [
            pd.DataFrame({11.8: range(50), 13.6: range(50), 593.5: range(50)},
                         index=pd.date_range(f'2026-01-0{i}', periods=50, freq='6min'))
            for i in (1, 2, 3)
        ]
        csv_dfs = [
            pd.DataFrame({11.34: range(10), 13.10: range(10), 615.27: range(10)},
                         index=pd.date_range(f'2026-02-0{i}', periods=10, freq='6min'))
            for i in (5, 6, 7)
        ]
        files = txt_files + csv_files
        df_list = txt_dfs + csv_dfs

        # Instance method but uses only `self.logger` and the static
        # `_bin_signature` — no real `__init__` needed.
        reader = Reader.__new__(Reader)
        import logging
        reader.logger = logging.getLogger('test')

        kept = reader._partition_compatible_scans(df_list, files)

        # Only the 3 TXT frames survive; the 3 CSVs were dropped.
        assert len(kept) == 3, f"Expected 3 TXT frames kept, got {len(kept)}"
        all_kept_bins = set()
        for df in kept:
            all_kept_bins.update(c for c in df.columns if isinstance(c, (int, float)))
        assert all_kept_bins == {11.8, 13.6, 593.5}, (
            f"Expected dominant TXT bin grid {{11.8, 13.6, 593.5}}, got {all_kept_bins}"
        )

    def test_filter_error_status_ignored_values_token_split(self):
        """`ignored_values` whitelists comma-separated tokens. A row passes
        only when EVERY token is either the OK value or in the whitelist.

        Verified at the QC primitive level (`filter_error_status`) because
        the higher-level reader path is hard to invoke without raw files;
        once this is correct, the SMPS reader change is just plumbing.
        """
        import pandas as pd
        from AeroViz.rawDataReader.core.qc import QualityControl

        # Build a status column covering realistic TP_SMPS shapes plus the
        # three empty sentinels ('', 'nan', 'None') — the last enters the
        # column post-concat when a file lacked that column and pandas filled
        # with Python None, which `astype(str)` turns into 'None'.
        statuses = [
            'Normal Scan',                                    # ok
            'Low aerosol flow',                               # ignored-only
            'Low aerosol flow,Neutralizer not active',        # both ignored
            'Low aerosol flow,Sheath flow error',             # one token NOT ignored
            'Sheath flow error',                              # NOT in whitelist
            '',                                               # empty -> never an error
            'nan',                                            # NaN stringified -> never an error
            'None',                                           # Python None stringified -> never an error
        ]
        df = pd.DataFrame({'Status Flag': statuses})

        # Without a whitelist: only 'Normal Scan' and the three empty
        # sentinels pass.
        no_whitelist = QualityControl.filter_error_status(
            df, status_column='Status Flag', status_type='text', ok_value='Normal Scan')
        assert list(no_whitelist) == [False, True, True, True, True, False, False, False]

        # With whitelist ['Low aerosol flow', 'Neutralizer not active']: the
        # first three rows pass; combined statuses containing an un-whitelisted
        # token still fail.
        whitelisted = QualityControl.filter_error_status(
            df, status_column='Status Flag', status_type='text', ok_value='Normal Scan',
            ignored_values=['Low aerosol flow', 'Neutralizer not active'])
        assert list(whitelisted) == [False, False, False, True, True, False, False, False]

    def test_metadata_aliases_aim10_canonical(self, data_path, date_range, temp_output_dir):
        """Reading an AIM 11.x .csv file should emit AIM 10.3 metadata column
        names, so downstream consumers see one schema regardless of which host
        software produced the file. AIM 11.x columns with no 10.3 equivalent
        (4-way error split, granular DMA timings) are kept under their 11.x
        names because collapsing them would lose information.
        """
        import shutil
        import pandas as pd
        from AeroViz import RawDataReader

        csv_path = data_path / 'csv_format'
        if not csv_path.exists():
            pytest.skip('SMPS csv_format test data not available')

        # Bypass the session-scoped reader cache (see base.py:_cached_reader_call)
        # — we need the on-disk raw pkl, and a cache hit would skip writing it.
        out = csv_path / 'smps_outputs'
        if out.exists():
            shutil.rmtree(out)
        scenario = self.SCENARIO_DATE_RANGES.get('csv_format', date_range)
        RawDataReader(
            'SMPS', csv_path,
            start=scenario['start'], end=scenario['end'],
            reset=True, mean_freq='1h', size_range=(11.34, 615.27),
            save_pkl=True, save_intermediate_csv=False, save_report=False,
            quiet=True, log_level='ERROR',
        )

        raw_pkl = out / '_read_smps_raw.pkl'
        assert raw_pkl.exists()
        raw = pd.read_pickle(raw_pkl)
        cols = set(raw.columns)

        # Canonical (AIM 10.3) names must be present after rename.
        assert 'Sample Temp (C)' in cols
        assert 'Relative Humidity (%)' in cols
        assert 'Density (g/cm)' in cols
        assert 'Total Conc. (#/cm)' in cols
        assert 'D50 (nm)' in cols
        assert 'Title' in cols

        # AIM 11.x original names must NOT survive the rename.
        for old in (
            'Aerosol Temperature (C)', 'Aerosol Humidity (%)',
            'Aerosol Density (g/cm³)', 'Total Concentration (#/cm³)',
            'Impactor D50 (nm)', 'Test Name',
        ):
            assert old not in cols, f"AIM 11.x column {old!r} should have been renamed"

        # AIM 11.x-only metadata (no 10.3 equivalent) is intentionally preserved.
        for kept in ('Classifier Errors', 'Detector Status', 'Sheath Pressure (kPa)'):
            assert kept in cols, f"AIM 11.x-unique column {kept!r} should be kept"

    def test_partition_compatible_scans_homogeneous_noop(self):
        """When every file has the same bin grid, `_partition_compatible_scans`
        is a no-op — neither dropping any frame nor emitting a warning."""
        import pandas as pd
        from pathlib import Path
        from AeroViz.rawDataReader.script.SMPS import Reader

        files = [Path(f"f{i}.TXT") for i in range(4)]
        df_list = [
            pd.DataFrame({11.8: range(10), 13.6: range(10)},
                         index=pd.date_range(f'2026-01-0{i+1}', periods=10, freq='6min'))
            for i in range(4)
        ]
        reader = Reader.__new__(Reader)
        import logging
        reader.logger = logging.getLogger('test')

        kept = reader._partition_compatible_scans(df_list, files)
        assert kept is df_list  # same object, no copy, no drops
