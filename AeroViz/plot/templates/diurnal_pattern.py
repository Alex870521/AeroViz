import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.pyplot import Figure, Axes
from matplotlib.ticker import AutoMinorLocator

from AeroViz.plot.utils import *

__all__ = ['diurnal_pattern']


@set_figure(figsize=(4, 4), fs=8)
def diurnal_pattern(data_set: pd.DataFrame,
					data_std: pd.DataFrame,
					y: str | list[str],
					std_area=0.5,
					ax: Axes | None = None,
					**kwargs) -> tuple[Figure, Axes]:
	fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

	Hour = range(0, 24)

	mean = data_set[y]
	std = data_std[y] * std_area

	# Plot Diurnal pattern
	ax.plot(Hour, mean, 'blue')
	ax.fill_between(Hour, y1=mean + std, y2=mean - std, alpha=0.5, color='blue', edgecolor=None)

	ax.set(xlabel=kwargs.get('xlabel', 'Hours'),
		   ylabel=kwargs.get('ylabel', Unit(y)),
		   xlim=kwargs.get('xlim', (0, 23)),
		   ylim=kwargs.get('ylim', (None, None)),
		   xticks=kwargs.get('xticks', [0, 4, 8, 12, 16, 20]))

	ax.tick_params(axis='both', which='major')
	ax.tick_params(axis='x', which='minor')
	ax.xaxis.set_minor_locator(AutoMinorLocator())
	ax.ticklabel_format(axis='y', style='sci', scilimits=(-2, 3), useMathText=True)

	plt.show()

	return fig, ax
