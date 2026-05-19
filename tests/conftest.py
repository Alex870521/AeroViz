"""
Pytest configuration and fixtures for AeroViz tests.
"""
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# =============================================================================
# Path Configuration
# =============================================================================

# Base path for test fixtures
FIXTURES_PATH = Path(__file__).parent / 'fixtures'
RAW_DATA_PATH = FIXTURES_PATH / 'raw_data'

# All supported instruments
INSTRUMENTS = [
    'AE33', 'AE43', 'APS', 'Aurora', 'BAM1020', 'BC1054',
    'EPA', 'GRIMM', 'IGAC', 'MA350', 'Minion', 'NEPH',
    'OCEC', 'Q-ACSM', 'SMPS', 'TEOM', 'VOC', 'Xact'
]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope='session')
def fixtures_path():
    """Return the path to test fixtures directory."""
    return FIXTURES_PATH


@pytest.fixture(scope='session')
def raw_data_path():
    """Return the path to raw data fixtures directory."""
    return RAW_DATA_PATH


@pytest.fixture(scope='function')
def temp_output_dir():
    """Create a temporary directory for test outputs, cleaned up after test."""
    temp_dir = tempfile.mkdtemp(prefix='aeroviz_test_')
    yield Path(temp_dir)
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope='session')
def default_date_range():
    """Default date range for testing (covers most test data)."""
    return {
        'start': datetime(2024, 1, 1),
        'end': datetime(2024, 12, 31, 23, 59, 59)
    }


# =============================================================================
# Instrument-specific fixtures
# =============================================================================

def _get_instrument_data_path(instrument: str) -> Path:
    """Get the data path for a specific instrument."""
    return RAW_DATA_PATH / instrument


def _has_test_data(instrument: str) -> bool:
    """Check if an instrument has test data files (including in subdirectories)."""
    path = _get_instrument_data_path(instrument)
    if not path.exists():
        return False
    # Check for any data files recursively (including in scenario subdirectories)
    return any(f.is_file() for f in path.rglob('*'))


# Generate fixtures for each instrument
for _instrument in INSTRUMENTS:
    # Create a fixture for each instrument's data path
    exec(f'''
@pytest.fixture(scope='session')
def {_instrument.lower().replace('-', '_')}_data_path():
    """Return the path to {_instrument} test data."""
    path = _get_instrument_data_path('{_instrument}')
    if not _has_test_data('{_instrument}'):
        pytest.skip('{_instrument} test data not available')
    return path
''')


# =============================================================================
# Markers
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "requires_data: mark test as requiring actual data files"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    # Add markers for each instrument (normalize Q-ACSM -> q_acsm to match test files)
    for instrument in INSTRUMENTS:
        marker_name = instrument.lower().replace('-', '_')
        config.addinivalue_line(
            "markers", f"{marker_name}: mark test as {instrument} specific"
        )


# =============================================================================
# Helpers available to all tests
# =============================================================================

@pytest.fixture(scope='session')
def get_instrument_files():
    """Return a function to get all test files for an instrument."""
    def _get_files(instrument: str, pattern: str = '*') -> list[Path]:
        path = _get_instrument_data_path(instrument)
        if not path.exists():
            return []
        return sorted(path.glob(pattern))
    return _get_files


@pytest.fixture(scope='session')
def get_instrument_scenarios():
    """
    Return a function to get test scenarios for an instrument.

    Scenarios are defined by subdirectories in the instrument's data folder:
    - normal/: Standard data files
    - multi_header/: Files with multiple headers (APS, etc.)
    - transposed/: Transposed format files
    - edge_cases/: Edge case files
    """
    def _get_scenarios(instrument: str) -> dict[str, Path]:
        path = _get_instrument_data_path(instrument)
        if not path.exists():
            return {}

        scenarios = {}
        for subdir in path.iterdir():
            if subdir.is_dir():
                scenarios[subdir.name] = subdir

        # If no subdirectories, treat root as 'normal' scenario
        if not scenarios:
            root_files = [f for f in path.iterdir() if f.is_file()]
            if root_files:
                scenarios['normal'] = path

        return scenarios
    return _get_scenarios
