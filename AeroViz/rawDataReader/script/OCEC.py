from pandas import to_datetime, read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'OCEC'

    def _raw_reader(self, file):
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            _df = read_csv(f, skiprows=3, nrows=25)

            _df['Start Date/Time'] = _df['Start Date/Time'].str.strip()
            _df['time'] = to_datetime(_df['Start Date/Time'], format='%m/%d/%Y %I:%M:%S %p', errors='coerce')
            _df = _df.set_index('time')
            _df.index = _df.index.round('1h')

            _df = _df.rename(columns={
                'Thermal/Optical OC (ugC/LCm^3)': 'Thermal_OC',
                'Thermal/Optical EC (ugC/LCm^3)': 'Thermal_EC',
                'OC=TC-BC (ugC/LCm^3)': 'Optical_OC',
                'BC (ugC/LCm^3)': 'Optical_EC',
                'TC (ugC/LCm^3)': 'TC',

                'OC ugC/m^3 (Thermal/Optical)': 'Thermal_OC',
                'EC ugC/m^3 (Thermal/Optical)': 'Thermal_EC',
                'OC by diff ugC (TC-OptEC)': 'Optical_OC',
                'OptEC ugC/m^3': 'Optical_EC',
                'TC ugC/m^3': 'TC',

                'Sample Volume Local Condition Actual m^3': 'Sample_Volume',

                'OCPk1-ug C': 'OC1_raw',
                'OCPk2-ug C': 'OC2_raw',
                'OCPk3-ug C': 'OC3_raw',
                'OCPk4-ug C': 'OC4_raw',
                'ECPk1-ug C': 'EC1_raw',
                'ECPk2-ug C': 'EC2_raw',
                'ECPk3-ug C': 'EC3_raw',
                'ECPk4-ug C': 'EC4_raw',
                'ECPk5-ug C': 'EC5_raw',
            })

            _df = _df[['Thermal_OC', 'Optical_OC', 'Thermal_EC', 'Optical_EC', 'TC', 'Sample_Volume',
                       'OC1_raw', 'OC2_raw', 'OC3_raw', 'OC4_raw', 'EC1_raw', 'EC2_raw', 'EC3_raw', 'EC4_raw',
                       'EC5_raw']]

            return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    # QC data
    def _QC(self, _df):
        import numpy as np

        _df = _df.mask((_df <= 0) | (_df > 100)).copy()

        thresholds = {
            'Thermal_OC': 0.3,
            'Optical_OC': 0.3,
            'Thermal_EC': 0.015,
            'Optical_EC': 0.015
        }

        for col, thresh in thresholds.items():
            _df.loc[_df[col] <= thresh, col] = np.nan

        return _df
