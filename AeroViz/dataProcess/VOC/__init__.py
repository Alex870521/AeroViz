from ..core import Writer, run_process

__all__ = ['VOC']


class VOC(Writer):

    @run_process('VOC - basic', 'voc_basic')
    def VOC_basic(self, _df_voc):
        from ._potential_par import _basic

        out = _basic(_df_voc)

        return self, out
