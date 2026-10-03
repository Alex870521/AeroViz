# Aerodynamic Particle Sizer (APS)

The APS is an instrument used for measuring aerodynamic particle size distributions in the micrometer range.

::: AeroViz.rawDataReader.script.APS.Reader

## Raw format

- File pattern: `*.txt`, tab-delimited
- Native frequency: `6min` is the config fallback, but the file header carries
  `Sample Time` (115 s in the corpus) — **not** a whole number of minutes.
  The native grid follows the period detected per file, so scans are not lost
  to bin collisions; `df.attrs['raw_freq']` reports what was actually used.
- Encoding: opened with `encoding='utf-8', errors='ignore'`
- Header layout: ~6 metadata lines (`Sample File`, `Sample Time`, `Density`,
  `Stokes Correction`, `Lower/Upper Channel Bound`) then a `Sample #` header
  row, found by scanning for that first cell (so files with several
  concatenated headers still locate it)
- Time columns: `Date` and `Start Time`
- Size distribution data: columns 3–54 of the export (the under-range
  `<0.523` column plus the 51 bins)

### Parse recipe

- Transposed exports (`Sample #` as a row rather than a column header) are
  rotated with `set_index('Sample #').T`; if that fails the reader raises
  `NotImplementedError` **with the original exception attached** and logs
  the first columns it saw.
- Date from `Date` + `Start Time`, formats `%m/%d/%y %H:%M:%S` then
  `%m/%d/%Y %H:%M:%S`; the winning format is logged, and a file matching
  neither raises with the list of known formats.
- Size bins are the numeric column names in 0.5–20 (µm), converted to float
  and rounded to 4 decimal places. Expected grid `(0.542, 19.81, 51 bins)`
  (TSI 3321/3320 factory-fixed); a deviation **warns loudly** but does not
  reject — an 8-year × 4-station audit of 1 485 files showed zero drift, so a
  deviation means a firmware change, and concatenating it with other files
  would create NaN-poisoned columns. The under-range `<0.523` column is kept
  as metadata, not a bin.
- The consumed index columns (`Date`, `Start Time`, `Sample #`,
  `Aerodynamic Diameter`) are dropped; rows with an unparseable or duplicated
  timestamp are dropped; every other source column is kept through L1.

## Measurement parameters

The APS provides aerodynamic particle size distribution measurements:

| Parameter | Value | Description |
|-----------|-------|-------------|
| Size range | 0.542–19.81 µm (51 bins) | Aerodynamic diameter range |
| Output | dN/dlogDp | Number concentration per size bin |
| Unit | #/cm³ | Particle number concentration |

## Status & error codes

Column `Status Flags`, mode `binary_string` (see
[status modes](../../../guide/reader-reference.md#3-how-a-status-judgement-is-made)).
OK is `'0000 0000 0000 0000'` (16-bit binary, all zeros); any bit still set
after clearing the whitelist mask is an error. A missing `Status Flags`
column is logged by `check_status_columns` and leaves the rule inert.

Bit meanings (from the TSI RF command):

- bit `0` (`0000 0000 0000 0001`) — Laser fault
- bit `1` (`0000 0000 0000 0010`) — Total Flow out of range
- bit `2` (`0000 0000 0000 0100`) — Sheath Flow out of range
- bit `3` (`0000 0000 0000 1000`) — Excessive sample concentration
- bit `4` (`0000 0000 0001 0000`) — Accumulator clipped (> 65535)
- bit `5` (`0000 0000 0010 0000`) — Autocal failed
- bit `6` (`0000 0000 0100 0000`) — Internal temperature < 10°C
- bit `7` (`0000 0000 1000 0000`) — Internal temperature > 40°C
- bit `8` (`0000 0001 0000 0000`) — Detector voltage out of range (±10% Vb)
- bit `9` (`0000 0010 0000 0000`) — Reserved (unused)

#### Status Condition Register

The `Status Flags` column is a bitfield: the instrument OR-sums every
active condition and reports the sum, so one value can mean several things at
once. `Reader.STATUS_BITS` carries this table, and it is what turns a raw status
into `df.attrs['status_conditions']` — a named condition instead of a number.

| Bit | Decimal | Condition |
|-----|---------|-----------|
| 8 | `256` | Detector voltage out of range |
| 7 | `128` | Internal temperature > 40°C |
| 6 | `64` | Internal temperature < 10°C |
| 5 | `32` | Autocal failed |
| 4 | `16` | Accumulator clipped |
| 3 | `8` | Excessive sample concentration |
| 2 | `4` | Sheath Flow out of range |
| 1 | `2` | Total Flow out of range |
| 0 | `1` | Laser fault |

The register is written as a space-grouped bit string
(`'0000 0000 0000 0001'` is bit 0, not the number one thousand). Bit 9 is
reserved. Every non-whitelisted bit counts as an error — this table names
the conditions, it does not decide which of them matter.

To stop treating one condition as an error, whitelist its decimal value:

```python
RawDataReader('APS', path, ignored_status_errors=[1])  # ignore Laser fault
```

## QC rules

Before the rules run, the total number concentration is computed as
Σ (dN/dlogDp × dlogDp) over the per-bin widths. A natural log was used here
until 2026-09-09 where the data is dN/dlog₁₀Dp, inflating every total by
ln 10 = 2.303×; that mattered more for APS than for SMPS because the range is
tight — a `MAX_TOTAL_CONC` of 700 was really 304 /cm³, so valid high-loading
scans were being rejected.

| Rule | Condition | Severity |
|------|-----------|----------|
| **Status Error** | `Status Flags` has any non-whitelisted bit set (see above) | error |
| **Insufficient** | an hour holds < 50 % of the scans it could have held at the detected frequency (edge hours scaled by coverage) | advisory (`WARNING`) — recorded, data kept |
| **Invalid Number Conc** | total < 1 or > 700 #/cm³ (`MIN_TOTAL_CONC` / `MAX_TOTAL_CONC`); a NaN total is also flagged | error |

## Output

The L2 frame holds **the dN/dlogDp matrix only** (diameters in **µm** as
columns) plus the QC bookkeeping; `Status Flags` and the other metadata
columns are dropped in `_process`. Statistics are *not* in the frame.

| Column | Unit | Description |
|--------|------|-------------|
| Size bins (0.542–19.81 µm) | dN/dlogDp | Number concentration for each size |

At L3 the same sidecars as SMPS are written next to the main output:
`{prefix}_dNdlogDp.csv`, `{prefix}_dSdlogDp.csv` (`π·d²·dN`, optional via `size_dist_outputs=`),
`{prefix}_dVdlogDp.csv` (`π·d³/6·dN`) and `{prefix}_stats.csv` (from
`psd_stats`, QC-aligned; a failure there is logged and never fails the read).
Pass `append_stats=True` to also append the statistics columns to the
returned frame; the default keeps it a clean PSD matrix for `psd_stats` /
`merge_psd` / `SizeDist`.

Files written per read are listed in
[RawDataReader Reference §1](../../../guide/reader-reference.md#files-written).

## Notes

- Measures aerodynamic particle diameter directly
- Complementary to SMPS for larger particle sizes
- Size range approximately 0.5–20 μm
- Logarithmic bin spacing in size distribution
- Counting efficiency: the APS under-counts at both ends — 85–99 % for solid
  particles, but falling from 75 % at 0.8 µm to 25 % at 10 µm for droplets
  (Volckens & Peters 2005). Not corrected for; see
  [Counting Efficiency](../../../theory/counting_efficiency.md).
