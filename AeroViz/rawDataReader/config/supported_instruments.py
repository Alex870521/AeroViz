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

    "APS_3321": {
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
            "Thermal OC": ["Thermal_OC"],
            "Thermal EC": ["Thermal_EC"],
            "Optical OC": ["Optical_OC"],
            "Optical EC": ["Optical_EC"],
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
    },

    "XRF": {
        "pattern": ["*.csv"],
        "freq": "1h",
        "deter_key": {
            "Al": ["Al"],
            "Si": ["Si"],
            "P": ["P"],
            "S": ["S"],
            "Cl": ["Cl"],
            "K": ["K"],
            "Ca": ["Ca"],
            "Ti": ["Ti"],
            "V": ["V"],
            "Cr": ["Cr"],
            "Mn": ["Mn"],
            "Fe": ["Fe"],
            "Ni": ["Ni"],
            "Cu": ["Cu"],
            "Zn": ["Zn"],
            "As": ["As"],
            "Se": ["Se"],
            "Br": ["Br"],
            "Rb": ["Rb"],
            "Sr": ["Sr"],
            "Y": ["Y"],
            "Zr": ["Zr"],
            "Mo": ["Mo"],
            "Ag": ["Ag"],
            "Cd": ["Cd"],
            "In": ["In"],
            "Sn": ["Sn"],
            "Sb": ["Sb"],
            "Te": ["Te"],
            "Cs": ["Cs"],
            "Ba": ["Ba"],
            "La": ["La"],
            "Ce": ["Ce"],
            "W": ["W"],
            "Pt": ["Pt"],
            "Au": ["Au"],
            "Hg": ["Hg"],
            "Tl": ["Tl"],
            "Pb": ["Pb"],
            "Bi": ["Bi"],
        },
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
            "XRF (Al, Ti, V, Cr, Mn, Fe)": ["Al", "Ti", "V", "Cr", "Mn", "Fe"],
        },
    },
}
