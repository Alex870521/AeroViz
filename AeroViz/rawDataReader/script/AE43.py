from pandas import read_csv, to_numeric, Timedelta

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    """ AE43 Aethalometer Data Reader

    A specialized reader for AE43 Aethalometer data files, which measure black carbon
    concentrations at multiple wavelengths.

    See full documentation at docs/instruments/AE43.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'AE43'

    def _raw_reader(self, file):
        """
        Read and parse raw AE43 Aethalometer data files.

        Parameters
        ----------
        file : Path or str
            Path to the AE43 data file.

        Returns
        -------
        pandas.DataFrame
            Processed AE43 data with datetime index and black carbon
            concentration columns.
        """
        _df = read_csv(file, parse_dates={'time': ['StartTime']}, index_col='time')
        _df_id = _df['SetupID'].iloc[-1]

        # get last SetupID data
        _df = _df.groupby('SetupID').get_group(_df_id)[
            ['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7', 'Status']].copy()

        _df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7']].apply(to_numeric, errors='coerce')

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on AE43 Aethalometer data.
        
        Parameters
        ----------
        _df : pandas.DataFrame
            Raw AE43 data with datetime index and black carbon concentration columns.
        
        Returns
        -------
        pandas.DataFrame
            Quality-controlled AE43 data with invalid measurements masked.
            
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

        # assume AE43 Status is same as AE33
        error_states = [
            1,  # Tape advance (tape advance, fast calibration, warm-up)
            2,  # First measurement – obtaining ATN0
            3,  # Stopped
            4,  # Flow low/high by more than 0.5 LPM or F1 < 0 or F2/F1 outside 0.2 – 0.75 range
            16,  # Calibrating LED
            32,  # Calibration error (at least one channel OK)
            384,  # Tape error (tape not moving, end of tape)
            1024,  # Stability test
            2048,  # Clean air test
            4096,  # Optical test
            # 8192,  # Connection Error (??)
        ]

        # remove data without error status
        _df = self.filter_error_status(_df, error_states)

        _df = _df.drop(columns=['Status'])

        bc_columns = ['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7']

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
