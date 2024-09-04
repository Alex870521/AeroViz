import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.pyplot import Figure, Axes
from pandas import DataFrame, date_range, concat
from sklearn.preprocessing import StandardScaler

from AeroViz.plot.utils import *

__all__ = ['metal_heatmaps', 'process_data_with_two_df']


def process_data(df, detected_limit=True, outlier_threshold=5, smoothing_window=6, fill_method='MDL'):
    # Fill missing values based on the specified method
    df = fill_missing_values(df.copy(), method=fill_method)

    # Normalize the data
    df = normalize_data(df)

    # Remove outliers
    df = remove_outliers(df, threshold=outlier_threshold)

    # Interpolate missing values
    df = df.interpolate(method='linear')

    # Smooth the data
    df = smooth_data(df, window=smoothing_window)

    return df


def process_data_with_two_df(df, df2, outlier_threshold=5, smoothing_window=6, fill_method='MDL'):
    # Shift the first DataFrame by 30 minutes
    df = df.shift(freq='30min')

    # Fill missing values for both DataFrames
    df = fill_missing_values(df.copy(), method=fill_method)
    df2 = fill_missing_values(df2.copy(), method=fill_method)

    # Normalize both DataFrames together
    df, df2 = normalize_and_split(df, df2)

    # Shift the first DataFrame back by 30 minutes
    df = df.shift(freq='-30min')

    # Remove outliers for both DataFrames
    df = remove_outliers(df, threshold=outlier_threshold)
    df2 = remove_outliers(df2, threshold=outlier_threshold)

    # Interpolate missing values
    df = df.interpolate(method='linear')
    df2 = df2.interpolate(method='linear')

    # Smooth the data
    df = smooth_data(df, window=smoothing_window)
    df2 = smooth_data(df2, window=smoothing_window)

    return df, df2


def fill_missing_values(df, method='MDL'):
    if method == 'interpolate':
        return df.interpolate(method='linear')
    else:
        return fill_with_mdl(df)


def fill_with_mdl(df):
    # Minimum detection limit (MDL) dictionary
    MDL = {
        'Al': 100, 'Si': 18, 'P': 5.2, 'S': 3.2,
        'Cl': 1.7, 'K': 1.2, 'Ca': 0.3, 'Ti': 1.6,
        'V': 0.12, 'Cr': 0.12, 'Mn': 0.14, 'Fe': 0.17,
        'Co': 0.14, 'Ni': 0.096, 'Cu': 0.079, 'Zn': 0.067,
        'Ga': 0.059, 'Ge': 0.056, 'As': 0.063, 'Se': 0.081,
        'Br': 0.1, 'Rb': 0.19, 'Sr': 0.22, 'Y': 0.28,
        'Zr': 0.33, 'Nb': 0.41, 'Mo': 0.48, 'Pd': 2.2,
        'Ag': 1.9, 'Cd': 2.5, 'In': 3.1, 'Sn': 4.1,
        'Sb': 5.2, 'Te': 0.6, 'I': 0.49, 'Cs': 0.37,
        'Ba': 0.39, 'La': 0.36, 'Ce': 0.3, 'Pt': 0.12,
        'Au': 0.1, 'Hg': 0.12, 'Tl': 0.12, 'Pb': 0.13,
        'Bi': 0.13
    }

    # Replace values below MDL with 5/6 * MDL
    for element, threshold in MDL.items():
        if element in df.columns:
            df.loc[:, element] = df[element].where(df[element] >= threshold, 5 / 6 * threshold)

    return df


def normalize_data(df):
    # Standardize the data (z-score normalization)
    return DataFrame(StandardScaler().fit_transform(df), index=df.index, columns=df.columns)


def remove_outliers(df, threshold=5):
    # Remove rows where any column value exceeds the threshold
    return df[(np.abs(df) < threshold)]


def smooth_data(df, window=6):
    # Apply rolling mean to smooth the data
    return df.rolling(window=window, min_periods=1).mean()


def normalize_and_split(df, df2):
    # Concatenate DataFrames for combined normalization
    combined_df = concat([df, df2])
    normalized_combined_df = normalize_data(combined_df)

    # Split the normalized DataFrame back into df and df2
    df = normalized_combined_df.loc[df.index]
    df2 = normalized_combined_df.loc[df2.index]

    return df, df2


@set_figure(figsize=(12, 3), fs=6)
def metal_heatmaps(df,
                   process=True,
                   major_freq='24h',
                   minor_freq='12h',
                   cmap='jet',
                   ax: Axes | None = None,
                   **kwargs
                   ) -> tuple[Figure, Axes]:
    if process:
        df = process_data(df)

    fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

    sns.heatmap(df.T, vmin=None, vmax=3, cmap=cmap, xticklabels=False, yticklabels=True,
                cbar_kws={'label': 'Z score', "pad": 0.02})
    ax.grid(color='gray', linestyle='-', linewidth=0.3)

    # Set x-tick positions and labels
    major_tick = date_range(start=df.index[0], end=df.index[-1], freq=major_freq)
    minor_tick = date_range(start=df.index[0], end=df.index[-1], freq=minor_freq)

    # Set the major and minor ticks
    ax.set_xticks(ticks=[df.index.get_loc(t) for t in major_tick])
    ax.set_xticks(ticks=[df.index.get_loc(t) for t in minor_tick], minor=True)
    ax.set_xticklabels(major_tick.strftime('%F'))
    ax.tick_params(axis='y', rotation=0)

    ax.set(xlabel='',
           ylabel='',
           title=kwargs.get('title', None)
           )

    plt.show()

    return fig, ax
