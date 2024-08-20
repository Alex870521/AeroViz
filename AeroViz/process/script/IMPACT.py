from pathlib import Path

from pandas import DataFrame, read_csv, concat

from AeroViz.process.core import DataProc
from AeroViz.tools.datareader import DataReader


class ImpactProc(DataProc):
    """
    A class for processing impact data.

    Parameters:
    -----------
    reset : bool, optional
        If True, resets the processing. Default is False.
    save_filename : str or Path, optional
        The name or path to save the processed data. Default is 'IMPACT.csv'.

    Methods:
    --------
    process_data(reset: bool = False, save_filename: str | Path = 'IMPACT.csv') -> DataFrame:
        Process data and save the result.

    save_data(data: DataFrame, save_filename: str | Path):
        Save processed data to a file.

    Attributes:
    -----------
    DEFAULT_PATH : Path
        The default path for data files.

    Examples:
    ---------
    >>> df_custom = ImpactProc().process_data(reset=True, save_filename='custom_file.csv')
    """

    def __init__(self, file_paths: list[Path | str] = None):
        super().__init__()
        self.file_paths = [Path(fp) for fp in file_paths]

    def process_data(self, reset: bool = False, save_file: Path | str = None) -> DataFrame:
        save_file = Path(save_file)
        if save_file.exists() and not reset:
            return read_csv(save_file, parse_dates=['Time'], index_col='Time')
        else:
            _df = concat([DataReader(file) for file in self.file_paths], axis=1)
            _df.to_csv(save_file)
            return _df
