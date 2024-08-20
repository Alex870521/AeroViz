import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.pyplot import Figure, Axes
from pandas import DataFrame

from AeroViz.plot.utils import *

__all__ = ['violin']


@set_figure(fw='bold')
def violin(df: DataFrame | dict,
           unit: str,
           ax: Axes | None = None,
           **kwargs
           ) -> tuple[Figure, Axes]:
    """
    Generate a violin plot for multiple data sets.

    Parameters
    ----------
    df : pd.DataFrame or dict
        A mapping from category names to pandas DataFrames containing the data.
    unit : str
        The unit for the data being plotted.
    ax : matplotlib.axes.Axes, optional
        The Axes object to draw the plot onto. If not provided, a new figure will be created.
    **kwargs : dict
        Additional keyword arguments to be passed to the violinplot function.

    Returns
    -------
    fig : Figure
        The matplotlib Figure object.
    ax : Axes
        The matplotlib Axes object with the scatter plot.

    """
    fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

    data = df.to_numpy()

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
    xticks = kwargs.get('xticks') or [x.replace('-', '\n') for x in list(df.keys())]

    ax.set(xlim=xlim, ylim=ylim, xlabel=xlabel, ylabel=ylabel, title=kwargs.get('title'))
    ax.set_xticks(x_position, xticks, fontweight='bold', fontsize=12)

    plt.show()

    return fig, ax
