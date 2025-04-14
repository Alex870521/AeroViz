from pathlib import Path

from .Chemistry import Chemistry
from .Optical import Optical
from .SizeDistr import SizeDistr
from .VOC import VOC

__all__ = ['DataProcess']


def DataProcess(method: str,
                path_out: Path,
                excel: bool = False,
                csv: bool = True,
                ):
    """Factory function to create appropriate data processing module based on method type.

    This function serves as an entry point for different data processing methods in AeroViz.
    It returns an instance of the appropriate processor class based on the specified method.

    Parameters
    ----------
    method : str
        The processing method to use. Must be one of: 'Chemistry', 'Optical',
        'SizeDistr', or 'VOC'.
    path_out : Path
        Path where processed output files will be saved.
    excel : bool, default=False
        Whether to save output in Excel format.
    csv : bool, default=True
        Whether to save output in CSV format.

    Returns
    -------
    object
        Instance of the selected processing class initialized with the provided parameters.

    Raises
    ------
    ValueError
        If the specified method name is not in the supported methods list.

    Examples
    --------
    >>> from AeroViz import DataProcess
    >>> from pathlib import Path
    >>> processor = DataProcess(method='Optical', path_out=Path('./results'))
    """
    # Mapping of method names to their respective classes
    method_class_map = {
        'Chemistry': Chemistry,
        'Optical': Optical,
        'SizeDistr': SizeDistr,
        'VOC': VOC
    }

    if method not in method_class_map.keys():
        raise ValueError(f"Method name '{method}' is not valid. \nMust be one of: {list(method_class_map.keys())}")

    writer_module = method_class_map[method](
        path_out=path_out,
        excel=excel,
        csv=csv
    )

    return writer_module
