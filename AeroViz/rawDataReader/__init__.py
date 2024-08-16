from datetime import datetime

from AeroViz.rawDataReader.script import *
from AeroViz.rawDataReader.utils.config import meta

__all__ = ['RawDataReader']


def RawDataReader(instrument_name: str,
				  _path,
				  QC: bool = True,
				  csv_raw: bool = True,
				  reset: bool = False,
				  rate: bool = False,
				  append_data: bool = False,
				  update_meta=None,
				  start: datetime | None = None,
				  end: datetime | None = None,
				  mean_freq='1h',
				  csv_out=True,
				  **kwargs
				  ):
	# Mapping of instrument names to their respective classes
	instrument_class_map = {
		'NEPH': NEPH,
		'Aurora': Aurora,
		'Table': Table,
		'EPA_vertical': EPA_vertical,
		'APS_3321': APS_3321,
		'SMPS_TH': SMPS_TH,
		'AE33': AE33,
		'AE43': AE43,
		'BC1054': BC1054,
		'MA350': MA350,
		'TEOM': TEOM,
		'OCEC_RES': OCEC_RES,
		'OCEC_LCRES': OCEC_LCRES,
		'IGAC_TH': IGAC_TH,
		'IGAC_ZM': IGAC_ZM,
		'VOC_TH': VOC_TH,
		'VOC_ZM': VOC_ZM,
		'SMPS_genr': SMPS_genr,
		'SMPS_aim11': SMPS_aim11,
		'GRIMM': GRIMM
		# Add other instruments and their corresponding classes here
	}

	# Check if the instrument name is in the map
	if instrument_name not in meta.keys():
		raise ValueError(f"Instrument name '{instrument_name}' is not valid. \nMust be one of: {list(meta.keys())}")

	# Instantiate the class and return the instance
	reader_module = instrument_class_map[instrument_name].Reader(
		_path=_path,
		QC=QC,
		csv_raw=csv_raw,
		reset=reset,
		rate=rate,
		append_data=append_data,
		update_meta=update_meta
	)
	return reader_module(
		start=start,
		end=end,
		mean_freq=mean_freq,
		csv_out=csv_out,
		**kwargs
	)
