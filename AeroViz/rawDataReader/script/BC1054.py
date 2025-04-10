from pandas import read_csv, to_numeric, Timedelta

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    """ BC1054 Black Carbon Monitor Data Reader

    A specialized reader for BC1054 data files, which measure black carbon
    concentrations using light absorption.

    See full documentation at docs/instruments/BC1054.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'BC1054'

    def _raw_reader(self, file):
        """
        Read and parse raw BC1054 data files.

        Parameters
        ----------
        file : Path or str
            Path to the BC1054 data file.

        Returns
        -------
        pandas.DataFrame
            Processed BC1054 data with datetime index and black carbon concentration columns.

        Notes
        -----
        
        """
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            _df = read_csv(f, parse_dates=True, index_col=0)

            _df.columns = _df.columns.str.replace(' ', '')

            _df = _df.rename(columns={
                'BC1(ng/m3)': 'BC1',
                'BC2(ng/m3)': 'BC2',
                'BC3(ng/m3)': 'BC3',
                'BC4(ng/m3)': 'BC4',
                'BC5(ng/m3)': 'BC5',
                'BC6(ng/m3)': 'BC6',
                'BC7(ng/m3)': 'BC7',
                'BC8(ng/m3)': 'BC8',
                'BC9(ng/m3)': 'BC9',
                'BC10(ng/m3)': 'BC10'
            })

            # remove data without Status=1, 8, 16, 32 (Automatic Tape Advance), 65536 (Tape Move)
            if self.meta.get('error_state', False):
                _df = _df[~_df['Status'].isin(self.meta.get('error_state'))]

            _df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7', 'BC8', 'BC9', 'BC10', 'Status']].apply(
                to_numeric,
                errors='coerce')

            return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on BC1054 data.

        Parameters
        ----------
        _df : pandas.DataFrame
            Raw BC1054 data with datetime index and black carbon concentration columns.

        Returns
        -------
        pandas.DataFrame
            Quality-controlled BC1054 data with invalid measurements masked.

        Notes
        -----
        Applies the following QC filters in sequence:

        1. Instrument status check:
           Filters out data points with invalid status codes
           (indicating filter tape issues or other instrument problems)

        2. Value range:
           Valid black carbon concentrations between 0-20000 ng/m³

        3. Data representativeness:
           - Requires at least 50% of expected data points in each 1-hour window
           - Time-based outlier detection using 1-hour window for IQR-based filtering
           - Ensures data quality and temporal consistency

        4. Complete record requirement:
           Requires values across all wavelengths to ensure data completeness
           and measurement reliability
        """
        _index = _df.index.copy()

        error_states = [
            1,  # Power Failure
            2,  # Digital Sensor Link Failure
            4,  # Tape Move Failure
            8,  # Maintenance
            16,  # Flow Failure
            32,  # Automatic Tape Advance
            64,  # Detector Failure
            256,  # Sensor Range
            512,  # Nozzle Move Failure
            1024,  # SPI Link Failure
            2048,  # Calibration Audit
            # 4096,  # Storage Processor Link Failure (??)
            65536  # Tape Move
        ]

        # remove data without error status
        _df = self.filter_error_status(_df, error_states)

        _df = _df.drop(columns=['Status'])

        # remove deduplicated row 如果一行與前一行或後一行重複，就標記為重複
        duplicate_rows = _df.eq(_df.shift()).all(axis=1) | _df.eq(_df.shift(-1)).all(axis=1)

        # 保留非重複的行
        _df = _df[~duplicate_rows]

        bc_columns = ['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7', 'BC8', 'BC9', 'BC10']

        # remove negative value
        _df[bc_columns] = _df[bc_columns].mask(
            (_df[bc_columns] <= 0) | (_df[bc_columns] > 20000)
        )

        # Check data representativeness (at least 50% data points per hour)
        points_per_hour = Timedelta('1h') / Timedelta(self.meta['freq'])
        for col in bc_columns:
            _size = _df[col].dropna().resample('1h').size().reindex(_index).ffill()
            _df[col] = _df[col].mask(_size < points_per_hour * 0.5)

        # use IQR_QC for outlier detection
        _df = self.time_aware_IQR_QC(_df, time_window='1h')

        # make sure all columns have values, otherwise set to nan
        return _df.dropna(how='any').reindex(_index)
