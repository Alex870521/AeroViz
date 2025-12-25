# kappa-Kohler Hygroscopicity Theory

kappa-Kohler theory uses a single parameter kappa to describe the hygroscopicity of aerosol particles, simplifying the complexity of traditional Kohler theory.

## Basic Principles

### Traditional Kohler Equation

$$\ln\left(\frac{RH}{100}\right) = \frac{4 M_w \sigma}{RT \rho_w D_{wet}} - \frac{6 n_s M_w}{\pi \rho_w D_{wet}^3}$$

The competition between the Kelvin effect term and Raoult effect term determines the equilibrium diameter of the particle.

### kappa Parameterization

Simplified form proposed by Petters and Kreidenweis (2007):

$$\frac{1}{a_w} = 1 + \kappa \frac{V_s}{V_w}$$

Where:
- $a_w$ = Water activity
- $\kappa$ = Hygroscopicity parameter
- $V_s$ = Dry particle volume
- $V_w$ = Water volume

## Physical Meaning of kappa Values

| kappa Range | Hygroscopicity | Typical Components |
|-------------|----------------|-------------------|
| 0 | Non-hygroscopic | Mineral dust, EC |
| 0.01-0.1 | Weakly hygroscopic | Organic matter |
| 0.1-0.3 | Moderately hygroscopic | Mixed aerosol |
| 0.3-0.7 | Highly hygroscopic | Ammonium sulfate, ammonium nitrate |
| >0.7 | Extremely hygroscopic | Sea salt |

## Component kappa Values

| Component | kappa Value | Source |
|-----------|-------------|--------|
| (NH4)2SO4 | 0.53 | Petters & Kreidenweis (2007) |
| NH4NO3 | 0.67 | Petters & Kreidenweis (2007) |
| NaCl | 1.28 | Petters & Kreidenweis (2007) |
| H2SO4 | 0.90 | Petters & Kreidenweis (2007) |
| SOA | 0.1 +/- 0.05 | Experimental range |
| POA | 0.01 | Estimated value |
| BC | 0 | Non-hygroscopic |

## Mixed Aerosol kappa Calculation

For internally mixed particles, use volume weighting:

$$\kappa = \sum_i \epsilon_i \kappa_i$$

Where $\epsilon_i$ is the volume fraction of component $i$.

## Hygroscopic Growth Factor

Calculate growth factor GF from kappa:

$$GF = \left(\frac{D_{wet}}{D_{dry}}\right) = \left(1 + \kappa \frac{RH/100}{1 - RH/100}\right)^{1/3}$$

## AeroViz Implementation

```python
from AeroViz.dataProcess import DataProcess
from pathlib import Path

dp = DataProcess('Chemistry', Path('./output'))

# Calculate kappa and growth factor
result = dp.kappa(df_chem, df_RH)

# Output
result['kappa']  # kappa value time series
result['gRH']    # Growth factor

# Example output
#                     kappa    gRH
# 2024-01-01 00:00    0.35    1.42
# 2024-01-01 01:00    0.38    1.45
```

## Applications

### 1. Dry PSD Calculation

Convert ambient PSD to dry PSD:

$$D_{dry} = D_{wet} / GF$$

### 2. Optical Hygroscopic Growth

Estimate f(RH) for IMPROVE equation.

### 3. CCN Activation

Predict the ability of aerosols to act as cloud condensation nuclei.

## References

1. Petters, M. D., & Kreidenweis, S. M. (2007). A single parameter representation of hygroscopic growth and cloud condensation nucleus activity. *Atmos. Chem. Phys.*, 7(8), 1961-1971.
2. Kohler, H. (1936). The nucleus in and the growth of hygroscopic droplets. *Trans. Faraday Soc.*, 32, 1152-1161.
