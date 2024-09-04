# Description: Configuration file for rawDataReader

meta = {
    "NEPH": {
        "pattern": "*.dat",
        "freq": "5min",
        "deter_key": {"Scatter Coe. (550 nm)": ["G"]},
    },

    "Aurora": {
        "pattern": "*.csv",
        "freq": "1min",
        "deter_key": {"Scatter Coe. (550 nm)": ["G"]},
    },

    "SMPS_TH": {
        "pattern": "*.txt",
        "freq": "6min",
        "deter_key": {"Bins": ["all"]},
    },

    "SMPS_genr": {
        "pattern": "*.txt",
        "freq": "6min",
        "deter_key": {"Bins": ["all"]},
    },

    "SMPS_aim11": {
        "pattern": "*.csv",
        "freq": "6min",
        "deter_key": {"Bins": ["all"]},
    },

    "GRIMM": {
        "pattern": "*.dat",
        "freq": "6min",
        "deter_key": {"Bins": ["all"]},
    },

    "APS_3321": {
        "pattern": "*.TXT",
        "freq": "6min",
        "deter_key": {"Bins": ["all"]},
    },

    "AE33": {
        "pattern": "[!ST|!CT|!FV]*[!log]_AE33*.dat",
        "freq": "1min",
        "deter_key": {"BC Mass Conc. (880 nm)": ["BC6"]},
        "error_state": [],
    },

    "AE43": {
        "pattern": "[!ST|!CT|!FV]*[!log]_AE43*.dat",
        "freq": "1min",
        "deter_key": {"BC Mass Conc. (880 nm)": ["BC6"]},
        "error_state": [],
    },

    "BC1054": {
        "pattern": "*.csv",
        "freq": "1min",
        "deter_key": {"BC Mass Conc. (880 nm)": ["BC9"]},
        "error_state": [1, 2, 4, 8, 16, 32, 65536],
    },

    "MA350": {
        "pattern": "*.csv",
        "freq": "1min",
        "deter_key": {"BC Mass Conc. (880 nm)": ["BC5"]},
    },

    "TEOM": {
        "pattern": "*.csv",
        "freq": "6min",
        "deter_key": {
            "PM1.0 Mass Conc.": ["PM_Total"],
            "PM1.0 NV Mass Conc.": ["PM_NV"],
        },
    },

    "Sunset_OCEC": {
        "pattern": "*LCRes.csv",
        "freq": "1h",
        "deter_key": {
            "Thermal OC/EC": ["Thermal_EC", "Thermal_OC"],
            "Thermal OC": ["Thermal_OC"],
            "Thermal EC": ["Thermal_EC"],
            "Optical OC/EC": ["Optical_EC", "Optical_OC"],
            "Optical OC": ["Optical_OC"],
            "Optical EC": ["Optical_EC"],
        },
    },

    "IGAC": {
        "pattern": "*.csv",
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
    },

    "VOC": {
        "pattern": "*.csv",
        "freq": "1h",
        "key": ['Ethane', 'Propane', 'Isobutane', 'n-Butane', 'Cyclopentane', 'Isopentane',
                'n-Pentane', '2,2-Dimethylbutane', '2,3-Dimethylbutane', '2-Methylpentane',
                '3-Methylpentane', 'n-Hexane', 'Methylcyclopentane', '2,4-Dimethylpentane',
                'Cyclohexane', '2-Methylhexane', '2-Methylhexane', '3-Methylheptane',
                '2,2,4-Trimethylpentane', 'n-Heptane', 'Methylcyclohexane',
                '2,3,4-Trimethylpentane', '2-Methylheptane', '3-Methylhexane', 'n-Octane',
                'n-Nonane', 'n-Decane', 'n-Undecane', 'Ethylene', 'Propylene', 't-2-Butene',
                '1-Butene', 'cis-2-Butene', 't-2-Pentene', '1-Pentene', 'cis-2-Pentene',
                'isoprene', 'Acetylene', 'Benzene', 'Toluene', 'Ethylbenzene', 'm,p-Xylene',
                'Styrene', 'o-Xylene', 'Isopropylbenzene', 'n-Propylbenzene', 'm-Ethyltoluene',
                'p-Ethyltoluene', '1,3,5-Trimethylbenzene', 'o-Ethyltoluene',
                '1,2,4-Trimethylbenzene', '1,2,3-Trimethylbenzene', 'm-Diethylbenzene',
                'p-Diethylbenzene'],

        "key_2": ['Isopentane', 'Hexane', '2-Methylhexane', '3-Methylhexane', '2-Methylheptane', '3-Methylheptane',
                  'Propene', '1.3-Butadiene', 'Isoprene', '1-Octene',
                  'Benzene', 'Toluene', 'Ethylbenzene', 'm.p-Xylene', 'o-Xylene', 'Iso-Propylbenzene', 'Styrene',
                  'n-Propylbenzene', '3.4-Ethyltoluene', '1.3.5-TMB', '2-Ethyltoluene', '1.2.4-TMB', '1.2.3-TMB',
                  'Acetaldehyde', 'Ethanol', 'Acetone', 'IPA', 'Ethyl Acetate', 'Butyl Acetate',
                  'VCM', 'TCE', 'PCE', '1.4-DCB', '1.2-DCB'],
        "deter_key": None,
    },

    "Table": {
        "pattern": "*.csv",
        "freq": "1h",
        "deter_key": None,
    },

    "EPA_vertical": {
        "pattern": "*.csv",
        "freq": "1h",
        "deter_key": None,
    },

    "Minion": {
        "pattern": "*.csv",
        "freq": "1h",
        "deter_key": None,
    },
}
