# Instrument Documentation

This section provides detailed documentation for various aerosol measurement instruments supported by AeroViz.

## Supported Instruments

### Black Carbon Monitors

- [AE33 Aethalometer](AE33.md)
- [AE43 Aethalometer](AE43.md)
- [BC1054 Black Carbon Monitor](BC1054.md)
- [MA350 MicroAeth](MA350.md)

### Particle Sizers

- [SMPS Scanning Mobility Particle Sizer](SMPS.md)
- [APS Aerodynamic Particle Sizer](APS.md)
- [GRIMM Optical Particle Counter](GRIMM.md)

### Chemical Composition Analyzers

- [OCEC Organic Carbon/Elemental Carbon Analyzer](OCEC.md)
- [XRF X-ray Fluorescence Spectrometer](XRF.md)
- [VOC Volatile Organic Compounds Analyzer](VOC.md)

### Other Instruments

- [NEPH Nephelometer](NEPH.md)
- [Aurora Spectrometer](Aurora.md)
- [TEOM Tapered Element Oscillating Microbalance](TEOM.md)
- [IGAC Integrated Gas and Aerosol Collector](IGAC.md)

### Details of Supported Instruments

The AeroViz project currently supports data from the following instruments:

| Instrument                                             | Time Resolution | File Type   | Display Columns                                       | QAQC method |
|:-------------------------------------------------------|:---------------:|:------------|-------------------------------------------------------|:-----------:|
| NEPH (Nephelometer)                                    |      5min       | .dat        | G                                                     |   default   |
| Aurora (Nephelometer)                                  |      1min       | .csv        | G                                                     |   default   |
| SMPS (Scanning Mobility Particle Sizer)                |      6min       | .txt, .csv  | all                                                   |   default   |
| GRIMM (GRIMM Aerosol Technik)                          |      6min       | .dat        | all                                                   |   default   |
| APS_3321 (Aerodynamic Particle Sizer)                  |      6min       | .txt        | all                                                   |   default   |
| AE33 (Aethalometer Model 33)                           |      1min       | .dat        | BC6                                                   |   default   |
| AE43 (Aethalometer Model 43)                           |      1min       | .dat        | BC6                                                   |   default   |
| BC1054 (Black Carbon Monitor 1054)                     |      1min       | .csv        | BC9                                                   |   default   |
| MA350 (MicroAeth MA350)                                |      1min       | .csv        | BC5                                                   |   default   |
| BAM1020 (Beta Attenuation Mass Monitor)                |       1h        | .csv        | Conc                                                  |   default   |
| TEOM (Continuous Ambient Particulate Monitor)          |      6min       | .csv        | PM_Total, PM_NV                                       |   default   |
| OCEC (Sunset Organic Carbon Elemental Carbon Analyzer) |       1h        | *LCRes.csv  | Thermal_OC, Thermal_EC, Optical_OC, Optical_EC        |   default   |
| IGAC (In-situ Gas and Aerosol Compositions monitor)    |       1h        | .csv        | Na+, NH4+, K+, Mg2+, Ca2+, Cl-, NO2-, NO3-, SO42-     |   default   |
| XRF (X-ray Fluorescence Spectrometer)                  |       1h        | .csv        | Al, Si, P, S, Cl, K, Ca, Ti, V, Cr, Mn, Fe, Ni, Cu... |   default   |
| VOC (Volatile Organic Compounds Monitor)               |       1h        | .csv        | voc                                                   |   default   |
| EPA                                                    |       1h        | .csv        | all                                                   |   default   |
| Minion                                                 |       1h        | .csv, .xlsx | Na+, NH4+, Cl-, NO3-, SO42-, Al, Ti, V, Cr, Mn, Fe    |   default   |

```{note}
Notes:
1. For VOC, due to the numerous display columns, we've simply noted "voc" in the table. In reality, it includes many specific VOC compound names.
2. For instruments marked with "all", it means all available columns or intervals are displayed.
3. The display columns for XRF include a large number of element names, all of which are listed.
4. The file types for AE33 and AE43 actually have more specific patterns, but are simplified to ".dat" in this table.
```