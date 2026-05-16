"""Tests for IGAC (Ion Chromatograph) reader."""
import pytest
from .base import BaseReaderTest


@pytest.mark.igac
class TestIGACReader(BaseReaderTest):
    INSTRUMENT = 'IGAC'
