import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.pyplot import Figure, Axes
from pandas import DataFrame, read_json
from scipy.optimize import curve_fit
from pathlib import Path

from AeroViz import plot
from AeroViz.plot.utils import *
from AeroViz.tools import DataBase, DataReader, DataClassifier

# TODO: this file has to be reorganized

__all__ = ['chemical_enhancement',
		   'ammonium_rich',
		   'pie_IMPROVE',
		   'MLR_IMPROVE',
		   'fRH_plot',
		   ]


@set_figure
def chemical_enhancement(data_set: DataFrame = None,
						 data_std: DataFrame = None,
						 ax: Axes | None = None,
						 **kwargs
						 ) -> tuple[Figure, Axes]:
	fig, ax = plt.subplots() if ax is None else (ax.get_figure(), ax)

	ser_grp_sta, ser_grp_sta_std = DataClassifier(DataBase('/Users/chanchihyu/NTU/2020能見度計畫/data/All_data.csv'),
												  by='State')
	species = ['AS', 'AN', 'POC', 'SOC', 'Soil', 'SS', 'EC', 'ALWC']
	data_set, data_std = ser_grp_sta.loc[:, species], ser_grp_sta_std.loc[:, species]

	width = 0.20
	block = width / 4

	x = np.array([1, 2, 3, 4, 5, 6, 7])
	for i, state in enumerate(['Clean', 'Transition', 'Event']):
		val = np.array(data_set.iloc[i, :-1])
		std = (0,) * 7, np.array(data_std.iloc[i, :-1])

		plt.bar(x + (i + 1) * (width + block), val, yerr=std, width=width, color=Color.colors3[:-1],
				alpha=0.6 + (0.2 * i),
				edgecolor=None, capsize=None, label=state)

	ax.set(xlabel=r'$\bf Chemical\ species$',
		   ylabel=r'$\bf Mass\ concentration\ ({\mu}g/m^3)$',
		   xticks=x + 2 * (width + block),
		   xticklabels=species,
		   ylim=(0, 25),
		   title=r'$\bf Chemical\ enhancement$')

	ax.vlines(8, 0, 25, linestyles='--', colors='k')

	ax2 = ax.twinx()
	for i, state in enumerate(['Clean', 'Transition', 'Event']):
		val = np.array(data_set.iloc[i, -1])
		std = np.array([[0], [data_std.iloc[i, -1]]])
		plt.bar(8 + (i + 1) * (width + block), val, yerr=std, width=width, color='#96c8e6',
				alpha=0.6 + (0.2 * i), edgecolor=None, capsize=None, label=state)

	ax2.set(ylabel=r'$\bf Mass\ concentration\ ({\mu}g/m^3)$',
			ylim=(0, 100),
			xticks=x + 2 * (width + block),
			xticklabels=species
			)

	a = (np.array(data_set.loc['Event']) + np.array(data_set.loc['Transition'])) / 2
	b = (np.array(data_set.loc['Transition']) + np.array(data_set.loc['Clean'])) / 2
	c = np.array(data_set.loc['Event']) / np.array(data_set.loc['Transition'])
	d = np.array(data_set.loc['Transition']) / np.array(data_set.loc['Clean'])

	for i, (posa, posb, vala, valb) in enumerate(zip(a, b, c, d)):
		if i < 7:
			ax.text(i + 1.5, posa, '{:.2f}'.format(vala), fontsize=6, weight='bold', zorder=1)
			ax.text(i + 1.25, posb, '{:.2f}'.format(valb), fontsize=6, weight='bold', zorder=1)
		else:
			ax2.text(i + 1.5, posa, '{:.2f}'.format(vala), fontsize=6, weight='bold', zorder=1)
			ax2.text(i + 1.25, posb, '{:.2f}'.format(valb), fontsize=6, weight='bold', zorder=1)

	plt.show()

	return fig, ax


@set_figure
def ammonium_rich(df: DataFrame,
				  **kwargs
				  ) -> tuple[Figure, Axes]:
	df = df[['NH4+', 'SO42-', 'NO3-', 'PM25']].dropna().copy().div([18, 96, 62, 1])
	df['required_ammonium'] = df['NO3-'] + 2 * df['SO42-']

	fig, ax = plt.subplots()

	scatter = ax.scatter(df['required_ammonium'].to_numpy(), df['NH4+'].to_numpy(), c=df['PM25'].to_numpy(),
						 vmin=0, vmax=70, cmap='jet', marker='o', s=10, alpha=1)

	ax.axline((0, 0), slope=1., color='k', lw=2, ls='--', alpha=0.5, label='1:1')
	plt.text(0.97, 0.97, r'$\bf 1:1\ Line$', color='k', ha='right', va='top', transform=ax.transAxes)

	ax.set(xlim=(0, 1.2),
		   ylim=(0, 1.2),
		   xlabel=r'$\bf NO_{3}^{-}\ +\ 2\ \times\ SO_{4}^{2-}\ (mole\ m^{-3})$',
		   ylabel=r'$\bf NH_{4}^{+}\ (mole\ m^{-3})$',
		   title=kwargs.get('title', ''))

	color_bar = plt.colorbar(scatter, label=Unit('PM25'), extend='both')

	# fig.savefig(f'Ammonium_rich_{title}')
	plt.show()

	return fig, ax


def pie_IMPROVE():
	Species1 = ['AS_ext_dry', 'AN_ext_dry', 'OM_ext_dry', 'Soil_ext_dry', 'SS_ext_dry', 'EC_ext_dry']
	Species2 = ['AS_ext_dry', 'AN_ext_dry', 'OM_ext_dry', 'Soil_ext_dry', 'SS_ext_dry', 'EC_ext_dry', 'ALWC_ext']
	Species3 = ['AS_ext', 'AN_ext', 'OM_ext', 'Soil_ext', 'SS_ext', 'EC_ext']

	ser_grp_sta, _ = DataClassifier(DataBase(), by='State')

	ext_dry_dict = ser_grp_sta.loc[:, Species1]
	ext_amb_dict = ser_grp_sta.loc[:, Species2]
	ext_mix_dict = ser_grp_sta.loc[:, Species3]

	plot.donuts(data_set=ext_dry_dict, labels=['AS', 'AN', 'OM', 'Soil', 'SS', 'BC'], unit='Extinction')
	plot.donuts(data_set=ext_mix_dict, labels=['AS', 'AN', 'OM', 'Soil', 'SS', 'BC'], unit='Extinction')
	plot.donuts(data_set=ext_amb_dict, labels=['AS', 'AN', 'OM', 'Soil', 'SS', 'BC', 'ALWC'],
				unit='Extinction', colors=Color.colors2)


def MLR_IMPROVE(**kwargs):
	"""
	Perform multiple linear regression analysis and generate plots based on IMPROVE dataset.

	Parameters
	----------
	**kwargs : dict
		Additional keyword arguments for customization.

	Returns
	-------
	None

	Examples
	--------
	Example usage of MLR_IMPROVE function:

	>>> MLR_IMPROVE()

	Notes
	-----
	This function performs multiple linear regression analysis on the IMPROVE dataset and generates plots for analysis.

	- The function first selects specific species from the dataset and drops NaN values.
	- It calculates a 'Localized' value based on a multiplier and the sum of selected species.
	- Data from 'modified_IMPROVE.csv' and 'revised_IMPROVE.csv' are read and concatenated with the dataset.
	- Statistical analysis is performed using DataClassifier to calculate mean and standard deviation.
	- Plots are generated using linear_regression for Extinction vs. Revised/Modified/Localized and Pie.donuts for a
	  pie chart showing the distribution of species based on Extinction.

	"""
	species = ['Extinction', 'Scattering', 'Absorption',
			   'total_ext_dry', 'AS_ext_dry', 'AN_ext_dry', 'OM_ext_dry', 'Soil_ext_dry', 'SS_ext_dry', 'EC_ext_dry',
			   'AS', 'AN', 'POC', 'SOC', 'Soil', 'SS', 'EC', 'OM']

	df = DataBase('/Users/chanchihyu/NTU/2020能見度計畫/data/All_data.csv')[species].dropna().copy()

	# multiple_linear_regression(df, x=['AS', 'AN', 'POC', 'SOC', 'Soil', 'SS'], y='Scattering', add_constant=True)
	# multiple_linear_regression(df, x=['POC', 'SOC', 'EC'], y='Absorption', add_constant=True)
	# multiple_linear_regression(df, x=['AS', 'AN', 'POC', 'SOC', 'Soil', 'SS', 'EC'], y='Extinction', add_constant=False)

	multiplier = [2.675, 4.707, 11.6, 7.272, 0, 0.131, 10.638]
	df['Localized'] = df[['AS', 'AN', 'POC', 'SOC', 'Soil', 'SS', 'EC']].mul(multiplier).sum(axis=1)
	# TODO: remove name
	modify_IMPROVE = DataReader('modified_IMPROVE.csv')['total_ext_dry'].rename('Modified')
	revised_IMPROVE = DataReader('revised_IMPROVE.csv')['total_ext_dry'].rename('Revised')

	df = pd.concat([df, revised_IMPROVE, modify_IMPROVE], axis=1)

	n_df = df[['AS', 'AN', 'POC', 'SOC', 'Soil', 'SS', 'EC']].mul(multiplier)
	mean, std = DataClassifier(n_df, 'State')

	ser_grp_sta, _ = DataClassifier(DataBase(), by='State')
	mass_comp = ser_grp_sta.loc[:, ['AS', 'AN', 'POC', 'SOC', 'Soil', 'SS', 'EC']]

	# plot
	plot.linear_regression(df, x='Extinction', y=['Revised', 'Modified', 'Localized'], xlim=[0, 400], ylim=[0, 400],
						   regression=True, diagonal=True)
	plot.donuts(data_set=mass_comp, labels=['AS', 'AN', 'POC', 'SOC', 'Soil', 'SS', 'EC'],
				unit='PM25', colors=Color.colors3)
	plot.donuts(mean, labels=['AS', 'AN', 'POC', 'SOC', 'Soil', 'SS', 'EC'], unit='Extinction', colors=Color.colors3)


@set_figure
def fRH_plot(**kwargs) -> tuple[Figure, Axes]:
	frh = read_json(Path(__file__).parent.parent / 'utils' / 'fRH.json')

	def fitting_func(RH, a, b, c):
		f = a + b * (RH / 100) ** c
		return f

	x = frh.index.to_numpy()
	y = frh['fRHs'].to_numpy()

	result = curve_fit(fitting_func, x, y)
	params = result[0].tolist()
	val_fit = fitting_func(x, *params)

	fig, ax = plt.subplots(figsize=(3, 3))

	ax.plot(frh.index, frh['fRH'], 'k-o', ms=2, label='$f(RH)_{original}$')
	ax.plot(frh.index, frh['fRHs'], 'g-o', ms=2, label='$f(RH)_{small\\ mode}$')
	ax.plot(frh.index, frh['fRHl'], 'r-o', ms=2, label='$f(RH)_{large\\ mode}$')
	ax.plot(frh.index, frh['fRHSS'], 'b-o', ms=2, label='$f(RH)_{sea\\ salt}$')

	ax.set(xlim=(0, 100),
		   ylim=(1, None),
		   xlabel='$RH (\\%)$',
		   ylabel='$f(RH)$',
		   title=f'$Hygroscopic\\ growth\\ factor$'
		   )

	ax.grid(axis='y', color='gray', linestyle='dashed', linewidth=0.4, alpha=0.4)

	ax.legend()

	plt.show()
	# fig.savefig('fRH_plot')

	return fig, ax


if __name__ == '__main__':
	# chemical_enhancement()
	# MLR_IMPROVE()
	# ammonium_rich()
	fRH_plot()
