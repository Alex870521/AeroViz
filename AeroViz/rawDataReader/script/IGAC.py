# read meteorological data from google sheet


from pandas import read_csv, to_numeric

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
    nam = 'IGAC'

    def _raw_reader(self, file):

        with file.open('r', encoding='utf-8-sig', errors='ignore') as f:
            _df = read_csv(f, parse_dates=True, index_col=0, na_values='-').apply(to_numeric, errors='coerce')

            _df.columns = _df.keys().str.strip(' ')
            _df.index.name = 'time'

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):

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
