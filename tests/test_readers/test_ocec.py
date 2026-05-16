"""Tests for OCEC (Sunset OC/EC Analyzer) reader."""
import pytest
from .base import BaseReaderTest


@pytest.mark.ocec
class TestOCECReader(BaseReaderTest):
    INSTRUMENT = 'OCEC'
    EXPECTED_COLUMNS = ['OC', 'EC', 'TC', 'QC_Flag']
