from functools import wraps
from typing import Literal

import matplotlib.pyplot as plt
from matplotlib.pyplot import Axes

__all__ = ['set_figure', 'combine_legends', 'auto_label_pct']


def set_figure(func=None,
               *,
               figsize: tuple | None = None,
               fs: int | None = None,
               fw: str = None,
               autolayout: bool = True):
    # For more details please see https://matplotlib.org/stable/users/explain/customizing.html
    def decorator(_func):
        @wraps(_func)
        def wrapper(*args, **kwargs):
            print(f'\n\tPlot:\033[96m {_func.__name__}\033[0m')

            plt.rcParams['mathtext.fontset'] = 'custom'
            plt.rcParams['mathtext.rm'] = 'Times New Roman'
            plt.rcParams['mathtext.it'] = 'Times New Roman: italic'
            plt.rcParams['mathtext.bf'] = 'Times New Roman: bold'
            plt.rcParams['mathtext.default'] = 'regular'

            # The font properties used by `text.Text`.
            # The text, annotate, label, title, ticks, are used to create text
            plt.rcParams['font.family'] = 'Times New Roman'
            plt.rcParams['font.weight'] = fw or 'normal'
            plt.rcParams['font.size'] = fs or 8

            plt.rcParams['axes.titlesize'] = 'large'
            plt.rcParams['axes.titleweight'] = 'bold'
            plt.rcParams['axes.labelweight'] = 'bold'

            # color
            plt.rcParams['axes.prop_cycle'] = plt.cycler(color=['b', 'g', 'r', 'c', 'm', 'y', 'k'])

            plt.rcParams['xtick.labelsize'] = 'medium'
            plt.rcParams['ytick.labelsize'] = 'medium'

            # matplotlib.font_manager.FontProperties ---> matplotlib.rcParams
            plt.rcParams['legend.loc'] = 'best'
            plt.rcParams['legend.frameon'] = False
            plt.rcParams['legend.fontsize'] = 'small'
            plt.rcParams['legend.title_fontsize'] = 'medium'
            plt.rcParams['legend.handlelength'] = 1.5
            plt.rcParams['legend.labelspacing'] = 0.7

            plt.rcParams['figure.figsize'] = figsize or (4, 4)
            plt.rcParams['figure.dpi'] = 200
            plt.rcParams['figure.autolayout'] = autolayout

            if not autolayout:
                plt.rcParams['figure.subplot.left'] = 0.1
                plt.rcParams['figure.subplot.right'] = 0.875
                plt.rcParams['figure.subplot.top'] = 0.875
                plt.rcParams['figure.subplot.bottom'] = 0.125

            # plt.rcParams['figure.constrained_layout.use'] = True

            plt.rcParams['savefig.transparent'] = True

            return _func(*args, **kwargs)

        return wrapper

    if func is None:
        return decorator

    return decorator(func)


def combine_legends(axes_list: list[Axes]) -> tuple[list, list]:
    return (
        [legend for axes in axes_list for legend in axes.get_legend_handles_labels()[0]],
        [label for axes in axes_list for label in axes.get_legend_handles_labels()[1]]
    )


def auto_label_pct(pct,
                   symbol: bool = True,
                   include_pct: bool = False,
                   ignore: Literal["inner", "outer"] = 'inner',
                   value: float = 2):
    if not symbol:
        return ''
    cond = pct <= value if ignore == 'inner' else pct > value
    label = '' if cond else '{:.1f}'.format(pct)
    return '' if label == '' else label + '%' if include_pct else label
