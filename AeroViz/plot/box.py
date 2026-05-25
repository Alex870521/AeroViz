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
    """Grouped box plot of ``y`` against ``x``.

    Two modes, chosen automatically:

    - **Categorical** — when ``x`` is non-numeric (e.g. a 'season' column) or
      ``x_bins`` is omitted: one box per unique ``x`` value.
    - **Binned** — when ``x`` is numeric and ``x_bins`` is given: ``x`` is cut
      into the supplied bin edges (any width, integer or float) and one box is
      drawn per bin.
    """
    fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

    df = df.dropna(subset=[x, y]).copy()

    box_style = dict(showfliers=False, showmeans=True, meanline=True, patch_artist=True,
                     boxprops=dict(facecolor='#f2c872', alpha=.7),
                     meanprops=dict(color='#000000', ls='none'),
                     medianprops=dict(ls='-', color='#000000'))

    numeric_x = pd.api.types.is_numeric_dtype(df[x])

    if x_bins is None or not numeric_x:
        # ---- categorical mode: one box per unique category ----
        if isinstance(df[x].dtype, pd.CategoricalDtype):
            categories = [c for c in df[x].cat.categories if (df[x] == c).any()]
        elif numeric_x:
            categories = sorted(df[x].unique())
        else:
            categories = list(pd.unique(df[x]))

        positions = np.arange(len(categories), dtype=float)
        vals = [df.loc[df[x] == c, y].to_numpy() for c in categories]
        labels = [str(c) for c in categories]
        jitter_sd = 0.08
        xlim = kwargs.get('xlim', (-0.5, len(categories) - 0.5))
    else:
        # ---- numeric binned mode (float-safe: no rounding of the edges) ----
        bins = np.asarray(x_bins, dtype=float)
        centers = (bins[:-1] + bins[1:]) / 2
        binned = pd.cut(df[x].to_numpy(), bins=bins, labels=centers, include_lowest=True)
        df = df.assign(_bin=binned)

        positions, vals, labels = [], [], []
        for center, subdf in df.groupby('_bin', observed=False):
            arr = subdf[y].to_numpy()
            if len(arr):                       # skip empty bins (boxplot can't draw them)
                positions.append(float(center))
                vals.append(arr)
        positions = np.asarray(positions, dtype=float)

        def _fmt(b):
            return ('{:.0f}' if np.isclose(b, round(b)) else '{:g}').format(b)

        ax.set_xticks(bins, labels=[_fmt(b) for b in bins])
        jitter_sd = (bins[1] - bins[0]) / 8
        xlim = kwargs.get('xlim', (bins[0], bins[-1]))

    if not vals:
        raise ValueError(f"box(): no data to plot for x={x!r}, y={y!r}.")

    widths = (np.diff(positions).min() / 2) if len(positions) > 1 else 0.5
    plt.boxplot(vals, positions=positions, widths=widths, **box_style)

    if x_bins is None or not numeric_x:
        ax.set_xticks(positions, labels=labels)

    ax.set(xlim=xlim,
           ylim=kwargs.get('ylim', (df[y].min(), df[y].max())),
           xlabel=kwargs.get('xlabel', Unit(x)),
           ylabel=kwargs.get('ylabel', Unit(y)),
           title=kwargs.get('title', ''))

    if add_scatter:
        for pos, arr in zip(positions, vals):
            jitter = np.random.normal(0, jitter_sd, len(arr))
            ax.scatter(np.full(len(arr), pos) + jitter, arr, s=10, c='gray', alpha=0.5)

    plt.show()

    return fig, ax


if __name__ == '__main__':
    from AeroViz import DataBase

    df = DataBase(load_data=True)
    box(df, x='PM25', y='Extinction', x_bins=np.arange(0, 120, 10))
