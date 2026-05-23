# Contributing to AeroViz

Contributions are welcome! For bug reports and feature requests, please use
[GitHub Issues](https://github.com/Alex870521/AeroViz/issues).

## Development setup

Building from source — an editable `pip install -e .`, or any platform without a
pre-built wheel — compiles a bundled Fortran extension (ISORROPIA II), so you
need a Fortran compiler (`gfortran`) plus `meson` / `ninja`:

```bash
# macOS:          brew install gcc
# Debian/Ubuntu:  sudo apt-get install gfortran
# Windows:        use the MSYS2 / mingw-w64 toolchain
pip install -e ".[test,dev]"
pytest
```

## Commits & releases

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
(`type(scope): subject`, e.g. `fix(reader): ...`). Releases are cut with
[Commitizen](https://commitizen-tools.github.io/commitizen/), which derives the
next version from the commit history, updates `docs/CHANGELOG.md`, and tags
`vX.Y.Z` — run the **Bump version** workflow (or `cz bump` locally). Pushing the
tag triggers the Release workflow, which builds and publishes the wheels.
