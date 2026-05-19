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

from AeroViz import plot
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
    # size top-level functions
    'psd_stats',
    'psd_distributions',
    'merge_psd',
    # voc top-level functions
    'voc_potentials',
    # Legacy
    'DataProcess',
]
