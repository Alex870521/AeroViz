# Description: Configuration file for rawDataReader

meta = {
    "NEPH": {
        "pattern": ["*.dat"],
        "freq": "5min",
        "deter_key": {"Scatter Coe. (550 nm)": ["G"]},
    },

    "Aurora": {
        "pattern": ["*.csv"],
        "freq": "1min",
        "deter_key": {"Scatter Coe. (550 nm)": ["G"]},
    },

    "SMPS": {
        "pattern": ["*.txt", "*.csv"],
        "freq": "6min",
        "deter_key": {"Bins": ["all"]},
    },

    "GRIMM": {
        "pattern": ["*.dat"],
        "freq": "6min",
        "deter_key": {"Bins": ["all"]},
    },

    "APS": {
        "pattern": ["*.txt"],
        "freq": "6min",
        "deter_key": {"Bins": ["all"]},
    },

    "AE33": {
        "pattern": ["[!ST|!CT|!FV]*[!log]_AE33*.dat"],
        "freq": "1min",
        "deter_key": {"BC Mass Conc. (880 nm)": ["BC6"]},
        "error_state": [],
    },

    "AE43": {
        "pattern": ["[!ST|!CT|!FV]*[!log]_AE43*.dat"],
        "freq": "1min",
        "deter_key": {"BC Mass Conc. (880 nm)": ["BC6"]},
        "error_state": [],
    },

    "BC1054": {
        "pattern": ["*.csv"],
        "freq": "1min",
        "deter_key": {"BC Mass Conc. (880 nm)": ["BC9"]},
        "error_state": [1, 2, 4, 8, 16, 32, 65536],
    },

    "MA350": {
        "pattern": ["*.csv"],
        "freq": "1min",
        "deter_key": {"BC Mass Conc. (880 nm)": ["BC5"]},
    },

    "BAM1020": {
        "pattern": ["*.csv"],
        "freq": "1h",
        "deter_key": {
            "Mass Conc.": ["Conc"]},
    },

    "TEOM": {
        "pattern": ["*.csv"],
        "freq": "6min",
        "deter_key": {
            "PM1.0 Mass Conc.": ["PM_Total"],
            "PM1.0 NV Mass Conc.": ["PM_NV"],
        },
    },

    "OCEC": {
        "pattern": ["*LCRes.csv"],
        "freq": "1h",
        "deter_key": {
            "Thermal OC & EC": ["Thermal_OC", "Thermal_EC"],
            "Optical OC & EC": ["Optical_OC", "Optical_EC"],
        },
    },

    "IGAC": {
        "pattern": ["*.csv"],
        "freq": "1h",
        "deter_key": {
            "Na+": ["Na+"],
            "NH4+": ["NH4+"],
            "K+": ["K+"],
            "Mg2+": ["Mg2+"],
            "Ca2+": ["Ca2+"],
            "Cl-": ["Cl-"],
            "NO2-": ["NO2-"],
            "NO3-": ["NO3-"],
            "SO42-": ["SO42-"],
            "Main Salt (NH4+, NO3-, SO42-)": ["NO3-", "SO42-", "NH4+"],
        },
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

    "XRF": {
        "pattern": ["*.csv"],
        "freq": "1h",
        "deter_key": {
            "Several trace element (Al, Si, Ti, V, Cr, Mn, Fe)": ["Al", "Si", "Ti", "V", "Cr", "Mn", "Fe"],

        },
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

    "VOC": {
        "pattern": ["*.csv"],
        "freq": "1h",
        "key": [
            'Benzene', 'Toluene', 'Ethylbenzene', 'm/p-Xylene', 'o-Xylene', 'Ethane', 'Propane', 'Isobutane',
            'n-Butane', 'Isopentane', 'n-Pentane', 'n-Hexane', 'n-Heptane', 'n-Octane', 'n-Nonane', 'n-Decane',
            'n-Undecane', 'n-Dodecane', 'Ethylene', 'Propylene', '1-Butene', 't-2-Butene', 'cis-2-Butene',
            '1-Pentene', 't-2-Pentene', 'cis-2-Pentene', '1-Hexene', 'Acetylene', 'Cyclopentane', 'Methylcyclopentane',
            'Cyclohexane', 'Methylcyclohexane', 'Isoprene', '2,2-Dimethylbutane', '2,3-Dimethylbutane',
            '2-Methylpentane', '3-Methylpentane', '2,4-Dimethylpentane', '2-Methylhexane', '2,3-Dimethylpentane',
            '3-Methylheptane', '2,2,4-Trimethylpentane', '2,3,4-Trimethylpentane', '2-Methylheptane', '3-Methylhexane',
            'Styrene', 'Isopropylbenzene', 'n-Propylbenzene', 'm-Ethyltoluene', 'p-Ethyltoluene', 'm-Diethylbenzene',
            'p-Diethylbenzene', '1,3,5-Trimethylbenzene', 'o-Ethyltoluene', '1,2,4-Trimethylbenzene',
            '1,2,3-Trimethylbenzene',
            '1.2-DCB', '1.4-DCB', '1.3-Butadiene', '1-Octene', '2-Ethyltoluene', '3.4-Ethyltoluene', 'Acetaldehyde',
            'Acetone', 'Butyl Acetate', 'Ethanol', 'Ethyl Acetate', 'Hexane', 'IPA', 'Iso-Propylbenzene',
            'PCE', 'Propene', 'TCE', 'VCM',
        ],
        "deter_key": None,
    },

    "EPA": {
        "pattern": ["*.csv"],
        "freq": "1h",
        "deter_key": {"Items": ["all"]},
    },

    "Minion": {
        "pattern": ["*.csv", "*.xlsx"],
        "freq": "1h",
        "deter_key": {
            "Main Salt (Na+, NH4+, Cl-, NO3-, SO42-)": ["Na+", "NH4+", "Cl-", "NO3-", "SO42-"],
            "Several trace element (Al, Ti, V, Cr, Mn, Fe)": ["Al", "Ti", "V", "Cr", "Mn", "Fe"],
        },
    },
}
