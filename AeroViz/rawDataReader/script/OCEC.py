import numpy as np
from pandas import to_datetime, read_csv, to_numeric

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    """ OC/EC (Organic Carbon/Elemental Carbon) Analyzer Data Reader

    A specialized reader for OC/EC analyzer data files, which measure carbonaceous
    aerosol composition using thermal and optical methods.

    See full documentation at docs/source/instruments/OCEC.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'OCEC'

    def _raw_reader(self, file):
        """
        Read and parse raw OC/EC data files.

        Parameters
        ----------
        file : Path or str
            Path to the OC/EC data file.

        Returns
        -------
        pandas.DataFrame
            Processed OC/EC data with datetime index and carbon fraction columns.
        """
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            _df = read_csv(f, skiprows=3, on_bad_lines='skip')

            _df['Start Date/Time'] = _df['Start Date/Time'].str.strip()
            _df['time'] = to_datetime(_df['Start Date/Time'], format='%m/%d/%Y %I:%M:%S %p', errors='coerce')

            if _df['time'].isna().all():
                _df['time'] = to_datetime(_df['Start Date/Time'], format='%m/%d/%Y %H:%M:%S', errors='coerce')

            _df = _df.set_index('time')

            _df = _df.loc[~_df.index.duplicated() & _df.index.notna()]

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
                'Pyrolized C ug': 'PC_raw',

                'ECPk1-ug C': 'EC1_raw',
                'ECPk2-ug C': 'EC2_raw',
                'ECPk3-ug C': 'EC3_raw',
                'ECPk4-ug C': 'EC4_raw',
                'ECPk5-ug C': 'EC5_raw',
            })

            _df = _df.apply(to_numeric, errors='coerce')

            _df['OC1'] = _df['OC1_raw'] / _df['Sample_Volume']
            _df['OC2'] = _df['OC2_raw'] / _df['Sample_Volume']
            _df['OC3'] = _df['OC3_raw'] / _df['Sample_Volume']
            _df['OC4'] = _df['OC4_raw'] / _df['Sample_Volume']

            _df['PC'] = _df['Thermal_OC'] - _df['OC1'] - _df['OC2'] - _df['OC3'] - _df['OC4']

            # _df['EC1'] = _df['EC1_raw'] / _df['Sample_Volume']
            # _df['EC2'] = _df['EC2_raw'] / _df['Sample_Volume']
            # _df['EC3'] = _df['EC3_raw'] / _df['Sample_Volume']
            # _df['EC4'] = _df['EC4_raw'] / _df['Sample_Volume']
            # _df['EC5'] = _df['EC5_raw'] / _df['Sample_Volume']

            _df = _df[['Thermal_OC', 'Thermal_EC', 'Optical_OC', 'Optical_EC', 'TC', 'Sample_Volume',
                       'OC1', 'OC2', 'OC3', 'OC4', 'PC']]

            return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on OC/EC data.

        Parameters
        ----------
        _df : pandas.DataFrame
            Raw OC/EC data with datetime index and carbon fraction columns.

        Returns
        -------
        pandas.DataFrame
            Quality-controlled OC/EC data with invalid measurements masked.

        Notes
        -----
        Applies the following QC filters:
        1. Value range: Valid carbon measurements between -5 and 100 μgC/m³
        2. Detection limits:
           - Thermal_OC: 0.3 μgC/m³
           - Optical_OC: 0.3 μgC/m³
           - Thermal_EC: 0.015 μgC/m³
           - Optical_EC: 0.015 μgC/m³
        3. Time-based outlier detection: Using IQR-based filtering
        4. Requires valid OC measurements (Thermal and Optical)
        """
        MDL = {'Thermal_OC': 0.3,  # 0.89
               'Optical_OC': 0.3,  # 0.08
               'Thermal_EC': 0.015,
               'Optical_EC': 0.015
               }

        _index = _df.index.copy()

        _df = _df.mask((_df <= -5) | (_df > 100))

        for col, threshold in MDL.items():
            _df.loc[_df[col] <= threshold, col] = np.nan

        # use IQR_QC
        _df = self.time_aware_IQR_QC(_df)

        return _df.dropna(subset=['Thermal_OC', 'Optical_OC']).reindex(_index)
