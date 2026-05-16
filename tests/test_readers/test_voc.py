"""Tests for VOC (Volatile Organic Compounds) reader."""
import pytest
from .base import BaseReaderTest


@pytest.mark.voc
class TestVOCReader(BaseReaderTest):
    INSTRUMENT = 'VOC'
