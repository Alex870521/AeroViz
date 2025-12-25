from ..core import Writer, run_process

__all__ = ['Chemistry']


class Chemistry(Writer):
    # Reconstruction
    @run_process('Chemistry - reconstruction basic', 'reconstrc_basic')
    def ReConstrc_basic(self, *df_chem, df_ref=None, df_water=None, df_density=None, nam_lst=None):
        from ._mass_volume import _basic

        if nam_lst is None:
            nam_lst = ['NH4+', 'SO42-', 'NO3-', 'Fe', 'Na+', 'OC', 'EC']

        out = _basic(df_chem, df_ref, df_water, df_density, nam_lst=nam_lst)

        return self, out

    # Partition (Gas-Particle Partitioning Ratios)
    @run_process('Chemistry - Partition', 'partition')
    def Partition(self, df_data):
        """
        Calculate gas-particle partitioning ratios (SOR, NOR, NTR, epsilon).

        Parameters
        ----------
        df_data : DataFrame
            Data containing particle and gas concentrations (μg/m³).
            Required: 'temp' column (temperature in Celsius)
            Optional species (at least one pair needed):
            - SO42-, SO2 : for SOR
            - NO3-, NO2 : for NOR
            - NH4+, NH3 : for NTR
            - Cl-, HCl : for chloride partitioning

        Returns
        -------
        DataFrame
            Partitioning ratios: SOR, NOR, NOR_2, NTR, epls_* columns.

        Notes
        -----
        - SOR > 0.1 indicates secondary sulfate formation
        - Values near 1.0: particle phase dominant
        - Values near 0.0: gas phase dominant
        """
        from ._calculate import partition_ratios

        out = partition_ratios(df_data)

        return self, out

    # ISOROPIA
    @run_process('Chemistry - ISOROPIA', 'isoropia')
    def ISOROPIA(self, *df_chem, nam_lst=None):
        from ._isoropia import _basic

        if nam_lst is None:
            nam_lst = ['Na+', 'SO42-', 'NH4+', 'NO3-', 'Cl-', 'Ca2+',
                       'K+', 'Mg2+', 'NH3', 'HNO3', 'HCl', 'RH', 'temp']

        if self.path_out is None:
            raise ValueError('Please Input "path_out" !!')

        out = _basic(df_chem, self.path_out, nam_lst=nam_lst)

        return self, out

    # OCEC
    @run_process('Chemistry - OC/EC basic', 'ocec_basic')
    def OCEC_basic(self, df_lcres, df_mass=None, ocec_ratio=None, ocec_ratio_month=1, hr_lim=200,
                   least_square_range=(0.1, 2.5, 0.1), WISOC_OC_range=(0.2, 0.7, 0.01), ):
        from ._ocec import _basic

        out = _basic(df_lcres, df_mass, ocec_ratio, ocec_ratio_month, hr_lim, least_square_range, WISOC_OC_range)

        return self, out

    # Volume Average Mixing
    @run_process('Chemistry - VAM', 'vam')
    def volume_average_mixing(self, df_volume, df_alwc=None):
        """
        Calculate volume-average refractive index and growth factor.

        Parameters
        ----------
        df_volume : DataFrame
            Volume data with AS_volume, AN_volume, etc. and total_dry columns.
        df_alwc : DataFrame, optional
            Aerosol liquid water content data.

        Returns
        -------
        DataFrame
            RI data with n_dry, k_dry, n_amb, k_amb, gRH columns.
        """
        from ._calculate import volume_average_mixing

        out = volume_average_mixing(df_volume, df_alwc)

        return self, out

    # Kappa calculation
    @run_process('Chemistry - kappa', 'kappa')
    def kappa(self, df_data, diameter=0.5):
        """
        Calculate hygroscopicity parameter kappa.

        Parameters
        ----------
        df_data : DataFrame
            Data containing gRH, AT (temperature in C), and RH (%).
        diameter : float, default=0.5
            Particle dry diameter in micrometers.

        Returns
        -------
        DataFrame
            Kappa values.
        """
        from ._calculate import kappa_calculate

        out = kappa_calculate(df_data, diameter)

        return self, out

    # gRH calculation
    @run_process('Chemistry - gRH', 'gRH')
    def gRH(self, df_volume, df_alwc):
        """
        Calculate hygroscopic growth factor.

        Parameters
        ----------
        df_volume : DataFrame
            Volume data with 'total_dry' column.
        df_alwc : DataFrame
            Aerosol liquid water content with 'ALWC' column.

        Returns
        -------
        DataFrame
            Growth factor data.
        """
        from ._calculate import gRH_calculate

        out = gRH_calculate(df_volume, df_alwc)

        return self, out
