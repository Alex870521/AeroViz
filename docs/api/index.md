# API Reference

Technical reference for AeroViz. The [Guide](../guide/index.md) is the place
to learn the workflow; these pages document signatures, inputs and outputs.

## Reading data

- [RawDataReader](RawDataReader/index.md) — the factory: one instrument name,
  one folder, a QC'd DataFrame back.
- [AbstractReader](AbstractReader.md) — the base class every reader extends.
- [Quality Control](QualityControl.md) — the statistical filters and the
  `QCRule` / `QCFlagBuilder` machinery.
- [Supported Instruments](instruments/index.md) — the catalogue, and one page
  per instrument with its raw format, status codes, QC rules and outputs.

| Family | Instruments |
|---|---|
| Aethalometers / BC | [AE33](instruments/aethalometers/AE33.md), [AE43](instruments/aethalometers/AE43.md), [BC1054](instruments/aethalometers/BC1054.md), [MA350](instruments/aethalometers/MA350.md) |
| Nephelometers | [Aurora](instruments/nephelometers/Aurora.md), [NEPH](instruments/nephelometers/NEPH.md) |
| Particle sizers | [SMPS](instruments/particle-sizers/SMPS.md), [APS](instruments/particle-sizers/APS.md), [GRIMM](instruments/particle-sizers/GRIMM.md) |
| Mass | [TEOM](instruments/mass/TEOM.md), [BAM1020](instruments/mass/BAM1020.md) |
| Chemistry | [IGAC](instruments/chemical/IGAC.md), [OCEC](instruments/chemical/OCEC.md), [Xact](instruments/chemical/Xact.md) |
| External | [EPA](instruments/other/EPA.md) |
| Not readable | [VOC](instruments/chemical/VOC.md) (pre-aggregated; read with pandas, then `voc_potentials`), Minion (removed), Q-ACSM (reader pending) |

## Post-processing

- [Overview and migration from `DataProcess`](DataProcess/index.md)
- [`AeroViz.size`](DataProcess/SizeDistr.md) — size-distribution statistics, SMPS–APS merge, `SizeDist`
- [`AeroViz.chemistry`](DataProcess/Chemistry.md) — mass reconstruction, refractive index, kappa, partitioning, OC/EC, ISORROPIA
- [`AeroViz.optical`](DataProcess/Optical.md) — IMPROVE, Mie, gas extinction, RI retrieval, brown carbon
- [`AeroViz.voc`](DataProcess/VOC.md) — OFP / SOAP / LOH
- [Utilities](utilities.md) — `DataBase`, `DataClassifier`

## Plotting

[Plot](plot/index.md) — [basic charts](plot/basic.md), [time series](plot/timeseries.md),
[size distribution](plot/distribution.md), [meteorology](plot/meteorology.md),
[optical](plot/optical.md), [templates](plot/templates.md). Needs the `plot` extra.

## Conventions

Docstrings follow the NumPy style and are rendered by mkdocstrings: parameters
with types, return values, and examples where a call is not obvious. Where a
page states a threshold, a status code or a rule list, it is checked against
the reader source — several tables are parsed back out by the test suite.
