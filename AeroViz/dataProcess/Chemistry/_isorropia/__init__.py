"""ISORROPIA II Fortran extension.

The compiled extension (``_ext``) is produced by meson-python from the
Fortran sources in this directory:

- ``isorropiaII_main_mod.F`` — ISORROPIA II thermodynamic equilibrium
  solver, extracted from GEOS-Chem 14.3.1. Copyright 1996-2006
  University of Miami / Carnegie Mellon University / Georgia Institute
  of Technology. See THIRD_PARTY_NOTICES.md.
- ``wrapper.f90`` — thin modern-Fortran wrapper exposing ``solve()`` and
  ``solve_batch()`` for clean f2py bindings.

User-facing API for AeroViz lives in ``AeroViz.chemistry.isoropia()``.
"""

from ._ext import isorropia_wrap as _wrap

solve = _wrap.solve
solve_batch = _wrap.solve_batch

__all__ = ['solve', 'solve_batch']
