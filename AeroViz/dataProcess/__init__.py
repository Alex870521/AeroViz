import warnings
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
    """Factory function (DEPRECATED) — use the top-level functions instead.

    .. deprecated::
        ``DataProcess(...)`` will be removed in a future release. Each method
        on the returned Writer instance now has a direct top-level function
        equivalent. Migration cheatsheet::

            DataProcess('Chemistry', ...).ReConstrc_basic(df, ...)
              → from AeroViz import reconstruct_mass
                reconstruct_mass(df, ...)

            DataProcess('Optical', ...).IMPROVE(df_mass, df_RH, method='revised')
              → from AeroViz import improve
                improve(df_mass, df_RH, method='revised')

            DataProcess('Optical', ...).Mie(df_psd, df_m)
              → from AeroViz import mie
                mie(df_psd, df_m)

            DataProcess('SizeDistr', ...).merge_SMPS_APS_v4(df_smps, df_aps, df_pm25)
              → from AeroViz import merge_psd
                merge_psd(df_smps, df_aps, df_pm25=df_pm25, version=4)

            DataProcess('VOC', ...).VOC_basic(df_voc)
              → from AeroViz import voc_potentials
                voc_potentials(df_voc)

        Sub-namespaces (``AeroViz.chemistry``, ``AeroViz.optical``,
        ``AeroViz.size``, ``AeroViz.voc``) are also supported. The new
        functions return DataFrames/dicts directly — pass ``df.to_csv(...)``
        yourself if you want files written.

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
    >>> processor = DataProcess(method='Optical', path_out=Path('./results'))  # deprecated
    """
    warnings.warn(
        "DataProcess(...) is deprecated and will be removed in a future "
        "release. Use the top-level functions instead, e.g. "
        "`from AeroViz import improve, mie, reconstruct_mass, merge_psd, ...`. "
        "See the function docstring for a migration cheatsheet.",
        DeprecationWarning,
        stacklevel=2,
    )
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
