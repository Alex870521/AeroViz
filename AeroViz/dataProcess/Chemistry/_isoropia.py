"""
ISORROPIA II thermodynamic equilibrium solver for inorganic aerosol.

Calls the ISORROPIA II Fortran library directly via an f2py extension
module (``_isorropia._ext``), so this works natively on macOS, Linux,
and Windows. Replaces the old ``isrpia2.exe``/subprocess approach.

The numerical engine is the same ISORROPIA II Fortran code used by
GEOS-Chem; only the Python ⇆ Fortran bridge changed. Outputs match the
legacy Windows ``isrpia2.exe`` to machine precision for typical
atmospheric conditions.
"""

from pathlib import Path
from typing import Optional

import numpy as np
from pandas import concat, DataFrame

from ._calculate import (
    convert_mass_to_molar_concentration,
    GAS_MOLECULAR_WEIGHTS,
)
from ._isorropia import solve_batch


# Indices into the ISORROPIA outputs (see isorropiaII_main_mod.F docs
# block around line ~10180 for the full layout):
#   AERLIQ(01) H+      AERLIQ(03) NH4+      AERLIQ(04) Cl-
#   AERLIQ(07) NO3-    AERLIQ(08) H2O
#   GAS(1) NH3         GAS(2) HNO3          GAS(3) HCl
_H_IDX, _NH4_IDX, _CL_IDX, _NO3_IDX, _H2O_IDX = 0, 2, 3, 6, 7

# Molecular weights (g/mol) used to convert ISORROPIA's mol/m³ back to
# µg/m³ for the user-facing DataFrame.
_MW = {
    'NH3': 17.031, 'HNO3': 63.013, 'HCl': 36.461,
    'NH4+': 18.039, 'NO3-': 62.005, 'Cl-': 35.453,
}


def _basic(df_che, path_out: Optional[Path], nam_lst):
    """
    Compute aerosol pH, ALWC, and gas-particle partitioning of
    semi-volatile inorganic species.

    Parameters
    ----------
    df_che : list of pandas.DataFrame
        Chemical species concentrations + meteorology, concatenated
        column-wise and renamed to ``nam_lst``.
    path_out : pathlib.Path or None
        Kept for API compatibility with the legacy subprocess version;
        no longer used (the native extension has no temp-file I/O).
    nam_lst : list of str
        Column names for the concatenated input; must include
        ``NH4+``, ``NH3``, ``HNO3``, ``NO3-``, ``HCl``, ``Cl-``, ``Na+``,
        ``SO42-``, ``Ca2+``, ``K+``, ``Mg2+``, ``RH``, ``temp``.

    Returns
    -------
    dict
        ``input`` (preprocessed ISORROPIA input) and ``output``
        (pH, ALWC, gas/aerosol partition of NH3/HNO3/HCl/NH4+/NO3-/Cl-).
    """
    df_all = concat(df_che, axis=1)

    # The legacy API renamed columns positionally
    # (``df_all.columns = nam_lst``), which silently mangled inputs
    # whose column order differed from ``nam_lst``. If the input
    # already has all required species by name, reorder them instead.
    if set(nam_lst).issubset(df_all.columns):
        df_all = df_all[nam_lst]
    else:
        df_all.columns = nam_lst

    df_umol = convert_mass_to_molar_concentration(df_all)

    # ``convert_mass_to_molar_concentration`` converts particulate ions
    # (NH4+, NO3-, SO42-, ...) to µmol/m³ but converts gas-phase species
    # (NH3, HNO3, HCl) to ppm via the ideal-gas law. ISORROPIA needs
    # total = particle + gas in consistent µmol/m³ units, so re-convert
    # the three gas species explicitly here.
    gas_umol = DataFrame(index=df_all.index)
    for sp in ('NH3', 'HNO3', 'HCl'):
        gas_umol[sp] = df_all[sp] / GAS_MOLECULAR_WEIGHTS[sp]

    # Build the ISORROPIA input frame in the same order the legacy code
    # used, so any downstream consumer of ``out['input']`` still sees
    # the familiar column layout.
    df_input = DataFrame(index=df_all.index)
    df_input['Na']   = df_umol['Na+']
    df_input['SO4']  = df_umol['SO42-']
    df_input['NH3']  = df_umol['NH4+'].fillna(0) + gas_umol['NH3']
    df_input['NO3']  = gas_umol['HNO3'].fillna(0) + df_umol['NO3-']
    df_input['Cl']   = gas_umol['HCl'].fillna(0)  + df_umol['Cl-']
    df_input['Ca']   = df_umol['Ca2+']
    df_input['K']    = df_umol['K+']
    df_input['Mg']   = df_umol['Mg2+']
    df_input['RH']   = df_all['RH'] / 100.0
    df_input['TEMP'] = df_all['temp'] + 273.15

    df_input = df_input[
        ['Na', 'SO4', 'NH3', 'NO3', 'Cl', 'Ca', 'K', 'Mg', 'RH', 'TEMP']
    ]

    # Drop rows with NaN in any input — ISORROPIA needs all 10 inputs.
    valid_mask = df_input.notna().all(axis=1)
    df_valid = df_input.loc[valid_mask]

    df_out = DataFrame(
        index=df_all.index,
        columns=['pH', 'ALWC', 'NH3', 'HNO3', 'HCl', 'NH4+', 'NO3-', 'Cl-'],
        dtype=float,
    )

    if df_valid.empty:
        return {'input': df_input, 'output': df_out}

    # umol/m³ → mol/m³ for the Fortran solver; (8, N) Fortran-order array
    # so solve_batch's column iteration is contiguous.
    wi_arr = np.asfortranarray(
        df_valid[['Na', 'SO4', 'NH3', 'NO3', 'Cl', 'Ca', 'K', 'Mg']]
        .values.T * 1e-6
    )
    rhi_arr = df_valid['RH'].values.astype(np.float64)
    tempi_arr = df_valid['TEMP'].values.astype(np.float64)
    cntrl = np.array([0.0, 1.0], dtype=np.float64)  # forward, metastable

    _wt, gas_arr, aerliq_arr, _aersld, _other = solve_batch(
        wi_arr, rhi_arr, tempi_arr, cntrl,
    )

    # pH from [H+] (mol/L) = AERLIQ(H+) / (AERLIQ(H2O) × 18.0153e-3)
    water_mol = aerliq_arr[_H2O_IDX]
    with np.errstate(divide='ignore', invalid='ignore'):
        h_mol_per_l = aerliq_arr[_H_IDX] / (water_mol * 18.0153e-3)
        ph = -np.log10(h_mol_per_l)
    # ALWC in µg/m³ from water mol/m³.
    alwc = water_mol * 18.0153 * 1e6

    rh_pct = df_all.loc[valid_mask, 'RH']
    valid_ph = (rh_pct >= 20) & (rh_pct <= 95)

    df_out.loc[valid_mask, 'pH'] = np.where(valid_ph, ph, np.nan)
    df_out.loc[valid_mask, 'ALWC'] = alwc

    # Gas + aerosol concentrations: convert mol/m³ → µg/m³.
    df_out.loc[valid_mask, 'NH3']  = gas_arr[0] * _MW['NH3']  * 1e6
    df_out.loc[valid_mask, 'HNO3'] = gas_arr[1] * _MW['HNO3'] * 1e6
    df_out.loc[valid_mask, 'HCl']  = gas_arr[2] * _MW['HCl']  * 1e6
    df_out.loc[valid_mask, 'NH4+'] = aerliq_arr[_NH4_IDX] * _MW['NH4+'] * 1e6
    df_out.loc[valid_mask, 'NO3-'] = aerliq_arr[_NO3_IDX] * _MW['NO3-'] * 1e6
    df_out.loc[valid_mask, 'Cl-']  = aerliq_arr[_CL_IDX]  * _MW['Cl-']  * 1e6

    return {'input': df_input, 'output': df_out}
