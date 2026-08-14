# Public AeroViz API.
#
# Two import styles are supported:
#
#   from AeroViz import RawDataReader, improve, mie         # flat aliases
#   from AeroViz import chemistry, optical, size, voc       # sub-namespaces
#   from AeroViz.optical import improve, mie                # explicit module
#
# Use whichever style suits your code; they all resolve to the same
# underlying implementations.

from AeroViz.rawDataReader import RawDataReader
from AeroViz.tools import DataBase, DataClassifier

# Sub-namespaces for the post-processing functions.
from AeroViz import chemistry, optical, size, voc

# Flat aliases — the most common top-level entry points.
from AeroViz.chemistry import (
    reconstruct_mass,
    split_oc_ec,
    partition_ratios,
    isoropia,
    volume_ri,
    kappa,
    growth_factor,
)
from AeroViz.optical import (
    optical_basic,
    mie,
    improve,
    gas_extinction,
    retrieve_ri,
    brown_carbon,
    # PyMieScatt-style additions
    mie_lognormal,
    mie_multimodal,
    scattering_function,
    scattering_function_sd,
    phase_matrix,
    nephelometer_truncation_correction,
    mie_core_shell,
    mie_core_shell_sd,
    iterative_inversion,
    iterative_inversion_sd,
    contour_intersection,
)
from AeroViz.size import (
    psd_stats,
    psd_distributions,
    merge_psd,
)
from AeroViz.voc import voc_potentials

# Legacy entry point (deprecated; will be removed in a future release).
# Prefer the top-level functions above.
from AeroViz.dataProcess import DataProcess


def __getattr__(name):
    """Lazily resolve `AeroViz.plot` (PEP 562).

    Plotting pulls in matplotlib, seaborn, cartopy, windrose, plotly and
    scikit-learn — none of which the reader / optical / size code needs. They
    now live behind the `plot` extra, so importing them eagerly here would make
    `import AeroViz` fail for anyone who installed the base package. Resolving
    on first access keeps `from AeroViz import plot` and `AeroViz.plot.xxx`
    working unchanged when the extra IS installed, and gives an actionable
    error when it is not.
    """
    if name == 'plot':
        import importlib
        try:
            module = importlib.import_module('AeroViz.plot')
        except ImportError as e:
            raise ImportError(
                "AeroViz.plot requires the plotting dependencies, which are not "
                "installed. Install them with:  pip install 'AeroViz[plot]'\n"
                f"(original error: {e})"
            ) from e
        globals()['plot'] = module
        return module
    raise AttributeError(f"module 'AeroViz' has no attribute '{name}'")

__all__ = [
    # I/O
    'RawDataReader',
    # Tools
    'DataBase',
    'DataClassifier',
    'plot',
    # Sub-namespaces
    'chemistry',
    'optical',
    'size',
    'voc',
    # chemistry top-level functions
    'reconstruct_mass',
    'split_oc_ec',
    'partition_ratios',
    'isoropia',
    'volume_ri',
    'kappa',
    'growth_factor',
    # optical top-level functions
    'optical_basic',
    'mie',
    'improve',
    'gas_extinction',
    'retrieve_ri',
    'brown_carbon',
    # PyMieScatt-style optical additions
    'mie_lognormal',
    'mie_multimodal',
    'scattering_function',
    'scattering_function_sd',
    'phase_matrix',
    'nephelometer_truncation_correction',
    'mie_core_shell',
    'mie_core_shell_sd',
    'iterative_inversion',
    'iterative_inversion_sd',
    'contour_intersection',
    # size top-level functions
    'psd_stats',
    'psd_distributions',
    'merge_psd',
    # voc top-level functions
    'voc_potentials',
    # Legacy
    'DataProcess',
]
