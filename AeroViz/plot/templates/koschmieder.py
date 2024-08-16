from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.pyplot import Figure, Axes
from scipy.optimize import curve_fit

from AeroViz.plot.utils import *

__all__ = ['koschmieder']


@set_figure(fs=12)
def koschmieder(df: pd.DataFrame,
				y: Literal['Vis_Naked', 'Vis_LPV'],
				function: Literal['log', 'reciprocal'] = 'log',
				ax: Axes | None = None,
				**kwargs) -> tuple[Figure, Axes]:
	# x = Visibility, y = Extinction, log-log fit!!
	def _log_fit(x, y, func=lambda x, a: -x + a):
		x_log = np.log(x)
		y_log = np.log(y)

		popt, pcov = curve_fit(func, x_log, y_log)

		residuals = y_log - func(x_log, *popt)
		ss_res = np.sum(residuals ** 2)
		ss_total = np.sum((y_log - np.mean(y_log)) ** 2)
		r_squared = 1 - (ss_res / ss_total)
		print(f'Const_Log = {popt[0].round(3)}')
		print(f'Const = {np.exp(popt)[0].round(3)}')
		print(f'R^2 = {r_squared.round(3)}')
		return np.exp(popt)[0], pcov

	def _reciprocal_fit(x, y, func=lambda x, a, b: a / (x ** b)):
		popt, pcov = curve_fit(func, x, y)

		residuals = y - func(x, *popt)
		ss_res = np.sum(residuals ** 2)
		ss_total = np.sum((y - np.mean(y)) ** 2)
		r_squared = 1 - (ss_res / ss_total)
		print(f'Const = {popt.round(3)}')
		print(f'  R^2 = {r_squared.round(3)}')
		return popt, pcov

	fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

	_df1 = df[['Extinction', 'ExtinctionByGas', y]].dropna().copy()
	_df2 = df[['total_ext_dry', 'ExtinctionByGas', y]].dropna().copy()

	x_data1 = _df1[y]
	y_data1 = _df1['Extinction'] + _df1['ExtinctionByGas']

	x_data2 = _df2[y]
	y_data2 = _df2['total_ext_dry'] + _df2['ExtinctionByGas']

	para_coeff = []
	boxcolors = ['#3f83bf', '#a5bf6b']

	for i, (df_, x_data, y_data) in enumerate(zip([_df1, _df2], [x_data1, x_data2], [y_data1, y_data2])):
		df_['Total_Ext'] = y_data

		if y == 'Vis_Naked':
			df_grp = df_.groupby(f'{y}')

			vals, median_vals, vis = [], [], []
			for j, (name, subdf) in enumerate(df_grp):
				if len(subdf['Total_Ext'].dropna()) > 20:
					vis.append('{:.0f}'.format(name))
					vals.append(subdf['Total_Ext'].dropna().values)
					median_vals.append(subdf['Total_Ext'].dropna().median())

			plt.boxplot(vals, labels=vis, positions=np.array(vis, dtype='int'), widths=0.4,
						showfliers=False, showmeans=True, meanline=False, patch_artist=True,
						boxprops=dict(facecolor=boxcolors[i], alpha=.7),
						meanprops=dict(marker='o', markerfacecolor='white', markeredgecolor='k', markersize=4),
						medianprops=dict(color='#000000', ls='-'))

			plt.scatter(x_data, y_data, marker='.', s=10, facecolor='white', edgecolor=boxcolors[i], alpha=0.1)

		if y == 'Vis_LPV':
			bins = np.linspace(0, 70, 36)
			wid = (bins + (bins[1] - bins[0]) / 2)[0:-1]

			df_[f'{x_data.name}' + '_bins'] = pd.cut(x=x_data, bins=bins, labels=wid)

			grouped = df_.groupby(f'{x_data.name}' + '_bins', observed=False)

			vals, median_vals, vis = [], [], []
			for j, (name, subdf) in enumerate(grouped):
				if len(subdf['Total_Ext'].dropna()) > 20:
					vis.append('{:.1f}'.format(name))
					vals.append(subdf['Total_Ext'].dropna().values)
					median_vals.append(subdf['Total_Ext'].dropna().mean())

			plt.boxplot(vals, labels=vis, positions=np.array(vis, dtype='float'), widths=(bins[1] - bins[0]) / 2.5,
						showfliers=False, showmeans=True, meanline=False, patch_artist=True,
						boxprops=dict(facecolor=boxcolors[i], alpha=.7),
						meanprops=dict(marker='o', markerfacecolor='white', markeredgecolor='k', markersize=4),
						medianprops=dict(color='#000000', ls='-'))

			plt.scatter(x_data, y_data, marker='.', s=10, facecolor='white', edgecolor=boxcolors[i], alpha=0.1)

		# fit curve
		_x = np.array(vis, dtype='float')
		_y = np.array(median_vals, dtype='float')

		if function == 'log':
			func = lambda x, a: a / x
			coeff, pcov = _log_fit(_x, _y)

		else:
			func = lambda x, a, b: a / (x ** b)
			coeff, pcov = _reciprocal_fit(_x, _y)

		para_coeff.append(coeff)

	# Plot lines (ref & Measurement)
	x_fit = np.linspace(0.1, 70, 1000)

	if function == 'log':
		line1, = ax.plot(x_fit, func(x_fit, para_coeff[0]), c='b', lw=3)
		line2, = ax.plot(x_fit, func(x_fit, para_coeff[1]), c='g', lw=3)

		labels = ['Vis (km) = ' + f'{round(para_coeff[0])}' + ' / Ext (Dry Extinction)',
				  'Vis (km) = ' + f'{round(para_coeff[1])}' + ' / Ext (Amb Extinction)']

	else:
		x_fit = np.linspace(0.1, 70, 1000)
		line1, = ax.plot(x_fit, func(x_fit, *para_coeff[0]), c='b', lw=3)
		line2, = ax.plot(x_fit, func(x_fit, *para_coeff[1]), c='g', lw=3)

		labels = [f'Ext = ' + '{:.0f} / Vis ^ {:.3f}'.format(*para_coeff[0]) + ' (Dry Extinction)',
				  f'Ext = ' + '{:.0f} / Vis ^ {:.3f}'.format(*para_coeff[1]) + ' (Amb Extinction)']

	plt.legend(handles=[line1, line2], labels=labels, loc='upper right', prop=dict(size=10, weight='bold'),
			   bbox_to_anchor=(0.99, 0.99))

	plt.xticks(ticks=np.array(range(0, 51, 5)), labels=np.array(range(0, 51, 5)))
	plt.xlim(0, 50)
	plt.ylim(0, 700)
	plt.title(r'$\bf Koschmieder\ relationship$')
	plt.xlabel(f'{y} (km)')
	plt.ylabel(r'$\bf Extinction\ coefficient\ (1/Mm)$')

	plt.show()

	return fig, ax


if __name__ == '__main__':
	from AeroViz.tools import DataBase

	koschmieder(DataBase(), 'Vis_LPV', 'log')
	# koschmieder(DataBase, 'Vis_Naked', 'reciprocal')
