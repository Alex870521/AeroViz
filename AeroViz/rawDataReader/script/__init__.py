# Auto-import all instrument reader modules dynamically
# New instruments only need to:
# 1. Add a new .py file in this directory
# 2. Add entry to supported_instruments.py meta dict

import importlib
from pathlib import Path

# Get all .py files in this directory (excluding __init__.py)
_script_dir = Path(__file__).parent
_module_files = [
    f.stem for f in _script_dir.glob('*.py')
    if f.stem != '__init__' and not f.stem.startswith('_')
]

# Dynamically import each module
__all__ = []
for _module_name in _module_files:
    try:
        _module = importlib.import_module(f'.{_module_name}', package=__name__)
        globals()[_module_name] = _module
        __all__.append(_module_name)
    except ImportError as e:
        # Skip modules that fail to import (e.g., missing dependencies)
        pass

# Clean up temporary variables
del _script_dir, _module_files, _module_name, _module, importlib, Path
