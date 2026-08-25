"""Decoding a bitwise status register into named conditions.

`Status Error` says a bit was set; it cannot say which, because the QC verdict
is a boolean. These tests pin the layer that turns "Status Error 8.3%" into
"Ambient RH & Temp sensor 8.3%".
"""
import pandas as pd
import pytest

from AeroViz.rawDataReader.script.TEOM import Reader as TEOMReader


def decode(status_values, column='status'):
    """Run the decoder against a hand-built frame, no file IO involved."""
    reader = TEOMReader.__new__(TEOMReader)
    df = pd.DataFrame({column: status_values})
    return TEOMReader._status_condition_rows(reader, df)


class TestTEOMStatusBits:
    def test_single_bit_is_named(self):
        rows = decode([8, 8, 0, 0])
        assert rows == [{'code': 8, 'name': 'Ambient RH & Temp sensor',
                         'count': 2, 'percentage': 50.0}]

    def test_or_summed_value_reports_every_condition(self):
        """24 = 8 | 16 — the register is a sum, so both conditions fired."""
        names = {row['name'] for row in decode([24])}
        assert names == {'Ambient RH & Temp sensor', 'Bypass Flow (>10% deviation)'}

    def test_sorted_by_how_often_it_fired(self):
        rows = decode([8, 8, 8, 16])
        assert [row['code'] for row in rows] == [8, 16]

    def test_zero_status_is_no_conditions(self):
        assert decode([0, 0, 0]) == []

    def test_missing_column_is_no_opinion(self):
        """Not the same as "nothing fired" — we simply cannot tell."""
        assert decode([8], column='something_else') is None

    def test_non_numeric_status_does_not_raise(self):
        rows = decode(['', 'n/a', 8])
        assert rows == [{'code': 8, 'name': 'Ambient RH & Temp sensor',
                         'count': 1, 'percentage': pytest.approx(33.3)}]

    def test_high_bits_survive_int64(self):
        """The register is 32-bit; bit 30 must not overflow or get truncated."""
        rows = decode([1 << 30])
        assert rows[0]['name'] == '%RH High Side A (>=98%)'


class TestTableIntegrity:
    def test_no_duplicate_bit_or_name(self):
        """The prose table this came from listed Enclosure Temp as "bit 2",
        which is Database's bit — encoding that would have fused two conditions."""
        bits = TEOMReader.STATUS_BITS
        assert len(set(bits.values())) == len(bits)
        assert bits[2] == 'Enclosure Temp (>60C)'
        assert bits[4] == 'Database (log failure)'

    def test_every_key_is_a_single_bit(self):
        for value in TEOMReader.STATUS_BITS:
            assert value & (value - 1) == 0, f'{value} is not a single bit'


class TestReadersWithoutATable:
    def test_absent_table_means_no_rows(self):
        """A reader whose manual has not been transcribed says nothing rather
        than guessing — a partial map reads as "that condition never fired"."""
        from AeroViz.rawDataReader.script.OCEC import Reader as OCECReader
        reader = OCECReader.__new__(OCECReader)
        df = pd.DataFrame({'Status': [8]})
        assert OCECReader._status_condition_rows(reader, df) is None
