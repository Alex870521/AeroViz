import numpy as np
from numpy import exp, log
from scipy.signal import find_peaks


def geometric(dp: np.ndarray,
              dist: np.ndarray
              ) -> tuple[float, float]:
    """ Calculate the geometric mean and standard deviation. """

    _gmd = (((dist * log(dp)).sum()) / dist.sum())

    logdp_mesh, gmd_mesh = np.meshgrid(log(dp), _gmd)
    _gsd = ((((logdp_mesh - gmd_mesh) ** 2) * dist).sum() / dist.sum()) ** .5

    return exp(_gmd), exp(_gsd)


def contribution(dp: np.ndarray,
                 dist: np.ndarray
                 ) -> tuple[float, float, float]:
    """ Calculate the relative contribution of each mode. """

    ultra = dist[(dp >= 11.8) & (dp < 100)].sum() / dist.sum()
    accum = dist[(dp >= 100) & (dp < 1000)].sum() / dist.sum()
    coars = dist[(dp >= 1000) & (dp < 2500)].sum() / dist.sum()

    return ultra, accum, coars


def mode(dp: np.ndarray,
         dist: np.ndarray
         ) -> np.ndarray:
    """ Find three peak mode in distribution. """

    min_value = np.array([dist.min()])
    mode, _ = find_peaks(np.concatenate([min_value, dist, min_value]), distance=len(dist) - 1)

    return dp[mode - 1]


def properties(dist,
               dp: np.ndarray,
               dlogdp: np.ndarray,
               weighting: str
               ) -> dict:
    """ for apply """
    dist = np.array(dist)

    gmd, gsd = geometric(dp, dist)
    ultra, accum, coarse = contribution(dp, dist)
    peak = mode(dp, dist)

    return {key: round(value, 3) for key, value in
            {f'total_{weighting}': (dist * dlogdp).sum(),
             f'GMD_{weighting}': gmd,
             f'GSD_{weighting}': gsd,
             f'mode_{weighting}': peak[0],
             f'ultra_{weighting}': ultra,
             f'accum_{weighting}': accum,
             f'coarse_{weighting}': coarse}
            .items()}
