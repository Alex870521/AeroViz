import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, RegularPolygon
from matplotlib.path import Path
from matplotlib.projections import register_projection
from matplotlib.projections.polar import PolarAxes
from matplotlib.spines import Spine
from matplotlib.transforms import Affine2D

from AeroViz.plot.utils import *

__all__ = ['radar']


def radar_factory(num_vars, frame='circle'):
    """
    Create a radar chart with `num_vars` axes.

    This function creates a RadarAxes projection and registers it.

    Parameters
    ----------
    num_vars : int
        Number of variables for radar chart.
    frame : {'circle', 'polygon'}
        Shape of frame surrounding axes.

    """
    # calculate evenly-spaced axis angles
    theta = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)

    class RadarTransform(PolarAxes.PolarTransform):

        def transform_path_non_affine(self, path):
            # Paths with non-unit interpolation steps correspond to gridlines,
            # in which case we force interpolation (to defeat PolarTransform's
            # autoconversion to circular arcs).
            if path._interpolation_steps > 1:
                path = path.interpolated(num_vars)
            return Path(self.transform(path.vertices), path.codes)

    class RadarAxes(PolarAxes):

        name = 'radar'
        PolarTransform = RadarTransform

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # rotate plot such that the first axis is at the top
            self.set_theta_zero_location('N')

        def fill(self, *args, closed=True, **kwargs):
            """Override fill so that line is closed by default"""
            return super().fill(closed=closed, *args, **kwargs)

        def plot(self, *args, **kwargs):
            """Override plot so that line is closed by default"""
            lines = super().plot(*args, **kwargs)
            for line in lines:
                self._close_line(line)

        def _close_line(self, line):
            x, y = line.get_data()
            if x[0] != x[-1]:
                x = np.append(x, x[0])
                y = np.append(y, y[0])
                line.set_data(x, y)

        def set_varlabels(self, labels):
            self.set_thetagrids(np.degrees(theta), labels)

        @staticmethod
        def _gen_axes_patch():
            # The Axes patch must be centered at (0.5, 0.5) and of radius 0.5
            # in axes coordinates.
            if frame == 'circle':
                return Circle((0.5, 0.5), 0.5)
            elif frame == 'polygon':
                return RegularPolygon((0.5, 0.5), num_vars,
                                      radius=.5, edgecolor="k")
            else:
                raise ValueError("Unknown value for 'frame': %s" % frame)

        def _gen_axes_spines(self):
            if frame == 'circle':
                return super()._gen_axes_spines()
            elif frame == 'polygon':
                # spine_type must be 'left'/'right'/'top'/'bottom'/'circle'.
                spine = Spine(axes=self,
                              spine_type='circle',
                              path=Path.unit_regular_polygon(num_vars))
                # unit_regular_polygon gives a polygon of radius 1 centered at
                # (0, 0) but we want a polygon of radius 0.5 centered at (0.5,
                # 0.5) in axes coordinates.
                spine.set_transform(Affine2D().scale(.5).translate(.5, .5)
                                    + self.transAxes)
                return {'polar': spine}
            else:
                raise ValueError("Unknown value for 'frame': %s" % frame)

    register_projection(RadarAxes)
    return theta


@set_figure(figsize=(3, 3))
def radar(data, labels=None, legend_labels=None, **kwargs) -> tuple[plt.Figure, plt.Axes]:
    """
    Creates a radar chart based on the provided data.

    Parameters
    ----------
    data : list of list
        A 2D list where each inner list represents a factor, and each element
        within the inner lists represents a value for a species.
        Shape: (n_factors, n_species)
        Example: [[0.88, 0.01, 0.03, ...], [0.07, 0.95, 0.04, ...], ...]

    labels : list, optional
        A list of strings representing the names of species (variables).
        If provided, it should have the same length as the number of elements
        in each inner list of `data`.
        Example: ['Sulfate', 'Nitrate', 'EC', 'OC1', 'OC2', 'OP', 'CO', 'O3']

    legend_labels : list, optional
        A list of strings for labeling each factor in the legend.
        If provided, it should have the same length as the number of inner lists in `data`.

    **kwargs : dict
        Additional keyword arguments to be passed to the plotting function.
        This may include 'title' for setting the chart title.

    Returns
    -------
    tuple[plt.Figure, plt.Axes]
        A tuple containing the Figure and Axes objects of the created plot.

    Example
    -------
    >>> data = [[0.88, 0.01, 0.03, 0.03, 0.00, 0.06, 0.01, 0.00],
    >>>         [0.07, 0.95, 0.04, 0.05, 0.00, 0.02, 0.01, 0.00],
    >>>         [0.01, 0.02, 0.85, 0.19, 0.05, 0.10, 0.00, 0.00],
    >>>         [0.02, 0.01, 0.07, 0.01, 0.21, 0.12, 0.98, 0.00],
    >>>         [0.01, 0.01, 0.02, 0.71, 0.74, 0.70, 0.30, 0.20]]
    >>> labels = ['Sulfate', 'Nitrate', 'EC', 'OC1', 'OC2', 'OP', 'CO', 'O3']
    >>> fig, ax = radar(data, labels=labels, title='Basecase')

    Note
    ----
    The first dimension of `data` represents each factor, while the second
    dimension represents each species.
    """
    theta = radar_factory(np.array(data).shape[1], frame='polygon')

    fig, ax = plt.subplots(subplot_kw=dict(projection='radar'))
    fig.subplots_adjust(wspace=0.25, hspace=0.20, top=0.80, bottom=0.05, right=0.80)

    colors = ['b', 'r', 'g', 'm', 'y']

    # Plot the four cases from the example data on separate axes
    for d, color in zip(data, colors):
        ax.plot(theta, d, color=color)
        ax.fill(theta, d, facecolor=color, alpha=0.25, label='_nolegend_')

    ax.set_varlabels(labels)
    ax.set_rgrids([0.2, 0.4, 0.6, 0.8])
    ax.set(title=kwargs.get('title', ''))

    # add legend relative to top-left plot
    legend_labels = legend_labels or ('Factor 1', 'Factor 2', 'Factor 3', 'Factor 4', 'Factor 5')
    legend = ax.legend(legend_labels, loc=(0.95, 0.95), labelspacing=0.1)

    plt.show()

    return fig, ax


if __name__ == '__main__':
    data = [[0.88, 0.01, 0.03, 0.03, 0.00, 0.06, 0.01, 0.00],
            [0.07, 0.95, 0.04, 0.05, 0.00, 0.02, 0.01, 0.00],
            [0.01, 0.02, 0.85, 0.19, 0.05, 0.10, 0.00, 0.00],
            [0.02, 0.01, 0.07, 0.01, 0.21, 0.12, 0.98, 0.00],
            [0.01, 0.01, 0.02, 0.71, 0.74, 0.70, 0.30, 0.20]]

    fig, ax = radar(data=data, labels=['Sulfate', 'Nitrate', 'EC', 'OC1', 'OC2', 'OP', 'CO', 'O3'], title='Basecase')
