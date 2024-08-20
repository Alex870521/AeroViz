from pathlib import Path
from typing import Literal

from pandas import read_csv, concat, read_json

from AeroViz.process.core import DataProc
from AeroViz.tools.datareader import DataReader


class ImproveProc(DataProc):
    """
    A class for process improved chemical data.

    Parameters:
    -----------
    reset : bool, optional
        If True, resets the process. Default is False.
    filename : str, optional
        The name of the file to process. Default is None.
    version : str, optional
        The version of the data process. Should be one of 'revised' or 'modified'.
        Default is None.

    Methods:
    --------
    revised(_df):
        Calculate revised version of particle contribution.

    modified(_df):
        Calculate modified version of particle contribution.

    gas(_df):
        Calculate gas contribution.

    frh(_RH, version=None):
        Helper function to get frh values based on relative humidity (RH) and version.

    process_data():
        Process data and save the result.

    Attributes:
    -----------
    DEFAULT_PATH : Path
        The default path for data files.

    Examples:
    ---------
    >>> df = ImproveProc(reset=True, filename='revised_IMPROVE.csv', version='revised').process_data()

    """

    def __init__(self, file_paths: list[Path | str] = None):
        super().__init__()
        self.file_paths = [Path(fp) for fp in file_paths]

    @staticmethod
    def frh(_RH):
        _frh = read_json(Path(__file__).parent.parent.parent / 'plot' / 'utils' / 'fRH.json')
        if _RH is not None:
            if _RH > 95:
                _RH = 95
            _RH = round(_RH)
            return _frh.loc[_RH].values.T

        return 1, 1, 1, 1

    def revised(self, _df):
        def mode(Mass):
            L_mode = Mass ** 2 / 20 if Mass < 20 else Mass
            S_mode = Mass - L_mode if Mass < 20 else 0

            return L_mode, S_mode

        _frh, _frhss, _frhs, _frhl = self.frh(_df['RH'])

        L_AS, S_AS = mode(_df['AS'])
        L_AN, S_AN = mode(_df['AN'])
        L_OM, S_OM = mode(_df['OM'])

        _df['AS_ext_dry'] = 2.2 * 1 * S_AS + 4.8 * 1 * L_AS
        _df['AN_ext_dry'] = 2.4 * 1 * S_AN + 5.1 * 1 * L_AN
        _df['OM_ext_dry'] = 2.8 * S_OM + 6.1 * L_OM
        _df['Soil_ext_dry'] = 1 * _df['Soil']
        _df['SS_ext_dry'] = 1.7 * 1 * _df['SS']
        _df['EC_ext_dry'] = 10 * _df['EC']
        _df['total_ext_dry'] = sum(_df['AS_ext_dry':'EC_ext_dry'])

        _df['AS_ext'] = (2.2 * _frhs * S_AS) + (4.8 * _frhl * L_AS)
        _df['AN_ext'] = (2.4 * _frhs * S_AN) + (5.1 * _frhl * L_AN)
        _df['OM_ext'] = (2.8 * S_OM) + (6.1 * L_OM)
        _df['Soil_ext'] = (1 * _df['Soil'])
        _df['SS_ext'] = (1.7 * _frhss * _df['SS'])
        _df['EC_ext'] = (10 * _df['EC'])
        _df['total_ext'] = sum(_df['AS_ext':'EC_ext'])

        _df['ALWC_AS_ext'] = _df['AS_ext'] - _df['AS_ext_dry']
        _df['ALWC_AN_ext'] = _df['AN_ext'] - _df['AN_ext_dry']
        _df['ALWC_SS_ext'] = _df['SS_ext'] - _df['SS_ext_dry']
        _df['ALWC_ext'] = _df['total_ext'] - _df['total_ext_dry']

        _df['fRH_IMPR'] = _df['total_ext'] / _df['total_ext_dry']

        return _df['AS_ext_dry':]

    def modified(self, _df):
        _frh, _frhss, _frhs, _frhl = self.frh(_df['RH'])

        _df['AS_ext_dry'] = 3 * 1 * _df['AS']
        _df['AN_ext_dry'] = 3 * 1 * _df['AN']
        _df['OM_ext_dry'] = 4 * _df['OM']
        _df['Soil_ext_dry'] = 1 * _df['Soil']
        _df['SS_ext_dry'] = 1.7 * 1 * _df['SS']
        _df['EC_ext_dry'] = 10 * _df['EC']
        _df['total_ext_dry'] = sum(_df['AS_ext_dry':'EC_ext_dry'])

        _df['AS_ext'] = (3 * _frh * _df['AS'])
        _df['AN_ext'] = (3 * _frh * _df['AN'])
        _df['OM_ext'] = (4 * _df['OM'])
        _df['Soil_ext'] = (1 * _df['Soil'])
        _df['SS_ext'] = (1.7 * _frhss * _df['SS'])
        _df['EC_ext'] = (10 * _df['EC'])
        _df['total_ext'] = sum(_df['AS_ext':'EC_ext'])

        _df['ALWC_AS_ext'] = _df['AS_ext'] - _df['AS_ext_dry']
        _df['ALWC_AN_ext'] = _df['AN_ext'] - _df['AN_ext_dry']
        _df['ALWC_SS_ext'] = _df['SS_ext'] - _df['SS_ext_dry']
        _df['ALWC_ext'] = _df['total_ext'] - _df['total_ext_dry']

        _df['fRH_IMPR'] = _df['total_ext'] / _df['total_ext_dry']

        return _df['AS_ext_dry':]

    @staticmethod
    def gas(_df):
        _df['ScatteringByGas'] = (11.4 * 293 / (273 + _df['AT']))
        _df['AbsorptionByGas'] = (0.33 * _df['NO2'])
        _df['ExtinctionByGas'] = _df['ScatteringByGas'] + _df['AbsorptionByGas']
        return _df['ScatteringByGas':]

    def process_data(self, reset: bool = False, save_file: Path | str = None,
                     version: Literal["revised", "modified"] = "revised"):
        save_file = Path(save_file)
        if save_file.exists() and not reset:
            return read_csv(save_file, parse_dates=['Time'], index_col='Time')
        else:
            # data_files = ['EPB.csv', 'IMPACT.csv', 'chemical.csv']
            df = concat([DataReader(file) for file in self.file_paths], axis=1)

            # particle contribution '銨不足不納入計算'
            improve_input_df = df.loc[df['NH4_status'] != 'Deficiency', ['AS', 'AN', 'OM', 'Soil', 'SS', 'EC', 'RH']]

            df_improve = improve_input_df.dropna().copy().apply(self.revised if version == 'revised' else self.modified,
                                                                axis=1)

            # gas contribution
            df_ext_gas = df[['NO2', 'AT']].dropna().copy().apply(self.gas, axis=1)

            _df = concat([df_improve, df_ext_gas], axis=1).reindex(df.index.copy())
            _df.to_csv(save_file)

            return _df
