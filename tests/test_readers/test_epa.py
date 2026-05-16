"""Tests for EPA (Taiwan EPA Air Quality) reader."""
import pytest
from .base import BaseReaderTest


@pytest.mark.epa
class TestEPAReader(BaseReaderTest):
    INSTRUMENT = 'EPA'
