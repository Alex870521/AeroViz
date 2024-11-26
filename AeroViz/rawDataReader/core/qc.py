import numpy as np
import pandas as pd


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
    def rolling_iqr(cls, df: pd.DataFrame, window_size: int = 24,
                    log_dist: bool = False) -> pd.DataFrame:
        """
        Detect outliers using rolling window IQR method

        Parameters
        ----------
        df : pd.DataFrame
            Input data
        window_size : int, default=24
            Size of the rolling window
        log_dist : bool, default=False
            Whether to apply log transformation to data

        Returns
        -------
        pd.DataFrame
            Cleaned DataFrame with outliers masked as NaN
        """
        df = cls._ensure_dataframe(df)
        df_transformed = cls._transform_if_log(df, log_dist)

        def iqr_filter(x):
            q1, q3 = x.quantile(0.25), x.quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            return (x >= lower) & (x <= upper)

        mask = df_transformed.rolling(
            window=window_size,
            center=True,
            min_periods=1
        ).apply(iqr_filter)

        return df.where(mask, np.nan)

    @classmethod
    def time_aware_iqr(cls, df: pd.DataFrame, time_window: str = '1D',
                       log_dist: bool = False) -> pd.DataFrame:
        """
        Detect outliers using time-aware IQR method

        Parameters
        ----------
        df : pd.DataFrame
            Input data
        time_window : str, default='1D'
            Time window size (e.g., '1D' for one day)
        log_dist : bool, default=False
            Whether to apply log transformation to data

        Returns
        -------
        pd.DataFrame
            Cleaned DataFrame with outliers masked as NaN
        """
        df = cls._ensure_dataframe(df)
        df_transformed = cls._transform_if_log(df, log_dist)

        def iqr_filter(group):
            q1, q3 = group.quantile(0.25), group.quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            return (group >= lower) & (group <= upper)

        mask = df_transformed.groupby(
            pd.Grouper(freq=time_window)
        ).transform(iqr_filter)

        return df.where(mask, np.nan)

    @classmethod
    def mad_iqr_hybrid(cls, df: pd.DataFrame, mad_threshold: float = 3.5,
                       log_dist: bool = False) -> pd.DataFrame:
        """
        Detect outliers using a hybrid of MAD and IQR methods

        Parameters
        ----------
        df : pd.DataFrame
            Input data
        mad_threshold : float, default=3.5
            Threshold for MAD method
        log_dist : bool, default=False
            Whether to apply log transformation to data

        Returns
        -------
        pd.DataFrame
            Cleaned DataFrame with outliers masked as NaN
        """
        df = cls._ensure_dataframe(df)
        df_transformed = cls._transform_if_log(df, log_dist)

        # IQR method
        q1, q3 = df_transformed.quantile(0.25), df_transformed.quantile(0.75)
        iqr = q3 - q1
        iqr_lower, iqr_upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr

        # MAD method
        median = df_transformed.median()
        mad = (df_transformed - median).abs().median()
        mad_lower = median - mad_threshold * mad
        mad_upper = median + mad_threshold * mad

        # Combine both methods
        lower = np.maximum(iqr_lower, mad_lower)
        upper = np.minimum(iqr_upper, mad_upper)

        mask = (df_transformed >= lower) & (df_transformed <= upper)
        return df.where(mask, np.nan)
