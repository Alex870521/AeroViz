# ICRP 66 Lung Deposition Model

ICRP (International Commission on Radiological Protection) Publication 66 provides a human respiratory tract aerosol deposition model for evaluating health effects of inhaled particles.

## Respiratory Tract Regions

### Head Airways (HA)

- Nasal cavity, pharynx, larynx
- Primary mechanisms: Inertial impaction, gravitational settling
- Main deposition region for large particles (>10 um)

### Tracheobronchial (TB)

- Trachea to terminal bronchioles
- Mucociliary clearance mechanism
- Deposition region for medium-sized particles

### Alveolar (AL)

- Respiratory bronchioles, alveolar ducts, alveoli
- Gas exchange region
- Main deposition region for fine particles (<1 um)

## Deposition Mechanisms

### Impaction

Large particles cannot follow airflow turns due to inertia and impact airway walls.

$$Stk = \frac{\rho_p D_p^2 U C_c}{18 \mu d}$$

### Sedimentation

Particles settle on airway walls due to gravity, primarily in small airways and alveoli.

$$v_s = \frac{\rho_p D_p^2 g C_c}{18 \mu}$$

### Diffusion

Ultrafine particles reach airway walls through Brownian motion.

$$D = \frac{k_B T C_c}{3 \pi \mu D_p}$$

## Activity Level Parameters

| Activity | Breathing Rate (min-1) | Tidal Volume (L) | Ventilation (L/min) | Breathing Mode |
|----------|------------------------|------------------|---------------------|----------------|
| Sleep | 12 | 0.625 | 7.5 | Nasal |
| Sitting | 12 | 0.75 | 9 | Nasal |
| Light Activity | 20 | 1.25 | 25 | Mixed |
| Heavy Activity | 26 | 1.92 | 50 | Oral |

## Deposition Fraction Curve

The relationship between particle size and total deposition efficiency shows a U-shape:

- **Ultrafine particles (<0.1 um)**: Diffusion dominated, high deposition efficiency
- **Accumulation mode (0.1-1 um)**: Lowest deposition efficiency ("penetration window")
- **Coarse particles (>1 um)**: Impaction and sedimentation dominated, high deposition efficiency

## AeroViz Implementation

```python
from AeroViz.dataProcess.SizeDistr import SizeDist

# Create PSD object
psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')

# Calculate lung deposition
result = psd.lung_deposition(activity='light')

# Output
result['DF']         # Deposition fraction DataFrame (HA, TB, AL, Total)
result['deposited']  # Deposited distribution (dN/dlogDp x DF)
result['dose']       # Regional dose
result['total_dose'] # Total deposited dose
```

### Output Example

```python
# Deposition fractions (by particle size)
result['DF']
#           HA       TB       AL    Total
# 11.8   0.012    0.045    0.285    0.342
# 20.5   0.008    0.032    0.198    0.238
# 50.0   0.005    0.018    0.112    0.135
# 100    0.004    0.012    0.085    0.101
# 200    0.006    0.015    0.095    0.116
# 500    0.025    0.035    0.125    0.185
```

## Health Significance

- **HA deposition**: Primarily cleared by mucociliary system
- **TB deposition**: May cause bronchitis, asthma
- **AL deposition**: Particles may enter bloodstream, affecting cardiovascular system

## References

1. ICRP (1994). Human Respiratory Tract Model for Radiological Protection. *ICRP Publication 66*, Ann. ICRP 24(1-3).
2. Hinds, W. C. (1999). *Aerosol Technology: Properties, Behavior, and Measurement of Airborne Particles*. Wiley.
