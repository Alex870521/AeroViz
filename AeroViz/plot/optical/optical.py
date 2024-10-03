import math
from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
# from PyMieScatt import ScatteringFunction
from matplotlib.pyplot import Figure, Axes

from AeroViz.plot.utils import *
from temp.process.method.mie_theory import Mie_Q, Mie_MEE, Mie_PESD

__all__ = ['Q_plot',
           'RI_couple',
           'RRI_2D',
           # 'scattering_phase',
           'response_surface',
           ]

mapping_dic = {'AS': {'m': 1.53 + 0j, 'density': 1.73, 'label': fr'$NH_{4}NO_{3}$', 'color': '#A65E58'},
               'AN': {'m': 1.55 + 0j, 'density': 1.77, 'label': fr'$(NH_{4})_{2}SO_{4}$', 'color': '#A5BF6B'},
               'OM': {'m': 1.54 + 0j, 'density': 1.40, 'label': 'OM', 'color': '#F2BF5E'},
               'Soil': {'m': 1.56 + 0.01j, 'density': 2.60, 'label': 'Soil', 'color': '#3F83BF'},
               'SS': {'m': 1.54 + 0j, 'density': 1.90, 'label': 'SS', 'color': '#B777C2'},
               'BC': {'m': 1.80 + 0.54j, 'density': 1.50, 'label': 'BC', 'color': '#D1CFCB'},
               'Water': {'m': 1.333 + 0j, 'density': 1.00, 'label': 'Water', 'color': '#96c8e6'}}


@set_figure
def Q_plot(species: Literal["AS", "AN", "OM", "Soil", "SS", "BC", "Water"] | list[
    Literal["AS", "AN", "OM", "Soil", "SS", "BC", "Water"]],
           x: Literal["dp", "sp"] = 'dp',
           y: Literal["Q", "MEE"] = "Q",
           mode: Literal["ext", "sca", "abs"] = 'ext',
           **kwargs) -> tuple[Figure, Axes]:
    """
    Generate a plot showing optical efficiency or mass optical efficiency for different particle species.

    Parameters
    ----------
    species : Union[Literal["AS", "AN", "OM", "Soil", "SS", "BC", "Water"], list[Literal["AS", "AN", "OM", "Soil", "SS", "BC", "Water"]]]
        The particle species or list of particle species to plot. Valid species include 'AS' (Ammonium Sulfate),
        'AN' (Ammonium Nitrate), 'OM' (Organic Matter), 'Soil', 'SS' (Sea Salt), 'BC' (Black Carbon), and 'Water'.

    x : Literal["dp", "sp"], optional
        The x-axis parameter. 'dp' represents particle diameter, and 'sp' represents size parameter (alpha).
        Default is 'dp'.

    y : Literal["Q", "MEE"], optional
        The y-axis parameter. 'Q' represents optical efficiency (Q_ext, Q_sca, Q_abs), and 'MEE' represents
        mass optical efficiency (MEE, MSE, MAE). Default is 'Q'.

    mode : Literal["ext", "sca", "abs"], optional
        The mode of efficiency to plot. 'ext' for extinction efficiency, 'sca' for scattering efficiency,
        and 'abs' for absorption efficiency. Default is 'ext'.

    **kwargs
        Additional keyword arguments to pass to the plot function.

    Returns
    -------
    ax : Axes
        Matplotlib Axes object containing the generated plot.

    Examples
    --------
    Example usage of the Q_plot function:

    >>> Q_plot('AS', x='dp', y='Q', mode='ext')
    >>> Q_plot(['AS', 'AN'], x='sp', y='MEE')
    """
    dp = np.geomspace(10, 10000, 2000)

    mode_mapping = {'ext': 0, 'sca': 1, 'abs': 2}

    xlabel_mapping = {'dp': 'Particle Diameter (nm)',
                      'sp': 'Size parameter (\\alpha)'}

    ylabel_mapping = {'Q': {'ext': r'$Extinction\ efficiency\ (Q_{ext})$',
                            'sca': r'$Scattering\ efficiency\ (Q_{sca})$',
                            'abs': r'$Absorption\ efficiency\ (Q_{abs})$'},
                      'MEE': {'ext': r'$MEE\ (m^{2}/g)$',
                              'sca': r'$MSE\ (m^{2}/g)$',
                              'abs': r'$MAE\ (m^{2}/g)$'}}

    typ = mode_mapping.get(mode, None)
    xlabel = xlabel_mapping.get(x, None)
    ylabel = ylabel_mapping.get(y, None).get(mode, None)

    fig, ax = plt.subplots()

    if x == "sp":
        size_para = math.pi * dp.copy() / 550
        dp_ = size_para

    else:
        plt.semilogx()
        dp_ = dp.copy()

    if isinstance(species, list):
        for i, specie in enumerate(species):
            label = mapping_dic[specie].get('label', None)
            color = mapping_dic[specie].get('color', None)

            mapping_dic[specie]['Q'] = Mie_Q(mapping_dic[specie]['m'], 550, dp)
            mapping_dic[specie]['MEE'] = Mie_MEE(mapping_dic[specie]['m'], 550, dp, mapping_dic[specie]['density'])

            plt.plot(dp_, mapping_dic[specie][f'{y}'][typ], color=color, label=label, alpha=1, lw=2)

    else:
        legend_label = {'Q': [r'$\bf Q_{{ext}}$', r'$\bf Q_{{scat}}$', r'$\bf Q_{{abs}}$'],
                        'MEE': [r'$\bf MEE$', r'$\bf MSE$', r'$\bf MAE$']}

        ylabel_mapping = {'Q': r'$\bf Optical\ efficiency\ (Q_{{ext, sca, abs}})$',
                          'MEE': r'$\bf Mass\ Optical\ Efficiency\ (m^2/g)$'}

        legend = legend_label.get(y, None)
        ylabel = ylabel_mapping.get(y, None)

        mapping_dic[species]['Q'] = Mie_Q(mapping_dic[species]['m'], 550, dp)
        mapping_dic[species]['MEE'] = Mie_MEE(mapping_dic[species]['m'], 550, dp, mapping_dic[species]['density'])

        plt.plot(dp_, mapping_dic[species][f'{y}'][0], color='b', label=legend[0])
        plt.plot(dp_, mapping_dic[species][f'{y}'][1], color='g', label=legend[1])
        plt.plot(dp_, mapping_dic[species][f'{y}'][2], color='r', label=legend[2])
        plt.text(0.04, 0.92, mapping_dic[species]['label'], transform=ax.transAxes, weight='bold')

    ax.set(xlim=(dp.min(), dp.max()), ylim=(0, None), xlabel=xlabel, ylabel=ylabel)
    ax.grid(color='k', axis='x', which='major', linestyle='dashdot', linewidth=0.4, alpha=0.4)
    ax.legend(loc='best', prop={'weight': 'bold'})

    # fig.savefig(PATH_MAIN/f'Q_{species}')
    plt.show()

    return fig, ax


@set_figure(figsize=(9, 4))
def RI_couple(**kwargs) -> tuple[Figure, Axes]:
    """
    Generate a plot to test the influence of imaginary parts on scattering and absorption efficiencies.

    Parameters
    ----------
    **kwargs
        Additional keyword arguments to pass to the plot function.

    Returns
    -------
    ax : Axes
        Matplotlib Axes object containing the generated plot.

    Examples
    --------
    Example usage of the IJ_couple function:

    >>> ax = RI_couple()
    """
    dp = np.geomspace(10, 10000, 5000)

    a = Mie_Q(1.50 + 0.01j, 550, dp)
    b = Mie_Q(1.50 + 0.1j, 550, dp)
    c = Mie_Q(1.50 + 0.5j, 550, dp)

    fig, ax = plt.subplots(1, 2)
    plt.subplots_adjust(right=0.9, wspace=0.4)
    (ax1, ax2) = ax
    size_para = math.pi * dp / 550

    ax1.plot(size_para, a[1], 'k-', alpha=1, label=r'$\bf\ k\ =\ 0.01$')
    ax1.plot(size_para, b[1], 'b-', alpha=1, label=r'$\bf\ k\ =\ 0.10$')
    ax1.plot(size_para, c[1], 'g-', alpha=1, label=r'$\bf\ k\ =\ 0.50$')
    ax1.legend()

    ax1.set_xlim(0, size_para[-1])
    ax1.set_ylim(0, None)
    ax1.set_xlabel(r'$\bf Size\ parameter\ (\alpha)$')
    ax1.set_ylabel(r'$\bf Scattering\ efficiency\ (Q_{{scat}})$')

    ax2.plot(size_para, a[2], 'k-', alpha=1, label=r'$\bf\ k\ =\ 0.01$')
    ax2.plot(size_para, b[2], 'b-', alpha=1, label=r'$\bf\ k\ =\ 0.10$')
    ax2.plot(size_para, c[2], 'g-', alpha=1, label=r'$\bf\ k\ =\ 0.50$')
    ax2.legend()

    ax2.set_xlim(0, size_para[-1])
    ax2.set_ylim(0, None)
    ax2.set_xlabel(r'$\bf Size\ parameter\ (\alpha)$')
    ax2.set_ylabel(r'$\bf Absorption\ efficiency\ (Q_{{abs}})$')

    fig.suptitle(r'$\bf n\ =\ 1.50 $')
    # fig.savefig(PATH_MAIN/f'IJ_couple')

    plt.show()

    return fig, ax


@set_figure
def RRI_2D(mode: Literal["ext", "sca", "abs"] = 'ext',
           **kwargs) -> tuple[Figure, Axes]:
    """
    Generate a 2D plot of scattering efficiency (Q) against real and imaginary parts of the refractive index.

    Parameters
    ----------
    mode : {'ext', 'sca', 'abs'}, optional
        The mode of scattering efficiency to plot:
        - 'ext' for extinction efficiency (Q_ext)
        - 'sca' for scattering efficiency (Q_sca)
        - 'abs' for absorption efficiency (Q_abs)
        Default is 'ext'.

    **kwargs
        Additional keyword arguments to pass to the plot function.

    Returns
    -------
    ax : Axes
        Matplotlib Axes object containing the generated 2D plot.

    Examples
    --------
    Example usage of the RRI_2D function:

    >>> RRI_2D(mode='sca', xlabel='Real Part (n)', ylabel='Imaginary Part (k)', title='Scattering Efficiency 2D Plot')
    """
    mode_mapping = {'ext': 0, 'sca': 1, 'abs': 2}

    typ = mode_mapping.get(mode, None)

    for dp in [400, 550, 700]:
        RRI = np.linspace(1.3, 2, 100)
        IRI = np.linspace(0, 0.7, 100)
        arr = np.zeros((RRI.size, IRI.size))

        for i, I_RI in enumerate(IRI):
            for j, R_RI in enumerate(RRI):
                arr[i, j] = Mie_Q(R_RI + 1j * I_RI, 550, dp)[typ]

        fig, ax = plt.subplots()
        plt.title(fr'$\bf dp\ = {dp}\ nm$', )
        plt.xlabel(r'$\bf Real\ part\ (n)$', )
        plt.ylabel(r'$\bf Imaginary\ part\ (k)$', )

        im = plt.imshow(arr, extent=(1.3, 2, 0, 0.7), cmap='jet', origin='lower')
        color_bar = plt.colorbar(im, extend='both')
        color_bar.set_label(label=fr'$\bf Q_{{{mode}}}$')

    # fig.savefig(PATH_MAIN/f'RRI_{mode}_{dp}')

    plt.show()

    return fig, ax


# @set_figure
# def scattering_phase(m: complex = 1.55 + 0.01j,
#                      wave: float = 600,
#                      dp: float = 200) -> tuple[Figure, Axes]:
#     """
#     Generate a polar plot to visualize the scattering phase function.
#
#     Parameters
#     ----------
#     m : complex, optional
#         The complex refractive index of the scattering medium. Default is 1.55 + 0.01j.
#     wave : float, optional
#         The wavelength of the incident light in nanometers. Default is 600 nm.
#     dp : float, optional
#         The particle diameter in nanometers. Default is 200 nm.
#
#     Returns
#     -------
#     ax : Axes
#         Matplotlib Axes object containing the generated polar plot.
#
#     Examples
#     --------
#     Example usage of the scattering_phase function:
#
#     >>> ax = scattering_phase(m=1.55 + 0.01j, wave=600, dp=200)
#     """
#     theta, _SL, _SR, _SU = ScatteringFunction(m, wave, dp)
#
#     SL = np.append(_SL, _SL[::-1])
#     SR = np.append(_SR, _SR[::-1])
#     SU = np.append(_SU, _SU[::-1])
#
#     angles = ['0', '60', '120', '180', '240', '300']
#
#     fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
#
#     theta = np.linspace(0, 2 * np.pi, len(SL))
#
#     plt.thetagrids(range(0, 360, int(360 / len(angles))), angles)
#
#     plt.plot(theta, SL, '-', linewidth=2, color='#115162', label='SL')
#     plt.fill(theta, SL, '#afe0f5', alpha=0.5)
#     plt.plot(theta, SR, '-', linewidth=2, color='#7FAE80', label='SR')
#     plt.fill(theta, SR, '#b5e6c5', alpha=0.5)
#     plt.plot(theta, SU, '-', linewidth=2, color='#621129', label='SU')
#     plt.fill(theta, SU, '#f5afbd', alpha=0.5)
#
#     plt.legend(loc='best', bbox_to_anchor=(1, 0, 0.2, 1), prop={'weight': 'bold'})
#     plt.title(r'$\bf Scattering\ phase\ function$')
#
#     plt.show()
#     return fig, ax


@set_figure
def response_surface(real_range=(1.33, 1.7),
                     gmd_range=(10, 500),
                     num=50,
                     **kwargs) -> tuple[Figure, Axes]:
    """
    Generate a response surface plot for sensitivity tests of extinction based on Mie scattering.

    Parameters
    ----------
    real_range : tuple, optional
        The range of real part (refractive index) values for sensitivity testing. Default is (1.33, 1.7).

    gmd_range : tuple, optional
        The range of geometric mean diameter (GMD) values for sensitivity testing. Default is (60, 400).

    num : int, optional
        The number of points to generate within the specified ranges. Default is 50.

    **kwargs
        Additional keyword arguments to pass to the plot function.

    Returns
    -------
    ax : Axes
        Matplotlib Axes object containing the generated response surface plot.

    Examples
    --------
    Example usage of the response_surface function:

    >>> response_surface(real_range=(1.4, 1.6), gmd_range=(100, 300), num=30, xlabel='Real Part (n)',
    ...                  ylabel='GMD (nm)', zlabel='Extinction (1/Mm)', title='Sensitivity Tests of Extinction')
    """

    def function(RI, GMD):
        Z = np.zeros_like(RI)  # 使用 np.zeros_like 可以確保 Z 和 RI 具有相同的形狀

        for i in range(RI.shape[0]):
            for j in range(RI.shape[1]):
                _RI, _GMD = RI[i, j], GMD[i, j]
                Bext, Bsca, Babs = Mie_PESD(m=_RI, lognormal=True, geoMean=_GMD, geoStdDev=2.)
                Z[i, j] = np.sum(Bext)

        return Z

    # 假設 RI、GSD、GMD
    RI = np.linspace(real_range[0], real_range[1], num)
    GMD = np.linspace(gmd_range[0], gmd_range[1], num)

    # 建立三維 meshgrid
    real, gmd = np.meshgrid(RI, GMD, indexing='xy')

    # Result
    ext = function(real, gmd)

    # plot
    fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
    ax.plot_surface(real, gmd, ext, rstride=1, cstride=1, cmap=plt.get_cmap('jet'), edgecolor='none')

    ax.set(xlabel='Real part (n)', ylabel='GMD (nm)', zlabel=Unit('Extinction'),
           title='Sensitive tests of Extinction')

    ax.zaxis.get_offset_text().set_visible(False)
    exponent = math.floor(math.log10(np.max(ext)))
    ax.text(ax.get_xlim()[1] * 1.01, ax.get_ylim()[1], ax.get_zlim()[1] * 1.1, s=fr'${{\times}}\ 10^{exponent}$')
    ax.ticklabel_format(style='sci', axis='z', scilimits=(0, 0), useOffset=False)

    plt.show()

    return fig, ax


if __name__ == '__main__':
    # Q_plot(['AS', 'AN', 'OM', 'Soil', 'SS', 'BC'], x='dp', y='MEE')
    # Q_plot(['AS', 'AN', 'OM', 'Soil', 'SS', 'BC'], x='dp', y='Q')

    # RI_couple()
    response_surface()
