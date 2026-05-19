"""
Top-level functions for chemistry analysis.

These are convenience wrappers — see ``AeroViz.dataProcess.Chemistry.*`` for
full algorithm details. Each function here is a thin re-export of an
underlying implementation, with the ``DataProcess`` / ``Writer`` boilerplate
(``path_out``, ``excel``, ``csv``, on-disk side effects) stripped away so
results are returned directly.

Example
-------
>>> from AeroViz.chemistry import reconstruct_mass
>>> result = reconstruct_mass(df_chem, df_ref=df_pm25)
>>> result['mass']
"""

from pathlib import Path
from typing import Optional

from pandas import DataFrame

__all__ = [
    'reconstruct_mass',
    'split_oc_ec',
    'partition_ratios',
    'isoropia',
    'volume_ri',
    'kappa',
    'growth_factor',
]


def reconstruct_mass(
    *df_chem: DataFrame,
    df_ref: Optional[DataFrame] = None,
    df_water: Optional[DataFrame] = None,
    df_density: Optional[DataFrame] = None,
    nam_lst: Optional[list] = None,
    split_om: bool = False,
    oa_oc_ratio: float = 1.8,
) -> dict:
    """
    Reconstruct aerosol mass and volume from chemical composition.

    Converts ionic species (NH4+, SO42-, NO3-, etc.) to reconstructed
    species (AS, AN, OM, Soil, SS, EC) considering the ammonium
    neutralization status. Also computes volumes, density, refractive
    index, and (optionally) the POA/SOA split via the EC-tracer method.

    Parameters
    ----------
    *df_chem : DataFrame
        Chemical composition data. Multiple DataFrames are concatenated
        along axis=1 and renamed to ``nam_lst``.
    df_ref : DataFrame or Series, optional
        Reference mass (e.g., PM2.5) for quality control.
    df_water : DataFrame, optional
        Aerosol liquid water content (ALWC).
    df_density : DataFrame, optional
        Measured density data (requires ``Cl-`` column).
    nam_lst : list, optional
        Column names for ``df_chem`` after concatenation.
        Default: ``['NH4+', 'SO42-', 'NO3-', 'Fe', 'Na+', 'OC', 'EC']``.
    split_om : bool, default=False
        If True, split OM into POA and SOA using the EC-tracer method.
    oa_oc_ratio : float, default=1.8
        OA/OC conversion ratio for POA/SOA calculation.

    Returns
    -------
    dict
        Keys: ``mass``, ``volume``, ``vol_cal``, ``eq``, ``NH4_status``,
        ``density_mat``, ``density_rec``, ``RI_550``, ``RI_450``. See
        :func:`AeroViz.dataProcess.Chemistry._mass_volume.reconstruction_basic`
        for details.
    """
    from AeroViz.dataProcess.Chemistry._mass_volume import reconstruction_basic

    if nam_lst is None:
        nam_lst = ['NH4+', 'SO42-', 'NO3-', 'Fe', 'Na+', 'OC', 'EC']

    return reconstruction_basic(
        df_chem,
        df_ref,
        df_water=df_water,
        df_density=df_density,
        nam_lst=nam_lst,
        split_om=split_om,
        oa_oc_ratio=oa_oc_ratio,
    )


def split_oc_ec(
    df_lcres: DataFrame,
    df_mass: Optional[DataFrame] = None,
    ocec_ratio: Optional[float] = None,
    ocec_ratio_month: int = 1,
    hr_lim: int = 200,
    least_square_range: tuple = (0.1, 2.5, 0.1),
    WISOC_OC_range: tuple = (0.2, 0.7, 0.01),
) -> dict:
    """
    Split OC into primary (POC) and secondary (SOC) using EC-tracer / MRS.

    Computes OC/EC, POC, SOC, WSOC, WISOC for both Thermal and Optical
    analyses, plus ratio-based status flags (Normal / Warning).

    Parameters
    ----------
    df_lcres : DataFrame
        OC/EC analyzer level results — must include columns
        ``OC1``, ``OC2``, ``OC3``, ``OC4``, ``PC``, ``Thermal_OC``,
        ``Thermal_EC``, ``Optical_OC``, ``Optical_EC``, ``Sample_Volume``.
    df_mass : DataFrame, optional
        Reference PM mass; used to compute species/PM ratios.
    ocec_ratio : float, optional
        Override the primary OC/EC ratio. If None, the MRS method searches
        a monthly grid.
    ocec_ratio_month : int, default=1
        Resampling window (in months) for the MRS ratio search.
    hr_lim : int, default=200
        Minimum number of valid hours per window for an MRS fit.
    least_square_range : tuple, default=(0.1, 2.5, 0.1)
        ``(start, stop, step)`` candidate OC/EC ratios.
    WISOC_OC_range : tuple, default=(0.2, 0.7, 0.01)
        ``(start, stop, step)`` candidate WISOC/OC ratios.

    Returns
    -------
    dict
        Keys ``basic`` (concatenated OC/EC data + status flags) and
        ``ratio`` (per-species PM / OC ratios).
    """
    from AeroViz.dataProcess.Chemistry._ocec import _basic

    return _basic(
        df_lcres,
        df_mass,
        ocec_ratio,
        ocec_ratio_month,
        hr_lim,
        least_square_range,
        WISOC_OC_range,
    )


def partition_ratios(df_data: DataFrame) -> DataFrame:
    """
    Calculate gas-particle partitioning ratios (SOR, NOR, NTR, epsilon).

    Parameters
    ----------
    df_data : DataFrame
        Particle and gas concentrations (μg/m³).
        Required: ``temp`` column (Celsius).
        Optional species (at least one pair):
        - ``SO42-`` + ``SO2``  → SOR
        - ``NO3-`` + ``NO2``   → NOR (and with ``HNO3`` → NOR_2)
        - ``NH4+`` + ``NH3``   → NTR
        - ``Cl-``  + ``HCl``   → chloride partitioning

    Returns
    -------
    DataFrame
        Partitioning ratios — columns include ``SOR``, ``NOR``, ``NOR_2``,
        ``NTR``, ``epls_SO42-``, ``epls_NO3-``, ``epls_NH4+``, ``epls_Cl-``.

    Notes
    -----
    - SOR > 0.1 typically indicates secondary sulfate formation.
    - Values near 1.0: particle phase dominant; near 0.0: gas phase dominant.
    """
    from AeroViz.dataProcess.Chemistry._calculate import partition_ratios as _partition_ratios

    return _partition_ratios(df_data)


def isoropia(
    *df_chem: DataFrame,
    path_out: Path,
    nam_lst: Optional[list] = None,
) -> dict:
    """
    Run ISORROPIA II to compute aerosol pH, ALWC, and gas-particle partitioning.

    EXCEPTION: this function keeps ``path_out`` because the underlying
    implementation shells out to a Windows binary (``isrpia2.exe``) that
    reads/writes temporary files on disk.

    Parameters
    ----------
    *df_chem : DataFrame
        Chemical species + meteorology DataFrames; concatenated and renamed
        to ``nam_lst``.
    path_out : pathlib.Path
        Output directory; ISORROPIA reads/writes temp files here.
    nam_lst : list, optional
        Column names for the concatenated input. Default:
        ``['Na+', 'SO42-', 'NH4+', 'NO3-', 'Cl-', 'Ca2+', 'K+', 'Mg2+',
        'NH3', 'HNO3', 'HCl', 'RH', 'temp']``.

    Returns
    -------
    dict
        ``input`` (preprocessed ISORROPIA input) and ``output``
        (pH, ALWC, gas/aerosol-phase NH3/HNO3/HCl/NH4+/NO3-/Cl-).

    Raises
    ------
    ValueError
        If ``path_out`` is None.
    """
    from AeroViz.dataProcess.Chemistry._isoropia import _basic

    if nam_lst is None:
        nam_lst = ['Na+', 'SO42-', 'NH4+', 'NO3-', 'Cl-', 'Ca2+',
                   'K+', 'Mg2+', 'NH3', 'HNO3', 'HCl', 'RH', 'temp']

    if path_out is None:
        raise ValueError('Please Input "path_out" !!')

    return _basic(df_chem, path_out, nam_lst=nam_lst)


def volume_ri(df_volume: DataFrame, df_alwc: Optional[DataFrame] = None) -> DataFrame:
    """
    Calculate volume-average refractive index (dry & ambient) and gRH.

    Uses the volume-mixing rule: ``RI_mix = Σ(Vi · RIi) / V_total``
    at 550 nm.

    Parameters
    ----------
    df_volume : DataFrame
        Volume concentrations (μm³/m³). Required: ``total_dry``; plus at
        least one of ``AS_volume``, ``AN_volume``, ``OM_volume``,
        ``Soil_volume``, ``SS_volume``, ``EC_volume``.
    df_alwc : DataFrame, optional
        Aerosol liquid water content (``ALWC`` column).

    Returns
    -------
    DataFrame
        Columns ``n_dry``, ``k_dry``, ``n_amb``, ``k_amb``, ``gRH``
        (ambient values NaN if ``df_alwc`` not provided).
    """
    from AeroViz.dataProcess.Chemistry._calculate import volume_average_mixing

    return volume_average_mixing(df_volume, df_alwc)


def kappa(df_data: DataFrame, diameter: float = 0.5) -> DataFrame:
    """
    Calculate the hygroscopicity parameter kappa.

    Parameters
    ----------
    df_data : DataFrame
        Must contain ``gRH``, ``AT`` (temperature in °C), ``RH`` (%).
    diameter : float, default=0.5
        Particle dry diameter in micrometers.

    Returns
    -------
    DataFrame
        Single column ``kappa_chem``.
    """
    from AeroViz.dataProcess.Chemistry._calculate import kappa_calculate

    return kappa_calculate(df_data, diameter)


def growth_factor(df_volume: DataFrame, df_alwc: DataFrame) -> DataFrame:
    """
    Calculate the hygroscopic growth factor gRH = (V_wet / V_dry)^(1/3).

    Parameters
    ----------
    df_volume : DataFrame
        Must contain ``total_dry``.
    df_alwc : DataFrame
        Must contain ``ALWC``.

    Returns
    -------
    DataFrame
        Single column ``gRH``.
    """
    from AeroViz.dataProcess.Chemistry._calculate import gRH_calculate

    return gRH_calculate(df_volume, df_alwc)
