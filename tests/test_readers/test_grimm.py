"""Tests for GRIMM Optical Particle Counter reader."""
import pytest
from .base import BaseReaderTest


@pytest.mark.grimm
class TestGRIMMReader(BaseReaderTest):
    INSTRUMENT = 'GRIMM'
