# read meteorological data from google sheet


from pandas import read_csv, to_numeric

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    """ IGAC (In-situ Gas and Aerosol Composition) Monitor Data Reader

    This class handles the reading and parsing of IGAC monitor data files,
    which provide real-time measurements of water-soluble inorganic ions in
    particulate matter.

    File structure handling:
    - Processes CSV formatted data files with datetime index
    - Handles special values like '-' as NA
    - Standardizes column names by stripping whitespace

    Data processing:
    - Converts all measurement values to numeric format with error handling
    - Filters out duplicated timestamps and invalid indices

    Quality Control procedures:
    - Applies minimum detection limit (MDL) filtering for each ion species
    - Verifies total ion concentration is less than PM2.5 mass concentration
    - Ensures presence of main ion species (NH4+, SO42-, NO3-)
    - Applies log-transformed IQR filtering for extreme value detection
    - Validates ion balance through cation/anion ratio checks
    - Applies lower exclusion thresholds for main ion species

    Returns:
    -------
    DataFrame
        Processed IGAC data with datetime index and the following ion columns:
        - Cations: Na+, NH4+, K+, Mg2+, Ca2+
        - Anions: Cl-, NO2-, NO3-, PO43-, SO42-

    Notes:
    -----
    IGAC monitors provide continuous measurements of water-soluble inorganic ions,
    which are critical components of secondary inorganic aerosols and contribute
    significantly to PM2.5 mass.
    """
    nam = 'IGAC'

    def _raw_reader(self, file):
        """
        Read and parse raw IGAC monitor data files.

        Parameters
        ----------
        file : Path or str
            Path to the IGAC data file.

        Returns
        -------
        pandas.DataFrame
            Processed IGAC data with datetime index and ion concentration columns.
        """
        with file.open('r', encoding='utf-8-sig', errors='ignore') as f:
            _df = read_csv(f, parse_dates=True, index_col=0, na_values='-')

            _df.columns = _df.keys().str.strip(' ')
            _df.index.name = 'time'

            _df = _df.apply(to_numeric, errors='coerce')

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """
        Perform quality control on IGAC ion composition data.

        This method applies a comprehensive series of filters specifically designed
        for water-soluble inorganic ion measurements, including detection limits,
        mass closure checks, and ion balance validation.

        Parameters
        ----------
        _df : pandas.DataFrame
            Raw IGAC data with datetime index and ion concentration columns.

        Returns
        -------
        pandas.DataFrame
            Quality-controlled IGAC data with invalid measurements masked.

        Notes
        -----
        Applies the following QC filters:
        1. MDL thresholds for each ion species:
           - Na+: 0.06 μg/m³
           - NH4+: 0.05 μg/m³
           - K+: 0.05 μg/m³
           - Mg2+: 0.12 μg/m³
           - Ca2+: 0.07 μg/m³
           - Cl-: 0.07 μg/m³
           - NO2-: 0.05 μg/m³
           - NO3-: 0.11 μg/m³
           - SO42-: 0.08 μg/m³
        2. Mass closure: Total ion mass < PM2.5 mass
        3. Completeness check: Requires main ions (NH4+, SO42-, NO3-)
        4. Log-transformed outlier detection for extreme values
        5. Ion balance validation: Cation/anion equivalence ratio checks
        6. Lower threshold filtering for main ion species
        """
        # QC parameter, function (MDL SE LE)
        _mdl = {
            'Na+': 0.06,
            'NH4+': 0.05,
            'K+': 0.05,
            'Mg2+': 0.12,
            'Ca2+': 0.07,
            'Cl-': 0.07,
            'NO2-': 0.05,
            'NO3-': 0.11,
            'SO42-': 0.08,
        }

        _cation, _anion, _main = (['Na+', 'NH4+', 'K+', 'Mg2+', 'Ca2+'],
                                  ['Cl-', 'NO2-', 'NO3-', 'PO43-', 'SO42-', ],
                                  ['SO42-', 'NO3-', 'NH4+'])

        _df_salt = _df[_mdl.keys()].copy()
        _df_pm = _df['PM2.5'].copy()

        # lower than PM2.5
        # conc. of main salt should be present at the same time (NH4+, SO42-, NO3-)
        _df_salt = _df_salt.mask(_df_salt.sum(axis=1, min_count=1) > _df_pm).dropna(subset=_main).copy()

        # mdl
        for (_key, _df_col), _mdl_val in zip(_df_salt.items(), _mdl.values()):
            _df_salt[_key] = _df_col.mask(_df_col < _mdl_val, _mdl_val / 2)

        # TODO:
        # calculate SE LE
        # salt < LE
        _se, _le = self.IQR_QC(_df_salt, log_dist=True)
        _df_salt = _df_salt.mask(_df_salt > _le).copy()

        # C/A, A/C
        _rat_CA = (_df_salt[_cation].sum(axis=1) / _df_salt[_anion].sum(axis=1)).to_frame()
        _rat_AC = (1 / _rat_CA).copy()

        _se, _le = self.IQR_QC(_rat_CA, )
        _cond_CA = (_rat_CA < _le) & (_rat_CA > 0)

        _se, _le = self.IQR_QC(_rat_AC, )
        _cond_AC = (_rat_AC < _le) & (_rat_AC > 0)

        _df_salt = _df_salt.where((_cond_CA * _cond_AC)[0]).copy()

        # conc. of main salt > SE
        _se, _le = self.IQR_QC(_df_salt[_main], log_dist=True)
        _df_salt[_main] = _df_salt[_main].mask(_df_salt[_main] < _se).copy()

        return _df_salt.reindex(_df.index)
