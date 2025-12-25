from ..core import Writer, run_process

from ._size_dist import SizeDist

__all__ = ['SizeDistr', 'SizeDist']


class SizeDistr(Writer):

    # basic
    @run_process('SizeDistr - basic', 'distr_basic')
    def basic(self, df, hybrid_bin_start_loc=None, unit='nm', bin_range=(0, 20000), input_type='norm'):
        """
        Process particle size distribution data.

        Parameters
        ----------
        df : DataFrame
            Raw particle size distribution data.
        hybrid_bin_start_loc : int, optional
            Column index where bin spacing changes (for hybrid instruments).
        unit : {'nm', 'um'}, default='nm'
            Unit of particle diameter.
        bin_range : tuple, default=(0, 20000)
            Size range to include (min, max).
        input_type : {'norm', 'raw'}, default='norm'
            Whether input is normalized (dN/dlogDp) or raw (dN).

        Returns
        -------
        dict
            Distributions and statistics for each size mode.
        """
        import numpy as np

        # Prepare data
        data = df.copy()
        data.columns = data.keys().to_numpy(float)

        # Filter by size range
        cols = data.keys()[(data.keys() >= bin_range[0]) & (data.keys() <= bin_range[-1])]
        data = data[cols].copy()

        dp = data.keys().to_numpy()

        # Calculate dlogdp
        if hybrid_bin_start_loc is None:
            dlog_dp = np.full(dp.size, np.diff(np.log10(dp)).mean())
        else:
            dlog_dp = np.ones(dp.size)
            dlog_dp[:hybrid_bin_start_loc] = np.diff(np.log10(dp[:hybrid_bin_start_loc])).mean()
            dlog_dp[hybrid_bin_start_loc:] = np.diff(np.log10(dp[hybrid_bin_start_loc:])).mean()

        # Handle normalization
        if input_type == 'norm':
            data_norm = data
        else:
            data_norm = data / dlog_dp

        # Create SizeDist and calculate
        psd = SizeDist(data_norm, state='dlogdp', weighting='n')
        psd.dlogdp = dlog_dp

        out = psd.mode_statistics(unit=unit)

        # Rename for backward compatibility
        out['other'] = out.pop('statistics')

        return self, out

    # merge
    @run_process('SizeDistr - merge_SMPS_APS_v4', 'distr_merge')
    def merge_SMPS_APS_v4(self, df_smps, df_aps, df_pm25, aps_unit='um',
                          smps_overlap_lowbound=500, aps_fit_highbound=1000, dndsdv_alg=True,
                          times_range=(0.8, 1.25, .05)):
        from .merge import merge_v4

        out = merge_v4(df_smps, df_aps, df_pm25, aps_unit, smps_overlap_lowbound, aps_fit_highbound, dndsdv_alg,
                       times_range)

        return self, out

    # merge
    @run_process('SizeDistr - merge_SMPS_APS_v3', 'distr_merge')
    def merge_SMPS_APS_v3(self, df_smps, df_aps, aps_unit='um',
                          smps_overlap_lowbound=500, aps_fit_highbound=1000, dndsdv_alg=True):
        from .merge import merge_v3

        out = merge_v3(df_smps, df_aps, aps_unit, smps_overlap_lowbound, aps_fit_highbound, dndsdv_alg)

        return self, out

    # merge
    @run_process('SizeDistr - merge_SMPS_APS_v2', 'distr_merge')
    def merge_SMPS_APS_v2(self, df_smps, df_aps, aps_unit='um',
                          smps_overlap_lowbound=500, aps_fit_highbound=1000):
        from .merge import merge_v2

        out = merge_v2(df_smps, df_aps, aps_unit, smps_overlap_lowbound, aps_fit_highbound)

        return self, out

    # merge
    @run_process('SizeDistr - merge_SMPS_APS_v1', 'distr_merge')
    def merge_SMPS_APS(self, df_smps, df_aps, aps_unit='um', shift_mode='mobility',
                       smps_overlap_lowbound=523, aps_fit_highbound=800):
        from .merge import merge_v1

        out = merge_v1(df_smps, df_aps, aps_unit, shift_mode, smps_overlap_lowbound, aps_fit_highbound)

        return self, out

    # Distribution calculations
    @run_process('SizeDistr - distributions', 'distr_calc')
    def distributions(self, df_pnsd):
        """
        Calculate number, surface, and volume distributions with properties.

        Parameters
        ----------
        df_pnsd : DataFrame
            Particle number size distribution data.

        Returns
        -------
        dict
            Dictionary with 'number', 'surface', 'volume', and 'properties' DataFrames.
        """
        from pandas import concat

        psd = SizeDist(df_pnsd, weighting='n')

        number = psd.data
        surface = psd.to_surface()
        volume = psd.to_volume()

        # Calculate properties for each distribution type
        props_n = psd.properties()
        props_s = SizeDist(surface, weighting='s').properties()
        props_v = SizeDist(volume, weighting='v').properties()

        out = {
            'number': number,
            'surface': surface,
            'volume': volume,
            'properties': concat([props_n, props_s, props_v], axis=1)
        }

        return self, out

    # Dry PSD
    @run_process('SizeDistr - dry_psd', 'distr_dry')
    def dry_psd(self, df_pnsd, df_gRH, uniform=True):
        """
        Convert ambient PSD to dry PSD.

        Parameters
        ----------
        df_pnsd : DataFrame
            Particle number size distribution data.
        df_gRH : DataFrame
            DataFrame with 'gRH' column (growth factor).
        uniform : bool, default=True
            Whether to apply uniform growth factor.

        Returns
        -------
        DataFrame
            Dry particle size distribution.
        """
        psd = SizeDist(df_pnsd)
        out = psd.to_dry(df_gRH, uniform=uniform)

        return self, out

    # Extinction distribution
    @run_process('SizeDistr - extinction', 'distr_ext')
    def extinction_distribution(self, df_pnsd, df_RI, method='internal', result_type='extinction'):
        """
        Calculate extinction distribution using Mie theory.

        Parameters
        ----------
        df_pnsd : DataFrame
            Particle number size distribution (dN/dlogDp).
        df_RI : DataFrame
            Refractive index data (n, k columns).
        method : {'internal', 'external', 'core_shell', 'sensitivity'}, default='internal'
            Mixing method for Mie calculation.
        result_type : {'extinction', 'scattering', 'absorption'}, default='extinction'
            Type of optical property.

        Returns
        -------
        dict
            - 'distribution': Extinction size distribution (Mm⁻¹)
            - 'properties': Statistical properties (GMD, GSD, mode)
        """
        psd = SizeDist(df_pnsd)
        ext_dist = psd.to_extinction(df_RI, method=method, result_type=result_type)
        ext_props = SizeDist(ext_dist, weighting=f'ext_{method[:2]}').properties()

        out = {
            'distribution': ext_dist,
            'properties': ext_props
        }

        return self, out

    # Full extinction analysis (internal + external)
    @run_process('SizeDistr - extinction_full', 'distr_ext_full')
    def extinction_full(self, df_pnsd, df_RI, result_type='extinction'):
        """
        Calculate extinction using both internal and external mixing.

        Parameters
        ----------
        df_pnsd : DataFrame
            Particle number size distribution (dN/dlogDp).
        df_RI : DataFrame
            Refractive index data with volume ratios.
        result_type : {'extinction', 'scattering', 'absorption'}, default='extinction'
            Type of optical property.

        Returns
        -------
        dict
            - 'internal': Internal mixing distribution
            - 'external': External mixing distribution
            - 'properties_internal': Internal properties
            - 'properties_external': External properties
        """
        psd = SizeDist(df_pnsd)

        ext_internal = psd.to_extinction(df_RI, method='internal', result_type=result_type)
        ext_external = psd.to_extinction(df_RI, method='external', result_type=result_type)

        out = {
            'internal': ext_internal,
            'external': ext_external,
            'properties_internal': SizeDist(ext_internal, weighting='ext_in').properties(),
            'properties_external': SizeDist(ext_external, weighting='ext_ex').properties()
        }

        return self, out
