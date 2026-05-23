"""
07_plotting.py - 繪圖範例

此範例展示 AeroViz 的視覺化功能。
"""

from pathlib import Path

import numpy as np
import pandas as pd

from AeroViz.plot import scatter, regression, box, bar, violin, pie, timeseries_interactive

# =============================================================================
# 設定
# =============================================================================

OUTPUT_PATH = Path('./output/plots')
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

# =============================================================================
# 範例 1: 基本散點圖
# =============================================================================

def basic_scatter():
    """基本散點圖"""

    # 建立測試數據
    np.random.seed(42)
    df = pd.DataFrame({
        'x': np.random.rand(50),
        'y': np.random.rand(50)
    })

    fig, ax = scatter(df, x='x', y='y', title='Basic Scatter Plot')
    fig.savefig(OUTPUT_PATH / 'basic_scatter.png', dpi=150, bbox_inches='tight')
    print(f"已儲存: {OUTPUT_PATH / 'basic_scatter.png'}")

    return fig, ax


# =============================================================================
# 範例 2: 帶色彩和大小編碼的散點圖
# =============================================================================

def scatter_with_encoding():
    """色彩和大小編碼的散點圖"""

    np.random.seed(42)
    df = pd.DataFrame({
        'x': np.random.rand(50),
        'y': np.random.rand(50),
        'color': np.random.rand(50),
        'size': np.random.randint(10, 100, 50)
    })

    fig, ax = scatter(
        df, x='x', y='y',
        c='color',
        s='size',
        fig_kws={'figsize': (6, 5)},
        title='Scatter with Color & Size'
    )
    fig.savefig(OUTPUT_PATH / 'scatter_encoding.png', dpi=150, bbox_inches='tight')
    print(f"已儲存: {OUTPUT_PATH / 'scatter_encoding.png'}")

    return fig, ax


# =============================================================================
# 範例 3: 帶迴歸線的散點圖
# =============================================================================

def scatter_with_regression():
    """帶迴歸線和對角線的散點圖"""

    np.random.seed(42)
    x = np.arange(0, 10, 0.2)
    y = x + np.random.normal(0, 1, len(x))

    df = pd.DataFrame({'x': x, 'y': y})

    fig, ax = scatter(
        df, x='x', y='y',
        regression=True,
        diagonal=True,
        title='Scatter with Regression'
    )
    fig.savefig(OUTPUT_PATH / 'scatter_regression.png', dpi=150, bbox_inches='tight')
    print(f"已儲存: {OUTPUT_PATH / 'scatter_regression.png'}")

    return fig, ax


# =============================================================================
# 範例 4: 箱型圖
# =============================================================================

def box_plot_example():
    """箱型圖範例"""

    np.random.seed(42)

    # 模擬季節數據
    seasons = ['Spring', 'Summer', 'Autumn', 'Winter']
    data = []
    for i, season in enumerate(seasons):
        n = 50
        values = np.random.normal(20 + i * 5, 5, n)
        data.extend([(season, v) for v in values])

    df = pd.DataFrame(data, columns=['Season', 'PM25'])

    fig, ax = box(df, x='Season', y='PM25', title='PM2.5 by Season')
    fig.savefig(OUTPUT_PATH / 'box_plot.png', dpi=150, bbox_inches='tight')
    print(f"已儲存: {OUTPUT_PATH / 'box_plot.png'}")

    return fig, ax


# =============================================================================
# 範例 5: 柱狀圖
# =============================================================================

def bar_plot_example():
    """柱狀圖範例 - 成分貢獻"""

    # 模擬化學成分數據
    components = ['AS', 'AN', 'OM', 'EC', 'Soil', 'SS']
    values = [8.5, 6.2, 12.3, 3.1, 2.8, 1.9]

    df = pd.Series(values, index=components)

    fig, ax = bar(df, ylabel='Mass (μg/m³)', title='PM2.5 Chemical Composition')
    fig.savefig(OUTPUT_PATH / 'bar_plot.png', dpi=150, bbox_inches='tight')
    print(f"已儲存: {OUTPUT_PATH / 'bar_plot.png'}")

    return fig, ax


# =============================================================================
# 範例 6: 小提琴圖
# =============================================================================

def violin_plot_example():
    """小提琴圖範例"""

    np.random.seed(42)

    categories = ['Urban', 'Suburban', 'Rural']
    data = []
    for i, cat in enumerate(categories):
        n = 100
        values = np.random.lognormal(3 - i * 0.5, 0.5, n)
        data.extend([(cat, v) for v in values])

    df = pd.DataFrame(data, columns=['Site', 'BC'])

    fig, ax = violin(df, x='Site', y='BC', title='BC Distribution by Site Type')
    fig.savefig(OUTPUT_PATH / 'violin_plot.png', dpi=150, bbox_inches='tight')
    print(f"已儲存: {OUTPUT_PATH / 'violin_plot.png'}")

    return fig, ax


# =============================================================================
# 範例 7: 圓餅圖
# =============================================================================

def pie_chart_example():
    """圓餅圖範例 - 成分比例"""

    labels = ['AS', 'AN', 'OM', 'EC', 'Soil', 'SS']
    values = [25, 18, 35, 9, 8, 5]

    fig, ax = pie(values, labels=labels, title='PM2.5 Composition (%)')
    fig.savefig(OUTPUT_PATH / 'pie_chart.png', dpi=150, bbox_inches='tight')
    print(f"已儲存: {OUTPUT_PATH / 'pie_chart.png'}")

    return fig, ax


# =============================================================================
# 範例 8: 多面板圖
# =============================================================================

def multi_panel_example():
    """多面板組合圖"""

    import matplotlib.pyplot as plt

    np.random.seed(42)

    # 建立測試數據
    n = 100
    df = pd.DataFrame({
        'BC': np.random.lognormal(2, 0.5, n),
        'PM25': np.random.lognormal(3, 0.4, n),
        'Season': np.random.choice(['Spring', 'Summer', 'Autumn', 'Winter'], n)
    })

    fig, axes = plt.subplots(2, 2, figsize=(10, 8))

    # 散點圖
    scatter(df, x='BC', y='PM25', ax=axes[0, 0], title='BC vs PM2.5')

    # 帶迴歸線
    scatter(df, x='BC', y='PM25', regression=True, ax=axes[0, 1], title='With Regression')

    # 箱型圖
    box(df, x='Season', y='BC', ax=axes[1, 0], title='BC by Season')

    # 箱型圖
    box(df, x='Season', y='PM25', ax=axes[1, 1], title='PM2.5 by Season')

    plt.tight_layout()
    fig.savefig(OUTPUT_PATH / 'multi_panel.png', dpi=150, bbox_inches='tight')
    print(f"已儲存: {OUTPUT_PATH / 'multi_panel.png'}")

    return fig


# =============================================================================
# 範例 9: 使用真實數據繪圖
# =============================================================================

def interactive_timeseries_example():
    """互動式時序圖(Plotly):一欄一條 trace,點 legend 切換欄位,可存成 HTML。"""
    idx = pd.date_range('2024-01-01', periods=24 * 14, freq='h', name='time')
    df = pd.DataFrame({
        'eBC': np.random.gamma(2, 500, len(idx)),
        'BC1': np.random.gamma(2, 600, len(idx)),
        'BC6': np.random.gamma(2, 450, len(idx)),
        'AAE': np.random.normal(1.2, 0.2, len(idx)),
    }, index=idx)

    out = OUTPUT_PATH / 'timeseries_interactive.html'
    # save= 匯出獨立 HTML;show=False 避免在「全部執行」時開瀏覽器
    timeseries_interactive(df, save=str(out), show=False)
    print(f"已儲存: {out}(用瀏覽器開啟,點 legend 切換欄位)")


def plot_real_data():
    """使用 RawDataReader 讀取真實數據並繪圖"""

    from datetime import datetime
    from AeroViz import RawDataReader

    DATA_PATH = Path('/path/to/your/data')
    START = datetime(2024, 1, 1)
    END = datetime(2024, 3, 31)

    # 讀取數據(start/end/mean_freq 皆可省略;省略 mean_freq 回傳原解析度)
    # df_ae33 = RawDataReader(
    #     instrument='AE33',
    #     path=DATA_PATH / 'AE33',
    #     start=START,
    #     end=END,
    #     mean_freq='1h'
    # )

    # 互動式時序圖(Plotly):點 legend 切換欄位
    # timeseries_interactive(df_ae33, columns=['eBC', 'BC1', 'BC6', 'AAE'])
    # timeseries_interactive(df_ae33, save='ae33.html', show=False)  # 存成 HTML

    # 或用 matplotlib 繪製靜態時間序列
    # import matplotlib.pyplot as plt
    # fig, ax = plt.subplots(figsize=(12, 4))
    # ax.plot(df_ae33.index, df_ae33['BC_880'], 'b-', alpha=0.7)
    # ax.set_xlabel('Time')
    # ax.set_ylabel('BC (μg/m³)')
    # ax.set_title('BC Time Series')
    # fig.savefig(OUTPUT_PATH / 'bc_timeseries.png', dpi=150, bbox_inches='tight')

    print("請修改 DATA_PATH 後取消註解執行")


# =============================================================================
# 主程式
# =============================================================================

if __name__ == '__main__':
    print("=== AeroViz 繪圖範例 ===\n")

    # 執行所有範例
    basic_scatter()
    scatter_with_encoding()
    scatter_with_regression()
    box_plot_example()
    bar_plot_example()
    violin_plot_example()
    pie_chart_example()
    multi_panel_example()
    interactive_timeseries_example()

    print(f"\n所有圖表已儲存至: {OUTPUT_PATH}")
