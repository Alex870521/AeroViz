import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.pyplot import Figure, Axes

from AeroViz.plot.utils import *

__all__ = ['box']


@set_figure
def box(df: pd.DataFrame,
        x: str,
        y: str,
        x_bins: list | np.ndarray = None,
        add_scatter: bool = True,
        ax: Axes | None = None,
        **kwargs
        ) -> tuple[Figure, Axes]:
    fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

    df = df.dropna(subset=[x, y]).copy()
    x_data, y_data = df[x].to_numpy(), df[y].to_numpy()

    bins = np.array(x_bins)
    bins = np.round(bins)
    wid = (bins + (bins[1] - bins[0]) / 2)[0:-1]

    df[x + '_bin'] = pd.cut(x=x_data, bins=bins, labels=wid)

    group = x + '_bin'
    column = y
    grouped = df.groupby(group, observed=False)

    names, vals = [], []

    for i, (name, subdf) in enumerate(grouped):
        names.append('{:.0f}'.format(name))
        vals.append(subdf[column].dropna().values)

    plt.boxplot(vals, labels=names, positions=wid, widths=(bins[1] - bins[0]) / 3,
                showfliers=False, showmeans=True, meanline=True, patch_artist=True,
                boxprops=dict(facecolor='#f2c872', alpha=.7),
                meanprops=dict(color='#000000', ls='none'),
                medianprops=dict(ls='-', color='#000000'))

    ax.set(xlim=kwargs.get('xlim', (x_data.min(), x_data.max())),
           ylim=kwargs.get('ylim', (y_data.min(), y_data.max())),
           xlabel=kwargs.get('xlabel', Unit(x)),
           ylabel=kwargs.get('ylabel', Unit(y)),
           title=kwargs.get('title', ''))

    ax.set_xticks(bins, labels=bins.astype(int))

    if add_scatter:
        for i, (name, subdf) in enumerate(grouped):
            jitter = np.random.normal(0, 0.5, len(subdf))
            ax.scatter([name] * len(subdf) + jitter, subdf[column], s=10, c='gray', alpha=0.5)

    plt.show()

    return fig, ax


if __name__ == '__main__':
    from AeroViz import DataBase

    df = DataBase(load_data=True)
    box(df, x='PM25', y='Extinction', x_bins=np.arange(0, 120, 10))
