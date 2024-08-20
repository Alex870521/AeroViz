from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.pyplot import Figure, Axes
from pandas import DataFrame

from AeroViz.plot.utils import *

__all__ = [
    'pie',
    'donuts'
]


@set_figure(fw='bold')
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

    text = [''] * pies if style == 'pie' else [Unit(unit) + '\n\n' +
                                               '{:.2f} ± {:.2f}'.format(x, s)
                                               for x, s in zip(data.sum(axis=1), data.std(axis=1))]
    pct_distance = 0.6 if style == 'pie' else 0.88

    fig, ax = plt.subplots(1, pies, figsize=((pies * 2) + 1, 2)) if ax is None else (ax.get_figure(), ax)

    if pies == 1:
        ax = [ax]

    for i in range(pies):
        ax[i].pie(data[i], labels=None, colors=colors, textprops=None,
                  autopct=lambda pct: auto_label_pct(pct, symbol=symbol, include_pct=True),
                  pctdistance=pct_distance, radius=radius, wedgeprops=dict(width=width, edgecolor='w'))

        ax[i].pie(data[i], labels=None, colors=colors, textprops=None,
                  autopct=lambda pct: auto_label_pct(pct, symbol=symbol, ignore='outer', include_pct=True),
                  pctdistance=1.3, radius=radius, wedgeprops=dict(width=width, edgecolor='w'))
        ax[i].axis('equal')
        ax[i].text(0, 0, text[i], ha='center', va='center')

        if kwargs.get('title') is None:
            ax[i].set_title(category_names[i])

        else:
            if len(kwargs.get('title')) == pies:
                title = kwargs.get('title')
            else:
                raise ValueError('The length of the title list must match the number of pies.')

            ax[i].set_title(title[i])

    ax[-1].legend(labels, loc='center left', prop={'size': 8, 'weight': 'normal'}, bbox_to_anchor=(1, 0, 1.15, 1))

    # fig.savefig(f"pie_{style}_{title}")

    plt.show()

    return fig, ax


@set_figure(fw='bold')
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
           autopct=lambda pct: auto_label_pct(pct, symbol=symbol, include_pct=True),
           pctdistance=0.9, radius=14, wedgeprops=dict(width=3, edgecolor='w'))

    ax.pie(data[1], labels=None, colors=colors2, textprops=None,
           autopct=lambda pct: auto_label_pct(pct, symbol=symbol, include_pct=True),
           pctdistance=0.85, radius=11, wedgeprops=dict(width=3, edgecolor='w'))

    ax.pie(data[0], labels=None, colors=colors3, textprops=None,
           autopct=lambda pct: auto_label_pct(pct, symbol=symbol, include_pct=True),
           pctdistance=0.80, radius=8, wedgeprops=dict(width=3, edgecolor='w'))

    text = (Unit(f'{unit}') + '\n\n' +
            'Event : ' + "{:.2f}".format(np.sum(data[2])) + '\n' +
            'Transition : ' + "{:.2f}".format(np.sum(data[1])) + '\n' +
            'Clean : ' + "{:.2f}".format(np.sum(data[0])))

    ax.text(0, 0, text, ha='center', va='center')
    ax.axis('equal')

    ax.set_title(kwargs.get('title', ''))

    ax.legend(labels, loc='center', prop={'size': 8}, title_fontproperties={'weight': 'bold'},
              title=f'Outer : {category_names[2]}' + '\n' + f'Middle : {category_names[1]}' + '\n' + f'Inner : {category_names[0]}',
              bbox_to_anchor=(0.8, 0, 0.5, 1))

    # fig.savefig(f"donuts_{title}")

    plt.show()

    return fig, ax
