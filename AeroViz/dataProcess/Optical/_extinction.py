"""
Basic extinction and optical property calculations.

Required Columns
----------------
df_sca:
    - sca_550 : Scattering coefficient at 550nm (Mm-1)
    - SAE     : Scattering Angstrom Exponent
df_abs:
    - abs_550 : Absorption coefficient at 550nm (Mm-1)
    - AAE     : Absorption Angstrom Exponent
    - eBC     : Equivalent Black Carbon (ng/m3)
"""

from pandas import DataFrame

from AeroViz.dataProcess.core import union_index, validate_inputs

# Required columns
REQUIRED_SCA_COLUMNS = ['sca_550', 'SAE']
REQUIRED_ABS_COLUMNS = ['abs_550', 'AAE', 'eBC']

COLUMN_DESCRIPTIONS = {
    'sca_550': 'Scattering coefficient at 550nm 散射係數 (Mm-1)',
    'SAE': 'Scattering Angstrom Exponent 散射埃指數',
    'abs_550': 'Absorption coefficient at 550nm 吸收係數 (Mm-1)',
    'AAE': 'Absorption Angstrom Exponent 吸收埃指數',
    'eBC': 'Equivalent Black Carbon 等效黑碳 (ng/m3)',
}


def _basic(df_sca, df_abs, df_mass=None, df_no2=None, df_temp=None):
    """
    Calculate basic optical properties and extinction.

    Parameters
    ----------
    df_sca : DataFrame
        Scattering data with columns: sca_550, SAE
    df_abs : DataFrame
        Absorption data with columns: abs_550, AAE, eBC
    df_mass : DataFrame, optional
        PM mass concentration (ug/m3) for MAE/MSE/MEE calculation
    df_no2 : DataFrame, optional
        NO2 concentration (ppb) for gas absorption
    df_temp : DataFrame, optional
        Temperature (Celsius) for Rayleigh scattering

    Returns
    -------
    DataFrame
        Optical properties: abs, sca, ext, SSA, SAE, AAE, eBC,
        and optionally MAE, MSE, MEE, abs_gas, sca_gas, ext_all

    Raises
    ------
    ValueError
        If required columns are missing from df_sca or df_abs
    """
    # Validate required columns
    validate_inputs(df_sca, REQUIRED_SCA_COLUMNS, '_basic (df_sca)', COLUMN_DESCRIPTIONS)
    validate_inputs(df_abs, REQUIRED_ABS_COLUMNS, '_basic (df_abs)', COLUMN_DESCRIPTIONS)

    df_sca, df_abs, df_mass, df_no2, df_temp = union_index(df_sca, df_abs, df_mass, df_no2, df_temp)

    df_out = DataFrame()

    # abs and sca coe
    df_out['abs'] = df_abs['abs_550'].copy()
    df_out['sca'] = df_sca['sca_550'].copy()

    # extinction coe.
    df_out['ext'] = df_out['abs'] + df_out['sca']

    # SSA
    df_out['SSA'] = df_out['sca'] / df_out['ext']

    # SAE, AAE, eBC
    df_out['SAE'] = df_sca['SAE'].copy()
    df_out['AAE'] = df_abs['AAE'].copy()
    df_out['eBC'] = df_abs['eBC'].copy() / 1e3

    # MAE, MSE, MEE
    if df_mass is not None:
        df_out['MAE'] = df_out['abs'] / df_mass
        df_out['MSE'] = df_out['sca'] / df_mass
        df_out['MEE'] = df_out['MSE'] + df_out['MAE']

    # gas absorbtion
    if df_no2 is not None:
        df_out['abs_gas'] = df_no2 * .33

    if df_temp is not None:
        df_out['sca_gas'] = (11.4 * 293 / (273 + df_temp))

    if df_no2 is not None and df_temp is not None:
        df_out['ext_all'] = df_out['ext'] + df_out['abs_gas'] + df_out['sca_gas']

    return df_out


def get_required_columns():
    """
    Get required column names for basic extinction calculation.

    Returns
    -------
    dict
        Dictionary with input names as keys and required columns as values.

    Examples
    --------
    >>> cols = get_required_columns()
    >>> print(cols['df_sca'])
    ['sca_550', 'SAE']
    """
    return {
        'df_sca': REQUIRED_SCA_COLUMNS.copy(),
        'df_abs': REQUIRED_ABS_COLUMNS.copy(),
        'df_mass': 'PM mass (any column) - optional',
        'df_no2': 'NO2 concentration (any column) - optional',
        'df_temp': 'Temperature in Celsius (any column) - optional'
    }
