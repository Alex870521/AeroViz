"""Decoding a bitwise status register into named conditions.

`Status Error` says a bit was set; it cannot say which, because the QC verdict
is a boolean. These tests pin the layer that turns "Status Error 8.3%" into
"Ambient RH & Temp sensor 8.3%".
"""
import pathlib

import pandas as pd
import pytest

from AeroViz.rawDataReader.script.AE33 import Reader as AE33Reader
from AeroViz.rawDataReader.script.AE43 import Reader as AE43Reader
from AeroViz.rawDataReader.script.APS import Reader as APSReader
from AeroViz.rawDataReader.script.BC1054 import Reader as BC1054Reader
from AeroViz.rawDataReader.script.MA350 import Reader as MA350Reader
from AeroViz.rawDataReader.script.TEOM import Reader as TEOMReader

#: Every reader that declares a decode table. Kept explicit rather than
#: discovered, so adding a table without a test is a visible omission.
READERS_WITH_TABLES = [AE33Reader, AE43Reader, APSReader, BC1054Reader,
                       MA350Reader, TEOMReader]


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


#: reader → 說明頁。文件與程式各存一份查找表就一定會漂,而**對不上的狀態表比
#: 沒有表更糟:它會讓人去檢查錯的零件**。下面那支測試是唯一擋得住的東西。
DOC_PAGES = {
    AE33Reader: 'docs/api/instruments/aethalometers/AE33.md',
    AE43Reader: 'docs/api/instruments/aethalometers/AE43.md',
    BC1054Reader: 'docs/api/instruments/aethalometers/BC1054.md',
    MA350Reader: 'docs/api/instruments/aethalometers/MA350.md',
    APSReader: 'docs/api/instruments/particle-sizers/APS.md',
    TEOMReader: 'docs/api/instruments/mass/TEOM.md',
}

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def doc_table(reader):
    """Parse the markdown table back out of the reader's page."""
    text = (REPO_ROOT / DOC_PAGES[reader]).read_text()
    start = text.index('#### Status Condition Register')
    end = min(i for i in (text.find('\n## ', start), len(text)) if i > 0)
    rows = {}
    for line in text[start:end].splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) == 3 and cells[1].startswith('`'):
            rows[int(cells[1].strip('`'))] = (int(cells[0]), cells[2])
    return rows


class TestDocsMatchTheTable:
    @pytest.mark.parametrize('reader', READERS_WITH_TABLES, ids=lambda r: r.nam)
    def test_doc_table_is_the_same_table(self, reader):
        published = {decimal: name for decimal, (_, name) in doc_table(reader).items()}
        assert published == reader.STATUS_BITS

    @pytest.mark.parametrize('reader', READERS_WITH_TABLES, ids=lambda r: r.nam)
    def test_bit_column_agrees_with_the_decimal(self, reader):
        rows = doc_table(reader)
        assert rows, f'{reader.nam} page has no table'
        for decimal, (bit, _) in rows.items():
            assert 1 << bit == decimal, f'{reader.nam}: bit {bit} is not {decimal}'


class TestEveryTableIsConsistent:
    """統一的契約:有表的 reader 一律 `STATUS_BITS = {十進位: 名稱}`。

    The shapes used to differ — APS keyed its map by bit *position* and called
    it ERROR_STATES, the same name the aethalometers give a list of codes that
    QC actually consumes. One decoder can only serve them all if the contract
    is the same everywhere.
    """

    @pytest.mark.parametrize('reader', READERS_WITH_TABLES, ids=lambda r: r.nam)
    def test_keys_are_single_bits(self, reader):
        for value in reader.STATUS_BITS:
            assert isinstance(value, int)
            assert value > 0 and value & (value - 1) == 0, \
                f'{reader.nam}: {value} is not a single bit'

    @pytest.mark.parametrize('reader', READERS_WITH_TABLES, ids=lambda r: r.nam)
    def test_names_are_unique_and_nonempty(self, reader):
        names = list(reader.STATUS_BITS.values())
        assert all(isinstance(n, str) and n.strip() for n in names)
        assert len(set(names)) == len(names), f'{reader.nam} has duplicate names'

    @pytest.mark.parametrize('reader', READERS_WITH_TABLES, ids=lambda r: r.nam)
    def test_declares_where_the_register_lives(self, reader):
        assert isinstance(reader.STATUS_COLUMN, str) and reader.STATUS_COLUMN
        assert reader.STATUS_ENCODING in ('int', 'binary_string')

    def test_named_bits_are_error_states(self):
        """命名的 bit 必須是 ERROR_STATES 認得的,否則會出現「有名字但永遠不觸發」。"""
        for reader in (AE33Reader, AE43Reader, BC1054Reader, MA350Reader):
            unknown = set(reader.STATUS_BITS) - set(reader.ERROR_STATES)
            assert not unknown, f'{reader.nam}: {unknown} named but not an error state'

    def test_ae33_and_ae43_agree(self):
        """兩者的 ERROR_STATES 已有測試釘住相等,名稱表也不該漂開。"""
        assert AE33Reader.STATUS_BITS == AE43Reader.STATUS_BITS

    def test_ae33_leaves_the_ambiguous_code_unnamed(self):
        """3 = 1|2,bitwise 下無法和 tape advance / first measurement 區分。"""
        assert 3 in AE33Reader.ERROR_STATES
        assert 3 not in AE33Reader.STATUS_BITS


class TestBinaryStringRegister:
    """APS 的暫存器是空格分組的位元字串,不是數字。"""

    def _decode(self, values):
        reader = APSReader.__new__(APSReader)
        df = pd.DataFrame({APSReader.STATUS_COLUMN: values})
        return APSReader._status_condition_rows(reader, df)

    def test_bit_string_is_parsed_as_bits(self):
        rows = self._decode(['0000 0000 0000 0001'])
        assert rows[0]['name'] == 'Laser fault'

    def test_not_parsed_as_a_decimal_number(self):
        """'0000 0000 0000 0010' 讀成數字是 10,讀成位元是 2 —— 差一個條件。"""
        rows = self._decode(['0000 0000 0000 0010'])
        assert [r['name'] for r in rows] == ['Total Flow out of range']

    def test_clean_register_is_empty_not_none(self):
        assert self._decode(['0000 0000 0000 0000']) == []
