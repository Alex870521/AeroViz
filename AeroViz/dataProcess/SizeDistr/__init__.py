from ..core import Writer, run_process

__all__ = ['SizeDistr']


class SizeDistr(Writer):

    # basic
    @run_process('SizeDistr - basic', 'distr_basic')
    def basic(self, df, hybrid_bin_start_loc=None, unit='nm', bin_range=(0, 20000), input_type='norm'):
        from ._size_distr import _basic

        out = _basic(df, hybrid_bin_start_loc, unit, bin_range, input_type)

        return self, out

    # merge
    @run_process('SizeDistr - merge_SMPS_APS_v4', 'distr_merge')
    def merge_SMPS_APS_v4(self, df_smps, df_aps, df_pm25, aps_unit='um',
                          smps_overlap_lowbound=500, aps_fit_highbound=1000, dndsdv_alg=True,
                          times_range=(0.8, 1.25, .05)):
        from ._merge_v4 import merge_SMPS_APS

        out = merge_SMPS_APS(df_smps, df_aps, df_pm25, aps_unit, smps_overlap_lowbound, aps_fit_highbound, dndsdv_alg,
                             times_range)

        return self, out

    # merge
    @run_process('SizeDistr - merge_SMPS_APS_v3', 'distr_merge')
    def merge_SMPS_APS_v3(self, df_smps, df_aps, aps_unit='um',
                          smps_overlap_lowbound=500, aps_fit_highbound=1000, dndsdv_alg=True):
        from ._merge_v3 import merge_SMPS_APS

        out = merge_SMPS_APS(df_smps, df_aps, aps_unit, smps_overlap_lowbound, aps_fit_highbound, dndsdv_alg)

        return self, out

    # merge
    @run_process('SizeDistr - merge_SMPS_APS_v2', 'distr_merge')
    def merge_SMPS_APS_v2(self, df_smps, df_aps, aps_unit='um',
                          smps_overlap_lowbound=500, aps_fit_highbound=1000):
        from ._merge_v2 import merge_SMPS_APS

        out = merge_SMPS_APS(df_smps, df_aps, aps_unit, smps_overlap_lowbound, aps_fit_highbound)

        return self, out

    # merge
    @run_process('SizeDistr - merge_SMPS_APS_v1', 'distr_merge')
    def merge_SMPS_APS(self, df_smps, df_aps, aps_unit='um', shift_mode='mobility',
                       smps_overlap_lowbound=523, aps_fit_highbound=800):
        from ._merge_v1 import _merge_SMPS_APS

        out = _merge_SMPS_APS(df_smps, df_aps, aps_unit, shift_mode, smps_overlap_lowbound, aps_fit_highbound)

        return self, out
