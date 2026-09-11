# Post-processing API

Post-processing is a flat set of top-level functions grouped into four
namespaces. Each call takes a DataFrame (or a few), runs one calculation and
returns a DataFrame or a dict — nothing is written to disk.

| Namespace | Page | Covers |
|---|---|---|
| `AeroViz.size` | [size](SizeDistr.md) | `psd_stats`, `psd_distributions`, `merge_psd`, and the `SizeDist` class |
| `AeroViz.chemistry` | [chemistry](Chemistry.md) | mass reconstruction, volumes and refractive index, kappa, partitioning, OC/EC, ISORROPIA |
| `AeroViz.optical` | [optical](Optical.md) | IMPROVE, Mie (bulk, lognormal, core-shell, angular), gas extinction, RI retrieval, brown carbon |
| `AeroViz.voc` | [voc](VOC.md) | `voc_potentials` (OFP / SOAP / LOH) |

Every function is also importable from the top level (`from AeroViz import
reconstruct_mass`). Worked usage lives in the guide:
[Post-Processing Functions](../../guide/dataprocess.md) and the four Examples
pages.

!!! warning "`DataProcess(...)` is deprecated"
    The `DataProcess(method=..., path_out=...)` factory and its method
    classes (`Chemistry`, `Optical`, `SizeDistr`, `VOC`) still exist but emit a
    `DeprecationWarning` and will be removed. The migration table below maps
    every legacy method to its replacement.

## Migrating from `DataProcess`

| Legacy call | Replacement |
|---|---|
| `DataProcess('SizeDistr').basic(df)` | `psd_stats(df)` — statistics under `['other']` |
| `DataProcess('SizeDistr').distributions(df)` | `psd_distributions(df)` |
| `DataProcess('SizeDistr').merge_SMPS_APS(smps, aps)` | `merge_psd(smps, aps, version=1)` |
| `DataProcess('SizeDistr').merge_SMPS_APS_v2(smps, aps)` | `merge_psd(smps, aps, version=2)` |
| `DataProcess('SizeDistr').merge_SMPS_APS_v3(smps, aps)` | `merge_psd(smps, aps, version=3)` |
| `DataProcess('SizeDistr').merge_SMPS_APS_v4(smps, aps, pm25)` | `merge_psd(smps, aps, df_pm25=pm25, version=4)` |
| `DataProcess('SizeDistr').dry_psd(df, df_gRH)` | `SizeDist(df).to_dry(df_gRH)` |
| `DataProcess('SizeDistr').extinction_distribution(df, df_RI)` | `SizeDist(df).to_extinction(df_RI, method='internal')` or `mie(df, ri, distribution=True)` |
| `DataProcess('SizeDistr').extinction_full(df, df_RI)` | `mie(df, ri)` |
| `DataProcess('Chemistry').ReConstrc_basic(df)` | `reconstruct_mass(df)` |
| `DataProcess('Chemistry').volume_average_mixing(df_volume, df_alwc)` | `volume_ri(df_volume, df_alwc=df_alwc)` |
| `DataProcess('Chemistry').gRH(df_volume, df_alwc)` | `growth_factor(df_volume, df_alwc)` |
| `DataProcess('Chemistry').kappa(df, diameter)` | `kappa(df, diameter=...)` |
| `DataProcess('Chemistry').Partition(df)` | `partition_ratios(df)` |
| `DataProcess('Chemistry').OCEC_basic(df_lcres, df_mass)` | `split_oc_ec(df_lcres, df_mass=...)` |
| `DataProcess('Chemistry').ISOROPIA(df)` | `isoropia(df_ions, df_met)` |
| `DataProcess('Optical').basic(df_sca, df_abs, ...)` | `optical_basic(df_sca, df_abs, ...)` |
| `DataProcess('Optical').IMPROVE(df_mass, df_RH, method)` | `improve(df_mass, df_RH, method=...)` |
| `DataProcess('Optical').Mie(df_psd, df_m)` | `mie(df_psd, df_m)` |
| `DataProcess('Optical').gas_extinction(df_no2, df_temp)` | `gas_extinction(df_no2, df_temp)` |
| `DataProcess('Optical').retrieve_RI(df_optical, df_pnsd)` | `retrieve_ri(df_optical, df_pnsd)` |
| `DataProcess('Optical').BrC(df_abs, ...)` | `brown_carbon(df_abs, ...)` |
| `DataProcess('Optical').scaCoe` / `.absCoe` | done inside the readers (`sca_550`, `SAE`, `abs_*`, `AAE`, `eBC` are reader outputs) |
| `DataProcess('Optical').derived(...)` | no single replacement — its columns were `PG` (sca + abs + gas), `MAC`, `Ox` (NO₂ + O₃), `Vis_cal` (Koschmieder visibility), `fRH_IMPR`, `OCEC_ratio`, `PM1_PM25`; compose them from `optical_basic`, `gas_extinction`, `improve` and plain pandas |
| `DataProcess('VOC').VOC_basic(df)` | `voc_potentials(df)` |

The legacy factory, for reference only:

::: AeroViz.dataProcess.DataProcess
