# Log-normal Distribution

Aerosol size distributions typically follow log-normal distributions, which is determined by the physical mechanisms of particle formation and growth.

## Mathematical Definition

### Probability Density Function

$$\frac{dN}{d\ln D_p} = \frac{N_t}{\sqrt{2\pi}\ln\sigma_g} \exp\left[-\frac{(\ln D_p - \ln D_{pg})^2}{2\ln^2\sigma_g}\right]$$

Where:
- $N_t$ = Total number concentration
- $D_{pg}$ = Geometric mean diameter (GMD)
- $\sigma_g$ = Geometric standard deviation (GSD)

### Common Representations

| Representation | Symbol | Unit | Description |
|----------------|--------|------|-------------|
| dN | $dN$ | #/cm3 | Number concentration |
| dN/dDp | $dN/dD_p$ | #/cm3/nm | Number per diameter |
| dN/dlogDp | $dN/d\log D_p$ | #/cm3 | Number per log diameter |

## Distribution Conversion

### Number to Surface Area

$$\frac{dS}{d\log D_p} = \pi D_p^2 \cdot \frac{dN}{d\log D_p}$$

### Number to Volume

$$\frac{dV}{d\log D_p} = \frac{\pi}{6} D_p^3 \cdot \frac{dN}{d\log D_p}$$

### Hatch-Choate Conversion

Relationship between GMD of different weightings:

$$\ln D_{pg,S} = \ln D_{pg,N} + 2\ln^2\sigma_g$$
$$\ln D_{pg,V} = \ln D_{pg,N} + 3\ln^2\sigma_g$$

## Modal Classification

Atmospheric aerosols typically contain multiple modes:

| Mode | Size Range | Primary Sources |
|------|------------|-----------------|
| Nucleation | 1-25 nm | Gas-to-particle conversion, new particle formation |
| Aitken | 25-100 nm | Growth, combustion emissions |
| Accumulation | 100-1000 nm | Aging, cloud processing |
| Coarse | >1000 nm | Mechanical processes, sea salt, dust |

## Statistical Calculations

### Geometric Mean Diameter (GMD)

$$D_{pg} = \exp\left(\frac{\sum n_i \ln D_{p,i}}{\sum n_i}\right)$$

### Geometric Standard Deviation (GSD)

$$\ln\sigma_g = \sqrt{\frac{\sum n_i (\ln D_{p,i} - \ln D_{pg})^2}{\sum n_i}}$$

### Mode Diameter

The diameter corresponding to the distribution peak.

## AeroViz Implementation

```python
from AeroViz.dataProcess.SizeDistr import SizeDist

# Create PSD object
psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')

# Distribution conversion
surface = psd.to_surface()  # Surface area distribution
volume = psd.to_volume()    # Volume distribution

# Statistical properties
props = psd.properties()
# props['total_n']  # Total number concentration
# props['GMD_n']    # Geometric mean diameter
# props['GSD_n']    # Geometric standard deviation
# props['mode_n']   # Mode diameter

# Mode statistics
stats = psd.mode_statistics()
# stats['number']     # Number distribution by mode
# stats['surface']    # Surface area distribution by mode
# stats['volume']     # Volume distribution by mode
# stats['statistics'] # GMD, GSD, total for each mode
```

## Multi-modal Fitting

Log-normal mixture model:

$$\frac{dN}{d\log D_p} = \sum_{i=1}^{n} \frac{N_i}{\sqrt{2\pi}\log\sigma_{g,i}} \exp\left[-\frac{(\log D_p - \log D_{pg,i})^2}{2\log^2\sigma_{g,i}}\right]$$

## References

1. Seinfeld, J. H., & Pandis, S. N. (2016). *Atmospheric Chemistry and Physics: From Air Pollution to Climate Change*. Wiley.
2. Hinds, W. C. (1999). *Aerosol Technology: Properties, Behavior, and Measurement of Airborne Particles*. Wiley.
