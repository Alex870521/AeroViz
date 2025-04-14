import csv

import numpy as np
from pandas import to_datetime, to_numeric, read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    """ SMPS (Scanning Mobility Particle Sizer) Data Reader

    A specialized reader for SMPS data files, which measure particle size distributions
    in the range of 11.8-593.5 nm.

    See full documentation at docs/source/instruments/SMPS.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'SMPS'

    def _raw_reader(self, file):
        """
        Read and parse raw SMPS data files.

        Parameters
        ----------
        file : Path or str
            Path to the SMPS data file.

        Returns
        -------
        pandas.DataFrame or None
            Processed raw SMPS data with datetime index and particle sizes as columns.
            Returns None if the file's size range doesn't match the expected range.
        """

        def find_header_row(file_obj, delimiter):
            csv_reader = csv.reader(file_obj, delimiter=delimiter)
            for skip, row in enumerate(csv_reader):
                if row and (row[0] in ['Sample #', 'Scan Number']):
                    return skip
            raise ValueError("Header row not found")

        def parse_date(df, date_format):
            if 'Date' in df.columns and 'Start Time' in df.columns:
                return to_datetime(df['Date'] + ' ' + df['Start Time'], format=date_format, errors='coerce')
            elif 'DateTime Sample Start' in df.columns:
                return to_datetime(df['DateTime Sample Start'], format=date_format, errors='coerce')
            else:
                raise ValueError("Expected date columns not found")

        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            if file.suffix.lower() == '.txt':
                delimiter, date_formats = '\t', ['%m/%d/%y %X', '%m/%d/%Y %X']
            else:  # csv
                delimiter, date_formats = ',', ['%d/%m/%Y %X']

            skip = find_header_row(f, delimiter)
            f.seek(0)

            _df = read_csv(f, sep=delimiter, skiprows=skip, low_memory=False)

            if 'Date' not in _df.columns:  # 資料需要轉置
                try:
                    _df = _df.T  # 轉置
                    _df.columns = _df.iloc[0]  # 使用第一列作為欄位名稱
                    _df = _df.iloc[1:]  # 移除第一列（因為已經變成欄位名稱）
                    _df = _df.reset_index(drop=True)  # 重設索引
                except:
                    raise NotImplementedError('Not supported date format')

            for date_format in date_formats:
                _time_index = parse_date(_df, date_format)
                if not _time_index.isna().all():
                    break
            else:
                raise ValueError("Unable to parse dates with given formats")

            # sequence the data
            numeric_cols = [col for col in _df.columns if col.strip().replace('.', '').isdigit()]
            numeric_cols.sort(key=lambda x: float(x.strip()))

            _df.index = _time_index
            _df.index.name = 'time'

            _df_smps = _df[numeric_cols]
            _df_smps.columns = _df_smps.columns.astype(float)
            _df_smps = _df_smps.loc[_df_smps.index.dropna().copy()]

            size_range = self.kwargs.get('size_range') or (11.8, 593.5)

            if _df_smps.columns[0] != size_range[0] or _df_smps.columns[-1] != size_range[1]:
                self.logger.warning(f'\tSMPS file: {file.name} is not match the setting size range {size_range}, '
                                    f'it is ({_df_smps.columns[0]}, {_df_smps.columns[-1]}). '
                                    f'Please run by another RawDataReader instance, and set the correct size range')
                return None

            return _df_smps.apply(to_numeric, errors='coerce')

    def _QC(self, _df):
        """
        Perform quality control on SMPS particle size distribution data.

        Parameters
        ----------
        _df : pandas.DataFrame
            Raw SMPS data with datetime index and particle diameters as columns.
            Column names should be numeric values representing particle diameters in nm.

        Returns
        -------
        pandas.DataFrame
            Quality-controlled SMPS data with invalid measurements masked.

        Notes
        -----
        Applies the following QC filters:
        1. Size range filter: Retains only data within the specified particle size range
        2. Hourly data completeness: Requires minimum 5 measurements per hour
        3. Total concentration threshold: Minimum 2000 particles/cm³
        4. Upper concentration limit: Maximum 1×10⁶ dN/dlogDp per bin
        5. Large particle filter: Maximum 4000 dN/dlogDp for particles >400 nm
        """
        _df = _df.copy()
        _index = _df.index.copy()

        size_range = self.kwargs.get('size_range') or (11.8, 593.5)

        size_range_mask = (_df.columns.astype(float) >= size_range[0]) & (
                _df.columns.astype(float) <= size_range[1])
        _df = _df.loc[:, size_range_mask]

        # mask out the data size lower than 7
        _df.loc[:, 'total'] = _df.sum(axis=1, min_count=1) * (np.diff(np.log(_df.columns[:-1].to_numpy(float)))).mean()

        hourly_counts = (_df['total']
                         .dropna()
                         .resample('h')
                         .size()
                         .resample('6min')
                         .ffill()
                         .reindex(_df.index, method='ffill', tolerance='6min'))

        # Remove data with less than 5 data per hour
        _df = _df.mask(hourly_counts < 5)

        # remove total conc. (dN) lower than 2000
        _df = _df.mask(_df['total'] < 2000)
        _df = _df.drop('total', axis=1)

        # remove single bin conc. (dN/dlogdp) larger than 1e6
        _df = _df.mask((_df > 1e6).any(axis=1))

        # remove the bin over 400 nm which num. conc. larger than 4000
        large_bins = _df.columns[_df.columns.astype(float) >= 400]
        _df = _df.mask((_df[large_bins] > 4000).any(axis=1))

        return _df
