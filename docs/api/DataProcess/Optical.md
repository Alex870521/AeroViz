# `AeroViz.optical`

Bulk optical properties, IMPROVE extinction, Mie theory (bulk, lognormal,
multimodal, core-shell, angular), gas extinction, brown-carbon separation and
refractive-index retrieval. Worked examples:
[Optical Closure](../../guide/optical_closure.md); call-by-call summary:
[Post-Processing Functions](../../guide/dataprocess.md#optical).
Theory: [IMPROVE](../../theory/improve.md), [Mie](../../theory/mie.md).

## Input

```python
df_sca.columns ⊇ ['sca_550', 'SAE']          # nephelometer reader output (lower-case)
df_abs.columns ⊇ ['abs_550', 'AAE', 'eBC']   # aethalometer reader output; abs_370 … abs_950 also available
df_mass.columns ⊇ ['AS', 'AN', 'OM', 'Soil', 'SS', 'EC']   # µg/m³, from reconstruct_mass(...)['mass']
```

!!! note "Reading `improve(...)` results"
    `df_RH` must be a **Series** (e.g. `met['RH']`), not a one-column
    DataFrame. Each returned frame (`dry`, `wet`) carries the per-species
    columns plus a lower-case `total`; use `dry['total']`, never
    `dry.sum(axis=1)`, which would count `total` twice.

Mixing modes for Mie: `internal` (volume-weighted mean refractive index),
`external` (each species computed separately, then summed), `core_shell`
(EC core with the remaining species as shell) and `sensitivity`. The first
two are selected with `mie(..., mixing=...)`; all four are available on
`SizeDist.to_extinction(method=...)`.

## Functions

::: AeroViz.optical
