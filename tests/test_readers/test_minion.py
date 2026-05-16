"""Tests for Minion sensor reader."""
import pytest
from .base import BaseReaderTest


@pytest.mark.minion
class TestMinionReader(BaseReaderTest):
    INSTRUMENT = 'Minion'
