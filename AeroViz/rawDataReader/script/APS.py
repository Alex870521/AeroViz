import numpy as np
from pandas import to_datetime, read_table

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    """ APS (Aerodynamic Particle Sizer) Data Reader

    A specialized reader for APS data files, which measure particle size distributions
    in the range of 542-1981 nm.

    See full documentation at docs/source/instruments/APS.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'APS'

    def _raw_reader(self, file):
        """
        Read and parse raw APS data files.

        Parameters
        ----------
        file : Path or str
            Path to the APS data file.

        Returns
        -------
        pandas.DataFrame
            Processed APS data with datetime index and particle sizes as columns.
        """
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            _df = read_table(f, skiprows=6, parse_dates={'Time': ['Date', 'Start Time']},
                             date_format='%m/%d/%y %H:%M:%S', low_memory=False).set_index('Time')

            # 542 nm ~ 1981 nm
            _df = _df.iloc[:, 3:54].rename(columns=lambda x: round(float(x), 4))

            _df_idx = to_datetime(_df.index, format='%m/%d/%y %H:%M:%S', errors='coerce')

        return _df.set_index(_df_idx).loc[_df_idx.dropna()]

    def _QC(self, _df):
        """
        Perform quality control on APS data.

        Parameters
        ----------
        _df : pandas.DataFrame
            Raw APS data with datetime index and particle diameters as columns.

        Returns
        -------
        pandas.DataFrame
            Quality-controlled APS data with invalid measurements masked.

        Notes
        -----
        Applies the following QC filters:
        1. Hourly data completeness: Requires minimum 5 measurements per hour
        2. Total concentration thresholds: Valid range between 1-700 particles/cm³
        3. Calculates total concentration accounting for logarithmic bin spacing
        """
        _df = _df.copy()
        _index = _df.index.copy()

        # mask out the data size lower than 7
        _df.loc[:, 'total'] = _df.sum(axis=1, min_count=1) * (np.diff(np.log(_df.keys().to_numpy(float)))).mean()

        hourly_counts = (_df['total']
                         .dropna()
                         .resample('h')
                         .size()
                         .resample('6min')
                         .ffill()
                         .reindex(_df.index, method='ffill', tolerance='6min'))

        # Remove data with less than 5 data per hour
        _df = _df.mask(hourly_counts < 5)

        # remove total conc. lower than 700 or lower than 1
        _df = _df.mask((_df['total'] > 700) | (_df['total'] < 1))

        return _df[_df.keys()[:-1]]
