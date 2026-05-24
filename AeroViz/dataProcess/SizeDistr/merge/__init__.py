"""
SMPS-APS Merge Algorithms

All v1-v4 derive the density from the SMPS-APS *overlap* and return the unified
dict keys ``data`` (+ version-specific variants) and ``density`` (see
``AeroViz.merge_psd`` for the full contract).

Version history (v0 / v0.1 removed — fully superseded):
- v1: Base power-law-fit merge with union_index alignment + ``shift_mode``
      (mobility/aerodynamic). Returns ``data`` + ``density``.
- v2: APS iterative correction + mobility & aerodynamic dual output.
      Returns ``data`` / ``data_aero`` + ``density``.
- v3: Multiprocessing + dN/dS/dV correlation; four algorithm variants
      (``data`` = cor_dndsdv, plus ``data_dn`` / ``data_dndsdv`` / ``data_cor_dn``)
      + ``density``.
- v4: v3 + PM2.5 fitness function + SMPS ``times`` correction.
- v5: ⚠️ EXPERIMENTAL / 測試中 ⚠️ mass-anchored density (PM1 mass closure,
      daily) instead of the degenerate overlap; requires a PM1 reference. API
      and behaviour are not stable.

v0.1's distinctive methods (APS iterative correction, mobility+aerodynamic dual
output) live on in v2/v3/v4, so both v0 and v0.1 were removed as dead code.
"""

from ._merge_v1 import _merge_SMPS_APS as merge_v1
from ._merge_v2 import merge_SMPS_APS as merge_v2
from ._merge_v3 import merge_SMPS_APS as merge_v3
from ._merge_v4 import merge_SMPS_APS as merge_v4
from ._merge_v5 import merge_SMPS_APS as merge_v5  # EXPERIMENTAL / 測試中

__all__ = ['merge_v1', 'merge_v2', 'merge_v3', 'merge_v4', 'merge_v5']
