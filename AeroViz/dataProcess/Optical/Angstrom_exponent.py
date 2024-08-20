import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


def get_species_wavelength(df, specified_band):
    func = lambda wavelength, _sl, _int: _sl * wavelength + _int
    popt, pcov = curve_fit(func, specified_band, df.values)

    return func(np.array(specified_band), *popt)


def get_Angstrom_exponent(df, band):
    if (df <= 0).any():
        return pd.Series([np.nan, np.nan], index=['slope', 'intercept'])  # 返回包含 NaN 的 Series，保持 DataFrame 结构

    func = lambda wavelength, _sl, _int: _sl * wavelength + _int
    popt, _ = curve_fit(func, np.log(band), np.log(df))

    return pd.Series(popt, index=['slope', 'intercept'])  # 返回带有索引的 Series
