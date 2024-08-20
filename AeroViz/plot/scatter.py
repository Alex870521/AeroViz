import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import Normalize
from matplotlib.pyplot import Figure, Axes
from matplotlib.ticker import ScalarFormatter

from AeroViz.plot.utils import *

__all__ = ['scatter']


def check_empty(*arrays):
    for i, arr in enumerate(arrays):
        if arr.size == 0:
            raise ValueError(f"Array is empty!")


@set_figure
def scatter(df: pd.DataFrame,
            x: str,
            y: str,
            c: str | None = None,
            color: str | None = '#7a97c9',
            s: str | None = None,
            cmap='jet',
            regression=False,
            regression_line_color: str | None = sns.xkcd_rgb["denim blue"],
            diagonal=False,
            ax: Axes | None = None,
            **kwargs
            ) -> tuple[Figure, Axes]:
    """
    Creates a scatter plot with optional color and size encoding.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the data to plot.
    x : str
        The column name for the x-axis values.
    y : str
        The column name for the y-axis values.
    c : str, optional
        The column name for c encoding. Default is None.
    color : str, optional
        The column name for color encoding. Default is None.
    s : str, optional
        The column name for size encoding. Default is None.
    cmap : str, optional
        The colormap to use for the color encoding. Default is 'jet'.
    regression : bool, optional
        If True, fits and plots a linear regression line. Default is False.
    regression_line_color : str, optional
        The color of the regression line. Default is 'sns.xkcd_rgb["denim blue"]'.
    diagonal : bool, optional
        If True, plots a 1:1 diagonal line. Default is False.
    ax : Axes, optional
        The matplotlib Axes to plot on. If not provided, a new figure and axes are created.
    **kwargs : Any
        Additional keyword arguments passed to customize the plot, such as `fig_kws` for figure creation and `xlabel`,
        `ylabel`, `xlim`, `ylim`, `title` for axis labeling and limits.

    Returns
    -------
    fig : Figure
        The matplotlib Figure object.
    ax : Axes
        The matplotlib Axes object with the scatter plot.

    Notes
    -----
    - If both `c` and `s` are provided, the scatter plot will encode data points using both color and size.
    - If only `c` is provided, data points will be color-coded according to the values in the `c` column.
    - If only `s` is provided, data points will be sized according to the values in the `s` column.
    - If neither `c` nor `s` is provided, a basic scatter plot is created.
    - The `regression` option will add a linear regression line and display the equation on the plot.
    - The `diagonal` option will add a 1:1 reference line to the plot.

    Examples
    --------
    >>> import pandas as pd
    >>> from AeroViz.plot import scatter
    >>> df = pd.DataFrame({
    >>>     'x': [1, 2, 3, 4],
    >>>     'y': [1.1, 2.0, 2.9, 4.1],
    >>>     'color': [10, 20, 30, 40],
    >>>     'size': [100, 200, 300, 400]
    >>> })
    >>> fig, ax = scatter(df, x='x', y='y', c='color', s='size', regression=True, diagonal=True)
    """
    fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

    if c is not None and s is not None:
        df_ = df.dropna(subset=[x, y, c, s]).copy()
        x_data, y_data, c_data, s_data = df_[x].to_numpy(), df_[y].to_numpy(), df_[c].to_numpy(), df_[s].to_numpy()
        check_empty(x_data, y_data, c_data, s_data)

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
        check_empty(x_data, y_data, c_data)

        scatter = ax.scatter(x_data, y_data, c=c_data, vmin=c_data.min(), vmax=np.percentile(c_data, 90), cmap=cmap,
                             alpha=0.7,
                             edgecolors=None)
        colorbar = True

    elif s is not None:
        df_ = df.dropna(subset=[x, y, s]).copy()
        x_data, y_data, s_data = df_[x].to_numpy(), df_[y].to_numpy(), df_[s].to_numpy()
        check_empty(x_data, y_data, s_data)

        scatter = ax.scatter(x_data, y_data, s=50 * (s_data / s_data.max()) ** 1.5, color=color, alpha=0.5,
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
        check_empty(x_data, y_data)

        scatter = ax.scatter(x_data, y_data, s=30, color=color, alpha=0.5, edgecolors='white')
        colorbar = False

    ax.set(xlim=kwargs.get('xlim', (x_data.min(), x_data.max())),
           ylim=kwargs.get('ylim', (y_data.min(), y_data.max())),
           xlabel=kwargs.get('xlabel', Unit(x)),
           ylabel=kwargs.get('ylabel', Unit(y)),
           title=kwargs.get('title', ''))

    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.yaxis.set_major_formatter(ScalarFormatter())

    if colorbar:
        plt.colorbar(scatter, extend='both', label=Unit(c))

    if regression:
        text, y_predict, slope = linear_regression_base(x_data, y_data)
        ax.plot(x_data, y_predict, linewidth=3, color=regression_line_color, alpha=1, zorder=3)
        plt.text(0.05, 0.95, text, fontdict={'weight': 'bold'}, color=regression_line_color,
                 ha='left', va='top', transform=ax.transAxes)

    if diagonal:
        ax.axline((0, 0), slope=1., color='k', lw=2, ls='--', alpha=0.5, label='1:1')

        data_range = min(ax.get_xlim()[1] - ax.get_xlim()[0], ax.get_ylim()[1] - ax.get_ylim()[0])
        plt.text(0.9 * data_range, 0.9 * data_range, r'$\bf 1:1\ Line$', color='k', ha='left', va='bottom',
                 bbox=dict(facecolor='white', edgecolor='none', alpha=0.1, pad=3))

    plt.show()

    return fig, ax
