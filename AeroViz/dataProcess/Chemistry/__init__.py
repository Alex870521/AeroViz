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

    # Partition
    @run_process('Chemistry -  Partition', 'partition')
    def Partition(self, *df_chem, nam_lst=None):
        from ._partition import _basic

        if nam_lst is None:
            nam_lst = ['NH4+', 'SO42-', 'NO3-', 'Cl-', 'NO2', 'HNO3', 'SO2', 'NH3', 'HCl', 'temp']

        out = _basic(df_chem, nam_lst=nam_lst)

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

    # TEOM
    @run_process('Chemistry - TEOM basic', 'teom_basic')
    def TEOM_basic(self, df_teom, df_check=None):
        from ._teom import _basic

        out = _basic(df_teom, df_check)

        return self, out
