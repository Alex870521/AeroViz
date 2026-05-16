"""
03_quality_control.py - 品質控制設定範例

此範例展示 RawDataReader 的品質控制選項和數據處理模式。
"""

from datetime import datetime
from pathlib import Path

from AeroViz import RawDataReader

# =============================================================================
# 設定參數
# =============================================================================

DATA_PATH = Path('/path/to/your/data')
START = datetime(2024, 1, 1)
END = datetime(2024, 6, 30)

# =============================================================================
# 範例 1: 品質控制報告頻率
# =============================================================================

def qc_report_frequency():
    """設定 QC 報告的輸出頻率"""

    # 月報告 (每月輸出一次 QC 統計)
    df_monthly = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'AE33',
        start=START,
        end=END,
        mean_freq='1h',
        qc='1MS'  # Month Start - 每月報告
    )

    # 週報告
    df_weekly = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'AE33',
        start=START,
        end=END,
        mean_freq='1h',
        qc='W'  # Weekly - 每週報告
    )

    # 季報告
    df_quarterly = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'AE33',
        start=START,
        end=END,
        mean_freq='1h',
        qc='QS'  # Quarter Start - 每季報告
    )

    """
    QC 報告輸出範例:

    ▶ Processing: 2024-01-01 to 2024-01-31
        ▶ BC Mass Conc. (880 nm)
            ├─ Sample Rate    :  100.0%    # 採樣率
            ├─ Valid  Rate    :   99.5%    # 有效率 (通過 QC)
            └─ Total  Rate    :   99.5%    # 總有效率
    """

    return df_monthly


# =============================================================================
# 範例 2: 跳過品質控制
# =============================================================================

def skip_qc():
    """跳過 QC 返回原始數據"""

    # 不套用 QC (用於檢查原始數據)
    df_raw = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'AE33',
        start=START,
        end=END,
        mean_freq='1h',
        qc=False  # 跳過 QC
    )

    print("=== 原始數據 (無 QC) ===")
    print(f"數據點數: {len(df_raw)}")
    print(f"包含 NaN: {df_raw.isna().sum().sum()}")

    return df_raw


# =============================================================================
# 範例 3: 數據處理模式
# =============================================================================

def processing_modes():
    """不同的數據處理模式"""

    # 模式 1: 使用快取 (預設)
    # 如果已有處理過的數據，直接使用
    df_cached = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'AE33',
        start=START,
        end=END,
        mean_freq='1h',
        reset=False  # 使用快取 (預設)
    )

    # 模式 2: 強制重新處理
    # 忽略快取，從原始檔案重新處理
    df_fresh = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'AE33',
        start=START,
        end=END,
        mean_freq='1h',
        reset=True  # 強制重新處理
    )

    # 模式 3: 附加新數據
    # 保留既有數據，只處理新增的檔案
    df_append = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'AE33',
        start=START,
        end=END,
        mean_freq='1h',
        reset='append'  # 附加模式
    )

    return df_cached


# =============================================================================
# 範例 4: 平均頻率設定
# =============================================================================

def resampling_frequency():
    """不同的時間平均設定"""

    # 小時平均
    df_hourly = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'AE33',
        start=START,
        end=END,
        mean_freq='1h'
    )

    # 30 分鐘平均
    df_30min = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'AE33',
        start=START,
        end=END,
        mean_freq='30min'
    )

    # 日平均
    df_daily = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'AE33',
        start=START,
        end=END,
        mean_freq='1D'
    )

    print(f"小時平均數據點: {len(df_hourly)}")
    print(f"30分鐘平均數據點: {len(df_30min)}")
    print(f"日平均數據點: {len(df_daily)}")

    return df_hourly, df_30min, df_daily


# =============================================================================
# 範例 5: 粒徑範圍過濾 (SMPS/APS)
# =============================================================================

def size_range_filtering():
    """設定粒徑分布的範圍"""

    # 標準範圍
    df_standard = RawDataReader(
        instrument='SMPS',
        path=DATA_PATH / 'SMPS',
        start=START,
        end=END,
        mean_freq='1h',
        size_range=(11.8, 593.5)  # 標準 SMPS 範圍
    )

    # 自訂範圍 (僅保留細粒子)
    df_fine = RawDataReader(
        instrument='SMPS',
        path=DATA_PATH / 'SMPS',
        start=START,
        end=END,
        mean_freq='1h',
        size_range=(10, 100)  # 僅 10-100 nm
    )

    print(f"標準範圍粒徑通道: {len(df_standard.columns)}")
    print(f"細粒子範圍粒徑通道: {len(df_fine.columns)}")

    return df_standard, df_fine


# =============================================================================
# 範例 6: 日誌等級設定
# =============================================================================

def logging_settings():
    """設定日誌輸出等級"""

    # 詳細日誌 (除錯用)
    df_debug = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'AE33',
        start=START,
        end=END,
        mean_freq='1h',
        log_level='DEBUG'
    )

    # 僅顯示警告和錯誤
    df_quiet = RawDataReader(
        instrument='AE33',
        path=DATA_PATH / 'AE33',
        start=START,
        end=END,
        mean_freq='1h',
        log_level='WARNING',
        suppress_warnings=True  # 抑制警告
    )

    return df_debug


# =============================================================================
# 主程式
# =============================================================================

if __name__ == '__main__':
    # 取消註解以執行對應範例

    # df = qc_report_frequency()
    # df = skip_qc()
    # df = processing_modes()
    # hourly, min30, daily = resampling_frequency()
    # standard, fine = size_range_filtering()

    print("請修改 DATA_PATH 後取消註解執行對應範例")
