from pandas import to_datetime, read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    """ GRIMM Aerosol Spectrometer Data Reader

    A specialized reader for GRIMM data files, which measure particle size distributions
    in the range of 0.25-32 μm.

    See full documentation at docs/source/instruments/GRIMM.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'GRIMM'

    def _raw_reader(self, file):
        """
        Read and parse raw GRIMM data files.

        Parameters
        ----------
        file : Path or str
            Path to the GRIMM data file.

        Returns
        -------
        pandas.DataFrame or None
            Processed GRIMM data with datetime index and size channels as columns.
            Returns None if the file is empty.
        """
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
        """
        Perform quality control on GRIMM data.

        Parameters
        ----------
        _df : pandas.DataFrame
            Raw GRIMM data with datetime index and size channels as columns.

        Returns
        -------
        pandas.DataFrame
            The input data unchanged.

        Notes
        -----
        No QC filters are currently applied. Future implementations could include:
        1. Value range checks for each size channel
        2. Total concentration consistency checks
        3. Time-based outlier detection
        """
        return _df
