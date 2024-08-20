from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'XRF'

    def _raw_reader(self, file):
        pass

    def _QC(self, _df):
        pass
