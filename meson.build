project(
  'AeroViz',
  ['c', 'fortran'],
  version: '0.3.0',
  meson_version: '>=1.2.0',
  default_options: [
    'buildtype=release',
    'fortran_std=legacy',  # ISORROPIA II uses F77 IMPLICIT REAL conventions
  ],
)

# --- Python + numpy / f2py discovery ----------------------------------
py = import('python').find_installation(pure: false)
py_dep = py.dependency()

# numpy + f2py header paths come back as absolute paths to site-packages,
# which can't be passed straight into include_directories(). Emit them
# as raw -I compile flags via a declare_dependency() bundle instead.
incdir_numpy = run_command(
  py, ['-c', 'import numpy; print(numpy.get_include())'],
  check: true,
).stdout().strip()

incdir_f2py = run_command(
  py, ['-c', 'import numpy.f2py; print(numpy.f2py.get_include())'],
  check: true,
).stdout().strip()

np_dep = declare_dependency(
  compile_args: ['-I' + incdir_numpy, '-I' + incdir_f2py],
)

# fortranobject.c ships with numpy; f2py-generated wrappers need it.
fortranobject_c = incdir_f2py / 'fortranobject.c'

# --- Pure-Python install ----------------------------------------------
# Copies the entire AeroViz/ tree into the site-packages layout.
# Meson's install_subdir handles the recursion that setuptools used to
# do via package-data wildcards.
install_subdir(
  'AeroViz',
  install_dir: py.get_install_dir(),
  exclude_directories: ['__pycache__', 'dataProcess/Chemistry/_isorropia'],
)

# Re-install the _isorropia package's Python sources separately so we
# can exclude the Fortran sources (build-time only).
py.install_sources(
  'AeroViz/dataProcess/Chemistry/_isorropia/__init__.py',
  'AeroViz/dataProcess/Chemistry/_isorropia/THIRD_PARTY_NOTICES.md',
  subdir: 'AeroViz/dataProcess/Chemistry/_isorropia',
)

# --- Native extension subdirectory ------------------------------------
subdir('AeroViz/dataProcess/Chemistry/_isorropia')
