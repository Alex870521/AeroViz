"""`size_dist_unit` in df.attrs: parsed, converted, and checked before computing."""
import numpy as np
import pandas as pd
import pytest

from AeroViz import merge_psd, psd_stats
from AeroViz.dataProcess.SizeDistr._size_dist import SizeDist, bin_widths
from AeroViz.dataProcess.SizeDistr.units import (
    DN_DLOGDP, UNIT_ATTR, ExportUnit, check_unit, parse_export_unit, to_dndlogdp)

DP = np.array([20.0, 50.0, 100.0, 200.0, 400.0])


def _psd(unit=None):
    df = pd.DataFrame([[100.0, 800.0, 1200.0, 400.0, 50.0]] * 3, columns=DP,
                      index=pd.date_range('2026-01-01', periods=3, freq='h'))
    if unit is not None:
        df.attrs[UNIT_ATTR] = unit
    return df


@pytest.mark.parametrize('units, weight, expected', [
    (None, None, ('N', True)),
    ('dN/dlogDp', None, ('N', True)), ('dN', None, ('N', False)),
    ('dS/dlogDp', None, ('S', True)), ('dM', None, ('M', False)),
    ('Raw Counts', None, None), ('%dN', None, None), ('dN/dlggDp', None, None),
    ('dw/dlogDp', 'Number', ('N', True)), ('dW/dlogDp', 'Volume', ('V', True)),
    ('Concentration (dW)', 'Number', ('N', False)), ('Concentration (DW)', 'Surface', ('S', False)),
    ('% Concentration', 'Number', None), ('dW/dlogDp', 'Charge', None),
])
def test_parse_export_unit(units, weight, expected):
    got = parse_export_unit(units, weight)
    assert got == (None if expected is None else ExportUnit(*expected))


def test_to_dndlogdp_inverts_to_surface_and_volume():
    n = _psd()
    psd = SizeDist(n)
    for derived, moment in ((psd.to_surface(), 'S'), (psd.to_volume(), 'V')):
        back = to_dndlogdp(derived, ExportUnit(moment, True), dp_unit='nm')
        pd.testing.assert_frame_equal(back, n, check_dtype=False)


def test_to_dndlogdp_per_channel_uses_the_given_width():
    n = _psd()
    per_channel = n * (1 / 64)
    back = to_dndlogdp(per_channel, ExportUnit('N', False), dp_unit='nm', dlogdp=1 / 64)
    pd.testing.assert_frame_equal(back, n, check_dtype=False)
    default = to_dndlogdp(n * bin_widths(DP), ExportUnit('N', False), dp_unit='nm')
    pd.testing.assert_frame_equal(default, n, check_dtype=False)


def test_mass_needs_density_and_a_verified_unit():
    with pytest.raises(ValueError, match='density'):
        to_dndlogdp(_psd(), ExportUnit('M', True), dp_unit='um')
    with pytest.raises(ValueError, match='verified'):
        to_dndlogdp(_psd(), ExportUnit('M', True), dp_unit='nm', density=1.5)


def test_check_unit():
    check_unit(_psd(), DN_DLOGDP, 'x')                 # no unit recorded: caller's word
    check_unit(_psd(DN_DLOGDP), DN_DLOGDP, 'x')
    with pytest.raises(ValueError, match='dS/dlogDp'):
        check_unit(_psd('dS/dlogDp'), DN_DLOGDP, 'x')


class TestCalculationsCheckTheUnitFirst:
    def test_sizedist_refuses_a_mismatched_frame(self):
        with pytest.raises(ValueError, match='SizeDist'):
            SizeDist(_psd('dV/dlogDp'), weighting='n')
        SizeDist(_psd('dV/dlogDp'), weighting='v')       # declared as volume: fine
        SizeDist(_psd('dN'), state='dN', weighting='n')

    def test_derived_distributions_carry_their_unit(self):
        psd = SizeDist(_psd(DN_DLOGDP))
        surface, volume = psd.to_surface(), psd.to_volume()
        assert surface.attrs[UNIT_ATTR] == 'dS/dlogDp'
        assert volume.attrs[UNIT_ATTR] == 'dV/dlogDp'
        with pytest.raises(ValueError):
            psd_stats(surface)                            # a surface distribution is not dN/dlogDp
        SizeDist(surface, weighting='s')

    def test_psd_stats_checks_against_input_type(self):
        psd_stats(_psd(DN_DLOGDP), bin_range=(DP.min(), DP.max()))
        psd_stats(_psd('dN'), bin_range=(DP.min(), DP.max()), input_type='raw')
        with pytest.raises(ValueError, match='psd_stats'):
            psd_stats(_psd('dN'), bin_range=(DP.min(), DP.max()))

    def test_merge_psd_checks_both_inputs(self):
        with pytest.raises(ValueError, match='df_aps'):
            merge_psd(_psd(DN_DLOGDP), _psd('dM'), version=1)
