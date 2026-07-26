# Description: Configuration file for rawDataReader

meta = {
    "NEPH": {
        "pattern": ["*.dat"],
        "freq": "5min",
    },

    "Aurora": {
        "pattern": ["*.csv"],
        "freq": "1min",
    },

    "SMPS": {
        "pattern": ["*.txt", "*.csv"],
        "freq": "6min",
    },

    "GRIMM": {
        "pattern": ["*.dat"],
        "freq": "6min",
    },

    "APS": {
        "pattern": ["*.txt"],
        "freq": "6min",
    },

    "AE33": {
        "pattern": ["[!ST|!CT|!FV]*[!log]_AE33*.dat"],
        "freq": "1min",
    },

    "AE43": {
        "pattern": ["[!ST|!CT|!FV]*[!log]_AE43*.dat"],
        "freq": "1min",
    },

    "BC1054": {
        "pattern": ["*.csv"],
        "freq": "1min",
    },

    "MA350": {
        "pattern": ["*.csv"],
        "freq": "1min",
    },

    "BAM1020": {
        "pattern": ["*.csv"],
        "freq": "1h",
    },

    "TEOM": {
        "pattern": ["*.csv"],
        "freq": "6min",
    },

    "OCEC": {
        "pattern": ["*LCRes.csv"],
        "freq": "1h",
    },

    "IGAC": {
        "pattern": ["*.csv"],
        "freq": "1h",

        # https://www.yangyao-env.com/web/product/product_in2.jsp?pd_id=PD1640151884502
        # HF: 0.08, F-: 0.08, PO43-: None is not measured
        "MDL": {
            'HF': None, 'HCl': 0.05, 'HNO2': 0.01, 'HNO3': 0.05, 'G-SO2': 0.05, 'NH3': 0.1,
            'Na+': 0.05, 'NH4+': 0.08, 'K+': 0.08, 'Mg2+': 0.05, 'Ca2+': 0.05,
            'F-': None, 'Cl-': 0.05, 'NO2-': 0.05, 'NO3-': 0.01, 'PO43-': None, 'SO42-': 0.05,
        },

        "MR": {
            'HF': 200, 'HCl': 200, 'HNO2': 200, 'HNO3': 200, 'G-SO2': 200, 'NH3': 300,
            'Na+': 300, 'NH4+': 300, 'K+': 300, 'Mg2+': 300, 'Ca2+': 300,
            'F-': 300, 'Cl-': 300, 'NO2-': 300, 'NO3-': 300, 'PO43-': None, 'SO42-': 300,
        }
    },

    "Xact": {
        "pattern": ["*.csv"],
        "freq": "1h",

        # base on Xact 625i Minimum Decision Limit (MDL) for XRF in ng/m3, 60 min sample time
        "MDL": {
            'Al': 100, 'Si': 18, 'P': 5.2, 'S': 3.2, 'Cl': 1.7,
            'K': 1.2, 'Ca': 0.3, 'Ti': 1.6, 'V': 0.12, 'Cr': 0.12,
            'Mn': 0.14, 'Fe': 0.17, 'Co': 0.14, 'Ni': 0.096, 'Cu': 0.079,
            'Zn': 0.067, 'Ga': 0.059, 'Ge': 0.056, 'As': 0.063, 'Se': 0.081,
            'Br': 0.1, 'Rb': 0.19, 'Sr': 0.22, 'Y': 0.28, 'Zr': 0.33,
            'Nb': 0.41, 'Mo': 0.48, 'Pd': 2.2, 'Ag': 1.9, 'Cd': 2.5,
            'In': 3.1, 'Sn': 4.1, 'Sb': 5.2, 'Te': 0.6, 'Cs': 0.37,
            'Ba': 0.39, 'La': 0.36, 'Ce': 0.3, 'W': 0.0001, 'Pt': 0.12,
            'Au': 0.1, 'Hg': 0.12, 'Tl': 0.12, 'Pb': 0.13, 'Bi': 0.13
        }
    },

    "Q-ACSM": {
        "pattern": ["*.csv"],
        "freq": "30min",
    },

    "EPA": {
        "pattern": ["*.csv"],
        "freq": "1h",
    },
}

# Real instruments whose reader is not written yet. They stay in `meta` (the
# native frequency is known) but have no module in `script/`, so the factory
# raises a plain "not implemented" instead of an abstract-class TypeError.
# Removing the entry here once a reader lands is all that is needed.
pending = {
    "Q-ACSM": (
        "Q-ACSM is a real instrument, but its reader is not implemented yet — no sample "
        "export has been available to write and test a parser against. Contribute one by "
        "adding AeroViz/rawDataReader/script/Q-ACSM.py with _raw_reader and _QC (see "
        "docs/guide/data-levels.md for the level contracts each must satisfy)."
    ),
}

# Instruments that used to have a reader and no longer do, with the migration
# advice surfaced by the RawDataReader factory. Both were pre-aggregated,
# second-hand datasets — somebody else's processed output rather than an
# instrument's raw log — so there was no raw format to parse and the readers only
# performed generic checks. Keep the entries: they turn a bare "not a valid
# instrument" error into an actionable one for existing scripts.
removed = {
    "VOC": (
        "VOC data is pre-aggregated (second-hand); there is no raw VOC log to parse. "
        "Read the file with pandas and pass the DataFrame to AeroViz.voc / "
        "voc_potentials, which validates species against support_voc.json: "
        "df = pd.read_csv(path, index_col=0, parse_dates=True, na_values=('-', 'N.D.'))"
    ),
    "Minion": (
        "Minion data is a pre-aggregated monthly report (second-hand); there is no raw "
        "Minion log to parse. Read it with pandas (read_excel / read_csv) and pass the "
        "DataFrame to whichever analysis function you need."
    ),
}
