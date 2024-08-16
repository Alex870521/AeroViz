from datetime import datetime
from typing import Literal

import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.pyplot import Figure, Axes
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from pandas import DataFrame, date_range, Timestamp

from AeroViz.plot.utils import *

__all__ = ['timeseries', 'timeseries_template']

default_bar_kws = dict(
	width=0.0417,
	edgecolor=None,
	linewidth=0,
	cmap='jet',
)

default_scatter_kws = dict(
	marker='o',
	s=5,
	edgecolor=None,
	linewidths=0.3,
	alpha=0.9,
	cmap='jet',
)

default_insert_kws = dict(
	width="1.5%",
	height="100%",
	loc='lower left',
	bbox_to_anchor=(1.01, 0, 1.2, 1),
	borderpad=0
)

default_plot_kws = dict()

default_cbar_kws = dict()


def _scatter(ax, df, _y, _c, scatter_kws, cbar_kws, inset_kws):
	if _c is None or _c not in df.columns:
		scatter_kws.pop('cmap')
		ax.scatter(df.index, df[_y], **scatter_kws)
	else:
		ax.scatter(df.index, df[_y], c=df[_c], **scatter_kws)
		cax = inset_axes(ax, **inset_kws)

		# Filter the children to find ScalarMappable objects
		mappable_objects = [child for child in ax.get_children() if isinstance(child, ScalarMappable)]

		# Use the first mappable object for the colorbar
		if mappable_objects:
			plt.colorbar(mappable=mappable_objects[0], cax=cax, **cbar_kws)
		else:
			print("No mappable objects found.")


def _bar(ax, df, _y, _c, bar_kws, cbar_kws, inset_kws):
	scalar_map, colors = Color.color_maker(df[_c].values, cmap=bar_kws.pop('cmap'))
	ax.bar(df.index, df[_y], color=scalar_map.to_rgba(colors), **bar_kws)
	cax = inset_axes(ax, **inset_kws)
	plt.colorbar(mappable=scalar_map, cax=cax, **cbar_kws)


def _plot(ax, df, _y, _color, plot_kws):
	ax.plot(df.index, df[_y], color=_color, **plot_kws)


def combine_legends(axes_list: list[Axes]) -> tuple[list, list]:
	return (
		[legend for axes in axes_list for legend in axes.get_legend_handles_labels()[0]],
		[label for axes in axes_list for label in axes.get_legend_handles_labels()[1]]
	)


@set_figure(fs=8, autolayout=False)
def timeseries(df: DataFrame,
			   y: list[str] | str,
			   y2: list[str] | str = None,
			   c: list[str] | str = None,
			   # color: list[str] | str = None,
			   rolling: str | int | None = None,
			   times: list[datetime | Timestamp | str] = None,
			   freq: str = '1MS',
			   style: list[Literal['scatter', 'bar', 'line']] | str | None = None,
			   ax: Axes | None = None,
			   set_xaxis_visible: bool | None = None,
			   legend_loc: Literal['best', 'upper right', 'upper left', 'lower left', 'lower right'] = 'best',
			   legend_ncol: int = 1,
			   **kwargs
			   ) -> tuple[Figure, Axes]:
	"""
	Plot the timeseries data with the option of scatterplot, barplot, and lineplot.

	Parameters
	-----------
	df : DataFrame
	The data to plot.
	y : list[str] | str
		The primary y-axis data columns.
	y2 : list[str] | str, optional
		The secondary y-axis data columns. Defaults to None.
	c : str, optional
		The column for color mapping or the color. Defaults to None.
	rolling : str | int | None, optional
		Rolling window size for smoothing. Defaults to None.
	times : tuple[datetime, datetime] | tuple[Timestamp, Timestamp], optional
		Time range for the data. Defaults to None.
	freq : str, optional
		Frequency for x-axis ticks. Defaults to '2MS'.
	style : Literal['scatter', 'bar', 'line'] | None, optional
		Style of the plot. Defaults to 'scatter'.
	ax : Axes | None, optional
		Matplotlib Axes object to plot on. Defaults to None.
	set_xaxis_visible : bool | None, optional
		Whether to set x-axis visibility. Defaults to None.
	legend_loc : Literal['best', 'upper right', 'upper left', 'lower left', 'lower right'], optional
		Location of the legend. Defaults to 'best'.
	legend_ncol : int, optional
		Number of columns in the legend. Defaults to 1.
	**kwargs : Additional keyword arguments for customization.
		fig_kws : dict, optional
			Additional keyword arguments for the figure. Defaults to {}.
		scatter_kws : dict, optional
			Additional keyword arguments for the scatter plot. Defaults to {}.
		bar_kws : dict, optional
			Additional keyword arguments for the bar plot. Defaults to {}.
		ax_plot_kws : dict, optional
			Additional keyword arguments for the primary y-axis plot. Defaults to {}.
		ax2_plot_kws : dict, optional
			Additional keyword arguments for the secondary y-axis plot. Defaults to {}.
		cbar_kws : dict, optional
			Additional keyword arguments for the colorbar. Defaults to {}.
		inset_kws : dict, optional
			Additional keyword arguments for the inset axes. Defaults to {}.

	Returns
	-------
	ax : AxesSubplot
		Matplotlib AxesSubplot.

	Example
	-------
	>>> timeseries(df, y='WS', c='WD', scatter_kws=dict(cmap='hsv'), cbar_kws=dict(ticks=[0, 90, 180, 270, 360]), ylim=[0, None])
	"""
	# Set the time

	if times is not None:
		st_tm, fn_tm = map(Timestamp, times)
	else:
		try:
			st_tm, fn_tm = df.index[0], df.index[-1]
		except IndexError:
			raise IndexError("The DataFrame is empty. Please provide a valid DataFrame.")

	# Apply rolling window if specified
	df = df.loc[st_tm:fn_tm] if rolling is None else (
		df.loc[st_tm:fn_tm].rolling(window=rolling, min_periods=1).mean(numeric_only=True))

	# Initialize figure and axis if not provided
	fig, ax = plt.subplots(**{**{'figsize': (6, 2)}, **kwargs.get('fig_kws', {})}) if ax is None else (
		ax.get_figure(), ax)

	# Ensure y, y2, c, and style are lists
	y = [y] if isinstance(y, str) else y
	y2 = [y2] if isinstance(y2, str) else y2 if y2 is not None else []
	c = [c] if isinstance(c, str) else c if c is not None else [None] * (len(y) + len(y2))
	style = [style] if isinstance(style, str) else style if style is not None else ['plot'] * (len(y) + len(y2))

	if len(c) != len(y) + len(y2):
		raise ValueError("The length of c must match the combined length of y and y2")

	if len(style) != len(y) + len(y2):
		raise ValueError("The length of style must match the combined length of y and y2")

	# Create a secondary y-axis if y2 is not empty
	ax2 = ax.twinx() if y2 else None

	# # Set color cycle
	ax.set_prop_cycle(Color.color_cycle)
	if y2:
		ax2.set_prop_cycle(Color.color_cycle[len(y):])

	if y2 and ('scatter' or 'bar') in style:
		fig.subplots_adjust(right=0.8)

	for i, _c in enumerate(c):
		if _c is not None and _c in df.columns:
			style[i] = 'scatter'

	for i, (_y, _c, _style) in enumerate(zip(y, c, style)):
		scatter_kws = {**default_scatter_kws, **{'label': Unit(_y)}, **kwargs.get('scatter_kws', {})}
		bar_kws = {**default_bar_kws, **{'label': Unit(_y)}, **kwargs.get('bar_kws', {})}
		plot_kws = {**default_plot_kws, **{'label': Unit(_y)}, **kwargs.get('plot_kws', {})}

		if _style in ['scatter', 'bar']:
			cbar_kws = {**default_cbar_kws, **{'label': Unit(_c), 'ticks': None}, **kwargs.get('cbar_kws', {})}
			inset_kws = {**default_insert_kws, **{'bbox_transform': ax.transAxes}, **kwargs.get('inset_kws', {})}

		if _style == 'scatter':
			_scatter(ax, df, _y, _c, scatter_kws, cbar_kws, inset_kws)

		elif _style == 'bar':
			_bar(ax, df, _y, _c, bar_kws, cbar_kws, inset_kws)

		else:
			_plot(ax, df, _y, _c, plot_kws)

	if y2:
		for i, (_y, _c, _style) in enumerate(zip(y2, c[len(y):], style[len(y):])):
			scatter_kws = {**default_scatter_kws, **{'label': Unit(_y)}, **kwargs.get('scatter_kws2', {})}
			bar_kws = {**default_bar_kws, **{'label': Unit(_y)}, **kwargs.get('bar_kws2', {})}
			plot_kws = {**default_plot_kws, **{'label': Unit(_y)}, **kwargs.get('plot_kws2', {})}

			if _style in ['scatter', 'bar']:
				cbar_kws = {**default_cbar_kws, **{'label': Unit(_c), 'ticks': None}, **kwargs.get('cbar_kws2', {})}
				inset_kws = {**default_insert_kws, **{'bbox_transform': ax.transAxes}, **kwargs.get('inset_kws2', {})}

			if _style == 'scatter':
				_scatter(ax2, df, _y, _c, scatter_kws, cbar_kws, inset_kws)

			elif _style == 'bar':
				_bar(ax2, df, _y, _c, bar_kws, cbar_kws, inset_kws)

			else:  # line plot
				_plot(ax2, df, _y, _c, plot_kws)

		# Combine legends from ax and ax2
		ax.legend(*combine_legends([ax, ax2]), loc=legend_loc, ncol=legend_ncol)

	else:
		ax.legend(loc=legend_loc, ncol=legend_ncol)

	if set_xaxis_visible is not None:
		ax.axes.xaxis.set_visible(set_xaxis_visible)

	ax.set(xlabel=kwargs.get('xlabel', ''),
		   ylabel=kwargs.get('ylabel', Unit(y) if isinstance(y, str) else Unit(y[0])),
		   xticks=kwargs.get('xticks', date_range(start=st_tm, end=fn_tm, freq=freq).strftime("%F")),
		   yticks=kwargs.get('yticks', ax.get_yticks()),
		   xticklabels=kwargs.get('xticklabels', date_range(start=st_tm, end=fn_tm, freq=freq).strftime("%F")),
		   yticklabels=kwargs.get('yticklabels', ax.get_yticklabels()),
		   xlim=kwargs.get('xlim', (st_tm, fn_tm)),
		   ylim=kwargs.get('ylim', (None, None)),
		   title=kwargs.get('title', '')
		   )

	if y2:
		ax2.set(ylabel=kwargs.get('ylabel2', Unit(y2) if isinstance(y2, str) else Unit(y2[0])),
				yticks=kwargs.get('yticks2', ax2.get_yticks()),
				yticklabels=kwargs.get('yticklabels2', ax2.get_yticklabels()),
				ylim=kwargs.get('ylim2', (None, None)))

	plt.show()

	return fig, ax


@set_figure(fs=8, autolayout=False)
def timeseries_template(df: DataFrame) -> tuple[Figure, Axes]:
	fig, ax = plt.subplots(5, 1, figsize=(len(df.index) * 0.01, 4))
	(ax1, ax2, ax3, ax4, ax5) = ax

	timeseries(df,
			   y=['Extinction', 'Scattering', 'Absorption'],
			   rolling=30,
			   ax=ax1,
			   ylabel='Coefficient',
			   ylim=[0., None],
			   set_xaxis_visible=False,
			   legend_ncol=3,
			   )

	# Temp, RH
	timeseries(df,
			   y='AT',
			   y2='RH',
			   rolling=30,
			   ax=ax2,
			   ax_plot_kws=dict(color='r'),
			   ax2_plot_kws=dict(color='b'),
			   ylim=[10, 30],
			   ylim2=[20, 100],
			   set_xaxis_visible=False,
			   legend_ncol=2,
			   )

	timeseries(df, y='WS', c='WD', style='scatter', ax=ax3, scatter_kws=dict(cmap='hsv'),
			   cbar_kws=dict(ticks=[0, 90, 180, 270, 360]),
			   ylim=[0, None], set_xaxis_visible=False)

	timeseries(df, y='VC', c='PBLH', style='bar', ax=ax4, bar_kws=dict(cmap='Blues'), set_xaxis_visible=False,
			   ylim=[0, 5000])

	timeseries(df, y='PM25', c='PM1/PM25', style='scatter', ax=ax5, ylim=[0, None])

	plt.show()

	return fig, ax
