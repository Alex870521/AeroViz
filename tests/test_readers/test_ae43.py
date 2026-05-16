"""Tests for AE43 Aethalometer reader."""
import pytest
from .base import BaseReaderTest


@pytest.mark.ae43
class TestAE43Reader(BaseReaderTest):
    INSTRUMENT = 'AE43'
    STATUS_COLUMN = 'Status'
    EXPECTED_COLUMNS = ['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7', 'abs_370', 'abs_880', 'AAE', 'eBC']
