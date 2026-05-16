"""Tests for Q-ACSM (Aerosol Chemical Speciation Monitor) reader."""
import pytest
from .base import BaseReaderTest


@pytest.mark.q_acsm
class TestQACSMReader(BaseReaderTest):
    INSTRUMENT = 'Q-ACSM'
