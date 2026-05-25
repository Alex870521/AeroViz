"""Regression tests for plotting helpers that previously crashed.

Covers:
- box() with a categorical (string) x-axis and with non-integer numeric bins
- Unit() escaping '%' so $...$ mathtext parses (and not spamming stdout)
"""
import matplotlib

matplotlib.use('Agg')  # headless: no display needed for these tests

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pytest


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close('all')


# --------------------------------------------------------------------------- #
# box()
# --------------------------------------------------------------------------- #
@pytest.fixture
def categorical_df():
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        'season': ['DJF', 'MAM', 'JJA', 'SON'] * 12,
        'BC': rng.random(48),
    })


@pytest.fixture
def numeric_df():
    rng = np.random.default_rng(1)
    return pd.DataFrame({
        'PM': rng.uniform(0, 10, 300),
        'BC': rng.random(300),
    })


def test_box_categorical_string_x(categorical_df):
    """A string x-axis is grouped per category instead of crashing on pd.cut."""
    from AeroViz.plot import box
    fig, ax = box(categorical_df, x='season', y='BC')
    # one box per unique category
    assert len(ax.get_xticks()) == categorical_df['season'].nunique()


def test_box_noninteger_bins(numeric_df):
    """Float-width bins must not collide (previously np.round'd the edges)."""
    from AeroViz.plot import box
    fig, ax = box(numeric_df, x='PM', y='BC', x_bins=np.arange(0.5, 10.5, 1.0))
    assert ax is not None


def test_box_numeric_without_bins_is_categorical(numeric_df):
    """Numeric x with no x_bins falls back to per-value categories (no crash)."""
    from AeroViz.plot import box
    small = numeric_df.assign(PM=numeric_df['PM'].round())  # few distinct values
    fig, ax = box(small, x='PM', y='BC')
    assert ax is not None


# --------------------------------------------------------------------------- #
# Unit()
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize('label', ['%', 'OM_mass_ratio', 'BC', 'PM25'])
def test_unit_renders_without_parse_error(label):
    """Unit() output must be valid mathtext (a bare '%' used to break parsing)."""
    from AeroViz.plot.utils._unit import Unit
    fig, ax = plt.subplots()
    ax.set_ylabel(Unit(label))
    fig.canvas.draw()  # forces mathtext parsing; raised ValueError before the fix


def test_unit_escapes_percent():
    from AeroViz.plot.utils._unit import Unit
    assert Unit('%') == r'$\%$'


def test_unit_unknown_label_is_quiet(capsys):
    """An unlisted label is a normal fallback, not a console warning."""
    from AeroViz.plot.utils._unit import Unit
    Unit('some_unlisted_label')
    assert capsys.readouterr().out == ''
