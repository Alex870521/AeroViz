import csv

import numpy as np
from pandas import to_datetime, to_numeric, read_csv

from AeroViz.rawDataReader.core import AbstractReader


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


class Reader(AbstractReader):
    nam = 'SMPS'

    def _raw_reader(self, file):
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            if file.suffix.lower() == '.txt':
                delimiter, date_formats = '\t', ['%m/%d/%y %X', '%m/%d/%Y %X']
            else:  # csv
                delimiter, date_formats = ',', ['%d/%m/%Y %X']

            skip = find_header_row(f, delimiter)
            f.seek(0)

            _df = read_csv(f, sep=delimiter, skiprows=skip, low_memory=False)

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

    # QC data
    def _QC(self, _df):
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

        # Remove data with less than 6 data per hour
        _df = _df.mask(hourly_counts < 6)

        # remove total conc. (dN) lower than 2000
        _df = _df.mask(_df['total'] < 2000)
        _df = _df.drop('total', axis=1)

        # remove single bin conc. (dN/dlogdp) larger than 1e6
        _df = _df.mask((_df > 1e6).any(axis=1))

        # remove the bin over 400 nm which num. conc. larger than 4000
        large_bins = _df.columns[_df.columns.astype(float) >= 400]
        _df = _df.mask((_df[large_bins] > 4000).any(axis=1))

        return _df
