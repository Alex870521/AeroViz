"""
04_size_distribution.py - 粒徑分布處理範例

此範例展示如何使用 AeroViz 的 top-level functions 處理粒徑分布數據。
"""

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

    print("=== 基本處理結果 ===")
    print(f"數量分布: {result['number'].shape}")
    print(f"表面積分布: {result['surface'].shape}")
    print(f"體積分布: {result['volume'].shape}")

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

    print("=== 模態統計 ===")
    print("\n各模態數量分布:")
    for mode in ['Nucleation', 'Aitken', 'Accumulation', 'Coarse']:
        if mode in stats['number']:
            mean_conc = stats['number'][mode].mean().mean()
            print(f"  {mode}: {mean_conc:.0f} #/cm³")

    print("\n統計摘要:")
    print(stats['statistics'])

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

    # 合併 (v4 版本，含密度校正) — 需要 PM2.5 reference
    # 若沒有 PM2.5 可用 version=3 跳過 fitness 步驟
    # result = merge_psd(df_smps, df_aps, df_pm25=df_pm25, version=4)
    result = merge_psd(df_smps, df_aps, version=3)

    merged = result['data_dn']
    print(f"合併後粒徑範圍: {merged.columns[0]:.1f} ~ {merged.columns[-1]:.1f} nm")
    print(f"合併後通道數: {len(merged.columns)}")

    if 'density' in result:
        print(f"估算密度: {result['density'].mean():.2f} g/cm³")

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
# 主程式
# =============================================================================

if __name__ == '__main__':
    # 取消註解以執行對應範例

    # result = basic_psd_processing()
    # psd, props = use_sizedist_class()
    # stats = mode_statistics()
    # merged = merge_smps_aps()
    # lung = lung_deposition()
    # dry = dry_psd()

    print("請修改 DATA_PATH 後取消註解執行對應範例")
