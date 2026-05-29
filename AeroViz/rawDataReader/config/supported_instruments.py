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

    "VOC": {
        "pattern": ["*.csv"],
        "freq": "1h",
        # No species `key` list here: the VOC reader no longer filters columns.
        # The supported-species list (with MW/MIR/SOAP/KOH coefficients) lives
        # solely in AeroViz/dataProcess/VOC/support_voc.json and is enforced by
        # the downstream process (AeroViz.voc), keeping a single source of truth.
    },

    "EPA": {
        "pattern": ["*.csv"],
        "freq": "1h",
    },

    "Minion": {
        "pattern": ["*.csv", "*.xlsx"],
        "freq": "1h",
    },
}
