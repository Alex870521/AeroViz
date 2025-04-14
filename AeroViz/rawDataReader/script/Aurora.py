from pandas import to_datetime, read_csv, to_numeric, Timedelta

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    """ Aurora Integrating Nephelometer Data Reader

    A specialized reader for Aurora nephelometer data files, which measure aerosol light
    scattering properties at multiple wavelengths.

    See full documentation at docs/source/instruments/Aurora.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'Aurora'

    def _raw_reader(self, file):
        """
        Read and parse raw Aurora nephelometer data files.

        Parameters
        ----------
        file : Path or str
            Path to the Aurora data file.

        Returns
        -------
        pandas.DataFrame
            Processed Aurora data with datetime index and standardized
            scattering coefficient columns.
        """
        _df = read_csv(file, low_memory=False, index_col=0)

        _df.index = to_datetime(_df.index, errors='coerce')
        _df.index.name = 'time'

        _df.columns = _df.keys().str.strip(' ')

        # consider another csv format
        _df = _df.rename(columns={
            '0°σspB': 'B',
            '0°σspG': 'G',
            '0°σspR': 'R',
            '90°σspB': 'BB',
            '90°σspG': 'BG',
            '90°σspR': 'BR',
            'Blue': 'B',
            'Green': 'G',
            'Red': 'R',
            'B_Blue': 'BB',
            'B_Green': 'BG',
            'B_Red': 'BR',
        })

        _df = _df[['B', 'G', 'R', 'BB', 'BG', 'BR']].apply(to_numeric, errors='coerce')

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on Aurora nephelometer data.

        Parameters
        ----------
        _df : pandas.DataFrame
            Raw Aurora data with datetime index and scattering coefficient columns.

        Returns
        -------
        pandas.DataFrame
            Quality-controlled Aurora data with invalid measurements masked.

        Notes
        -----
        Applies the following QC filters:
        1. Value range: Valid scattering coefficients between 0-2000 Mm^-1
        2. Physics consistency: Back-scattering must be less than total scattering
        3. Wavelength dependence: Blue > Green > Red (Rayleigh scattering principle)
        4. Time-based outlier detection: Uses 1-hour window for IQR-based filtering
        5. Complete record requirement: Requires values across all channels
        """
        _index = _df.index.copy()

        _df = _df.mask((_df <= 0) | (_df > 2000))

        _df = _df.loc[(_df['BB'] < _df['B']) & (_df['BG'] < _df['G']) & (_df['BR'] < _df['R'])]

        _df = _df.loc[(_df['B'] > _df['G']) & (_df['G'] > _df['R'])]

        # use IQR_QC
        _df = self.time_aware_IQR_QC(_df, time_window='1h')

        # Ensure temporal data representativeness (>50% data per hour)
        points_per_hour = Timedelta('1h') / Timedelta(self.meta['freq'])
        if points_per_hour > 0:
            hourly_counts = _df.count(axis=1).resample('1h').size()
            hourly_counts = hourly_counts.reindex(_df.index, method='ffill')
            _df = _df.mask(hourly_counts < points_per_hour * 0.5)

        # make sure all columns have values, otherwise set to nan
        return _df.dropna(how='any').reindex(_index)
