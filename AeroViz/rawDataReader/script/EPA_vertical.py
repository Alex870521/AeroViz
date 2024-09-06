import numpy as np
from pandas import read_csv, to_numeric

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'EPA_vertical'

    def _raw_reader(self, file):
        with file.open('r', encoding='ascii', errors='ignore') as f:
            # 有、無輸出有效值都可以
            # read 查詢小時值(測項).csv
            df = read_csv(f, encoding='ascii', encoding_errors='ignore', index_col=0, parse_dates=True,
                          usecols=lambda col: col != 'Unnamed: 1')

            df.index.name = 'Time'
            df.rename(columns={'AMB_TEMP': 'AT', 'WIND_SPEED': 'WS', 'WIND_DIREC': 'WD'}, inplace=True)

            # 欄位排序
            desired_order = ['SO2', 'NO', 'NOx', 'NO2', 'CO', 'O3', 'THC', 'NMHC', 'CH4', 'PM10', 'PM2.5', 'WS', 'WD',
                             'AT', 'RH']

            missing_columns = []

            for col in desired_order:
                if col not in df.columns:
                    df[col] = np.nan
                    missing_columns.append(col)

            if missing_columns:
                self.logger.info(f"{'=' * 60}")
                self.logger.info(f"Missing columns: {missing_columns}")
                self.logger.info(f"{'=' * 60}")
                print(f"Missing columns: {missing_columns}")

            df = df[desired_order]

            # 如果沒有將無效值拿掉就輸出 請將包含 #、L、O 的字串替換成 *
            df.replace(to_replace=r'\d*[#LO]\b', value='*', regex=True, inplace=True)
            df = df.apply(to_numeric, errors='coerce')

        return df

    def _QC(self, _df):
        return _df
