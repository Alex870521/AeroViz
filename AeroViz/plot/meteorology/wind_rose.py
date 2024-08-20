from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
import windrose
from matplotlib.pyplot import Figure, Axes
from pandas import DataFrame, Series

from AeroViz.plot.utils import *

__all__ = ['wind_rose']


@set_figure(figsize=(4.3, 4))
def wind_rose(df: DataFrame,
              WS: Series | str,
              WD: Series | str,
              val: Series | str | None = None,
              typ: Literal['bar', 'scatter'] = 'scatter',
              rlabel_pos: float = 30,
              **kwargs
              ) -> tuple[Figure, Axes]:
    # conditional bivariate probability function (cbpf) python
    # https://davidcarslaw.github.io/openair/reference/polarPlot.html
    # https://github.com/davidcarslaw/openair/blob/master/R/polarPlot.R
    windrose.WindroseAxes._info = 'WindroseAxes'

    df = df.dropna(subset=[WS, WD] + ([val] if val is not None else []))

    radius = df[WS].to_numpy()
    theta = df[WD].to_numpy()
    radian = np.radians(theta)
    values = df[val].to_numpy() if val is not None else None

    # In this case, the windrose is a simple frequency diagram,
    # the function automatically calculates the radians of the given wind direction.
    if typ == 'bar':
        fig, ax = plt.subplots(figsize=(5.5, 4), subplot_kw={'projection': 'windrose'})
        fig.subplots_adjust(left=0)

        ax.bar(theta, radius, bins=[0, 1, 2, 3], normed=True, colors=['#0F1035', '#365486', '#7FC7D9', '#DCF2F1'])
        ax.set(
            ylim=(0, 30),
            yticks=[0, 15, 30],
            yticklabels=['', '15 %', '30 %'],
            rlabel_position=rlabel_pos
        )
        ax.set_thetagrids(angles=[0, 45, 90, 135, 180, 225, 270, 315],
                          labels=["E", "NE", "N", "NW", "W", "SW", "S", "SE"])

        ax.legend(units='m/s', bbox_to_anchor=[1.1, 0.5], loc='center left', ncol=1)

    # In this case, the windrose is a scatter plot,
    # in contrary, this function does not calculate the radians, so user have to input the radian.
    else:
        fig, ax = plt.subplots(figsize=(5, 4), subplot_kw={'projection': 'windrose'})
        fig.subplots_adjust(left=0)

        scatter = ax.scatter(radian, radius, s=15, c=values, vmax=np.quantile(values, 0.90), edgecolors='none',
                             cmap='jet', alpha=0.8)
        ax.set(
            ylim=(0, 7),
            yticks=[1, 3, 5, 7],
            yticklabels=['1 m/s', '3 m/s', '5 m/s', '7 m/s'],
            rlabel_position=rlabel_pos,
            theta_direction=-1,
            theta_zero_location='N',
            title=kwargs.get('title', None)
        )
        ax.set_thetagrids(angles=[0, 45, 90, 135, 180, 225, 270, 315],
                          labels=["N", "NE", "E", "SE", "S", "SW", "W", "NW"])

        plt.colorbar(scatter, ax=ax, label=Unit(val), pad=0.1, fraction=0.04)

    plt.show()

    return fig, ax
