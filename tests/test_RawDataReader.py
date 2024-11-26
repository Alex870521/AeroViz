import unittest
from datetime import datetime
from pathlib import Path

import pytest

from AeroViz import RawDataReader


@pytest.mark.requires_data
class TestRawDataReader(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # 設置基礎路徑
        cls.base_path = Path('/Users/chanchihyu/NTU/2024_高雄能見度計畫')
        cls.start = datetime(2024, 2, 1)
        cls.end = datetime(2024, 9, 30, 23, 59, 59)

    def test_nz_aurora(self):
        path_raw = self.base_path / 'NZ' / 'data' / 'Aurora'
        reader = RawDataReader('Aurora', path_raw, reset=True, qc='1MS', start=self.start, end=self.end)
        self.assertIsNotNone(reader)
        self.validate_data(reader)

    def test_nz_bc1054(self):
        path_raw = self.base_path / 'NZ' / 'data' / 'BC1054'
        reader = RawDataReader('BC1054', path_raw, reset=True, qc='1MS', start=self.start, end=self.end)
        self.assertIsNotNone(reader)
        self.validate_data(reader)

    def test_fs_neph(self):
        path_raw = self.base_path / 'FS' / 'data' / 'Neph'
        reader = RawDataReader('NEPH', path_raw, reset=True, qc='1MS', start=self.start, end=self.end)
        self.assertIsNotNone(reader)
        self.validate_data(reader)

    def test_fs_ae33(self):
        path_raw = self.base_path / 'FS' / 'data' / 'AE33'
        reader = RawDataReader('AE33', path_raw, reset=True, qc='1MS', start=self.start, end=self.end)
        self.assertIsNotNone(reader)
        self.validate_data(reader)

    def test_nz_teom(self):
        path_raw = self.base_path / 'NZ' / 'data' / 'Teom'
        reader = RawDataReader('TEOM', path_raw, reset=True, qc='1MS', start=self.start, end=self.end)
        self.assertIsNotNone(reader)
        self.validate_data(reader)

    def test_nz_ocec(self):
        path_raw = self.base_path / 'NZ' / 'data' / 'OCEC_Rawdata'
        reader = RawDataReader('OCEC', path_raw, reset=True, qc='1MS', start=self.start, end=self.end)
        self.assertIsNotNone(reader)
        self.validate_data(reader)

    # def test_fs_ocec(self):
    #     path_raw = self.base_path / 'FS' / 'data' / 'OCEC'
    #     reader = RawDataReader('OCEC', path_raw, reset=True, qc='1MS', start=self.start, end=self.end)
    #     self.assertIsNotNone(reader)
    #     self.validate_data(reader)

    def test_smps(self):
        path_raw = self.base_path / 'NZ' / 'data' / 'SMPS'
        reader = RawDataReader('SMPS', path_raw, reset=True, qc='1MS', start=self.start, end=self.end)
        self.assertIsNotNone(reader)
        self.validate_data(reader)

    # def test_aps(self):
    #     path_raw = self.base_path / 'NZ' / 'data' / 'APS'
    #     reader = RawDataReader('APS', path_raw, reset=True, qc='1MS', start=self.start, end=self.end)
    #     self.assertIsNotNone(reader)
    #     self.validate_data(reader)

    def test_nz_minion(self):
        path_raw = self.base_path / 'NZ' / 'data' / 'Minion'
        reader = RawDataReader('Minion', path_raw, reset=True, qc='1MS', start=self.start, end=self.end)
        self.assertIsNotNone(reader)
        self.validate_data(reader)

    def test_fs_minion(self):
        path_raw = self.base_path / 'FS' / 'data' / 'Minion'
        reader = RawDataReader('Minion', path_raw, reset=True, qc='1MS', start=self.start, end=self.end)
        self.assertIsNotNone(reader)
        self.validate_data(reader)

    def validate_data(self, reader):
        # 檢查日期範圍
        self.assertTrue((reader.index >= self.start).all() and (reader.index <= self.end).all())

        # 檢查是否有數據
        self.assertFalse(reader.empty)

        # 檢查特定列是否存在（根據你的數據結構調整）
        # if isinstance(reader, pd.DataFrame):
        #     expected_columns = ['PM2.5', 'NO2', 'AT']  # 根據實際數據調整
        #     for col in expected_columns:
        #         self.assertIn(col, reader.columns)

        # 檢查數據類型
        # self.assertTrue(pd.api.types.is_numeric_dtype(reader['PM2.5']))

        # 檢查是否有處理過的特殊符號
        # self.assertFalse((reader == '_').any().any())
        # self.assertFalse((reader == '*').any().any())

    # def test_reset_functionality(self):
    #     path_raw = self.base_path / 'NZ' / 'data' / 'Minion'
    #     reader1 = RawDataReader('Minion', path_raw, reset=True, start=self.start, end=self.end)
    #     reader2 = RawDataReader('Minion', path_raw, reset=False, start=self.start, end=self.end)
    #     # 比較兩者的結果，這裡需要根據你的具體實現來定義比較邏輯
    #     self.assertEqual(reader1.shape, reader2.shape)

    # def test_error_handling(self):
    #     with self.assertRaises(ValueError):
    #         RawDataReader('InvalidInstrument', self.base_path)
    #     with self.assertRaises(FileNotFoundError):
    #         RawDataReader('Minion', Path("non_existent_path"))


if __name__ == '__main__':
    unittest.main()
