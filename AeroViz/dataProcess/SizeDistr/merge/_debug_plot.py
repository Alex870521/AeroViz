"""Optional matplotlib debug plots for the SMPS-APS merge, shared by v1-v4.

These are diagnostic helpers — they are NOT called in the normal merge flow.
They previously lived as near-duplicate ``__test_plot`` (v1/v2) and
``_test_plot`` / ``test_plot`` (v3) functions; consolidated here so any version
can ``from ._debug_plot import plot_overlap, plot_nsv`` while debugging a merge.
"""
import numpy as np


def plot_overlap(smpsx, smps, apsx, aps, mergex, merge, mergeox, mergeo, _sh):
    """Single-axes log-log overlay of SMPS, APS and the merged distribution.

    (Formerly ``__test_plot`` in v1/v2.)
    """
    from matplotlib.pyplot import subplots, close, show

    fig, ax = subplots()

    ax.plot(smpsx, smps, c='#ff794c', label='smps', marker='o', lw=2)
    ax.plot(apsx, aps, c='#4c79ff', label='aps', marker='o', lw=2)
    ax.plot(mergex, merge, c='#79796a', label='merge')
    # ax.plot(mergeox, mergeo, c='#111111', label='mergeo', marker='o', lw=.75)

    ax.set(xscale='log', yscale='log')
    ax.legend(framealpha=0)
    ax.set_title((_sh ** 2)[0], fontsize=13)

    show()
    close()


def _plot_nsv_axis(ax, smps, aps, unp, shft):
    """Plot SMPS, original + shifted APS, and the merged curve on one axis.

    (Formerly ``_test_plot`` in v3.)
    """
    ax.plot(smps, c='#2693ff', label='smps')
    ax.plot(aps, c='#ff4c4d', label='aps_ori')
    ax.plot(aps.index / shft, aps.values, c='#ff181b', label='aps_shft', ls='--')
    ax.plot(unp, c='#333333', label='unp')
    ax.set(xlim=(11.8, 2500), xscale='log')


def plot_nsv(smps, aps, unp, shft):
    """Three-panel number / surface / volume debug plot.

    (Formerly ``test_plot`` in v3.)
    """
    from matplotlib.pyplot import subplots, show

    fig, axes = subplots(3, 1)

    ds_fc = lambda _dt: _dt * _dt.index ** 2 * np.pi
    dv_fc = lambda _dt: _dt * _dt.index ** 3 * np.pi / 6

    axes[0].set_title(shft)

    _plot_nsv_axis(axes[0], smps, aps, unp, shft)
    _plot_nsv_axis(axes[1], ds_fc(smps), ds_fc(aps), ds_fc(unp), shft)
    _plot_nsv_axis(axes[2], dv_fc(smps), dv_fc(aps), dv_fc(unp), shft)

    show()
