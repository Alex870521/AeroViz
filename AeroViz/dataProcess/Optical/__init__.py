from ..core import Writer, run_process

__all__ = ['Optical']


class Optical(Writer):

    @run_process('Optical - scaCoe', 'scaCoe')
    def scaCoe(self, df_sca, instru, specified_band):
        from ._scattering import _scaCoe

        out = _scaCoe(df_sca, instru=instru, specified_band=[550] if specified_band is None else specified_band)

        return self, out

    @run_process('Optical - absCoe', 'absCoe')
    def absCoe(self, df_ae33, instru, specified_band):
        from ._absorption import _absCoe

        out = _absCoe(df_ae33, instru=instru, specified_band=[550] if specified_band is None else specified_band)

        return self, out

    @run_process('Optical - basic', 'opt_basic')
    def basic(self, df_sca, df_abs, df_mass=None, df_no2=None, df_temp=None):
        from ._extinction import _basic

        out = _basic(df_sca, df_abs, df_mass, df_no2, df_temp)

        return self, out

    @run_process('Optical - Mie', 'Mie')
    def Mie(self, df_psd, df_m, wave_length=550):
        from ._mie import _mie

        out = _mie(df_psd, df_m, wave_length)

        return self, out

    @run_process('Optical - IMPROVE', 'IMPROVE')
    def IMPROVE(self, df_mass, df_RH, method='revised'):
        # _fc = __import__(f'_IMPROVE._{method}')
        from ._IMPROVE import _revised

        out = _revised(df_mass, df_RH)

        return self, out
