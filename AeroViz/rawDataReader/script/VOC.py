from pandas import read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    """ Volatile Organic Compounds (VOC) Data Reader

    This class handles the reading and parsing of VOC measurement data files,
    which provide concentrations of various volatile organic compounds in air.

    File structure handling:
    - Processes CSV formatted data files with datetime index
    - Handles special values like '-' and 'N.D.' (Not Detected) as NA
    - Standardizes column names by stripping whitespace

    Data processing:
    - Filters VOC species based on a predefined list of supported compounds
    - Warns about unsupported VOC species in the data file
    - Handles duplicate timestamps and invalid indices

    Quality Control procedures:
    - Basic file validation
    - No additional QC is applied in the current implementation

    Returns:
    -------
    DataFrame
        Processed VOC data with datetime index and supported VOC species as columns.
        If no supported species are found, returns the original dataframe.

    Notes:
    -----
    VOC measurements are important for understanding air quality, photochemical
    reactions, and sources of secondary organic aerosols. This reader requires
    a predefined list of supported VOC species to be provided in the meta attribute.
    """
    nam = 'VOC'

    def _raw_reader(self, file):
        """
        Read and parse raw VOC measurement data files.

        Parameters
        ----------
        file : Path or str
            Path to the VOC data file.

        Returns
        -------
        pandas.DataFrame
            Processed VOC data with datetime index and supported VOC species as columns.

        Notes
        -----
        Requires self.meta["key"] to contain a list of supported VOC species names.
        If no supported species are found, returns the original dataframe with a warning.
        """
        with file.open('r', encoding='utf-8-sig', errors='ignore') as f:
            _df = read_csv(f, parse_dates=True, index_col=0, na_values=('-', 'N.D.'))

            _df.columns = _df.keys().str.strip(' ')
            _df.index.name = 'time'

            support_voc = set(self.meta["key"])

            valid_keys = [key for key in _df.keys() if key in support_voc]
            invalid_keys = [key for key in _df.keys() if key not in support_voc]

            if invalid_keys:
                self.logger.warning(f'{invalid_keys} are not supported keys.')
                print(f'\n\t{invalid_keys} are not supported keys.'
                      f'\n\tPlease check the\033[91m support_voc.md\033[0m file to use the correct name.')

            if valid_keys:
                return _df[valid_keys].loc[~_df.index.duplicated() & _df.index.notna()]
            else:
                self.logger.warning("沒有找到匹配的鍵。返回原始DataFrame。")
                return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on VOC measurement data.

        This method is a placeholder for future QC implementation. Currently,
        it returns the data unchanged.

        Parameters
        ----------
        _df : pandas.DataFrame
            Raw VOC data with datetime index and concentration columns.

        Returns
        -------
        pandas.DataFrame
            The input data unchanged.

        Notes
        -----
        No QC filters are currently applied. Future implementations could include:
        1. Minimum detection limit filtering
        2. Value range checks for each VOC species
        3. Time-based outlier detection
        4. Correlation checks between related VOC species
        """
        return _df
