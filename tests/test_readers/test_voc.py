"""Tests for VOC (Volatile Organic Compounds) reader."""
import tempfile
import warnings

import pytest

from .base import BaseReaderTest


@pytest.mark.voc
class TestVOCReader(BaseReaderTest):
    INSTRUMENT = 'VOC'


@pytest.mark.voc
def test_voc_reader_is_deprecated():
    """Instantiating the VOC reader emits a DeprecationWarning (it is a thin
    CSV loader; users should read the CSV directly and call voc_potentials)."""
    from AeroViz.rawDataReader.script.VOC import Reader

    with tempfile.TemporaryDirectory() as d:
        with pytest.warns(DeprecationWarning, match="deprecated"):
            Reader(path=d, qc=False)
