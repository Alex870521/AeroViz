# Mass Reconstruction

Mass reconstruction reconstructs PM2.5 mass from chemical composition to verify the completeness and closure of chemical analysis.

## Major Components

### Secondary Inorganic Aerosol (SIA)

#### Ammonium Sulfate (AS)

$$(NH_4)_2SO_4 = 1.375 \times SO_4^{2-}$$

#### Ammonium Nitrate (AN)

$$NH_4NO_3 = 1.29 \times NO_3^{-}$$

#### Ammonium Status Determination

Calculate ion balance:

$$R = \frac{[NH_4^+]}{[SO_4^{2-}]/48 \times 2 + [NO_3^-]/62}$$

| R Value | Status | Description |
|---------|--------|-------------|
| >1.1 | Excess | NH4+ excess, possibly NH4Cl present |
| 0.9-1.1 | Balance | Near neutral |
| <0.9 | Deficiency | NH4+ deficient, acidic aerosol |

### Organic Matter (OM)

$$OM = OC \times f_{OM/OC}$$

| Environment Type | $f_{OM/OC}$ | Description |
|------------------|-------------|-------------|
| Urban fresh | 1.4-1.6 | Primary organic matter dominated |
| Suburban aged | 1.6-1.8 | Mixed sources |
| Background | 1.8-2.2 | Secondary organic matter dominated |

### Elemental Carbon (EC)

Use measured value directly:

$$EC = EC_{measured}$$

### Soil Dust

Estimated from crustal elements:

$$Soil = 2.20 \times Al + 2.49 \times Si + 1.63 \times Ca + 2.42 \times Fe + 1.94 \times Ti$$

If Si data is unavailable:

$$Soil = 2.20 \times Al + 1.63 \times Ca + 2.42 \times Fe + 1.94 \times Ti$$

Multiply by correction factor (~1.89).

### Sea Salt (SS)

$$SS = 2.54 \times Na^+$$

Or considering chloride depletion:

$$SS = Na^+ + Cl^- + 0.038 \times Na^+$$

## Total Mass Reconstruction

$$PM_{2.5,reconstructed} = AS + AN + OM + EC + Soil + SS$$

## Closure Evaluation

$$Closure = \frac{PM_{2.5,reconstructed}}{PM_{2.5,measured}} \times 100\%$$

| Closure | Assessment |
|---------|------------|
| 80-120% | Good |
| 70-80% or 120-130% | Acceptable |
| <70% or >130% | Needs review |

## Unidentified Mass

$$Unidentified = PM_{2.5,measured} - PM_{2.5,reconstructed}$$

Possible sources:
- Bound water
- Metal oxides
- Analytical errors
- Unmeasured components

## In AeroViz

Usage lives in the guide: [Mass Reconstruction](../guide/chemical_analysis.md#mass-reconstruction) for `reconstruct_mass`, its return keys and `split_om`, and the required input columns in [Input Format Requirements](../guide/dataprocess.md#input-format-requirements).

## References

1. Malm, W. C., et al. (1994). Spatial and monthly trends in speciated fine particle concentration in the United States. *JGR*, 99(D1), 1347-1370.
2. Turpin, B. J., & Lim, H. J. (2001). Species contributions to PM2.5 mass concentrations: Revisiting common assumptions for estimating organic mass. *Aerosol Sci. Technol.*, 35(1), 602-610.
