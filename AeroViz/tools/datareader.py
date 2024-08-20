from abc import ABC, abstractmethod
from pathlib import Path

from pandas import read_csv, read_json, read_excel, DataFrame


class FileHandler(ABC):
    """ An abstract base class for reading data files with different extensions (.csv, .json, .xls, .xlsx). """

    @abstractmethod
    def read_data(self, file_path: Path) -> DataFrame:
        pass


class CsvFileHandler(FileHandler):
    def read_data(self, file_path: Path) -> DataFrame:
        return read_csv(file_path, na_values=('E', 'F', '-', '_', '#', '*'), index_col=0, parse_dates=True,
                        low_memory=False)


class JsonFileHandler(FileHandler):
    def read_data(self, file_path: Path) -> DataFrame:
        return read_json(file_path)


class ExcelFileHandler(FileHandler):
    def read_data(self, file_path: Path) -> DataFrame:
        return read_excel(file_path, index_col=0, parse_dates=True, )


class DataReaderFactory:
    _handler_mapping = {
        '.csv': CsvFileHandler(),
        '.json': JsonFileHandler(),
        '.xls': ExcelFileHandler(),
        '.xlsx': ExcelFileHandler(),
    }

    @staticmethod
    def create_handler(file_extension: str) -> FileHandler:
        reader_class = DataReaderFactory._handler_mapping.get(file_extension)
        if reader_class is None:
            raise ValueError(f"Unsupported file format: {file_extension}")
        return reader_class


class DataReader:
    """
    A class for reading data files with different extensions (.csv, .json, .xls, .xlsx).

    Parameters
    ----------
        filename (Path | str): The name of the file to be read or the Path of the file.

    Returns
    -------
        pandas.DataFrame: data

    Examples
    --------
    >>> psd = DataReader(Path(...))
    """

    def __new__(cls, file_path: Path | str) -> DataFrame:
        file_path = Path(file_path)
        return DataReaderFactory.create_handler(file_path.suffix.lower()).read_data(file_path)
