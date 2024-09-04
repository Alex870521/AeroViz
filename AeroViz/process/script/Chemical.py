from pathlib import Path

import numpy as np
from pandas import read_csv, concat, notna, DataFrame, to_numeric

from AeroViz.process.core import DataProc
from AeroViz.tools.datareader import DataReader


class ChemicalProc(DataProc):
    """
    A class for process chemical data.

    Parameters:
    -----------
    reset : bool, optional
        If True, resets the process. Default is False.
    filename : str, optional
        The name of the file to process. Default is None.

    Methods:
    --------
    mass(_df):
        Calculate mass-related parameters.

    volume(_df):
        Calculate volume-related parameters.

    volume_average_mixing(_df):
        Calculate volume average mixing parameters.

    process_data():
        Process data and save the result.

    Attributes:
    -----------
    DEFAULT_PATH : Path
        The default path for data files.

    Examples:
    ---------

    """

    def __init__(self, file_paths: list[Path | str] = None):
        super().__init__()
        self.file_paths = [Path(fp) for fp in file_paths]

    @staticmethod
    def mass(_df):  # Series like
        Ammonium, Sulfate, Nitrate, OC, Soil, SS, EC, PM25 = _df
        status = (Ammonium / 18) / (2 * (Sulfate / 96) + (Nitrate / 62))

        if status >= 1:
            _df['NH4_status'] = 'Enough'
            _df['AS'] = 1.375 * Sulfate
            _df['AN'] = 1.29 * Nitrate

        if status < 1:
            _df['NH4_status'] = 'Deficiency'
            mol_A = Ammonium / 18
            mol_S = Sulfate / 96
            mol_N = Nitrate / 62
            residual = mol_A - 2 * mol_S

            if residual > 0:
                _df['AS'] = 1.375 * Sulfate
                _df['AN'] = residual * 80 if residual <= mol_N else mol_N * 80

            else:
                _df['AS'] = mol_A / 2 * 132 if mol_A <= 2 * mol_S else mol_S * 132
                _df['AN'] = 0

        _df['OM'] = 1.8 * OC
        _df['Soil'] = 28.57 * Soil / 1000
        _df['SS'] = 2.54 * SS
        _df['EC'] = EC
        _df['SIA'] = _df['AS'] + _df['AN']
        _df['total_mass'] = _df[['AS', 'AN', 'OM', 'Soil', 'SS', 'EC']].sum()
        species_lst = ['AS', 'AN', 'OM', 'Soil', 'SS', 'EC', 'SIA', 'unknown_mass']

        _df['unknown_mass'] = PM25 - _df['total_mass'] if PM25 >= _df['total_mass'] else 0
        for _species, _val in _df[species_lst].items():
            _df[f'{_species}_ratio'] = _val / PM25 if PM25 >= _df['total_mass'] else _val / _df['total_mass']

        return _df['NH4_status':]

    @staticmethod
    def volume(_df):
        _df['AS_volume'] = (_df['AS'] / 1.76)
        _df['AN_volume'] = (_df['AN'] / 1.73)
        _df['OM_volume'] = (_df['OM'] / 1.4)
        _df['Soil_volume'] = (_df['Soil'] / 2.6)
        _df['SS_volume'] = (_df['SS'] / 2.16)
        _df['EC_volume'] = (_df['EC'] / 1.5)
        _df['ALWC_volume'] = _df['ALWC']
        _df['total_volume'] = sum(_df['AS_volume':'EC_volume'])

        for _species, _val in _df['AS_volume':'ALWC_volume'].items():
            _df[f'{_species}_ratio'] = _val / _df['total_volume']

        _df['density'] = _df['total_mass'] / _df['total_volume']
        return _df['AS_volume':]

    @staticmethod
    def volume_average_mixing(_df):
        _df['n_dry'] = (1.53 * _df['AS_volume_ratio'] +
                        1.55 * _df['AN_volume_ratio'] +
                        1.55 * _df['OM_volume_ratio'] +
                        1.56 * _df['Soil_volume_ratio'] +
                        1.54 * _df['SS_volume_ratio'] +
                        1.80 * _df['EC_volume_ratio'])

        _df['k_dry'] = (0.00 * _df['OM_volume_ratio'] +
                        0.01 * _df['Soil_volume_ratio'] +
                        0.54 * _df["EC_volume_ratio"])

        # 檢查_df['ALWC']是否缺失 -> 有值才計算ambient的折射率
        if notna(_df['ALWC']):
            v_dry = _df['total_volume']
            v_wet = _df['total_volume'] + _df['ALWC']

            multiplier = v_dry / v_wet
            _df['ALWC_volume_ratio'] = (1 - multiplier)

            _df['n_amb'] = (1.53 * _df['AS_volume_ratio'] +
                            1.55 * _df['AN_volume_ratio'] +
                            1.55 * _df['OM_volume_ratio'] +
                            1.56 * _df['Soil_volume_ratio'] +
                            1.54 * _df['SS_volume_ratio'] +
                            1.80 * _df['EC_volume_ratio']) * multiplier + \
                           (1.33 * _df['ALWC_volume_ratio'])

            _df['k_amb'] = (0.00 * _df['OM_volume_ratio'] +
                            0.01 * _df['Soil_volume_ratio'] +
                            0.54 * _df['EC_volume_ratio']) * multiplier

            _df['gRH'] = (v_wet / v_dry) ** (1 / 3)

            return _df[['n_dry', 'k_dry', 'n_amb', 'k_amb', 'gRH']]

    @staticmethod
    def kappa(_df, diameter=0.5):
        surface_tension, Mw, density, universal_gas_constant = 0.072, 18, 1, 8.314  # J/mole*K

        A = 4 * (surface_tension * Mw) / (density * universal_gas_constant * (_df['AT'] + 273))
        power = A / diameter
        a_w = (_df['RH'] / 100) * (np.exp(-power))

        _df['kappa_chem'] = (_df['gRH'] ** 3 - 1) * (1 - a_w) / a_w
        _df['kappa_vam'] = np.nan

    @staticmethod
    def ISORROPIA():
        pass

    def process_data(self, reset: bool = False, save_file: Path | str = None) -> DataFrame:
        save_file = Path(save_file)
        if save_file.exists() and not reset:
            return read_csv(save_file, parse_dates=['Time'], index_col='Time')
        else:
            df = concat([DataReader(file) for file in self.file_paths], axis=1).apply(to_numeric, errors='coerce')

            df_mass = df[['NH4+', 'SO42-', 'NO3-', 'Optical_OC', 'Fe', 'Na+', 'Optical_EC', 'PM2.5']].dropna().apply(
                self.mass,
                                                                                                        axis=1)
            df_mass['ALWC'] = df['ALWC']
            df_volume = df_mass[['AS', 'AN', 'OM', 'Soil', 'SS', 'EC', 'total_mass', 'ALWC']].dropna().apply(
                self.volume,
                axis=1)
            df_volume['ALWC'] = df['ALWC']
            df_vam = df_volume.dropna().apply(self.volume_average_mixing, axis=1)

            _df = concat([df_mass, df_volume.drop(['ALWC'], axis=1), df_vam], axis=1).reindex(df.index.copy())
            _df.to_csv(save_file)

            return _df
