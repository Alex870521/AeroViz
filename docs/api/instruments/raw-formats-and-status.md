# Raw Formats & Status Codes

> **One page, three questions per instrument:** what does the raw file look like,
> how is an instrument error decided, and where does that decision get recorded?
>
> The per-instrument pages under this section describe *usage*. This page is the
> **reference for the parsing recipe and the error/status semantics** — the
> things you need when a file won't parse, when `Status Error` fires on every
> row, or when it never fires at all. For the level model that frames all of
> this, see [Data Levels (L0–L3)](../../guide/data-levels.md).

---

## 1. How a status judgement is made

Every status check goes through one function —
`QualityControl.filter_error_status` (`core/qc.py`) — in one of **four modes**.
The mode determines how the raw status value is interpreted *and* how the
`ignored_status_errors` whitelist is applied.

| Mode | Raw value looks like | Error when | Instruments | `ignored_status_errors` entries are… |
|------|---------------------|-----------|-------------|--------------------------------------|
| `bitwise` | integer, OR-summed bits (`0`, `4`, `536870912`) | any non-whitelisted code in `ERROR_STATES` matches bitwise, or the value equals a `special_codes` entry | AE33, AE43, BC1054, MA350, **TEOM** | integer codes/bits **removed from the error definition** |
| `numeric` | flat integer code (`0`, `4`, `16`) | `status != ok_value` and not NaN | Aurora, NEPH | numeric codes **treated as OK** |
| `text` | free text, possibly comma-joined (`Normal Scan`, `Low aerosol flow,Neutralizer not active`) | any token is neither `ok_value` nor whitelisted | SMPS (both status columns) | string tokens, matched **per token** |
| `binary_string` | space-grouped bit string (`0000 0000 0000 0000`) | any non-whitelisted bit remains set after clearing the whitelist mask | APS | integer bit masks **cleared before testing** |

Two behaviours to know:

- **Empty means OK, always.** In `text` mode the sentinels `''`, `'nan'` and
  `'None'` are never errors. (`'None'` arrives when a column is missing from
  *some* files of a multi-file concat: pandas fills with Python `None`, which
  `astype(str)` renders as `'None'`.)
- **A missing status column is silently OK.** If `status_column` is not in the
  frame, `filter_error_status` returns all-`False` and says nothing. This is
  deliberate (mixed exports), but it means a status rule can be completely inert
  without any signal — see [§6 Coverage gaps](#6-coverage-gaps).

Entries in `ignored_status_errors` that don't fit a mode are skipped, so the same
whitelist can be passed to any reader safely:

```python
RawDataReader('TEOM', path, ignored_status_errors=[536870912])          # bitwise: ignore "Dryer A"
RawDataReader('SMPS', path, ignored_status_errors=['Low aerosol flow']) # text: per-token
RawDataReader('APS',  path, ignored_status_errors=[1, 2])               # binary_string: clear bits 0,1
RawDataReader('Aurora', path, ignored_status_errors=[4, 16])            # numeric: extra OK codes
```

---

## 2. Where a judgement is recorded

| Channel | Written by | Granularity | Content |
|---------|-----------|-------------|---------|
| `QC_Flag` column | `_QC` / `_process` (L2) | per row | `"Valid"`, or comma-joined names of every rule that fired |
| `{inst}.log` | all levels | per run | parse warnings, skipped/dropped files, mixed-resolution & stray-date warnings, **QC Summary** (count + % per rule), rates |
| `report.json` | L3 | per week / month + timeline | `rates.weekly` / `rates.monthly` (acquisition / yield / total), `timeline` of operational & down periods with reasons |
| `df.attrs` | L3 (`_stamp`) | per call | provenance, `coverage_*` vs `requested_*`, `raw_freq`, `freq_mixed`, `acquisition_rate` / `yield_rate` / `total_rate` |
| `_read_{inst}_qc.csv` | L2 | per row | the flagged frame *before* masking — the only place where flag and value coexist |

**Lifecycle of one flag:**

```
_QC       → QCRule.condition(df) → mask → QC_Flag = "Status Error, Insufficient"
_process  → may append via update_qc_flag()  → "Status Error, Insufficient, Invalid AAE"
log       → "  Status Error: 24312 (4.9%)"
report    → row counts toward yield rate (a period is valid when >50% of its points are "Valid")
__call__  → QC_Flag != "Valid"  →  entire row set to NaN, QC_Flag dropped
```

!!! warning "Every flag is fatal today"
    There is no severity distinction: an advisory flag (`Below MDL`,
    `Upscale Warning`, `Insufficient`, `Spike`) masks the row exactly as hard as
    `Status Error`. If you need the underlying values, read
    `_read_{inst}_qc.csv`, or call with `qc=False` (which returns L1 — no QC and
    also no resampling). Tracked as P1-5 in
    [Data Levels §7](../../guide/data-levels.md#7-non-conformance-what-still-needs-fixing).

### QC_Flag vocabulary

| Flag | Meaning | Used by |
|------|---------|---------|
| `Valid` | passed every rule | all |
| `Status Error` | instrument status register reports a non-whitelisted condition | AE33, AE43, BC1054, MA350, SMPS, APS, Aurora, NEPH, TEOM |
| `Insufficient` | < 50 % of the expected points in that clock hour carry data | AE33, AE43, BC1054, MA350, SMPS, APS, Aurora, NEPH, TEOM |
| `Invalid BC` | any BC channel ≤ 0 or > 20 000 ng/m³ | AE33, AE43, BC1054, MA350 |
| `Invalid AAE` | \|AAE\| outside 0.7–2.0 (added in `_process`) | AE33, AE43, BC1054, MA350 |
| `Invalid Number Conc` | total number concentration outside range (SMPS 2 000–1e7, APS 1–700 #/cm³) | SMPS, APS |
| `DMA Water Ingress` | any bin > 400 nm exceeds 4 000 dN/dlogDp | SMPS |
| `Invalid Scat Value` | any scattering channel ≤ 0 or > 2 000 Mm⁻¹ | Aurora, NEPH |
| `Invalid Scat Rel` | B < G < R — inverted wavelength dependence | Aurora, NEPH |
| `No Data` | all six scattering channels NaN | Aurora, NEPH |
| `High Noise` | TEOM `noise` ≥ 0.01 | TEOM |
| `Non-positive` | `PM_NV` ≤ 0 or `PM_Total` ≤ 0 | TEOM |
| `NV > Total` | `PM_NV` > `PM_Total` (physically impossible) | TEOM |
| `Spike` | change > 3 × median absolute change, or a large up-down reversal | TEOM, BAM1020, OCEC |
| `Invalid Conc` | PM ≤ 0 or > 500 µg/m³ | BAM1020 |
| `Invalid Carbon` | any carbon fraction ≤ −5 or > 100 µgC/m³ | OCEC |
| `Below MDL` | value at or below the method detection limit | OCEC, IGAC |
| `Missing OC` | `Thermal_OC` or `Optical_OC` missing | OCEC |
| `Mass Closure` | Σ ions > PM2.5 | IGAC |
| `Missing Main` | any of NH₄⁺ / SO₄²⁻ / NO₃⁻ missing | IGAC |
| `Ion Balance` | cation/anion ratio outside 1.5 × IQR | IGAC |
| `Calibration Mode` | `SAMPLE_TYPE != 1` | Xact |
| `Instrument Error` | `ALARM` in 100–110 | Xact |
| `Upscale Warning` | `ALARM` in 200–203 | Xact |
| `Invalid Value` | element concentration outside 0–100 000 ng/m³ | Xact |
| `Internal Std Drift` | Nb outside ±20 % of its median | Xact |
| `Negative` | any numeric column < 0 | EPA |

---

## 3. Aethalometers / BC monitors

### AE33

| | |
|---|---|
| **Pattern** | `[!ST|!CT|!FV]*[!log]_AE33*.dat` |
| **Native freq** | `1min` |
| **Parse** | `read_table(delimiter=r'\s+', skiprows=5, usecols=range(67))`; header is line 6, semicolon-suffixed names are stripped; index built from columns 0+1 (`Date(yyyy/MM/dd)` + `Time(hh:mm:ss)`) |
| **Quirks** | Files < 550 KB log "may not be a whole daily data". The pattern's `[!ST|!CT|!FV]` is a *single-character* negated class (excludes `S T C F V | !` as the first character), **not** an alternation of `ST`/`CT`/`FV` prefixes — it happens to filter the ST/CT/FV log files but not for the reason it looks like. |
| **Status** | column `Status`, mode `bitwise`. Raw file also carries `ContStatus`, `DetectStatus`, `LedStatus`, `ValveStatus`, which are **not** checked. |
| **Error codes** | 1 tape advance / fast cal / warm-up · 2 first measurement (obtaining ATN0) · 3 stopped · 4 flow off by > 0.5 LPM · 16 calibrating LED · 32 calibration error · 1024 stability test · 2048 clean-air test · 4096 optical test |
| **Deliberately not errors** | 128 / 256 (tape *low* warnings) and therefore 384 — data is still valid |
| **QC rules** | `Status Error`, `Invalid BC` (0–20 000 ng/m³ over BC1–BC7), `Insufficient`; `Invalid AAE` added in `_process` |
| **L2 output** | `BC1`–`BC7`, `abs_370`…`abs_950`, `abs_550`, `AAE`, `eBC`, `BB(%)` when present, `QC_Flag` |

### AE43

Identical to AE33 except:

- **Pattern** `[!ST|!CT|!FV]*[!log]_AE43*.dat`; parsed with
  `read_csv(parse_dates=['StartTime'], index_col='StartTime')`.
- Keeps only the rows of the **last `SetupID`** in the file (a setup change
  mid-file discards the earlier segment).
- `ERROR_STATES` **still contains 384** ("tape error"), unlike AE33 — an
  unresolved inconsistency, see
  [Data Levels P1-9](../../guide/data-levels.md#p1-rule-violations).

### BC1054

| | |
|---|---|
| **Pattern** | `*.csv`, native `1min` |
| **Parse** | header row located by scanning the first 20 lines for one starting with `Time` or `Raw_Time` (variants seen: header on line 1; `Raw_Time,Time,…`; a `Data Report` / `User Report` block plus 3 metadata lines; leading blank lines). Then `read_csv(parse_dates=True, index_col=0, skiprows=skip)`; spaces stripped from column names; `BC1 (ng/m3)`→`BC1` … `BC10`, `Flow(lpm)`→`Flow`, `WS`, `WD`, `AT`, `RH`, `BP` |
| **Quirks** | With both `Raw_Time` and `Time` present, **`Raw_Time` becomes the index and `Time` is dropped** — in the NZ 2025 fixture the two differ by hours on some rows. `_QC` first removes rows identical to their previous *or* next row (consecutive-duplicate filter) before flagging. |
| **Status** | column `Status`, mode `bitwise` |
| **Error codes** | 1 power failure · 2 digital sensor link failure · 4 tape move failure · 8 maintenance · 16 flow failure · 32 automatic tape advance · 64 detector failure · 256 sensor range · 512 nozzle move failure · 1024 SPI link failure · 2048 calibration audit · 65536 tape move |
| **QC rules** | `Status Error`, `Invalid BC` (BC1–BC10), `Insufficient`, + `Invalid AAE` |
| **L2 output** | `abs_370`…`abs_950`, `abs_550`, `AAE`, `eBC`, **plus every non-BC source column** (Flow, AT, RH, BP, …), `QC_Flag` |

### MA350

| | |
|---|---|
| **Pattern** | `*.csv`, native `1min` |
| **Parse** | `read_csv(parse_dates=['Date / time local'], index_col='Date / time local')`; renames `UV/Blue/Green/Red/IR BCc`→`BC1`–`BC5`, `Biomass BCc`→`BB mass`, `Fossil fuel BCc`→`FF mass`, `Delta-C`, `AAE`→`AAE_ref`, `BB (%)`→`BB` |
| **Status** | column `Status`, mode `bitwise` (rule is inert if the firmware labels it differently) |
| **Error codes** | 1 power failure · 2 start up · 4 tape advance · 16 optical saturation · 32 sample timing error · 128 flow unstable · 256 pump drive limit · 2048 system busy · 8192 tape jam · 16384 tape at end · 32768 tape not ready · 65536 tape transport not ready · 262144 invalid date/time · 524288 tape error |
| **QC rules** | `Status Error`, `Invalid BC` (BC1–BC5), `Insufficient`, + `Invalid AAE` |
| **L2 output** | `abs_375`, `abs_470`, `abs_528`, `abs_625`, `abs_880`, `abs_550`, `AAE`, `eBC`, all non-BC columns, `QC_Flag`. Note the vendor's own `AAE` is preserved separately as `AAE_ref`. |

---

## 4. Particle sizers

### SMPS

| | |
|---|---|
| **Pattern** | `*.txt`, `*.csv`; native `6min` |
| **Parse** | opened with `encoding='utf-8', errors='ignore'` (real files contain non-UTF-8 bytes in the sample-path metadata). Header row is found by scanning for a first cell of `Sample #` (TXT / AIM 10.3, ~row 25) or `Scan Number` (CSV / AIM 11.x, ~row 52). Delimiter: tab for `.txt`, comma for `.csv`. Time from `Date` + `Start Time`, or `DateTime Sample Start`; date formats tried in order (`%m/%d/%y`, `%m/%d/%Y`, `%Y/%m/%d` for TXT; `%d/%m/%Y` for CSV). Some exports are **transposed** — if no date column is found the frame is rotated and re-parsed. |
| **Size bins** | numeric column names → float; expected 11.8–593.5 nm. A mismatch **warns**; the file is only rejected when the caller passed an explicit `size_range`. |
| **AIM reconciliation** | Two independent problems. (1) *Mixed bin grids in one folder* → `_partition_compatible_scans` keeps the group with the most rows and names every dropped file in a warning. (2) *Renamed metadata* → `METADATA_ALIASES` rewrites AIM 11.x names to the AIM 10.3 canonical form (`Total Concentration (#/cm³)`→`Total Conc. (#/cm)`, `Aerosol Temperature (C)`→`Sample Temp (C)`, `Aerosol Humidity (%)`→`Relative Humidity (%)`, `Aerosol Density (g/cm³)`→`Density (g/cm)`, `Impactor D50 (nm)`→`D50 (nm)`, `Test Name`→`Title`, `Geo. Std. Dev`→`Geo. Std. Dev.`, `DMA Column transit time Tf (s)`→`tf (s)`, `DMA Exit to Optical Detector Td (s)`→`td + 0.5 (s)`). AIM 11.x-only columns keep their own names. |
| **Status** | **two** columns, mode `text`, masks OR'd: `Status Flag` with `ok_value='Normal Scan'`, and `Instrument Errors` with `ok_value=''` plus `'Normal Scan'` auto-whitelisted. Rationale: on AIM 10.3 `.TXT` (and AIM 11.x) the real warnings — `Low aerosol flow`, `Neutralizer not active`, comma-combined — live in `Instrument Errors` while `Status Flag` is absent or empty; some sites' `Instrument Errors` is empty-when-OK, others write the positive `Normal Scan` sentinel there. Both dialects must pass. |
| **QC rules** | `Status Error`, `Insufficient`, `Invalid Number Conc` (2 000–1e7 #/cm³, NaN total ⇒ flagged), `DMA Water Ingress` (any bin ≥ 400 nm > 4 000 dN/dlogDp) |
| **L2 output** | **the dN/dlogDp matrix only** (diameters in nm as columns) + `QC_Flag`. Statistics are *not* in the frame. |
| **L3 sidecars** | `{prefix}_dNdlogDp.csv`, `_dSdlogDp.csv` (`πd²·dN`), `_dVdlogDp.csv` (`πd³/6·dN`), `_stats.csv` (from `psd_stats`). Pass `append_stats=True` to also append the statistics columns to the returned frame. |
| **Gap** | AIM 11.x CSV exports have **neither** configured status column — errors are split into `Detector Status`, `Classifier Errors`, `Communication Status`, `Neutralizer Status`, none of which is checked. `Status Error` can never fire for those files. |

### APS

| | |
|---|---|
| **Pattern** | `*.txt`; native `6min` |
| **Parse** | tab-separated; ~6 metadata lines (`Sample File`, `Sample Time`, `Density`, `Stokes Correction`, `Lower/Upper Channel Bound`) then a `Sample #` header row. Transposed exports are rotated (`set_index('Sample #').T`), and a failure there raises `NotImplementedError` **with the original exception attached**. Date from `Date` + `Start Time`, formats `%m/%d/%y %H:%M:%S` then `%m/%d/%Y %H:%M:%S`; the winning format is logged. |
| **Size bins** | numeric column names in 0.5–20 (µm) → float, rounded to 4 dp. Expected grid `(0.542, 19.81, 51 bins)`; deviation **warns loudly** (an 8-year × 4-station audit of 1 485 files showed zero drift, so a deviation means a firmware change — and would reproduce the NaN-poisoned-concat problem SMPS had). The under-range `<0.523` column is kept as metadata, not a bin. |
| **Status** | column `Status Flags`, mode `binary_string`; OK is `'0000 0000 0000 0000'` |
| **Bit meanings** | 0 laser fault · 1 total flow out of range · 2 sheath flow out of range · 3 excessive sample concentration · 4 accumulator clipped (> 65535) · 5 autocal failed · 6 internal temp < 10 °C · 7 internal temp > 40 °C · 8 detector voltage out of range · 9 reserved |
| **QC rules** | `Status Error`, `Insufficient`, `Invalid Number Conc` (1–700 #/cm³) |
| **L2 output / sidecars** | as SMPS, diameters in **µm** |

### GRIMM

| | |
|---|---|
| **Pattern** | `*.dat`; native `6min` |
| **Parse** | `read_csv(header=233, delimiter='\t', index_col=0, parse_dates=[0], encoding='ISO-8859-1', dayfirst=True)` — the header row is a **hard-coded line number**; then columns 0–10 and the trailing 5 (or from column 128 for files named `A407ST*`) are dropped, and all values are divided by `0.035`. Empty files are reported with `print` (not the logger) and skipped. |
| **Status** | none |
| **QC rules** | **none** — `_QC` returns the frame unchanged, so no `QC_Flag` is produced. With the default `qc=True` this currently raises `AttributeError: … 'report_dict'`; use `qc=False`. See [Data Levels P0-1](../../guide/data-levels.md#p0-live-breakage). |

---

## 5. Nephelometers, mass, chemistry, external sources

### Aurora

| | |
|---|---|
| **Pattern** | `*.csv`; native `1min` |
| **Parse** | `read_csv(low_memory=False, index_col=0)`; index coerced to datetime; column aliases `0°σspB/G/R`→`B/G/R`, `90°σspB/G/R`→`BB/BG/BR`, and `Blue/Green/Red`→`B/G/R`, `B_Blue/B_Green/B_Red`→`BB/BG/BR`; `Raw_Data_Time` dropped |
| **Status** | first match among `Status`, `status`, `Error`, `error`, `Flag`, `flag` is renamed to `Status`; mode `numeric`, `ok_value=0` |
| **QC rules** | `Status Error`, `No Data`, `Invalid Scat Value` (0–2 000 Mm⁻¹), `Invalid Scat Rel` (`B < G & G < R`), `Insufficient` |
| **L2 output** | `sca_550`, `SAE`, plus all non-scattering columns (T1, T2, RH, P, S1, S2, …), `QC_Flag` |
| **Gap** | the production CSV (`Data_Time, Raw_Data_Time, Red, Green, Blue, B_Red, B_Green, B_Blue, T1, T2, RH, P, S1, S2`) contains **none** of the six candidate status names. The instrument's status is in the hex-ish `S1`/`S2` fields (values like `00`, `07`, `04`, `AB`), which nothing decodes. `Status Error` is therefore permanently all-`False` for this format. |

### NEPH

| | |
|---|---|
| **Pattern** | `*.dat`; native `5min` |
| **Parse** | record-oriented, no header: `read_csv(header=None, names=range(11))` then grouped by the record type in column 0. `T` = timestamp (`YYYY MM DD HH MM SS` across columns 1–6, zero-padded and concatenated). `D` = data; the `NBXX` sub-group is used, falling back to `NTXX`, columns 3–8 × 1e6 → `B, G, R, BB, BG, BR`. `Y` = state: col 2 pressure, 3 temp1, 4 temp2, 5 RH, **9 status**. A file containing a record type outside `{B,G,R,D,T,Y,Z}` is skipped with a warning. |
| **Quirks** | `Y`-row fields are attached to the data frame **positionally** (`.values`), so a file with unequal `D` and `Y` counts misaligns or raises. |
| **Status** | column `status` (from `Y` row field 9, e.g. `0000`), mode `numeric`, `ok_value=0` |
| **QC rules / output** | same five rules and same outputs as Aurora |

### TEOM

| | |
|---|---|
| **Pattern** | `*.csv`; native `6min` |
| **Parse** | `read_csv(skiprows=3, index_col=False)`; **both** alias maps are applied to every file because real exports mix conventions. `remote`/GUI names (`Time Stamp`→`time`, `System status`→`status`, `PM-2.5 base MC`→`PM_NV`, `PM-2.5 MC`→`PM_Total`, `PM-2.5 TEOM noise`→`noise`, …) and `usb`/SNMP names (`tmoStatusCondition_0`→`status`, `tmoTEOMABaseMC_0`→`PM_NV`, `tmoTEOMAMC_0`→`PM_Total`, `tmoTEOMANoise_0`→`noise`, …) land on the same canonical short names. Format is then detected post-rename and logged: `time` present ⇒ remote (timestamps like `07 - 六月 - 2025 12:00:00`, Chinese month names mapped, `format='%d - %m - %Y %X'`); `Date`+`Time` ⇒ usb. Neither ⇒ a file-named `NotImplementedError`. |
| **Status** | column `status`, mode **`bitwise`** — this is the subtle one: the TEOM `status condition` register is a **32-bit bitfield** (TEOM 1405 / 1405-F manual, Appendix A, Table A-1), so the instrument reports the *decimal sum* of every active warning. Treating it as a flat code (`status != 0`) makes any co-set bit unmaskable; bitwise mode lets one condition be whitelisted regardless of what else is set. `ERROR_STATES = [1 << b for b in range(32)]` — every bit counts as an error by default. |
| **Documented bits** | 30 (1073741824) %RH high side A · 29 (536870912) dryer A · 28 (268435456) cooler A · 27 (134217728) exchange filter A · 26 (67108864) flow A · 25 (33554432) heaters side A · 24 (16777216) mass transducer A · 22–16 the same for side B · 14 user I/O · 13 FDMS device · 12 head 1 · 11 head 0 · 10 MFC 1 · 9 MFC 0 · 8 system bus · 7 vacuum pressure · 6 case/cap heater · 5 FDMS valve · 4 bypass flow · 3 ambient RH & temp sensor · 2 database log failure · 1 enclosure temp · 0 power failure |
| **QC rules** | `Status Error`, `High Noise` (≥ 0.01), `Non-positive`, `NV > Total`, `Spike`, `Insufficient` |
| **L2 output** | `Volatile_Fraction = (PM_Total − PM_NV) / PM_Total` **plus every other column** — `OUTPUT_COLUMNS` exists but is never applied |

### BAM1020

| | |
|---|---|
| **Pattern** | `*.csv`; native `1h` |
| **Parse** | `read_csv(parse_dates=True, index_col=0, usecols=range(0, 21))`; `Conc (mg/m3)`→`Conc`; the literal value `1` is replaced with NA; then ×1000 (mg/m³ → µg/m³) |
| **Status** | none |
| **QC rules** | `Invalid Conc` (0–500 µg/m³), `Spike` |
| **L2 output** | `Conc`, `QC_Flag` |

### OCEC

| | |
|---|---|
| **Pattern** | `*LCRes.csv`; native `1h` |
| **Parse** | `read_csv(skiprows=3, on_bad_lines='skip')`; time from `Start Date/Time`, formats `%m/%d/%Y %I:%M:%S %p` (RTCalc705 default) then `%m/%d/%Y %H:%M:%S`, then **rounded to `1h`**. Three alias maps are applied unconditionally: RTCalc705 (`Thermal/Optical OC (ugC/LCm^3)`→`Thermal_OC`, `OC=TC-BC (ugC/LCm^3)`→`Optical_OC`, `BC (ugC/LCm^3)`→`Optical_EC`, …), RTCalc802 (`OC ugC/m^3 (Thermal/Optical)`→`Thermal_OC`, `OptEC ugC/m^3`→`Optical_EC`, …), and the shared per-peak set (`OCPk1-4-ug C`→`OC1_raw`…, `Pyrolized C ug`→`PC_raw`, `ECPk1-5-ug C`→`EC*_raw`, `Sample Volume Local Condition Actual m^3`→`Sample_Volume`). Firmware is inferred from the presence of per-peak columns and logged. |
| **Derived at L1** | `OC{i} = OC{i}_raw / Sample_Volume` (NaN on RTCalc705, which has no per-peak columns, or if `Sample_Volume` is missing — warned); `PC = Thermal_OC − OC1 − OC2 − OC3 − OC4` when all four exist, else NaN |
| **Status** | none |
| **MDL** | `Thermal_OC` 0.3, `Optical_OC` 0.3, `Thermal_EC` 0.015, `Optical_EC` 0.015 µgC/m³ (class constant, **not** the config `meta`) |
| **QC rules** | `Invalid Carbon` (−5 … 100 µgC/m³), `Below MDL` (`value <= MDL`), `Spike`, `Missing OC` |
| **L2 output** | `Thermal_OC`, `Thermal_EC`, `Optical_OC`, `Optical_EC`, `TC`, `OC1`–`OC4`, `PC`, `QC_Flag` |

### IGAC

| | |
|---|---|
| **Pattern** | `*.csv`; native `1h` |
| **Parse** | `read_csv(parse_dates=True, index_col=0, na_values='-')` with `encoding='utf-8-sig'`; column names stripped; everything coerced to numeric |
| **Status** | none |
| **MDL** | class constant, 9 ions (µg/m³): Na⁺ 0.06, NH₄⁺ 0.05, K⁺ 0.05, Mg²⁺ 0.12, Ca²⁺ 0.07, Cl⁻ 0.07, NO₂⁻ 0.05, NO₃⁻ 0.11, SO₄²⁻ 0.08. The config `meta['IGAC']['MDL']` / `['MR']` (17 species incl. gases) is **unused** by this reader. |
| **QC rules** | `Mass Closure` (Σ ions > `PM2.5` when that column exists), `Missing Main` (NH₄⁺/SO₄²⁻/NO₃⁻), `Below MDL`, `Ion Balance` (cation/anion ratio outside 1.5 × IQR) |
| **L2 output** | the 9 MDL ions present in the file + `QC_Flag` (other source columns are dropped) |

### Xact

| | |
|---|---|
| **Pattern** | `*.csv`; native `1h` |
| **Parse** | **two** header rows: line 0 is element names in caps (`MAGNESIUM,,ALUMINIUM,,…`), line 1 is the real header; the data rows carry one extra trailing field, absorbed as `_extra_` and dropped. `TIME` parsed as `%m/%d/%Y %H:%M:%S`. Rows with `Sample Type != 1` are dropped **before** rounding to `1h` (the daily 00:00–00:30 QA check would otherwise displace a valid 00:30 sample). Element columns are matched by pattern (`Mg 12 (ng/m3)`→`Mg`, `Al Uncert (ng/m3)`→`Al_uncert`); environment columns are renamed to short forms (`AT (C)`→`AT`, `FLOW 25 (slpm)`→`FLOW_25`, …); `PUMP START TIME`, `Output Pin 7`, `XC VER` dropped. |
| **Status** | column `ALARM`, matched by **exact code**, not bitwise; `0` = normal. `decode_alarm()` turns a code into text. |
| **Alarm codes** | errors 100 X-ray voltage · 101 X-ray current · 102 tube temperature · 103 enclosure temperature · 104 tape · 105 pump · 106 filter wheel · 107 dynamic rod · 108 nozzle · 109 energy calibration · 110 software. Warnings 200 upscale Cr · 201 upscale Pb · 202 upscale Cd · 203 upscale Nb. |
| **QC rules** | `Calibration Mode`, `Instrument Error` (100–110), `Upscale Warning` (200–203), `Invalid Value` (0–100 000 ng/m³), `Internal Std Drift` (Nb ±20 % of median). Each is registered only if its source column exists. |
| **L2 output** | all columns + `QC_Flag`. `meta['Xact']['MDL']` (45 elements) is **not used** by this reader. |

### VOC — deprecated

`*.csv`, native `1h`. `read_csv(parse_dates=True, index_col=0, na_values=('-','N.D.'))`
with `utf-8-sig`; returns every column. No status, **no QC** (`_QC` is a
pass-through, so no `QC_Flag` — and therefore the `report_dict` crash on
`qc=True`). Emits a `DeprecationWarning` on construction: read the CSV yourself
and pass the frame to `AeroViz.voc` / `voc_potentials`, which validates species
against `support_voc.json` (the single source of truth — the reader deliberately
holds no species list).

### EPA — external, pre-aggregated

`*.csv`, native `1h`, `encoding='big5'`. Accepts the Taiwan EPA hourly exports
(測項 / 直式). Raises if more than one 測站 is present; drops 測站; pivots
`測項`/`資料` into columns when present; renames `AMB_TEMP`→`AT`,
`WIND_SPEED`→`WS`, `WIND_DIREC`→`WD`. Invalid-value markers are normalised by
regex (`…#`→`#`, `…L`→`_`) and then coerced to NaN. Columns reordered to
`SO2, NO, NOx, NO2, CO, O3, THC, NMHC, CH4, PM10, PM2.5, PM1, WS, WD, AT, RH`.
No status; one QC rule: `Negative`.

### Minion — currently broken

`*.csv` / `*.xlsx`, native `1h`, monthly pre-aggregated reports.
`read_excel(index_col=0, parse_dates=True)`; row 0 holds units (saved to
`self.units`, then dropped); `維護校正`→`*`, `Nodata`/NaN→`-`, `0L` and any
`…L` value → `-999`, and every zero outside `WD` → `-999`; `-999` is the
sentinel for "below MDL / invalid". `_raw_reader` also **writes**
`Level1/{file}_Level1.csv` as a side effect.

Three defects to know before touching it:

1. It looks up `meta.get('XRF')`, but the config key is `Xact` — so it raises
   `AttributeError` on the first file and **cannot read anything**.
2. `_QC` produces no `QC_Flag`; it masks values in place and replaces sub-MDL
   values with `0.5 × MDL`, which is L3 work done at L2 with no audit trail.
3. Its `Level1/` output introduces a second, incompatible level vocabulary.

### Q-ACSM — not implemented

`script/Q-ACSM.py` declares only `nam = 'Q-ACSM'`. Because `_raw_reader` and
`_QC` are abstract, `RawDataReader('Q-ACSM', …)` raises
`TypeError: Can't instantiate abstract class Reader …`. It is nevertheless
listed in `meta` and therefore offered in the error message of the instrument
validator.

---

## 6. Coverage gaps

Where the status/QC machinery is *silently* doing nothing:

| Instrument | Symptom | Cause |
|---|---|---|
| **Aurora** | `Status Error` never fires | production CSV has no `Status`/`status`/`Error`/`error`/`Flag`/`flag` column; status is in undecoded hex `S1`/`S2` |
| **SMPS** (AIM 11.x CSV) | `Status Error` never fires | neither `Status Flag` nor `Instrument Errors` exists; errors split into `Detector Status`, `Classifier Errors`, `Communication Status`, `Neutralizer Status` |
| **MA350** | possible | `Status` column presence not verified against a real export |
| **GRIMM, VOC, Minion** | no `QC_Flag` at all | `_QC` is a pass-through (GRIMM, VOC) or masks in place (Minion) → also crashes on the default `qc=True` |
| **All bitwise/numeric/text/binary readers** | a typo'd or renamed status column degrades to "no errors" | `filter_error_status` returns all-`False` for a missing column, without warning |
| **All readers using `Insufficient`** | threshold computed against the *config* frequency, not the detected one | `hourly_completeness_QC(..., freq=self.meta['freq'])` in all nine callers |

Full remediation list, with priorities and suggested order:
[Data Levels §7](../../guide/data-levels.md#7-non-conformance-what-still-needs-fixing).

---

## 7. Summary matrix

| Instrument | Pattern | Native | Status column | Mode | QC rules | `_process` |
|---|---|---|---|---|:---:|:---:|
| AE33 | `…_AE33*.dat` | 1 min | `Status` | bitwise | 4 | ✅ |
| AE43 | `…_AE43*.dat` | 1 min | `Status` | bitwise | 4 | ✅ |
| BC1054 | `*.csv` | 1 min | `Status` | bitwise | 4 | ✅ |
| MA350 | `*.csv` | 1 min | `Status` | bitwise | 4 | ✅ |
| Aurora | `*.csv` | 1 min | `Status` (absent in practice) | numeric | 5 | ✅ |
| NEPH | `*.dat` | 5 min | `status` (`Y` row f9) | numeric | 5 | ✅ |
| SMPS | `*.txt`, `*.csv` | 6 min | `Status Flag` + `Instrument Errors` | text ×2 | 4 | ✅ |
| APS | `*.txt` | 6 min | `Status Flags` | binary_string | 3 | ✅ |
| GRIMM | `*.dat` | 6 min | — | — | 0 | ❌ |
| TEOM | `*.csv` | 6 min | `status` | bitwise (32-bit) | 6 | ✅ |
| BAM1020 | `*.csv` | 1 h | — | — | 2 | ❌ |
| OCEC | `*LCRes.csv` | 1 h | — | — | 4 | ❌ |
| IGAC | `*.csv` | 1 h | — | — | 4 | ❌ |
| Xact | `*.csv` | 1 h | `ALARM` | exact code | 5 | ❌ |
| VOC | `*.csv` | 1 h | — | — | 0 | ❌ |
| EPA | `*.csv` | 1 h | — | — | 1 | ❌ |
| Minion | `*.csv`, `*.xlsx` | 1 h | — | — | in-place | ❌ |
| Q-ACSM | `*.csv` | 30 min | — | — | — | — |

`Native` is the `meta['freq']` fallback; the grid actually used is detected per
file at run time and reported as `df.attrs['raw_freq']`.
