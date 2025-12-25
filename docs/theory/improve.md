# IMPROVE Extinction Equation

The IMPROVE (Interagency Monitoring of Protected Visual Environments) equation estimates atmospheric extinction coefficients from chemical composition, widely used in visibility research.

## Revised IMPROVE (2007)

### Complete Equation

$$b_{ext} = b_{sp} + b_{ap} + b_{sg} + b_{ag}$$

### Particle Scattering ($b_{sp}$)

$$b_{sp} = 2.2 \times f_S(RH) \times [Small\ (NH_4)_2SO_4] + 4.8 \times f_L(RH) \times [Large\ (NH_4)_2SO_4]$$
$$+ 2.4 \times f_S(RH) \times [Small\ NH_4NO_3] + 5.1 \times f_L(RH) \times [Large\ NH_4NO_3]$$
$$+ 2.8 \times [Small\ OM] + 6.1 \times [Large\ OM]$$
$$+ 1 \times [Soil] + 1.7 \times f_{SS}(RH) \times [SS]$$

### Particle Absorption ($b_{ap}$)

$$b_{ap} = 10 \times [EC]$$

### Size Classification

- **Small** (fine mode): When $[X] < 20\ \mu g/m^3$, $[Small] = [X]$
- **Large** (coarse mode): $[Large] = [X] - [Small]$

### Hygroscopic Growth Factor f(RH)

| RH (%) | $f_S(RH)$ | $f_L(RH)$ | $f_{SS}(RH)$ |
|--------|-----------|-----------|--------------|
| 30 | 1.0 | 1.0 | 1.0 |
| 50 | 1.3 | 1.4 | 1.5 |
| 70 | 2.0 | 2.4 | 2.8 |
| 80 | 3.0 | 3.8 | 4.5 |
| 90 | 5.5 | 7.5 | 9.0 |

## Modified IMPROVE

Simplified version using a single f(RH):

$$b_{ext} = 3 \times f(RH) \times [(NH_4)_2SO_4 + NH_4NO_3]$$
$$+ 4 \times [OM] + 10 \times [EC] + 1 \times [Soil] + 1.7 \times f(RH) \times [SS]$$

## Mass Extinction Efficiency (MEE)

| Component | Dry MEE (m2/g) | Description |
|-----------|----------------|-------------|
| (NH4)2SO4 | 2.2-4.8 | Highly hygroscopic |
| NH4NO3 | 2.4-5.1 | Highly hygroscopic |
| OM | 2.8-6.1 | Depends on organic type |
| EC | 10 | Strong absorption |
| Soil | 1 | Low efficiency |
| SS | 1.7 | Highly hygroscopic |

## Gas Extinction

### Rayleigh Scattering

$$b_{sg} = 11.4\ Mm^{-1}$$ (at sea level standard conditions)

### NO2 Absorption

$$b_{ag} = 0.33 \times [NO_2]\ (ppb)$$

## AeroViz Implementation

```python
from AeroViz.dataProcess import DataProcess
from pathlib import Path

dp = DataProcess('Optical', Path('./output'))

# IMPROVE calculation
result = dp.IMPROVE(
    df_mass,            # Mass concentration (AS, AN, OM, Soil, SS, EC)
    df_RH,              # Relative humidity
    method='revised'    # 'revised' or 'modified'
)

# Output
result['dry']    # Dry extinction by component
result['wet']    # Wet extinction by component
result['ALWC']   # Aerosol liquid water contribution
result['fRH']    # Hygroscopic growth factor
```

## References

1. Pitchford, M., et al. (2007). Revised Algorithm for Estimating Light Extinction from IMPROVE Particle Speciation Data. *JAPCA*, 57(11), 1326-1336.
2. Malm, W. C., & Hand, J. L. (2007). An examination of the physical and optical properties of aerosols collected in the IMPROVE program. *Atmos. Environ.*, 41(16), 3407-3427.
