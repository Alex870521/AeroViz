"""The instrument registry: supported, pending, and removed.

Three categories, three different errors:

* **supported** — a module in ``script/`` and an entry in ``meta``.
* **pending** (``Q-ACSM``) — a real instrument whose reader has not been written
  yet, because no sample export was available to write a parser against. Raises
  ``NotImplementedError``, not the abstract-class ``TypeError`` it used to.
* **removed** (``VOC``, ``Minion``) — pre-aggregated, second-hand datasets:
  somebody else's processed output rather than an instrument's raw log, so there
  was no raw format to parse and the readers only ran generic checks. Raises
  ``KeyError`` carrying migration advice.

These tests pin each category so the distinction cannot erode silently.
"""
import tempfile

import pytest

from AeroViz import RawDataReader
from AeroViz.rawDataReader.config.supported_instruments import meta, pending, removed

REMOVED = ['VOC', 'Minion']
PENDING = ['Q-ACSM']


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


@pytest.mark.parametrize('instrument', PENDING)
def test_pending_instrument_stays_in_the_roster(instrument):
    """A pending instrument is a real one: its native frequency stays documented
    in `meta` even though no reader exists."""
    assert instrument in meta
    assert 'freq' in meta[instrument]
    assert instrument not in removed


@pytest.mark.parametrize('instrument', PENDING)
def test_pending_raises_not_implemented(instrument):
    """Not a TypeError about abstract classes, and not 'invalid instrument'."""
    with tempfile.TemporaryDirectory() as d:
        with pytest.raises(NotImplementedError) as exc:
            RawDataReader(instrument, d)

    message = str(exc.value)
    assert 'not implemented yet' in message
    # Says how to contribute one rather than leaving a dead end.
    assert '_raw_reader' in message


@pytest.mark.parametrize('instrument', PENDING)
def test_pending_has_no_reader_module(instrument):
    import AeroViz.rawDataReader.script as script_module

    assert not hasattr(script_module, instrument)


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
