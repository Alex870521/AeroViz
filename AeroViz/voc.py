"""
Top-level functions for VOC analysis.

These are convenience wrappers — see ``AeroViz.dataProcess.VOC.*`` for full
algorithm details. Each function here is a thin re-export of an underlying
implementation, with the ``DataProcess`` / ``Writer`` boilerplate
(``path_out``, ``excel``, ``csv``, on-disk side effects) stripped away so
results are returned directly.

Example
-------
>>> from AeroViz.voc import voc_potentials
>>> result = voc_potentials(df_voc)
"""

from pandas import DataFrame

__all__ = ['voc_potentials']


def voc_potentials(df_voc: DataFrame) -> dict:
    """
    Compute VOC chemical-reactivity potentials and concentration summaries.

    For each VOC species in ``df_voc`` (ppb), this function uses the bundled
    ``support_voc.json`` parameter table (MW, MIR, SOAP, KOH) to compute:

    - Mass concentrations (μg/m³)
    - Ozone Formation Potential (OFP, μg O₃/m³ via MIR × ppb)
    - Secondary Organic Aerosol Potential (SOAP-scaled)
    - OH-reactivity (KOH × concentration)

    Species are also aggregated into chemistry classes (alkane, alkene,
    aromatic, alkyne, OVOC, ClVOC).

    Parameters
    ----------
    df_voc : DataFrame
        VOC concentrations in ppb. Column names must match the supported
        species in ``AeroViz/dataProcess/VOC/support_voc.json``
        (see ``AeroViz/docs/instruments/voc.md``).

    Returns
    -------
    dict
        Per-species and per-class summaries of concentration, OFP, SOAP,
        and OH-reactivity.

    Raises
    ------
    KeyError
        If any column in ``df_voc`` is not a supported VOC species.
    """
    from AeroViz.dataProcess.VOC._potential_par import _basic

    return _basic(df_voc)
