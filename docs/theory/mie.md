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

## AeroViz Implementation

```python
from AeroViz import mie

# Single-material RI: pass a Series of complex numbers (n + ik per row)
result = mie(
    df_pnsd,           # Particle number size distribution
    df_RI_complex,     # Series of complex RI, one per row
    wavelength=550,    # Wavelength (nm)
)

# Output: DataFrame with extinction, scattering, absorption (Mm-1)

# Species mixing-table: DataFrame with '*_volume_ratio' columns
result_mix = mie(
    df_pnsd,
    df_mixing_table,           # AS_volume_ratio, AN_volume_ratio, ...
    wavelength=550,
    mixing='internal',         # 'internal' | 'external' | 'both'
)

# Per-bin distribution instead of totals
dext = mie(df_pnsd, df_RI_complex, wavelength=550, distribution=True)
```

`mie` replaces the legacy `Mie` / `extinction_distribution` / `extinction_full` triplet — behavior is selected by the shape of `ri` and the `mixing` / `distribution` keywords.

## References

1. Mie, G. (1908). Beitrage zur Optik truber Medien. *Annalen der Physik*, 330(3), 377-445.
2. Bohren, C. F., & Huffman, D. R. (1983). *Absorption and Scattering of Light by Small Particles*. Wiley.
