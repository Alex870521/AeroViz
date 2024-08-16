import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import Normalize
from matplotlib.pyplot import Figure, Axes
from matplotlib.ticker import ScalarFormatter

from AeroViz.plot.templates.regression import _linear_regression
from AeroViz.plot.utils import *

__all__ = ['scatter']


@set_figure
def scatter(df: pd.DataFrame,
			x: str,
			y: str,
			c: str | None = None,
			s: str | None = None,
			cmap='jet',
			regression=False,
			diagonal=False,
			box=False,
			ax: Axes | None = None,
			**kwargs) -> tuple[Figure, Axes]:
	fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

	if c is not None and s is not None:
		df_ = df.dropna(subset=[x, y, c, s]).copy()
		x_data, y_data, c_data, s_data = df_[x].to_numpy(), df_[y].to_numpy(), df_[c].to_numpy(), df_[s].to_numpy()

		scatter = ax.scatter(x_data, y_data, c=c_data,
							 norm=Normalize(vmin=np.percentile(c_data, 10), vmax=np.percentile(c_data, 90)),
							 cmap=cmap, s=50 * (s_data / s_data.max()) ** 1.5, alpha=0.7, edgecolors=None)
		colorbar = True

		dot = np.linspace(s_data.min(), s_data.max(), 6).round(-1)

		for dott in dot[1:-1]:
			plt.scatter([], [], c='k', alpha=0.8, s=50 * (dott / s_data.max()) ** 1.5, label='{:.0f}'.format(dott))

		plt.legend(title=Unit(s))

	elif c is not None:
		df_ = df.dropna(subset=[x, y, c]).copy()
		x_data, y_data, c_data = df_[x].to_numpy(), df_[y].to_numpy(), df_[c].to_numpy()

		scatter = ax.scatter(x_data, y_data, c=c_data, vmin=c_data.min(), vmax=np.percentile(c_data, 90), cmap=cmap,
							 alpha=0.7,
							 edgecolors=None)
		colorbar = True

	elif s is not None:
		df_ = df.dropna(subset=[x, y, s]).copy()
		x_data, y_data, s_data = df_[x].to_numpy(), df_[y].to_numpy(), df_[s].to_numpy()

		scatter = ax.scatter(x_data, y_data, s=50 * (s_data / s_data.max()) ** 1.5, color='#7a97c9', alpha=0.7,
							 edgecolors='white')
		colorbar = False

		# dealing
		dot = np.linspace(s_data.min(), s_data.max(), 6).round(-1)

		for dott in dot[1:-1]:
			plt.scatter([], [], c='k', alpha=0.8, s=50 * (dott / s_data.max()) ** 1.5, label='{:.0f}'.format(dott))

		plt.legend(title=Unit(s))

	else:
		df_ = df.dropna(subset=[x, y]).copy()
		x_data, y_data = df_[x].to_numpy(), df_[y].to_numpy()

		scatter = ax.scatter(x_data, y_data, s=30, color='#7a97c9', alpha=0.7, edgecolors='white')
		colorbar = False

	xlim = kwargs.get('xlim', (x_data.min(), x_data.max()))
	ylim = kwargs.get('ylim', (y_data.min(), y_data.max()))
	xlabel = kwargs.get('xlabel', Unit(x))
	ylabel = kwargs.get('ylabel', Unit(y))
	title = kwargs.get('title', '')
	ax.set(xlim=xlim, ylim=ylim, xlabel=xlabel, ylabel=ylabel, title=title)

	# color_bar
	if colorbar:
		color_bar = plt.colorbar(scatter, extend='both')
		color_bar.set_label(label=Unit(c), size=14)

	if regression:
		text, y_predict, slope = _linear_regression(x_data, y_data)
		plt.plot(x_data, y_predict, linewidth=3, color=sns.xkcd_rgb["denim blue"], alpha=1, zorder=3)

		plt.text(0.05, 0.95, f'{text}', fontdict={'weight': 'bold'}, color=sns.xkcd_rgb["denim blue"],
				 ha='left', va='top', transform=ax.transAxes)

	if diagonal:
		ax.axline((0, 0), slope=1., color='k', lw=2, ls='--', alpha=0.5, label='1:1')
		plt.text(0.91, 0.97, r'$\bf 1:1\ Line$', color='k', ha='right', va='top', transform=ax.transAxes)

	if box:
		bins = np.linspace(x_data.min(), x_data.max(), 11, endpoint=True)
		wid = (bins + (bins[1] - bins[0]) / 2)[0:-1]

		df[x + '_bin'] = pd.cut(x=x_data, bins=bins, labels=wid)

		group = x + '_bin'
		column = y
		grouped = df.groupby(group, observed=False)

		names, vals = [], []

		for i, (name, subdf) in enumerate(grouped):
			names.append('{:.0f}'.format(name))
			vals.append(subdf[column].dropna().values)

		plt.boxplot(vals, labels=names, positions=wid, widths=(bins[1] - bins[0]) / 3,
					showfliers=False, showmeans=True, meanline=True, patch_artist=True,
					boxprops=dict(facecolor='#f2c872', alpha=.7),
					meanprops=dict(color='#000000', ls='none'),
					medianprops=dict(ls='-', color='#000000'))

		plt.xlim(x_data.min(), x_data.max())
		ax.set_xticks(bins, labels=bins.astype(int))

	ax.xaxis.set_major_formatter(ScalarFormatter())
	ax.yaxis.set_major_formatter(ScalarFormatter())

	plt.show()

	return fig, ax
