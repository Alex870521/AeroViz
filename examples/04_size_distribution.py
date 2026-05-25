"""
04_size_distribution.py - 粒徑分布處理範例

此範例展示如何使用 AeroViz 的 top-level functions 處理粒徑分布數據。

重要：``RawDataReader('SMPS'/'APS')`` 回傳的是「粒徑分布矩陣」本身
(dN/dlogDp，欄位為粒徑：SMPS 以 nm、APS 以 µm)，可直接餵給
``psd_stats`` / ``psd_distributions`` / ``merge_psd`` / ``SizeDist``。
總數量濃度、GMD、GSD 等「統計量」預設不在 reader 回傳值裡，而是：
  * 由 ``psd_stats(df)`` 即時衍生（``result['other']``），或
  * 直接讀每次讀檔自動產生的 ``{prefix}_stats.csv``。
每次讀檔也會輸出 N/S/V 分布檔（``_dNdlogDp`` / ``_dSdlogDp`` / ``_dVdlogDp``）。
若想把統計量「夾在分布後面」一起回傳，傳 ``append_stats=True``
（注意：這樣回傳的 df 含字串欄，不能再直接餵給 psd_stats / merge_psd）。

How to run / 執行方式:
  * Edit DATA_PATH then uncomment a call in __main__:
        python examples/04_size_distribution.py
  * Or run the synthetic demo (no data files needed):
        python examples/04_size_distribution.py --demo
"""

import sys
from datetime import datetime
from pathlib import Path

from AeroViz import RawDataReader, psd_stats, merge_psd
from AeroViz.dataProcess.SizeDistr import SizeDist

# =============================================================================
# 設定參數
# =============================================================================

DATA_PATH = Path('/path/to/your/data')
OUTPUT_PATH = Path('./output')
START = datetime(2024, 1, 1)
END = datetime(2024, 3, 31)

# =============================================================================
# 範例 1: 基本粒徑分布處理
# =============================================================================

def basic_psd_processing():
    """基本 PSD 統計處理"""

    # 讀取 SMPS 數據
    df_pnsd = RawDataReader(
        instrument='SMPS',
        path=DATA_PATH / 'SMPS',
        start=START,
        end=END,
        mean_freq='1h',
        size_range=(11.8, 593.5)
    )

    # 使用 top-level function
    result = psd_stats(df_pnsd)

    # Expected output: a dict with keys
    #   'number','number_norm','surface','surface_norm','volume','volume_norm','other'
    #   - the *distribution* frames have diameters as columns (same shape as input)
    #   - result['other'] holds the statistics: total_num_all, GMD_num_all,
    #     GSD_num_all, mode_num_all, plus per-mode columns
    print("=== 基本處理結果 ===")
    print(f"數量分布: {result['number'].shape}")
    print(f"表面積分布: {result['surface'].shape}")
    print(f"體積分布: {result['volume'].shape}")
    print(f"平均總數量濃度: {result['other']['total_num_all'].mean():.0f} #/cm³")

    return result


# =============================================================================
# 範例 2: 使用 SizeDist 類
# =============================================================================

def use_sizedist_class():
    """使用 SizeDist 類進行分布轉換"""

    # 讀取數據
    df_pnsd = RawDataReader(
        instrument='SMPS',
        path=DATA_PATH / 'SMPS',
        start=START,
        end=END,
        mean_freq='1h'
    )

    # 建立 SizeDist 物件
    psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')

    # 查看屬性
    print(f"粒徑範圍: {psd.dp[0]:.1f} ~ {psd.dp[-1]:.1f} nm")
    print(f"粒徑通道數: {len(psd.dp)}")

    # 分布轉換
    surface = psd.to_surface()  # 表面積分布
    volume = psd.to_volume()    # 體積分布

    # 計算統計屬性
    props = psd.properties()
    print(f"\n平均總數量濃度: {props['total_n'].mean():.0f} #/cm³")
    print(f"平均 GMD: {props['GMD_n'].mean():.1f} nm")
    print(f"平均 GSD: {props['GSD_n'].mean():.2f}")

    return psd, props


# =============================================================================
# 範例 3: 模態統計
# =============================================================================

def mode_statistics():
    """計算各粒徑模態的統計"""

    df_pnsd = RawDataReader(
        instrument='SMPS',
        path=DATA_PATH / 'SMPS',
        start=START,
        end=END,
        mean_freq='1h'
    )

    psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')
    stats = psd.mode_statistics()

    # Per-mode totals live in the 'statistics' summary frame as
    # total_num_{mode} columns (the 'number' frame is the dN/dlogDp matrix).
    summary = stats['statistics']

    print("=== 模態統計 ===")
    print("\n各模態平均數量濃度:")
    for mode in ['Nucleation', 'Aitken', 'Accumulation', 'Coarse']:
        col = f'total_num_{mode}'
        if col in summary.columns:
            print(f"  {mode}: {summary[col].mean():.0f} #/cm³")

    print("\n統計摘要欄位:")
    print(list(summary.columns))

    return stats


# =============================================================================
# 範例 4: SMPS-APS 合併
# =============================================================================

def merge_smps_aps():
    """合併 SMPS 和 APS 數據"""

    # 讀取 SMPS
    df_smps = RawDataReader(
        instrument='SMPS',
        path=DATA_PATH / 'SMPS',
        start=START,
        end=END,
        mean_freq='1h',
        size_range=(11.8, 593.5)
    )

    # 讀取 APS
    df_aps = RawDataReader(
        instrument='APS',
        path=DATA_PATH / 'APS',
        start=START,
        end=END,
        mean_freq='1h'
    )

    # 版本選擇 / choosing a version:
    #   * version=4 (推薦/recommended)：需要 PM2.5 reference (df_pm25)，多了
    #     PM2.5 fitness + SMPS-times 校正。有 PM2.5 就用 4。
    #   * version=3：不需要任何質量 reference，故本範例在沒有 PM2.5 時 fallback 用 3。
    #   * version=5 (實驗性/experimental)：質量錨定密度，需 df_pm1。
    # density_range=(0.6, 2.6) 為品質門檻（有效密度 g/cm³）；放寬用 (0.3, 2.6)
    # result = merge_psd(df_smps, df_aps, df_pm25=df_pm25, version=4)  # 有 PM2.5 時
    result = merge_psd(df_smps, df_aps, version=3, density_range=(0.6, 2.6))  # 無 PM2.5 fallback

    # 所有版本都保證有 'data'（建議用的合併結果）與 'density' 兩個 key
    merged = result['data']
    print(f"合併後粒徑範圍: {merged.columns[0]:.1f} ~ {merged.columns[-1]:.1f} nm")
    print(f"合併後通道數: {len(merged.columns)}")
    print(f"估算密度: {result['density'].mean().mean():.2f} g/cm³")

    return result


# =============================================================================
# 範例 5: 肺沉積計算
# =============================================================================

def lung_deposition():
    """計算肺沉積 (ICRP 66 模型)"""

    df_pnsd = RawDataReader(
        instrument='SMPS',
        path=DATA_PATH / 'SMPS',
        start=START,
        end=END,
        mean_freq='1h'
    )

    psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')

    # 計算不同活動強度的肺沉積
    activities = ['sleep', 'sitting', 'light', 'heavy']

    print("=== 肺沉積計算 ===")
    for activity in activities:
        result = psd.lung_deposition(activity=activity)

        # 平均沉積分率
        df_mean = result['DF'].mean()
        total_dose = result['total_dose'].mean()

        print(f"\n{activity.upper()}:")
        print(f"  頭氣道 (HA): {df_mean['HA']:.1%}")
        print(f"  氣管支氣管 (TB): {df_mean['TB']:.1%}")
        print(f"  肺泡 (AL): {df_mean['AL']:.1%}")
        print(f"  總沉積: {df_mean['Total']:.1%}")
        print(f"  沉積劑量: {total_dose:.0f} #/cm³")

    return result


# =============================================================================
# 範例 6: 乾燥 PSD 計算
# =============================================================================

def dry_psd():
    """計算乾燥粒徑分布 (吸濕校正)"""

    import pandas as pd

    df_pnsd = RawDataReader(
        instrument='SMPS',
        path=DATA_PATH / 'SMPS',
        start=START,
        end=END,
        mean_freq='1h'
    )

    # 假設有成長因子數據 (通常從化學成分計算)
    # 這裡使用假數據示範
    df_gRH = pd.DataFrame(
        {'gRH': 1.3},  # 假設均勻成長因子
        index=df_pnsd.index
    )

    psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')
    dry = psd.to_dry(df_gRH, uniform=True)

    print("=== 乾燥 PSD ===")
    print(f"原始粒徑範圍: {psd.dp[0]:.1f} ~ {psd.dp[-1]:.1f} nm")
    print(f"乾燥粒徑範圍: {dry.columns[0]:.1f} ~ {dry.columns[-1]:.1f} nm")

    return dry


# =============================================================================
# 合成資料 Demo / Synthetic demo (no data files required)
# =============================================================================

def demo():
    """Run the size-distribution functions on a synthetic SMPS dN/dlogDp matrix.

    用合成的 SMPS dN/dlogDp 矩陣示範 psd_stats / SizeDist，不需要任何資料檔。
    (這裡不示範 merge_psd，因為它較重且需要 SMPS+APS 與多進程。)
    """
    import numpy as np
    import pandas as pd

    print("=== AeroViz 粒徑分布 Demo (synthetic SMPS data) ===\n")

    # Build a synthetic SMPS dN/dlogDp matrix: columns are diameters (nm),
    # index is time. A single lognormal mode centered ~80 nm.
    rng = np.random.default_rng(0)
    diameters = np.logspace(np.log10(11.8), np.log10(593.5), 60)
    idx = pd.date_range('2024-01-01', periods=48, freq='h', name='time')
    lognorm = np.exp(-0.5 * ((np.log(diameters) - np.log(80)) / np.log(1.8)) ** 2)
    base = np.outer(rng.uniform(8000, 12000, len(idx)), lognorm)
    df_pnsd = pd.DataFrame(base * rng.uniform(0.8, 1.2, base.shape),
                           index=idx, columns=diameters)

    # 1) Top-level psd_stats (one-call statistics + distributions)
    stats = psd_stats(df_pnsd)
    print("psd_stats keys:", list(stats.keys()))
    print(f"  mean total N : {stats['other']['total_num_all'].mean():.0f} #/cm³")
    print(f"  mean GMD     : {stats['other']['GMD_num_all'].mean():.1f} nm")

    # 2) SizeDist class (properties is time-indexed: one row per timestamp)
    psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')
    props = psd.properties()      # columns: total_n, GMD_n, GSD_n, mode_n, ...
    print(f"\nSizeDist.properties() shape: {props.shape} (time-indexed)")
    print(f"  mean GSD     : {props['GSD_n'].mean():.2f}")

    # 3) Lung deposition (ICRP 66)
    lung = psd.lung_deposition(activity='light')
    print(f"\nLung deposition (light activity):")
    print(f"  mean total deposition fraction: {lung['DF']['Total'].mean():.1%}")

    print("\n(這是合成資料；要處理真實資料請編輯 DATA_PATH 並用上面的函式。)")
    return df_pnsd


# =============================================================================
# 主程式 / Main
# =============================================================================

if __name__ == '__main__':
    if '--demo' in sys.argv:
        demo()
        sys.exit(0)

    # 取消註解以執行對應範例 / Uncomment a call to run it (edit DATA_PATH first)

    # result = basic_psd_processing()
    # psd, props = use_sizedist_class()
    # stats = mode_statistics()
    # merged = merge_smps_aps()
    # lung = lung_deposition()
    # dry = dry_psd()

    print("請修改 DATA_PATH 後取消註解執行對應範例，"
          "或執行 `python examples/04_size_distribution.py --demo` 跑合成資料。")
