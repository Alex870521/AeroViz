from datetime import datetime

from pandas import DataFrame, Timestamp
from tabulate import tabulate


def data_table(df: DataFrame,
               items: list[str] | str = None,
               times: list[datetime | Timestamp | str] = None,
               ):
    """
    This function cuts the DataFrame based on the given time periods and calculates the mean and standard deviation
    of the specified items for each period.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to be processed. It should have a DateTime index.
    items : list[str] | str, optional
        The columns of the DataFrame to be processed. It can be a list of column names or a single column name.
        By default, it is ['NO', 'NO2', 'NOx'].
    times : list[str] | str, optional
        The time periods to cut the DataFrame. It can be a list of time strings or a single time string.
        Each time string should be in the format of 'YYYY-MM-DD'. By default, it is ['2024-03-21', '2024-04-30'].

    Returns
    -------
    None
        This function doesn't return any value. It prints out a table showing the mean and standard deviation
        of the specified items for each time period.
    """
    items = [items] if isinstance(items, str) else items
    times = [times] if isinstance(times, str) else times
    times = list(map(Timestamp, times))

    times.sort()

    results = []
    periods = []
    for i in range(len(times) + 1):
        if i == 0:
            df_period = df.loc[df.index <= times[i], items]
            period_label = f'Before {times[i].date()}'
        elif i == len(times):
            df_period = df.loc[df.index > times[i - 1], items]
            period_label = f'After {times[i - 1].date()}'
        else:
            df_period = df.loc[(df.index > times[i - 1]) & (df.index <= times[i]), items]
            period_label = f'{times[i - 1].date()} to {times[i].date()}'

        mean, std = df_period.mean().round(2).to_numpy(), df_period.std().round(2).to_numpy()

        results.append([f'{m} ± {s}' for m, s in zip(mean, std)])
        periods.append(period_label)

    result = DataFrame(results, columns=items, index=periods)

    print(tabulate(result, headers='keys', tablefmt='fancy_grid'))
