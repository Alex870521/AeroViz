# Contributing to AeroViz

Thanks for your interest in improving AeroViz! Bug reports, feature requests,
documentation fixes, and new instrument readers are all welcome.

- **Questions, bugs, ideas:** open a [GitHub Issue](https://github.com/Alex870521/AeroViz/issues).
- **Code changes:** fork, branch, and open a pull request (see below).

## Development setup

Building from source — an editable `pip install -e .`, or any platform without a
pre-built wheel — compiles a bundled Fortran extension (ISORROPIA II), so you
need a Fortran compiler (`gfortran`) plus `meson` / `ninja`:

```bash
# Install a Fortran toolchain first:
#   macOS:          brew install gcc
#   Debian/Ubuntu:  sudo apt-get install gfortran
#   Windows:        use the MSYS2 / mingw-w64 toolchain

git clone https://github.com/Alex870521/AeroViz.git
cd AeroViz
pip install -e ".[test,dev]"
```

## Running tests

```bash
pytest                      # full suite
pytest tests/test_readers   # just the instrument readers
```

The reader tests run against small fixtures in `tests/fixtures/raw_data/`. Keep
the requested date ranges tight — `RawDataReader` reindexes to the requested
window, so a wide range over a small fixture inflates the cached pickle.

## Code style

Match the style of the surrounding code. The `dev` extra installs `black`,
`isort`, `flake8`, and `mypy` if you'd like to format and lint locally; none are
enforced in CI, so use your judgement and keep diffs focused.

## Commit messages

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
`type(scope): subject`, e.g. `fix(reader): handle empty AE33 file`. Common types
are `feat`, `fix`, `docs`, `refactor`, `test`, `ci`, `chore`. The commit history
drives the changelog and the next version number, so a clear subject matters.

## Pull requests

1. Branch off `main`.
2. Make focused changes with conventional-commit messages.
3. Add or update tests, and run `pytest`.
4. Update the docs (`README.md`, `docs/`, or the relevant docstring) if you
   changed behaviour.
5. Open the PR with a short description of the what and why.

## Adding a new instrument

Instrument readers are auto-discovered — there's no central registry to edit.
Two steps:

1. **Create `AeroViz/rawDataReader/script/<NAME>.py`** with a `Reader` subclass.
   Implement `_raw_reader` (parse one file into a DataFrame with a
   `DatetimeIndex`) and `_QC` (flag rows via the QC builder); add `_process` for
   derived parameters if needed.

   ```python
   from AeroViz.rawDataReader.core import AbstractReader, QCFlagBuilder, QCRule


   class Reader(AbstractReader):
       nam = '<NAME>'

       def _raw_reader(self, file):
           df = ...  # parse `file` -> DataFrame indexed by time
           return df

       def _QC(self, df):
           qc = QCFlagBuilder()
           qc.add_rules([
               QCRule(name='Invalid', condition=lambda d: ..., description='...'),
           ])
           return qc.apply(df)
   ```

2. **Register it in `AeroViz/rawDataReader/config/supported_instruments.py`** by
   adding an entry to the `meta` dict:

   ```python
   "<NAME>": {"pattern": ["*.csv"], "freq": "1h"},
   ```

   `pattern` is the glob(s) for the raw files; `freq` is a fallback resolution
   (the reader auto-detects the real frequency per file).

3. Add a fixture under `tests/fixtures/raw_data/<NAME>/normal/` and a test that
   subclasses `BaseReaderTest` in `tests/test_readers/`.

The file in `script/` is imported automatically on startup, so once `meta` knows
about it, `RawDataReader('<NAME>', ...)` just works.

## Releases (maintainers)

Releases are cut with [Commitizen](https://commitizen-tools.github.io/commitizen/),
which derives the next version from the commit history, updates
`docs/CHANGELOG.md`, and tags `vX.Y.Z`:

- Run the **Bump version** workflow from the Actions tab, or `cz bump` locally
  followed by `git push --follow-tags`.
- Pushing the `vX.Y.Z` tag triggers the **Release** workflow, which builds the
  wheels and publishes to PyPI via OIDC.
