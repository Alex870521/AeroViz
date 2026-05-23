"""
01_basic_reading.py - 基本儀器數據讀取範例

此範例展示如何使用 RawDataReader 讀取各種氣膠儀器的數據。
"""

from datetime import datetime
from pathlib import Path

from AeroViz import RawDataReader

# =============================================================================
# 設定參數
# =============================================================================

# 修改為您的數據路徑
# DATA_PATH = Path('/Users/chanchihyu/Downloads')
DATA_PATH = Path(
    '/Users/chanchihyu/Library/CloudStorage/GoogleDrive-alex870521@gmail.com/共用雲端硬碟/Data Center/TCLab_Database/Raw Data Repository/2026/NZ/NZ_APS')

# 時間範圍
START = datetime(2026, 1, 1)
END = datetime(2026, 3, 5)


# =============================================================================
# 範例 1: 讀取 AE33 黑碳數據
# =============================================================================

def read_ae33():
    """讀取 AE33 七波長黑碳儀數據"""

    df = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'TP_AE33',
        reset=True,
        start=START,
        end=END,
        mean_freq='1h'  # 小時平均
    )

    print("=== AE33 數據 ===")
    print(f"時間範圍: {df.index[0]} ~ {df.index[-1]}")
    print(f"數據點數: {len(df)}")
    print(f"欄位: {df.columns.tolist()}")
    print(df.head())

    return df


# =============================================================================
# 範例 2: 讀取 NEPH 散射數據
# =============================================================================

def read_neph():
    """讀取 TSI 積分渾濁計數據"""

    df = RawDataReader(
        instrument='NEPH',
        path=DATA_PATH / 'NEPH',
        start=START,
        end=END,
        mean_freq='1h'
    )

    print("=== NEPH 數據 ===")
    print(f"時間範圍: {df.index[0]} ~ {df.index[-1]}")
    print(f"欄位: {df.columns.tolist()}")
    print(df.describe())

    return df


# =============================================================================
# 範例 3: 讀取 SMPS 粒徑分布數據
# =============================================================================

def read_smps():
    """讀取 SMPS 掃描電遷移粒徑分析儀數據"""

    df = RawDataReader(
        instrument='SMPS',
        path=DATA_PATH / 'NZ_SMPS',
        reset=True,
        start=START,
        end=END,
        mean_freq='1h',
        size_range=(11.8, 593.5)  # 指定粒徑範圍 (nm)
    )

    print("=== SMPS 數據 ===")
    print(f"時間範圍: {df.index[0]} ~ {df.index[-1]}")
    print(f"粒徑通道數: {len(df.columns)}")
    print(f"粒徑範圍: {df.columns[0]} ~ {df.columns[-1]} nm")

    return df


# =============================================================================
# 範例 4: 讀取 APS 粒徑分布數據
# =============================================================================

def read_aps():
    """讀取 APS 空氣動力學粒徑分析儀數據"""

    df = RawDataReader(
        instrument='APS',
        path=DATA_PATH,
        reset=True,
        start=START,
        end=END,
        mean_freq='1h',
        output_dir=Path('/Users/chanchihyu/Desktop/test'),
    )

    print("=== APS 數據 ===")
    print(f"時間範圍: {df.index[0]} ~ {df.index[-1]}")
    print(f"粒徑通道數: {len(df.columns)}")

    return df


# =============================================================================
# 範例 5: 讀取 OCEC 碳成分數據
# =============================================================================

def read_ocec():
    """讀取 OC/EC 分析儀數據"""

    df = RawDataReader(
        instrument='OCEC',
        path=DATA_PATH / 'OCEC',
        start=START,
        end=END,
        mean_freq='1h'
    )

    print("=== OCEC 數據 ===")
    print(f"欄位: {df.columns.tolist()}")
    print(df.describe())

    return df


# =============================================================================
# 範例 6: 讀取 IGAC 離子數據
# =============================================================================

def read_igac():
    """讀取離子層析儀數據"""

    df = RawDataReader(
        instrument='IGAC',
        path=DATA_PATH / 'IGAC',
        start=START,
        end=END,
        mean_freq='1h'
    )

    print("=== IGAC 數據 ===")
    print(f"欄位: {df.columns.tolist()}")
    print(df.describe())

    return df


# =============================================================================
# 範例 7: 讀取 TEOM 數據
# =============================================================================

def read_TEOM():
    """讀取TEOM數據"""

    df = RawDataReader(
        instrument='TEOM',
        reset=True,
        path=Path('/Users/chanchihyu/DataCenter/Raw Data/NZ_TEOM'),
        start=START,
        end=END,
        mean_freq='1h'
    )

    print("=== TEOM 數據 ===")
    print(f"欄位: {df.columns.tolist()}")
    print(df.describe())

    return df


# =============================================================================
# 範例 8: 使用字串格式的時間
# =============================================================================

def read_with_string_time():
    """使用 ISO 格式字串指定時間"""

    df = RawDataReader(
        instrument='Xact',
        reset=True,
        path=Path('/Users/chanchihyu/DataCenter/Raw Data/FS_Xact'),
        start='2025-11-13',  # ISO 格式字串
        end='2025-12-25',  # ISO 格式字串
        mean_freq='1h'
    )

    return df


# =============================================================================
# 範例 9: 可選時間範圍 + 原解析度(新行為)
# =============================================================================

def read_full_coverage():
    """省略 start/end 與 mean_freq → 回傳檔案全部 coverage、原解析度(不 resample)。"""

    # start/end 皆可省略;不給 mean_freq 就不 resample(回傳儀器原頻率)
    df = RawDataReader('AE33', path=DATA_PATH / 'TP_AE33')

    print("=== 全 coverage(原解析度)===")
    print(f"資料涵蓋: {df.attrs.get('coverage_start')} ~ {df.attrs.get('coverage_end')}")
    print(f"原始頻率: {df.attrs.get('raw_freq')} | 列數: {len(df)}")
    return df


# =============================================================================
# 範例 10: 讀取結果的中繼資料(df.attrs)
# =============================================================================

def inspect_metadata():
    """每次讀取都會在 df.attrs 附上 provenance / coverage / QC 統計。"""

    df = RawDataReader('AE33', path=DATA_PATH / 'TP_AE33',
                       start=START, end=END, mean_freq='1h')

    a = df.attrs
    print("=== df.attrs ===")
    print(f"instrument : {a.get('instrument')}")
    print(f"coverage   : {a.get('coverage_start')} ~ {a.get('coverage_end')}")
    print(f"requested  : {a.get('requested_start')} ~ {a.get('requested_end')}")
    print(f"raw_freq   : {a.get('raw_freq')} (mixed={a.get('freq_mixed')})")
    print(f"rates      : acquisition {a.get('acquisition_rate')}% / total {a.get('total_rate')}%")
    return df


# =============================================================================
# 範例 11: fill_missing — pad 到請求範圍 vs 夾到 coverage
# =============================================================================

def read_padded_vs_clamped():
    """fill_missing=True(預設)pad 到 [start, end];False 夾到實際 coverage(不膨脹)。"""

    padded = RawDataReader('AE33', path=DATA_PATH / 'TP_AE33',
                           start=START, end=END, mean_freq='1h')                # 預設 True
    clamped = RawDataReader('AE33', path=DATA_PATH / 'TP_AE33',
                            start=START, end=END, mean_freq='1h', fill_missing=False)

    print(f"padded  列數: {len(padded)}  ({padded.index[0]} ~ {padded.index[-1]})")
    print(f"clamped 列數: {len(clamped)}  ({clamped.index[0]} ~ {clamped.index[-1]})")
    return padded, clamped


# =============================================================================
# 主程式
# =============================================================================

if __name__ == '__main__':
    # 取消註解以執行對應範例

    # df_ae33 = read_ae33()
    # df_neph = read_neph()
    # df_smps = read_smps()
    df_aps = read_aps()
    # df_ocec = read_ocec()
    # df_igac = read_igac()
    # df_xact = read_with_string_time()
    # df = read_TEOM()
    # df_full = read_full_coverage()       # 省略範圍/頻率 → 全 coverage、原解析度
    # df_meta = inspect_metadata()         # 看 df.attrs
    # read_padded_vs_clamped()             # fill_missing 行為對比
