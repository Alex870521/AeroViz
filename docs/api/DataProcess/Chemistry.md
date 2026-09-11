# `AeroViz.chemistry`

Mass reconstruction, component volumes and refractive index, hygroscopic
growth and kappa, gas–particle partitioning, OC/EC splitting and ISORROPIA II.
Worked examples: [Chemical Analysis](../../guide/chemical_analysis.md);
call-by-call summary: [Post-Processing Functions](../../guide/dataprocess.md#chemistry).
Theory: [Mass Reconstruction](../../theory/mass_reconstruction.md),
[κ-Köhler](../../theory/kappa.md).

## Input

```python
# reconstruct_mass — species columns in µg/m³; extra ions (K+, Mg2+, Ca2+)
# may be present and are carried through, but the reconstruction itself uses:
df_chem.columns ⊇ ['SO42-', 'NO3-', 'NH4+', 'OC', 'EC', 'Na+', 'Cl-', 'Al', 'Fe', 'Ti', 'PM25']

# partition_ratios — the chemistry frame plus gases and temperature:
gas_columns = ['SO2', 'NO2', 'HNO3', 'NH3']      # ppb or µg/m³
```

## Functions

::: AeroViz.chemistry
