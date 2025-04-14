import pandas as pd
from pandas import to_datetime, read_csv, Timedelta, to_numeric

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    """ TEOM Output Data Formats Reader

    A specialized reader for TEOM (Tapered Element Oscillating Microbalance)
    particulate matter data files with support for multiple file formats and
    comprehensive quality control.

    See full documentation at docs/source/instruments/TEOM.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'TEOM'

    def _raw_reader(self, file):
        """
        Read and parse raw TEOM data files in various formats.

        Handles multiple TEOM data formats and standardizes them to a consistent
        structure with uniform column names and datetime index.

        Parameters
        ----------
        file : Path or str
            Path to the TEOM data file.

        Returns
        -------
        pandas.DataFrame
            Processed raw TEOM data with datetime index and standardized columns.

        Raises
        ------
        NotImplementedError
            If the file format is not recognized as a supported TEOM data format.
        """
        _df = read_csv(file, skiprows=3, index_col=False)

        # Chinese month name conversion dictionary
        _time_replace = {'十一月': '11', '十二月': '12', '一月': '01', '二月': '02', '三月': '03', '四月': '04',
                         '五月': '05', '六月': '06', '七月': '07', '八月': '08', '九月': '09', '十月': '10'}

        # Try both naming conventions (will ignore columns that don't exist)
        _df = _df.rename(columns={
            # Remote download format
            'Time Stamp': 'time',
            'System status': 'status',
            'PM-2.5 base MC': 'PM_NV',
            'PM-2.5 MC': 'PM_Total',
            'PM-2.5 TEOM noise': 'noise',
            # USB/auto export format
            'time_stamp': 'time',
            'tmoStatusCondition_0': 'status',
            'tmoTEOMABaseMC_0': 'PM_NV',
            'tmoTEOMAMC_0': 'PM_Total',
            'tmoTEOMANoise_0': 'noise'
        })

        # Handle different time formats
        if 'time' in _df.columns:  # Remote download or auto export with time column
            _tm_idx = _df.time
            # Convert Chinese month names if present
            for _ori, _rpl in _time_replace.items():
                _tm_idx = _tm_idx.str.replace(_ori, _rpl)

            _df = _df.set_index(to_datetime(_tm_idx, errors='coerce', format='%d - %m - %Y %X'))

        elif 'Date' in _df.columns and 'Time' in _df.columns:  # USB download format
            _df['time'] = pd.to_datetime(_df['Date'] + ' ' + _df['Time'],
                                         errors='coerce', format='%Y-%m-%d %H:%M:%S')
            _df.drop(columns=['Date', 'Time'], inplace=True)
            _df.set_index('time', inplace=True)

        else:
            raise NotImplementedError("Unsupported TEOM data format")

        _df = _df[['PM_NV', 'PM_Total', 'noise', 'status']].apply(to_numeric, errors='coerce')

        # Remove duplicates and NaN indices
        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on TEOM particulate matter data.

        This method applies a series of filters to identify and mask invalid or
        unreliable data points based on established criteria for continuous
        PM2.5 measurements.

        Parameters
        ----------
        _df : pandas.DataFrame
            Raw TEOM data with datetime index and standardized columns:
            PM_NV, PM_Total, noise and status.

        Returns
        -------
        pandas.DataFrame
            Quality-controlled TEOM data with invalid measurements masked.

        Notes
        -----
        Applies the following QC filters:
        1. Noise threshold: Accepts only data with noise < 0.01
        2. Value range: Removes negative or zero concentration values
        3. Time-aware outlier detection: Uses 6-hour window for IQR-based filtering
        4. Hourly data completeness: Requires minimum 50% of expected measurements per hour
        5. Complete record requirement: Requires values in all columns (PM_NV and PM_Total)
        """
        _index = _df.index.copy()

        # remove status not equal 0
        # _df = _df.where(_df.status < 1)

        # remove noise greater than 0.01
        _df = _df.where(_df.noise < 0.01)

        # remove negative value
        _df = _df[['PM_NV', 'PM_Total']].mask((_df <= 0))

        # QC data in 1 hr
        # use time_aware_IQR_QC
        _df = self.time_aware_IQR_QC(_df, time_window='6h')

        # remove data where size < 50% in 1-hr
        points_per_hour = Timedelta('1h') / Timedelta(self.meta['freq'])
        for _key in ['PM_Total', 'PM_NV']:
            _size = _df[_key].dropna().resample('1h').size().reindex(_index).ffill()
            _df[_key] = _df[_key].mask(_size < points_per_hour * 0.5)

        # make sure all columns have values, otherwise set to nan
        return _df.dropna(how='any').reindex(_index)
