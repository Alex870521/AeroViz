import matplotlib.pyplot as plt
import numpy as np
from matplotlib.pyplot import Figure, Axes
from scipy.optimize import curve_fit

from AeroViz.plot.utils import *

__all__ = ['contour']


@set_figure
def contour(df, ax: Axes | None = None, **kwargs) -> tuple[Figure, Axes]:
    fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

    npoints = 1000
    xreg = np.linspace(df.PM25.min(), df.PM25.max(), 83)
    yreg = np.linspace(df.gRH.min(), df.gRH.max(), 34)
    X, Y = np.meshgrid(xreg, yreg)

    d_f = df.copy()
    df['gRH'] = d_f['gRH'].round(2)
    df['PM25'] = d_f['PM25'].round(2)

    def func(data, *params):
        return params[0] * data ** (params[1])

    initial_guess = [1.0, 1.0]

    fit_df = df[['PM25', 'gRH', 'Extinction']].dropna()
    popt, pcov = curve_fit(func, xdata=(fit_df['PM25'] * fit_df['gRH']), ydata=fit_df['Extinction'], p0=initial_guess,
                           maxfev=2000000, method='trf')

    x, y = df.PM25, df.gRH

    # pcolor = ax.pcolormesh(X, Y, (X * 4.5 * Y ** (1 / 3)), cmap='jet', shading='auto', vmin=0, vmax=843, alpha=0.8)
    Z = func(X * Y, *popt)
    cont = ax.contour(X, Y, Z, colors='black', levels=5, vmin=0, vmax=Z.max())
    conf = ax.contourf(X, Y, Z, cmap='YlGnBu', levels=100, vmin=0, vmax=Z.max())
    ax.clabel(cont, colors=['black'], fmt=lambda s: f"{s:.0f} 1/Mm")
    ax.set(xlabel=Unit('PM25'), ylabel=Unit('gRH'), xlim=(x.min(), x.max()), ylim=(y.min(), y.max()))

    color_bar = plt.colorbar(conf, pad=0.02, fraction=0.05, label='Extinction (1/Mm)')
    color_bar.ax.set_xticklabels(color_bar.ax.get_xticks().astype(int))

    plt.show()

    return fig, ax
