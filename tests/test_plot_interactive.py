"""Tests for the interactive timeseries viewer (AeroViz.plot.timeseries_interactive)."""
import numpy as np
import pandas as pd
import pytest

from AeroViz.plot import timeseries_interactive


def _df(n=50):
    idx = pd.date_range('2025-03-05', periods=n, freq='1min', name='time')
    df = pd.DataFrame({
        'eBC': np.random.rand(n),
        'AAE': np.random.rand(n),
        '11.34': np.random.rand(n),   # size-bin column (numeric name)
        '11.76': np.random.rand(n),   # size-bin column
        'QC_Flag': ['Valid'] * n,
    }, index=idx)
    df.attrs.update(instrument='AE33', coverage_start=idx[0], coverage_end=idx[-1])
    return df


def test_returns_figure_excluding_bins_and_flag():
    fig = timeseries_interactive(_df(), show=False)
    names = [t.name for t in fig.data]
    assert names == ['eBC', 'AAE']            # size bins + QC_Flag excluded
    assert 'go' in type(fig).__module__ or fig.__class__.__name__ == 'Figure'


def test_columns_override_allows_bins():
    fig = timeseries_interactive(_df(), columns=['11.34', 'eBC'], show=False)
    assert [t.name for t in fig.data] == ['11.34', 'eBC']


def test_title_defaults_from_attrs():
    fig = timeseries_interactive(_df(), show=False)
    assert fig.layout.title.text.startswith('AE33')


def test_explicit_title_overrides():
    fig = timeseries_interactive(_df(), title='custom', show=False)
    assert fig.layout.title.text == 'custom'


def test_save_writes_html(tmp_path):
    out = tmp_path / 'ts.html'
    timeseries_interactive(_df(), save=str(out), show=False)
    assert out.exists() and out.stat().st_size > 0


def test_no_plottable_columns_raises():
    idx = pd.date_range('2025-03-05', periods=10, freq='1min')
    bins_only = pd.DataFrame({'11.34': range(10), '11.76': range(10)}, index=idx)
    with pytest.raises(ValueError):
        timeseries_interactive(bins_only, show=False)


def test_non_datetime_index_raises():
    df = pd.DataFrame({'a': range(5)})
    with pytest.raises(TypeError):
        timeseries_interactive(df, show=False)
