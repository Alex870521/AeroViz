from datetime import datetime
from pathlib import Path

from AeroViz.rawDataReader.config.supported_instruments import meta
from AeroViz.rawDataReader.script import *

__all__ = ['RawDataReader']


def RawDataReader(instrument_name: str,
                  path: Path,
                  qc: bool = True,
                  csv_raw: bool = True,
                  reset: bool = False,
                  rate: bool = False,
                  append_data: bool = False,
                  start: datetime | None = None,
                  end: datetime | None = None,
                  mean_freq='1h',
                  csv_out=True,
                  ):
    # Mapping of instrument names to their respective classes
    instrument_class_map = {
        'NEPH': NEPH,
        'Aurora': Aurora,
        'SMPS_genr': SMPS_genr,
        'SMPS_aim11': SMPS_aim11,
        'SMPS_TH': SMPS_TH,
        'GRIMM': GRIMM,
        'APS_3321': APS_3321,
        'AE33': AE33,
        'AE43': AE43,
        'BC1054': BC1054,
        'MA350': MA350,
        'TEOM': TEOM,
        'Sunset_OCEC': Sunset_OCEC,
        'IGAC': IGAC,
        'VOC': VOC,
        'Table': Table,
        'EPA_vertical': EPA_vertical,
        'Minion': Minion
        # Add other instruments and their corresponding classes here
    }

    # Check if the instrument name is in the map
    if instrument_name not in meta.keys():
        raise ValueError(f"Instrument name '{instrument_name}' is not valid. \nMust be one of: {list(meta.keys())}")

    # Instantiate the class and return the instance
    reader_module = instrument_class_map[instrument_name].Reader(
        path=path,
        qc=qc,
        csv_raw=csv_raw,
        reset=reset,
        rate=rate,
        append_data=append_data
    )
    return reader_module(
        start=start,
        end=end,
        mean_freq=mean_freq,
        csv_out=csv_out,
    )
