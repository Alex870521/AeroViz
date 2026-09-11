# `AeroViz.voc`

Ozone formation potential (OFP), secondary organic aerosol potential (SOAP)
and OH reactivity (LOH) from VOC concentrations. Worked example:
[VOC Analysis](../../guide/voc_analysis.md). Theory: [OFP / SOAP](../../theory/ofp.md).
Species table with MIR / SOAP factors: [VOC data](../instruments/chemical/VOC.md).

## Input

```python
# columns are species names, validated against support_voc.json (unknown names raise)
df_voc.columns = ['Benzene', 'Toluene', 'Ethylbenzene', 'm,p-Xylene', ...]
df_voc.index   = DatetimeIndex
# units: ppb or µg/m³
```

There is no VOC reader — read the export with pandas (see the guide) and call
`voc_potentials` directly.

## Output

`voc_potentials` returns a dict of four time-indexed DataFrames. Each carries
one column per species, per-class subtotals (`alkane_total`, `aromatic_total`,
…) and a grand `Total`:

| Key | Content |
|---|---|
| `Conc` | mass concentration (µg/m³) |
| `OFP` | ozone formation potential (µg O₃/m³), from MIR |
| `SOAP` | secondary organic aerosol potential |
| `LOH` | OH reactivity (loss rate) |

## Functions

::: AeroViz.voc
