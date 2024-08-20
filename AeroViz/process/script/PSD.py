from pathlib import Path

from pandas import concat, read_csv, DataFrame

from AeroViz.process.core import DataProc
from AeroViz.process.core.SizeDist import SizeDist
from AeroViz.process.script.AbstractDistCalc import DistributionCalculator


class ParticleSizeDistProc(DataProc):
	"""
    A class for process particle size distribution (PSD) data.

    Parameters
    ----------
    filename : str, optional
        The name of the PSD data file.
        Defaults to 'PNSD_dNdlogdp.csv' in the default path.

    Attributes
    ----------
    file_path : Path
        The directory path where the PSD data file is located.

    psd : SizeDist
        The SizeDist object.

    Methods
    -------
    process_data(filename='PSD.csv')
        Process and save overall PSD properties.

    Examples
    --------
    Example 1: Use default path and filename
    >>> psd_data = ParticleSizeDistProc(filename='PNSD_dNdlogdp.csv').process_data(reset=True)
    """

	def __init__(self, file_path: Path | str = None):
		super().__init__()
		self.file_path = Path(file_path)

		self.psd = SizeDist(read_csv(file_path, parse_dates=['Time'], index_col='Time'))

	def process_data(self, reset: bool = False, save_file: Path | str = None) -> DataFrame:
		save_file = Path(save_file)
		if save_file.exists() and not reset:
			return read_csv(save_file, parse_dates=['Time'], index_col='Time')

		number = DistributionCalculator('number', self.psd).useApply()
		surface = DistributionCalculator('surface', self.psd).useApply()
		volume = DistributionCalculator('volume', self.psd).useApply()

		surface.to_csv(save_file.parent / 'PSSD_dSdlogdp.csv')
		volume.to_csv(save_file.parent / 'PVSD_dVdlogdp.csv')

		result_df = concat(
			[DistributionCalculator('property', SizeDist(data=number, weighting='n')).useApply(),
			 DistributionCalculator('property', SizeDist(data=surface, weighting='s')).useApply(),
			 DistributionCalculator('property', SizeDist(data=volume, weighting='v')).useApply()
			 ], axis=1)

		result_df.to_csv(save_file)
		return result_df


class ExtinctionDistProc(DataProc):

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

	def process_data(self, reset: bool = False, save_file: Path | str = 'PESD.csv'):
		save_file = Path(save_file)
		if save_file.exists() and not reset:
			return read_csv(save_file, parse_dates=['Time']).set_index('Time')

		ext_internal = DistributionCalculator('extinction', self.psd, self.RI, method='internal',
											  result_type='extinction').useApply()
		ext_external = DistributionCalculator('extinction', self.psd, self.RI, method='external',
											  result_type='extinction').useApply()

		ext_internal.to_csv(save_file.parent / 'PESD_dextdlogdp_internal.csv')
		ext_external.to_csv(save_file.parent / 'PESD_dextdlogdp_external.csv')

		result_df = concat([
			DistributionCalculator('property', SizeDist(data=ext_internal, weighting='ext_in')).useApply(),
			DistributionCalculator('property', SizeDist(data=ext_internal, weighting='ext_ex')).useApply(),
		], axis=1)

		result_df.to_csv(save_file)
		return result_df
