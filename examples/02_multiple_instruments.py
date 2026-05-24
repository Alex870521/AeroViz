"""
02_multiple_instruments.py - 多儀器數據整合範例

此範例展示如何讀取多種儀器數據並進行整合分析。
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from AeroViz import RawDataReader

# =============================================================================
# 設定參數
# =============================================================================

DATA_PATH = Path('/path/to/your/data')
START = datetime(2024, 1, 1)
END = datetime(2024, 3, 31)
MEAN_FREQ = '1h'

# =============================================================================
# 範例 1: 讀取光學儀器組合 (散射 + 吸收)
# =============================================================================

def read_optical_instruments():
    """讀取 NEPH 和 AE33 計算光學特性"""

    # 讀取散射係數
    df_neph = RawDataReader(
        instrument='NEPH',
        path=DATA_PATH / 'NEPH',
        start=START,
        end=END,
        mean_freq=MEAN_FREQ
    )

    # 讀取吸收係數
    df_ae33 = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'AE33',
        start=START,
        end=END,
        mean_freq=MEAN_FREQ
    )

    # 合併數據 (自動對齊時間索引)
    df_optical = pd.concat([df_neph, df_ae33], axis=1)

    # 計算消光係數
    if 'Sca_550' in df_optical.columns and 'Abs_550' in df_optical.columns:
        df_optical['Ext_550'] = df_optical['Sca_550'] + df_optical['Abs_550']

        # 計算單次散射反照率 (SSA)
        df_optical['SSA_550'] = df_optical['Sca_550'] / df_optical['Ext_550']

    print("=== 光學數據整合 ===")
    print(f"數據點數: {len(df_optical)}")
    print(f"欄位: {df_optical.columns.tolist()}")

    return df_optical


# =============================================================================
# 範例 2: 讀取粒徑分布組合 (SMPS + APS)
# =============================================================================

def read_size_distribution():
    """讀取 SMPS 和 APS 覆蓋完整粒徑範圍"""

    # SMPS: 10-600 nm
    df_smps = RawDataReader(
        instrument='SMPS',
        path=DATA_PATH / 'SMPS',
        start=START,
        end=END,
        mean_freq=MEAN_FREQ,
        size_range=(11.8, 593.5)
    )

    # APS: 0.5-20 μm
    df_aps = RawDataReader(
        instrument='APS',
        path=DATA_PATH / 'APS',
        start=START,
        end=END,
        mean_freq=MEAN_FREQ
    )

    print("=== 粒徑分布數據 ===")
    print(f"SMPS 粒徑範圍: {df_smps.columns[0]} ~ {df_smps.columns[-1]} nm")
    print(f"APS 粒徑範圍: {df_aps.columns[0]} ~ {df_aps.columns[-1]} µm")

    # 注意: SMPS-APS 合併使用 AeroViz.size.merge_psd
    # 參見 04_size_distribution.py

    return df_smps, df_aps


# =============================================================================
# 範例 3: 讀取化學成分組合 (離子 + 碳)
# =============================================================================

def read_chemical_composition():
    """讀取 IGAC 和 OCEC 組成完整化學成分"""

    # 離子成分
    df_igac = RawDataReader(
        instrument='IGAC',
        path=DATA_PATH / 'IGAC',
        start=START,
        end=END,
        mean_freq=MEAN_FREQ
    )

    # 碳成分
    df_ocec = RawDataReader(
        instrument='OCEC',
        path=DATA_PATH / 'OCEC',
        start=START,
        end=END,
        mean_freq=MEAN_FREQ
    )

    # 合併
    df_chem = pd.concat([df_igac, df_ocec], axis=1)

    print("=== 化學成分數據 ===")
    print(f"離子欄位: {df_igac.columns.tolist()}")
    print(f"碳欄位: {df_ocec.columns.tolist()}")

    return df_chem


# =============================================================================
# 範例 4: 完整數據整合
# =============================================================================

def read_all_instruments():
    """讀取所有儀器並整合"""

    instruments = {
        'NEPH': DATA_PATH / 'NEPH',
        'AE33': DATA_PATH / 'AE33',
        'SMPS': DATA_PATH / 'SMPS',
        'IGAC': DATA_PATH / 'IGAC',
        'OCEC': DATA_PATH / 'OCEC',
    }

    dataframes = {}

    for inst, path in instruments.items():
        if path.exists():
            try:
                kwargs = {'mean_freq': MEAN_FREQ}
                if inst == 'SMPS':
                    kwargs['size_range'] = (11.8, 593.5)

                df = RawDataReader(
                    instrument=inst,
                    path=path,
                    start=START,
                    end=END,
                    **kwargs
                )
                dataframes[inst] = df
                print(f"✓ {inst}: {len(df)} 筆數據")
            except Exception as e:
                print(f"✗ {inst}: {e}")
        else:
            print(f"- {inst}: 路徑不存在")

    return dataframes


# =============================================================================
# 範例 5: 數據對齊與插值
# =============================================================================

def align_and_interpolate():
    """對齊不同時間解析度的數據"""

    # 讀取不同解析度數據
    df_neph = RawDataReader(
        instrument='NEPH',
        path=DATA_PATH / 'NEPH',
        start=START,
        end=END,
        mean_freq='1h'  # 小時數據
    )

    # 假設有日數據 (例如濾紙採樣)
    # df_filter = read_filter_data()  # 日數據

    # 對齊到共同時間索引
    common_index = df_neph.index

    # 合併時自動對齊
    # df_combined = pd.concat([df_neph, df_filter.reindex(common_index, method='ffill')], axis=1)

    print("數據對齊完成")

    return df_neph


# =============================================================================
# 主程式
# =============================================================================

if __name__ == '__main__':
    # 取消註解以執行對應範例

    # df_optical = read_optical_instruments()
    # df_smps, df_aps = read_size_distribution()
    # df_chem = read_chemical_composition()
    # all_data = read_all_instruments()

    print("請修改 DATA_PATH 後取消註解執行對應範例")
