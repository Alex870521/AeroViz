import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.pyplot import Figure, Axes
from pandas import DataFrame, date_range
from sklearn.preprocessing import StandardScaler

from AeroViz.plot.utils import *


def process_data(df):
	# detected_limit = 0.0001
	df = df.where(df >= 0.0001, np.nan)
	# Normalize the data
	df = DataFrame(StandardScaler().fit_transform(df), index=df.index, columns=df.columns)
	# Remove outliers
	df = df[(np.abs(df) < 6)]
	# Interpolate the missing values
	df = df.interpolate(method='linear')
	# Smooth the data
	df = df.rolling(window=3, min_periods=1).mean()

	return df


@set_figure(figsize=(12, 3), fs=6)
def metal_heatmaps(df, major_freq='24h', minor_freq='12h', ax: Axes | None = None, title=None, **kwargs
				   ) -> tuple[Figure, Axes]:
	items = ['Al', 'Zr', 'Si', 'Ca', 'Ti', 'Mn', 'Fe', 'V', 'Cl', 'K',
			 'Sr', 'Ba', 'Bi', 'Pd', 'Sn', 'Cr', 'W', 'Cu', 'Zn',
			 'As', 'Co', 'Se', 'Br', 'Cd', 'Sb', 'In', 'Pb', 'Ni']

	df = df[items]

	fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

	sns.heatmap(df.T, vmax=3, cmap="jet", xticklabels=False, yticklabels=True,
				cbar_kws={'label': 'Z score'})
	ax.grid(color='gray', linestyle='-', linewidth=0.3)
	# Set x-tick positions and labels
	major_tick = date_range(start=df.index[0], end=df.index[-1], freq=major_freq)
	minor_tick = date_range(start=df.index[0], end=df.index[-1], freq=minor_freq)

	# Set the major and minor ticks
	ax.set_xticks(ticks=[df.index.get_loc(t) for t in major_tick])
	ax.set_xticks(ticks=[df.index.get_loc(t) for t in minor_tick], minor=True)
	ax.set_xticklabels(major_tick.strftime('%F'))
	ax.tick_params(axis='y', rotation=0)

	ax.set_title(f"{title}", fontsize=10)
	ax.set(xlabel='',
		   ylabel='',
		   )

	plt.show()

	return fig, ax
