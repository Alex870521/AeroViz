"""
SMPS-APS Merge Algorithms

Version history (v0 / v0.1 removed — fully superseded):
- v1: Base power-law-fit merge with union_index alignment + ``shift_mode``
      (mobility/aerodynamic). Returns ``data_all`` / ``data_qc`` + density.
      Supersedes the original v0 (v0 was a strict subset of v1).
- v2: APS iterative correction + mobility & aerodynamic dual output, without
      QC filtering. Returns ``data_all`` / ``data_all_aer`` + density.
- v3: Multiprocessing + dN/dS/dV correlation; four algorithm variants
      (``dn`` / ``cor_dn`` / ``dndsdv`` / ``cor_dndsdv``) + density.
- v4: v3 + PM2.5 fitness function + SMPS ``times`` correction.

v0.1's distinctive methods (APS iterative correction, mobility+aerodynamic dual
output) live on in v2/v3/v4, so both v0 and v0.1 were removed as dead code.
"""

from ._merge_v1 import _merge_SMPS_APS as merge_v1
from ._merge_v2 import merge_SMPS_APS as merge_v2
from ._merge_v3 import merge_SMPS_APS as merge_v3
from ._merge_v4 import merge_SMPS_APS as merge_v4

__all__ = ['merge_v1', 'merge_v2', 'merge_v3', 'merge_v4']
