from datetime import datetime
from typing import Literal, Sequence

import pandas as pd
from pandas import concat, DataFrame, Series


class Classifier:
    Seasons = {'2020-Summer': (datetime(2020, 9, 4), datetime(2020, 9, 21, 23)),
               '2020-Autumn': (datetime(2020, 9, 22), datetime(2020, 12, 29, 23)),
               '2020-Winter': (datetime(2020, 12, 30), datetime(2021, 3, 25, 23)),
               '2021-Spring': (datetime(2021, 3, 26), datetime(2021, 5, 6, 23))}

    # '2021-Summer': (datetime(2021, 5, 7), datetime(2021, 10, 16, 23))
    # '2021-Autumn': (datetime(2021, 10, 17), datetime(2021, 12, 31, 23))

    @classmethod
    def classify(cls, df) -> DataFrame:
        df = cls.classify_by_diurnal(df)
        df = cls.classify_by_state(df)
        df = cls.classify_by_season(df)
        df = cls.classify_by_season_state(df)

        return df

    @classmethod
    def classify_by_diurnal(cls, df):
        df['Hour'] = df.index.hour
        df['Diurnal'] = df['Hour'].apply(cls.map_diurnal)
        return df

    @classmethod
    def classify_by_state(cls, df):
        df['State'] = df.apply(cls.map_state, axis=1, clean_bound=df.Extinction.quantile(0.2),
                               event_bound=df.Extinction.quantile(0.8))
        return df

    @classmethod
    def classify_by_season(cls, df):
        for season, (season_start, season_end) in cls.Seasons.items():
            df.loc[season_start:season_end, 'Season'] = season
        return df

    @classmethod
    def classify_by_season_state(cls, df):
        for _grp, _df in df.groupby('Season'):
            df['Season_State'] = df.apply(cls.map_state, axis=1, clean_bound=_df.Extinction.quantile(0.2),
                                          event_bound=_df.Extinction.quantile(0.8))
        return df

    @staticmethod
    def map_diurnal(hour):
        return 'Day' if 7 <= hour <= 18 else 'Night'

    @staticmethod
    def map_state(row, clean_bound, event_bound):
        return 'Event' if row['Extinction'] >= event_bound else 'Clean' if row[
                                                                               'Extinction'] < clean_bound else 'Transition'


class DataClassifier(Classifier):
    """
    Notes
    -----
    First, create group then return the selected statistic method.
    If the 'by' does not exist in DataFrame, import the default DataFrame to help to sign the different group.

    """

    def __new__(cls,
                df: DataFrame,
                by: Literal["Hour", "State", "Season", "Season_state"] | str,
                df_support: DataFrame | Series = None,
                cut_bins: Sequence = None,
                qcut: int = None,
                labels: list[str] = None
                ) -> tuple[DataFrame, DataFrame]:
        group = cls._group_data(df, by, df_support, cut_bins, qcut, labels)
        return cls._compute_statistics(df, group)

    @staticmethod
    def _group_data(df, by, df_support, cut_bins, qcut, labels):
        if by not in df.columns:
            if df_support is None:
                raise KeyError(f"Column '{by}' does not exist in DataFrame."
                               f"Please provide a support DataFrame or Series to help classify.")
            else:
                df = concat([df, Classifier.classify(df_support.copy())[by]], axis=1)

        if cut_bins is not None:
            df[f'{by}_cut'] = pd.cut(df.loc[:, f'{by}'], cut_bins,
                                     labels=labels or (cut_bins + (cut_bins[1] - cut_bins[0]) / 2)[:-1])
            return df.groupby(f'{by}_cut', observed=False)

        elif qcut is not None:
            df[f'{by}_qcut'] = pd.qcut(df.loc[:, f'{by}'], q=qcut, labels=labels)
            return df.groupby(f'{by}_qcut', observed=False)

        else:
            if by == 'State':
                return df.groupby(by)

            elif by == 'Season':
                return df.groupby(pd.Categorical(df['Season'], categories=['2020-Summer', '2020-Autumn', '2020-Winter',
                                                                           '2021-Spring']), observed=False)
            else:
                return df.groupby(by, observed=False)

    @staticmethod
    def _compute_statistics(df, group):
        mean_df = group.mean(numeric_only=True)
        mean_df.loc['Total'] = df.mean(numeric_only=True)

        std_df = group.std(numeric_only=True)
        std_df.loc['Total'] = df.std(numeric_only=True)

        return mean_df, std_df
