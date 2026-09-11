# Supported Instruments

AeroViz provides comprehensive support for reading and processing data from a wide range of aerosol measurement
instruments. Each instrument has a dedicated reader that handles its specific data format, file structure, and
measurement characteristics.

!!! info "Instrument Support"

    You name the instrument; AeroViz does **not** guess it. `instrument=` is
    required and is validated against the supported list — a wrong or unknown name
    raises `KeyError` listing what is valid. The reader then handles that
    instrument's file format, header layout and status codes for you, including
    the dialect differences between host-software versions.

## Instrument Categories

### Aethalometers (Black Carbon Measurement)

Instruments for measuring black carbon and light absorption:

- **[AE33](aethalometers/AE33.md)** - Magee Scientific AE33 (7-wavelength aethalometer)
- **[AE43](aethalometers/AE43.md)** - Magee Scientific AE43 (real-time BC measurements)
- **[BC1054](aethalometers/BC1054.md)** - MetOne BC1054 (high-resolution absorption)
- **[MA350](aethalometers/MA350.md)** - AethLabs MA350 (multi-angle absorption photometer)

### Nephelometers (Light Scattering)

Instruments for measuring aerosol light scattering:

- **[Aurora](nephelometers/Aurora.md)** - Ecotech Aurora (3-wavelength nephelometer)
- **[NEPH](nephelometers/NEPH.md)** - TSI Nephelometer (standard scattering measurements)

### Particle Sizers

Instruments for measuring particle size distributions:

- **[SMPS](particle-sizers/SMPS.md)** - Scanning Mobility Particle Sizer (10-600 nm)
- **[APS](particle-sizers/APS.md)** - Aerodynamic Particle Sizer (0.5-20 μm)
- **[GRIMM](particle-sizers/GRIMM.md)** - GRIMM Aerosol Spectrometer (optical sizing)

### Chemical Analysis

Instruments for chemical composition analysis:

- **[IGAC](chemical/IGAC.md)** - Ion chromatography (water-soluble ions)
- **[OCEC](chemical/OCEC.md)** - Organic/Elemental Carbon Analyzer
- **[Xact](chemical/Xact.md)** - Xact 625i XRF Analyzer (elemental analysis)

### Mass Concentration

Instruments for PM mass concentration measurement:

- **[TEOM](mass/TEOM.md)** - Tapered Element Oscillating Microbalance
- **[BAM1020](mass/BAM1020.md)** - Beta Attenuation Monitor (PM2.5)

### External / pre-aggregated sources

Not instruments, but read through the same factory:

- **[EPA](other/EPA.md)** - Taiwan EPA hourly air-quality export (`big5`-encoded 測項 / 直式 CSV)

### Not readable

- **Q-ACSM** - a real instrument (30-min native resolution), but its reader is
  not written yet: calling it raises `NotImplementedError` explaining what to
  contribute — see [Contributing a Reader](../../guide/contributing-reader.md).
- **VOC**, **Minion** - pre-aggregated, second-hand data with no raw log to
  parse. The readers were removed; calling them raises `KeyError` carrying the
  migration advice. See [VOC Data](chemical/VOC.md).

!!! tip "Usage Example"

    ```python
    from AeroViz import RawDataReader

    # Name the instrument and the folder holding its raw files.
    df = RawDataReader('AE33', '/data/NZ_AE33', start='2024-01-01', end='2024-06-30')

    # What was actually read is reported in df.attrs
    print(df.attrs['raw_freq'])         # native resolution detected from the files
    print(df.attrs['coverage_start'])   # first timestamp carrying real data
    print(df.attrs['total_rate'])       # % of expected periods that passed QC
    ```

## Technical Specifications

| Instrument | Time Resolution | File Type | QC Rules |
|:-----------|:---------------:|:----------|:---------|
| **AE33** | 1 min | .dat | Status Error, Invalid BC, Invalid AAE, Insufficient |
| **AE43** | 1 min | .dat | Status Error, Invalid BC, Invalid AAE, Insufficient |
| **BC1054** | 1 min | .csv | Status Error, Invalid BC, Invalid AAE, Insufficient |
| **MA350** | 1 min | .csv | Status Error, Invalid BC, Invalid AAE, Insufficient |
| **NEPH** | 5 min | .dat | Status Error, No Data, Invalid Scat Value, Invalid Scat Rel, Insufficient |
| **Aurora** | 1 min | .csv | Status Error, No Data, Invalid Scat Value, Invalid Scat Rel, Insufficient |
| **SMPS** | 6 min | .txt, .csv | Status Error, Invalid Number Conc, CPC Over-range, DMA Water Ingress, Insufficient |
| **APS** | 6 min | .txt | Status Error, Invalid Number Conc, Insufficient |
| **GRIMM** | 6 min | .dat | No Data, Negative Conc, Insufficient |
| **TEOM** | 6 min | .csv | Status Error, High Noise, Non-positive, NV > Total, Spike, Insufficient |
| **BAM1020** | 1 h | .csv | Invalid Conc, Spike |
| **OCEC** | 1 h | *LCRes.csv | Invalid Carbon, Below MDL, Spike, Missing OC |
| **IGAC** | 1 h | .csv | Mass Closure, Missing Main, Above MR, Ion Balance |
| **Xact** | 1 h | .csv | Calibration Mode, Instrument Error, Upscale Warning, Invalid Value, High Uncertainty, Internal Std Drift |
| **EPA** | 1 h | .csv | Negative |

Every reader declares its rules as `QCRule`s; what a flag means, which are
advisory and where the verdict is recorded is explained once in
[RawDataReader Reference §2](../../guide/reader-reference.md#2-qc-machinery),
and the files each read writes in
[Reference §1](../../guide/reader-reference.md#files-written).

## Adding an instrument

See [Contributing a Reader](../../guide/contributing-reader.md): the `meta`
entry, the `Reader` class with its `_raw_reader` / `_QC` / `_process` hooks,
the tests and the docs page.

## Related

- [AbstractReader](../AbstractReader.md) — base class for all readers
- [Quality Control](../QualityControl.md) — the filters the rules are built from
- [RawDataReader](../RawDataReader/index.md) — the factory
