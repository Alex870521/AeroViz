"""
01_basic_reading.py - 基本儀器數據讀取範例 / Basic instrument data reading

此範例展示如何使用 RawDataReader 讀取各種氣膠儀器的數據。
This example shows how to read raw aerosol-instrument data with RawDataReader.

How to run / 執行方式:
  1. Edit DATA_PATH below to point at your data directory, then uncomment one of
     the read_*() calls in the __main__ block:
         python examples/01_basic_reading.py
     編輯下方 DATA_PATH 指向你的資料夾，並取消註解 __main__ 內的某個 read_*()。
  2. Or run the synthetic demo (no data files needed):
     或直接跑合成資料 demo（不需要任何資料檔）:
         python examples/01_basic_reading.py --demo
"""

import sys
from datetime import datetime
from pathlib import Path

from AeroViz import RawDataReader

# =============================================================================
# 設定參數 / Configuration
# =============================================================================

# 修改為您的數據路徑 / Edit this to your data directory
DATA_PATH = Path('/path/to/your/data')

# 時間範圍 / Time range
START = datetime(2024, 1, 1)
END = datetime(2024, 3, 31)


# =============================================================================
# 範例 1: 讀取 AE33 黑碳數據
# =============================================================================

def read_ae33():
    """讀取 AE33 七波長黑碳儀數據"""

    df = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'AE33',
        start=START,
        end=END,
        mean_freq='1h'  # 小時平均 / hourly average
    )

    # Expected output: a time-indexed DataFrame with columns
    #   BC1-BC7, abs_370-abs_950, AAE, eBC, QC_Flag (+ df.attrs metadata)
    print("=== AE33 數據 ===")
    print(f"時間範圍: {df.index[0]} ~ {df.index[-1]}")
    print(f"數據點數: {len(df)}")
    print(f"欄位: {df.columns.tolist()}")
    print(df[['eBC', 'AAE']].describe())

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
        path=DATA_PATH / 'SMPS',
        start=START,
        end=END,
        mean_freq='1h',
        size_range=(11.8, 593.5)  # 指定粒徑範圍 (nm) / size range in nm
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
        path=DATA_PATH / 'APS',
        start=START,
        end=END,
        mean_freq='1h',
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
        path=DATA_PATH / 'TEOM',
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
        path=DATA_PATH / 'Xact',
        start='2024-01-01',  # ISO 格式字串 / ISO date string
        end='2024-03-31',  # ISO 格式字串 / ISO date string
        mean_freq='1h'
    )

    return df


# =============================================================================
# 範例 9: 可選時間範圍 + 原解析度(新行為)
# =============================================================================

def read_full_coverage():
    """省略 start/end 與 mean_freq → 回傳檔案全部 coverage、原解析度(不 resample)。"""

    # start/end 皆可省略;不給 mean_freq 就不 resample(回傳儀器原頻率)
    df = RawDataReader('AE33', path=DATA_PATH / 'AE33')

    print("=== 全 coverage(原解析度)===")
    print(f"資料涵蓋: {df.attrs.get('coverage_start')} ~ {df.attrs.get('coverage_end')}")
    print(f"原始頻率: {df.attrs.get('raw_freq')} | 列數: {len(df)}")
    return df


# =============================================================================
# 範例 10: 讀取結果的中繼資料(df.attrs)
# =============================================================================

def inspect_metadata():
    """每次讀取都會在 df.attrs 附上 provenance / coverage / QC 統計。"""

    df = RawDataReader('AE33', path=DATA_PATH / 'AE33',
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

    padded = RawDataReader('AE33', path=DATA_PATH / 'AE33',
                           start=START, end=END, mean_freq='1h')                # 預設 True
    clamped = RawDataReader('AE33', path=DATA_PATH / 'AE33',
                            start=START, end=END, mean_freq='1h', fill_missing=False)

    print(f"padded  列數: {len(padded)}  ({padded.index[0]} ~ {padded.index[-1]})")
    print(f"clamped 列數: {len(clamped)}  ({clamped.index[0]} ~ {clamped.index[-1]})")
    return padded, clamped


# =============================================================================
# 合成資料 Demo / Synthetic demo (no data files required)
# =============================================================================

def demo():
    """Show the *shape* of a reader result using synthetic data — no files needed.

    用合成資料示範 reader 回傳值的「樣子」（時間索引 + 欄位 + df.attrs），
    不需要任何資料檔。實際讀檔請用上面的 read_*() 函式。
    """
    import numpy as np
    import pandas as pd

    print("=== AeroViz 基本讀取 Demo (synthetic data) ===\n")

    # A reader returns a time-indexed DataFrame. Here we fake an AE33 result.
    idx = pd.date_range('2024-01-01', periods=72, freq='h', name='time')
    rng = np.random.default_rng(0)
    df = pd.DataFrame({
        'eBC': rng.gamma(2, 500, len(idx)),       # ng/m3
        'AAE': rng.normal(1.1, 0.15, len(idx)),
        'abs_880': rng.gamma(2, 3, len(idx)),     # Mm-1
    }, index=idx)
    df['QC_Flag'] = 'Valid'

    # Real reads attach provenance/coverage to df.attrs — we mimic the key ones.
    df.attrs.update({
        'instrument': 'AE33',
        'coverage_start': idx[0],
        'coverage_end': idx[-1],
        'raw_freq': '1min',
    })

    print(f"時間範圍 / time range : {df.index[0]} ~ {df.index[-1]}")
    print(f"數據點數 / n rows     : {len(df)}")
    print(f"欄位 / columns        : {df.columns.tolist()}")
    print(f"df.attrs              : instrument={df.attrs['instrument']}, "
          f"coverage={df.attrs['coverage_start']} ~ {df.attrs['coverage_end']}")
    print("\n" + str(df[['eBC', 'AAE']].describe()))
    print("\n(這是合成資料；用 --demo 以外的方式請編輯 DATA_PATH。)")
    return df


# =============================================================================
# 主程式 / Main
# =============================================================================

if __name__ == '__main__':
    if '--demo' in sys.argv:
        demo()
        sys.exit(0)

    if not DATA_PATH.exists():
        print("DATA_PATH does not exist. Edit DATA_PATH at the top of this file,")
        print("or run the synthetic demo:  python examples/01_basic_reading.py --demo")
        sys.exit(0)

    # 取消註解以執行對應範例 / Uncomment the read you want to run
    df_ae33 = read_ae33()
    # df_neph = read_neph()
    # df_smps = read_smps()
    # df_aps = read_aps()
    # df_ocec = read_ocec()
    # df_igac = read_igac()
    # df_xact = read_with_string_time()
    # df = read_TEOM()
    # df_full = read_full_coverage()       # 省略範圍/頻率 → 全 coverage、原解析度
    # df_meta = inspect_metadata()         # 看 df.attrs
    # read_padded_vs_clamped()             # fill_missing 行為對比
