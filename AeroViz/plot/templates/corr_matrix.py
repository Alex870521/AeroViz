import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import colormaps
from matplotlib.pyplot import Figure, Axes
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from scipy.stats import pearsonr

from AeroViz.plot.utils import *

__all__ = ['corr_matrix', 'cross_corr_matrix']


@set_figure
def corr_matrix(data: pd.DataFrame,
                cmap: str = "RdBu",
                ax: Axes | None = None,
                items_order: list = None,  # 新增參數用於指定順序
                **kwargs
                ) -> tuple[Figure, Axes]:
    fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

    _corr = data.corr()
    breakpoint()
    corr = pd.melt(_corr.reset_index(), id_vars='index')
    corr.columns = ['x', 'y', 'value']

    p_values = _corr.apply(lambda col1: _corr.apply(lambda col2: pearsonr(col1, col2)[1]))
    p_values = p_values.mask(p_values > 0.05)
    p_values = pd.melt(p_values.reset_index(), id_vars='index').dropna()
    p_values.columns = ['x', 'y', 'value']

    # Mapping from column names to integer coordinates
    x_labels = [v for v in sorted(corr['x'].unique())]
    y_labels = [v for v in sorted(corr['y'].unique())]
    x_to_num = {p[1]: p[0] for p in enumerate(x_labels)}
    y_to_num = {p[1]: p[0] for p in enumerate(y_labels)}

    # Show column labels on the axes
    ax.set_xticks([x_to_num[v] for v in x_labels])
    ax.set_xticklabels(x_labels, rotation=90, horizontalalignment='center')
    ax.set_yticks([y_to_num[v] for v in y_labels])
    ax.set_yticklabels(y_labels)

    # ax.tick_params(axis='both', which='major', direction='out', top=True, left=True)

    ax.grid(False, 'major')
    ax.grid(True, 'minor')
    ax.set_xticks([t + 0.5 for t in ax.get_xticks()], minor=True)
    ax.set_yticks([t + 0.5 for t in ax.get_yticks()], minor=True)

    ax.set_xlim([-0.5, max([v for v in x_to_num.values()]) + 0.5])
    ax.set_ylim([-0.5, max([v for v in y_to_num.values()]) + 0.5])

    n_colors = 256  # Use 256 colors for the diverging color palette
    palette = sns.color_palette(cmap, n_colors=n_colors)  # Create the palette

    # Range of values that will be mapped to the palette, i.e. min and max possible correlation
    color_min, color_max = [-1, 1]

    def value_to_color(val):
        val_position = float((val - color_min)) / (color_max - color_min)
        ind = int(val_position * (n_colors - 1))  # target index in the color palette
        return palette[ind]

    point = ax.scatter(
        x=corr['x'].map(x_to_num),
        y=corr['y'].map(y_to_num),
        s=corr['value'].abs() * 70,
        c=corr['value'].apply(value_to_color),  # Vector of square color values, mapped to color palette
        marker='s',
        label='$R^{2}$'
    )

    axes_image = plt.cm.ScalarMappable(cmap=colormaps[cmap])

    cax = inset_axes(ax, width="5%",
                     height="100%",
                     loc='lower left',
                     bbox_to_anchor=(1.02, 0., 1, 1),
                     bbox_transform=ax.transAxes,
                     borderpad=0)

    cbar = plt.colorbar(mappable=axes_image, cax=cax, label=r'$R^{2}$')

    cbar.set_ticks([0, 0.25, 0.5, 0.75, 1])
    cbar.set_ticklabels(np.linspace(-1, 1, 5))

    point2 = ax.scatter(
        x=p_values['x'].map(x_to_num),
        y=p_values['y'].map(y_to_num),
        s=10,
        marker='*',
        color='k',
        label='p < 0.05'
    )

    ax.legend(handles=[point2], labels=['p < 0.05'], bbox_to_anchor=(0.02, 1, 0.05, 0.05))

    plt.show()

    return fig, ax


@set_figure(figsize=(6, 6))
def cross_corr_matrix(data1: pd.DataFrame,
                      data2: pd.DataFrame,
                      cmap: str = "RdBu",
                      ax: Axes | None = None,
                      items_order: list = None,  # 新增參數用於指定順序
                      **kwargs
                      ) -> tuple[Figure, Axes]:
    """
    Create a correlation matrix between two different DataFrames.

    Parameters:
    -----------
    data1 : pd.DataFrame
        First DataFrame
    data2 : pd.DataFrame
        Second DataFrame
    cmap : str, optional
        Color map for the correlation matrix
    ax : Axes, optional
        Matplotlib axes to plot on
    items_order : list, optional
        List specifying the order of items to display
    **kwargs : dict
        Additional keyword arguments
    """
    if ax is None:
        fig_kws = kwargs.get('fig_kws', {})
        default_figsize = fig_kws.get('figsize', (8, 8))
        fig = plt.figure(figsize=default_figsize)
        ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])
    else:
        fig = ax.get_figure()

    # 如果沒有指定順序，使用原始列名順序
    if items_order is None:
        x_labels = list(data1.columns)
        y_labels = list(data2.columns)
    else:
        # 使用指定順序，但只包含實際存在於數據中的列
        x_labels = [item for item in items_order if item in data1.columns]
        y_labels = [item for item in items_order if item in data2.columns]

    # Calculate cross-correlation between the two DataFrames
    correlations = []
    p_values_list = []

    for col1 in x_labels:  # 使用指定順序的列名
        for col2 in y_labels:
            try:
                mask = ~(np.isnan(data1[col1]) | np.isnan(data2[col2]))
                if mask.sum() > 2:
                    corr, p_val = pearsonr(data1[col1][mask], data2[col2][mask])
                else:
                    corr, p_val = np.nan, np.nan
            except Exception as e:
                print(f"Error calculating correlation for {col1} and {col2}: {str(e)}")
                corr, p_val = np.nan, np.nan

            correlations.append({
                'x': col1,
                'y': col2,
                'value': corr
            })
            if p_val is not None and p_val < 0.05:
                p_values_list.append({
                    'x': col1,
                    'y': col2,
                    'value': p_val
                })

    corr = pd.DataFrame(correlations)
    p_values = pd.DataFrame(p_values_list)

    # Create mapping using the specified order
    x_to_num = {label: i for i, label in enumerate(x_labels)}
    y_to_num = {label: i for i, label in enumerate(y_labels)}

    # 調整標籤顯示
    ax.set_xticks([x_to_num[v] for v in x_labels])
    ax.set_xticklabels(x_labels, rotation=45, ha='right')
    ax.set_yticks([y_to_num[v] for v in y_labels])
    ax.set_yticklabels(y_labels)

    ax.grid(False, 'major')
    ax.grid(True, 'minor')
    ax.set_xticks([t + 0.5 for t in ax.get_xticks()], minor=True)
    ax.set_yticks([t + 0.5 for t in ax.get_yticks()], minor=True)

    ax.set_xlim([-0.5, max([v for v in x_to_num.values()]) + 0.5])
    ax.set_ylim([-0.5, max([v for v in y_to_num.values()]) + 0.5])

    # Color mapping
    n_colors = 256
    palette = sns.color_palette(cmap, n_colors=n_colors)
    color_min, color_max = [-1, 1]

    def value_to_color(val):
        if pd.isna(val):
            return (1, 1, 1)
        val_position = float((val - color_min)) / (color_max - color_min)
        val_position = np.clip(val_position, 0, 1)
        ind = int(val_position * (n_colors - 1))
        return palette[ind]

    # Plot correlation squares
    x_coords = corr['x'].map(x_to_num)
    y_coords = corr['y'].map(y_to_num)
    sizes = corr['value'].abs().fillna(0) * 70
    colors = [value_to_color(val) for val in corr['value']]

    point = ax.scatter(
        x=x_coords,
        y=y_coords,
        s=sizes,
        c=colors,
        marker='s',
        label='$R^{2}$'
    )

    # 調整顏色軸的位置和大小
    cax = fig.add_axes([0.91, 0.1, 0.02, 0.8])
    axes_image = plt.cm.ScalarMappable(cmap=colormaps[cmap])
    cbar = plt.colorbar(mappable=axes_image, cax=cax, label=r'$R^{2}$')
    cbar.set_ticks([0, 0.25, 0.5, 0.75, 1])
    cbar.set_ticklabels(np.linspace(-1, 1, 5))

    # Plot significance markers
    if not p_values.empty:
        point2 = ax.scatter(
            x=p_values['x'].map(x_to_num),
            y=p_values['y'].map(y_to_num),
            s=10,
            marker='*',
            color='k',
            label='p < 0.05'
        )
        ax.legend(handles=[point2], labels=['p < 0.05'],
                  bbox_to_anchor=(0.005, 1.04), loc='upper left')

    # Add labels
    ax.set_xlabel('NZ', labelpad=10)
    ax.set_ylabel('FS', labelpad=10)

    plt.show()

    return fig, ax


if __name__ == '__main__':
    import pandas as pd
    from pandas import to_numeric

    df_NZ = pd.read_csv('/Users/chanchihyu/Desktop/NZ_minion_202402-202411.csv', parse_dates=True, index_col=0)
    df_FS = pd.read_csv('/Users/chanchihyu/Desktop/FS_minion_202402-202411.csv', parse_dates=True, index_col=0)

    items = ['Ext', 'Sca', 'Abs', 'PNC', 'PSC', 'PVC', 'SO2', 'NO', 'NOx', 'NO2', 'CO', 'O3', 'THC', 'NMHC', 'CH4',
             'PM10', 'PM2.5', 'WS', 'AT', 'RH',
             'OC', 'EC', 'Na+', 'NH4+', 'NO3-', 'SO42-', 'Al', 'Si', 'Ca', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Cu', 'Zn']
    df_NZ = df_NZ.apply(to_numeric, errors='coerce')

    corr_matrix(df_NZ[items], items_order=items)
