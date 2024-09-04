from pandas import to_datetime, read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'Sunset_OCEC'

    def _raw_reader(self, _file):
        with open(_file, 'r', encoding='utf-8', errors='ignore') as f:
            _df = read_csv(f, skiprows=3)

            _df['Start Date/Time'] = _df['Start Date/Time'].str.strip()
            _df['time'] = to_datetime(_df['Start Date/Time'], format='%m/%d/%Y %I:%M:%S %p', errors='coerce')
            _df = _df.set_index('time')

            _df = _df.rename(columns={
                'Thermal/Optical OC (ugC/LCm^3)': 'Thermal_OC',
                'OC ugC/m^3 (Thermal/Optical)': 'Thermal_OC',

                'Thermal/Optical EC (ugC/LCm^3)': 'Thermal_EC',
                'EC ugC/m^3 (Thermal/Optical)': 'Thermal_EC',

                'OC=TC-BC (ugC/LCm^3)': 'Optical_OC',
                'OC by diff ugC (TC-OptEC)': 'Optical_OC',

                'BC (ugC/LCm^3)': 'Optical_EC',
                'OptEC ugC/m^3': 'Optical_EC',

                'Sample Volume Local Condition Actual m^3': 'Sample_Volume',
                'TC (ugC/LCm^3)': 'TC',
                'TC ugC/m^3': 'TC',
                'OCPk1-ug C': 'OC1',
                'OCPk2-ug C': 'OC2',
                'OCPk3-ug C': 'OC3',
                'OCPk4-ug C': 'OC4',
                'Pyrolized C ug': 'PC'
            })

            _df = _df[['Thermal_OC', 'Optical_OC', 'Thermal_EC', 'Optical_EC', 'TC', 'OC1', 'OC2', 'OC3', 'OC4']]

            return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    # QC data
    def _QC(self, _df):
        import numpy as np

        _df = _df.where(_df > 0)

        thresholds = {
            'Thermal_OC': 0.3,
            'Optical_OC': 0.3,
            'Thermal_EC': 0.015,
            'Optical_EC': 0.015
        }

        for col, thresh in thresholds.items():
            _df.loc[_df[col] <= thresh, col] = np.nan

        return _df
