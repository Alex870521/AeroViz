from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.pyplot import Figure, Axes
from pandas import DataFrame

from AeroViz.plot.utils import *

__all__ = ['bar']


@set_figure(fw='bold')
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
			else:
				_ = ax.barh(groups_arr, widths, left=starts, height=0.7, color=colors[i], label=labels[i],
							edgecolor=None, capsize=None)
			if symbol:
				ax.bar_label(_, fmt=auto_label_pct, label_type='center', padding=0, fontsize=8, weight='bold')

	if style == "dispersed":
		width = 0.1
		block = width / 4

		for i in range(species):
			val = data[:, i]
			std = (0,) * groups, data_std[:, i]
			if orientation == 'va':
				_ = ax.bar(groups_arr + (i + 1) * (width + block), val, yerr=std, width=width, color=colors[i],
						   edgecolor=None, capsize=None)
			else:
				_ = ax.barh(groups_arr + (i + 1) * (width + block), val, xerr=std, height=width, color=colors[i],
							edgecolor=None, capsize=None)
			if symbol:
				ax.bar_label(_, fmt=auto_label_pct, label_type='center', padding=0, fontsize=8, weight='bold')

	if orientation == 'va':
		xticks = groups_arr + (species / 2 + 0.5) * (width + block) if style == "dispersed" else groups_arr
		ax.set_xticks(xticks, category_names, weight='bold')
		ax.set_ylabel(Unit(unit) if style == "dispersed" else '$Contribution (\\%)$')
		ax.set_ylim(0, None if style == "dispersed" else 100)
		ax.legend(labels, bbox_to_anchor=(1, 1), loc='upper left', prop={'size': 8})

	if orientation == 'ha':
		ax.invert_yaxis()
		yticks = groups_arr + 3.5 * (width + block) if style == "dispersed" else groups_arr
		ax.set_yticks(yticks, category_names, weight='bold')
		ax.set_xlabel(Unit(unit) if style == "dispersed" else '$Contribution (\\%)$')
		ax.set_xlim(0, None if style == "dispersed" else 100)
		ax.legend(labels, bbox_to_anchor=(1, 1), loc='upper left', prop={'size': 8})

	# fig.savefig(f"Barplot_{title}")

	plt.show()

	return fig, ax
