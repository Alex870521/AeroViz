"""
SMPS-APS Merge Algorithms

Version history:
- v0: Original implementation
- v0.1: Added union_index alignment
- v1: Added shift_mode parameter
- v2: Simplified output, removed qc filtering
- v3: Multiprocessing + dN/dS/dV algorithm
- v4: PM2.5 fitness + SMPS times correction
"""

from ._merge_v0 import _merge_SMPS_APS as merge_v0
from ._merge_v0_1 import merge_SMPS_APS as merge_v0_1
from ._merge_v1 import _merge_SMPS_APS as merge_v1
from ._merge_v2 import merge_SMPS_APS as merge_v2
from ._merge_v3 import merge_SMPS_APS as merge_v3
from ._merge_v4 import merge_SMPS_APS as merge_v4

__all__ = ['merge_v0', 'merge_v0_1', 'merge_v1', 'merge_v2', 'merge_v3', 'merge_v4']
