import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.pyplot import Figure, Axes

from AeroViz.plot.utils import *

__all__ = [
    'linear_regression',
    'multiple_linear_regression',
]


@set_figure
def linear_regression(df: pd.DataFrame,
                      x: str | list[str],
                      y: str | list[str],
                      labels: str | list[str] = None,
                      ax: Axes | None = None,
                      diagonal=False,
                      positive: bool = True,
                      fit_intercept: bool = True,
                      **kwargs
                      ) -> tuple[Figure, Axes]:
    """
    Create a scatter plot with regression lines for the given data.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame containing the data.
    x : str or list of str
        Column name(s) for the x-axis variable(s). If a list, only the first element is used.
    y : str or list of str
        Column name(s) for the y-axis variable(s).
    labels : str or list of str, optional
        Labels for the y-axis variable(s). If None, column names are used as labels. Default is None.
    ax : Axes, optional
        Matplotlib Axes object to use for the plot. If None, a new subplot is created. Default is None.
    diagonal : bool, optional
        If True, a diagonal line (1:1 line) is added to the plot. Default is False.
    positive : bool, optional
        Whether to constrain the regression coefficients to be positive. Default is True.
    fit_intercept: bool, optional
        Whether to calculate the intercept for this model. Default is True.
    **kwargs
        Additional keyword arguments for plot customization.

    Returns
    -------
    fig : Figure
        The matplotlib Figure object.
    ax : Axes
        The matplotlib Axes object with the scatter plot.

    Notes
    -----
    - The function creates a scatter plot with optional regression lines.
    - The regression line is fitted for each y variable.
    - Customization options are provided via **kwargs.

    Example
    -------
    >>> linear_regression(df, x='X', y=['Y1', 'Y2'], labels=['Label1', 'Label2'],
    ...                  diagonal=True, xlim=(0, 10), ylim=(0, 20),
    ...                  xlabel="X-axis", ylabel="Y-axis", title="Scatter Plot with Regressions")
    """
    fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

    if not isinstance(x, str):
        x = x[0]

    if not isinstance(y, list):
        y = [y]

    if labels is None:
        labels = y

    df = df.dropna(subset=[x, *y])
    x_array = df[[x]].to_numpy()

    color_cycle = Color.linecolor

    handles, text_list = [], []

    for i, y_var in enumerate(y):
        y_array = df[[y_var]].to_numpy()

        color = color_cycle[i % len(color_cycle)]

        scatter = ax.scatter(x_array, y_array, s=25, color=color['face'], edgecolors=color['edge'], alpha=0.8,
                             label=labels[i])
        handles.append(scatter)

        text, y_predict, slope = linear_regression_base(x_array, y_array,
                                                        columns=labels[i],
                                                        positive=positive,
                                                        fit_intercept=fit_intercept)

        text_list.append(f'{labels[i]}:\n{text}')
        plt.plot(x_array, y_predict, linewidth=3, color=color['line'], alpha=1, zorder=3)

    ax.set(xlim=kwargs.get('xlim'), ylim=kwargs.get('ylim'), xlabel=Unit(x), ylabel=Unit(y[0]),
           title=kwargs.get('title'))

    # Add regression info to the legend
    leg = plt.legend(handles=handles, labels=text_list, loc='upper left', prop={'weight': 'bold'})

    for text, color in zip(leg.get_texts(), [color['line'] for color in color_cycle]):
        text.set_color(color)

    if diagonal:
        ax.axline((0, 0), slope=1., color='k', lw=2, ls='--', alpha=0.5, label='1:1')
        plt.text(0.97, 0.97, r'$\bf 1:1\ Line$', color='k', ha='right', va='top', transform=ax.transAxes)

    plt.show()

    return fig, ax


@set_figure
def multiple_linear_regression(df: pd.DataFrame,
                               x: str | list[str],
                               y: str | list[str],
                               labels: str | list[str] = None,
                               ax: Axes | None = None,
                               diagonal=False,
                               positive: bool = True,
                               fit_intercept: bool = True,
                               **kwargs
                               ) -> tuple[Figure, Axes]:
    """
    Perform multiple linear regression analysis and plot the results.

    Parameters
    ----------
    df : pd.DataFrame
       Input DataFrame containing the data.
    x : str or list of str
       Column name(s) for the independent variable(s). Can be a single string or a list of strings.
    y : str or list of str
       Column name(s) for the dependent variable(s). Can be a single string or a list of strings.
    labels : str or list of str, optional
       Labels for the dependent variable(s). If None, column names are used as labels. Default is None.
    ax : Axes, optional
       Matplotlib Axes object to use for the plot. If None, a new subplot is created. Default is None.
    diagonal : bool, optional
       Whether to include a diagonal line (1:1 line) in the plot. Default is False.
    positive : bool, optional
       Whether to constrain the regression coefficients to be positive. Default is True.
    fit_intercept: bool, optional
        Whether to calculate the intercept for this model. Default is True.
    **kwargs
       Additional keyword arguments for plot customization.

    Returns
    -------
    tuple[Figure, Axes]
       The Figure and Axes containing the regression plot.

    Notes
    -----
    This function performs multiple linear regression analysis using the input DataFrame.
    It supports multiple independent variables and can plot the regression results.

    Example
    -------
    >>> multiple_linear_regression(df, x=['X1', 'X2'], y='Y', labels=['Y1', 'Y2'],
    ...                             diagonal=True, fit_intercept=True,
    ...                             xlabel="X-axis", ylabel="Y-axis", title="Multiple Linear Regression Plot")
    """
    fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

    if not isinstance(x, list):
        x = [x]

    if not isinstance(y, str):
        y = y[0]

    if labels is None:
        labels = x

    df = df[[*x, y]].dropna()
    x_array = df[[*x]].to_numpy()
    y_array = df[[y]].to_numpy()

    text, y_predict, coefficients = linear_regression_base(x_array, y_array,
                                                           columns=labels,
                                                           positive=positive,
                                                           fit_intercept=fit_intercept)

    df = pd.DataFrame(np.concatenate([y_array, y_predict], axis=1), columns=['y_actual', 'y_predict'])

    linear_regression(df, x='y_actual', y='y_predict', ax=ax, regression=True, diagonal=diagonal)

    return fig, ax
