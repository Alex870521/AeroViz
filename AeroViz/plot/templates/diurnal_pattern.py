import matplotlib.pyplot as plt
from matplotlib.pyplot import Figure, Axes
from matplotlib.ticker import AutoMinorLocator
from pandas import DataFrame

from AeroViz.plot.utils import *

__all__ = ['diurnal_pattern']


@set_figure
def diurnal_pattern(df: DataFrame,
                    y: str | list[str],
                    std_area: float = 0.5,
                    ax: Axes | None = None,
                    **kwargs
                    ) -> tuple[Figure, Axes]:
    if 'hour' not in df.columns and 'Hour' not in df.columns:
        df['Hour'] = df.index.hour

    Hour = range(0, 24)
    mean = df.groupby('Hour')[y].mean()
    std = df.groupby('Hour')[y].std() * std_area

    fig, ax = plt.subplots() if ax is None else (ax.get_figure(), ax)

    # Plot Diurnal pattern
    ax.plot(Hour, mean, 'blue', zorder=3)
    ax.fill_between(Hour, y1=mean + std, y2=mean - std, alpha=0.2, color='blue', edgecolor=None, zorder=2)

    # Plot Boxplot for each hour
    bp = ax.boxplot([df[df['Hour'] == h][y].dropna() for h in Hour],
                    positions=Hour,
                    widths=0.5,
                    patch_artist=True,
                    showfliers=False,
                    zorder=1)

    # Customize boxplot colors
    for element in ['boxes', 'whiskers', 'fliers', 'means', 'medians', 'caps']:
        plt.setp(bp[element], color='gray')

    for patch in bp['boxes']:
        patch.set(facecolor='lightgray', alpha=0.5)

    ax.set(xlabel=kwargs.get('xlabel', 'Hours'),
           ylabel=kwargs.get('ylabel', Unit(y)),
           xlim=kwargs.get('xlim', (-0.5, 23.5)),
           ylim=kwargs.get('ylim', (None, None)),
           xticks=kwargs.get('xticks', range(0, 24, 4)),
           xticklabels=kwargs.get('xticklabels', range(0, 24, 4)))

    ax.tick_params(axis='both', which='major')
    ax.tick_params(axis='x', which='minor')
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.ticklabel_format(axis='y', style='sci', scilimits=(-2, 3), useMathText=True)

    plt.tight_layout()
    plt.show()

    return fig, ax