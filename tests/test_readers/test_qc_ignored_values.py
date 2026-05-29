"""
Tests for the `ignored_values` whitelist in `QualityControl.filter_error_status`.

The whitelist lets callers suppress operator-known benign statuses without
rewriting raw files. It is supported in all four status modes, each with a
mode-appropriate interpretation:

- text          : comma-split string tokens (SMPS)
- numeric       : numeric status codes (TEOM / Aurora / NEPH)
- bitwise       : integer error codes/bits (AE33 / AE43 / BC1054 / MA350)
- binary_string : integer bit masks (APS)

Backward-compatibility: with ``ignored_values=None`` every mode must behave
exactly as before, and a whitelist meant for one mode (e.g. string tokens) must
be a harmless no-op when it reaches another (e.g. a bitwise instrument).
"""
import pandas as pd
import pytest

from AeroViz.rawDataReader.core.qc import QualityControl

filter_error_status = QualityControl.filter_error_status


def _df(status_col, values):
    return pd.DataFrame({status_col: values})


# --------------------------------------------------------------------------- #
# text mode (SMPS)
# --------------------------------------------------------------------------- #
class TestTextMode:
    VALUES = ['Normal Scan', 'Low aerosol flow',
              'Low aerosol flow,Neutralizer not active',
              'Sheath flow error', '', 'None', 'nan']

    def test_no_whitelist(self):
        mask = filter_error_status(_df('S', self.VALUES), status_column='S',
                                   status_type='text', ok_value='Normal Scan')
        # OK value + empty sentinels pass; every non-empty non-OK token errors.
        assert mask.tolist() == [False, True, True, True, False, False, False]

    def test_whitelist_tokens(self):
        mask = filter_error_status(
            _df('S', self.VALUES), status_column='S', status_type='text',
            ok_value='Normal Scan',
            ignored_values=['Low aerosol flow', 'Neutralizer not active'])
        # Both benign tokens (alone or comma-combined) now pass; the genuine
        # 'Sheath flow error' still errors.
        assert mask.tolist() == [False, False, False, True, False, False, False]


# --------------------------------------------------------------------------- #
# numeric mode (TEOM / Aurora / NEPH)
# --------------------------------------------------------------------------- #
class TestNumericMode:
    VALUES = [0, 1, 4, 16]

    def test_no_whitelist(self):
        mask = filter_error_status(_df('status', self.VALUES), status_column='status',
                                   status_type='numeric', ok_value=0)
        assert mask.tolist() == [False, True, True, True]

    def test_whitelist_codes(self):
        mask = filter_error_status(_df('status', self.VALUES), status_column='status',
                                   status_type='numeric', ok_value=0,
                                   ignored_values=[4, 16])
        # 4 and 16 now treated as OK; 1 still an error.
        assert mask.tolist() == [False, True, False, False]

    def test_string_whitelist_is_noop(self):
        # A text whitelist reaching a numeric instrument must not crash and must
        # behave as if no whitelist was given.
        mask = filter_error_status(_df('status', self.VALUES), status_column='status',
                                   status_type='numeric', ok_value=0,
                                   ignored_values=['Low aerosol flow'])
        assert mask.tolist() == [False, True, True, True]


# --------------------------------------------------------------------------- #
# bitwise mode (AE33 / AE43 / BC1054 / MA350)
# --------------------------------------------------------------------------- #
class TestBitwiseMode:
    ERROR_CODES = [1, 2, 4]
    # 0 = OK, 4 = flow bit only, 6 = flow(4)+first-meas(2), 1 = tape advance
    VALUES = [0, 4, 6, 1]

    def test_no_whitelist(self):
        mask = filter_error_status(_df('Status', self.VALUES), self.ERROR_CODES,
                                   status_column='Status', status_type='bitwise')
        assert mask.tolist() == [False, True, True, True]

    def test_whitelist_drops_one_bit(self):
        mask = filter_error_status(_df('Status', self.VALUES), self.ERROR_CODES,
                                   status_column='Status', status_type='bitwise',
                                   ignored_values=[4])
        # 4 (only flow bit) passes; 6 still errors (bit 2 not whitelisted);
        # 1 still errors.
        assert mask.tolist() == [False, False, True, True]

    def test_special_codes_whitelisted(self):
        # special_codes use exact match; whitelisting one removes it.
        df = _df('Status', [3, 99])
        mask = filter_error_status(df, error_codes=None, special_codes=[3, 99],
                                   status_column='Status', status_type='bitwise',
                                   ignored_values=[99])
        assert mask.tolist() == [True, False]


# --------------------------------------------------------------------------- #
# binary_string mode (APS)
# --------------------------------------------------------------------------- #
class TestBinaryStringMode:
    # 0, bit0 (=1), bit1 (=2), bit0+bit1 (=3)
    VALUES = ['0000 0000 0000 0000', '0000 0000 0000 0001',
              '0000 0000 0000 0010', '0000 0000 0000 0011']

    def test_no_whitelist(self):
        mask = filter_error_status(_df('Status Flags', self.VALUES),
                                   status_column='Status Flags', status_type='binary_string')
        assert mask.tolist() == [False, True, True, True]

    def test_whitelist_clears_bit(self):
        mask = filter_error_status(_df('Status Flags', self.VALUES),
                                   status_column='Status Flags', status_type='binary_string',
                                   ignored_values=[1])
        # bit0 cleared: '...0001' passes; '...0010' (bit1) still errors;
        # '...0011' still errors (bit1 remains).
        assert mask.tolist() == [False, False, True, True]


def test_missing_status_column_returns_all_false():
    df = _df('S', ['Normal Scan'])
    mask = filter_error_status(df, status_column='NOPE', status_type='text',
                               ok_value='Normal Scan', ignored_values=['x'])
    assert mask.tolist() == [False]
