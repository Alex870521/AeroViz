from typing import Literal

import numpy as np
import pandas
from pandas import DataFrame, read_excel

from AeroViz.rawDataReader.config.supported_instruments import meta
from AeroViz.rawDataReader.core import AbstractReader

pandas.set_option("future.no_silent_downcasting", True)

desired_order1 = ['SO2', 'NO', 'NOx', 'NO2', 'CO', 'O3', 'THC', 'NMHC',
                  'CH4', 'PM10', 'PM2.5', 'WS', 'WD', 'AT', 'RH']

desired_order2 = ['Benzene', 'Toluene', 'EthylBenzene', 'm/p-Xylene', 'o-Xylene']

MDL_NUMBER = -999


class Reader(AbstractReader):
    nam = 'Minion'

    # 楠梓8月數據(環境部)(空品、重金屬和氣膠可用率) -> 楠梓8月數據_level1 -> NZ_minion_XXXX
    def _raw_reader(self, file):
        df = read_excel(file, index_col=0, parse_dates=True)
        df.index.name = 'Time'

        # 重命名列，去除空白
        df = df.rename(columns=lambda x: x.strip())

        # 保存單位
        self.units = df.iloc[0].copy()

        # 刪除原始數據中的單位行
        df = df.iloc[1:]

        # 替換特定值
        df = df.replace({'維護校正': '*', np.nan: '-', 'Nodata': '-', '0L': MDL_NUMBER})
        # df = df.replace(to_replace=r'\d*\.?\d*[#]\b', value='_', regex=True)
        df = df.replace(to_replace=r'\d*\.?\d*[L]\b', value=MDL_NUMBER, regex=True)

        # 處理除了'WD'列的 0 值 替換為 '_'
        for col in [col for col in df.columns if col != 'WD']:
            df[col] = df[col].replace({0: MDL_NUMBER})

        # replace to numeric for estimating qc rate
        df = df.replace({'_': MDL_NUMBER})

        XRF_col = list(meta.get('XRF').get('MDL').keys())
        IGAC_col = list(meta.get('IGAC').get('MDL').keys())

        # 重新排序列
        df = self.reorder_dataframe_columns(df, [desired_order1, desired_order2, XRF_col, IGAC_col])

        # 將單位行添加回 DataFrame
        # df = concat([units.to_frame().T, df])

        # save Level1 data
        output_folder = file.parent / 'Level1'
        output_folder.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_folder / f'{file.stem}_Level1.csv')

        return df.loc[~df.index.duplicated() & df.index.notna()]

    def _QC(self, _df):
        IGAC_col = list(meta.get('IGAC').get('MDL'))
        XRF_col = list(meta.get('XRF').get('MDL'))

        # IGAC MDL QC
        _df[IGAC_col] = self.IGAC_QAQC(_df[IGAC_col])

        # XRF MDL QC
        _df[XRF_col] = self.XRF_QAQC(_df[XRF_col])

        # remove negative value
        # _df = _df.mask((_df < 0))
        _df = _df.mask(_df == MDL_NUMBER, np.nan)

        col = [col for col in desired_order1 if col != 'WD']
        _df[col] = self.time_aware_IQR_QC(_df[col])

        # Calculate the mass and ion balance
        # mass tolerance = ± 1, ions balance tolerance = ± 1

        # # conc. of main salt should be present at the same time (NH4+, SO42-, NO3-)
        # _df_salt = df.mask(df.sum(axis=1, min_count=1) > df.PM25).dropna(subset=_main).copy()

        ions_mass = _df[['Na+', 'NH4+', 'K+', 'Mg2+', 'Ca2+', 'Cl-', 'NO3-', 'SO42-']].sum(axis=1)
        element_mass = _df[XRF_col].sum(axis=1)

        estimated_mass = ions_mass + element_mass

        valid_mask = 2 * _df['PM2.5'] > estimated_mass

        _df.loc[~valid_mask, IGAC_col + XRF_col] = np.nan

        return _df

    def mdlReplace_timeAware_qc(self, df: DataFrame, MDL: dict, MDL_replace) -> DataFrame:
        # Step 1: Track MDL positions and values below threshold
        mdl_mask = (df.eq(MDL_NUMBER) |
                    df.apply(lambda x: x < MDL.get(x.name, float('-inf'))))

        # Step 2: Convert all values below MDL to MDL_NUMBER (-999)
        df_mdl = df.mask(mdl_mask, MDL_NUMBER)

        # Step 3: Apply time_aware_IQR_QC (excluding MDL_NUMBER values)
        df_qc = self.time_aware_IQR_QC(df_mdl.mask(df_mdl == MDL_NUMBER))

        # Step 4: Handle values below MDL according to specified method
        if MDL_replace == '0.5 * MDL':
            for column, threshold in MDL.items():
                if column in df.columns and threshold is not None:
                    df_qc.loc[df_mdl[column] == MDL_NUMBER, column] = 0.5 * threshold
                else:
                    df_qc.loc[df_mdl[column] == MDL_NUMBER, column] = np.nan
        else:  # 'nan'
            df_qc = df_qc.mask(df_mdl == MDL_NUMBER, np.nan)

        return df_qc

    def XRF_QAQC(self,
                 df: DataFrame,
                 MDL_replace: Literal['nan', '0.5 * MDL'] = '0.5 * MDL'
                 ) -> DataFrame:
        """
        Perform Quality Assurance and Quality Control for XRF data

        Parameters
        ----------
        df : pd.DataFrame
            Input dataframe with XRF data
        MDL_replace : {'nan', '0.5 * MDL'}, default='nan'
            Method to handle values below MDL:
            - 'nan': Replace with NaN
            - '0.5 * MDL': Replace with half of MDL value

        Returns
        -------
        pd.DataFrame
            Processed dataframe with QC applied and MDL values handled
        """
        MDL = meta.get('XRF').get('MDL')

        df = self.mdlReplace_timeAware_qc(df, MDL, MDL_replace)

        # 轉換單位 ng/m3 -> ug/m3
        if df.Al.max() > 10 and df.Fe.max() > 10:
            columns_to_convert = [col for col in MDL.keys() if col in df.columns]
            df[columns_to_convert] = df[columns_to_convert].div(1000)

        self.logger.info(f"\t{'XRF QAQC summary':21}: transform values below MDL to {MDL_replace}")

        return df

    def IGAC_QAQC(self,
                  df: DataFrame,
                  MDL_replace: Literal['nan', '0.5 * MDL'] = '0.5 * MDL',
                  tolerance: float = 1
                  ) -> DataFrame:
        """
        Perform Quality Assurance and Quality Control for IGAC data

        Parameters
        ----------
        df : pd.DataFrame
            Input dataframe with IGAC data
        MDL_replace : {'nan', '0.5 * MDL'}, default='nan'
            Method to handle values below MDL:
            - 'nan': Replace with NaN
            - '0.5 * MDL': Replace with half of MDL value
        tolerance : float, default=1
            Tolerance value for QC checks

        Returns
        -------
        pd.DataFrame
            Processed dataframe with QC applied and MDL values handled
        """
        MDL = meta.get('IGAC').get('MDL')

        df = self.mdlReplace_timeAware_qc(df, MDL, MDL_replace)

        # Define the ions
        _df = df.copy()
        _cation, _anion, _main = (['Na+', 'NH4+', 'K+', 'Mg2+', 'Ca2+'],
                                  ['Cl-', 'NO2-', 'NO3-', 'SO42-'],
                                  ['SO42-', 'NO3-', 'NH4+'])

        CA_range = ()  # CA, AC Q3=1.5 * IQR

        _df['+_mole'] = _df[_cation].div([23, 18, 39, (24 / 2), (40 / 2)]).sum(axis=1, skipna=True)
        _df['-_mole'] = _df[_anion].div([35.5, 46, 62, (96 / 2)]).sum(axis=1, skipna=True)

        # Avoid division by zero
        _df['ratio'] = np.where(_df['-_mole'] != 0, _df['+_mole'] / _df['-_mole'], np.nan)

        # Calculate bounds
        lower_bound, upper_bound = 1 - tolerance, 1 + tolerance

        # 根據ratio决定是否保留原始数据
        valid_mask = ((_df['ratio'] <= upper_bound) & (_df['ratio'] >= lower_bound) &
                      ~np.isnan(_df['+_mole']) & ~np.isnan(_df['-_mole']))

        # 保留数據或將不符合的條件設為NaN
        df.loc[~valid_mask] = np.nan

        # 計算保留的数據的百分比
        retained_percentage = (valid_mask.sum() / len(df)) * 100

        self.logger.info(
            f"\t{'Ions balance summary':21}: {retained_percentage.__round__(0)}% within tolerance ± {tolerance}")

        if retained_percentage < 70:
            self.logger.warning("\tWarning: The percentage of retained data is less than 70%")

        return df
