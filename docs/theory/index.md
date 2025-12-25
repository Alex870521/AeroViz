# Theoretical Background

This section introduces the aerosol science theories and calculation methods used in AeroViz.

## Optical Properties

### [Mie Scattering Theory](mie.md)

Mie theory describes the scattering and absorption of electromagnetic waves by spherical particles and is the foundation for calculating aerosol optical properties.

- Extinction, scattering, and absorption efficiency factors
- Internal mixing vs external mixing vs core-shell structure
- Effects of refractive index and particle size

### [IMPROVE Extinction Equation](improve.md)

The IMPROVE (Interagency Monitoring of Protected Visual Environments) equation is used to estimate extinction coefficients from chemical composition.

- Original version vs revised version
- Hygroscopic growth factor f(RH)
- Mass extinction efficiency of each component

## Size Distribution

### [Log-normal Distribution](lognormal.md)

Aerosol size distributions typically follow log-normal distributions and can be characterized by geometric mean diameter (GMD) and geometric standard deviation (GSD).

- Number/surface area/volume distribution conversion
- Modal analysis (Nucleation, Aitken, Accumulation, Coarse)
- Size distribution statistics

### [ICRP 66 Lung Deposition Model](icrp.md)

The International Commission on Radiological Protection (ICRP) human respiratory tract model is used to calculate regional deposition of inhaled aerosols.

- Head airways (HA), tracheobronchial (TB), and alveolar (AL) regions
- Activity intensity and breathing patterns
- Deposition fraction calculation

## Chemical Properties

### [kappa-Kohler Theory](kappa.md)

kappa-Kohler theory describes the hygroscopicity of aerosol particles, where the kappa value reflects the particle's ability to act as cloud condensation nuclei.

- Single-parameter kappa definition
- Relationship between chemical composition and kappa
- Hygroscopic growth factor calculation

### [Mass Reconstruction](mass_reconstruction.md)

Reconstructing PM2.5 mass from chemical composition to verify analytical completeness.

- Major components: SIA, OM, EC, Soil, SS
- Ammonium status determination
- OM/OC ratio selection

## VOC Analysis

### [Ozone Formation Potential (OFP)](ofp.md)

Assessment of volatile organic compounds (VOC) contribution to ozone formation.

- Maximum Incremental Reactivity (MIR)
- Species-specific OFP calculation
- Secondary Organic Aerosol Potential (SOAP)
