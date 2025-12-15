from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd


# =============================================================================
# QC Flag System
# =============================================================================

@dataclass
class QCRule:
    """
    Declarative QC rule definition.

    Parameters
    ----------
    name : str
        Short identifier for the flag (e.g., 'Status Error')
    condition : Callable[[pd.DataFrame], pd.Series]
        Function that takes DataFrame and returns boolean Series
        where True = flagged (problematic data)
    description : str, optional
        Detailed explanation of what this rule checks

    Examples
    --------
    >>> rule = QCRule(
    ...     name='Invalid BC',
    ...     condition=lambda df: (df['BC6'] <= 0) | (df['BC6'] > 20000),
    ...     description='BC concentration outside valid range 0-20000 ng/m³'
    ... )
    """
    name: str
    condition: Callable[[pd.DataFrame], pd.Series]
    description: str = ''


class QCFlagBuilder:
    """
    Centralized QC flag aggregation system.

    This class collects multiple QC rules and applies them efficiently
    using vectorized operations, producing a single QC_Flag column.

    Examples
    --------
    >>> builder = QCFlagBuilder()
    >>> builder.add_rule(QCRule('Invalid Value', lambda df: df['value'] < 0))
    >>> builder.add_rule(QCRule('Missing Data', lambda df: df['value'].isna()))
    >>> df_with_flags = builder.apply(df)
    """

    def __init__(self):
        self.rules: list[QCRule] = []

    def add_rule(self, rule: QCRule) -> 'QCFlagBuilder':
        """Add a QC rule. Returns self for method chaining."""
        self.rules.append(rule)
        return self

    def add_rules(self, rules: list[QCRule]) -> 'QCFlagBuilder':
        """Add multiple QC rules. Returns self for method chaining."""
        self.rules.extend(rules)
        return self

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all registered QC rules and add QC_Flag column.

        Parameters
        ----------
        df : pd.DataFrame
            Input DataFrame to apply QC rules to

        Returns
        -------
        pd.DataFrame
            DataFrame with added 'QC_Flag' column containing
            comma-separated flag names or 'Valid'
        """
        if not self.rules:
            df = df.copy()
            df['QC_Flag'] = 'Valid'
            return df

        # Create a mask DataFrame: each column is a boolean mask for one rule
        # This is much faster than iterating row by row
        flag_masks = {}
        for rule in self.rules:
            try:
                mask = rule.condition(df)
                if isinstance(mask, pd.Series):
                    flag_masks[rule.name] = mask
                else:
                    # Handle scalar or array results
                    flag_masks[rule.name] = pd.Series(mask, index=df.index)
            except Exception as e:
                print(f"Warning: QC rule '{rule.name}' failed: {e}")
                flag_masks[rule.name] = pd.Series(False, index=df.index)

        # Convert to DataFrame for vectorized string operations
        mask_df = pd.DataFrame(flag_masks)

        # Build flag strings efficiently using numpy
        def build_flag_string(row):
            flags = [col for col, val in row.items() if val]
            return ', '.join(flags) if flags else 'Valid'

        # Apply vectorized where possible, fallback to apply for string building
        df = df.copy()
        df['QC_Flag'] = mask_df.apply(build_flag_string, axis=1)

        return df

    def get_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get summary statistics of QC flags.

        Returns DataFrame with counts and percentages for each flag.
        """
        results = []
        total = len(df)
        flagged_mask = pd.Series(False, index=df.index)

        for rule in self.rules:
            try:
                mask = rule.condition(df)
                flagged_mask |= mask
                count = mask.sum()
                results.append({
                    'Rule': rule.name,
                    'Count': count,
                    'Percentage': f'{count / total * 100:.1f}%',
                    'Description': rule.description
                })
            except Exception:
                results.append({
                    'Rule': rule.name,
                    'Count': 'Error',
                    'Percentage': '-',
                    'Description': rule.description
                })

        # Add Valid count
        valid_count = (~flagged_mask).sum()
        results.append({
            'Rule': 'Valid',
            'Count': valid_count,
            'Percentage': f'{valid_count / total * 100:.1f}%',
            'Description': 'Passed all QC checks'
        })

        return pd.DataFrame(results)


class QualityControl:
    """A class providing various methods for data quality control and outlier detection"""

    @staticmethod
    def _ensure_dataframe(df: pd.DataFrame | pd.Series) -> pd.DataFrame:
        """Ensure input data is in DataFrame format"""
        return df.to_frame() if isinstance(df, pd.Series) else df

    @staticmethod
    def _transform_if_log(df: pd.DataFrame, log_dist: bool) -> pd.DataFrame:
        """Transform data to log scale if required"""
        return np.log10(df) if log_dist else df

    @classmethod
    def n_sigma(cls, df: pd.DataFrame, std_range: int = 5) -> pd.DataFrame:
        """
        Detect outliers using n-sigma method

        Parameters
        ----------
        df : pd.DataFrame
            Input data
        std_range : int, default=5
            Number of standard deviations to use as threshold

        Returns
        -------
        pd.DataFrame
            Cleaned DataFrame with outliers masked as NaN
        """
        df = cls._ensure_dataframe(df)
        df_ave = df.mean()
        df_std = df.std()

        lower_bound = df < (df_ave - df_std * std_range)
        upper_bound = df > (df_ave + df_std * std_range)

        return df.mask(lower_bound | upper_bound)

    @classmethod
    def iqr(cls, df: pd.DataFrame, log_dist: bool = False) -> pd.DataFrame:
        """
        Detect outliers using Interquartile Range (IQR) method

        Parameters
        ----------
        df : pd.DataFrame
            Input data
        log_dist : bool, default=False
            Whether to apply log transformation to data

        Returns
        -------
        pd.DataFrame
            Cleaned DataFrame with outliers masked as NaN
        """
        df = cls._ensure_dataframe(df)
        df_transformed = cls._transform_if_log(df, log_dist)

        q1 = df_transformed.quantile(0.25)
        q3 = df_transformed.quantile(0.75)
        iqr = q3 - q1

        lower_bound = df_transformed < (q1 - 1.5 * iqr)
        upper_bound = df_transformed > (q3 + 1.5 * iqr)

        return df.mask(lower_bound | upper_bound)

    @classmethod
    def time_aware_rolling_iqr(cls, df: pd.DataFrame, window_size: str = '24h',
                               log_dist: bool = False, iqr_factor: float = 5,
                               min_periods: int = 5) -> pd.DataFrame:
        """
        Detect outliers using rolling time-aware IQR method with handling for initial periods

        Parameters
        ----------
        df : pd.DataFrame
            Input data
        window_size : str, default='24h'
            Size of the rolling window
        log_dist : bool, default=False
            Whether to apply log transformation to data
        iqr_factor : float, default=3
            The factor by which to multiply the IQR
        min_periods : int, default=4
            Minimum number of observations required in window

        Returns
        -------
        pd.DataFrame
            Cleaned DataFrame with outliers masked as NaN
        """
        df = cls._ensure_dataframe(df)
        df_transformed = cls._transform_if_log(df, log_dist)

        # Create result DataFrame
        result = pd.DataFrame(index=df.index)

        # Apply rolling IQR to each column
        for col in df_transformed.columns:
            series = df_transformed[col]

            # Calculate global IQR for initial values
            global_q1 = series.quantile(0.25)
            global_q3 = series.quantile(0.75)
            global_iqr = global_q3 - global_q1

            global_lower = global_q1 - iqr_factor * global_iqr
            global_upper = global_q3 + iqr_factor * global_iqr

            # Calculate rolling IQR
            rolling_q1 = series.rolling(window_size, min_periods=min_periods).quantile(0.25)
            rolling_q3 = series.rolling(window_size, min_periods=min_periods).quantile(0.75)
            rolling_iqr = rolling_q3 - rolling_q1

            # Calculate dynamic thresholds
            lower_bound = rolling_q1 - iqr_factor * rolling_iqr
            upper_bound = rolling_q3 + iqr_factor * rolling_iqr

            # Use global thresholds for initial NaN values
            lower_bound = lower_bound.fillna(global_lower)
            upper_bound = upper_bound.fillna(global_upper)

            # Mark data points within thresholds
            mask = (series >= lower_bound) & (series <= upper_bound)
            result[col] = mask

        # Set values in original data that don't meet conditions to NaN
        return df.where(result, np.nan)

    def time_aware_std_QC(self, df: pd.DataFrame, time_window: str = '6h',
                          std_factor: float = 3.0, min_periods: int = 4) -> pd.DataFrame:
        """
        Time-aware outlier detection using rolling standard deviation

        Parameters
        ----------
        df : pd.DataFrame
            Input data
        time_window : str, default='6h'
            Rolling window size
        std_factor : float, default=3.0
            Standard deviation multiplier (e.g., 3 means 3σ)
        min_periods : int, default=4
            Minimum number of observations required in window

        Returns
        -------
        pd.DataFrame
            Quality controlled DataFrame with outliers marked as NaN
        """
        df = self._ensure_dataframe(df)

        # Create result DataFrame
        result = pd.DataFrame(index=df.index)

        # Apply rolling standard deviation to each column
        for col in df.columns:
            series = df[col]

            # Calculate global standard deviation for initial values
            global_mean = series.mean()
            global_std = series.std()

            global_lower = global_mean - std_factor * global_std
            global_upper = global_mean + std_factor * global_std

            # Calculate rolling mean and standard deviation
            rolling_mean = series.rolling(time_window, min_periods=min_periods).mean()
            rolling_std = series.rolling(time_window, min_periods=min_periods).std()

            # Calculate dynamic thresholds
            lower_bound = rolling_mean - std_factor * rolling_std
            upper_bound = rolling_mean + std_factor * rolling_std

            # Use global thresholds for initial NaN values
            lower_bound = lower_bound.fillna(global_lower)
            upper_bound = upper_bound.fillna(global_upper)

            # Mark data points within thresholds
            mask = (series >= lower_bound) & (series <= upper_bound)
            result[col] = mask

        # Set values in original data that don't meet conditions to NaN
        return df.where(result, np.nan)

    @classmethod
    def bidirectional_trend_std_QC(cls, df: pd.DataFrame, window_size: str = '6h',
                                   std_factor: float = 3.0, trend_window: str = '30min',
                                   trend_factor: float = 2, min_periods: int = 4) -> pd.Series:
        """
        Perform quality control using standard deviation with awareness of both upward and downward trends.

        This method identifies outliers considering both upward and downward trends in the data,
        applying more lenient criteria when consistent trends are detected.

        Parameters
        ----------
        df : pd.DataFrame
            Input data frame with time series (QC_Flag column is now optional)
        window_size : str, default='6h'
            Size of the rolling window for std calculation
        std_factor : float, default=3.0
            Base factor for standard deviation threshold
        trend_window : str, default='30min'
            Window for trend detection
        trend_factor : float, default=2
            Factor to increase std_factor when trends are detected
        min_periods : int, default=4
            Minimum number of observations in window

        Returns
        -------
        pd.Series
            Boolean mask where True indicates outliers
        """
        df = cls._ensure_dataframe(df)

        # 使用預先分配的 NumPy 數組，而不是 pandas Series
        index = df.index
        n_rows = len(index)
        outlier_array = np.zeros(n_rows, dtype=bool)  # 更高效的初始化

        # 只處理數值列，跳過 QC_Flag 等非數值列
        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()  # 轉為 list 以提高索引性能

        # 預先計算滾動窗口大小（以點數而非時間表示）
        # 這僅適用於固定頻率的數據，若數據不規則則保持原始時間窗口
        try:
            if hasattr(df.index, 'freq') and df.index.freq is not None:
                # 將時間窗口轉換為點數
                window_points = int(pd.Timedelta(window_size) / df.index.freq)
                trend_points = int(pd.Timedelta(trend_window) / df.index.freq)
                use_points = True
            else:
                # 嘗試計算平均時間間隔
                if isinstance(df.index, pd.DatetimeIndex) and len(df.index) > 1:
                    avg_interval = (df.index[-1] - df.index[0]) / (len(df.index) - 1)
                    window_points = int(pd.Timedelta(window_size) / avg_interval)
                    trend_points = int(pd.Timedelta(trend_window) / avg_interval)
                    use_points = True
                else:
                    use_points = False
                    window_points = None
                    trend_points = None
        except:
            use_points = False
            window_points = None
            trend_points = None

        # 預編譯趨勢計算函數使用 numba (如果可用)
        try:
            import numba

            @numba.jit(nopython=True)
            def calc_trend_numba(values):
                n = len(values)
                if n > 3:
                    # 使用更高效的線性回歸實現
                    x = np.arange(n)
                    sum_x = np.sum(x)
                    sum_y = np.sum(values)
                    sum_xx = np.sum(x * x)
                    sum_xy = np.sum(x * values)

                    # 計算斜率
                    denom = (n * sum_xx - sum_x * sum_x)
                    if denom != 0:
                        slope = (n * sum_xy - sum_x * sum_y) / denom
                        return slope
                return 0.0

            use_numba = True
        except ImportError:
            use_numba = False

            # 回退函數
            def calc_trend_numba(values):
                n = len(values)
                if n > 3:
                    try:
                        return np.polyfit(range(len(values)), values, 1)[0]
                    except:
                        return 0
                return 0

        # 使用並行處理每列
        try:
            from concurrent.futures import ThreadPoolExecutor
            from functools import partial

            def process_column(col, df, use_points, window_points, trend_points, std_factor,
                               min_periods, trend_factor, use_numba):
                # 從 DataFrame 中提取該列
                if isinstance(df, pd.DataFrame):
                    series = df[col].values
                else:
                    # 如果直接傳入了 Series
                    series = df.values

                # 處理 NaN 值
                valid_mask = ~np.isnan(series)
                valid_indices = np.where(valid_mask)[0]

                if len(valid_indices) < min_periods:
                    return np.zeros(len(series), dtype=bool)

                # 全局統計量只使用有效值計算
                valid_values = series[valid_mask]
                global_mean = np.mean(valid_values)
                global_std = np.std(valid_values)
                if global_std == 0:
                    global_std = 1e-6  # 避免除零

                # 初始化結果數組
                col_outlier_mask = np.zeros(len(series), dtype=bool)

                # 滾動統計量計算
                # 對於基於索引的滾動計算
                if use_points and window_points is not None and window_points > 0:
                    # 初始化數組
                    rolling_mean = np.full_like(series, np.nan, dtype=float)
                    rolling_std = np.full_like(series, np.nan, dtype=float)
                    trends = np.full_like(series, np.nan, dtype=float)
                    trend_significance = np.full_like(series, np.nan, dtype=float)

                    # 手動實現滾動窗口
                    for i in valid_indices:
                        # 滾動均值和標準差
                        start_idx = max(0, i - window_points + 1)
                        window_vals = series[start_idx:i + 1]
                        valid_window = window_vals[~np.isnan(window_vals)]

                        if len(valid_window) >= min_periods:
                            rolling_mean[i] = np.mean(valid_window)
                            rolling_std[i] = np.std(valid_window)

                        # 趨勢計算
                        if trend_points > 0:
                            trend_start = max(0, i - trend_points + 1)
                            trend_vals = series[trend_start:i + 1]
                            valid_trend = trend_vals[~np.isnan(trend_vals)]

                            if len(valid_trend) >= 3:
                                # 使用 numba 加速的趨勢計算
                                trends[i] = calc_trend_numba(valid_trend)
                                trend_std = np.std(valid_trend)
                                if trend_std > 0:
                                    trend_significance[i] = abs(trends[i]) / trend_std

                    # 計算滾動變化率
                    pct_change = np.full_like(series, np.nan, dtype=float)
                    for i in range(1, len(series)):
                        if not np.isnan(series[i]) and not np.isnan(series[i - 1]) and series[i - 1] != 0:
                            pct_change[i] = abs((series[i] - series[i - 1]) / series[i - 1])

                    # 滾動平均變化率
                    avg_change_rates = np.full_like(series, np.nan, dtype=float)
                    for i in valid_indices:
                        if trend_points > 0:
                            rate_start = max(0, i - trend_points + 1)
                            rate_vals = pct_change[rate_start:i + 1]
                            valid_rates = rate_vals[~np.isnan(rate_vals)]

                            if len(valid_rates) >= 3:
                                avg_change_rates[i] = np.mean(valid_rates)
                else:
                    # 使用 pandas 的滾動窗口（對於時間索引數據）
                    # 注意：這裡我們實際上需要創建一個具有時間索引的臨時 Series
                    temp_series = pd.Series(series, index=df.index)

                    # 計算滾動統計量
                    rolling_mean = temp_series.rolling(window_size, min_periods=min_periods).mean().values
                    rolling_std = temp_series.rolling(window_size, min_periods=min_periods).std().values

                    # 趨勢計算
                    if use_numba:
                        # 使用 apply + numba
                        trend_series = temp_series.rolling(trend_window, min_periods=3).apply(
                            lambda x: calc_trend_numba(x.values))
                    else:
                        # 使用內建的 apply + polyfit
                        trend_series = temp_series.rolling(trend_window, min_periods=3).apply(
                            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 3 else 0)

                    trends = trend_series.values

                    # 計算趨勢顯著性
                    series_std = temp_series.rolling(trend_window, min_periods=3).std().values
                    trend_significance = np.zeros_like(trends)
                    for i in range(len(trends)):
                        if not np.isnan(trends[i]) and not np.isnan(series_std[i]) and series_std[i] > 0:
                            trend_significance[i] = abs(trends[i]) / series_std[i]
                        elif not np.isnan(trends[i]):
                            trend_significance[i] = abs(trends[i]) / (global_std * 0.1)

                    # 計算變化率
                    pct_change = temp_series.pct_change(fill_method=None).abs().values

                    # 重用 temp_series 計算滾動平均變化率
                    temp_change_series = pd.Series(pct_change, index=df.index)
                    avg_change_rates = temp_change_series.rolling(trend_window, min_periods=3).mean().values

                # 動態調整標準差因子
                dynamic_factor = np.full(len(series), std_factor)
                for i in valid_indices:
                    if not np.isnan(trend_significance[i]) and trend_significance[i] > 0.1:
                        dynamic_factor[i] = std_factor * trend_factor

                # 調整極低標準差
                min_std = global_std * 0.1
                adjusted_std = np.copy(rolling_std)
                for i in valid_indices:
                    if not np.isnan(adjusted_std[i]) and adjusted_std[i] < min_std:
                        adjusted_std[i] = min_std

                # 計算閾值
                lower_bound = np.full_like(series, np.nan, dtype=float)
                upper_bound = np.full_like(series, np.nan, dtype=float)

                for i in valid_indices:
                    if not np.isnan(rolling_mean[i]) and not np.isnan(adjusted_std[i]):
                        lower_bound[i] = rolling_mean[i] - dynamic_factor[i] * adjusted_std[i]
                        upper_bound[i] = rolling_mean[i] + dynamic_factor[i] * adjusted_std[i]
                    else:
                        # 使用全局統計量
                        lower_bound[i] = global_mean - std_factor * global_std
                        upper_bound[i] = global_mean + std_factor * global_std

                # 標記超出閾值的點
                for i in valid_indices:
                    if not (lower_bound[i] <= series[i] <= upper_bound[i]):
                        col_outlier_mask[i] = True

                # 趨勢一致性檢查
                trend_consistent = np.zeros_like(col_outlier_mask, dtype=bool)
                for i in valid_indices:
                    if i > 0 and not np.isnan(pct_change[i]) and not np.isnan(avg_change_rates[i]):
                        trend_consistent[i] = pct_change[i] <= (avg_change_rates[i] * 3)

                # 顯著趨勢檢查
                significant_trend_mask = np.zeros_like(col_outlier_mask, dtype=bool)
                for i in valid_indices:
                    if not np.isnan(trend_significance[i]) and trend_significance[i] > 0.1:
                        significant_trend_mask[i] = True

                # 最終掩碼：僅當點超出範圍且不符合顯著趨勢時才標記為異常
                col_final_mask = col_outlier_mask.copy()
                for i in valid_indices:
                    if col_outlier_mask[i] and trend_consistent[i] and significant_trend_mask[i]:
                        col_final_mask[i] = False

                return col_final_mask

            # 嘗試使用並行處理
            with ThreadPoolExecutor(max_workers=min(4, len(numeric_cols))) as executor:
                col_results = list(executor.map(
                    partial(process_column, df=df, use_points=use_points,
                            window_points=window_points, trend_points=trend_points,
                            std_factor=std_factor, min_periods=min_periods,
                            trend_factor=trend_factor, use_numba=use_numba),
                    numeric_cols))

            # 合併結果
            for col_mask in col_results:
                outlier_array = outlier_array | col_mask

        except Exception as e:
            # 如果並行處理失敗，回退到原始實現
            print(f"Warning: Parallel processing failed, falling back to original implementation. Error: {e}")

            # 創建結果掩碼 - 初始全部為 False (不是異常值)
            outlier_mask = pd.Series(False, index=df.index)

            for col in numeric_cols:
                series = df[col]

                # 計算全局統計量
                global_mean = series.mean()
                global_std = series.std()

                # 檢測趨勢方向和強度
                def calc_trend(x):
                    if len(x) > 3:
                        try:
                            return np.polyfit(range(len(x)), x, 1)[0]
                        except:
                            return 0
                    return 0

                trend = series.rolling(trend_window, min_periods=3).apply(calc_trend)

                # 計算趨勢顯著性
                series_std = series.rolling(trend_window, min_periods=3).std()
                # 避免除以零
                trend_significance = np.abs(trend) / series_std.replace(0, np.nan).fillna(global_std * 0.1)

                # 動態因子調整
                dynamic_factor = pd.Series(std_factor, index=df.index)
                significant_trend = trend_significance > 0.1
                dynamic_factor[significant_trend] = std_factor * trend_factor

                # 計算滾動統計量
                rolling_mean = series.rolling(window_size, min_periods=min_periods).mean()
                rolling_std = series.rolling(window_size, min_periods=min_periods).std()

                # 調整極低標準差
                min_std_threshold = global_std * 0.1
                adjusted_std = rolling_std.clip(lower=min_std_threshold)

                # 計算閾值
                lower_bound = rolling_mean - dynamic_factor * adjusted_std
                upper_bound = rolling_mean + dynamic_factor * adjusted_std

                # 填充初始 NaN 值
                lower_bound = lower_bound.fillna(global_mean - std_factor * global_std)
                upper_bound = upper_bound.fillna(global_mean + std_factor * global_std)

                # 檢查變化率一致性
                rate_of_change = series.pct_change(fill_method=None).abs()
                avg_change_rate = rate_of_change.rolling(trend_window, min_periods=3).mean()

                # 標記異常值
                col_outlier_mask = ~((series >= lower_bound) & (series <= upper_bound))
                trend_consistent = rate_of_change <= (avg_change_rate * 3)

                # 最終掩碼：只有當點超出範圍且不屬於一致趨勢時才標記為異常
                col_final_outlier_mask = col_outlier_mask & ~(col_outlier_mask & trend_consistent & significant_trend)

                # 更新總掩碼 - 如果任一列有異常，則標記為異常
                outlier_mask = outlier_mask | col_final_outlier_mask

            return outlier_mask

        # 轉換回 pandas Series
        return pd.Series(outlier_array, index=index)
    
    @staticmethod
    def filter_error_status(_df, error_codes, special_codes=None, return_mask=True):
        """
        Filter data based on error status codes.

        Parameters
        ----------
        _df : pd.DataFrame
            Input DataFrame
        error_codes : list or array-like
            Codes indicating errors
        special_codes : list or array-like, optional
            Special codes to handle differently
        return_mask : bool, default=True
            If True, returns a boolean mask where True indicates errors;
            If False, returns filtered DataFrame

        Returns
        -------
        Union[pd.DataFrame, pd.Series]
            If return_mask=True: boolean Series with True for error points
            If return_mask=False: Filtered DataFrame with error points masked
        """
        # Create an empty mask
        error_mask = pd.Series(False, index=_df.index)

        # Convert Status to integer (if it's not already)
        status_values = pd.to_numeric(_df['Status'], errors='coerce').fillna(0).astype(int)

        # Bitwise test normal error codes
        for code in error_codes:
            # Use bitwise operation on the integer-converted status_values
            error_mask = error_mask | ((status_values & code) != 0)

        # Exact matching for special codes
        if special_codes:
            error_mask = error_mask | status_values.isin(special_codes)

        # Return either the mask or the filtered DataFrame
        if return_mask:
            return error_mask
        else:
            return _df.mask(error_mask)

    @classmethod
    def spike_detection(cls, df: pd.DataFrame,
                        max_change_rate: float = 3.0,
                        min_abs_change: float = None) -> pd.Series:
        """
        Vectorized spike detection using change rate analysis.

        Detects sudden unreasonable value changes while allowing legitimate
        gradual changes during events (pollution episodes, etc.).

        This method is much faster than rolling window methods because it uses
        pure numpy vectorized operations.

        Parameters
        ----------
        df : pd.DataFrame
            Input data frame with time series
        max_change_rate : float, default=3.0
            Maximum allowed ratio of current change to median absolute change.
            Higher values = more permissive. A value of 3.0 means a change
            must be 3x larger than the median change to be flagged.
        min_abs_change : float, optional
            Minimum absolute change required to be considered a spike.
            If None, uses 10% of the data's standard deviation.

        Returns
        -------
        pd.Series
            Boolean mask where True indicates detected spikes

        Notes
        -----
        The algorithm:
        1. Calculate absolute difference between consecutive points
        2. Calculate the median absolute change (robust baseline)
        3. Flag points where change > max_change_rate * median_change
        4. Also detect "reversals" (spike up then immediately down)

        This approach allows gradual changes during events while catching
        sudden spikes that are likely instrument errors.

        Examples
        --------
        >>> qc = QualityControl()
        >>> spike_mask = qc.spike_detection(df, max_change_rate=3.0)
        """
        df = cls._ensure_dataframe(df)

        # Initialize result mask
        spike_mask = pd.Series(False, index=df.index)

        # Process each numeric column
        numeric_cols = df.select_dtypes(include=np.number).columns

        for col in numeric_cols:
            values = df[col].values
            n = len(values)

            if n < 3:
                continue

            # Calculate absolute differences (vectorized)
            diff = np.abs(np.diff(values))

            # Handle NaN values
            valid_diff = diff[~np.isnan(diff)]

            if len(valid_diff) < 3:
                continue

            # Calculate median absolute change (robust measure)
            median_change = np.median(valid_diff)

            # Set minimum threshold
            if min_abs_change is None:
                # Use 10% of std as minimum meaningful change
                std_val = np.nanstd(values)
                min_threshold = std_val * 0.1
            else:
                min_threshold = min_abs_change

            # Ensure median_change is not too small
            if median_change < min_threshold:
                median_change = min_threshold

            # Calculate spike threshold
            spike_threshold = max_change_rate * median_change

            # Detect spikes: diff[i] is the change from values[i] to values[i+1]
            # So spike at index i+1 if diff[i] > threshold
            large_changes = diff > spike_threshold

            # Detect reversals: sudden up then immediate down (or vice versa)
            # A reversal at index i means: sign(diff[i-1]) != sign(diff[i])
            # and both changes are large
            signed_diff = np.diff(values)  # Keep sign for reversal detection

            # Reversal detection (vectorized)
            # Check if consecutive changes have opposite signs and both are significant
            if len(signed_diff) >= 2:
                sign_change = signed_diff[:-1] * signed_diff[1:] < 0  # Opposite signs
                both_large = (np.abs(signed_diff[:-1]) > spike_threshold * 0.5) & \
                            (np.abs(signed_diff[1:]) > spike_threshold * 0.5)
                reversals = sign_change & both_large

                # Mark the middle point of a reversal as spike
                # reversals[i] indicates reversal at values[i+1]
                col_spike_mask = np.zeros(n, dtype=bool)

                # Large changes: mark the point after the change
                col_spike_mask[1:] = large_changes

                # Reversals: mark the middle point (already aligned to i+1)
                col_spike_mask[1:-1] = col_spike_mask[1:-1] | reversals
            else:
                col_spike_mask = np.zeros(n, dtype=bool)
                col_spike_mask[1:] = large_changes

            # Update overall mask
            spike_mask = spike_mask | pd.Series(col_spike_mask, index=df.index)

        return spike_mask

    @classmethod
    def hourly_completeness_QC(cls, df: pd.DataFrame, freq: str,
                               threshold: float = 0.5) -> pd.Series:
        """
        Check if each hour has sufficient data points.

        Parameters
        ----------
        df : pd.DataFrame
            Input data frame with time series
        freq : str
            Data frequency (e.g., '6min')
        threshold : float, default=0.5
            Minimum required proportion of data points per hour (0-1)

        Returns
        -------
        pd.Series
            Boolean mask where True indicates insufficient data
        """
        # Ensure input is DataFrame
        df = cls._ensure_dataframe(df)

        # Create result mask
        completeness_mask = pd.Series(False, index=df.index)

        # Calculate expected data points per hour
        points_per_hour = pd.Timedelta('1h') / pd.Timedelta(freq)
        min_points = points_per_hour * threshold

        # Only process numeric columns
        numeric_cols = df.select_dtypes(include=np.number).columns

        for col in numeric_cols:
            # Calculate actual data points per hour
            hourly_count = df[col].dropna().resample('1h').size().reindex(df.index).ffill()

            # Mark points with insufficient data
            insufficient_mask = hourly_count < min_points
            completeness_mask = completeness_mask | insufficient_mask

        return completeness_mask
