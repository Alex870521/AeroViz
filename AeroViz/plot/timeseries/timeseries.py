from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.cm import ScalarMappable
from matplotlib.pyplot import Figure, Axes
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from pandas import DataFrame, date_range

from AeroViz.plot.utils import *

__all__ = ['timeseries', 'timeseries_stacked']


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


def process_timeseries_data(df, rolling=None, interpolate_limit=None):
    # apply rolling window if specified
    df = df.rolling(window=rolling, min_periods=1).mean(numeric_only=True) if rolling is not None else df

    # apply interpolation if specified
    df = df.interpolate(method='time', limit=interpolate_limit) if interpolate_limit is not None else df
    return df


@set_figure(autolayout=False)
def timeseries(df: DataFrame,
               y: list[str] | str,
               y2: list[str] | str = None,
               yi: list[str] | str = None,
               color: list[str] | str | None = None,
               label: list[str] | str | None = None,
               rolling: int | str | None = 3,
               interpolate_limit: int | None = 6,
               major_freq: str = '1MS',
               minor_freq: str = '10d',
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
    yi : list[str] | str, optional
        The components for percentage calculation. Defaults to None.
    color : str, optional
        The column for color mapping or the color. Defaults to None.
    label : str, optional
        The label for the legend. Defaults to None.
    rolling : str | int | None, optional
        Rolling window size for smoothing. Defaults to None.
    interpolate_limit : int, optional
        Interpolation limit for missing values. Defaults to None.
    major_freq : str, optional
        Frequency for x-axis ticks. Defaults to '1MS'.
    minor_freq : str, optional
        Frequency for x-axis minor ticks. Defaults to '10d'.
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
    >>> timeseries(df, y='WS', color='WD', scatter_kws=dict(cmap='hsv'), cbar_kws=dict(ticks=[0, 90, 180, 270, 360]), ylim=[0, None])
    """
    # Set the time
    try:
        st_tm, fn_tm = df.index[0], df.index[-1]
    except IndexError:
        raise IndexError("The DataFrame is empty. Please provide a valid DataFrame.")

    # calculate the percentage of each component
    if yi is not None:
        df_pct = df[yi].div(df[yi].sum(axis=1), axis=0) * 100
        mean = [f"{_label} : {df[comp].mean():.2f}" for _label, comp in zip(label, yi)]
        pct = [f"{_label} : {df_pct[comp].mean():.2f}%" for _label, comp in zip(label, yi)]
        df_pct = process_timeseries_data(df_pct, rolling, interpolate_limit)

    # process data
    df = process_timeseries_data(df, rolling, interpolate_limit)

    # Initialize figure and axis if not provided
    fig, ax = plt.subplots(**{**{'figsize': (6, 2)}, **kwargs.get('fig_kws', {})}) if ax is None else (
        ax.get_figure(), ax)

    # Ensure y, y2, c, and style are lists
    y = [y] if isinstance(y, str) else y
    y2 = [y2] if isinstance(y2, str) else y2 if y2 is not None else []
    color = [color] if isinstance(color, str) else color if color is not None else [None] * (len(y) + len(y2))
    label = [label] if isinstance(label, str) else label if label is not None else [None] * (len(y) + len(y2))
    style = [style] if isinstance(style, str) else style if style is not None else ['plot'] * (len(y) + len(y2))

    for name, lst in [("c", color), ("style", style), ("label", label)]:
        if len(lst) != len(y) + len(y2):
            raise ValueError(f"The length of {name} must match the combined length of y and y2")

    # Create a secondary y-axis if y2 is not empty
    ax2 = ax.twinx() if y2 else None

    # # Set color cycle
    ax.set_prop_cycle(Color.color_cycle)
    if y2:
        ax2.set_prop_cycle(Color.color_cycle[len(y):])

    if y2 and ('scatter' or 'bar') in style:
        fig.subplots_adjust(right=0.8)

    for i, _c in enumerate(color):
        if _c is not None and _c in df.columns:
            style[i] = 'scatter'

    for i, (_y, _c, _label, _style) in enumerate(zip(y, color, label, style)):
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
        for i, (_y, _c, _style) in enumerate(zip(y2, color[len(y):], style[len(y):])):
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
           xlim=kwargs.get('xlim', (st_tm, fn_tm)),
           ylim=kwargs.get('ylim', (None, None)),
           title=kwargs.get('title', '')
           )

    xticks = kwargs.get('xticks', date_range(start=st_tm, end=fn_tm, freq=major_freq))
    minor_xticks = kwargs.get('minor_xticks', date_range(start=st_tm, end=fn_tm, freq=minor_freq))

    ax.set_xticks(ticks=xticks, labels=xticks.strftime("%F"))
    ax.set_xticks(minor_xticks, minor=True)

    if y2:
        ax2.set(ylim=kwargs.get('ylim2', (None, None)),
                ylabel=kwargs.get('ylabel2', Unit(y2) if isinstance(y2, str) else Unit(y2[0]))
                )

    plt.show()

    return fig, ax


@set_figure(autolayout=False)
def timeseries_stacked(df,
                       y: list[str] | str,
                       yi: list[str] | str,
                       label: list[str] | str,
                       rolling: int | str | None = 6,
                       interpolate_limit: int | None = 6,
                       major_freq: str = '1MS',
                       minor_freq: str = '10d',
                       ax: Axes | None = None,
                       legend_ncol: int = 1,
                       **kwargs
                       ) -> tuple[Figure, Axes]:
    try:
        st_tm, fn_tm = df.index[0], df.index[-1]
    except IndexError:
        raise IndexError("The DataFrame is empty. Please provide a valid DataFrame.")

    # calculate the percentage of each component
    df_pct = df[yi].div(df[yi].sum(axis=1), axis=0) * 100
    mean = [f"{_label} : {df[comp].mean():.2f}" for _label, comp in zip(label, yi)]
    pct = [f"{_label} : {df_pct[comp].mean():.2f}%" for _label, comp in zip(label, yi)]

    # process data
    df = process_timeseries_data(df, rolling, interpolate_limit)
    df_pct = process_timeseries_data(df_pct, rolling, interpolate_limit)

    fig, (ax1, ax2) = plt.subplots(2, 1, **{**{'figsize': (12, 3)}, **kwargs.get('fig_kws', {})})

    width = 0.0417
    color = Color.colors1

    for name, lst in [("color", color), ("label", label)]:
        if len(lst) != len(yi):
            raise ValueError(f"The length of {name} must match the combined length of y and y2")

    bottom = None  # 初始化堆疊位置
    for i, (_column, _color, _label) in enumerate(zip(yi, color, mean)):
        if i == 0:
            bottom = df[_column] * 0  # 第一個堆疊底部為零
        ax1.bar(df.index, df[_column], color=_color, width=width, bottom=bottom, label=_label)
        bottom += df[_column]  # 更新堆疊底部位置

    ax1.legend(loc='upper left', ncol=legend_ncol, prop={'weight': 'bold'}, bbox_to_anchor=(1, 0, 1.2, 1))

    ax1.axes.xaxis.set_visible(False)

    ax1.set(xlabel=kwargs.get('xlabel', ''),
            ylabel=kwargs.get('ylabel', Unit(y) if isinstance(y, str) else Unit(y[0])),
            xlim=kwargs.get('xlim', (st_tm, fn_tm)),
            ylim=kwargs.get('ylim', (None, None)),
            title=kwargs.get('title', ''),
            )

    xticks = kwargs.get('xticks', date_range(start=st_tm, end=fn_tm, freq=major_freq))
    yticks = kwargs.get('yticks', np.linspace(*ax1.get_ylim(), num=6))
    minor_xticks = kwargs.get('minor_xticks', date_range(start=st_tm, end=fn_tm, freq=minor_freq))

    ax1.set_xticks(ticks=xticks, labels=xticks.strftime("%F"))
    ax1.set_yticks(ticks=yticks, labels=[f'{tick:.0f}' for tick in yticks])
    ax1.set_xticks(minor_xticks, minor=True)

    # ax2
    bottom = None  # 初始化堆疊位置
    for i, (_column, _color, _label) in enumerate(zip(yi, color, pct)):
        if i == 0:
            bottom = df_pct[_column] * 0  # 第一個堆疊底部為零
        ax2.bar(df_pct.index, df_pct[_column], color=_color, width=width, bottom=bottom, label=_label)
        bottom += df_pct[_column]  # 更新堆疊底部位置

    ax2.legend(loc='upper left', ncol=legend_ncol, prop={'weight': 'bold'}, bbox_to_anchor=(1, 0, 1.2, 1))

    ax2.set(xlabel=kwargs.get('xlabel', ''),
            ylabel=kwargs.get('ylabel', 'Percentage (%)'),
            xlim=kwargs.get('xlim', (st_tm, fn_tm)),
            ylim=(0, 100),
            )

    xticks = kwargs.get('xticks', date_range(start=st_tm, end=fn_tm, freq=major_freq))
    yticks = kwargs.get('yticks', np.linspace(*ax2.get_ylim(), num=6))
    minor_xticks = kwargs.get('minor_xticks', date_range(start=st_tm, end=fn_tm, freq=minor_freq))

    ax2.set_xticks(ticks=xticks, labels=xticks.strftime("%F"))
    ax2.set_yticks(ticks=yticks, labels=[f'{tick:.0f}' for tick in yticks])
    ax2.set_xticks(minor_xticks, minor=True)

    return fig, ax1
