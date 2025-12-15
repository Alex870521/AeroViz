import numpy as np
from pandas import read_csv, to_numeric

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder

desired_order1 = ['SO2', 'NO', 'NOx', 'NO2', 'CO', 'O3', 'THC', 'NMHC',
                  'CH4', 'PM10', 'PM2.5', 'PM1', 'WS', 'WD', 'AT', 'RH']

desired_order2 = ['Benzene', 'Toluene', 'EthylBenzene', 'm/p-Xylene', 'o-Xylene']


class Reader(AbstractReader):
    """EPA Environmental Data Reader

    A specialized reader for EPA air quality monitoring data files.

    See full documentation at docs/source/instruments/EPA.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'EPA'

    def _raw_reader(self, file):
        # 查詢小時值(測項).csv & 查詢小時值(直式).csv (有、無輸出有效值都可以)
        df = read_csv(file, encoding='big5', encoding_errors='ignore', index_col=0, parse_dates=True,
                      on_bad_lines='skip')

        if len(df.groupby('測站')) > 1:
            raise ValueError(f"Multiple stations found in the file: {df['測站'].unique()}")
        else:
            if '測站' in df.columns:
                df.drop(columns=['測站'], inplace=True)

            if '測項' in df.columns:
                df = df.pivot(columns='測項', values='資料')

            df.rename(columns={'AMB_TEMP': 'AT', 'WIND_SPEED': 'WS', 'WIND_DIREC': 'WD'}, inplace=True)
            df.index.name = 'Time'

            # 如果沒有將無效值拿掉就輸出 請將包含 #、L 的字串替換成 # 或 _
            df = df.replace(to_replace=r'\d*\.?\d*[#]\b', value='#', regex=True)
            df = df.replace(to_replace=r'\d*\.?\d*[L]\b', value='_', regex=True)

            # 欄位排序
            return self.reorder_dataframe_columns(df, [desired_order1]).apply(to_numeric, errors='coerce')

    def _QC(self, _df):
        """
        Perform quality control on EPA data.

        QC Rules Applied
        ----------------
        1. Negative        : Any measurement value < 0
        """
        _index = _df.index.copy()
        df_qc = _df.copy()

        # Get numeric columns for negative value check
        numeric_cols = df_qc.select_dtypes(include=[np.number]).columns.tolist()

        # Build QC rules declaratively
        qc = QCFlagBuilder()
        qc.add_rules([
            QCRule(
                name='Negative',
                condition=lambda df: (df[numeric_cols] < 0).any(axis=1) if numeric_cols else False,
                description='Measurement value is negative (< 0)'
            ),
        ])

        # Apply all QC rules and get flagged DataFrame
        df_qc = qc.apply(df_qc)

        # Log QC summary
        summary = qc.get_summary(df_qc)
        self.logger.info(f"{self.nam} QC Summary:")
        for _, row in summary.iterrows():
            self.logger.info(f"  {row['Rule']}: {row['Count']} ({row['Percentage']})")

        return df_qc.reindex(_index)
