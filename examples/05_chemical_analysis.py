"""
05_chemical_analysis.py - 化學成分分析範例

此範例展示如何使用 DataProcess 進行化學成分分析。
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from AeroViz import RawDataReader
from AeroViz.dataProcess import DataProcess

# =============================================================================
# 設定參數
# =============================================================================

DATA_PATH = Path('/path/to/your/data')
OUTPUT_PATH = Path('./output')
START = datetime(2024, 1, 1)
END = datetime(2024, 3, 31)

# =============================================================================
# 範例 1: 讀取化學成分數據
# =============================================================================

def read_chemical_data():
    """讀取離子和碳成分數據"""

    # 讀取離子數據 (IGAC)
    df_igac = RawDataReader(
        instrument='IGAC',
        path=DATA_PATH / 'IGAC',
        start=START,
        end=END,
        mean_freq='1h'
    )

    # 讀取碳成分數據 (OCEC)
    df_ocec = RawDataReader(
        instrument='OCEC',
        path=DATA_PATH / 'OCEC',
        start=START,
        end=END,
        mean_freq='1h'
    )

    # 合併
    df_chem = pd.concat([df_igac, df_ocec], axis=1)

    print("=== 化學成分數據 ===")
    print(f"欄位: {df_chem.columns.tolist()}")
    print(df_chem.describe())

    return df_chem


# =============================================================================
# 範例 2: 質量重建
# =============================================================================

def mass_reconstruction():
    """質量重建計算"""

    df_chem = read_chemical_data()

    dp = DataProcess('Chemistry', OUTPUT_PATH)
    result = dp.reconstruction_basic(df_chem)

    # 重建質量
    df_mass = result['mass']
    print("\n=== 質量重建結果 ===")
    print(f"欄位: {df_mass.columns.tolist()}")
    print("\n平均質量濃度 (μg/m³):")
    for col in ['AS', 'AN', 'OM', 'EC', 'Soil', 'SS', 'PM25_rc']:
        if col in df_mass.columns:
            print(f"  {col}: {df_mass[col].mean():.2f}")

    # 銨根狀態
    nh4_status = result['NH4_status']
    print(f"\n銨根狀態分布:")
    print(nh4_status.value_counts())

    # 閉合度
    if 'PM25' in df_chem.columns and 'PM25_rc' in df_mass.columns:
        closure = df_mass['PM25_rc'] / df_chem['PM25'] * 100
        print(f"\n閉合度: {closure.mean():.1f} ± {closure.std():.1f}%")

    return result


# =============================================================================
# 範例 3: 體積與折射率計算
# =============================================================================

def volume_and_ri():
    """計算體積分率和折射率"""

    df_chem = read_chemical_data()

    dp = DataProcess('Chemistry', OUTPUT_PATH)
    result = dp.volume_RI(df_chem)

    # 體積分率
    df_volume = result['volume']
    print("\n=== 體積分率 ===")
    print(df_volume.mean())

    # 折射率
    df_RI = result['RI']
    print(f"\n=== 折射率 ===")
    print(f"實部 (n): {df_RI['n'].mean():.3f} ± {df_RI['n'].std():.3f}")
    print(f"虛部 (k): {df_RI['k'].mean():.4f} ± {df_RI['k'].std():.4f}")

    return result


# =============================================================================
# 範例 4: 吸濕性 (κ) 計算
# =============================================================================

def kappa_calculation():
    """計算 κ 值和成長因子"""

    df_chem = read_chemical_data()

    # 需要 RH 數據 (這裡假設從氣象數據讀取)
    # 實際使用時需要提供真實的 RH 數據
    df_RH = pd.DataFrame(
        {'RH': 70},  # 假設 RH = 70%
        index=df_chem.index
    )

    dp = DataProcess('Chemistry', OUTPUT_PATH)
    result = dp.kappa(df_chem, df_RH)

    print("\n=== 吸濕性參數 ===")
    print(f"κ 值: {result['kappa'].mean():.3f} ± {result['kappa'].std():.3f}")
    print(f"成長因子 gRH: {result['gRH'].mean():.2f} ± {result['gRH'].std():.2f}")

    return result


# =============================================================================
# 範例 5: 氣粒分配比
# =============================================================================

def partition_ratios():
    """計算氣粒分配比"""

    df_chem = read_chemical_data()

    # 需要氣體數據 (SO2, NO2, HNO3, NH3)
    # 這裡假設從其他來源讀取
    # df_gas = read_gas_data()
    # df_combined = pd.concat([df_chem, df_gas], axis=1)

    dp = DataProcess('Chemistry', OUTPUT_PATH)

    # 如果有完整數據
    # result = dp.partition_ratios(df_combined)
    # print("\n=== 氣粒分配比 ===")
    # print(f"SOR: {result['SOR'].mean():.2f}")
    # print(f"NOR: {result['NOR'].mean():.2f}")

    print("需要氣體數據 (SO2, NO2, HNO3, NH3) 才能計算氣粒分配比")


# =============================================================================
# 範例 6: OC/EC 比值分析
# =============================================================================

def ocec_analysis():
    """OC/EC 比值分析"""

    df_ocec = RawDataReader(
        instrument='OCEC',
        path=DATA_PATH / 'OCEC',
        start=START,
        end=END,
        mean_freq='1h'
    )

    dp = DataProcess('Chemistry', OUTPUT_PATH)
    result = dp.ocec_ratio(df_ocec)

    print("\n=== OC/EC 分析 ===")
    if 'ratio' in result:
        print(f"OC/EC 比值: {result['ratio'].mean():.2f} ± {result['ratio'].std():.2f}")
    if 'SOC' in result:
        print(f"SOC 估算: {result['SOC'].mean():.2f} μg/m³")

    return result


# =============================================================================
# 範例 7: 完整化學分析流程
# =============================================================================

def full_chemical_analysis():
    """完整的化學成分分析流程"""

    # 1. 讀取數據
    df_chem = read_chemical_data()

    # 2. 初始化處理器
    dp = DataProcess('Chemistry', OUTPUT_PATH)

    # 3. 質量重建
    mass_result = dp.reconstruction_basic(df_chem)
    df_mass = mass_result['mass']

    # 4. 體積和折射率
    vol_ri = dp.volume_RI(df_chem)
    df_RI = vol_ri['RI']

    # 5. 成分貢獻比例
    components = ['AS', 'AN', 'OM', 'EC', 'Soil', 'SS']
    available = [c for c in components if c in df_mass.columns]

    if available and 'PM25_rc' in df_mass.columns:
        contribution = df_mass[available].div(df_mass['PM25_rc'], axis=0) * 100

        print("\n=== 成分貢獻 (%) ===")
        for comp in available:
            print(f"  {comp}: {contribution[comp].mean():.1f}%")

    # 6. 輸出摘要
    print("\n=== 分析摘要 ===")
    if 'PM25' in df_chem.columns:
        print(f"PM2.5: {df_chem['PM25'].mean():.1f} ± {df_chem['PM25'].std():.1f} μg/m³")
    print(f"RI: {df_RI['n'].mean():.3f} + {df_RI['k'].mean():.4f}i")

    return {
        'mass': df_mass,
        'RI': df_RI,
        'NH4_status': mass_result['NH4_status']
    }


# =============================================================================
# 主程式
# =============================================================================

if __name__ == '__main__':
    # 取消註解以執行對應範例

    # df_chem = read_chemical_data()
    # mass = mass_reconstruction()
    # vol_ri = volume_and_ri()
    # kappa = kappa_calculation()
    # partition_ratios()
    # ocec = ocec_analysis()
    # result = full_chemical_analysis()

    print("請修改 DATA_PATH 後取消註解執行對應範例")
