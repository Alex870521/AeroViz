"""Interactive timeseries viewer for a RawDataReader result.

A quick way to eyeball instrument data: one Plotly trace per column, with the
legend acting as the column selector (click an entry to show/hide it). Reads
``df.attrs`` (instrument + coverage) for the default title.
"""
from __future__ import annotations

import warnings

import pandas as pd

__all__ = ['timeseries_interactive']

# Cap auto-selected columns so wide frames (e.g. SMPS/APS size bins) don't
# render hundreds of traces when the caller doesn't pass `columns`.
_MAX_AUTO_COLUMNS = 30


def _is_size_bin(col) -> bool:
    """True for size-distribution bin columns, whose names are numeric (e.g. '11.34')."""
    try:
        float(col)
        return True
    except (ValueError, TypeError):
        return False


def _default_columns(df: pd.DataFrame) -> list:
    """Numeric, non-bin columns (excludes size bins and QC_Flag)."""
    return [
        c for c in df.columns
        if c != 'QC_Flag' and not _is_size_bin(c) and pd.api.types.is_numeric_dtype(df[c])
    ]


def _default_title(df: pd.DataFrame) -> str | None:
    parts = []
    if df.attrs.get('instrument'):
        parts.append(str(df.attrs['instrument']))
    cov_start, cov_end = df.attrs.get('coverage_start'), df.attrs.get('coverage_end')
    if cov_start is not None and cov_end is not None:
        parts.append(f"{pd.Timestamp(cov_start):%Y-%m-%d %H:%M} ~ {pd.Timestamp(cov_end):%Y-%m-%d %H:%M}")
    return ' · '.join(parts) or None


def timeseries_interactive(df: pd.DataFrame, columns: list | None = None, *,
                           save: str | None = None, show: bool = True,
                           title: str | None = None):
    """Interactive timeseries plot (Plotly); the legend toggles columns.

    Parameters
    ----------
    df : pd.DataFrame
        A RawDataReader result (DatetimeIndex). ``df.attrs`` is used for the
        default title.
    columns : list, optional
        Columns to plot. Defaults to the numeric, non-size-bin columns (size
        bins like ``'11.34'`` and ``QC_Flag`` are excluded; capped at
        ``30`` with a warning). Pass an explicit list to override — including
        size-bin columns if you want them.
    save : str, optional
        If given, write the figure to this standalone HTML path.
    show : bool, default=True
        Display the figure (inline in notebooks, or open a browser tab).
    title : str, optional
        Figure title; defaults to ``"<instrument> · <coverage>"`` from
        ``df.attrs``.

    Returns
    -------
    plotly.graph_objects.Figure
        The figure, for further customisation.
    """
    import plotly.graph_objects as go

    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("timeseries_interactive expects a DataFrame with a DatetimeIndex.")

    if columns is None:
        columns = _default_columns(df)
        if len(columns) > _MAX_AUTO_COLUMNS:
            warnings.warn(
                f"{len(columns)} columns to plot; showing the first {_MAX_AUTO_COLUMNS}. "
                f"Pass columns=[...] to choose specific ones.")
            columns = columns[:_MAX_AUTO_COLUMNS]
    else:
        columns = [c for c in columns if c in df.columns]

    if not columns:
        raise ValueError(
            "No plottable columns. Size-bin and QC_Flag columns are excluded by "
            "default — pass columns=[...] to plot them explicitly.")

    fig = go.Figure()
    for col in columns:
        # Scattergl (WebGL) keeps long series responsive (e.g. a month at 1-min).
        fig.add_trace(go.Scattergl(x=df.index, y=df[col], name=str(col), mode='lines'))

    fig.update_layout(
        title=title if title is not None else _default_title(df),
        hovermode='x unified',
        template='plotly_white',
        xaxis=dict(title='Time', rangeslider=dict(visible=True)),
        yaxis=dict(title='Value'),
        legend=dict(title='Click to toggle'),
    )

    if save is not None:
        fig.write_html(str(save))
    if show:
        fig.show()
    return fig
