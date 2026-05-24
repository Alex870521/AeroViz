"""
06_optical_properties.py - 光學特性計算範例

此範例展示如何使用 AeroViz 的 top-level functions 計算光學特性。
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from AeroViz import (
    RawDataReader,
    reconstruct_mass,
    volume_ri,
    improve,
    mie,
    retrieve_ri,
)

# =============================================================================
# 設定參數
# =============================================================================

DATA_PATH = Path('/path/to/your/data')
OUTPUT_PATH = Path('./output')
START = datetime(2024, 1, 1)
END = datetime(2024, 3, 31)

# =============================================================================
# 範例 1: 讀取光學數據
# =============================================================================

def read_optical_data():
    """讀取散射和吸收數據"""

    # 讀取散射係數 (NEPH)
    df_neph = RawDataReader(
        instrument='NEPH',
        path=DATA_PATH / 'NEPH',
        start=START,
        end=END,
        mean_freq='1h'
    )

    # 讀取吸收係數 (AE33)
    df_ae33 = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'AE33',
        start=START,
        end=END,
        mean_freq='1h'
    )

    print("=== 光學數據 ===")
    print(f"NEPH 欄位: {df_neph.columns.tolist()}")
    print(f"AE33 欄位: {df_ae33.columns.tolist()}")

    return df_neph, df_ae33


# =============================================================================
# 範例 2: IMPROVE 消光計算
# =============================================================================

def improve_extinction():
    """使用 IMPROVE 方程計算消光"""

    # 讀取化學成分數據
    df_igac = RawDataReader(
        instrument='IGAC',
        path=DATA_PATH / 'IGAC',
        start=START,
        end=END,
        mean_freq='1h'
    )

    df_ocec = RawDataReader(
        instrument='OCEC',
        path=DATA_PATH / 'OCEC',
        start=START,
        end=END,
        mean_freq='1h'
    )

    df_chem = pd.concat([df_igac, df_ocec], axis=1)

    # 質量重建
    mass_result = reconstruct_mass(df_chem)
    df_mass = mass_result['mass']

    # RH 數據 (假設)
    df_RH = pd.DataFrame({'RH': 70}, index=df_mass.index)

    # IMPROVE 計算
    result = improve(
        df_mass=df_mass,
        df_RH=df_RH,
        method='revised'  # 'revised' / 'modified' / 'localized'
    )

    print("\n=== IMPROVE 消光 ===")
    print("乾燥消光成分 (Mm⁻¹):")
    for col in ['AS_ext', 'AN_ext', 'OM_ext', 'EC_ext', 'Soil_ext', 'SS_ext']:
        if col in result['dry'].columns:
            print(f"  {col}: {result['dry'][col].mean():.1f}")

    print(f"\n總乾燥消光: {result['dry']['Total_ext'].mean():.1f} Mm⁻¹")
    print(f"總濕消光: {result['wet']['Total_ext'].mean():.1f} Mm⁻¹")
    print(f"ALWC 貢獻: {result['ALWC']['Total_ext'].mean():.1f} Mm⁻¹")

    return result


# =============================================================================
# 範例 3: Mie 理論消光計算
# =============================================================================

def mie_extinction():
    """使用 Mie 理論計算消光"""

    # 讀取粒徑分布
    df_pnsd = RawDataReader(
        instrument='SMPS',
        path=DATA_PATH / 'SMPS',
        start=START,
        end=END,
        mean_freq='1h'
    )

    # 讀取化學成分計算折射率
    df_chem = pd.concat([
        RawDataReader('IGAC', DATA_PATH / 'IGAC', start=START, end=END, mean_freq='1h'),
        RawDataReader('OCEC', DATA_PATH / 'OCEC', start=START, end=END, mean_freq='1h')
    ], axis=1)

    # 計算折射率 (體積平均混合)
    mass_result = reconstruct_mass(df_chem)
    ri_result = volume_ri(mass_result['volume'])
    # 把 n_dry/k_dry 組合成 complex RI 給 mie 用
    ri_complex = ri_result['n_dry'] + 1j * ri_result['k_dry']

    # Mie 計算（單一材料路徑：給 complex Series）
    optics = mie(df_pnsd, ri=ri_complex, wavelength=550)
    total_ext = optics['ext']
    total_sca = optics['sca']
    total_abs = optics['abs']

    print("\n=== Mie 消光計算 (體積平均 RI) ===")
    print(f"消光係數: {total_ext.mean():.1f} Mm⁻¹")
    print(f"散射係數: {total_sca.mean():.1f} Mm⁻¹")
    print(f"吸收係數: {total_abs.mean():.1f} Mm⁻¹")
    print(f"SSA: {(total_sca / total_ext).mean():.3f}")

    return optics


# =============================================================================
# 範例 4: 混合模式比較
# =============================================================================

def compare_mixing_modes():
    """比較 internal vs external mixing 模式的消光計算"""

    df_pnsd = RawDataReader(
        instrument='SMPS',
        path=DATA_PATH / 'SMPS',
        start=START,
        end=END,
        mean_freq='1h'
    )

    # 假設有 species mixing 表 (各成分的 volume ratio)
    # 實務上會從 reconstruct_mass + volume_ri 流程拿到
    df_mixing = pd.DataFrame({
        'AS_volume_ratio': 0.3,
        'AN_volume_ratio': 0.2,
        'OM_volume_ratio': 0.3,
        'EC_volume_ratio': 0.1,
        'Soil_volume_ratio': 0.05,
        'SS_volume_ratio': 0.05,
    }, index=df_pnsd.index)

    print("\n=== 混合模式比較 ===")
    both = mie(df_pnsd, ri=df_mixing, wavelength=550, mixing='both')
    for mode, result in both.items():
        total = result['ext'].mean()
        print(f"{mode}: {total:.1f} Mm⁻¹")

    return both


# =============================================================================
# 範例 5: 折射率反演
# =============================================================================

def retrieve_refractive_index():
    """從測量數據反演折射率"""

    # 讀取光學測量
    df_neph, df_ae33 = read_optical_data()
    df_optical = pd.concat([df_neph, df_ae33], axis=1)

    # 讀取粒徑分布
    df_pnsd = RawDataReader(
        instrument='SMPS',
        path=DATA_PATH / 'SMPS',
        start=START,
        end=END,
        mean_freq='1h'
    )

    # 反演折射率
    result = retrieve_ri(
        df_optical=df_optical,
        df_pnsd=df_pnsd,
        wavelength=550,
    )

    print("\n=== 折射率反演 ===")
    print(f"實部 (n): {result['re_real'].mean():.3f}")
    print(f"虛部 (k): {result['re_imaginary'].mean():.4f}")

    return result


# =============================================================================
# 範例 6: 衍生光學參數
# =============================================================================

def derived_optical_parameters():
    """計算衍生光學參數"""

    df_neph, df_ae33 = read_optical_data()

    df_ocec = RawDataReader(
        instrument='OCEC',
        path=DATA_PATH / 'OCEC',
        start=START,
        end=END,
        mean_freq='1h'
    )

    # 假設有氣體和氣象數據
    # df_no2 = read_gas_data()
    # df_temp = read_met_data()

    # 衍生光學參數目前在 AeroViz.dataProcess.Optical._derived 內部
    # (沒有 expose 在 top-level)，使用方式：
    #
    # from AeroViz.dataProcess.Optical._derived import derived_parameters
    # result = derived_parameters(
    #     df_sca=df_neph, df_abs=df_ae33, df_ec=df_ocec,
    #     df_no2=df_no2, df_temp=df_temp,
    # )
    # print(f"MAC: {result['MAC'].mean():.2f} m²/g")
    # print(f"能見度: {result['Vis_cal'].mean():.1f} km")

    print("需要完整數據 (散射、吸收、EC、NO2、溫度) 才能計算衍生參數")


# =============================================================================
# 範例 7: 光學閉合分析
# =============================================================================

def optical_closure():
    """光學閉合分析"""

    # 1. 測量消光
    df_neph, df_ae33 = read_optical_data()

    if 'Sca_550' in df_neph.columns and 'Abs_550' in df_ae33.columns:
        ext_measured = df_neph['Sca_550'] + df_ae33['Abs_550']
    else:
        # 使用其他波長
        sca_col = [c for c in df_neph.columns if 'Sca' in c][0]
        abs_col = [c for c in df_ae33.columns if 'Abs' in c][0]
        ext_measured = df_neph[sca_col] + df_ae33[abs_col]

    # 2. IMPROVE 計算消光
    improve_result = improve_extinction()
    ext_improve = improve_result['wet']['Total_ext']

    # 3. 對齊時間索引
    common_idx = ext_measured.index.intersection(ext_improve.index)
    ext_m = ext_measured.loc[common_idx]
    ext_i = ext_improve.loc[common_idx]

    # 4. 計算閉合統計
    from scipy import stats
    slope, intercept, r, p, se = stats.linregress(ext_m, ext_i)

    print("\n=== 光學閉合 (IMPROVE) ===")
    print(f"測量消光: {ext_m.mean():.1f} Mm⁻¹")
    print(f"IMPROVE 消光: {ext_i.mean():.1f} Mm⁻¹")
    print(f"R²: {r**2:.3f}")
    print(f"斜率: {slope:.2f}")
    print(f"比值: {(ext_i / ext_m).mean():.2f}")

    return ext_m, ext_i


# =============================================================================
# 主程式
# =============================================================================

if __name__ == '__main__':
    # 取消註解以執行對應範例

    # df_neph, df_ae33 = read_optical_data()
    # improve = improve_extinction()
    # optics = mie_extinction()
    # mixing = compare_mixing_modes()
    # ri = retrieve_refractive_index()
    # derived_optical_parameters()
    # ext_m, ext_i = optical_closure()

    print("請修改 DATA_PATH 後取消註解執行對應範例")
