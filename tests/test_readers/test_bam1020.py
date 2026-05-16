"""Tests for BAM1020 Beta Attenuation Monitor reader."""
import pytest
from .base import BaseReaderTest


@pytest.mark.bam1020
class TestBAM1020Reader(BaseReaderTest):
    INSTRUMENT = 'BAM1020'
    EXPECTED_COLUMNS = ['Conc', 'QC_Flag']
