"""`to_netcdf` / `read_netcdf` — a reader result as a CF-style NetCDF file and back."""
import shutil

import numpy as np
import pandas as pd
import pytest

xr = pytest.importorskip('xarray')
pytest.importorskip('netCDF4')

from AeroViz import RawDataReader, to_netcdf, read_netcdf
from AeroViz.rawDataReader.netcdf import to_dataset, _nc_name, _units_for


@pytest.fixture
def ae33(raw_data_path, tmp_path):
    src = raw_data_path / 'AE33' / 'normal'
    if not src.exists() or not any(src.iterdir()):
        pytest.skip('AE33/normal fixture not available')
    dst = tmp_path / 'NZ_AE33'
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('*_outputs'))
    return RawDataReader('AE33', dst, start='2025-03-01', end='2025-03-31', reset=True, quiet=True,
                         save_csv=False, mean_freq='1h')


def test_round_trip_keeps_values_and_attrs(ae33, tmp_path):
    out = to_netcdf(ae33, tmp_path / 'nc' / 'ae33.nc')
    back = read_netcdf(out)
    for col in ('BC6', 'eBC', 'AAE', 'BB(%)', 'Delta-C'):         # names NetCDF can't hold come back intact
        np.testing.assert_allclose(back[col].to_numpy(), ae33[col].to_numpy(), equal_nan=True)
    assert back.attrs['instrument'] == 'AE33' and back.attrs['station'] == 'NZ'
    assert back.attrs['coverage_start'] == ae33.attrs['coverage_start']       # Timestamp restored
    assert back.attrs['qc_rules'][0]['rule'] == ae33.attrs['qc_rules'][0]['rule']   # JSON restored
    assert back.attrs['total_rate'] == pytest.approx(ae33.attrs['total_rate'])


def test_global_attributes_are_cf_style(ae33, tmp_path):
    out = to_netcdf(ae33, tmp_path / 'ae33.nc', title='NZ AE33 test')
    with xr.open_dataset(out) as ds:
        assert ds.attrs['Conventions'] == 'CF-1.8'
        assert ds.attrs['title'] == 'NZ AE33 test'
        assert ds.attrs['source'].startswith('AeroViz')
        assert ds['BC6'].attrs == {'long_name': 'BC6', 'units': 'ng m-3'}
        assert ds['abs_550'].attrs['units'] == 'Mm-1'
        assert ds['BB'].attrs['long_name'] == 'BB(%)' and ds['BB'].attrs['units'] == '%'
        assert ds['time'].attrs['standard_name'] == 'time'
        assert not any(k for k, v in ds.attrs.items() if v is None)


def test_size_distribution_becomes_a_diameter_dimension(tmp_path):
    dp = np.geomspace(10, 500, 40)
    idx = pd.date_range('2026-01-01', periods=6, freq='6min')
    df = pd.DataFrame(np.random.default_rng(0).random((6, 40)) * 1e3, index=idx, columns=dp)
    df['total_num_all'] = df.sum(axis=1)
    df.attrs.update(instrument='SMPS', station='TP', raw_freq='6min')

    ds = to_dataset(df)
    assert ds['dN_dlogDp'].dims == ('time', 'diameter') and ds['dN_dlogDp'].shape == (6, 40)
    assert ds['diameter'].attrs['units'] == 'nm'
    assert ds['total_num_all'].attrs['units'] == 'cm-3'

    back = read_netcdf(to_netcdf(df, tmp_path / 'smps.nc'))
    np.testing.assert_allclose(back[dp].to_numpy(), df[dp].to_numpy(), rtol=1e-6)   # float32 on disk
    assert list(back.columns[-1:]) == ['total_num_all']


def test_aps_diameters_are_micrometres(tmp_path):
    dp = np.geomspace(0.5, 20, 30)
    df = pd.DataFrame(np.ones((3, 30)), index=pd.date_range('2026-01-01', periods=3, freq='h'), columns=dp)
    df.attrs['instrument'] = 'APS'
    assert to_dataset(df)['diameter'].attrs['units'] == 'um'
    assert to_dataset(df, diameter_unit='nm')['diameter'].attrs['units'] == 'nm'


def test_tz_aware_index_is_written_as_utc(tmp_path):
    idx = pd.date_range('2026-01-01 08:00', periods=3, freq='h', tz='Asia/Taipei')
    df = pd.DataFrame({'x': [1.0, 2.0, 3.0]}, index=idx)
    ds = to_dataset(df)
    assert str(ds['time'].values[0]).startswith('2026-01-01T00:00')
    assert 'Asia/Taipei' in ds['time'].attrs['note']


def test_non_datetime_index_is_rejected():
    with pytest.raises(TypeError, match='DatetimeIndex'):
        to_dataset(pd.DataFrame({'x': [1.0]}))


@pytest.mark.parametrize('col,name,unit', [
    ('BB(%)', 'BB', '%'), ('Delta-C', 'Delta_C', 'ng m-3'), ('dN/dlogDp', 'dN_dlogDp', None),
    ('abs_370', 'abs_370', 'Mm-1'), ('GMD_num_all', 'GMD_num_all', 'nm'), ('11.8', 'v_11_8', None),
])
def test_names_and_units(col, name, unit):
    assert _nc_name(col) == name and _units_for(col) == unit
