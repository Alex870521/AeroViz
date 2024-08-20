from pathlib import Path

import numpy as np
from pandas import DataFrame, read_csv, concat

from AeroViz.process.core import DataProc
from AeroViz.process.core.SizeDist import SizeDist


class DryPSDProc(DataProc):
    """
    A class for process impact data.

    Parameters
    ----------
    reset : bool, optional
        If True, resets the process. Default is False.
    filename : str, optional
        The name of the file to process. Default is None.

    Methods
    -------
    process_data():
        Process data and save the result.

    Attributes
    ----------
    DEFAULT_PATH : Path
        The default path for data files.


    Examples
    --------
    >>> df = DryPSDProc(reset=True, filename='PNSD_dNdlogdp_dry.csv').process_data()
    """

    def __init__(self, file_path: Path | str = 'PNSD_dNdlogdp.csv', file_path_chem: Path | str = 'chemical.csv'):
        super().__init__()
        self.file_path = Path(file_path)
        self.file_path_chem = Path(file_path_chem)

        self.psd = SizeDist(read_csv(file_path, parse_dates=['Time'], index_col='Time'))
        self.RI = read_csv(file_path_chem, parse_dates=['Time'], index_col='Time')[['n_dry', 'n_amb', 'k_dry', 'k_amb',
                                                                                    'AS_volume_ratio',
                                                                                    'AN_volume_ratio',
                                                                                    'OM_volume_ratio',
                                                                                    'Soil_volume_ratio',
                                                                                    'SS_volume_ratio',
                                                                                    'EC_volume_ratio',
                                                                                    'ALWC_volume_ratio']]

    def process_data(self, reset: bool = False, save_filename: Path | str = None) -> DataFrame:
        save_filename = Path(save_filename)
        if save_filename.exists() and not reset:
            return read_csv(save_filename, parse_dates=['Time']).set_index('Time')
        _df = concat([self.psd, self.RI], axis=1)
        _df.to_csv(save_filename)
        return _df


def dry_PNSD_process(dist, dp, **kwargs):
    ndp = np.array(dist[:np.size(dp)])
    gRH = resolved_gRH(dp, dist['gRH'], uniform=True)

    dry_dp = dp / gRH
    belong_which_ibin = np.digitize(dry_dp, dp) - 1

    result = {}
    for i, (ibin, dn) in enumerate(zip(belong_which_ibin, ndp)):
        if dp[ibin] not in result:
            result[dp[ibin]] = []
        result[dp[ibin]].append(ndp[i])

    dry_ndp = []
    for key, val in result.items():
        dry_ndp.append(sum(val) / len(val))

    return np.array(dry_ndp)


def resolved_gRH(dp, gRH=1.31, uniform=True):
    if uniform:
        return np.array([gRH] * dp.size)

    else:
        lognorm_dist = lambda x, geoMean, geoStd: (gRH / (np.log10(geoStd) * np.sqrt(2 * np.pi))) * np.exp(
            -(x - np.log10(geoMean)) ** 2 / (2 * np.log10(geoStd) ** 2))
        abc = lognorm_dist(np.log10(dp), 200, 2.0)
        return np.where(abc < 1, 1, abc)


if __name__ == '__main__':
    pass
