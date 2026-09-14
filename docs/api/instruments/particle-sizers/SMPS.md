# Scanning Mobility Particle Sizer (SMPS)

The SMPS is an instrument used for measuring particle size distributions in the nanometer range.

::: AeroViz.rawDataReader.script.SMPS.Reader

## Raw format

- File pattern: `*.txt` or `*.csv`
    - `.txt` files (tab-delimited) from AIM 8.x / 9.x / **10.3**
    - `.csv` files (comma-delimited) from AIM **11.x**
- Native frequency: `6min` (config fallback; the grid actually used is detected
  per file and reported as `df.attrs['raw_freq']`)
- Encoding: opened with `encoding='utf-8', errors='ignore'` — real files
  contain non-UTF-8 bytes in the sample-path metadata
- Header layout: a metadata block (which names the CPC, see below) followed by
  the data header row. The header row is found by scanning for a first cell of
  `Sample #` (TXT / AIM 10.3, ~row 25) or `Scan Number` (CSV / AIM 11.x,
  ~row 52).
- **Default size grid: 11.8–593.5 nm (110 bins) on AIM 10.3; 11.34–615.27 nm
  (112 bins) on AIM 11.x.** A folder mixing both versions cannot be
  outer-joined safely — see "Mixed AIM versions" below.

### Parse recipe

- Delimiter: tab for `.txt`, comma for `.csv`.
- Time from `Date` + `Start Time`, or from `DateTime Sample Start`. Date
  formats are tried in order until one parses:
    - TXT: `%m/%d/%y %X` (mm/dd/yy, older versions), `%m/%d/%Y %X`
      (mm/dd/yyyy, newer versions), `%Y/%m/%d %X` (AIM 10.3+ exports such as
      `2021/1/3`)
    - CSV: `%d/%m/%Y %X` (dd/mm/yyyy, EU format)
- Some exports are **transposed** — if no date column is found the frame is
  rotated and re-parsed.
- Columns whose *name* contains a comma are taken as a comma-decimal export;
  the comma is rewritten to `.` with a warning.
- Size bins are the numeric column names, converted to float and sorted
  numerically. Expected range 11.8–593.5 nm: a mismatch **warns** (so older
  instrument configs such as 18.8–914 nm still parse for coverage purposes);
  the file is only rejected when the caller passed an explicit `size_range=`.
- The consumed index columns (`Date`, `Start Time`, `DateTime Sample Start`,
  `Sample #`, `Scan Number`, `Diameter Midpoint`) are dropped; every other
  source column is kept through L1.

### Mixed AIM versions

The same physical SMPS exports at different size-bin grids and re-labels many
metadata columns depending on the host software. The reader treats each scan
grid as its own logical instrument — concatenating mismatched grids would
create NaN-only columns that downstream completeness checks read as 100 %
Insufficient. Two independent problems, two mechanisms:

**1. Partition by bin grid (auto-applied):** `_partition_compatible_scans`
buckets files by their sorted size-bin tuple. The bucket with the most rows
wins; the others are dropped before concat with a warning naming every skipped
file. The picked-by-row-count rule means a swarm of tiny minority files cannot
outvote one large export just by file count.

To process the dropped bucket explicitly, either move those files to a
separate folder, or pass `size_range=` to force `_raw_reader` to reject
files outside that exact range:

```python
# Process only AIM 11.x scans in a mixed folder:
df = RawDataReader('SMPS', path=mixed_folder, size_range=(11.34, 615.27))
```

**2. Metadata column aliases:** AIM 11.x renames many metadata columns that
carry the same physical quantity as AIM 10.3. `METADATA_ALIASES` rewrites the
AIM 11.x form to the AIM 10.3 canonical form on every parsed file, so a folder
of either version (or a partitioned-down folder) produces a consistent schema
downstream. The 9 renamed pairs:

| AIM 11.x | → | AIM 10.3 canonical |
|---|---|---|
| `Total Concentration (#/cm³)` | → | `Total Conc. (#/cm)` |
| `Aerosol Temperature (C)` | → | `Sample Temp (C)` |
| `Aerosol Humidity (%)` | → | `Relative Humidity (%)` |
| `Aerosol Density (g/cm³)` | → | `Density (g/cm)` |
| `Impactor D50 (nm)` | → | `D50 (nm)` |
| `Test Name` | → | `Title` |
| `Geo. Std. Dev` | → | `Geo. Std. Dev.` |
| `DMA Column transit time Tf (s)` | → | `tf (s)` |
| `DMA Exit to Optical Detector Td (s)` | → | `td + 0.5 (s)` |

AIM 11.x columns that have no AIM 10.3 equivalent — the 4-way error split
(`Classifier Errors` / `Detector Status` / `Communication Status` /
`Neutralizer Status`), granular DMA timings (`THIGH` / `TLOW` / `TUP` /
`TDOWN`), `Sheath Pressure/Temp/Humidity`, etc. — are intentionally kept
under their AIM 11.x names. Collapsing them onto AIM 10.3's coarser
`Instrument Errors` / `Scan Time` would lose information. If a file already
carries the canonical AIM 10.3 name, the 10.3 column is kept and the AIM 11.x
duplicate dropped.

### CPC metadata

The metadata block above the header names the counter that did the counting
(`Detector Model` — spelled `CPC Model` on AIM 10.3 — plus `Detector S/N` and
`Nano Enhancer`). These are captured while the header row is located and
reported in `df.attrs` as `cpc_detector_model`, `cpc_cpc_model`,
`cpc_detector_s_n`, `cpc_nano_enhancer` (key = field name lower-cased, spaces
and `/` replaced by `_`). The CPC's cut-off decides how far the lowest
channels under-report — see
[Counting Efficiency](../../../theory/counting_efficiency.md). Not corrected
for. The same model string feeds the `CPC Over-range` rule below.

## Measurement parameters

The SMPS provides particle size distribution measurements:

| Parameter | Value | Description |
|-----------|-------|-------------|
| Size range | 11.8-593.5 nm | Default particle diameter range |
| Output | dN/dlogDp | Number concentration per size bin |
| Unit | #/cm³ | Particle number concentration |

## Status & error codes

Mode `text` (see
[status modes](../../../guide/reader-reference.md#3-how-a-status-judgement-is-made)),
across **six** columns; the error masks of whichever columns are present are
OR'd. The same information is reported under different names per
host-software version:

- `Status Flag` (AIM 10.3) ↔ `Detector Status` (AIM 11.x) — positive
  sentinel, OK when `Normal Scan` (e.g. `Conditioner Temperature Error`
  is an error)
- `Instrument Errors` (AIM 10.3) ↔ `Classifier Errors` (AIM 11.x) — error
  tokens, OK when empty (e.g. `Low aerosol flow`, `Neutralizer not active`)
- `Communication Status` (AIM 11.x only) — OK when `0`
- `Neutralizer Status` (AIM 11.x only) — OK when `ON`

There are no numeric codes: the values are free-text tokens, so no status
register table exists and `df.attrs['status_conditions']` is not produced for
SMPS.

**Not errors:**

- Empty cells (`''`, `'nan'`, and the Python-None-stringified `'None'` that
  appears when a column is missing from some files of a multi-file concat)
  are never errors.
- `Normal Scan` is auto-whitelisted on the error-token columns too, because
  some sites (e.g. FS) write the positive sentinel there instead of leaving
  the cell blank.
- Tokens listed in the `ignored_status_errors` kwarg are exempted, with
  comma-split semantics: `"Low aerosol flow,Neutralizer not active"` passes
  when both tokens are whitelisted.

Until all six columns were listed an AIM 11.x export had **neither** 10.3
name, so `Status Error` could never fire on it. The reader now calls
`check_status_columns` first and logs which dialect's columns it found; an
export with none of the six leaves the rule inert *with a warning*.

#### Whitelisting benign status warnings

If an instrument runs in a known-low-aerosol mode and reports `"Low aerosol
flow"` on every scan, every row trips Status Error. Pass
`ignored_status_errors=[...]` to RawDataReader to suppress those tokens:

```python
df = RawDataReader(
    instrument='SMPS', path='/data/TP_SMPS',
    start='2026-01-01', end='2026-05-31',
    ignored_status_errors=['Low aerosol flow', 'Neutralizer not active'],
)
```

Token-level matching: a row passes when EVERY comma-split token is either
the OK sentinel or in the whitelist. `"Low aerosol flow,Sheath flow
error"` still fails because `Sheath flow error` is not whitelisted.

## QC rules

Before the rules run, the bins are restricted to `size_range` (default
11.8–593.5 nm) and the total number concentration is computed as
Σ (dN/dlogDp × dlogDp) over the per-bin widths (see "Total concentration"
below).

| Rule | Condition | Severity |
|------|-----------|----------|
| **Status Error** | any of the six status columns reports a non-whitelisted token (see above) | error |
| **Insufficient** | an hour holds < 50 % of the scans it could have held at the detected frequency (edge hours scaled by coverage) | advisory (`WARNING`) — recorded, data kept |
| **Invalid Number Conc** | total < 10 or > 1e6 #/cm³; a NaN total is also flagged. Override per run with `min_total_conc=` / `max_total_conc=` | error |
| **CPC Over-range** | any bin's dN/dlogDp exceeds the per-bin ceiling derived from the CPC's rated maximum and the recorded sheath ratio; inert (logged) when the detector model is unknown or the flow columns are absent. Override with `cpc_max_conc=` (or `cpc_model=`) | error |
| **DMA Water Ingress** | any bin ≥ 400 nm (`LARGE_BIN_THRESHOLD`) exceeds 4 000 dN/dlogDp (`MAX_LARGE_BIN_CONC`) — water contamination in the DMA column | error |
| **Truncated Scan** | the scan has counts, but every bin at or above 2 × the smallest bin (`TRUNCATED_SCAN_FACTOR`, 23.6 nm on the standard grid) is exactly zero — the DMA voltage ramp never completed, not a nucleation burst (a real burst still has particles above 20 nm). Seen at FS from 2026-08 at ~5 % of scans; passes every other rule, so it needs its own | error |

Thresholds live on the reader class: `MIN_TOTAL_CONC = 10`,
`MAX_TOTAL_CONC = 1e6`, `MAX_LARGE_BIN_CONC = 4000`, `LARGE_BIN_THRESHOLD = 400`.

### Total concentration

The total is Σ (dN/dlogDp × dlogDp) using the per-bin widths from
`bin_widths`, which is also correct on a non-uniform grid. Until 2026-09-09
(v0.4.6) two bugs made the `Invalid Number Conc` thresholds mean something
other than they said: a natural log was used where the data is dN/dlog₁₀Dp,
inflating every total by ln 10 = 2.3× (so `MAX_TOTAL_CONC = 1e7` was really
4.34e6 and `MIN_TOTAL_CONC = 2000` was 868), and one column was dropped
before diffing so the mean step averaged n−2 gaps instead of n−1. The fixed
total is verified against the instrument's own `Total Conc.` column at
0.996–0.999.

The thresholds changed in the same fix:

- `MIN_TOTAL_CONC` was 2000, which made the reader unusable at any clean
  site: EBAS background stations sit at 50–300 /cm³ (Zeppelin's median is
  95), so 99–100 % of their record was rejected. A minimum is there to catch
  "instrument off / no flow", which reads ~0, not to encode an urban site's
  typical loading.
- `MAX_TOTAL_CONC` was 1e7, which caught 19 % of the scans a five-station
  TCLab audit found implausible; 1e6 catches 30 % and is still above any
  credible ambient total (roadside peaks reach 2–5e5). Implausible *shapes*
  are left to the CPC and water-ingress rules.

### CPC Over-range

The DMA passes one narrow mobility band at a time, so the CPC only ever sees
a slice of the distribution — the rated maximum is a **per-bin** limit, not a
limit on the total (comparing it against the total would be a category
error). The reader takes the detector model from the file header
(`Detector Model` / `CPC Model`; `cpc_model=` overrides), looks up its rated
maximum in `CPC_MAX_CONC`, and converts it to a dN/dlogDp ceiling per bin
using the sheath ratio β = `Aerosol Flow(lpm)` / `Sheath Flow(lpm)` from the
data rows (NaN ratios filled with the median) and the file's own
`Mean Free Path (m)` when present (otherwise 67.3 nm, the reference state
296.15 K / 101.3 kPa). A scan with any bin above its ceiling is flagged.

| CPC model | Rated maximum (#/cm³) |
|---|---|
| `3772` | 1e4 (single-count only, no photometric mode) |
| `3787` | 2.5e5 |
| `3788` | 4e5 |
| `3022` / `3022A` | 1e7 (photometric above ~1e4; effectively unconstrained) |

The model string is matched on the longest known key it contains (`3788 Low
Flow` → `3788`; `3022A` is not answered by `3022`). The ceiling is a curve,
not a constant: the transfer-function width in diameter depends on the local
slope |dlnZ/dlnDp| (≈2 in the free-molecular regime, ≈1 in the continuum),
so it is about 40 % lower at 600 nm than at 12 nm, and a higher sheath ratio
*raises* it. Unknown models leave the rule inert with a debug log entry; pass
`cpc_max_conc=` (a number, or a dict such as `{'3022': 1e7}` to extend the
table) to enable or override it.

## Output

The L2 frame holds **the dN/dlogDp matrix only** (diameters in nm as
columns) plus the QC bookkeeping; all metadata and status columns are dropped
in `_process`. Statistics are *not* in the frame.

| Column | Unit | Description |
|--------|------|-------------|
| Size bins (float diameters, nm) | dN/dlogDp | Number concentration for each particle size |

At L3 the size-distribution sidecars are written next to the main output:

- `{prefix}_dNdlogDp.csv` — number distribution
- `{prefix}_dSdlogDp.csv` — surface distribution, `π·d²·dN`
- `{prefix}_dVdlogDp.csv` — volume distribution, `π·d³/6·dN`
- `{prefix}_stats.csv` — QC-aligned summary statistics from `psd_stats`
  (total / GMD / GSD / mode, mode fractions); a failure here is logged and
  never fails the read

Pass `append_stats=True` to also append the statistics columns to the
returned frame; the default keeps it a clean PSD matrix that `psd_stats` /
`merge_psd` / `SizeDist` consume directly. The returned frame's `df.attrs`
additionally carries the `cpc_*` metadata described above.

Files written per read are listed in
[RawDataReader Reference §1](../../../guide/reader-reference.md#files-written).

## Notes

- Different AIM software versions may produce different file formats — see
  "Mixed AIM versions" above for how the reader isolates and reconciles them
- Size range validation ensures data quality
- DMA water ingress detection: High concentrations in bins ≥400nm indicate water contamination in the DMA column
- Automatic format detection and parsing
