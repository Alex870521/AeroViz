import pandas as pd
from pandas import to_datetime, read_csv, Timedelta, to_numeric

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'TEOM'

    # TEOM Output Data Formats
    # There are three data formats from TEOM instrument output:
    #
    # 1. Remote download format
    #    - Identified by 'Time Stamp' column
    #    - Date format: 'DD - MM - YYYY HH:MM:SS'
    #    - May contain Chinese month names requiring conversion
    #    - Maps columns: Time Stamp → time, System status → status,
    #      PM-2.5 base MC → PM_NV, PM-2.5 MC → PM_Total, PM-2.5 TEOM noise → noise
    #
    # 2. USB download or auto export format
    #    - Identified by 'tmoStatusCondition_0' column
    #    - Two possible time formats:
    #      a) Standard: 'Date' and 'Time' columns (YYYY-MM-DD HH:MM:SS)
    #      b) Alternative: 'time_stamp' column (similar to remote format)
    #    - Maps columns: tmoStatusCondition_0 → status, tmoTEOMABaseMC_0 → PM_NV,
    #      tmoTEOMAMC_0 → PM_Total, tmoTEOMANoise_0 → noise
    #
    # 3. Other formats
    #    - Not implemented, raises NotImplementedError
    #
    # All formats are standardized to the same column names with timestamp as index

    def _raw_reader(self, file):
        # TEOM Data Format Handler
        # Standardizes different TEOM data formats (remote download and USB/auto export)
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

        # Filter and clean data
        _df = _df.where(_df['status'] < 1)
        _df = _df[['PM_NV', 'PM_Total', 'noise']].apply(to_numeric, errors='coerce')

        # Remove duplicates and NaN indices
        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    # QC data
    def _QC(self, _df):
        _index = _df.index.copy()

        # remove negative value
        _df = _df.where(_df.noise < 0.01)[['PM_NV', 'PM_Total']].mask((_df <= 0))

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
