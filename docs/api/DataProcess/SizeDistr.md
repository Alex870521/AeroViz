# `AeroViz.size`

Size-distribution processing: statistics, weighting conversions and the
SMPS–APS merge. Worked examples: [Size Distribution](../../guide/size_distribution.md);
call-by-call summary: [Post-Processing Functions](../../guide/dataprocess.md#size-distribution).
Theory: [Log-normal Distribution](../../theory/lognormal.md),
[ICRP 66](../../theory/icrp.md), [Mie](../../theory/mie.md).

## Input

```python
df_pnsd.columns = [11.8, 13.6, 15.7, ..., 523.3]   # diameters (nm) as numeric column labels
df_pnsd.index   = DatetimeIndex                     # one row per scan
df_gRH          = DataFrame({'gRH': [1.2, 1.3, ...]}, index=time_index)   # for to_dry
```

This is exactly what `RawDataReader('SMPS' | 'APS', ...)` returns.

## Functions

::: AeroViz.size

## The `SizeDist` class

The engine behind the functions, for per-row conversions (extinction, dry PSD,
lung deposition). Not deprecated.

| Attribute | Type | Meaning |
|---|---|---|
| `data` | DataFrame | the distribution as given |
| `dp` | ndarray | diameters (nm) |
| `dlogdp` | ndarray | log-spacing per bin |
| `index` | DatetimeIndex | time index |
| `state` | str | `'dN'`, `'ddp'` or `'dlogdp'` — how `data` is normalised |
| `weighting` | str | `'n'`, `'s'`, `'v'`, `'ext_in'`, `'ext_ex'` |

Modes used by `mode_statistics()`: Nucleation 10–25 nm, Aitken 25–100 nm,
Accumulation 100–1000 nm, Coarse 1000–2500 nm (absent when out of range).
`to_extinction(RI, method=...)` accepts `'internal'`, `'external'`,
`'core_shell'` (EC core, everything else as shell) and `'sensitivity'`.

::: AeroViz.dataProcess.SizeDistr.SizeDist
    options:
      show_root_heading: true
      members:
        - to_surface
        - to_volume
        - to_extinction
        - to_dry
        - properties
        - mode_statistics
        - lung_deposition
