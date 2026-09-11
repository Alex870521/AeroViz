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

## In AeroViz

Usage lives in the guide: [Lung Deposition Calculation](../guide/size_distribution.md#lung-deposition-calculation) shows `SizeDist.lung_deposition()`, its return keys and a per-diameter example.

## Health Significance

- **HA deposition**: Primarily cleared by mucociliary system
- **TB deposition**: May cause bronchitis, asthma
- **AL deposition**: Particles may enter bloodstream, affecting cardiovascular system

## References

1. ICRP (1994). Human Respiratory Tract Model for Radiological Protection. *ICRP Publication 66*, Ann. ICRP 24(1-3).
2. Hinds, W. C. (1999). *Aerosol Technology: Properties, Behavior, and Measurement of Airborne Particles*. Wiley.
