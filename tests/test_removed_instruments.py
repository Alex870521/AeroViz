"""Instruments withdrawn from RawDataReader.

VOC and Minion were pre-aggregated, second-hand datasets — somebody else's
processed output rather than an instrument's raw log — so there was no raw
format for a reader to parse and the readers only performed generic checks.
They were removed; these tests pin the removal so a reader for either cannot
reappear by accident, and so existing scripts keep getting actionable advice
instead of a bare "not a valid instrument".
"""
import tempfile

import pytest

from AeroViz import RawDataReader
from AeroViz.rawDataReader.config.supported_instruments import meta, removed

REMOVED = ['VOC', 'Minion']


@pytest.mark.parametrize('instrument', REMOVED)
def test_not_a_supported_instrument(instrument):
    """The instrument is gone from the reader config."""
    assert instrument not in meta


@pytest.mark.parametrize('instrument', REMOVED)
def test_reader_module_is_gone(instrument):
    """No reader module is importable for it."""
    import AeroViz.rawDataReader.script as script_module

    assert not hasattr(script_module, instrument)


@pytest.mark.parametrize('instrument', REMOVED)
def test_raises_with_migration_advice(instrument):
    """Calling it raises KeyError carrying the migration advice, not a bare
    'not valid' listing."""
    with tempfile.TemporaryDirectory() as d:
        with pytest.raises(KeyError) as exc:
            RawDataReader(instrument, d)

    message = str(exc.value)
    assert 'no longer read by RawDataReader' in message
    assert 'pre-aggregated' in message
    assert removed[instrument][:40] in message


def test_voc_advice_points_at_the_process_api():
    """VOC users need voc_potentials, not a reader."""
    assert 'voc_potentials' in removed['VOC']


def test_voc_processing_still_works_from_a_plain_frame():
    """Removing the reader must not touch the VOC processing path: a DataFrame
    read by the user still flows through voc_potentials."""
    import pandas as pd

    from AeroViz import voc_potentials

    df = pd.DataFrame(
        {'Benzene': [1.0, 1.5], 'Toluene': [2.0, 2.5], 'Isoprene': [0.5, 0.6]},
        index=pd.date_range('2024-01-01', periods=2, freq='1h'),
    )
    result = voc_potentials(df)

    assert isinstance(result, dict)
    assert 'Conc' in result
