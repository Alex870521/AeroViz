from typing import Literal

import matplotlib.colors as colors
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.pyplot import Figure, Axes
from matplotlib.ticker import FuncFormatter
from numpy import log, exp, sqrt, pi
from pandas import DataFrame, Series, date_range
from scipy.optimize import curve_fit
from scipy.signal import find_peaks
from scipy.stats import norm, lognorm
from tabulate import tabulate

from AeroViz.plot.utils import *

__all__ = [
    'plot_dist',
    'heatmap',
    'heatmap_tms',
    'three_dimension',
    'curve_fitting'
]


@set_figure
def plot_dist(data: DataFrame | np.ndarray,
              data_std: DataFrame | None = None,
              std_scale: float | None = 1,
              unit: Literal["Number", "Surface", "Volume", "Extinction"] = 'Number',
              additional: Literal["Std", "Enhancement", "Error"] = None,
              fig: Figure | None = None,
              ax: Axes | None = None,
              **kwargs
              ) -> tuple[Figure, Axes]:
    """
    Plot particle size distribution curves and optionally show enhancements.

    Parameters
    ----------
    data : dict or list
        If dict, keys are labels and values are arrays of distribution values.
        If listed, it should contain three arrays for different curves.
    data_std : dict
        Dictionary containing standard deviation data for ambient extinction distribution.
    std_scale : float
        The width of standard deviation.
    unit : {'Number', 'Surface', 'Volume', 'Extinction'}
        Unit of measurement for the data.
    additional : {'std', 'enhancement', 'error'}
        Whether to show enhancement curves.
    fig : Figure, optional
        Matplotlib Figure object to use.
    ax : AxesSubplot, optional
        Matplotlib AxesSubplot  object to use. If not provided, a new subplot will be created.
    **kwargs : dict
        Additional keyword arguments.

    Returns
    -------
    ax : AxesSubplot
        Matplotlib AxesSubplot.

    Examples
    --------
    >>> plot_dist(DataFrame(...), additional="Enhancement")
    """
    fig, ax = plt.subplots(**{**{'figsize': (6, 2)}, **kwargs.get('fig_kws', {})}) if ax is None else (
        ax.get_figure(), ax)

    # plot_kws
    plot_kws = dict(ls='solid', lw=2, alpha=0.8, **kwargs.get('plot_kws', {}))

    # Receive input data
    dp = np.array(data.columns, dtype=float)
    states = np.array(data.index)

    for state in states:
        mean = data.loc[state].to_numpy()
        ax.plot(dp, mean, label=state, color=Color.color_choose[state][0], **plot_kws)

        if additional == 'Std':
            std = data_std.loc[state].to_numpy() * std_scale
            ax.fill_between(dp, y1=mean - std, y2=mean + std, alpha=0.4, color=Color.color_choose[state][1],
                            edgecolor=None, label='__nolegend__')

    # figure_set
    ax.set(xlim=(dp.min(), dp.max()), ylim=(0, None), xscale='log',
           xlabel=r'$D_{p} (nm)$', ylabel=Unit(f'{unit}_dist'), title=kwargs.get('title', unit))

    ax.ticklabel_format(axis='y', style='sci', scilimits=(0, 3), useMathText=True)
    ax.grid(axis='x', which='major', color='k', linestyle='dashdot', linewidth=0.4, alpha=0.4)

    Clean = data.loc['Clean'].to_numpy()
    Transition = data.loc['Transition'].to_numpy()
    Event = data.loc['Event'].to_numpy()

    if additional == "Enhancement":
        ax2 = ax.twinx()
        ax2.plot(dp, Transition / Clean, ls='dashed', color='k', label=f'{additional} ratio 1')
        ax2.plot(dp, Event / Transition, ls='dashed', color='gray', label=f'{additional} ratio 2')
        ax2.set(ylabel='Enhancement ratio')

    else:
        ax2 = ax.twinx()
        error1 = np.where(Transition != 0, np.abs(Clean - Transition) / Clean * 100, 0)
        error2 = np.where(Event != 0, np.abs(Transition - Event) / Transition * 100, 0)

        ax2.plot(dp, error1, ls='--', color='k', label='Error 1 ')
        ax2.plot(dp, error2, ls='--', color='gray', label='Error 2')
        ax2.set(ylabel='Error (%)')

    ax.legend(*combine_legends(fig.get_axes()), prop={'weight': 'bold'})

    plt.show()

    return fig, ax


@set_figure
def heatmap(data: DataFrame,
            unit: Literal["Number", "Surface", "Volume", "Extinction"],
            cmap: str = 'Blues',
            colorbar: bool = False,
            magic_number: int = 11,
            ax: Axes | None = None,
            **kwargs
            ) -> tuple[Figure, Axes]:
    """
    Plot a heatmap of particle size distribution.

    Parameters
    ----------
    data : pandas.DataFrame
        The data containing particle size distribution values. Each column corresponds to a size bin,
        and each row corresponds to a different distribution.

    unit : {'Number', 'Surface', 'Volume', 'Extinction'}, optional
        The unit of measurement for the data.

    cmap : str, default='Blues'
        The colormap to use for the heatmap.

    colorbar : bool, default=False
        Whether to show the colorbar.

    magic_number : int, default=11
        The number of bins to use for the histogram.

    ax : matplotlib.axes.Axes, optional
        The axes to plot the heatmap on. If not provided, a new subplot will be created.

    **kwargs
        Additional keyword arguments to pass to matplotlib functions.

    Returns
    -------
    matplotlib.axes.Axes
        The Axes object containing the heatmap.

    Examples
    --------
    >>> heatmap(DataFrame(...), unit='Number')

    Notes
    -----
    This function calculates a 2D histogram of the log-transformed particle sizes and the distribution values.
    It then plots the heatmap using a logarithmic color scale.

    """
    fig, ax = plt.subplots(**{**{'figsize': (3, 3)}, **kwargs.get('fig_kws', {})}) if ax is None else (
        ax.get_figure(), ax)

    min_value = 1e-8
    dp = np.array(data.columns, dtype=float)
    x = np.append(np.tile(dp, data.to_numpy().shape[0]), np.log(dp).max())
    y = np.append(data.to_numpy().flatten(), min_value)

    # mask NaN
    x = x[~np.isnan(y)]
    y = y[~np.isnan(y)]

    # using log(x)
    histogram, xedges, yedges = np.histogram2d(np.log(x), y, bins=len(dp) + magic_number)
    histogram[histogram == 0] = min_value  # Avoid log(0)

    plot_kws = dict(norm=colors.LogNorm(vmin=1, vmax=histogram.max()), cmap=cmap, **kwargs.get('plot_kws', {}))

    pco = ax.pcolormesh(xedges[:-1], yedges[:-1], histogram.T, shading='gouraud', **plot_kws)

    ax.plot(np.log(dp), data.mean() + data.std(), ls='dashed', color='r', label='pollutant')
    ax.plot(np.log(dp), data.mean(), ls='dashed', color='k', alpha=0.5, label='mean')
    ax.plot(np.log(dp), data.mean() - data.std(), ls='dashed', color='b', label='clean')

    ax.set(xlim=(np.log(dp).min(), np.log(dp).max()), ylim=(0, None),
           xlabel=r'$D_{p} (nm)$', ylabel=Unit(f'{unit}_dist'), title=kwargs.get('title', unit))

    major_ticks = np.power(10, np.arange(np.ceil(np.log10(dp.min())), np.floor(np.log10(dp.max())) + 1))
    minor_ticks = [v for v in np.concatenate([_ * np.arange(2, 10) for _ in major_ticks]) if min(dp) <= v <= max(dp)]

    ax.set_xticks(np.log(major_ticks))
    ax.set_xticks(np.log(minor_ticks), minor=True)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda tick, pos: "{:.0f}".format(np.exp(tick))))

    ax.ticklabel_format(axis='y', style='sci', scilimits=(0, 3), useMathText=True)
    ax.grid(axis='x', which='major', color='k', linestyle='dashdot', linewidth=0.4, alpha=0.4)
    ax.legend(prop={'weight': 'bold'})

    if colorbar:
        plt.colorbar(pco, pad=0.02, fraction=0.05, label='Counts', **kwargs.get('cbar_kws', {}))

    plt.show()

    return fig, ax


@set_figure
def heatmap_tms(data: DataFrame,
                unit: Literal["Number", "Surface", "Volume", "Extinction"],
                cmap: str = 'jet',
                ax: Axes | None = None,
                **kwargs
                ) -> tuple[Figure, Axes]:
    """ Plot the size distribution over time.

    Parameters
    ----------
    data : DataFrame
        A DataFrame of particle concentrations to plot the heatmap.

    ax : matplotlib.axis.Axis
        An axis object to plot on. If none is provided, one will be created.

    unit : Literal["Number", "Surface", "Volume", "Extinction"]
        default='Number'

    cmap : matplotlib.colormap, default='viridis'
        The colormap to use. Can be anything other that 'jet'.

    Returns
    -------
    ax : matplotlib.axis.Axis

    Notes
    -----
        Do not dropna when using this code.

    Examples
    --------
    Plot a SPMS + APS data:
    >>> heatmap_tms(DataFrame(...), cmap='jet')
    """
    fig, ax = plt.subplots(
        **{**{'figsize': (len(data.index) * 0.01, 2)}, **kwargs.get('fig_kws', {})}) if ax is None else (
        ax.get_figure(), ax)

    time = data.index
    dp = np.array(data.columns, dtype=float)

    # data = data.interpolate(method='linear', axis=0)
    data = np.nan_to_num(data.to_numpy())

    vmin_mapping = {'Number': 1e2, 'Surface': 1e8, 'Volume': 1e9, 'Extinction': 1}

    # Set the colorbar min and max based on the min and max of the values
    cbar_min = kwargs.get('cbar_kws', {}).pop('cbar_min', vmin_mapping[unit])
    cbar_max = kwargs.get('cbar_kws', {}).pop('cbar_max', np.nanmax(data))

    # Set the plot_kws
    plot_kws = dict(norm=colors.LogNorm(vmin=cbar_min, vmax=cbar_max), cmap=cmap, **kwargs.get('plot_kws', {}))

    # main plot
    pco = ax.pcolormesh(time, dp, data.T, shading='auto', **plot_kws)

    # Set ax
    st_tm, fn_tm = time[0], time[-1]
    tick_time = date_range(st_tm, fn_tm, freq=kwargs.get('freq', '10d')).strftime("%F")

    ax.set(xlim=(st_tm, fn_tm),
           ylim=(dp.min(), dp.max()),
           ylabel='$D_p (nm)$',
           xticks=tick_time,
           xticklabels=tick_time,
           yscale='log',
           title=kwargs.get('title', f'{st_tm.strftime("%F")} - {fn_tm.strftime("%F")}'))

    plt.colorbar(pco, pad=0.02, fraction=0.02, label=Unit(f'{unit}_dist'), **kwargs.get('cbar_kws', {}))

    plt.show()

    return fig, ax


@set_figure
def three_dimension(data: DataFrame | np.ndarray,
                    unit: Literal["Number", "Surface", "Volume", "Extinction"],
                    cmap: str = 'Blues',
                    ax: Axes | None = None,
                    **kwargs
                    ) -> tuple[Figure, Axes]:
    """
    Create a 3D plot with data from a pandas DataFrame or numpy array.

    Parameters
    ----------
    data : DataFrame or ndarray
        Input data containing the values to be plotted.

    unit : {'Number', 'Surface', 'Volume', 'Extinction'}
        Unit of measurement for the data.

    cmap : str, default='Blues'
        The colormap to use for the facecolors.

    ax : AxesSubplot, optional
        Matplotlib AxesSubplot. If not provided, a new subplot will be created.
    **kwargs
        Additional keyword arguments to customize the plot.

    Returns
    -------
    Axes
        Matplotlib Axes object representing the 3D plot.

    Notes
    -----
    - The function creates a 3D plot with data provided in a pandas DataFrame or numpy array.
    - The x-axis is logarithmically scaled, and ticks and labels are formatted accordingly.
    - Additional customization can be done using the **kwargs.

    Example
    -------
    >>> three_dimension(DataFrame(...), unit='Number', cmap='Blues')
    """
    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw={"projection": "3d"},
                           **kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

    dp = np.array(['11.7', *data.columns, '2437.4'], dtype=float)
    lines = data.shape[0]

    _X, _Y = np.meshgrid(np.log(dp), np.arange(lines))
    _Z = np.pad(data, ((0, 0), (1, 1)), 'constant')

    verts = []
    for i in range(_X.shape[0]):
        verts.append(list(zip(_X[i, :], _Z[i, :])))

    facecolors = plt.colormaps[cmap](np.linspace(0, 1, len(verts)))
    poly = PolyCollection(verts, facecolors=facecolors, edgecolors='k', lw=0.5, alpha=.7)
    ax.add_collection3d(poly, zs=range(1, lines + 1), zdir='y')

    ax.set(xlim=(np.log(11.7), np.log(2437.4)), ylim=(1, lines), zlim=(0, np.nanmax(_Z)),
           xlabel='$D_{p} (nm)$', ylabel='Class', zlabel=Unit(f'{unit}_dist'))

    ax.set_xticks(np.log([10, 100, 1000]))
    ax.set_xticks(np.log([20, 30, 40, 50, 60, 70, 80, 90, 200, 300, 400, 500, 600, 700, 800, 900, 2000]), minor=True)
    ax.xaxis.set_major_formatter(FuncFormatter((lambda tick, pos: "{:.0f}".format(np.exp(tick)))))
    ax.ticklabel_format(axis='z', style='sci', scilimits=(0, 3), useMathText=True)

    ax.zaxis.get_offset_text().set_visible(False)
    exponent = np.floor(np.log10(np.nanmax(data))).astype(int)
    ax.text(ax.get_xlim()[1] * 1.05, ax.get_ylim()[1], ax.get_zlim()[1] * 1.1, s=fr'${{\times}}\ 10^{exponent}$')

    plt.show()

    return fig, ax


@set_figure
def curve_fitting(dp: np.ndarray,
                  dist: np.ndarray | Series | DataFrame,
                  mode: int = None,
                  unit: Literal["Number", "Surface", "Volume", "Extinction"] = None,
                  ax: Axes | None = None,
                  **kwargs
                  ) -> tuple[Figure, Axes]:
    """
    Fit a log-normal distribution to the given data and plot the result.

    Parameters
    ----------
    - dp (array): Array of diameter values.
    - dist (array): Array of distribution values corresponding to each diameter.
    - mode (int, optional): Number of log-normal distribution to fit (default is None).
    - **kwargs: Additional keyword arguments to be passed to the plot_function.

    Returns
    -------
    None

    Notes
    -----
    - The function fits a sum of log-normal distribution to the input data.
    - The number of distribution is determined by the 'mode' parameter.
    - Additional plotting customization can be done using the **kwargs.

    Example
    -------
    >>> curve_fitting(dp, dist, mode=2, xlabel="Diameter (nm)", ylabel="Distribution")
    """
    fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

    # Calculate total number concentration and normalize distribution
    total_num = np.sum(dist * log(dp))
    norm_data = dist / total_num

    def lognorm_func(x, *params):
        num_distributions = len(params) // 3
        result = np.zeros_like(x)

        for i in range(num_distributions):
            offset = i * 3
            _number, _geomean, _geostd = params[offset: offset + 3]

            result += (_number / (log(_geostd) * sqrt(2 * pi)) *
                       exp(-(log(x) - log(_geomean)) ** 2 / (2 * log(_geostd) ** 2)))

        return result

    # initial gauss
    min_value = np.array([min(dist)])
    extend_ser = np.concatenate([min_value, dist, min_value])
    _mode, _ = find_peaks(extend_ser, distance=20)
    peak = dp[_mode - 1]
    mode = mode or len(peak)

    # 初始參數猜測
    initial_guess = [0.05, 20., 2.] * mode

    # 設定參數範圍
    bounds = ([1e-6, 10, 1] * mode, [1, 3000, 8] * mode)

    # 使用 curve_fit 函數進行擬合
    result = curve_fit(lognorm_func, dp, norm_data, p0=initial_guess, bounds=bounds)

    # 獲取擬合的參數
    params = result[0].tolist()

    print('\n' + "Fitting Results:")
    table = []

    for i in range(mode):
        offset = i * 3
        num, mu, sigma = params[offset:offset + 3]
        table.append([f'log-{i + 1}', f"{num * total_num:.3f}", f"{mu:.3f}", f"{sigma:.3f}"])

    # 使用 tabulate 來建立表格並印出
    print(tabulate(table, headers=["log-", "number", "mu", "sigma"], floatfmt=".3f", tablefmt="fancy_grid"))

    fit_curve = total_num * lognorm_func(dp, *params)

    plt.plot(dp, fit_curve, color='#c41b1b', label='Fitting curve', lw=2.5)
    plt.plot(dp, dist, color='b', label='Observed curve', lw=2.5)

    ax.set(xlim=(dp.min(), dp.max()), ylim=(0, None), xscale='log',
           xlabel=r'$\bf D_{p}\ (nm)$', ylabel=Unit(f'{unit}_dist'), title=kwargs.get('title'))

    plt.grid(color='k', axis='x', which='major', linestyle='dashdot', linewidth=0.4, alpha=0.4)
    ax.ticklabel_format(axis='y', style='sci', scilimits=(0, 3), useMathText=True)
    ax.legend(prop={'weight': 'bold'})

    plt.show(block=True)

    return fig, ax


@set_figure
def ls_mode(**kwargs) -> tuple[Figure, Axes]:
    """
    Plot log-normal mass size distribution for small mode, large mode, and sea salt particles.

    Parameters
    ----------
    **kwargs : dict
        Additional keyword arguments.

    Examples
    --------
    Example : Plot log-normal mass size distribution with default settings
    >>> ls_mode()
    """

    fig, ax = plt.subplots(**kwargs.get('fig_kws', {}))

    geoMean = [0.2, 0.5, 2.5]
    geoStdv = [2.2, 1.5, 2.0]
    color = ['g', 'r', 'b']
    label = [r'$\bf Small\ mode\ :D_{g}\ =\ 0.2\ \mu m,\ \sigma_{{g}}\ =\ 2.2$',
             r'$\bf Large\ mode\ :D_{g}\ =\ 0.5\ \mu m,\ \sigma_{{g}}\ =\ 1.5$',
             r'$\bf Sea\ salt\ :D_{g}\ =\ 2.5\ \mu m,\ \sigma_{{g}}\ =\ 2.0$']

    x = np.geomspace(0.001, 20, 10000)
    for _gmd, _gsd, _color, _label in zip(geoMean, geoStdv, color, label):
        lognorm = 1 / (log(_gsd) * sqrt(2 * pi)) * (exp(-(log(x) - log(_gmd)) ** 2 / (2 * log(_gsd) ** 2)))

        ax.semilogx(x, lognorm, color=_color, label=_label)
        ax.fill_between(x, lognorm, 0, where=(lognorm > 0), color=_color, alpha=0.3, label='__nolegend__')

    ax.set(xlim=(0.001, 20), ylim=(0, None), xscale='log', xlabel=r'$\bf D_{p}\ (nm)$',
           ylabel=r'$\bf Probability\ (dM/dlogdp)$', title=r'Log-normal Mass Size Distribution')

    ax.grid(color='k', axis='x', which='major', linestyle='dashdot', linewidth=0.4, alpha=0.4)
    ax.legend(prop={'weight': 'bold'})

    plt.show()

    return fig, ax


@set_figure
def lognorm_dist(**kwargs) -> tuple[Figure, Axes]:
    #
    """
    Plot various particle size distribution to illustrate log-normal distribution and transformations.

    Parameters
    ----------
    **kwargs : dict
        Additional keyword arguments.

    Examples
    --------
    Example : Plot default particle size distribution
    >>> lognorm_dist()
    """

    fig, ax = plt.subplots(2, 2, **kwargs.get('fig_kws', {}))
    ([ax1, ax2], [ax3, ax4]) = ax
    fig.suptitle('Particle Size Distribution', fontweight='bold')
    plt.subplots_adjust(left=0.125, right=0.925, bottom=0.1, top=0.93, wspace=0.4, hspace=0.4)

    # pdf
    normpdf = lambda x, mu, sigma: (1 / (sigma * sqrt(2 * pi))) * exp(-(x - mu) ** 2 / (2 * sigma ** 2))
    lognormpdf = lambda x, gmean, gstd: (1 / (log(gstd) * sqrt(2 * pi))) * exp(
        -(log(x) - log(gmean)) ** 2 / (2 * log(gstd) ** 2))
    lognormpdf2 = lambda x, gmean, gstd: (1 / (x * log(gstd) * sqrt(2 * pi))) * exp(
        -(log(x) - log(gmean)) ** 2 / (2 * log(gstd) ** 2))

    # 生成x
    x = np.linspace(-10, 10, 1000)
    x2 = np.geomspace(0.01, 100, 1000)

    # Question 1
    # 若對數常態分布x有gmd=3, gstd=2，ln(x) ~ 常態分佈，試問其分布的平均值與標準差??  Y ~ N(mu=log(gmean), sigma=log(gstd))
    data1 = lognorm(scale=3, s=log(2)).rvs(size=5000)

    # Question 2
    # 若常態分布x有平均值3 標準差1，exp(x)則為一對數常態分佈? 由對數常態分佈的定義 若隨機變數ln(Z)是常態分布 則Z為對數常態分布
    # 因此已知Z = exp(x), so ln(Z)=x，Z ~ 對數常態分佈，試問其分布的幾何平均值與幾何標準差是??  Z ~ LN(geoMean=exp(mu), geoStd=exp(sigma))
    data2 = norm(loc=3, scale=1).rvs(size=5000)

    def plot_distribution(ax, x, pdf, color='k-', xscale='linear'):
        ax.plot(x, pdf, color)
        ax.set(xlabel='Particle Size (micron)', ylabel='Probability Density', xlim=(x.min(), x.max()), xscale=xscale)

    # 繪製粒徑分布
    plot_distribution(ax1, x, normpdf(x, mu=0, sigma=2))

    plot_distribution(ax2, x2, lognormpdf(x2, gmean=0.8, gstd=1.5), 'g-', xscale='log')
    plot_distribution(ax2, x2, lognormpdf2(x2, gmean=0.8, gstd=1.5), 'r--', xscale='log')
    plot_distribution(ax2, x2, lognorm(scale=0.8, s=log(1.5)).pdf(x2), 'b--', xscale='log')

    plot_distribution(ax3, x, normpdf(x, mu=log(3), sigma=log(2)), 'k-')
    ax3.hist(log(data1), bins=100, density=True, alpha=0.6, color='g')

    plot_distribution(ax4, x2, lognormpdf2(x2, gmean=exp(3), gstd=exp(1)), 'r-', xscale='log')
    ax4.hist(exp(data2), bins=100, density=True, alpha=0.6, color='g')

    plt.show()

    return fig, ax


if __name__ == '__main__':
    lognorm_dist()
