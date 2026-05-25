"""
05_chemical_analysis.py - 化學成分分析範例

此範例展示如何使用 AeroViz 的 top-level functions 進行化學成分分析。
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from AeroViz import (
    RawDataReader,
    reconstruct_mass,
    volume_ri,
    kappa,
    growth_factor,
    partition_ratios,
    split_oc_ec,
)

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

    # 假設有 PM2.5 reference 資料 (df_pm25)
    df_pm25 = df_chem.get('PM25') if 'PM25' in df_chem.columns else None
    result = reconstruct_mass(df_chem, df_ref=df_pm25)

    # 重建質量
    # df_mass 欄位：AS, AN, OM, Soil, SS, EC, total（'total' = 重建總質量；無 'PM25_rc'）
    df_mass = result['mass']
    print("\n=== 質量重建結果 ===")
    print(f"欄位: {df_mass.columns.tolist()}")
    print("\n平均質量濃度 (μg/m³):")
    for col in ['AS', 'AN', 'OM', 'EC', 'Soil', 'SS', 'total']:
        if col in df_mass.columns:
            print(f"  {col}: {df_mass[col].mean():.2f}")

    # 銨根狀態：result['NH4_status'] 是含 'ratio'/'status' 欄的 DataFrame
    nh4_status = result['NH4_status']
    print(f"\n銨根狀態分布:")
    print(nh4_status['status'].value_counts())

    # 閉合度（用重建總質量 'total' 對比量測 PM2.5）
    if 'PM25' in df_chem.columns:
        closure = df_mass['total'] / df_chem['PM25'] * 100
        print(f"\n閉合度: {closure.mean():.1f} ± {closure.std():.1f}%")

    return result


# =============================================================================
# 範例 3: 體積與折射率計算
# =============================================================================

def volume_and_ri():
    """計算體積分率和折射率"""

    df_chem = read_chemical_data()

    # volume_ri 需要 df_volume (來自 reconstruct_mass) + 可選 df_alwc
    mass_result = reconstruct_mass(df_chem)
    df_volume = mass_result['volume']

    result = volume_ri(df_volume)

    print("\n=== 折射率 (體積平均混合) ===")
    print(f"乾氣膠 n: {result['n_dry'].mean():.3f}")
    print(f"乾氣膠 k: {result['k_dry'].mean():.4f}")

    return result


# =============================================================================
# 範例 4: 吸濕性 (κ) 計算
# =============================================================================

def kappa_calculation():
    """計算 κ 值和成長因子"""

    df_chem = read_chemical_data()

    # kappa 需要 gRH + AT + RH 三個欄位
    # 通常流程：reconstruct_mass → volume_ri (得 gRH) → 配上氣象資料 → kappa
    mass_result = reconstruct_mass(df_chem)
    df_volume = mass_result['volume']

    # 假設有 ALWC 資料（從 ISORROPIA 或其他來源）
    df_alwc = pd.DataFrame({'ALWC': 5.0}, index=df_chem.index)
    df_gRH = growth_factor(df_volume, df_alwc)

    # 組合 gRH + 氣象資料供 kappa 使用
    df_for_kappa = pd.DataFrame({
        'gRH': df_gRH['gRH'],
        'AT': 25.0,   # 假設 AT = 25°C
        'RH': 70.0,   # 假設 RH = 70%
    }, index=df_chem.index)

    result = kappa(df_for_kappa, diameter=0.5)

    print("\n=== 吸濕性參數 ===")
    print(f"κ 值: {result['kappa_chem'].mean():.3f}")
    print(f"成長因子 gRH: {df_gRH['gRH'].mean():.2f}")

    return result


# =============================================================================
# 範例 5: 氣粒分配比
# =============================================================================

def gas_particle_partitioning():
    """計算氣粒分配比 (SOR/NOR/NTR 等)"""

    df_chem = read_chemical_data()

    # 需要氣體數據 (SO2, NO2, HNO3, NH3) 並含 temp 欄位
    # df_gas = read_gas_data()
    # df_combined = pd.concat([df_chem, df_gas], axis=1)
    # result = partition_ratios(df_combined)
    # print("\n=== 氣粒分配比 ===")
    # print(f"SOR: {result['SOR'].mean():.2f}")
    # print(f"NOR: {result['NOR'].mean():.2f}")

    print("需要氣體數據 (SO2, NO2, HNO3, NH3) + 溫度才能計算氣粒分配比")


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

    result = split_oc_ec(df_ocec)

    print("\n=== OC/EC 分析 ===")
    df_basic = result.get('basic')
    if df_basic is not None and 'OC/EC_thm' in df_basic.columns:
        print(f"OC/EC 比值: {df_basic['OC/EC_thm'].mean():.2f}")
    if df_basic is not None and 'SOC_thm' in df_basic.columns:
        print(f"SOC 估算: {df_basic['SOC_thm'].mean():.2f} μgC/m³")

    return result


# =============================================================================
# 範例 7: 完整化學分析流程
# =============================================================================

def full_chemical_analysis():
    """完整的化學成分分析流程"""

    # 1. 讀取數據
    df_chem = read_chemical_data()

    # 2. 質量重建
    mass_result = reconstruct_mass(df_chem)
    df_mass = mass_result['mass']

    # 3. 折射率 (從質量重建拿 df_volume)
    df_RI = volume_ri(mass_result['volume'])

    # 5. 成分貢獻比例（以重建總質量 'total' 為分母）
    components = ['AS', 'AN', 'OM', 'EC', 'Soil', 'SS']
    available = [c for c in components if c in df_mass.columns]

    if available and 'total' in df_mass.columns:
        contribution = df_mass[available].div(df_mass['total'], axis=0) * 100

        print("\n=== 成分貢獻 (%) ===")
        for comp in available:
            print(f"  {comp}: {contribution[comp].mean():.1f}%")

    # 6. 輸出摘要
    print("\n=== 分析摘要 ===")
    if 'PM25' in df_chem.columns:
        print(f"PM2.5: {df_chem['PM25'].mean():.1f} ± {df_chem['PM25'].std():.1f} μg/m³")
    print(f"RI: {df_RI['n_dry'].mean():.3f} + {df_RI['k_dry'].mean():.4f}i")

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
