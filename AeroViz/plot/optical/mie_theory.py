from typing import Sequence, Literal

import numpy as np
import pandas as pd
from numpy import exp, log, log10, sqrt, pi

from .PyMieScatt_update import AutoMieQ


def Mie_Q(m: complex,
          wavelength: float,
          dp: float | Sequence[float]
          ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate Mie scattering efficiency (Q) for given spherical particle diameter(s).

    Parameters
    ----------
    m : complex
        The complex refractive index of the particles.
    wavelength : float
        The wavelength of the incident light (in nm).
    dp : float | Sequence[float]
        Particle diameters (in nm), can be a single value or Sequence object.

    Returns
    -------
    Q_ext : ndarray
        The Mie extinction efficiency for each particle diameter.
    Q_sca : ndarray
        The Mie scattering efficiency for each particle diameter.
    Q_abs : ndarray
        The Mie absorption efficiency for each particle diameter.

    Examples
    --------
    >>> Q_ext, Q_sca, Q_abs = Mie_Q(m=complex(1.5, 0.02), wavelength=550, dp=[100, 200, 300, 400])
    """
    # Ensure dp is a numpy array
    dp = np.atleast_1d(dp)

    # Transpose for proper unpacking
    Q_ext, Q_sca, Q_abs, g, Q_pr, Q_back, Q_ratio = np.array([AutoMieQ(m, wavelength, _dp) for _dp in dp]).T

    return Q_ext, Q_sca, Q_abs


def Mie_MEE(m: complex,
            wavelength: float,
            dp: float | Sequence[float],
            density: float
            ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate mass extinction efficiency and other parameters.

    Parameters
    ----------
    m : complex
        The complex refractive index of the particles.
    wavelength : float
        The wavelength of the incident light.
    dp : float | Sequence[float]
        List of particle sizes or a single value.
    density : float
        The density of particles.

    Returns
    -------
    MEE : ndarray
        The mass extinction efficiency for each particle diameter.
    MSE : ndarray
        The mass scattering efficiency for each particle diameter.
    MAE : ndarray
        The mass absorption efficiency for each particle diameter.

    Examples
    --------
    >>> MEE, MSE, MAE = Mie_MEE(m=complex(1.5, 0.02), wavelength=550, dp=[100, 200, 300, 400], density=1.2)
    """
    Q_ext, Q_sca, Q_abs = Mie_Q(m, wavelength, dp)

    MEE = (3 * Q_ext) / (2 * density * dp) * 1000
    MSE = (3 * Q_sca) / (2 * density * dp) * 1000
    MAE = (3 * Q_abs) / (2 * density * dp) * 1000

    return MEE, MSE, MAE


def Mie_PESD(m: complex,
             wavelength: float = 550,
             dp: float | Sequence[float] = None,
             ndp: float | Sequence[float] = None,
             lognormal: bool = False,
             dp_range: tuple = (1, 2500),
             geoMean: float = 200,
             geoStdDev: float = 2,
             numberOfParticles: float = 1e6,
             numberOfBins: int = 167,
             ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Simultaneously calculate "extinction distribution" and "integrated results" using the Mie_Q method.

    Parameters
    ----------
    m : complex
        The complex refractive index of the particles.
    wavelength : float
        The wavelength of the incident light.
    dp : float | Sequence[float]
        Particle sizes.
    ndp : float | Sequence[float]
        Number concentration from SMPS or APS in the units of dN/dlogdp.
    lognormal : bool, optional
        Whether to use lognormal distribution for ndp. Default is False.
    dp_range : tuple, optional
        Range of particle sizes. Default is (1, 2500) nm.
    geoMean : float, optional
        Geometric mean of the particle size distribution. Default is 200 nm.
    geoStdDev : float, optional
        Geometric standard deviation of the particle size distribution. Default is 2.
    numberOfParticles : float, optional
        Number of particles. Default is 1e6.
    numberOfBins : int, optional
        Number of bins for the lognormal distribution. Default is 167.

    Returns
    -------
    ext_dist : ndarray
        The extinction distribution for the given data.
    sca_dist : ndarray
        The scattering distribution for the given data.
    abs_dist : ndarray
        The absorption distribution for the given data.

    Notes
    -----
    return in "dext/dlogdp", please make sure input the dNdlogdp data.

    Examples
    --------
    >>> Ext, Sca, Abs = Mie_PESD(m=complex(1.5, 0.02), wavelength=550, dp=[100, 200, 500, 1000], ndp=[100, 50, 30, 20])
    """
    if lognormal:
        dp = np.logspace(log10(dp_range[0]), log10(dp_range[1]), numberOfBins)

        ndp = numberOfParticles * (1 / (log(geoStdDev) * sqrt(2 * pi)) *
                                   exp(-(log(dp) - log(geoMean)) ** 2 / (2 * log(geoStdDev) ** 2)))

    # dN / dlogdp
    ndp = np.atleast_1d(ndp)

    Q_ext, Q_sca, Q_abs = Mie_Q(m, wavelength, dp)

    # The 1e-6 here is so that the final value is the same as the unit 1/10^6m.
    Ext = Q_ext * (pi / 4 * dp ** 2) * ndp * 1e-6
    Sca = Q_sca * (pi / 4 * dp ** 2) * ndp * 1e-6
    Abs = Q_abs * (pi / 4 * dp ** 2) * ndp * 1e-6

    return Ext, Sca, Abs


def internal(dist: pd.Series,
             dp: float | Sequence[float],
             wavelength: float = 550,
             result_type: Literal['extinction', 'scattering', 'absorption'] = 'extinction'
             ) -> np.ndarray:
    """
    Calculate the extinction distribution by internal mixing model.

    Parameters
    ----------
    dist : pd.Series
        Particle size distribution data.
    dp : float | Sequence[float]
        Diameter(s) of the particles, either a single value or a sequence.
    wavelength : float, optional
        Wavelength of the incident light, default is 550 nm.
    result_type : {'extinction', 'scattering', 'absorption'}, optional
        Type of result to calculate, defaults to 'extinction'.

    Returns
    -------
    np.ndarray
        Extinction distribution calculated based on the internal mixing model.
    """
    ext_dist, sca_dist, abs_dist = Mie_PESD(m=complex(dist['n_amb'], dist['k_amb']),
                                            wavelength=wavelength,
                                            dp=dp,
                                            ndp=np.array(dist[:np.size(dp)]))

    if result_type == 'extinction':
        return ext_dist
    elif result_type == 'scattering':
        return sca_dist
    else:
        return abs_dist


# return dict(ext=ext_dist, sca=sca_dist, abs=abs_dist)


def external(dist: pd.Series,
             dp: float | Sequence[float],
             wavelength: float = 550,
             result_type: Literal['extinction', 'scattering', 'absorption'] = 'extinction'
             ) -> np.ndarray:
    """
    Calculate the extinction distribution by external mixing model.

    Parameters
    ----------
    dist : pd.Series
        Particle size distribution data.
    dp : float | Sequence[float]
        Diameter(s) of the particles, either a single value or a sequence.
    wavelength : float, optional
        Wavelength of the incident light, default is 550 nm.
    result_type : {'extinction', 'scattering', 'absorption'}, optional
        Type of result to calculate, defaults to 'extinction'.

    Returns
    -------
    np.ndarray
        Extinction distribution calculated based on the external mixing model.
    """
    refractive_dic = {'AS_volume_ratio': complex(1.53, 0.00),
                      'AN_volume_ratio': complex(1.55, 0.00),
                      'OM_volume_ratio': complex(1.54, 0.00),
                      'Soil_volume_ratio': complex(1.56, 0.01),
                      'SS_volume_ratio': complex(1.54, 0.00),
                      'EC_volume_ratio': complex(1.80, 0.54),
                      'ALWC_volume_ratio': complex(1.33, 0.00)}

    ndp = np.array(dist[:np.size(dp)])
    mie_results = (
        Mie_PESD(refractive_dic[_specie], wavelength, dp, dist[_specie] / (1 + dist['ALWC_volume_ratio']) * ndp) for
        _specie in refractive_dic)

    ext_dist, sca_dist, abs_dist = (np.sum([res[0] for res in mie_results], axis=0),
                                    np.sum([res[1] for res in mie_results], axis=0),
                                    np.sum([res[2] for res in mie_results], axis=0))

    if result_type == 'extinction':
        return ext_dist
    elif result_type == 'scattering':
        return sca_dist
    else:
        return abs_dist


def core_shell():
    pass


def sensitivity():
    pass


if __name__ == '__main__':
    result = Mie_Q(m=complex(1.5, 0.02), wavelength=550, dp=[100., 200.])
