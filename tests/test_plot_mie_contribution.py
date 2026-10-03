import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pytest

from AeroViz.plot.optical import mie_contribution
from AeroViz.optical import mie_lognormal

pytestmark = [pytest.mark.optical]


def test_mie_contribution_two_panels_and_legend_totals():
    fig, (ax1, ax2) = mie_contribution(1.8 + 0.1j, [550, 880], geo_mean=140, geo_std=1.95,
                                       total_mass=30, density=1.85)
    try:
        assert len(fig.axes) >= 2
        labels = [t.get_text() for t in ax2.get_legend().get_texts()]
        assert len(labels) == 4                       # sca + abs × 2 wavelengths
        # the number in the legend is the bulk coefficient mie_lognormal gives
        bulk = mie_lognormal(1.8 + 0.1j, 550, geo_mean=140, geo_std=1.95, total_mass=30, density=1.85,
                             dp_range=(5, 10000), n_bins=500)
        sca_label = next(l for l in labels if 'sca' in l and '550' in l)
        shown = float(sca_label.split('= ')[1].split(' ')[0])
        assert shown == pytest.approx(bulk['sca'], abs=0.06)
    finally:
        plt.close(fig)
