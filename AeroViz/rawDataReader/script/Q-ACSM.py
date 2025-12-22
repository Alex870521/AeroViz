from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    """Q-ACSM Data Reader

    A specialized reader for Q-ACSM data files.

    See full documentation at docs/source/instruments/Q-ACSM.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'Q-ACSM'
