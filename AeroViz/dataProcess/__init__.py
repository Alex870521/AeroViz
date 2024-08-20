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
