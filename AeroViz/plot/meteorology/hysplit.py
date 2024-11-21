from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import pandas as pd

from AeroViz.plot.utils import set_figure

# Hybrid Single-Particle Lagrangian Integrated Trajectory (HYSPLIT) model


__all__ = ['hysplit']

# 設置默認文件路徑
DEFAULT_FILE = Path(__file__).parent.parent.parent / 'data' / 'hysplit_example_data.txt'


def read_hysplit_data(file: Path):
    data = pd.read_csv(file, skiprows=8, sep=r'\s+', names=range(0, 12), engine='python')
    data = data.reset_index(drop=False)
    data.columns = ['category', 'name', 'year', 'month', 'day', 'hour', 'minute', 'count', 'backward', 'lat', 'lon',
                    'height', 'pressure']

    time_cols = ['year', 'month', 'day', 'hour', 'minute']

    data['time'] = pd.to_datetime(data[time_cols].astype(str).agg(''.join, axis=1), format='%y%m%d%H%M')

    data = data.drop(columns=time_cols)

    data = data[['time'] + [col for col in data.columns if col != 'time']]

    return data


@set_figure
def hysplit(file: Path = DEFAULT_FILE):
    data = read_hysplit_data(file)

    # 創建地圖
    fig, ax = plt.subplots(figsize=(4, 5), subplot_kw={'projection': ccrs.PlateCarree()})

    ax.set_global()
    # ax.stock_img()

    # 設置地圖範圍
    ax.set_extent([116, 126, 17, 30], crs=ccrs.PlateCarree())

    # 添加自然地理特徵
    ax.add_feature(cfeature.LAND.with_scale('10m'))
    ax.add_feature(cfeature.OCEAN.with_scale('10m'))
    ax.add_feature(cfeature.COASTLINE.with_scale('10m'))
    ax.add_feature(cfeature.BORDERS.with_scale('10m'), linestyle=':')

    # 添加經緯度網格
    ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False)

    # 定義四種顏色
    colors = ['red', 'blue', 'green', 'purple']

    # 繪製四條軌跡線
    group = data.groupby('category')
    for i, (name, _data) in enumerate(group):
        trajectory = _data
        ax.plot(trajectory['lon'], trajectory['lat'], color=colors[i],
                linewidth=2, transform=ccrs.Geodetic(),
                label=f'Trajectory {name}')

        # 添加起點和終點標記
        # ax.plot(trajectory['lon'].iloc[-1], trajectory['lat'].iloc[-1], 'o',
        #         color=colors[i], markersize=4, transform=ccrs.Geodetic())
        # ax.plot(trajectory['lon'].iloc[0], trajectory['lat'].iloc[0], 's',
        #         color=colors[i], markersize=4, transform=ccrs.Geodetic())

    ax.legend(loc='upper right')
    # 添加色標
    # cbar = plt.colorbar(scatter, ax=ax, shrink=0.6, pad=0.12)
    # cbar.set_label('Height (m)')

    # 添加標題
    plt.title("HYSPLIT model", pad=12)

    plt.tight_layout()

    # 保存地圖
    plt.savefig('backward_hysplit.png', dpi=300, bbox_inches='tight')

    # 顯示地圖（可選）
    plt.show()


if __name__ == "__main__":
    hysplit()  # 請替換為您的實際檔案路徑
