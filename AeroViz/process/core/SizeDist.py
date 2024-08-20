from typing import Literal

import numpy as np
from pandas import DataFrame

__all__ = ['SizeDist']


class SizeDist:
    """
    Attributes
    ----------

    _data: DataFrame
        The processed PSD data stored as a pandas DataFrame.

    _dp: ndarray
        The array of particle diameters from the PSD data.

    _dlogdp: ndarray
        The array of logarithmic particle diameter bin widths.

    _index: DatetimeIndex
        The index of the DataFrame representing time.

    _state: str
        The state of particle size distribution data.

    Methods
    -------
    number()
        Calculate number distribution properties.

    surface(filename='PSSD_dSdlogdp.csv')
        Calculate surface distribution properties.

    volume(filename='PVSD_dVdlogdp.csv')
        Calculate volume distribution properties.

    """

    def __init__(self,
                 data: DataFrame,
                 state: Literal['dN', 'ddp', 'dlogdp'] = 'dlogdp',
                 weighting: Literal['n', 's', 'v', 'ext_in', 'ext_ex'] = 'n'
                 ):
        self._data = data
        self._dp = np.array(self._data.columns, dtype=float)
        self._dlogdp = np.full_like(self._dp, 0.014)
        self._index = self._data.index.copy()
        self._state = state
        self._weighting = weighting

    @property
    def data(self) -> DataFrame:
        return self._data

    @property
    def dp(self) -> np.ndarray:
        return self._dp

    @dp.setter
    def dp(self, new_dp: np.ndarray):
        self._dp = new_dp

    @property
    def dlogdp(self) -> np.ndarray:
        return self._dlogdp

    @dlogdp.setter
    def dlogdp(self, new_dlogdp: np.ndarray):
        self._dlogdp = new_dlogdp

    @property
    def index(self):
        return self._index

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        if value not in ['dN', 'dlogdp', 'ddp']:
            raise ValueError("state must be 'dlogdp' or 'ddp'")
        self._state = value

    @property
    def weighting(self):
        return self._weighting
