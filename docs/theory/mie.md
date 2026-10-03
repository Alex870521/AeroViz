# Mie Scattering Theory

Mie theory provides the exact solution for the interaction of electromagnetic waves with homogeneous spherical particles, proposed by Gustav Mie in 1908.

## Basic Principles

When electromagnetic waves encounter particles, scattering and absorption occur. Mie theory provides the mathematical framework for calculating these processes.

### Efficiency Factors

For a particle with diameter $D_p$, the efficiency factors are defined as:

$$Q_{ext} = Q_{sca} + Q_{abs}$$

Where:
- $Q_{ext}$ = Extinction efficiency factor
- $Q_{sca}$ = Scattering efficiency factor
- $Q_{abs}$ = Absorption efficiency factor

### Size Parameter

$$x = \frac{\pi D_p}{\lambda}$$

Where $\lambda$ is the wavelength of incident light.

### Complex Refractive Index

$$m = n + ik$$

- $n$ = Real part (refraction)
- $k$ = Imaginary part (absorption)

## Extinction Coefficient Calculation

Calculate total extinction coefficient from size distribution:

$$b_{ext} = \int_0^\infty Q_{ext}(D_p, m, \lambda) \cdot \frac{\pi D_p^2}{4} \cdot n(D_p) \, dD_p$$

Where $n(D_p)$ is the particle number size distribution.

## Mixing Modes

### Internal Mixing

All components are uniformly mixed within a single particle, using volume-weighted average refractive index:

$$m_{mix} = \sum_i f_i \cdot m_i$$

Where $f_i$ is the volume fraction of component $i$.

### External Mixing

Each component forms independent particles, calculated separately and summed:

$$b_{ext} = \sum_i b_{ext,i}$$

### Core-Shell Structure

EC as the core with other components as the shell. Suitable for aged aerosols.

## Lognormal Modes by Mass

A synthetic mode is usually known by its mass loading, not its number
concentration. For a lognormal number mode with count median diameter $CMD$
and geometric standard deviation $\sigma_g$, the Hatch–Choate relations give
the volume-mode median and the total volume:

$$VMD = CMD \cdot e^{3\ln^2\sigma_g}, \qquad
V = N \cdot \frac{\pi}{6}\,CMD^3\, e^{4.5\ln^2\sigma_g}$$

so a mass concentration $M$ with density $\rho$ fixes $N = M/(\rho V_1)$, where
$V_1$ is the volume of a unit-number mode. `mie_lognormal(..., total_mass=,
density=)` and `mie_multimodal(..., amount='mass', density=)` do this
conversion; `hatch_choate()` converts medians between weightings. The grid is
built as $dN/d\log_{10}D_p$, which is what the integration assumes.

## In AeroViz

Usage lives in the guide: [`mie`](../guide/dataprocess.md#mie-calculation) for the call and its `mixing` / `distribution` options, and [Optical Closure](../guide/optical_closure.md#mie-closure) for a worked comparison against measured extinction.

## References

1. Mie, G. (1908). Beitrage zur Optik truber Medien. *Annalen der Physik*, 330(3), 377-445.
2. Bohren, C. F., & Huffman, D. R. (1983). *Absorption and Scattering of Light by Small Particles*. Wiley.
