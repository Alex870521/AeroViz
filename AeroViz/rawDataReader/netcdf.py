"""NetCDF export of a reader result — CF-style, self-describing, citable.

``df.attrs`` already carries provenance, coverage, native frequency, QC rates
and the applied QC configuration. Written as NetCDF global attributes next to
the data, the file answers "what is this, from where, how was it screened"
without the Python session that made it. Size distributions become a proper
``(time, diameter)`` variable instead of a few hundred float-named columns.

xarray and a NetCDF backend (``netCDF4`` or ``h5netcdf``) are optional —
``pip install AeroViz[netcdf]``.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

__all__ = ['to_netcdf', 'read_netcdf', 'to_dataset']

#: Units for columns the readers produce, by exact name or prefix.
UNITS = {
    'BC': 'ng m-3', 'eBC': 'ng m-3', 'Delta-C': 'ng m-3', 'BB(%)': '%',
    'abs_': 'Mm-1', 'sca_': 'Mm-1', 'ext_': 'Mm-1', 'AAE': '1', 'SAE': '1',
    'B': 'Mm-1', 'G': 'Mm-1', 'R': 'Mm-1', 'BB': 'Mm-1', 'BG': 'Mm-1', 'BR': 'Mm-1',
    'PM_': 'ug m-3', 'Volatile_Fraction': '1',
    'Thermal_OC': 'ugC m-3', 'Thermal_EC': 'ugC m-3', 'Optical_OC': 'ugC m-3',
    'Optical_EC': 'ugC m-3', 'TC': 'ugC m-3', 'OC': 'ugC m-3', 'PC': 'ugC m-3',
    'total_num_': 'cm-3', 'GMD_': 'nm', 'GSD_': '1', 'mode_': 'nm',
    'RH': '%', 'Temp': 'degC',
}

_DIST_VARIABLE = {'SMPS': 'dN_dlogDp', 'APS': 'dN_dlogDp', 'GRIMM': 'dN_dlogDp'}
_DIAMETER_UNIT = {'APS': 'um'}


def _require_xarray():
    try:
        import xarray as xr
    except ImportError as e:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            "NetCDF export needs xarray and a backend: pip install 'AeroViz[netcdf]'") from e
    return xr


def _units_for(column: str) -> str | None:
    if column in UNITS:
        return UNITS[column]
    for prefix, unit in UNITS.items():
        if prefix.endswith('_') and column.startswith(prefix):
            return unit
    if column.startswith('BC') and column[2:].isdigit():
        return UNITS['BC']
    return None


def _nc_name(column) -> str:
    """A NetCDF-safe variable name; the original stays in ``long_name``."""
    name = ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in str(column)).strip('_')
    if not name or name[0].isdigit():
        name = f'v_{name}'
    return name


def _attr_value(value):
    """Coerce one ``df.attrs`` value to something NetCDF can hold (str/number/array)."""
    if value is None or isinstance(value, bool):
        return None if value is None else int(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, (int, float, str, np.integer, np.floating)):
        return value
    return json.dumps(value, default=str, ensure_ascii=False)


def _split_columns(df: pd.DataFrame):
    """Columns that are diameters (float-convertible) vs. everything else."""
    diam, other = [], []
    for c in df.columns:
        try:
            float(c)
            diam.append(c)
        except (TypeError, ValueError):
            other.append(c)
    return diam, other


def to_dataset(df: pd.DataFrame, *, variable: str | None = None,
               diameter_unit: str | None = None, title: str | None = None):
    """Build the ``xarray.Dataset`` that :func:`to_netcdf` writes.

    Float-named columns become a ``diameter`` dimension holding ``variable``
    (default ``dN_dlogDp``); every other column becomes a ``(time,)`` variable
    with its original name in ``long_name`` and units where known.
    """
    xr = _require_xarray()
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError('to_netcdf expects a DatetimeIndex (a RawDataReader result)')
    a = df.attrs
    instrument = a.get('instrument')

    time = df.index
    tz_note = None
    if time.tz is not None:
        tz_note = str(time.tz)
        time = time.tz_convert('UTC').tz_localize(None)
    coords = {'time': ('time', time.values)}
    data_vars = {}

    diam, other = _split_columns(df)
    if len(diam) >= 3:
        var = variable or _DIST_VARIABLE.get(instrument, 'dN_dlogDp')
        coords['diameter'] = ('diameter', np.asarray([float(c) for c in diam]),
                              {'long_name': 'particle diameter',
                               'units': diameter_unit or _DIAMETER_UNIT.get(instrument, 'nm')})
        data_vars[var] = (('time', 'diameter'), df[diam].to_numpy(dtype=float),
                          {'long_name': 'number size distribution dN/dlogDp', 'units': 'cm-3'})
    else:
        other = list(df.columns)

    for c in other:
        s = df[c]
        if s.dtype == bool:
            values, attrs = s.to_numpy(dtype='int8'), {'flag_values': np.array([0, 1], 'int8'),
                                                       'flag_meanings': 'false true'}
        elif pd.api.types.is_numeric_dtype(s):
            values, attrs = s.to_numpy(dtype=float), {}
        else:
            values, attrs = s.astype(object).where(s.notna(), '').astype(str).to_numpy(), {}
        attrs['long_name'] = str(c)
        unit = _units_for(str(c))
        if unit:
            attrs['units'] = unit
        data_vars[_nc_name(c)] = (('time',), values, attrs)

    ds = xr.Dataset(data_vars, coords=coords)
    ds['time'].attrs.update({'long_name': 'time', 'standard_name': 'time'})
    if tz_note:
        ds['time'].attrs['note'] = f'converted to UTC from {tz_note}'

    for key, value in a.items():
        v = _attr_value(value)
        if v is not None:
            ds.attrs[key] = v
    ds.attrs.update({
        'Conventions': 'CF-1.8',
        'featureType': 'timeSeries',
        'title': title or f"{a.get('station', '')} {instrument or ''} {a.get('mean_freq') or a.get('raw_freq') or ''}".strip(),
        'source': f"AeroViz {a.get('aeroviz_version') or ''} RawDataReader".strip(),
        'history': f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} AeroViz.to_netcdf",
    })
    return ds


def to_netcdf(df: pd.DataFrame, path: Path | str, *, variable: str | None = None,
              diameter_unit: str | None = None, title: str | None = None,
              engine: str | None = None) -> Path:
    """Write a ``RawDataReader`` result to a CF-style NetCDF file.

    Parameters
    ----------
    df : DataFrame
        A reader result (``DatetimeIndex``; ``df.attrs`` become global attributes).
    path : Path or str
        Output ``.nc`` file; parent folders are created.
    variable : str, optional
        Name of the 2-D size-distribution variable (default ``dN_dlogDp``).
    diameter_unit : str, optional
        Units attribute of the diameter axis (default ``nm``; ``um`` for APS).
    title : str, optional
        Global ``title`` attribute (default ``"<station> <instrument> <freq>"``).
    engine : str, optional
        xarray backend (``netcdf4`` / ``h5netcdf``); default lets xarray choose.
    """
    ds = to_dataset(df, variable=variable, diameter_unit=diameter_unit, title=title)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoding = {'time': {'units': 'seconds since 1970-01-01T00:00:00', 'dtype': 'float64'}}
    for name, var in ds.data_vars.items():
        if var.ndim == 2:
            encoding[name] = {'zlib': True, 'complevel': 4, 'dtype': 'float32'}
    ds.to_netcdf(path, engine=engine, encoding=encoding)
    ds.close()
    return path


def read_netcdf(path: Path | str) -> pd.DataFrame:
    """Read a file written by :func:`to_netcdf` back into a DataFrame.

    The size-distribution variable comes back as float-named columns, other
    variables under their ``long_name`` (the original column), and the global
    attributes under ``df.attrs`` with timestamps and JSON values restored.
    """
    xr = _require_xarray()
    with xr.open_dataset(path) as ds:
        ds = ds.load()
    frames = []
    for name, var in ds.data_vars.items():
        if var.ndim == 2:
            frames.append(pd.DataFrame(var.values, index=ds['time'].values,
                                       columns=ds['diameter'].values.astype(float)))
        else:
            values = var.values
            if 'flag_meanings' in var.attrs and var.attrs.get('flag_meanings') == 'false true':
                values = values.astype(bool)
            frames.append(pd.Series(values, index=ds['time'].values,
                                    name=var.attrs.get('long_name', name)))
    df = pd.concat(frames, axis=1) if frames else pd.DataFrame(index=ds['time'].values)
    df.index.name = 'time'
    for key, value in ds.attrs.items():
        if isinstance(value, str):
            if key.endswith(('_start', '_end')) or key == 'processed_at':
                try:
                    value = pd.Timestamp(value)
                except ValueError:
                    pass
            elif value[:1] in '{[':
                try:
                    value = json.loads(value)
                except ValueError:
                    pass
        df.attrs[key] = value
    return df
