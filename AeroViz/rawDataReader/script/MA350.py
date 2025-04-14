from pandas import read_csv, to_numeric, Timedelta

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    """ MA350 Aethalometer Data Reader
    
    A specialized reader for MA350 Aethalometer data files, which measure 
    black carbon at multiple wavelengths and provide source apportionment.
    
    See full documentation at docs/source/instruments/MA350.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'MA350'

    def _raw_reader(self, file):
        """
        Read and parse raw MA350 Aethalometer data files.

        Parameters
        ----------
        file : Path or str
            Path to the MA350 data file.

        Returns
        -------
        pandas.DataFrame
            Processed MA350 data with datetime index and standardized black carbon
            and source apportionment columns.
        """
        _df = read_csv(file, parse_dates=['Date / time local'], index_col='Date / time local').rename_axis(
            "Time")

        _df = _df.rename(columns={
            'UV BCc': 'BC1',
            'Blue BCc': 'BC2',
            'Green BCc': 'BC3',
            'Red BCc': 'BC4',
            'IR BCc': 'BC5',
            'Biomass BCc  (ng/m^3)': 'BB mass',
            'Fossil fuel BCc  (ng/m^3)': 'FF mass',
            'Delta-C  (ng/m^3)': 'Delta-C',
            'AAE': 'AAE',
            'BB (%)': 'BB',
        })

        _df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BB mass', 'FF mass', 'Delta-C', 'AAE', 'BB', 'Status']].apply(
            to_numeric,
            errors='coerce')

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on MA350 Aethalometer data.
        
        Parameters
        ----------
        _df : pandas.DataFrame
            Raw MA350 data with datetime index and measurement columns.
        
        Returns
        -------
        pandas.DataFrame
            Quality-controlled MA350 data with invalid measurements masked.
            
        Notes
        -----
        Applies the following QC filters in sequence:

        1. Instrument status check:
           Filters out data points with invalid status codes
           (indicating filter tape issues or other instrument problems)

        2. Value range:
           Valid black carbon concentrations between 0-20000 ng/m³
           (applied to BC1-BC5 wavelength-specific channels)

        3. Data representativeness:
           - Requires at least 50% of expected data points in each 1-hour window
           - Time-based outlier detection using 1-hour window for IQR-based filtering
           - Ensures data quality and temporal consistency

        4. Complete record requirement:
           Requires values across all columns to ensure data completeness
           and measurement reliability
        """
        _index = _df.index.copy()

        error_states = [
            1,  # Power Failure
            2,  # Start up
            4,  # Tape advance
            16,  # Optical saturation
            32,  # Sample timing error
            128,  # Flow unstable
            256,  # Pump drive limit
            2048,  # System busy
            8192,  # Tape jam
            16384,  # Tape at end
            32768,  # Tape not ready
            65536,  # Tape transport not ready
            262144,  # Invalid date/time
            524288,  # Tape error
        ]

        # remove data without error status
        _df = self.filter_error_status(_df, error_states)

        _df = _df.drop(columns=['Status'])

        bc_columns = ['BC1', 'BC2', 'BC3', 'BC4', 'BC5']

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
