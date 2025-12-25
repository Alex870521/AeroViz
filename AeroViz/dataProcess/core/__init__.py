import functools
import pickle as pkl
import warnings
from datetime import datetime as dtm
from pathlib import Path

from pandas import concat

# Ensure all deprecation warnings are displayed
warnings.filterwarnings('always', category=DeprecationWarning)
warnings.filterwarnings('always', category=FutureWarning)


class Writer:
    """
    Base class for data output management with various file format support.

    This class provides functionality to save processed data in multiple formats,
    including pickle, Excel, and CSV. It handles file permission issues gracefully.

    Parameters
    ----------
    path_out : str or Path, optional
        Directory path where output files will be saved
    excel : bool, default=True
        Whether to save outputs as Excel files
    csv : bool, default=False
        Whether to save outputs as CSV files
    """

    def __init__(self, path_out=None, excel=True, csv=False):
        self.path_out = Path(path_out) if path_out is not None else path_out
        self.excel = excel
        self.csv = csv

    @staticmethod
    def pre_process(_out):
        """
        Prepare data for output by ensuring proper index naming.

        Parameters
        ----------
        _out : DataFrame or dict of DataFrames
            Data to be prepared for output

        Returns
        -------
        DataFrame or dict of DataFrames
            Processed data with properly named index
        """
        if isinstance(_out, dict):
            for _ky, _df in _out.items():
                _df.index.name = 'time'
        else:
            _out.index.name = 'time'

        return _out

    def save_out(self, _nam, _out):
        """
        Save processed data to disk in specified formats.

        Handles various output formats (pickle, Excel, CSV) and manages file
        permission errors by prompting the user to close open files.

        Parameters
        ----------
        _nam : str
            Base name for the output files
        _out : DataFrame or dict of DataFrames
            Data to be saved
        """
        _check = True
        while _check:
            try:
                if self.path_out is not None:
                    self.path_out.mkdir(exist_ok=True, parents=True)
                    with (self.path_out / f'{_nam}.pkl').open('wb') as f:
                        pkl.dump(_out, f, protocol=pkl.HIGHEST_PROTOCOL)

                    if self.excel:
                        from pandas import ExcelWriter
                        with ExcelWriter(self.path_out / f'{_nam}.xlsx') as f:
                            if type(_out) == dict:
                                for _key, _val in _out.items():
                                    _val.to_excel(f, sheet_name=f'{_key}')
                            else:
                                _out.to_excel(f, sheet_name=f'{_nam}')

                    if self.csv:
                        if isinstance(_out, dict):
                            _path_out = self.path_out / _nam
                            _path_out.mkdir(exist_ok=True, parents=True)

                            for _key, _val in _out.items():
                                _val.to_csv(_path_out / f'{_key}.csv')
                        else:
                            _out.to_csv(self.path_out / f'{_nam}.csv')

                _check = False

            except PermissionError as _err:
                print('\n', _err)
                input('\t\t\33[41m Please Close The File And Press "Enter" \33[0m\n')


def run_process(*_ini_set: str):
    """
    Decorator for standardizing data processing functions.

    This decorator wraps processing functions to provide consistent logging,
    output formatting, and file saving behavior.

    Parameters
    ----------
    *_ini_set : str
        Two strings: process display name and output file name

    Returns
    -------
    callable
        Decorated function that handles the entire process flow

    Examples
    --------
    @run_process('Process Description', 'output_filename')
    def process_function(self, data):
        # Process data
        return self, processed_data
    """

    def _decorator(_prcs_fc):
        def _wrap(*arg, **kwarg):
            _fc_name, _nam = _ini_set

            if kwarg.get('nam') is not None:
                _nam = kwarg.pop('nam')

            print(f"\n\t{dtm.now().strftime('%m/%d %X')} : Process \033[92m{_fc_name}\033[0m -> {_nam}")

            _class, _out = _prcs_fc(*arg, **kwarg)
            _out = _class.pre_process(_out)

            _class.save_out(_nam, _out)

            return _out

        return _wrap

    return _decorator


def union_index(*_df_arg):
    """
    Reindex multiple DataFrames to a common union index.

    Creates a unified index from all input DataFrames and reindexes each
    DataFrame to this common index, handling None values appropriately.

    Parameters
    ----------
    *_df_arg : DataFrame
        One or more pandas DataFrames to reindex

    Returns
    -------
    list
        List of reindexed DataFrames in the same order as input
    """
    _idx = concat(_df_arg, axis=1).index

    return [_df.reindex(_idx) if _df is not None else None for _df in _df_arg]


def validate_inputs(df, required_columns, func_name, column_descriptions=None):
    """
    Validate that DataFrame contains all required columns.

    Parameters
    ----------
    df : DataFrame
        Input DataFrame to validate.
    required_columns : list
        List of required column names.
    func_name : str
        Name of the calling function (for error message).
    column_descriptions : dict, optional
        Dictionary mapping column names to descriptions.
        Example: {'AS': 'Ammonium Sulfate 硫酸銨 (ug/m3)'}

    Raises
    ------
    ValueError
        If DataFrame is None/empty or any required columns are missing.

    Examples
    --------
    >>> REQUIRED = ['AS', 'AN', 'OM']
    >>> DESCRIPTIONS = {'AS': 'Ammonium Sulfate', 'AN': 'Ammonium Nitrate', 'OM': 'Organic Matter'}
    >>> validate_inputs(df, REQUIRED, 'my_function', DESCRIPTIONS)
    """
    if df is None:
        raise ValueError(
            f"\n{func_name}() 輸入資料為 None！\n"
            f"  需要欄位: {required_columns}"
        )

    if hasattr(df, 'empty') and df.empty:
        raise ValueError(
            f"\n{func_name}() 輸入資料為空！\n"
            f"  需要欄位: {required_columns}"
        )

    existing_columns = set(df.columns)
    required_set = set(required_columns)
    missing = required_set - existing_columns

    if missing:
        error_msg = (
            f"\n{func_name}() 缺少必要欄位！\n"
            f"  需要欄位: {required_columns}\n"
            f"  缺少欄位: {sorted(missing)}\n"
            f"  現有欄位: {sorted(existing_columns)}"
        )

        if column_descriptions:
            error_msg += "\n\n欄位說明:"
            for col in required_columns:
                if col in column_descriptions:
                    error_msg += f"\n  {col:6s} - {column_descriptions[col]}"

        raise ValueError(error_msg)


def deprecated(message):
    """
    Decorator to mark functions as deprecated.

    This decorator adds a warning message when a deprecated function is called,
    informing users about the deprecation and suggesting alternatives.

    Parameters
    ----------
    message : str
        Message explaining why the function is deprecated and what to use instead

    Returns
    -------
    callable
        Decorator function that adds deprecation warnings

    Examples
    --------
    @deprecated("Use new_function() instead.")
    def old_function():
        # Function implementation
        pass
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated and will be removed in a future version. {message}",
                category=DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)

        return wrapper

    return decorator
