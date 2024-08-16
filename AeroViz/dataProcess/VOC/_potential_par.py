from datetime import datetime as dtm
from pandas import DataFrame, to_datetime, read_json
from pathlib import Path
import pickle as pkl

import numpy as np


def _basic(_df_voc):
	## parameter
	_keys = _df_voc.keys()

	with (Path(__file__).parent / 'voc_par.pkl').open('rb') as f:
		_par = pkl.load(f)
		_MW, _MIR, _SOAP, _KOH = _par.loc['MW', _keys], _par.loc['MIR', _keys], _par.loc['SOAP', _keys], _par.loc[
			'KOH', _keys]

	with (Path(__file__).parent / 'voc_par.json').open('r', encoding='utf-8', errors='ignore') as f:
		_parr = read_json(f)
		_MW, _MIR, _SOAP, _KOH = _par.loc['MW', _keys], _par.loc['MIR', _keys], _par.loc['SOAP', _keys], _par.loc[
			'KOH', _keys]

	_voc_clasfy = {
		'alkane_total': ['Isopentane', 'n-Butane', '2-Methylhexane', 'Cyclopentane', '3-Methylpentane',
						 '2,3-Dimethylbutane',
						 '2-Methylheptane', 'n-Nonane', 'Methylcyclohexane', '2,4-Dimethylpentane', '2-Methylpentane',
						 'n-Decane',
						 'n-Heptane', 'Cyclohexane', 'n-Octane', 'Isobutane', '2,2-Dimethylbutane',
						 'Methylcyclopentane', 'n-Hexane',
						 '2,3,4-Trimethylpentane', '3-Methylhexane', 'n-Undecane', '3-Methylheptane', 'Hexane',
						 '2,2,4-Trimethylpentane', 'n-Pentane', 'Ethane', 'Propane'],

		'alkane_total': ['Isoprene', '1-Butene', 'cis-2-Butene', 'Propene', '1.3-Butadiene',
						 't-2-Butene', 'cis-2-Pentene', 'Propylene', 'isoprene', '1-Pentene',
						 'Ethylene', 't-2-Pentene', '1-Octene'],

		'aromatic_total': ['o-Ethyltoluene', '1,3,5-Trimethylbenzene', 'Ethylbenzene', 'm,p-Xylene', 'n-Propylbenzene',
						   'Benzene', 'Toluene', '1.2.4-TMB', 'Styrene', 'p-Ethyltoluene', 'o-Xylene',
						   'm-Diethylbenzene',
						   '1.2.3-TMB', 'Isopropylbenzene', 'm-Ethyltoluene', '2-Ethyltoluene', '1.3.5-TMB',
						   'Iso-Propylbenzene',
						   '3.4-Ethyltoluene', 'p-Diethylbenzene', '1,2,4-Trimethylbenzene', 'm.p-Xylene',
						   '1,2,3-Trimethylbenzene'],

		'alkyne_total': ['Acetylene'],

		'OVOC': ['Acetaldehyde', 'Ethanol', 'Acetone', 'IPA', 'Ethyl Acetate', 'Butyl Acetate'],

		'ClVOC': ['VCM', 'TCE', 'PCE', '1.4-DCB', '1.2-DCB'],
	}

	_df_MW = (_df_voc * _MW).copy()
	_df_dic = {
		'Conc': _df_voc.copy(),
		'OFP': _df_MW / 48 * _MIR,
		'SOAP': _df_MW / 24.5 * _SOAP / 100 * 0.054,
		'LOH': _df_MW / 24.5 / _MW * 0.602 * _KOH,
	}

	## calculate
	_out = {}
	for _nam, _df in _df_dic.items():

		_df_out = DataFrame(index=_df_voc.index)

		for _voc_nam, _voc_lst in _voc_clasfy.items():
			_lst = list(set(_keys) & set(_voc_lst))
			if len(_lst) == 0: continue

			_df_out[_voc_nam] = _df[_lst].sum(axis=1, min_count=1)

		_df_out['Total'] = _df.sum(axis=1, min_count=1)

		_out[_nam] = _df_out

	return _out
