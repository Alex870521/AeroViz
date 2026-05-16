"""Tests for MA350 MicroAeth reader."""
import pytest
from .base import BaseReaderTest


@pytest.mark.ma350
class TestMA350Reader(BaseReaderTest):
    INSTRUMENT = 'MA350'
    STATUS_COLUMN = 'Status'
    EXPECTED_COLUMNS = ['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'abs_375', 'abs_880', 'AAE', 'eBC']
