"""SMPS size-channel lattice and per-period time grids.

Regression for 2026-11-20, FS station: the SMPS was set up again under AIM
11.5 (CSV, 11.34-615.27 nm printed with two decimals, 5-minute scans) into a
folder that already held the year's AIM 10.3 exports (TXT, 11.8-593.5 nm, one
decimal, 6-minute scans). The reader treated the two headers as different
grids, kept the larger group and skipped the new file whole — the station's
live data went out as timestamps with no values. They are the same physical
channels: both sit on TSI's 64-channel/decade lattice.

The `mixed_aim` fixture is that folder: one AIM 10.3 file and the AIM 11.5
file from the same afternoon.
"""
import shutil
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from AeroViz import RawDataReader
from AeroViz.rawDataReader.core.size_grid import (
    channel_index, channel_label, channel_midpoint, lattice_channels)

pytestmark = pytest.mark.smps

#: The AIM 10.3 header every TCLab long-DMA export since 2018 carries.
AIM103_LABELS = [
    11.8, 12.2, 12.6, 13.1, 13.6, 14.1, 14.6, 15.1, 15.7, 16.3,
    16.8, 17.5, 18.1, 18.8, 19.5, 20.2, 20.9, 21.7, 22.5, 23.3,
    24.1, 25.0, 25.9, 26.9, 27.9, 28.9, 30.0, 31.1, 32.2, 33.4,
    34.6, 35.9, 37.2, 38.5, 40.0, 41.4, 42.9, 44.5, 46.1, 47.8,
    49.6, 51.4, 53.3, 55.2, 57.3, 59.4, 61.5, 63.8, 66.1, 68.5,
    71.0, 73.7, 76.4, 79.1, 82.0, 85.1, 88.2, 91.4, 94.7, 98.2,
    101.8, 105.5, 109.4, 113.4, 117.6, 121.9, 126.3, 131.0, 135.8, 140.7,
    145.9, 151.2, 156.8, 162.5, 168.5, 174.7, 181.1, 187.7, 194.6, 201.7,
    209.1, 216.7, 224.7, 232.9, 241.4, 250.3, 259.5, 269.0, 278.8, 289.0,
    299.6, 310.6, 322.0, 333.8, 346.0, 358.7, 371.8, 385.4, 399.5, 414.2,
    429.4, 445.1, 461.4, 478.3, 495.8, 514.0, 532.8, 552.3, 572.5, 593.5,
]


class TestLattice:
    def test_canonical_labels_reproduce_the_aim103_header(self):
        """Channels 68..177 label exactly as AIM 10.3 prints them — so
        relabelling a decade of existing exports changes nothing."""
        assert [channel_label(k) for k in range(68, 178)] == AIM103_LABELS

    def test_below_10nm_labels_keep_two_decimals(self):
        # nano-DMA header starts 2.02; long-DMA wide scans start 9.82
        assert channel_label(channel_index(2.02)) == 2.02
        assert channel_label(channel_index(9.82)) == 9.82

    @pytest.mark.parametrize('printed, canonical', [
        (11.76, 11.8),     # AIM 11.x two-decimal label -> AIM 10.3 label
        (16.85, 16.8),     # round(16.85, 1) would give 16.9 (or 16.8 by float luck)
        (572.55, 572.5),
        (11.34, 11.3),     # one channel below the AIM 10.3 window
        (615.27, 615.3),   # one channel above it
    ])
    def test_aim11_labels_map_to_the_same_channel(self, printed, canonical):
        assert channel_label(channel_index(printed)) == canonical

    def test_printed_label_and_channel_midpoint_agree(self):
        for label in AIM103_LABELS:
            exact = channel_midpoint(channel_index(label))
            assert abs(exact - label) / label < 0.005

    def test_off_lattice_grid_is_rejected(self):
        # 32 channels/decade read as if it were 64: every other midpoint
        # falls on a channel edge.
        coarse = [10 ** ((k + 0.5) / 32) for k in range(30, 60)]
        assert lattice_channels(coarse) is None
        assert lattice_channels([11.8, 11.81]) is None       # two in one channel
        assert lattice_channels([0.0, 11.8]) is None


@pytest.fixture
def mixed_folder(raw_data_path, tmp_path):
    """A private copy, so the read's outputs do not land in the fixtures."""
    src = raw_data_path / 'SMPS' / 'mixed_aim'
    if not src.exists():
        pytest.skip('SMPS mixed_aim test data not available')
    dst = tmp_path / 'FS_SMPS'
    dst.mkdir()
    for f in src.iterdir():
        if f.is_file():
            shutil.copy(f, dst / f.name)
    return dst


def _read(folder, **kwargs):
    kwargs.setdefault('reset', True)
    return RawDataReader('SMPS', folder, start=datetime(2026, 11, 20, 12),
                         end=datetime(2026, 11, 20, 18), **kwargs)


def _bins(df):
    return [c for c in df.columns if isinstance(c, float)]


class TestMixedAimFolder:
    def test_both_versions_are_read(self, mixed_folder):
        df = _read(mixed_folder)
        have_data = df[_bins(df)].notna().any(axis=1)
        assert have_data[:'2026-11-20 16:00'].sum() > 0, 'AIM 10.3 scans missing'
        assert have_data['2026-11-20 16:20':].sum() == 8, 'AIM 11.5 scans missing'

    def test_columns_are_the_union_under_canonical_labels(self, mixed_folder):
        bins = _bins(_read(mixed_folder))
        assert bins == [11.3] + AIM103_LABELS + [615.3]

    def test_values_are_not_interpolated(self, mixed_folder):
        """Aligning to the lattice renames columns; it must not touch a value."""
        df = _read(mixed_folder, qc=False)
        raw = pd.read_csv(mixed_folder / 'SMPS_3082002344002_20261120_162114.csv',
                          skiprows=_header_row(mixed_folder), encoding='utf-8')
        first = raw.iloc[0]
        row = df.loc['2026-11-20 16:25:00']
        for printed, canonical in [('11.34', 11.3), ('11.76', 11.8), ('16.85', 16.8),
                                   ('593.52', 593.5), ('615.27', 615.3)]:
            assert row[canonical] == pytest.approx(float(first[printed]))

    def test_channels_a_period_did_not_measure_stay_nan(self, mixed_folder):
        df = _read(mixed_folder)
        old = df[:'2026-11-20 16:00']
        measured = old[old[11.8].notna()]
        assert len(measured) and measured[[11.3, 615.3]].isna().all().all()

    def test_each_period_keeps_its_own_time_grid(self, mixed_folder):
        df = _read(mixed_folder)
        assert df.attrs['freq_mixed'] is True
        schedule = df.attrs['freq_schedule']
        assert [freq for _, freq in schedule] == ['6min', '5min']
        new = df['2026-11-20 16:25':'2026-11-20 17:00']
        assert (new.index.minute % 5 == 0).all()
        assert new[11.8].notna().sum() == 8            # every scan in its own slot
        assert not df.index.duplicated().any() and df.index.is_monotonic_increasing

    def test_nothing_is_skipped(self, mixed_folder):
        _read(mixed_folder)
        log = (mixed_folder / 'smps_outputs' / 'SMPS.log').read_text(encoding='utf-8')
        assert 'skipping' not in log
        assert 'different size ranges on the same channel lattice' in log

    def test_schedule_survives_the_pickle_cache(self, mixed_folder):
        fresh = _read(mixed_folder)
        cached = _read(mixed_folder, reset=False)
        assert cached.attrs['freq_schedule'] == fresh.attrs['freq_schedule']
        pd.testing.assert_index_equal(cached.index, fresh.index)

    def test_raw_freq_still_forces_a_single_grid(self, mixed_folder):
        df = _read(mixed_folder, raw_freq='6min')
        assert df.attrs['freq_schedule'] is None
        assert (df.index.minute % 6 == 0).all()

    def test_size_range_accepts_the_printed_diameters(self, mixed_folder):
        """`size_range` is given as AIM printed it; only the file whose window
        matches is kept."""
        df = _read(mixed_folder, size_range=(11.34, 615.27))
        assert df[_bins(df)].notna().any(axis=1).sum() == 8


def _header_row(folder):
    with open(folder / 'SMPS_3082002344002_20261120_162114.csv', encoding='utf-8') as fh:
        for i, line in enumerate(fh):
            if line.startswith('Scan Number'):
                return i
    raise AssertionError('no header row')


def test_128_channels_per_decade_is_not_the_64_lattice():
    """Midpoints of a 128-channel grid sit a quarter channel off the 64 one."""
    fine = [10 ** ((k + 0.5) / 128) for k in range(136, 362)]
    assert lattice_channels(fine) is None


class TestNarrowerWindowIsSkipped:
    """A lattice file that does not span the record's window is a different
    measurement and stays out — by name, not silently."""

    @staticmethod
    def _frame(labels, start, on_lattice=True, rows=20):
        df = pd.DataFrame({float(c): np.arange(rows, dtype=float) for c in labels},
                          index=pd.date_range(start, periods=rows, freq='6min'))
        df.attrs['smps_on_lattice'] = on_lattice
        return df

    @staticmethod
    def _reader(tmp_path, **kwargs):
        from AeroViz.rawDataReader.core.logger import ReaderLogger
        from AeroViz.rawDataReader.script.SMPS import Reader
        reader = Reader.__new__(Reader)
        reader.logger = ReaderLogger('test', tmp_path, quiet=True)
        reader.kwargs = kwargs
        return reader

    def test_wider_kept_narrower_dropped(self, tmp_path):
        from pathlib import Path
        std = self._frame(AIM103_LABELS, '2026-01-01', rows=200)
        wide = self._frame([11.3] + AIM103_LABELS + [615.3], '2026-02-01')
        nano = self._frame([channel_label(k) for k in range(31, 130)], '2026-01-01')   # 3.11-105.5
        short = self._frame(AIM103_LABELS[3:], '2026-03-01')                           # starts 13.1
        files = [Path(n) for n in ('std.TXT', 'wide.csv', 'nano.txt', 'short.TXT')]

        reader = self._reader(tmp_path)
        kept = reader._partition_compatible_scans([std, wide, nano, short], files)

        assert [id(df) for df in kept] == [id(std), id(wide)]
        assert reader._reference_window == (11.8, 593.5)

    def test_reference_stays_standard_when_the_wide_window_dominates(self, tmp_path):
        """A year that is mostly AIM 11.x must not turn its AIM 10.3 files
        into the odd ones out."""
        from pathlib import Path
        std = self._frame(AIM103_LABELS, '2026-01-01', rows=20)
        wide = self._frame([11.3] + AIM103_LABELS + [615.3], '2026-02-01', rows=500)
        reader = self._reader(tmp_path)
        kept = reader._partition_compatible_scans([std, wide], [Path('a.TXT'), Path('b.csv')])
        assert len(kept) == 2 and reader._reference_window == (11.8, 593.5)

    def test_an_archive_on_another_range_is_its_own_reference(self, tmp_path):
        from pathlib import Path
        old_range = [channel_label(k) for k in range(81, 190)]            # 18.8-914
        a = self._frame(old_range, '2017-09-11', rows=200)
        b = self._frame(old_range[5:], '2017-09-12')
        reader = self._reader(tmp_path)
        kept = reader._partition_compatible_scans([a, b], [Path('a.txt'), Path('b.txt')])
        assert [id(df) for df in kept] == [id(a)]
        assert reader._reference_window == (18.8, 914.0)
