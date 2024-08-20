import matplotlib.pyplot as plt
from matplotlib.pyplot import Figure, Axes
from pandas import DataFrame

from AeroViz.plot.utils import set_figure, Unit


@set_figure(figsize=(5, 4))
def ammonium_rich(df: DataFrame,
                  **kwargs
                  ) -> tuple[Figure, Axes]:
    df = df[['NH4+', 'SO42-', 'NO3-', 'PM2.5']].dropna().copy().div([18, 96, 62, 1])
    df['required_ammonium'] = df['NO3-'] + 2 * df['SO42-']

    fig, ax = plt.subplots()

    scatter = ax.scatter(df['required_ammonium'].to_numpy(), df['NH4+'].to_numpy(), c=df['PM2.5'].to_numpy(),
                         vmin=0, vmax=70, cmap='jet', marker='o', s=10, alpha=1)

    ax.axline((0, 0), slope=1., color='k', lw=2, ls='--', alpha=0.5, label='1:1')
    plt.text(0.97, 0.97, r'$\bf 1:1\ Line$', color='k', ha='right', va='top', transform=ax.transAxes)

    ax.set(xlim=(0, 1.2),
           ylim=(0, 1.2),
           xlabel=r'$\bf NO_{3}^{-}\ +\ 2\ \times\ SO_{4}^{2-}\ (mole\ m^{-3})$',
           ylabel=r'$\bf NH_{4}^{+}\ (mole\ m^{-3})$',
           title=kwargs.get('title', ''))

    color_bar = plt.colorbar(scatter, label=Unit('PM2.5'), extend='both')

    # fig.savefig(f'Ammonium_rich_{title}')
    plt.show()

    return fig, ax
