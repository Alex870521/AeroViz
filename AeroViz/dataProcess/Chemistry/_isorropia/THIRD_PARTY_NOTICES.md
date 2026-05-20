# Third-party notices: ISORROPIA II

AeroViz includes a copy of the ISORROPIA II Fortran source code to
provide cross-platform aerosol thermodynamic equilibrium calculations
(aerosol pH, ALWC, gas-particle partitioning of NH3/NH4+, HNO3/NO3-,
HCl/Cl-).

## Source

The file `isorropiaII_main_mod.F` was extracted from the GEOS-Chem
14.3.1 release:

  https://github.com/geoschem/geos-chem/tree/14.3.1/ISORROPIA

GEOS-Chem is distributed under the MIT License. The ISORROPIA II
algorithm and original copyright are preserved in the source file
header.

## Copyright

```
Copyright 1996-2006, University of Miami, Carnegie Mellon University,
Georgia Institute of Technology
Written by Athanasios Nenes
Updated by Christos Fountoukis
Update | Adjoint by Shannon Capps
```

## Required citations

If you use AeroViz's `isoropia()` function in published research,
please cite both of the ISORROPIA II references:

  Nenes, A., Pandis, S. N., and Pilinis, C. (1998).
  ISORROPIA: A new thermodynamic equilibrium model for multiphase
  multicomponent inorganic aerosols.
  Aquatic Geochemistry, 4, 123–152.
  https://doi.org/10.1023/A:1009604003981

  Fountoukis, C. and Nenes, A. (2007).
  ISORROPIA II: a computationally efficient thermodynamic equilibrium
  model for K+–Ca2+–Mg2+–NH4+–Na+–SO42-–NO3-–Cl-–H2O aerosols.
  Atmospheric Chemistry and Physics, 7, 4639–4659.
  https://doi.org/10.5194/acp-7-4639-2007

## Contact

For licensing questions about ISORROPIA II itself, contact the original
author: Prof. Athanasios Nenes
(athanasios.nenes@gatech.edu / athanasios.nenes@epfl.ch).

For AeroViz-specific usage questions, see https://github.com/Alex870521/AeroViz.
