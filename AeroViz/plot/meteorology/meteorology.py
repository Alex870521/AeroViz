import math
from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import windrose
from matplotlib.pyplot import Figure, Axes
from pandas import DataFrame, Series
from scipy.ndimage import gaussian_filter

from AeroViz.plot.utils import *

__all__ = ['wind_rose',
           'CBPF'
           ]


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


# TODO: fix the bug of the CBPF function
@set_figure(figsize=(4.3, 4))
def CBPF(df: DataFrame,
         WS: Series | str,
         WD: Series | str,
         val: Series | str | None = None,
         percentile: list | float | int | None = None,
         max_ws: float | None = 5,
         resolution: int = 100,
         sigma: float | tuple = 2,
         rlabel_pos: float = 30,
         bottom_text: str | bool | None = None,
         **kwargs
         ) -> tuple[Figure, Axes]:
    # conditional bivariate probability function (cbpf) python
    # https://davidcarslaw.github.io/openair/reference/polarPlot.html
    # https://github.com/davidcarslaw/openair/blob/master/R/polarPlot.R

    df = df.dropna(subset=[WS, WD] + ([val] if val is not None else [])).copy()

    df['u'] = df[WS].to_numpy() * np.sin(np.radians(df[WD].to_numpy()))
    df['v'] = df[WS].to_numpy() * np.cos(np.radians(df[WD].to_numpy()))

    u_bins = np.linspace(df.u.min(), df.u.max(), resolution)
    v_bins = np.linspace(df.v.min(), df.v.max(), resolution)

    # 使用 u_group 和 v_group 進行分組
    df['u_group'] = pd.cut(df['u'], u_bins)
    df['v_group'] = pd.cut(df['v'], v_bins)
    grouped = df.groupby(['u_group', 'v_group'], observed=False)

    X, Y = np.meshgrid(u_bins, v_bins)

    # Note:
    # The CBPF is the ratio between the number of points in each cell and the total number of points.
    # So, it is not equal to the probability density function (PDF) of the wind speed and wind direction.

    if percentile is None:
        histogram = (grouped[val].count() / grouped[val].count().sum()).unstack().values.T
        # histogram, v_edges, u_edges = np.histogram2d(df.v, df.u, bins=(v_bins, u_bins))
        # histogram = histogram / histogram.sum()
        histogram = np.where(histogram == 0, np.nan, histogram)
        bottom_text = rf'$PDF\ plot$'

    else:
        if not all(0 <= p <= 100 for p in (percentile if isinstance(percentile, list) else [percentile])):
            raise ValueError("Percentile must be between 0 and 100")

        if isinstance(percentile, (float, int)):
            bottom_text = rf'$CPF:\ >{int(percentile)}^{{th}}$'
            thershold = df[val].quantile(percentile / 100)
            cond = lambda x: (x >= thershold).sum()

        elif isinstance(percentile, list) and len(percentile) == 1:
            # Extract the single element from the list
            single_percentile = percentile[0]
            bottom_text = rf'$CPF:\ >{int(single_percentile)}^{{th}}$'
            threshold = df[val].quantile(single_percentile / 100)
            cond = lambda x: (x >= threshold).sum()

        else:
            bottom_text = rf'$CPF:\ {int(percentile[0])}^{{th}}\ to\ {int(percentile[1])}^{{th}}$'
            thershold_small, thershold_large = df[val].quantile([percentile[0] / 100, percentile[1] / 100])
            cond = lambda x: ((x >= thershold_small) & (x < thershold_large)).sum()

        histogram = (grouped[val].apply(cond) / grouped[val].count()).unstack().values.T

    # if np.isnan(histogram).all():
    #     raise "CBPF_array contains only NaN values."
    # else:
    #     print(f"\nHistogram contains NaN before masking: {np.isnan(histogram).sum()}")

    histogram_filled = np.nan_to_num(histogram, nan=0)  # 將 NaN 替換為 0

    filtered_histogram = gaussian_filter(histogram_filled, sigma=sigma)
    filtered_histogram[np.isnan(histogram)] = np.nan

    def is_within_circle(center_row, center_col, row, col, radius):
        return np.sqrt((center_row - row) ** 2 + (center_col - col) ** 2) <= radius

    def remove_lonely_point(filtered_histogram, radius=4, magic_num=13):
        rows, cols = filtered_histogram.shape
        data_positions = np.where(~np.isnan(filtered_histogram))

        for row, col in zip(*data_positions):
            valid_data_count = 0
            for i in range(max(0, row - radius), min(rows, row + radius + 1)):
                for j in range(max(0, col - radius), min(cols, col + radius + 1)):
                    if (i, j) != (row, col) and is_within_circle(row, col, i, j, radius):
                        if not np.isnan(filtered_histogram[i, j]):
                            valid_data_count += 1

            if valid_data_count <= magic_num:
                filtered_histogram[row, col] = np.nan

        return filtered_histogram

    def fill_nan_with_mean(filtered_histogram, radius=4, magic_num=13):
        rows, cols = filtered_histogram.shape
        nan_positions = np.where(np.isnan(filtered_histogram))

        for row, col in zip(*nan_positions):
            surrounding_values = []
            surrounding_values_within_one = []
            nan_count = 0

            for i in range(max(0, row - radius), min(rows, row + radius + 1)):
                for j in range(max(0, col - radius), min(cols, col + radius + 1)):
                    if (i, j) != (row, col) and is_within_circle(row, col, i, j, radius):
                        if np.isnan(filtered_histogram[i, j]):
                            nan_count += 1
                        else:
                            surrounding_values.append(filtered_histogram[i, j])

            for i in range(max(0, row - 2), min(rows, row + 2 + 1)):
                for j in range(max(0, col - 2), min(cols, col + 2 + 1)):
                    if (i, j) != (row, col) and is_within_circle(row, col, i, j, 2):
                        if np.isnan(filtered_histogram[i, j]):
                            pass
                        else:
                            surrounding_values_within_one.append(filtered_histogram[i, j])

            if nan_count < magic_num and surrounding_values_within_one:
                filtered_histogram[row, col] = np.mean(surrounding_values)

        return filtered_histogram

    # Apply the function to your data
    fil_radius, magic_num = 3, 13
    filtered_histogram = remove_lonely_point(filtered_histogram, fil_radius, magic_num)
    filtered_histogram = fill_nan_with_mean(filtered_histogram, fil_radius, magic_num)
    if np.all(np.isnan(filtered_histogram)):
        raise ValueError("All values in the filtered histogram are NaN. Please decrease the resolution.")
    # plot
    fig, ax = plt.subplots()
    fig.subplots_adjust(left=0)

    surf = ax.pcolormesh(X, Y, filtered_histogram, shading='auto', cmap='jet', antialiased=True)

    max_ws = max_ws or np.concatenate((abs(df.u), abs(df.v))).max()  # Get the maximum value of the wind speed

    radius_lst = np.arange(1, math.ceil(max_ws) + 1)  # Create a list of radius

    for i, radius in enumerate(radius_lst):
        circle = plt.Circle((0, 0), radius, fill=False, color='gray', linewidth=1, linestyle='--', alpha=0.5)
        ax.add_artist(circle)

        for angle, label in zip(range(0, 360, 90), ["E", "N", "W", "S"]):
            radian = np.radians(angle)
            line_x, line_y = radius * np.cos(radian), radius * np.sin(radian)

            if i + 2 == len(radius_lst):  # Add wind direction line and direction label at the edge of the circle
                ax.plot([0, line_x * 1.05], [0, line_y * 1.05], color='k', linestyle='-', linewidth=1, alpha=0.5)
                ax.text(line_x * 1.15, line_y * 1.15, label, ha='center', va='center')

        ax.text(radius * np.cos(np.radians(rlabel_pos)), radius * np.sin(np.radians(rlabel_pos)),
                str(radius) + ' m/s', ha='center', va='center', fontsize=8)

    for radius in range(math.ceil(max_ws) + 1, 10):
        circle = plt.Circle((0, 0), radius, fill=False, color='gray', linewidth=1, linestyle='--', alpha=0.5)
        ax.add_artist(circle)

    ax.set(xlim=(-max_ws * 1.02, max_ws * 1.02),
           ylim=(-max_ws * 1.02, max_ws * 1.02),
           xticks=[],
           yticks=[],
           xticklabels=[],
           yticklabels=[],
           aspect='equal')

    if bottom_text:
        ax.text(0.50, -0.05, bottom_text, fontweight='bold', fontsize=8, va='center', ha='center',
                transform=ax.transAxes)

    ax.text(0.5, 1.05, Unit(val), fontweight='bold', fontsize=12, va='center', ha='center', transform=ax.transAxes)

    cbar = plt.colorbar(surf, ax=ax, label='Frequency', pad=0.01, fraction=0.04)
    cbar.ax.yaxis.label.set_fontsize(8)
    cbar.ax.tick_params(labelsize=8)

    plt.show()

    return fig, ax
