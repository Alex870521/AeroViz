import warnings

from pandas import read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    """ Volatile Organic Compounds (VOC) Data Reader

    .. deprecated::
        ``RawDataReader('VOC', ...)`` is deprecated and will be removed in a
        future release. The reader is a thin CSV loader with no VOC-specific
        logic; read the file directly (e.g. ``pandas.read_csv`` with a datetime
        index) and pass the DataFrame to ``AeroViz.voc`` / ``voc_potentials``,
        which validates species against ``support_voc.json``.

    Reads a VOC measurement CSV into a clean, time-indexed DataFrame. The reader
    is intentionally thin — it is mainly a connector that feeds the downstream
    VOC process (``AeroViz.voc`` / ``VOC._basic``).

    File structure handling:
    - CSV formatted data files with a datetime index in column 0
    - Treats '-' and 'N.D.' (Not Detected) as NA
    - Strips whitespace from column names; drops duplicate / invalid timestamps

    Species handling:
    - The reader does NOT filter or validate species names. The supported
      species (with MW/MIR/SOAP/KOH coefficients) live in
      ``AeroViz/dataProcess/VOC/support_voc.json``, and the process validates
      each column against it before computing potentials. Keeping that the
      single source of truth avoids the reader/process list drift that a
      duplicated whitelist would (and did) cause.

    Quality Control:
    - None applied (``_QC`` returns the frame unchanged); VOC is read as
      pre-aggregated second-hand data.

    Returns
    -------
    DataFrame
        VOC data with a datetime index and every column from the source file.
    """
    nam = 'VOC'

    _DEPRECATION_MSG = (
        "RawDataReader('VOC', ...) is deprecated and will be removed in a future "
        "release. The VOC reader is a thin CSV loader with no VOC-specific logic; "
        "read the file directly (e.g. pandas.read_csv with a datetime index) and "
        "pass the DataFrame to AeroViz.voc / voc_potentials, which validates "
        "species against support_voc.json."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Fire once per reader instance (not per file).
        warnings.warn(self._DEPRECATION_MSG, DeprecationWarning, stacklevel=2)
        self.logger.warning(self._DEPRECATION_MSG)

    def _raw_reader(self, file):
        """Read a VOC CSV into a clean, time-indexed DataFrame (all columns)."""
        with file.open('r', encoding='utf-8-sig', errors='ignore') as f:
            _df = read_csv(f, parse_dates=True, index_col=0, na_values=('-', 'N.D.'))

        _df.columns = _df.columns.str.strip(' ')
        _df.index.name = 'time'

        # Return every column as-is; species selection/validation is the
        # downstream process's job (single source of truth: support_voc.json).
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
