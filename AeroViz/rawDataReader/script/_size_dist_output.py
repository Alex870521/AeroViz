"""Shared output handling for size-distribution readers (SMPS, APS).

The canonical reader return value is the ``dN/dlogDp`` distribution — a
DataFrame whose columns are particle diameters. After the parent pipeline
produces that (QC-applied, resampled) frame, :func:`finalize_size_dist`:

* writes the number / surface / volume distributions as sibling CSVs
  (``{prefix}_dNdlogDp.csv`` / ``_dSdlogDp.csv`` / ``_dVdlogDp.csv``);
* computes QC-aligned summary statistics with :func:`AeroViz.psd_stats` and
  writes them to ``{prefix}_stats.csv``;
* optionally appends those statistics to the returned frame when the caller
  passed ``append_stats=True`` (default ``False`` keeps the return value a
  clean diameter-indexed PSD matrix that ``psd_stats`` / ``merge_psd`` /
  ``SizeDist`` can consume directly).

Both ``dS/dlogDp`` and ``dV/dlogDp`` are derived from ``dN/dlogDp``:
``dS = π·d²·dN`` and ``dV = (π/6)·d³·dN``. Which of the four files are written
is chosen with ``size_dist_outputs=`` (default: all). For a year of 6-minute
scans the surface and volume files are ~70–80 MB each and carry no information
the number file does not, so a pipeline that only stores ``dN/dlogDp`` can ask
for ``('number', 'stats')`` and skip two writes.
"""
import numpy as np

#: Names accepted by ``size_dist_outputs``.
SIZE_DIST_OUTPUTS = ('number', 'surface', 'volume', 'stats')


def wanted_outputs(kwargs) -> set:
    """Resolve ``size_dist_outputs`` from reader kwargs (None = everything)."""
    chosen = kwargs.get('size_dist_outputs')
    if chosen is None:
        return set(SIZE_DIST_OUTPUTS)
    if isinstance(chosen, str):
        chosen = (chosen,)
    chosen = set(chosen)
    unknown = chosen - set(SIZE_DIST_OUTPUTS)
    if unknown:
        raise ValueError(
            f"size_dist_outputs: unknown {sorted(unknown)}; choose from {SIZE_DIST_OUTPUTS}")
    return chosen


def _diameter_columns(df):
    """Diameter (float-labelled) columns, i.e. the size bins."""
    return [c for c in df.columns if isinstance(c, (int, float))]


def finalize_size_dist(reader, dist, *, unit):
    """Persist N/S/V distributions + a stats sidecar; optionally append stats.

    Parameters
    ----------
    reader : AbstractReader
        The reader instance (supplies output paths, logger and ``kwargs``).
    dist : pandas.DataFrame
        The ``dN/dlogDp`` frame returned by the parent ``__call__`` (diameters
        as columns; may also carry a status column on the ``qc=False`` path).
    unit : {'nm', 'um'}
        Diameter unit of the columns (SMPS → nm, APS → um); passed to
        ``psd_stats`` so weighted statistics use the right scale.

    Returns
    -------
    pandas.DataFrame
        ``dist`` unchanged, or with the statistics columns appended when the
        caller requested ``append_stats=True``.
    """
    from AeroViz.size import psd_stats
    from AeroViz.dataProcess.SizeDistr.units import DN_DLOGDP, UNIT_ATTR

    # The readers convert every supported export to dN/dlogDp while parsing,
    # so this is what the returned frame is in; `source_units` (stamped by the
    # reader core) says what any converted files were originally.
    dist.attrs[UNIT_ATTR] = DN_DLOGDP

    bins = dist[_diameter_columns(dist)]
    if bins.empty or bins.dropna(how='all').empty:
        return dist

    prefix = reader._output_prefix
    dp = np.asarray(bins.columns, dtype=float)
    wanted = wanted_outputs(reader.kwargs)
    append_stats = reader.kwargs.get('append_stats', False)

    # Number / surface / volume distributions (dX/dlogDp) — only the ones asked for
    # Each product goes through the reader's writer: output_split layout and
    # "unchanged → don't rewrite" apply to the sidecars exactly as to the main CSV.
    if 'number' in wanted:
        reader._write_product(f'{prefix}_dNdlogDp', bins.round(4))
    if 'surface' in wanted:
        reader._write_product(f'{prefix}_dSdlogDp', (bins * np.pi * dp ** 2).round(4))
    if 'volume' in wanted:
        reader._write_product(f'{prefix}_dVdlogDp', (bins * np.pi * dp ** 3 / 6).round(4))

    if 'stats' not in wanted and not append_stats:
        return dist

    # QC-aligned summary statistics (the frame is already QC-masked + resampled)
    try:
        stats = psd_stats(bins, unit=unit,
                          bin_range=(float(dp.min()), float(dp.max())))['other']
    except Exception as e:  # statistics are a convenience — never fail the read
        reader.logger.warning(f"Could not compute statistics sidecar: {e}")
        return dist

    if 'stats' in wanted:
        reader._write_product(f'{prefix}_stats', stats.round(4))

    if append_stats:
        from pandas import concat
        out = concat([bins, stats], axis=1)
        out.attrs = dict(dist.attrs)
        return out

    return dist
