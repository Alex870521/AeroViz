import numpy as np
from pandas import read_csv, to_datetime, to_numeric

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'Minion'

    def _raw_reader(self, file):
        with file.open('r', encoding='utf-8-sig', errors='ignore') as f:
            _df = read_csv(f, low_memory=False, index_col=0)

            _df.index = to_datetime(_df.index, errors='coerce')
            _df.index.name = 'time'

            _df.columns = _df.keys().str.strip(' ')

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        # XRF QAQC
        _df = self.XRF_QAQC(_df)

        # ions balance
        _df = self.ions_balance(_df)

        # remove negative value
        _df = _df.mask((_df < 0).copy())

        # QC data in 6h
        return _df.resample('6h').apply(self.basic_QC).resample(self.meta.get("freq")).mean()

    # base on Xact 625i Minimum Decision Limit (MDL) for XRF in ng/m3, 60 min sample time
    def XRF_QAQC(self, df):
        MDL = {
            'Al': 100, 'Si': 18, 'P': 5.2, 'S': 3.2,
            'Cl': 1.7, 'K': 1.2, 'Ca': 0.3, 'Ti': 1.6,
            'V': 0.12, 'Cr': 0.12, 'Mn': 0.14, 'Fe': 0.17,
            'Co': 0.14, 'Ni': 0.096, 'Cu': 0.079, 'Zn': 0.067,
            'Ga': 0.059, 'Ge': 0.056, 'As': 0.063, 'Se': 0.081,
            'Br': 0.1, 'Rb': 0.19, 'Sr': 0.22, 'Y': 0.28,
            'Zr': 0.33, 'Nb': 0.41, 'Mo': 0.48, 'Ag': 1.9,
            'Cd': 2.5, 'In': 3.1, 'Sn': 4.1, 'Sb': 5.2,
            'Te': 0.6, 'I': 0.49, 'Cs': 0.37, 'Ba': 0.39,
            'La': 0.36, 'Ce': 0.3, 'Pt': 0.12, 'Au': 0.1,
            'Hg': 0.12, 'Tl': 0.12, 'Pb': 0.13, 'Bi': 0.13
        }
        # 將小於 MDL 值的數據替換為 NaN
        for element, threshold in MDL.items():
            if element in df.columns:
                df[element] = df[element].where(df[element] >= threshold, np.nan)

        self.logger.info(f"{'=' * 60}")
        self.logger.info(f"XRF QAQC summary:")
        self.logger.info("\t\ttransform values below MDL to NaN")
        self.logger.info(f"{'=' * 60}")

        return df

    def ions_balance(self, df, tolerance=0.3):
        """
        Calculate the balance of ions in the system
        """
        # Define the ions
        item = ['Na+', 'NH4+', 'K+', 'Mg2+', 'Ca2+', 'F-', 'Cl-', 'NO2-', 'NO3-', 'PO43-', 'SO42-']

        # Calculate the balance
        _df = df[item].copy()
        _df = _df.apply(lambda x: to_numeric(x, errors='coerce'))
        _df['+_mole'] = _df[['Na+', 'NH4+', 'K+', 'Mg2+', 'Ca2+']].div([23, 18, 39, (24 / 2), (40 / 2)]).sum(axis=1,
                                                                                                             skipna=True)
        _df['-_mole'] = _df[['Cl-', 'NO2-', 'NO3-', 'SO42-']].div([35.5, 46, 62, (96 / 2)]).sum(axis=1, skipna=True)

        # Avoid division by zero
        _df['ratio'] = np.where(_df['-_mole'] != 0, _df['+_mole'] / _df['-_mole'], np.nan)

        # Calculate bounds
        lower_bound, upper_bound = 1 - tolerance, 1 + tolerance

        # 根据ratio决定是否保留原始数据
        valid_mask = (
                (_df['ratio'] <= upper_bound) &
                (_df['ratio'] >= lower_bound) &
                ~np.isnan(_df['+_mole']) &
                ~np.isnan(_df['-_mole'])
        )

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

        return df
