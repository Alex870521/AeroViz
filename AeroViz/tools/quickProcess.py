from pathlib import Path
from datetime import datetime
from typing import Optional, Union

from pandas import DataFrame

from AeroViz import RawDataReader, DataProcess


def quick_process(
    instrument: str,
    path: Union[str, Path],
    start: datetime,
    end: datetime,
    mean_freq: str = '1h',
    output_path: Optional[Path] = None,
    excel: bool = False,
    csv: bool = True,
    **kwargs
) -> dict[str, DataFrame]:
    """
    A combined function that integrates the functionality of RawDataReader and DataProcess
    to quickly process instrument data in one step.

    Parameters
    ----------
    instrument : str
        Instrument name, e.g., 'AE33', 'NEPH', 'SMPS', etc.
    path : str or Path
        Path to the data files
    start : datetime
        Start time
    end : datetime
        End time
    mean_freq : str, default='1h'
        Time frequency for data averaging
    output_path : Path, optional
        Output file path. If not specified, uses input path
    excel : bool, default=False
        Whether to output Excel files
    csv : bool, default=True
        Whether to output CSV files
    **kwargs : dict
        Additional parameters passed to RawDataReader

    Returns
    -------
    Dict[str, DataFrame]
        Dictionary containing processed data, with keys as data types
        and values as corresponding DataFrames

    Examples
    --------
    >>> from datetime import datetime
    >>> from pathlib import Path
    >>> from AeroViz.tools import quick_process
    >>> 
    >>> data = quick_process(
    ...     instrument='AE33',
    ...     path=Path('/path/to/data'),
    ...     start=datetime(2024, 1, 1),
    ...     end=datetime(2024, 12, 31),
    ...     mean_freq='1h'
    ... )
    """
    # 如果没有指定输出路径，使用输入路径
    if output_path is None:
        output_path = Path(path) / f"{instrument}_outputs"
    
    # 首先使用 RawDataReader 读取数据
    raw_data = RawDataReader(
        instrument=instrument,
        path=path,
        start=start,
        end=end,
        mean_freq=mean_freq,
        **kwargs
    )
    
    # 根据不同的仪器类型选择相应的处理方法
    method_map = {
        'AE33': 'Optical',
        'NEPH': 'Optical',
        'SMPS': 'SizeDistr',
        'APS': 'SizeDistr',
        'GRIMM': 'SizeDistr',
        'ACSM': 'Chemistry',
        'AMS': 'Chemistry',
        'PILS': 'Chemistry',
        'VOC': 'VOC'
    }
    
    # 获取处理方法
    process_method = method_map.get(instrument)
    if process_method is None:
        return {'raw': raw_data}
    
    # 使用 DataProcess 进行进一步处理
    processor = DataProcess(
        method=process_method,
        path_out=output_path,
        excel=excel,
        csv=csv
    )
    
    # 根据不同的处理方法调用相应的基本处理函数
    if process_method == 'Optical':
        if instrument == 'AE33':
            processed_data = processor.absCoe(raw_data, instrument, specified_band=[550])
        elif instrument == 'NEPH':
            processed_data = processor.scaCoe(raw_data, instrument, specified_band=[550])
    elif process_method == 'SizeDistr':
        processed_data = processor.basic(raw_data, hybrid_bin_start_loc=None)
    elif process_method == 'Chemistry':
        processed_data = processor.ReConstrc_basic(raw_data)
    elif process_method == 'VOC':
        processed_data = processor.VOC_basic(raw_data)
    
    return {
        'raw': raw_data,
        'processed': processed_data
    } 