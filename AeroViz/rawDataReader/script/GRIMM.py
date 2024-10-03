from pandas import to_datetime, read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'GRIMM'

    def _raw_reader(self, file):

        _df = read_csv(file, header=233, delimiter='\t', index_col=0, parse_dates=[0], encoding='ISO-8859-1',
                       dayfirst=True).rename_axis("Time")
        _df.index = to_datetime(_df.index, format="%d/%m/%Y %H:%M:%S", dayfirst=True)

        if file.name.startswith("A407ST"):
            _df.drop(_df.columns[0:11].tolist() + _df.columns[128:].tolist(), axis=1, inplace=True)
        else:
            _df.drop(_df.columns[0:11].tolist() + _df.columns[-5:].tolist(), axis=1, inplace=True)

        if _df.empty:
            print(file, "is empty")
            return None

        return _df / 0.035

    def _QC(self, _df):
        # QC data in 1h
        return _df.resample('1h').apply(self.n_sigma_QC).resample(self.meta.get("freq")).mean()
