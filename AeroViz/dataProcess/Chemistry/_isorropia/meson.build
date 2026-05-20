# ISORROPIA II f2py extension build
#
# Compiles the F77 source (isorropiaII_main_mod.F) + F90 wrapper
# (wrapper.f90) + f2py-generated C glue into the extension module
#   AeroViz.dataProcess.Chemistry._isorropia._ext

fortran_args = [
  '-fdefault-real-8',
  '-fdefault-double-8',
  '-w',  # silence the legacy F77 source's warnings
]

# Generate f2py glue (C module + F90 wrapper) at build time.
# `only:` keeps f2py from scanning all 163 subroutines in the F77 file.
# Our wrapper is F90 so f2py only emits the .c + .f90 wrappers (no F77
# pywrappers.f), which keeps the custom_target outputs tidy.
f2py_output = custom_target(
  '_ext_f2py_gen',
  output: [
    '_extmodule.c',
    '_ext-f2pywrappers2.f90',
  ],
  input: ['wrapper.f90', 'isorropiaII_main_mod.F'],
  command: [
    py,
    '-m', 'numpy.f2py',
    '@INPUT@',
    'only:', 'solve', 'solve_batch', ':',
    '-m', '_ext',
    '--lower',
    '--build-dir', '@OUTDIR@',
  ],
)

py.extension_module(
  '_ext',
  [
    f2py_output,
    fortranobject_c,
    'wrapper.f90',
    'isorropiaII_main_mod.F',
  ],
  c_args: ['-DNPY_NO_DEPRECATED_API=NPY_1_7_API_VERSION'],
  fortran_args: fortran_args,
  dependencies: [py_dep, np_dep],
  install: true,
  subdir: 'AeroViz/dataProcess/Chemistry/_isorropia',
)
