from pathlib import Path

import numpy as np
from pandas import read_csv, concat, DataFrame

from AeroViz.process.core import DataProc
from AeroViz.tools.datareader import DataReader


class OthersProc(DataProc):
    """
    A class for process impact data.

    Parameters:
    -----------
    reset : bool, optional
        If True, resets the process. Default is False.
    filename : str, optional
        The name of the file to process. Default is None.

    Methods:
    --------
    process_data():
        Process data and save the result.

    Attributes:
    -----------
    DEFAULT_PATH : Path
        The default path for data files.

    Examples:
    ---------
    >>> df = OthersProc().process_data(reset=True, filename=None)

    """

    def __init__(self, file_paths: Path | list[Path | str] = None):
        super().__init__()
        self.file_paths = [Path(fp) for fp in file_paths]

    def process_data(self, reset: bool = False, save_file: Path | str = None) -> DataFrame:
        save_file = Path(save_file)
        if save_file.exists() and not reset:
            return read_csv(save_file, parse_dates=['Time'], index_col='Time')
        else:
            df = concat([DataReader(file) for file in self.file_paths], axis=1)

            results = DataFrame(index=df.index)

            results['PG'] = df[
                ['Scattering', 'Absorption', 'ScatteringByGas', 'AbsorptionByGas']].dropna().copy().apply(np.sum,
                                                                                                          axis=1)
            results['MAC'] = df['Absorption'] / df['T_EC']
            results['Ox'] = df['NO2'] + df['O3']
            results['N2O5_tracer'] = df['NO2'] * df['O3']
            results['Vis_cal'] = 1096 / df['Extinction']
            # results['fRH_Mix'] = df['Bext'] / df['Extinction']
            # results['fRH_PNSD'] = df['Bext_internal'] / df['Bext_dry']
            results['fRH_IMPR'] = df['total_ext'] / df['total_ext_dry']
            results['OCEC_ratio'] = df['O_OC'] / df['O_EC']
            results['PM1/PM25'] = np.where(df['PM1'] / df['PM2.5'] < 1, df['PM1'] / df['PM2.5'], np.nan)
            # results['MEE_PNSD'] = df['Bext_internal'] / df['PM25']
            # results['MEE_dry_PNSD'] = df['Bext_dry'] / df['PM25']

            return results
