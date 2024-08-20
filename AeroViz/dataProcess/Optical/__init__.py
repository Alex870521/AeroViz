from ..core import _writter, _run_process

__all__ = [

    'Optical',

]


class Optical(_writter):

    ## scatter
    @_run_process('Optical - SAE', 'SAE')
    def SAE(self, df_sca):
        from ._scattering import _SAE

        out = _SAE(df_sca)

        return self, out

    ## absorption
    @_run_process('Optical - absCoe', 'absCoe')
    def absCoe(self, df_ae33, abs_band=[550]):
        from ._absorption import _absCoe

        out = _absCoe(df_ae33, abs_band)

        return self, out

    @_run_process('Optical - AAE', 'AAE')
    def AAE(self, df_abs):
        from ._absorption import _AAE

        out = _AAE(df_abs)

        return self, out

    ## extinction
    @_run_process('Optical - basic', 'opt_basic')
    def basic(self, df_abs, df_sca, df_ec=None, df_mass=None, df_no2=None):
        from ._extinction import _basic

        out = _basic(df_abs, df_sca, df_ec, df_mass, df_no2)

        return self, out

    @_run_process('Optical - Mie', 'Mie')
    def Mie(self, df_psd, df_m, wave_length=550):
        from ._mie import _mie

        out = _mie(df_psd, df_m, wave_length)

        return self, out

    @_run_process('Optical - IMPROVE', 'IMPROVE')
    def IMPROVE(self, df_mass, df_RH, method='revised'):
        # _fc = __import__(f'_IMPROVE._{method}')
        from ._IMPROVE import _revised

        out = _revised(df_mass, df_RH)

        return self, out
