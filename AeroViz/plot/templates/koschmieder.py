
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.pyplot import Figure, Axes
from scipy.optimize import curve_fit

from AeroViz.plot.utils import *

__all__ = ['koschmieder']


@set_figure(figsize=(2.4, 3))
def koschmieder(df: pd.DataFrame,
                vis: str,
                ext: list[str],
                ax: Axes | None = None,
                **kwargs
                ) -> tuple[Figure, Axes]:
    """
    Plot Koschmieder relationship between Visibility and Extinction.

    x = Visibility, y = Extinction, log-log fit!!
    """
    def _log_fit(x, y, func=lambda x, a: -x + a):
        x_log, y_log = np.log(x), np.log(y)
        popt, pcov = curve_fit(func, x_log, y_log)

        return np.exp(popt)[0], pcov

    fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

    boxcolors = ['#a5bf6b', '#3f83bf']
    scattercolor = ['green', 'blue']
    arts = []
    labels = []

    for i, ext_col in enumerate(ext):
        _df = df[[ext_col, vis]].dropna().copy()
        x_data = _df[vis]
        y_data = _df[ext_col]

        bins = np.linspace(0, 50, 25)
        wid = (bins + (bins[1] - bins[0]) / 2)[0:-1]

        _df[f'{vis}_bins'] = pd.cut(x_data, bins=bins, labels=wid)

        grouped = _df.groupby(f'{vis}_bins', observed=False)

        vis_labels, vals, median_vals = [], [], []
        for _, subdf in grouped:
            if len(subdf[ext_col].dropna()) > 3:
                vis_labels.append(subdf[vis].mean())
                vals.append(subdf[ext_col].dropna().values)
                median_vals.append(subdf[ext_col].mean())

        plt.boxplot(vals, labels=vis_labels, positions=np.array(vis_labels, dtype='float'),
                    widths=(bins[1] - bins[0]) / 2.5,
                    showfliers=False, showmeans=True, meanline=False, patch_artist=True,
                    boxprops=dict(facecolor=boxcolors[i], alpha=.7),
                    meanprops=dict(marker='o', markerfacecolor='white', markeredgecolor='k', markersize=4),
                    medianprops=dict(color='#000000', ls='-'))

        plt.scatter(x_data, y_data, marker='.', s=10, facecolor='white', edgecolor=boxcolors[i], alpha=0.1)

        # fit curve
        coeff, _ = _log_fit(np.array(vis_labels, dtype='float'), np.array(median_vals, dtype='float'))

        # Plot lines (ref & Measurement)
        x_fit = np.linspace(0.1, 50, 1000)

        func = lambda x, a: a / x
        line, = ax.plot(x_fit, func(x_fit, coeff), c=scattercolor[i], lw=3,
                        label=f'Vis (km) = {round(coeff)} / Ext')

        arts.append(line)
        if 'dry' in ext_col:
            labels.append(f'Vis (km) = {round(coeff)} / Ext (dry)')
        else:
            labels.append(f'Vis (km) = {round(coeff)} / Ext (amb)')

    ax.legend(handles=arts, labels=labels, loc='upper right', prop=dict(weight='bold'), bbox_to_anchor=(0.99, 0.99))

    ax.set(xlabel=kwargs.get('xlabel', 'Visibility (km)'),
           ylabel=kwargs.get('ylabel', 'Extinction (1/Mm)'),
           title=kwargs.get('title', 'Koschmieder relationship'),
           xlim=kwargs.get('xlim', (0, 30)),
           ylim=kwargs.get('ylim', (0, 800))
           )

    plt.xticks(ticks=np.array(range(0, 31, 5)), labels=np.array(range(0, 31, 5)))

    plt.show()

    return fig, ax
