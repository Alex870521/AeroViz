from pandas import to_datetime, read_csv, to_numeric

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    """ Nephelometer (NEPH) Data Reader

    A specialized reader for integrating nephelometer data files, which measure
    light scattering properties of aerosols at multiple wavelengths.

    See full documentation at docs/source/instruments/NEPH.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'NEPH'

    def _raw_reader(self, file):
        """
        Read and parse raw Nephelometer data files.

        Parameters
        ----------
        file : Path or str
            Path to the Nephelometer data file.

        Returns
        -------
        pandas.DataFrame
            Processed Nephelometer data with datetime index and scattering coefficient columns.
        """
        _df = read_csv(file, header=None, names=range(11))

        _df_grp = _df.groupby(0)

        # T : time
        _idx_tm = to_datetime(
            _df_grp.get_group('T')[[1, 2, 3, 4, 5, 6]]
            .map(lambda x: f"{int(x):02d}")
            .agg(''.join, axis=1),
            format='%Y%m%d%H%M%S'
        )

        # D : data
        # col : 3~8 B G R BB BG BR
        # 1e6
        try:
            _df_dt = _df_grp.get_group('D')[[1, 2, 3, 4, 5, 6, 7, 8]].set_index(_idx_tm)

            try:
                _df_out = (_df_dt.groupby(1).get_group('NBXX')[[3, 4, 5, 6, 7, 8]] * 1e6).reindex(_idx_tm)
            except KeyError:
                _df_out = (_df_dt.groupby(1).get_group('NTXX')[[3, 4, 5, 6, 7, 8]] * 1e6).reindex(_idx_tm)

            _df_out.columns = ['B', 'G', 'R', 'BB', 'BG', 'BR']
            _df_out.index.name = 'Time'

            # Y : state
            # col : 5 RH
            _df_st = _df_grp.get_group('Y')
            _df_out['RH'] = _df_st[5].values
            _df_out['status'] = _df_st[9].values

            _df_out.mask(_df_out['status'] != 0)  # 0000 -> numeric to 0

            _df = _df_out[['B', 'G', 'R', 'BB', 'BG', 'BR', 'RH']].apply(to_numeric, errors='coerce')

            return _df.loc[~_df.index.duplicated() & _df.index.notna()]

        except ValueError:  # Define valid groups and find invalid indices
            invalid_indices = _df[~_df[0].isin({'B', 'G', 'R', 'D', 'T', 'Y', 'Z'})].index
            self.logger.warning(
                f"\tInvalid values in {file.name}: {', '.join(f'{_}:{_df.at[_, 0]}' for _ in invalid_indices)}."
                f" Skipping file.")

            return None

    def _QC(self, _df):
        """
        Perform quality control on Nephelometer data.

        Parameters
        ----------
        _df : pandas.DataFrame
            Raw Nephelometer data with datetime index and scattering coefficient columns.

        Returns
        -------
        pandas.DataFrame
            Quality-controlled Nephelometer data with invalid measurements masked.

        Notes
        -----
        Applies the following QC filters:
        1. Value range: Valid scattering coefficients between 0-2000 Mm^-1
        2. Physics consistency: Back-scattering must be less than total scattering
        3. Wavelength dependence: Blue > Green > Red (where applicable)
        4. Time-based outlier detection: Uses 1-hour window for IQR-based filtering
        5. Complete record requirement: Requires values across all channels
        """
        MDL_sensitivity = {'B': .1, 'G': .1, 'R': .3}

        _index = _df.index.copy()

        # remove negative value
        _df = _df.mask((_df <= 0) | (_df > 2000))

        # total scattering is larger than back scattering
        _df = _df.loc[(_df['BB'] < _df['B']) & (_df['BG'] < _df['G']) & (_df['BR'] < _df['R'])]

        # blue scattering is larger than green scattering, green scattering is larger than red scattering
        # due to the nephelometer's Green PMT in FS is already aged, this QC may delete too many data
        # _df = _df.loc[(_df['B'] > _df['G']) & (_df['G'] > _df['R'])]

        # use IQR_QC
        _df = self.time_aware_IQR_QC(_df, time_window='1h')

        # make sure all columns have values, otherwise set to nan
        return _df.dropna(how='any').reindex(_index)
