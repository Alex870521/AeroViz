# Organic Carbon/Elemental Carbon Analyzer (OC/EC)

The OC/EC analyzer measures carbonaceous aerosol components using thermal and optical methods.

::: AeroViz.rawDataReader.script.OCEC.Reader

## Raw format

- File pattern: `*LCRes.csv`
- Native frequency: `1h`
- Encoding: read as UTF-8 with undecodable bytes ignored
- Header layout: 3 rows of metadata, then the column header
  (`read_csv(skiprows=3, on_bad_lines='skip')`)
- Data structure:
    - Time column: `Start Date/Time`
    - Carbon fraction measurements (thermal/optical OC, EC, TC; per-peak
      fractions on newer firmware)
    - Sample volume information

### Parse recipe

1. `Start Date/Time` is stripped and parsed with the first format that matches
   any row, tried in order: `%m/%d/%Y %I:%M:%S %p` (12-hour AM/PM, the
   RTCalc705 default) then `%m/%d/%Y %H:%M:%S` (24-hour). The format used is
   logged; if neither matches, a warning names the file and the sample value and
   the file yields an empty frame.
2. A results file with the header lines but **no sample rows** (RTCalc writes
   one for a run that produced nothing) is skipped with a debug line — it is
   not a read error.
3. Duplicate and NaT indices are removed, then the index is **rounded to `1h`**.
4. Three alias maps are applied unconditionally (only keys present in the file
   rename; the rest are inert):

    | Firmware | Raw column | Canonical |
    |---|---|---|
    | RTCalc705 | `Thermal/Optical OC (ugC/LCm^3)` | `Thermal_OC` |
    | RTCalc705 | `Thermal/Optical EC (ugC/LCm^3)` | `Thermal_EC` |
    | RTCalc705 | `OC=TC-BC (ugC/LCm^3)` | `Optical_OC` |
    | RTCalc705 | `BC (ugC/LCm^3)` | `Optical_EC` |
    | RTCalc705 | `TC (ugC/LCm^3)` | `TC` |
    | RTCalc802 | `OC ugC/m^3 (Thermal/Optical)` | `Thermal_OC` |
    | RTCalc802 | `EC ugC/m^3 (Thermal/Optical)` | `Thermal_EC` |
    | RTCalc802 | `OC by diff ugC (TC-OptEC)` | `Optical_OC` |
    | RTCalc802 | `OptEC ugC/m^3` | `Optical_EC` |
    | RTCalc802 | `TC ugC/m^3` | `TC` |
    | shared | `Sample Volume Local Condition Actual m^3` | `Sample_Volume` |
    | shared | `OCPk1-ug C` … `OCPk4-ug C` | `OC1_raw` … `OC4_raw` |
    | shared | `Pyrolized C ug` | `PC_raw` |
    | shared | `ECPk1-ug C` … `ECPk5-ug C` | `EC1_raw` … `EC5_raw` |

4. Firmware is inferred post-rename from the presence of per-peak columns
   (`OC{i}_raw`) and logged, so a mixed-firmware batch shows up in the log.
5. Every column that converts cleanly is coerced to numeric; genuinely textual
   columns (sample ID, firmware version, laser-correction string) survive.
6. Derived at L1:
    - `OC{i} = OC{i}_raw / Sample_Volume` for i = 1–4. NaN on RTCalc705, which
      has no per-peak columns, or when `Sample_Volume` is missing (a warning
      names the file).
    - `PC = Thermal_OC − OC1 − OC2 − OC3 − OC4` when all four exist, else NaN.
7. The ~45-column Sunset export is kept whole — laser/temperature correction,
   oven pressures, calibration peak area. It used to be narrowed to 11 columns
   at L1, which put the instrument's own diagnostics out of reach.

## Measurement Parameters

The OC/EC analyzer provides measurements of:

| Parameter | Unit | Description |
|-----------|------|-------------|
| Thermal_OC | μgC/m³ | Thermal organic carbon |
| Thermal_EC | μgC/m³ | Thermal elemental carbon |
| Optical_OC | μgC/m³ | Optical organic carbon |
| Optical_EC | μgC/m³ | Optical elemental carbon |
| OC1-4 | μgC/m³ | Carbon fractions by temperature |
| PC | μgC/m³ | Pyrolyzed carbon |
| TC | μgC/m³ | Total carbon |

## Status & error codes

None. The Sunset export carries no status register; see
[status modes](../../../guide/reader-reference.md#3-how-a-status-judgement-is-made)
for the readers that do evaluate one.

## QC rules

| Rule | Condition | Severity |
|------|-----------|----------|
| `Invalid Carbon` | any of `Thermal_OC`, `Thermal_EC`, `Optical_OC`, `Optical_EC`, `TC`, `OC1`–`OC4`, `PC` is `<= -5` (`MIN_VALUE`) or `> 100` µgC/m³ (`MAX_VALUE`) | error |
| `Below MDL` | any of the four MDL columns is `<=` its detection limit | advisory |
| `Spike` | sudden change in `Thermal_OC`, `Thermal_EC`, `Optical_OC` or `Optical_EC` (`spike_detection`, `max_change_rate=3.0`) | error |
| `Missing OC` | `Thermal_OC` **or** `Optical_OC` is NaN | error |

`Below MDL` is advisory because a sub-MDL carbon fraction is a real measurement
of clean air, not a broken row: invalidating it deleted whole clean-air periods
along with the other fractions in the row. Promote it per run with
`flag_severity={'Below MDL': 'error'}` (see
[severity](../../../guide/reader-reference.md#severity-not-every-flag-is-fatal)).

### Minimum Detection Limits

Class constants on the reader (`Reader.MDL`), **not** the config `meta`:

| Parameter | MDL (μgC/m³) |
|-----------|--------------|
| Thermal_OC | 0.3 |
| Optical_OC | 0.3 |
| Thermal_EC | 0.015 |
| Optical_EC | 0.015 |

## Output

L2 carries the carbon fractions plus the remaining source columns — the
fractions are the product, but the metadata beside them is what explains a bad
one.

| Column | Unit | Description |
|--------|------|-------------|
| Thermal_OC | μgC/m³ | Thermal organic carbon |
| Thermal_EC | μgC/m³ | Thermal elemental carbon |
| Optical_OC | μgC/m³ | Optical organic carbon |
| Optical_EC | μgC/m³ | Optical elemental carbon |
| TC | μgC/m³ | Total carbon |
| OC1, OC2, OC3, OC4 | μgC/m³ | Per-peak OC fractions, `OC{i}_raw / Sample_Volume` (NaN on RTCalc705) |
| PC | μgC/m³ | Pyrolyzed carbon, `Thermal_OC − OC1 − OC2 − OC3 − OC4` |
| remaining source columns | as exported | `Sample_Volume`, `*_raw` peaks, laser/temperature corrections, oven pressures, … |

Files written per read are listed in
[RawDataReader Reference §1](../../../guide/reader-reference.md#files-written).

## Notes

- Provides critical information about combustion sources
- Helps identify secondary organic aerosol formation
- Combines thermal and optical analysis methods
- Standardizes output across different instrument formats
