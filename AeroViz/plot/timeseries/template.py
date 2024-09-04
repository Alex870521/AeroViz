import matplotlib.pyplot as plt
from matplotlib.pyplot import Figure, Axes
from pandas import DataFrame

from AeroViz.plot.timeseries import timeseries


def timeseries_template(df: DataFrame) -> tuple[Figure, Axes]:
    fig, ax = plt.subplots(5, 1, figsize=(len(df.index) * 0.01, 4))
    (ax1, ax2, ax3, ax4, ax5) = ax

    timeseries(df,
               y=['Extinction', 'Scattering', 'Absorption'],
               rolling=30,
               ax=ax1,
               ylabel='Coefficient',
               ylim=[0., None],
               set_xaxis_visible=False,
               legend_ncol=3,
               )

    # Temp, RH
    timeseries(df,
               y='AT',
               y2='RH',
               rolling=30,
               ax=ax2,
               ax_plot_kws=dict(color='r'),
               ax2_plot_kws=dict(color='b'),
               ylim=[10, 30],
               ylim2=[20, 100],
               set_xaxis_visible=False,
               legend_ncol=2,
               )

    timeseries(df, y='WS', color='WD', style='scatter', ax=ax3, scatter_kws=dict(cmap='hsv'),
               cbar_kws=dict(ticks=[0, 90, 180, 270, 360]),
               ylim=[0, None], set_xaxis_visible=False)

    timeseries(df, y='VC', color='PBLH', style='bar', ax=ax4, bar_kws=dict(cmap='Blues'), set_xaxis_visible=False,
               ylim=[0, 5000])

    timeseries(df, y='PM25', color='PM1/PM25', style='scatter', ax=ax5, ylim=[0, None])

    plt.show()

    return fig, ax
