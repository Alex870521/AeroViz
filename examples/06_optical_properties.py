"""
06_optical_properties.py - 光學特性計算範例

此範例展示如何使用 DataProcess 計算光學特性。
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from AeroViz import RawDataReader
from AeroViz.dataProcess import DataProcess
from AeroViz.dataProcess.SizeDistr import SizeDist

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
    dp_chem = DataProcess('Chemistry', OUTPUT_PATH)
    mass_result = dp_chem.reconstruction_basic(df_chem)
    df_mass = mass_result['mass']

    # RH 數據 (假設)
    df_RH = pd.DataFrame({'RH': 70}, index=df_mass.index)

    # IMPROVE 計算
    dp_opt = DataProcess('Optical', OUTPUT_PATH)
    result = dp_opt.IMPROVE(
        df_mass=df_mass,
        df_RH=df_RH,
        method='revised'  # 'revised' 或 'modified'
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

    # 計算折射率
    dp_chem = DataProcess('Chemistry', OUTPUT_PATH)
    vol_ri = dp_chem.volume_RI(df_chem)
    df_RI = vol_ri['RI']

    # 使用 SizeDist 計算消光分布
    psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')

    # 內混合模式
    ext_internal = psd.to_extinction(df_RI, method='internal', result_type='extinction')
    sca_internal = psd.to_extinction(df_RI, method='internal', result_type='scattering')
    abs_internal = psd.to_extinction(df_RI, method='internal', result_type='absorption')

    # 總消光係數
    total_ext = ext_internal.sum(axis=1)
    total_sca = sca_internal.sum(axis=1)
    total_abs = abs_internal.sum(axis=1)

    print("\n=== Mie 消光計算 (內混合) ===")
    print(f"消光係數: {total_ext.mean():.1f} Mm⁻¹")
    print(f"散射係數: {total_sca.mean():.1f} Mm⁻¹")
    print(f"吸收係數: {total_abs.mean():.1f} Mm⁻¹")
    print(f"SSA: {(total_sca / total_ext).mean():.3f}")

    return ext_internal, sca_internal, abs_internal


# =============================================================================
# 範例 4: 混合模式比較
# =============================================================================

def compare_mixing_modes():
    """比較不同混合模式的消光計算"""

    df_pnsd = RawDataReader(
        instrument='SMPS',
        path=DATA_PATH / 'SMPS',
        start=START,
        end=END,
        mean_freq='1h'
    )

    # 假設有折射率數據
    df_RI = pd.DataFrame({
        'n': 1.5,
        'k': 0.01
    }, index=df_pnsd.index)

    psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')

    methods = ['internal', 'external', 'core_shell']
    results = {}

    print("\n=== 混合模式比較 ===")
    for method in methods:
        try:
            ext = psd.to_extinction(df_RI, method=method, result_type='extinction')
            total = ext.sum(axis=1).mean()
            results[method] = total
            print(f"{method}: {total:.1f} Mm⁻¹")
        except Exception as e:
            print(f"{method}: {e}")

    return results


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

    psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')

    # 反演折射率
    dp_opt = DataProcess('Optical', OUTPUT_PATH)
    result = dp_opt.retrieve_RI(
        df_optical=df_optical,
        df_pnsd=df_pnsd,
        dlogdp=psd.dlogdp,
        wavelength=550
    )

    print("\n=== 折射率反演 ===")
    print(f"實部 (n): {result['n'].mean():.3f} ± {result['n'].std():.3f}")
    print(f"虛部 (k): {result['k'].mean():.4f} ± {result['k'].std():.4f}")

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

    dp_opt = DataProcess('Optical', OUTPUT_PATH)

    # result = dp_opt.derived(
    #     df_sca=df_neph,
    #     df_abs=df_ae33,
    #     df_ec=df_ocec,
    #     df_no2=df_no2,
    #     df_temp=df_temp
    # )

    # print("\n=== 衍生參數 ===")
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
    # ext, sca, abs = mie_extinction()
    # mixing = compare_mixing_modes()
    # ri = retrieve_refractive_index()
    # derived_optical_parameters()
    # ext_m, ext_i = optical_closure()

    print("請修改 DATA_PATH 後取消註解執行對應範例")
