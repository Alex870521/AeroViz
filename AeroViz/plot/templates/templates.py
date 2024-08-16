from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.pyplot import Figure, Axes
from pandas import DataFrame

from AeroViz.plot.utils import *

__all__ = [
	'pie',
	'donuts',
	'violin',
	'bar',
]


def _auto_label_pct(pct,
					symbol: bool = True,
					include_pct: bool = False,
					ignore: Literal["inner", "outer"] = 'inner',
					value: float = 2):
	if not symbol:
		return ''
	cond = pct <= value if ignore == 'inner' else pct > value
	label = '' if cond else '{:.1f}'.format(pct)
	return '' if label == '' else label + '%' if include_pct else label


@set_figure(fs=8, fw='bold')
def pie(data_set: DataFrame | dict,
		labels: list[str],
		unit: str,
		style: Literal["pie", 'donut'],
		ax: Axes | None = None,
		symbol: bool = True,
		**kwargs) -> tuple[Figure, Axes]:
	"""
	Create a pie or donut chart based on the provided data.

	Parameters
	----------
	data_set : pd.DataFrame | dict
		A pandas DataFrame or dictionary mapping category names to a list of species.
		If a DataFrame is provided, the index represents the categories, and each column contains species data.
		If a dictionary is provided, it maps category names to lists of species data.
		It is assumed that all lists or DataFrame columns contain the same number of entries as the *labels* list.
	labels : list of str
		The labels for each category.
	unit : str
		The unit to display in the center of the donut chart.
	style : Literal["pie", 'donut']
		The style of the chart, either 'pie' for a standard pie chart or 'donut' for a donut chart.
	ax : plt.Axes or None, optional
		The Axes object to plot the chart onto. If None, a new figure and Axes will be created.
	symbol : bool, optional
		Whether to display values for each species in the chart.
	**kwargs
		Additional keyword arguments to be passed to the plotting function.

	Returns
	-------
	matplotlib.axes.Axes
		The Axes object containing the violin plot.

	Notes
	-----
	- If *data_set* is a dictionary, it should contain lists of species that correspond to each category in *labels*.
	- The length of each list in *data_set* or the number of columns in the DataFrame should match the length of the *labels* list.

	Examples
	--------
	>>> data_set = {'Category 1': [10, 20, 30], 'Category 2': [15, 25, 35]}
	>>> labels = ['Species 1', 'Species 2', 'Species 3']
	>>> pie(data_set, labels, unit='kg', style='pie', symbol=True)
	"""
	if isinstance(data_set, DataFrame):
		category_names = list(data_set.index)
		data = data_set.to_numpy()

		pies, species = data.shape

	elif isinstance(data_set, dict):
		category_names = list(data_set.keys())
		data = np.array(list(data_set.values()))

		pies, species = data.shape

	else:
		raise ValueError('data_set must be a DataFrame or a dictionary.')

	colors = kwargs.get('colors') or (Color.colors1 if species == 6 else Color.getColor(num=species))

	radius = 4
	width = 4 if style == 'pie' else 1

	text = [''] * pies if style == 'pie' else [Unit(unit) + '\n\n' + '{:.2f}'.format(x) for x in data.sum(axis=1)]
	pct_distance = 0.6 if style == 'pie' else 0.88

	fig, ax = plt.subplots(1, pies, figsize=((pies * 2) + 1, 2)) if ax is None else (ax.get_figure(), ax)

	if pies == 1:
		ax = [ax]

	for i in range(pies):
		ax[i].pie(data[i], labels=None, colors=colors, textprops=None,
				  autopct=lambda pct: _auto_label_pct(pct, symbol=symbol, include_pct=True),
				  pctdistance=pct_distance, radius=radius, wedgeprops=dict(width=width, edgecolor='w'))

		ax[i].pie(data[i], labels=None, colors=colors, textprops=None,
				  autopct=lambda pct: _auto_label_pct(pct, symbol=symbol, ignore='outer', include_pct=True),
				  pctdistance=1.3, radius=radius, wedgeprops=dict(width=width, edgecolor='w'))
		ax[i].axis('equal')
		ax[i].text(0, 0, text[i], ha='center', va='center')
		ax[i].set_title(category_names[i])

	ax[-1].legend(labels, loc='center left', prop={'weight': 'bold'}, bbox_to_anchor=(1, 0, 1.15, 1))

	# fig.savefig(f"pie_{style}_{title}")

	plt.show()

	return fig, ax


@set_figure(fs=8, fw='bold')
def donuts(data_set: DataFrame | dict,
		   labels: list[str],
		   unit: str,
		   ax: Axes | None = None,
		   symbol=True,
		   **kwargs) -> tuple[Figure, Axes]:
	"""
	Plot a donut chart based on the data set.

	Parameters
	----------
	data_set : pd.DataFrame | dict
		A pandas DataFrame or a dictionary mapping category names to a list of species.
		If a DataFrame is provided, the index represents the categories, and each column contains species data.
		If a dictionary is provided, it maps category names to lists of species data.
		It is assumed that all lists or DataFrame columns contain the same number of entries as the *labels* list.
	labels : list of str
		The category labels.
	unit : str
		The unit to be displayed in the center of the donut chart.
	ax : matplotlib.axes.Axes, optional
		The axes to plot on. If None, the current axes will be used (default).
	symbol : bool, optional
		Whether to display values for each species (default is True).
	**kwargs : dict, optional
		Additional keyword arguments to pass to the matplotlib pie chart function.

	Returns
	-------
	matplotlib.axes.Axes
		The axes containing the donut chart.
	"""

	if isinstance(data_set, DataFrame):
		category_names = list(data_set.index)
		data = data_set.to_numpy()

		pies, species = data.shape

	elif isinstance(data_set, dict):
		category_names = list(data_set.keys())
		data = np.array(list(data_set.values()))

		pies, species = data.shape

	else:
		raise ValueError('data_set must be a DataFrame or a dictionary.')

	colors1 = kwargs.get('colors') or (Color.colors1 if species == 6 else Color.getColor(num=species))
	colors2 = Color.adjust_opacity(colors1, 0.8)
	colors3 = Color.adjust_opacity(colors1, 0.6)

	fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

	ax.pie(data[2], labels=None, colors=colors1, textprops=None,
		   autopct=lambda pct: _auto_label_pct(pct, symbol=symbol, include_pct=True),
		   pctdistance=0.9, radius=14, wedgeprops=dict(width=3, edgecolor='w'))

	ax.pie(data[1], labels=None, colors=colors2, textprops=None,
		   autopct=lambda pct: _auto_label_pct(pct, symbol=symbol, include_pct=True),
		   pctdistance=0.85, radius=11, wedgeprops=dict(width=3, edgecolor='w'))

	ax.pie(data[0], labels=None, colors=colors3, textprops=None,
		   autopct=lambda pct: _auto_label_pct(pct, symbol=symbol, include_pct=True),
		   pctdistance=0.80, radius=8, wedgeprops=dict(width=3, edgecolor='w'))

	text = (Unit(f'{unit}') + '\n\n' +
			'Event : ' + "{:.2f}".format(np.sum(data[2])) + '\n' +
			'Transition : ' + "{:.2f}".format(np.sum(data[1])) + '\n' +
			'Clean : ' + "{:.2f}".format(np.sum(data[0])))

	ax.text(0, 0, text, ha='center', va='center')
	ax.axis('equal')

	ax.set_title(kwargs.get('title', ''))

	ax.legend(labels, loc='center', prop={'weight': 'bold'}, title_fontproperties={'weight': 'bold'},
			  title=f'Outer : {category_names[2]}' + '\n' + f'Middle : {category_names[1]}' + '\n' + f'Inner : {category_names[0]}',
			  bbox_to_anchor=(0.8, 0, 0.5, 1))

	# fig.savefig(f"donuts_{title}")

	plt.show()

	return fig, ax


@set_figure(figsize=(5, 4))
def bar(data_set: DataFrame | dict,
		data_std: DataFrame | None,
		labels: list[str],
		unit: str,
		style: Literal["stacked", "dispersed"] = "dispersed",
		orientation: Literal["va", "ha"] = 'va',
		ax: Axes | None = None,
		symbol=True,
		**kwargs
		) -> tuple[Figure, Axes]:
	"""
	Parameters
	----------
	data_set : pd.DataFrame or dict
		A mapping from category names to a list of species mean or a DataFrame with columns as categories and values as means.
	data_std : pd.DataFrame or None
		A DataFrame with standard deviations corresponding to data_set, or None if standard deviations are not provided.
	labels : list of str
		The species names.
	unit : str
		The unit for the values.
	style : {'stacked', 'dispersed'}, default 'dispersed'
		Whether to display the bars stacked or dispersed.
	orientation : {'va', 'ha'}, default 'va'
		The orientation of the bars, 'va' for vertical and 'ha' for horizontal.
	ax : plt.Axes or None, default None
		The Axes object to plot on. If None, a new figure and Axes are created.
	symbol : bool, default True
		Whether to display values for each bar.
	kwargs : dict
		Additional keyword arguments passed to the barplot function.

	Returns
	-------
	matplotlib.Axes
		The Axes object containing the plot.

	"""
	# data process
	data = data_set.values

	if data_std is None:
		data_std = np.zeros(data.shape)
	else:
		data_std = data_std.values

	groups, species = data.shape
	groups_arr = np.arange(groups)
	species_arr = np.arange(species)

	total = np.array([data.sum(axis=1), ] * species).T

	pct_data = data / total * 100
	data_cum = pct_data.cumsum(axis=1)

	# figure info
	category_names = kwargs.get('ticks') or list(data_set.index)
	title = kwargs.get('title', '')
	colors = kwargs.get('colors') or (Color.colors1 if species == 6 else Color.getColor(num=species))

	fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

	if style == "stacked":
		for i in range(species):
			widths = pct_data[:, i]
			starts = data_cum[:, i] - pct_data[:, i]

			if orientation == 'va':
				_ = ax.bar(groups_arr, widths, bottom=starts, width=0.7, color=colors[i], label=labels[i],
						   edgecolor=None, capsize=None)
			if orientation == 'ha':
				_ = ax.barh(groups_arr, widths, left=starts, height=0.7, color=colors[i], label=labels[i],
							edgecolor=None, capsize=None)
			if symbol:
				ax.bar_label(_, fmt=_auto_label_pct, label_type='center', padding=0, fontsize=10, weight='bold')

	if style == "dispersed":
		width = 0.1
		block = width / 4

		for i in range(species):
			val = data[:, i]
			std = (0,) * groups, data_std[:, i]
			if orientation == 'va':
				_ = ax.bar(groups_arr + (i + 1) * (width + block), val, yerr=std, width=width, color=colors[i],
						   edgecolor=None, capsize=None)
			if orientation == 'ha':
				_ = ax.barh(groups_arr + (i + 1) * (width + block), val, xerr=std, height=width, color=colors[i],
							edgecolor=None, capsize=None)
			if symbol:
				ax.bar_label(_, fmt=_auto_label_pct, label_type='center', padding=0, fontsize=8, weight='bold')

	if orientation == 'va':
		xticks = groups_arr + (species / 2 + 0.5) * (width + block) if style == "dispersed" else groups_arr
		ax.set_xticks(xticks, category_names, weight='bold')
		ax.set_ylabel(Unit(unit) if style == "dispersed" else '$Contribution (\\%)$')
		ax.set_ylim(0, None if style == "dispersed" else 100)
		ax.legend(labels, bbox_to_anchor=(1, 1), loc='upper left', prop={'size': 12})

	if orientation == 'ha':
		ax.invert_yaxis()
		yticks = groups_arr + 3.5 * (width + block) if style == "dispersed" else groups_arr
		ax.set_yticks(yticks, category_names, weight='bold')
		ax.set_xlabel(Unit(unit) if style == "dispersed" else '$Contribution (\\%)$')
		ax.set_xlim(0, None if style == "dispersed" else 100)
		ax.legend(labels, bbox_to_anchor=(1, 1), loc='upper left', prop={'size': 12})

	# fig.savefig(f"Barplot_{title}")

	plt.show()

	return fig, ax


@set_figure
def violin(data_set: DataFrame | dict,
		   unit: str,
		   ax: Axes | None = None,
		   **kwargs
		   ) -> tuple[Figure, Axes]:
	"""
	Generate a violin plot for multiple data sets.

	Parameters
	----------
	data_set : pd.DataFrame or dict
		A mapping from category names to pandas DataFrames containing the data.
	unit : str
		The unit for the data being plotted.
	ax : matplotlib.axes.Axes, optional
		The Axes object to draw the plot onto. If not provided, a new figure will be created.
	**kwargs : dict
		Additional keyword arguments to be passed to the violinplot function.

	Returns
	-------
	matplotlib.axes.Axes
		The Axes object containing the violin plot.

	"""
	fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

	data = data_set.to_numpy()

	data = data[~np.isnan(data).any(axis=1)]

	grps = data.shape[1]

	width = 0.6
	block = width / 2
	x_position = np.arange(grps)

	plt.boxplot(data, positions=x_position, widths=0.15,
				showfliers=False, showmeans=True, meanline=False, patch_artist=True,
				capprops=dict(linewidth=0),
				whiskerprops=dict(linewidth=1.5, color='k', alpha=1),
				boxprops=dict(linewidth=1.5, color='k', facecolor='#4778D3', alpha=1),
				meanprops=dict(marker='o', markeredgecolor='black', markerfacecolor='white', markersize=6),
				medianprops=dict(linewidth=1.5, ls='-', color='k', alpha=1))

	sns.violinplot(data=data, density_norm='area', color='#4778D3', inner=None)

	for violin, alpha in zip(ax.collections[:], [0.5] * len(ax.collections[:])):
		violin.set_alpha(alpha)
		violin.set_edgecolor(None)

	plt.scatter(x_position, data.mean(), marker='o', facecolor='white', edgecolor='k', s=10)

	xlim = kwargs.get('xlim') or (x_position[0] - (width / 2 + block), x_position[-1] + (width / 2 + block))
	ylim = kwargs.get('ylim') or (0, None)
	xlabel = kwargs.get('xlabel') or ''
	ylabel = kwargs.get('ylabel') or Unit(unit)
	xticks = kwargs.get('xticks') or [x.replace('-', '\n') for x in list(data_set.keys())]

	ax.set(xlim=xlim, ylim=ylim, xlabel=xlabel, ylabel=ylabel, title=kwargs.get('title'))
	ax.set_xticks(x_position, xticks, fontweight='bold', fontsize=12)

	# fig.savefig(f'Violin_{unit}')

	plt.show()

	return fig, ax
