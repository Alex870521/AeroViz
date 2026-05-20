## Unreleased

## v0.3.0 (2026-05-21)

### BREAKING CHANGE

- Build backend switched from setuptools to **meson-python**. Contributors
  building from source now need `gfortran` in addition to Python deps
  (Linux: `apt install gfortran`; macOS: `brew install gcc`; Windows:
  rtools45). End-user `pip install AeroViz` is unchanged — pip auto-picks
  the prebuilt wheel for the user's platform.
- The bundled `isrpia2.exe` (1.5 MB, 32-bit Windows only) has been
  removed. `isoropia()` now calls the ISORROPIA II Fortran library
  natively via an f2py extension; works on macOS (arm64 + x86_64),
  Linux x86_64, and Windows AMD64. The `path_out` parameter is retained
  but no longer used.
- `setup.py` and `scripts/install_*.{sh,bat}` removed (obsolete with
  meson-python; `pip install AeroViz` covers all use cases).

### Feat

- **chemistry**: cross-platform ISORROPIA II via native f2py extension.
  Same Fortran numerics as the legacy `isrpia2.exe` (sourced from
  GEOS-Chem 14.3.1, original copyright Nenes/Fountoukis/Capps preserved
  in `THIRD_PARTY_NOTICES.md`). ~25x faster on bulk batches (100k rows
  in ~0.38 s).
- **optical**: PyMieScatt-parity additions — angular scattering
  (`scattering_function`, `scattering_function_sd`, `phase_matrix`,
  `nephelometer_truncation_correction`), Aden-Kerker coated-sphere Mie
  (`mie_core_shell`, `mie_core_shell_sd`), iterative RI retrieval
  (`iterative_inversion`, `iterative_inversion_sd`,
  `contour_intersection`).
- Top-level flat-import API across every sub-namespace:
  `from AeroViz import reconstruct_mass, improve, mie, merge_psd, ...`.
- Three independent CI jobs: `quick` (dataProcess, 5 Python versions),
  `readers` (full rawDataReader pipeline, 2 Python versions), and a
  release-only `wheels` job that publishes 4 OS × 5 Python wheels +
  sdist to PyPI on tag push.

### Fix

- **chemistry**: `_basic()` previously did `df_all.columns = nam_lst`,
  which positionally renamed input columns. Inputs whose column order
  differed from `nam_lst` were silently mangled. Now: if all required
  species are present by name, reorder by name; fall back to the
  positional rename otherwise.
- **chemistry**: gas-phase species (NH3 / HNO3 / HCl) now correctly
  converted to µmol/m³ via molecular weights instead of going through
  `convert_mass_to_molar_concentration()` (which produces ppm via the
  ideal-gas law and was unit-mismatched with the particulate inputs).
- Reader test suite was reindexing raw pickles to a 2-year requested
  window for one day of fixture data, ballooning pickles to 500+ MB
  per instrument. Tight per-instrument `date_range` + session-scoped
  DataFrame cache: 9:42 → 14 s (40x), fixtures dir 7.4 GB → 403 MB.
- ISORROPIA II is invoked on macOS/Linux — was a cryptic
  `Exec format error` from the bundled Windows .exe; now just works
  natively.

### Refactor

- Tests reorganised into `tests/test_dataprocess/` so changes to
  post-processing modules don't trigger reader I/O tests. Markers
  (`reader`, `dataprocess`, `optical`, `slow`) registered for `pytest
  -m` filtering.
- Mie engine unification: `mie_theory.py` deleted, `mie.py` (formerly
  `_mie_sd.py`) is the sole vectorised Mie kernel.
  `calculate_mie_efficiencies()` now returns a 7-key dict with
  `Q_ext / Q_sca / Q_abs / g / Q_pr / Q_back / Q_ratio`.

## v0.1.17 (2025-12-14)

### Feat

- Implement QCFlagBuilder system for unified QC workflow
- Add QCRule dataclass for declarative QC rule definition
- Add pre_process.py for unified absorption/scattering coefficient calculation
- Unified QC_Flag column for all instrument data quality marking
- QC Summary output at end of processing with validation results

### Docs

- Update QC_Flag handling documentation for all instruments
- Clarify QC_Flag only in intermediate files, removed from final output
- Update RawDataReader processing flow documentation
- Simplify Technical Specifications table in instruments index

### Refactor

- Simplify rate calculation and remove deter_key dependency
- Unify QC output format across all instrument readers

## v0.1.16 (2025-02-20)

### BREAKING CHANGE

- Complete overhaul from v0.1.9.0 to v0.1.11

### Feat

- enhance rate calculation to use minimum rates across all determinant keys
- **workflow**: add unpublish.yml

### Fix

- repair TEOM parsing and optical scatter key errors
- improve time handling for instrument data and reporting
- improve aerosol data processing and quality control
- improve aerosol data processing and quality control
- RawDataReader and the ReaderLogger class to better handle different environments and edge cases

### Refactor

- **RawDataReader**: simplify configuration and unify output handling
