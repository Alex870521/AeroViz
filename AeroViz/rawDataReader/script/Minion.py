from typing import Literal

import numpy as np
import pandas
from pandas import read_excel, to_numeric

from AeroViz.rawDataReader.core import AbstractReader

pandas.set_option("future.no_silent_downcasting", True)

desired_order1 = ['SO2', 'NO', 'NOx', 'NO2', 'CO', 'O3', 'THC', 'NMHC',
                  'CH4', 'PM10', 'PM2.5', 'WS', 'WD', 'AT', 'RH']

desired_order2 = ['Benzene', 'Toluene', 'EthylBenzene', 'm/p-Xylene', 'o-Xylene']

desired_order3 = ['Al', 'Si', 'P', 'S', 'Cl', 'K', 'Ca', 'Ti', 'V', 'Cr', 'Mn', 'Fe',
                  'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Rb', 'Sr',
                  'Y', 'Zr', 'Nb', 'Mo', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te',
                  'Cs', 'Ba', 'La', 'Ce', 'W', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi']

desired_order4 = ['NH3', 'HF', 'HCl', 'HNO2', 'HNO3', 'G-SO2',
                  'Na+', 'NH4+', 'K+', 'Mg2+', 'Ca2+',
                  'F-', 'Cl-', 'NO2-', 'NO3-', 'PO43-', 'SO42-']


class Reader(AbstractReader):
    nam = 'Minion'

    def _raw_reader(self, file):
        # 讀取 Excel 文件
        df = read_excel(file, index_col=0, parse_dates=True)

        # 重命名列，去除空白
        df = df.rename(columns=lambda x: x.strip())

        # 保存單位行並給它一個名稱
        units = df.iloc[0].copy()

        # 刪除原始數據中的單位行
        df = df.iloc[1:]

        # 替換特定值
        df = df.replace({'維護校正': '*', np.nan: '-', '0L': '_', 'Nodata': '-'}, inplace=False)
        df = df.replace(to_replace=r'\d*[#]\b', value='#', regex=True)
        df = df.replace(to_replace=r'\d*[L]\b', value='_', regex=True)

        # 處理除了'WD'列的 0 值
        non_wd_columns = [col for col in df.columns if col != 'WD']
        df.loc[:, non_wd_columns] = df.loc[:, non_wd_columns].replace({0: '_'})

        # 重新排序列
        df = self.reorder_dataframe_columns(df, [desired_order1, desired_order2, desired_order3, desired_order4])

        # 將單位行添加回 DataFrame
        # df = concat([units.to_frame().T, df])

        df.index.name = 'Time'

        return df.loc[~df.index.duplicated() & df.index.notna()]

    def _QC(self, _df):
        # remove negative value
        _df = _df.mask((_df < 0).copy())

        # XRF QAQC
        _df = self.XRF_QAQC(_df)

        # ions balance
        _df = self.IGAC_QAQC(_df)

        # QC data in 6h
        return _df.resample('6h').apply(self.n_sigma_QC).resample(self.meta.get("freq")).mean()

    # base on Xact 625i Minimum Decision Limit (MDL) for XRF in ng/m3, 60 min sample time
    def XRF_QAQC(self, df, MDL_replace: Literal['nan', '0.5 * MDL'] = 'nan'):
        MDL = {
            'Al': 100, 'Si': 18, 'P': 5.2, 'S': 3.2,
            'Cl': 1.7, 'K': 1.2, 'Ca': 0.3, 'Ti': 1.6,
            'V': 0.12, 'Cr': 0.12, 'Mn': 0.14, 'Fe': 0.17,
            'Co': 0.14, 'Ni': 0.096, 'Cu': 0.079, 'Zn': 0.067,
            'Ga': 0.059, 'Ge': 0.056, 'As': 0.063, 'Se': 0.081,
            'Br': 0.1, 'Rb': 0.19, 'Sr': 0.22, 'Y': 0.28,
            'Zr': 0.33, 'Nb': 0.41, 'Mo': 0.48, 'Pd': 2.2,
            'Ag': 1.9, 'Cd': 2.5, 'In': 3.1, 'Sn': 4.1,
            'Sb': 5.2, 'Te': 0.6, 'Cs': 0.37, 'Ba': 0.39,
            'La': 0.36, 'Ce': 0.3, 'W': 0.0001, 'Pt': 0.12,
            'Au': 0.1, 'Hg': 0.12, 'Tl': 0.12, 'Pb': 0.13,
            'Bi': 0.13
        }
        # 將小於 MDL 值的數據替換為 nan or 5/6 MDL
        for element, threshold in MDL.items():
            if element in df.columns:
                rep = np.nan if MDL_replace == 'nan' else 0.5 * threshold
                df[element] = df[element].where(df[element] >= threshold, rep)

        self.logger.info(f"{'=' * 60}")
        self.logger.info(f"XRF QAQC summary:")
        self.logger.info("\t\ttransform values below MDL to NaN")
        self.logger.info(f"{'=' * 60}")

        # 轉換單位 ng/m3 -> ug/m3
        if df.Al.max() > 10 and df.Fe.max() > 10:
            # 確保 MDL.keys() 中的所有列都存在於 _df 中
            columns_to_convert = [col for col in MDL.keys() if col in df.columns]

            df[columns_to_convert] = df[columns_to_convert].div(1000)

        return df

    def IGAC_QAQC(self, df, tolerance=1):
        """
        Calculate the balance of ions in the system
        """
        # https://www.yangyao-env.com/web/product/product_in2.jsp?pd_id=PD1640151884502
        MDL = {
            'HF': 0.08, 'HCl': 0.05, 'HNO2': 0.01, 'HNO3': 0.05, 'G-SO2': 0.05, 'NH3': 0.1,
            'Na+': 0.05, 'NH4+': 0.08, 'K+': 0.08, 'Mg2+': 0.05, 'Ca2+': 0.05,
            'F-': 0.08, 'Cl-': 0.05, 'NO2-': 0.05, 'NO3-': 0.01, 'PO43-': None, 'SO42-': 0.05,
        }

        MR = {
            'HF': 200, 'HCl': 200, 'HNO2': 200, 'HNO3': 200, 'G-SO2': 200, 'NH3': 300,
            'Na+': 300, 'NH4+': 300, 'K+': 300, 'Mg2+': 300, 'Ca2+': 300,
            'F-': 300, 'Cl-': 300, 'NO2-': 300, 'NO3-': 300, 'PO43-': None, 'SO42-': 300,
        }

        _cation, _anion, _main = (['Na+', 'NH4+', 'K+', 'Mg2+', 'Ca2+'],
                                  ['Cl-', 'NO2-', 'NO3-', 'SO42-'],
                                  ['SO42-', 'NO3-', 'NH4+'])
        # QC: replace values below MDL with 0.5 * MDL -> ions balance -> PM2.5 > main salt
        # mass tolerance = 0.3, ions balance tolerance = 0.3

        # # conc. of main salt should be present at the same time (NH4+, SO42-, NO3-)
        # _df_salt = df.mask(df.sum(axis=1, min_count=1) > df.PM25).dropna(subset=_main).copy()

        # Define the ions
        item = ['Na+', 'NH4+', 'K+', 'Mg2+', 'Ca2+', 'Cl-', 'NO2-', 'NO3-', 'SO42-']

        # Calculate the balance
        _df = df[item].apply(lambda x: to_numeric(x, errors='coerce'))

        # for (_key, _df_col) in _df.items():
        #     _df[_key] = _df_col.mask(_df_col < MDL[_key], MDL[_key] / 2)

        _df['+_mole'] = _df[['Na+', 'NH4+', 'K+', 'Mg2+', 'Ca2+']].div([23, 18, 39, (24 / 2), (40 / 2)]).sum(axis=1,
                                                                                                             skipna=True)
        _df['-_mole'] = _df[['Cl-', 'NO2-', 'NO3-', 'SO42-']].div([35.5, 46, 62, (96 / 2)]).sum(axis=1, skipna=True)

        # Avoid division by zero
        _df['ratio'] = np.where(_df['-_mole'] != 0, _df['+_mole'] / _df['-_mole'], np.nan)

        # Calculate bounds
        lower_bound, upper_bound = 1 - tolerance, 1 + tolerance

        # 根据ratio决定是否保留原始数据
        valid_mask = ((_df['ratio'] <= upper_bound) & (_df['ratio'] >= lower_bound) &
                      ~np.isnan(_df['+_mole']) & ~np.isnan(_df['-_mole']))

        # 保留数据或将不符合条件的行设为NaN
        df.loc[~valid_mask, item] = np.nan

        # 计算保留的数据的百分比
        retained_percentage = (valid_mask.sum() / len(df)) * 100

        self.logger.info(f"{'=' * 60}")
        self.logger.info(f"Ions balance summary:")
        self.logger.info(f"\t\tretain {retained_percentage.__round__(0)}% data within tolerance {tolerance}")
        self.logger.info(f"{'=' * 60}")

        if retained_percentage < 70:
            self.logger.warning("Warning: The percentage of retained data is less than 70%")

        # print(f"\tretain {retained_percentage.__round__(0)}% data within tolerance {tolerance}")

        return df
