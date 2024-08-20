from abc import ABC, abstractmethod
from pathlib import Path

from pandas import DataFrame

__all__ = ['DataProc']


class DataProc(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def process_data(self,
                     reset: bool = False,
                     save_filename: str | Path = None
                     ) -> DataFrame:
        """ Implementation of processing data """
        pass
