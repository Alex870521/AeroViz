"""
Deprecated post-processing helpers used by ``DataProcess.absCoe`` /
``DataProcess.scaCoe``.

These wrappers exist purely for backward compatibility — new code should
let the reader pipeline compute absorption / scattering coefficients via
``rawDataReader.core.pre_process`` (the canonical implementation that uses
numba-accelerated log–log Ångström fits and handles AE33 / BC1054 / MA350).

The old in-file implementation here had two bugs:

* ``get_species_wavelength`` fit a **linear** ``y = m·λ + b`` (rather than
  log–log) without ever seeing the actual source wavelengths, so what was
  meant to be a power-law extrapolation collapsed to the average of the
  input values.
* The instrument dispatch used a binary ``if AE33 else BC1054`` ternary, so
  passing ``instru='MA350'`` silently fell through to the BC1054 coefficient
  table and column-name conventions and produced wrong / shape-mismatched
  output.

Both are fixed by delegating to the single canonical implementation in
``pre_process``.
"""

from AeroViz.rawDataReader.core.pre_process import _absCoe as _absCoe_canonical
from AeroViz.rawDataReader.core.pre_process import _scaCoe as _scaCoe_canonical


def _scaCoe(df, instru, specified_band: list):
    """Compute scattering coefficients via the canonical implementation.

    Returns only the derived columns (``sca_{wl}`` for each entry in
    ``specified_band`` plus ``SAE``) to preserve the legacy return contract.
    """
    full = _scaCoe_canonical(df, instru=instru, specified_band=specified_band)
    keep = [f'sca_{wl}' for wl in specified_band] + ['SAE']
    return full[[c for c in keep if c in full.columns]].reindex(df.index)


def _absCoe(df, instru, specified_band: list):
    """Compute absorption coefficients via the canonical implementation.

    Returns only the derived columns (``abs_{wl}`` for each entry in
    ``specified_band`` plus ``eBC`` and ``AAE``).
    """
    full = _absCoe_canonical(df, instru=instru, specified_band=specified_band)
    keep = [f'abs_{wl}' for wl in specified_band] + ['eBC', 'AAE']
    return full[[c for c in keep if c in full.columns]].reindex(df.index)
