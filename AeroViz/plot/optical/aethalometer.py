import matplotlib.pyplot as plt
import numpy as np
from pandas import date_range

from AeroViz.plot.utils import *

__all__ = ['plot_MA350',
		   'plot_MA3502',
		   'plot_day_night']


@set_figure(figsize=(15, 5))
def plot_MA350(df, **kwargs):
	fig, ax = plt.subplots()

	# ax.scatter(df.index, df['UV BCc'], marker='o', c='purple', alpha=0.5, label='UV BCc')
	# ax.scatter(df.index, df['Blue BCc'], c='b', alpha=0.5, label='Blue BCc')
	# ax.scatter(df.index, df['Green BCc'], c='g', alpha=0.5, label='Green BCc')
	# ax.scatter(df.index, df['Red BCc'], c='r', alpha=0.5, label='Red BCc')
	mean, std = round(df.mean(), 2), round(df.std(), 2)

	label1 = rf'$MA350-0171\ :\;{mean["MA350_0171 IR BCc"]}\;\pm\;{std["MA350_0171 IR BCc"]}\;(ng/m^3)$'
	label2 = rf'$MA350-0176\ :\;{mean["MA350_0176 IR BCc"]}\;\pm\;{std["MA350_0176 IR BCc"]}\;(ng/m^3)$'
	label3 = rf'$BC-1054\ :\;{mean["BC1054 IR BCc"]}\;\pm\;{std["BC1054 IR BCc"]}\;(ng/m^3)$'
	ax.scatter(df.index, df['MA350_0171 IR BCc'], s=10, ls='-', marker='o', c='#a3b18a', alpha=0.5, label=label1)
	ax.scatter(df.index, df['MA350_0176 IR BCc'], s=10, ls='-', marker='o', c='#3a5a40', alpha=0.5, label=label2)
	ax.scatter(df.index, df['BC1054 IR BCc'], s=10, ls='-', marker='o', c='g', alpha=0.5, label=label3)
	ax.legend(prop={'weight': 'bold'}, loc='upper left')

	st_tm, fn_tm = df.index[0], df.index[-1]
	tick_time = date_range(st_tm, fn_tm, freq=kwargs.get('freq', '10d'))

	ax.set(xlabel=kwargs.get('xlabel', ''),
		   ylabel=kwargs.get('ylabel', r'$BC\ (ng/m^3)$'),
		   xticks=kwargs.get('xticks', tick_time),
		   xticklabels=kwargs.get('xticklabels', [_tm.strftime("%F") for _tm in tick_time]),
		   xlim=kwargs.get('xlim', (st_tm, fn_tm)),
		   ylim=kwargs.get('ylim', (0, None)),
		   )


@set_figure
def plot_MA3502(df):
	fig, ax = plt.subplots()

	bins = np.array([375, 470, 528, 625, 880])
	vals = df.dropna().iloc[:, -5:].values

	ax.boxplot(vals, positions=bins, widths=20,
			   showfliers=False, showmeans=True, meanline=True, patch_artist=True,
			   boxprops=dict(facecolor='#f2c872', alpha=.7),
			   meanprops=dict(color='#000000', ls='none'),
			   medianprops=dict(ls='-', color='#000000'))

	ax.set(xlim=(355, 900),
		   ylim=(0, None),
		   xlabel=r'$\lambda\ (nm)$',
		   ylabel=r'$Absorption\ (1/Mm)$', )


@set_figure(figsize=(6, 5))
def plot_day_night(df):
	# Group by hour of day and calculate mean
	df_grouped = df.groupby(df.index.hour).mean()

	# Create figure and plot
	fig, ax = plt.subplots()
	ax.plot(df_grouped.index, df_grouped['MA350_0171 IR BCc'], marker='o', c='k', alpha=0.5, label='MA350-0171')
	ax.plot(df_grouped.index, df_grouped['MA350_0176 IR BCc'], marker='o', c='r', alpha=0.5, label='MA350-0176')
	ax.plot(df_grouped.index, df_grouped['BC1054 IR BCc'], marker='o', c='b', alpha=0.5, label='BC-1054')

	ax.set(xlim=(0, 23),
		   xlabel='Hour of Day',
		   ylabel=r'$BC\ (ng/m^3)$',
		   title=f'Diurnal pattern', )

	ax.legend()
