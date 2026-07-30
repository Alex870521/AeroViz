from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd


# =============================================================================
# QC Flag System
# =============================================================================

#: A rule's verdict is either *invalidating* (the measurement itself cannot be
#: trusted) or *advisory* (the measurement stands, but something about it is worth
#: knowing). Only invalidating flags cause the row to be masked in the public
#: output; both are always recorded in ``QC_Flag`` and in the summary.
ERROR = 'error'
WARNING = 'warning'
SEVERITIES = (ERROR, WARNING)


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
    severity : {'error', 'warning'}, default='error'
        ``'error'`` — the measurement is invalid; the row is masked to NaN in the
        public output and does not count towards the yield rate.
        ``'warning'`` — advisory: the value is a real measurement and is kept.
        Use it when the flag describes a *circumstance* rather than a broken
        reading (below a detection limit, an upscale warning, a sparse hour).
        Default is ``'error'`` so a new rule is conservative until classified.

    Examples
    --------
    >>> rule = QCRule(
    ...     name='Invalid BC',
    ...     condition=lambda df: (df['BC6'] <= 0) | (df['BC6'] > 20000),
    ...     description='BC concentration outside valid range 0-20000 ng/m³'
    ... )
    >>> advisory = QCRule(
    ...     name='Below MDL',
    ...     condition=lambda df: df['Thermal_OC'] <= 0.3,
    ...     description='At or below the method detection limit',
    ...     severity='warning',
    ... )
    """
    name: str
    condition: Callable[[pd.DataFrame], pd.Series]
    description: str = ''
    severity: str = ERROR

    def __post_init__(self):
        if self.severity not in SEVERITIES:
            raise ValueError(
                f"QCRule('{self.name}') has severity={self.severity!r}; "
                f"expected one of {SEVERITIES}")


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

    #: Column holding the human-readable record of every rule that fired.
    FLAG_COLUMN = 'QC_Flag'
    #: Boolean column holding the *verdict*: True when at least one
    #: invalidating rule fired. This is what the presentation layer masks on —
    #: keeping it separate from ``QC_Flag`` means an advisory flag can be
    #: recorded without deleting the measurement.
    INVALID_COLUMN = 'QC_Invalid'

    def __init__(self, severity_overrides: dict | None = None, logger=None,
                 extra_flags: tuple[str, ...] = ()):
        """
        Parameters
        ----------
        severity_overrides : dict, optional
            ``{rule_name: 'error' | 'warning'}``, applied when the builder runs.
            Lets a caller reclassify a rule for one run (e.g. treat
            ``'Insufficient'`` as advisory) without editing the reader.
        logger : optional
            Where to report a rule that raises. Defaults to ``print``, which is
            easy to miss in a long read — pass the reader's logger so the failure
            lands in the log file alongside the QC summary.
        extra_flags : tuple of str, optional
            Flags the reader raises *after* this builder runs, through
            `AbstractReader.update_qc_flag` (e.g. ``'Invalid AAE'``). They are not
            rules here, but an override naming one is still legitimate, so they
            count as known names when the override keys are checked.
        """
        self.rules: list[QCRule] = []
        self.severity_overrides = dict(severity_overrides or {})
        self.logger = logger
        self.extra_flags = tuple(extra_flags)

    def known_flags(self) -> set[str]:
        """Every flag name an override may legitimately name."""
        return {rule.name for rule in self.rules} | set(self.extra_flags)

    def _check_override_names(self) -> None:
        """Reject an override that names no rule this instrument actually has.

        An unknown key used to be silently ignored, so a typo — or a rule name
        borrowed from a different instrument — looked like it had been applied
        while QC carried on unchanged.
        """
        unknown = set(self.severity_overrides) - self.known_flags()
        if unknown:
            raise ValueError(
                f"flag_severity names no QC rule of this instrument: {sorted(unknown)}. "
                f"Available: {sorted(self.known_flags())}")

    def add_rule(self, rule: QCRule) -> 'QCFlagBuilder':
        """Add a QC rule. Returns self for method chaining."""
        self.rules.append(rule)
        return self

    def add_rules(self, rules: list[QCRule]) -> 'QCFlagBuilder':
        """Add multiple QC rules. Returns self for method chaining."""
        self.rules.extend(rules)
        return self

    def severity_of(self, rule: QCRule) -> str:
        """Effective severity of ``rule``, honouring the override map."""
        override = self.severity_overrides.get(rule.name)
        if override is None:
            return rule.severity
        if override not in SEVERITIES:
            raise ValueError(
                f"severity override for '{rule.name}' is {override!r}; "
                f"expected one of {SEVERITIES}")
        return override

    def _evaluate(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Run every rule once, returning ``{rule name: boolean mask}``.

        A rule that raises is reported and treated as "did not fire", so one
        broken rule cannot take the whole read down.
        """
        masks = {}
        for rule in self.rules:
            try:
                mask = rule.condition(df)
                if not isinstance(mask, pd.Series):
                    # Handle scalar or array results
                    mask = pd.Series(mask, index=df.index)
                masks[rule.name] = mask.reindex(df.index).fillna(False).astype(bool)
            except Exception as e:
                # A rule that raises is disabled for this run, which quietly
                # weakens QC — say so where it will be seen.
                message = (f"QC rule '{rule.name}' failed and was skipped "
                           f"({type(e).__name__}: {e}). Data that this rule would "
                           f"have flagged is passing QC unchecked.")
                if self.logger is not None:
                    self.logger.warning(message)
                else:
                    print(f"Warning: {message}")
                masks[rule.name] = pd.Series(False, index=df.index)
        return masks

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all registered QC rules; add ``QC_Flag`` and ``QC_Invalid``.

        Parameters
        ----------
        df : pd.DataFrame
            Input DataFrame to apply QC rules to

        Returns
        -------
        pd.DataFrame
            DataFrame with two added columns:

            ``QC_Flag``
                comma-separated names of every rule that fired (advisory ones
                included), or ``'Valid'`` when none did.
            ``QC_Invalid``
                True when at least one *invalidating* rule fired. Rows where this
                is False keep their values in the public output even if an
                advisory flag is recorded against them.
        """
        df = df.copy()
        self._check_override_names()

        if not self.rules:
            df[self.FLAG_COLUMN] = 'Valid'
            df[self.INVALID_COLUMN] = False
            return df

        masks = self._evaluate(df)

        # Vectorised flag-string assembly: start from 'Valid' and append each
        # rule's name to the rows it fired on.
        flag = pd.Series('', index=df.index, dtype='object')
        invalid = pd.Series(False, index=df.index)

        for rule in self.rules:
            mask = masks[rule.name]
            flag = flag.mask(mask, flag.where(flag == '', flag + ', ') + rule.name)
            if self.severity_of(rule) == ERROR:
                invalid |= mask

        df[self.FLAG_COLUMN] = flag.where(flag != '', 'Valid')
        df[self.INVALID_COLUMN] = invalid

        return df

    def get_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get summary statistics of QC flags.

        Returns a DataFrame with one row per rule (count, percentage, severity,
        description), then two totals: ``Valid`` — passed every check — and
        ``Usable`` — no *invalidating* flag, i.e. what survives into the output.
        The two differ by exactly the rows carrying only advisory flags.
        """
        results = []
        total = len(df) or 1  # avoid ZeroDivisionError on an empty frame
        masks = self._evaluate(df)

        flagged = pd.Series(False, index=df.index)
        invalid = pd.Series(False, index=df.index)

        for rule in self.rules:
            mask = masks[rule.name]
            severity = self.severity_of(rule)
            flagged |= mask
            if severity == ERROR:
                invalid |= mask
            count = int(mask.sum())
            results.append({
                'Rule': rule.name,
                'Count': count,
                'Percentage': f'{count / total * 100:.1f}%',
                'Severity': severity,
                'Description': rule.description,
            })

        valid_count = int((~flagged).sum())
        results.append({
            'Rule': 'Valid',
            'Count': valid_count,
            'Percentage': f'{valid_count / total * 100:.1f}%',
            'Severity': '',
            'Description': 'Passed all QC checks',
        })

        usable_count = int((~invalid).sum())
        results.append({
            'Rule': 'Usable',
            'Count': usable_count,
            'Percentage': f'{usable_count / total * 100:.1f}%',
            'Severity': '',
            'Description': 'No invalidating flag — kept in the output',
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
    def filter_error_status(_df, error_codes=None, special_codes=None, return_mask=True,
                            status_column='Status', status_type='bitwise', ok_value=None,
                            ignored_values=None):
        """
        Filter data based on error status codes.

        Parameters
        ----------
        _df : pd.DataFrame
            Input DataFrame
        error_codes : list or array-like, optional
            Codes indicating errors (for 'bitwise' type)
        special_codes : list or array-like, optional
            Special codes to handle differently (exact match)
        return_mask : bool, default=True
            If True, returns a boolean mask where True indicates errors;
            If False, returns filtered DataFrame
        status_column : str, default='Status'
            Name of the status column in DataFrame
        status_type : str, default='bitwise'
            Type of status check:
            - 'bitwise': Use bitwise AND to check error codes (AE33, AE43, BC1054, MA350)
            - 'numeric': Check if status != ok_value (TEOM, Aurora, NEPH)
            - 'text': Check if status != ok_value as string (SMPS)
            - 'binary_string': Parse binary string and check if > 0 (APS)
        ok_value : any, optional
            The value indicating OK status (for 'numeric', 'text' types)
            - For 'numeric': typically 0
            - For 'text': typically 'Normal Scan'
        ignored_values : list, optional
            Whitelist of statuses to suppress (treat as OK) without editing the
            raw files — e.g. an operator-known benign warning. Interpretation is
            mode-specific; entries that don't fit a mode are silently skipped so
            a whitelist meant for one instrument is harmless if it reaches
            another. Defaults to None (no whitelist; behaviour unchanged).

            - ``'text'``          : string tokens. The status is comma-split and
              a row passes when every token is ``ok_value`` or whitelisted. A
              token ``'Low aerosol flow'`` matches both the bare string and
              combined statuses like ``'Low aerosol flow,Neutralizer not
              active'`` (when both tokens are whitelisted).
            - ``'numeric'``       : numeric status codes treated as OK in
              addition to ``ok_value`` (e.g. ``[4, 16]``).
            - ``'bitwise'``       : integer error codes/bits dropped from the
              error definition; a row is flagged only if a NON-whitelisted code
              still matches (token-level, mirroring text mode; e.g. ``[4]``).
            - ``'binary_string'`` : integer bit masks cleared before testing; a
              row is flagged only if a NON-whitelisted bit remains set
              (e.g. ``[1, 2]``).

        Returns
        -------
        Union[pd.DataFrame, pd.Series]
            If return_mask=True: boolean Series with True for error points
            If return_mask=False: Filtered DataFrame with error points masked
        """
        # Check if status column exists
        if status_column not in _df.columns:
            # No status column, return all False (no errors)
            if return_mask:
                return pd.Series(False, index=_df.index)
            else:
                return _df

        # Create an empty mask
        error_mask = pd.Series(False, index=_df.index)

        # `ignored_values` whitelist helpers. Interpretation is mode-specific
        # (see the docstring); non-convertible entries are dropped so a
        # whitelist meant for one instrument is harmless if it reaches another.
        def _ignored_ints():
            out = set()
            for v in (ignored_values or []):
                try:
                    out.add(int(v))
                except (TypeError, ValueError):
                    pass
            return out

        def _ignored_nums():
            out = set()
            for v in (ignored_values or []):
                n = pd.to_numeric(v, errors='coerce')
                if pd.notna(n):
                    out.add(n)
            return out

        if status_type == 'bitwise':
            # Bitwise logic for AE33, AE43, BC1054, MA350.
            status_values = pd.to_numeric(_df[status_column], errors='coerce').fillna(0).astype(int)
            ignored_codes = _ignored_ints()

            # Whitelisted codes are dropped from the error definition: a row is
            # flagged only if at least one NON-whitelisted code matches.
            if error_codes:
                for code in error_codes:
                    if code in ignored_codes:
                        continue
                    error_mask = error_mask | ((status_values & code) != 0)

            # Exact matching for special codes (also whitelist-filtered).
            if special_codes:
                effective_special = [c for c in special_codes if c not in ignored_codes]
                if effective_special:
                    error_mask = error_mask | status_values.isin(effective_special)

        elif status_type == 'numeric':
            # Simple numeric comparison for TEOM, Aurora, NEPH.
            status_values = pd.to_numeric(_df[status_column], errors='coerce')
            ok = ok_value if ok_value is not None else 0   # Default: 0 is OK
            error_mask = (status_values != ok) & status_values.notna()

            # Whitelisted numeric status codes are treated as OK.
            ignored_nums = _ignored_nums()
            if ignored_nums:
                error_mask = error_mask & ~status_values.isin(ignored_nums)

        elif status_type == 'text':
            # Text comparison for SMPS. Three forms all mean "no status reported"
            # and must NEVER be flagged as errors: empty string, the pandas
            # NaN-stringified 'nan', and the Python-None-stringified 'None'.
            # The last one arrives when a column is missing in some files of a
            # multi-file concat (pd.concat fills the gap with Python None,
            # which `astype(str)` turns into the string 'None').
            EMPTY_SENTINELS = ('', 'nan', 'None')
            status_values = _df[status_column].astype(str).str.strip()
            if ok_value is not None:
                if ignored_values:
                    # Token-level whitelist: split each row's status by ','
                    # and require every token to be either the OK value or in
                    # the whitelist. Empty statuses are never errors.
                    ignored_set = {str(v).strip() for v in ignored_values}
                    allowed = ignored_set | {ok_value}

                    def _is_error(s):
                        if s in EMPTY_SENTINELS:
                            return False
                        return not all(t.strip() in allowed for t in s.split(','))

                    error_mask = status_values.apply(_is_error)
                else:
                    error_mask = (status_values != ok_value) & ~status_values.isin(EMPTY_SENTINELS)
            else:
                # No ok_value specified, can't determine errors
                error_mask = pd.Series(False, index=_df.index)

        elif status_type == 'binary_string':
            # Binary string parsing for APS ('0000 0000 0000 0000')
            def parse_binary_status(status_str):
                if not isinstance(status_str, str) or status_str in ('nan', ''):
                    return 0
                binary_str = status_str.replace(' ', '')
                try:
                    return int(binary_str, 2)
                except ValueError:
                    return 0

            status_values = _df[status_column].apply(parse_binary_status)

            # Whitelisted bits are cleared before testing: a row is flagged
            # only if a NON-whitelisted bit remains set.
            ignore_mask = 0
            for code in _ignored_ints():
                ignore_mask |= code
            if ignore_mask:
                error_mask = status_values.apply(lambda v: (v & ~ignore_mask) > 0)
            else:
                error_mask = status_values > 0

        else:
            raise ValueError(f"Unknown status_type: {status_type}")

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
        Check whether each clock hour holds enough data to be representative.

        Parameters
        ----------
        df : pd.DataFrame
            Input data frame with time series
        freq : str
            Data frequency (e.g. '6min')
        threshold : float, default=0.5
            Minimum required proportion of the points that hour could hold (0-1)

        Returns
        -------
        pd.Series
            Boolean mask where True indicates insufficient data

        Notes
        -----
        This is a statement about **representativeness**, not validity: the
        readings in a sparse hour are perfectly good measurements, it is an
        *average over that hour* that would misrepresent it. Readers therefore
        raise it at ``severity='warning'`` — see `QCRule`.

        The expectation is scaled by how much of each hour the data actually
        spans, which matters at the two ends of every read. An hour is compared
        against the points it *could* have held given the coverage, not against a
        full hour it never had the chance to fill: a read starting at 10:54 has
        six minutes in the 10 o'clock hour, so a full-hour expectation condemns it
        no matter how perfectly the instrument ran. That is what made short reads
        unusable — a 22-minute file had every row flagged — while leaving
        multi-day reads almost untouched, since the effect is always exactly two
        hours out of however many.

        Interior hours are unaffected: they overlap the coverage completely, so
        their expectation is the full hour and a genuine outage is still caught.
        """
        # Ensure input is DataFrame
        df = cls._ensure_dataframe(df)

        # Create result mask
        completeness_mask = pd.Series(False, index=df.index)
        if df.empty:
            return completeness_mask

        # Calculate the sampling period. Go through `to_offset` rather than
        # `Timedelta(freq)` directly: a pandas freqstr may omit the multiplier
        # ('min', 'h'), which Timedelta rejects outright.
        try:
            period = pd.Timedelta(pd.tseries.frequencies.to_offset(freq))
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"hourly_completeness_QC could not interpret freq={freq!r}: {exc}") from exc

        # How many points each hour could hold, given what the data spans. The
        # last row stands for a whole period, hence the + period.
        hour_start = pd.Series(df.index.floor('1h'), index=df.index)
        coverage_start, coverage_end = df.index.min(), df.index.max() + period
        overlap = (
            pd.concat([hour_start + pd.Timedelta('1h'),
                       pd.Series(coverage_end, index=df.index)], axis=1).min(axis=1)
            - pd.concat([hour_start,
                         pd.Series(coverage_start, index=df.index)], axis=1).max(axis=1)
        )
        expected = overlap / period
        min_points = expected * threshold

        # Only process numeric columns, and ignore any that are empty throughout:
        # an unconnected optional sensor says nothing about a particular hour, but
        # would otherwise mark every hour insufficient for every other column too.
        numeric_cols = [c for c in df.select_dtypes(include=np.number).columns
                        if df[c].notna().any()]

        for col in numeric_cols:
            # Calculate actual data points per hour
            hourly_count = df[col].notna().groupby(hour_start).transform('sum')
            # Mark points with insufficient data. An hour that could not hold even
            # one point is not judged — there is nothing to be short of.
            insufficient_mask = (hourly_count < min_points) & (expected >= 1)
            completeness_mask = completeness_mask | insufficient_mask

        return completeness_mask
