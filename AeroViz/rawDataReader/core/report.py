import os

import pandas as pd


def process_timeline_report(report_dict: dict, df: pd.DataFrame, max_gap_hours: int = 2,
                            logger=None) -> dict:
    """
    Process instrument data and generate timeline data showing operational status.

    Parameters
    ----------
    report_dict : dict
        Report dictionary containing instrument information and configuration.
    df : pandas.DataFrame
        Data frame containing instrument measurements with datetime index or column.
    max_gap_hours : int, default 2
        Maximum allowed downtime (hours) before considering it as a significant data gap
        rather than brief downtime.
    logger : Logger, optional
        Logger object to use for logging messages. If None, print statements are used.

    Returns
    -------
    dict
        Updated report_dict with added 'timeline' key containing status changes.
        Timeline data includes operational periods and downtime periods with reasons.

    Notes
    -----
    The function detects data gaps based on whether any data exists in each row.
    Known issues are loaded from a YAML configuration file and matched against
    detected downtime periods to provide specific reason information.
    """

    # Helper function for logging
    def log_message(level: str, message: str) -> None:
        if logger:
            if level == "info":
                logger.info(message)
            elif level == "warning":
                logger.warning(message)
            elif level == "error":
                logger.error(message)
        else:
            print(message)

    # 使用報告中的儀器ID
    instrument_id = report_dict.get('instrument_id')

    # 查找已知問題 - 使用環境變量或默認路徑
    known_issues_file = os.environ.get(
        'KNOWN_ISSUES_PATH',
        '/Users/chanchihyu/DataCenter/Config/known_issues.yml'
    )
    try:
        import yaml
        with open(known_issues_file, 'r', encoding='utf-8') as f:
            known_issues = yaml.safe_load(f)
    except ImportError:
        known_issues = {}
    except FileNotFoundError:
        # Silently ignore missing known issues file - it's optional
        known_issues = {}
    except Exception as e:
        log_message("error", f"Error loading known issues: {e}")
        known_issues = {}

    # 檢查數據是否為空
    if df.empty:
        return report_dict

    # 處理時間列
    df = df.copy()
    time_col = None

    # 如果是DatetimeIndex，將其重置為列
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()
        time_col = df.columns[0]
    else:
        # 嘗試找到時間列
        time_col_candidates = ['time', 'Time', 'timestamp', 'Timestamp',
                               'datetime', 'DateTime', 'date', 'Date']
        for col in time_col_candidates:
            if col in df.columns:
                time_col = col
                break

    if not time_col:
        return report_dict

    # 確保時間列是datetime格式
    try:
        df[time_col] = pd.to_datetime(df[time_col])
    except Exception as e:
        log_message("error", f"Time format conversion failed: {e}")
        return report_dict

    # 排序數據
    df = df.sort_values(time_col)

    # 判斷狀態：檢查每行是否有任何數據（排除時間列）
    data_columns = [col for col in df.columns if col != time_col]
    df['operational'] = df[data_columns].notna().any(axis=1)

    # 處理狀態變化
    status_changes = []
    current_status = None
    current_start = None
    previous_time = None
    current_down_start = None

    # 內部函數：格式化時間間隔
    def format_duration(duration):
        """格式化時間間隔為人類可讀格式"""
        hours = duration.total_seconds() / 3600
        if hours < 1:
            return f"{int(hours * 60)} minutes"
        elif hours < 24:
            return f"{int(hours)} hours"
        else:
            days = int(hours / 24)
            remaining_hours = int(hours % 24)
            return f"{days} days{' ' + str(remaining_hours) + ' hours' if remaining_hours > 0 else ''}"

    # 內部函數：查找已知問題
    def find_known_issue(start_time, end_time):
        """查找指定時間段內的已知問題"""
        if not known_issues or not instrument_id or instrument_id not in known_issues:
            return None

        instrument_issues = known_issues.get(instrument_id, [])
        start_time = pd.to_datetime(start_time)
        end_time = pd.to_datetime(end_time)

        for issue in instrument_issues:
            try:
                issue_start = pd.to_datetime(issue['start'])
                issue_end = pd.to_datetime(issue['end'])

                # 檢查時間段是否重疊
                if not (end_time <= issue_start or start_time >= issue_end):
                    return issue['reason']
            except Exception as e:
                log_message("error", f"Error processing issue: {e}")

        return None

    # 處理每一行數據
    for i, row in df.iterrows():
        time_str = row[time_col].strftime('%Y/%m/%d %H:%M')
        status = 'operational' if row['operational'] else 'down'

        # 第一條記錄
        if current_status is None:
            current_status = status
            current_start = time_str
            previous_time = row[time_col]
            if status == 'down':
                current_down_start = row[time_col]
            continue

        # 狀態變化
        if status != current_status:
            # 從運行變為停機
            if status == 'down':
                status_changes.append({
                    'start': current_start,
                    'end': time_str,
                    'status': 'operational',
                    'reason': None,
                    'duration': None
                })
                current_start = time_str
                current_down_start = row[time_col]
            # 從停機變為運行
            else:
                down_duration = row[time_col] - current_down_start
                known_reason = find_known_issue(current_start, time_str)

                if known_reason:
                    reason = known_reason
                elif down_duration <= pd.Timedelta(hours=max_gap_hours):
                    reason = "Brief Downtime"
                else:
                    reason = "Data Gap"

                status_changes.append({
                    'start': current_start,
                    'end': time_str,
                    'status': 'down',
                    'reason': reason,
                    'duration': format_duration(down_duration)
                })
                current_start = time_str
                current_down_start = None

            current_status = status

        previous_time = row[time_col]

    # 添加最後一個時間段
    if current_start is not None:
        if current_status == 'down':
            down_duration = previous_time - current_down_start
            known_reason = find_known_issue(current_start, previous_time.strftime('%Y/%m/%d %H:%M'))

            if known_reason:
                reason = known_reason
            elif down_duration <= pd.Timedelta(hours=max_gap_hours):
                reason = "Brief Downtime"
            else:
                reason = "Data Gap"

            status_changes.append({
                'start': current_start,
                'end': previous_time.strftime('%Y/%m/%d %H:%M'),
                'status': 'down',
                'reason': reason,
                'duration': format_duration(down_duration)
            })
        else:
            status_changes.append({
                'start': current_start,
                'end': previous_time.strftime('%Y/%m/%d %H:%M'),
                'status': current_status,
                'reason': None,
                'duration': None
            })

    # 將結果添加到報告中
    report_dict['timeline'] = status_changes

    return report_dict


def process_rates_report(logger, report_dict: dict,
                         weekly_raw_groups, monthly_raw_groups,
                         weekly_flag_groups, monthly_flag_groups) -> dict:
    """
    Generate acquisition and yield reports based on grouped data.

    Parameters
    ----------
    logger : Logger
        Logger object for outputting messages
    report_dict : dict
        Report dictionary to update with rate information
    weekly_raw_groups : pandas.core.groupby.GroupBy
        Raw data grouped by week
    monthly_raw_groups : pandas.core.groupby.GroupBy
        Raw data grouped by month
    weekly_flag_groups : pandas.core.groupby.GroupBy
        QC flag data grouped by week
    monthly_flag_groups : pandas.core.groupby.GroupBy
        QC flag data grouped by month

    Returns
    -------
    dict
        Updated report dictionary with weekly and monthly rate information

    Notes
    -----
    The report contains acquisition rates (percentage of data acquired vs expected),
    yield rates (percentage of data passing QC vs acquired), and
    total rates (overall percentage of valid data) for each time period.
    """
    report = report_dict.copy()

    # 確保 report 中有必要的結構
    if "rates" not in report:
        report["rates"] = {
            "weekly": {},
            "monthly": {}
        }

    # 處理週數據 - 使用標準週時間範圍
    for week_start, week_raw_data in weekly_raw_groups:
        # 獲取對應的 QC Flag 數據
        week_qc_flag = None
        if week_start in weekly_flag_groups.groups:
            week_qc_flag = weekly_flag_groups.get_group(week_start)

        if not week_raw_data.empty and week_qc_flag is not None:
            # 計算標準週結束時間（週日23:59:59）
            week_end = week_start + pd.Timedelta(days=6, hours=23, minutes=59, seconds=59)

            # 使用週的開始日期作為鍵
            period_key = week_start.strftime('%Y-%m-%d')

            report["rates"]["weekly"][period_key] = {
                "start_time": week_start.strftime('%Y-%m-%d %H:%M:%S'),
                "end_time": week_end.strftime('%Y-%m-%d %H:%M:%S'),
                "rates": calculate_rates(logger, week_raw_data, week_qc_flag)
            }

    # 處理月數據 - 使用標準月時間範圍
    for month_start, month_raw_data in monthly_raw_groups:
        # 獲取對應的 QC Flag 數據
        month_qc_flag = None
        if month_start in monthly_flag_groups.groups:
            month_qc_flag = monthly_flag_groups.get_group(month_start)

        if not month_raw_data.empty and month_qc_flag is not None:
            # 計算標準月結束時間（月末23:59:59）
            next_month_start = (month_start + pd.Timedelta(days=32)).replace(day=1)
            month_end = next_month_start - pd.Timedelta(seconds=1)

            # 使用月份作為鍵
            period_key = month_start.strftime('%Y-%m')

            report["rates"]["monthly"][period_key] = {
                "start_time": month_start.strftime('%Y-%m-%d %H:%M:%S'),
                "end_time": month_end.strftime('%Y-%m-%d %H:%M:%S'),
                "rates": calculate_rates(logger, month_raw_data, month_qc_flag)
            }

    return report


def calculate_rates(logger, raw_data: pd.DataFrame, qc_flag: pd.Series,
                    with_log: bool = False, resample_freq: str = '1h') -> dict:
    """
    Calculate data quality rates using QC_Flag.

    Parameters
    ----------
    logger : Logger
        Logger to use for message output
    raw_data : pd.DataFrame
        Raw data before quality control
    qc_flag : pd.Series
        QC flag series indicating validity of each row ("Valid" or error type)
    with_log : bool, default=False
        If True, outputs calculation logs
    resample_freq : str, default='1h'
        Frequency for resampling data when calculating rates

    Returns
    -------
    dict
        Dictionary containing:
            acquisition_rate : float
                Percentage of data acquired vs expected (期望時段內有資料的比例)
            yield_rate : float
                Percentage of data passing QC vs acquired (取得資料中通過QC的比例)
            total_rate : float
                Overall percentage of valid data (期望時段內有效資料的比例)

    Notes
    -----
    - Acquisition Rate: periods with data / expected periods
    - Yield Rate: periods passed QC / periods with data
    - Total Rate: periods passed QC / expected periods
    """
    if raw_data.empty or qc_flag is None:
        return {'acquisition_rate': 0, 'yield_rate': 0, 'total_rate': 0}

    # 期望的時段數量（基於 resample 頻率）
    period_size = len(raw_data.resample(resample_freq).mean().index)

    # 有資料的時段數量（raw_data 中至少有一個非 NaN 值的時段）
    sample_size = len(raw_data.resample(resample_freq).mean().dropna(how='all').index)

    # 使用 QC_Flag 計算有效時段
    valid_mask = qc_flag == 'Valid'
    # 重採樣：計算每個時段內 Valid 的比例
    valid_ratio_per_period = valid_mask.resample(resample_freq).mean()
    # 確保只計算 raw_data 有資料的時段
    has_data_mask = raw_data.resample(resample_freq).mean().notna().any(axis=1)
    # 有效時段：該時段內有資料且超過 50% 通過 QC
    qc_size = ((valid_ratio_per_period > 0.5) & has_data_mask).sum()

    # 防止除以零
    if period_size == 0:
        return {'acquisition_rate': 0, 'yield_rate': 0, 'total_rate': 0}

    # 計算比率
    sample_rate = round((sample_size / period_size) * 100, 1)
    valid_rate = round((qc_size / sample_size) * 100, 1) if sample_size > 0 else 0
    total_rate = round((qc_size / period_size) * 100, 1)

    if with_log:
        logger.info(f"  Acquisition Rate : {logger.BLUE}{sample_rate:>5.1f}%{logger.RESET} ({sample_size}/{period_size} periods with data)")
        logger.info(f"  Yield Rate       : {logger.BLUE}{valid_rate:>5.1f}%{logger.RESET} ({qc_size}/{sample_size} periods passed QC)")
        logger.info(f"  Total Rate       : {logger.BLUE}{total_rate:>5.1f}%{logger.RESET} ({qc_size}/{period_size} valid periods)")

    return {
        'acquisition_rate': sample_rate,
        'yield_rate': valid_rate,
        'total_rate': total_rate
    }
