"""Platform-guard tests for isoropia().

Full numerical correctness is not tested here — that requires a working
``isrpia2.exe``, which only runs on Windows. These tests focus on the
clean failure mode on unsupported platforms.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from AeroViz.chemistry import isoropia
from AeroViz.dataProcess.Chemistry._isoropia import _check_platform_supported


pytestmark = pytest.mark.dataprocess


@pytest.fixture
def minimal_chem_df():
    """Tiny chemistry input the ISORROPIA wrapper would accept."""
    return pd.DataFrame({
        'NH4+': [1.0],
        'NH3': [0.1],
        'HNO3': [0.05],
        'NO3-': [0.5],
        'HCl': [0.01],
        'Cl-': [0.1],
        'Na+': [0.1],
        'SO42-': [2.0],
        'Ca2+': [0.1],
        'K+': [0.05],
        'Mg2+': [0.02],
        'RH': [80],
        'temp': [25],
    })


class TestPlatformGuard:
    @pytest.mark.skipif(sys.platform == 'win32',
                        reason="On Windows the guard correctly allows execution")
    def test_raises_on_non_windows(self, minimal_chem_df, tmp_path):
        """macOS / Linux should get a clear RuntimeError, not a subprocess crash."""
        with pytest.raises(RuntimeError, match="cannot run on this platform"):
            isoropia(minimal_chem_df, path_out=tmp_path)

    @pytest.mark.skipif(sys.platform == 'win32',
                        reason="On Windows the guard correctly allows execution")
    def test_error_mentions_workaround(self, minimal_chem_df, tmp_path):
        """The error should tell the user where to get a native binary."""
        with pytest.raises(RuntimeError) as excinfo:
            isoropia(minimal_chem_df, path_out=tmp_path)
        msg = str(excinfo.value)
        # Surface key bits so users aren't stuck guessing
        assert sys.platform in msg
        assert 'isrpia2.exe' in msg
        assert 'epfl.ch' in msg.lower() or 'binary' in msg.lower()

    def test_check_function_accepts_win32(self):
        """Spoof sys.platform=win32 and verify the guard lets it through."""
        with patch.object(sys, 'platform', 'win32'):
            _check_platform_supported()  # should not raise

    @pytest.mark.parametrize('plat', ['darwin', 'linux', 'cygwin', 'aix'])
    def test_check_function_rejects_others(self, plat):
        with patch.object(sys, 'platform', plat):
            with pytest.raises(RuntimeError, match="cannot run on this platform"):
                _check_platform_supported()
