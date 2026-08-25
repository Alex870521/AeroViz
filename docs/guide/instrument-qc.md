# Instrument Formats & QC

> **One page, three questions per instrument:** what does the raw file look like,
> how is an instrument error decided, and where does that decision get recorded?
>
> This is the reference for everything **L2** does — the parsing recipe and the
> error/status semantics — for when a file won't parse, when `Status Error` fires
> on every row, or when it never fires at all. The
> [per-instrument API pages](../api/instruments/index.md) cover *usage*; the
> level model that frames all of this is in
> [Data Levels (L0–L3)](data-levels.md), whose rules **R2** and **R2a** define
> what QC may and may not do to your data.

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
| `text` | free text, possibly comma-joined (`Normal Scan`, `Low aerosol flow,Neutralizer not active`) | any token is neither `ok_value` nor whitelisted | SMPS (six columns across two AIM dialects) | string tokens, matched **per token** |
| `binary_string` | space-grouped bit string (`0000 0000 0000 0000`) | any non-whitelisted bit remains set after clearing the whitelist mask | APS | integer bit masks **cleared before testing** |

Two behaviours to know:

- **Empty means OK, always.** In `text` mode the sentinels `''`, `'nan'` and
  `'None'` are never errors. (`'None'` arrives when a column is missing from
  *some* files of a multi-file concat: pandas fills with Python `None`, which
  `astype(str)` renders as `'None'`.)
- **A missing status column reads as OK — but now says so.** `filter_error_status`
  returns all-`False` for a column it cannot find, which is deliberate (mixed
  exports must not crash) but used to make a status rule *completely inert with no
  signal*. Every status reader now calls `check_status_columns` first and logs a
  warning naming what it looked for and what the file actually contains, so a new
  export dialect surfaces instead of silently passing every fault.

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
| `QC_Flag` column | `_QC` / `_process` (L2) | per row | `"Valid"`, or comma-joined names of every rule that fired (advisory ones included) |
| `QC_Invalid` column | `_QC` / `_process` (L2) | per row | boolean verdict: did an *invalidating* rule fire? The only thing masking looks at |
| `{inst}.log` | all levels | per run | parse warnings, skipped/dropped files, mixed-resolution & stray-date warnings, **QC Summary** (count + % per rule), rates |
| `report.json` | L3 | per week / month + timeline | `rates.weekly` / `rates.monthly` (acquisition / yield / total), `timeline` of operational & down periods with reasons |
| `df.attrs` | L3 (`_stamp`) | per call | provenance, `coverage_*` vs `requested_*`, `raw_freq`, `freq_mixed`, `acquisition_rate` / `yield_rate` / `total_rate` |
| `_read_{inst}_qc.csv` | L2 | per row | the flagged frame *before* masking — the only place where flag and value coexist |

**Lifecycle of one flag:**

```
_QC       → QCRule.condition(df) → mask → QC_Flag   = "Below MDL, Status Error"
                                        → QC_Invalid = True   (Status Error is severity='error';
                                                               Below MDL alone would leave it False)
_process  → may append via update_qc_flag(..., severity=...) → "…, Invalid AAE"
log       → "  Status Error: 24312 (4.9%)" / "  Below MDL: 1201 (2.4%) [advisory]"
report    → yield counts rows that survived the verdict, so an advisory-only row counts
__call__  → QC_Invalid  →  entire row set to NaN; QC_Flag + QC_Invalid dropped
```

!!! info "Not every flag is fatal"
    Each rule carries a **severity**. `'error'` (the default) masks the row;
    `'warning'` records the flag and keeps the measurement. Advisory today:
    OCEC's `Below MDL` and Xact's `Upscale Warning` — a sub-detection-limit value
    or a vendor upscale notice is a real measurement, and masking is per row, so
    invalidating it would delete every other species at that timestamp too.

    `Insufficient` is advisory too: it describes how well an hour is *covered*,
    which decides whether an average over it is representative, not whether the
    readings are real. `Spike` remains invalidating — it asserts the value itself
    is wrong. Reclassify per run without editing a reader:

    ```python
    # tighten an advisory flag back into an invalidating one
    RawDataReader('SMPS', path, flag_severity={'Insufficient': 'error'})

    # the other direction — the closest thing to switching a check off
    RawDataReader('AE33', path, flag_severity={'Invalid AAE': 'warning'})
    ```

    Demoting to `warning` does not stop the rule running: it still fires and
    still lands in `QC_Flag`, the row just keeps its values. Nothing short of
    `qc=False` stops a rule running altogether.

    Every flag in the vocabulary below can be named, including `Invalid AAE`,
    which is raised after the main pass once the derived AAE column exists. A key
    naming no rule of the instrument being read raises `ValueError` listing that
    instrument's flags — a typo cannot silently do nothing.

    To see values behind an invalidating flag, read `_read_{inst}_qc.csv` (flag,
    verdict and value side by side) or call with `qc=False` (returns L1 — no QC,
    and no resampling either).

### QC_Flag vocabulary

Severity is `error` unless marked **advisory**.

| Flag | Meaning | Used by |
|------|---------|---------|
| `Valid` | passed every rule | all |
| `Status Error` | instrument status register reports a non-whitelisted condition | AE33, AE43, BC1054, MA350, SMPS, APS, Aurora, NEPH, TEOM |

!!! tip "Which condition, not just *a* condition"

    `Status Error` is a boolean verdict — it cannot say which bit tripped it.
    A reader that declares `STATUS_BITS` (`{decimal_bit: condition_name}`) gets
    the register decoded into `df.attrs['status_conditions']`, so a TEOM status
    of `8` is reported as *Ambient RH & Temp sensor* rather than left as a
    number. **TEOM is the only table transcribed so far**; the other bitwise
    readers list their codes in prose in `ERROR_STATES` and need a pass against
    the instrument manual before being encoded — a partly-filled map is worse
    than an empty one, because a missing entry silently reads as "that
    condition never fired".
| `Insufficient` | an hour holds < 50 % of the points it could have held, given how much of that hour the read covers — **advisory** | AE33, AE43, BC1054, MA350, SMPS, APS, Aurora, NEPH, TEOM, GRIMM |
| `Invalid BC` | any BC channel ≤ 0 or > 20 000 ng/m³ | AE33, AE43, BC1054, MA350 |
| `Invalid AAE` | AAE outside 0.7–3.0 (added in `_process`) | AE33, AE43, BC1054, MA350 |
| `Invalid Number Conc` | total number concentration outside range (SMPS 2 000–1e7, APS 1–700 #/cm³) | SMPS, APS |
| `DMA Water Ingress` | any bin > 400 nm exceeds 4 000 dN/dlogDp | SMPS |
| `Invalid Scat Value` | any scattering channel ≤ 0 or > 2 000 Mm⁻¹ | Aurora, NEPH |
| `Invalid Scat Rel` | B < G < R — inverted wavelength dependence | Aurora, NEPH |
| `No Data` | every measurement channel NaN | Aurora, NEPH, GRIMM |
| `High Noise` | TEOM `noise` ≥ 0.01 | TEOM |
| `Non-positive` | `PM_NV` ≤ 0 or `PM_Total` ≤ 0 | TEOM |
| `NV > Total` | `PM_NV` > `PM_Total` (physically impossible) | TEOM |
| `Spike` | change > 3 × median absolute change, or a large up-down reversal | TEOM, BAM1020, OCEC |
| `Negative Conc` | any size channel is negative | GRIMM |
| `Invalid Conc` | PM ≤ 0 or > 500 µg/m³ | BAM1020 |
| `Invalid Carbon` | any carbon fraction ≤ −5 or > 100 µgC/m³ | OCEC |
| `Below MDL` | value at or below the method detection limit — **advisory** | OCEC |
| `Missing OC` | `Thermal_OC` or `Optical_OC` missing | OCEC |
| `Above MR` | concentration above the instrument's stated measurement range | IGAC |
| `Mass Closure` | Σ ions > PM2.5 | IGAC |
| `Missing Main` | any of NH₄⁺ / SO₄²⁻ / NO₃⁻ missing | IGAC |
| `Ion Balance` | cation/anion ratio outside 1.5 × IQR | IGAC |
| `Calibration Mode` | `SAMPLE_TYPE != 1` | Xact |
| `Instrument Error` | `ALARM` in 100–110 | Xact |
| `Upscale Warning` | `ALARM` in 200–203 — **advisory** (the instrument's own warning class) | Xact |
| `Invalid Value` | element concentration outside 0–100 000 ng/m³ | Xact |
| `Internal Std Drift` | Nb outside ±20 % of its median | Xact |
| `High Uncertainty` | a normally-quantitative element reported above its detection limit with < 3σ confidence — **advisory** | Xact |
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
| **L2 output** | `BC1`–`BC7`, `abs_370`…`abs_950`, `abs_550`, `AAE`, `eBC`, `Delta-C` (= BC1 − BC6), `K1`–`K7` and `BB(%)` when present, `QC_Flag` |

### AE43

Identical to AE33 except:

- **Pattern** `[!ST|!CT|!FV]*[!log]_AE43*.dat`; parsed with
  `read_csv(parse_dates=['StartTime'], index_col='StartTime')`.
- Keeps only the rows of the **last `SetupID`** in the file (a setup change
  mid-file discards the earlier segment).
- `ERROR_STATES` is now **identical to AE33's** — it used to keep `384`, which
  AE33 had dropped as a tape-*low* warning. A test pins the two lists equal.

### BC1054

| | |
|---|---|
| **Pattern** | `*.csv`, native `1min` |
| **Parse** | header row located by scanning the first 20 lines for one starting with `Time` or `Raw_Time` (variants seen: header on line 1; `Raw_Time,Time,…`; a `Data Report` / `User Report` block plus 3 metadata lines; leading blank lines). Then `read_csv(parse_dates=True, index_col=0, skiprows=skip)`; spaces stripped from column names; `BC1 (ng/m3)`→`BC1` … `BC10`, `Flow(lpm)`→`Flow`, `WS`, `WD`, `AT`, `RH`, `BP` |
| **Two clocks** | a file may carry both. `Time` is Met One's own field — *"the date and timestamp for the data record. The timestamp is end of the minute"* — written from the instrument's internal RTC, which an operator sets by hand (manual §3.5.7 SET CLOCK) and which can therefore be wrong. `Raw_Time` appears **nowhere in the manual**, so it comes from whatever logged or downloaded the file, on that host's clock. |
| **Which is the index** | `Raw_Time`: the measurement happened at the wall-clock instant whatever the instrument believed, and in the corpus it is the well-behaved column — strictly increasing, no duplicates. The instrument clock is not: one fixture repeats timestamps and jumps 14 h 42 m mid-file, another sits a constant **12 h 04 m** behind for all 1440 rows of a day (an RTC set to the wrong AM/PM, plus drift). The instrument's timestamp is kept as `Instrument_Time`, and a median disagreement over 60 s is **warned** — dropping it silently, as this reader used to, also discarded the only evidence that a clock needed resetting. |
| **Quirks** | `_QC` first removes rows identical to their previous *or* next row (consecutive-duplicate filter) before flagging. |
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
| **Status** | **six** columns, mode `text`, masks OR'd — whichever are present. The same information is reported under **different names per host-software version**:<br><br>`Status Flag` (10.3) ↔ `Detector Status` (11.x) — positive sentinel, OK when `'Normal Scan'`<br>`Instrument Errors` (10.3) ↔ `Classifier Errors` (11.x) — error tokens, OK when empty<br>`Communication Status` (11.x only) — OK when `'0'`<br>`Neutralizer Status` (11.x only) — OK when `'ON'`<br><br>Two value shapes: a *positive sentinel* column (OK when it equals a known-good string) and an *error-token* column (OK when empty, otherwise comma-separated fault names). `'Normal Scan'` is auto-whitelisted on the token columns too, because some sites write the positive sentinel there instead of leaving it blank. |
| **QC rules** | `Status Error`, `Insufficient`, `Invalid Number Conc` (2 000–1e7 #/cm³, NaN total ⇒ flagged), `DMA Water Ingress` (any bin ≥ 400 nm > 4 000 dN/dlogDp) |
| **L2 output** | **the dN/dlogDp matrix only** (diameters in nm as columns) + `QC_Flag`. Statistics are *not* in the frame. |
| **CPC** | the file names the counter that did the counting (`Detector Model`, `Detector S/N`, `Nano Enhancer`), reported in `df.attrs` as `cpc_*`. Its cut-off decides how far the lowest channels under-report — see [Counting Efficiency](counting-efficiency.md). Not corrected for. |
| **L3 sidecars** | `{prefix}_dNdlogDp.csv`, `_dSdlogDp.csv` (`πd²·dN`), `_dVdlogDp.csv` (`πd³/6·dN`), `_stats.csv` (from `psd_stats`). Pass `append_stats=True` to also append the statistics columns to the returned frame. |
| **Was a gap** | an AIM 11.x export has **neither** AIM 10.3 name, so until all six were listed its `Status Error` rule could never fire — every scan passed the status check regardless of what the instrument reported. Verified on the CSV fixture: `Detector Status='Normal Scan'`, `Classifier Errors='Low aerosol flow'`, `Communication Status='0'`, `Neutralizer Status='ON'` on all 62 scans, so the flag now fires (and `ignored_status_errors=['Low aerosol flow']` clears it, as on the 10.3 dialect). |

### APS

| | |
|---|---|
| **Pattern** | `*.txt`; native `6min` |
| **Parse** | tab-separated; ~6 metadata lines (`Sample File`, `Sample Time`, `Density`, `Stokes Correction`, `Lower/Upper Channel Bound`) then a `Sample #` header row. Transposed exports are rotated (`set_index('Sample #').T`), and a failure there raises `NotImplementedError` **with the original exception attached**. Date from `Date` + `Start Time`, formats `%m/%d/%y %H:%M:%S` then `%m/%d/%Y %H:%M:%S`; the winning format is logged. |
| **Sampling period** | the file header carries `Sample Time` (115 s in the corpus) — **not** a whole number of minutes, and not the `6min` in the config. The native grid follows the detected period, so scans are not lost to bin collisions; `df.attrs['raw_freq']` reports what was actually used. |
| **Size bins** | numeric column names in 0.5–20 (µm) → float, rounded to 4 dp. Expected grid `(0.542, 19.81, 51 bins)`; deviation **warns loudly** (an 8-year × 4-station audit of 1 485 files showed zero drift, so a deviation means a firmware change — and would reproduce the NaN-poisoned-concat problem SMPS had). The under-range `<0.523` column is kept as metadata, not a bin. |
| **Status** | column `Status Flags`, mode `binary_string`; OK is `'0000 0000 0000 0000'` |
| **Bit meanings** | 0 laser fault · 1 total flow out of range · 2 sheath flow out of range · 3 excessive sample concentration · 4 accumulator clipped (> 65535) · 5 autocal failed · 6 internal temp < 10 °C · 7 internal temp > 40 °C · 8 detector voltage out of range · 9 reserved |
| **QC rules** | `Status Error`, `Insufficient`, `Invalid Number Conc` (1–700 #/cm³) |
| **L2 output / sidecars** | as SMPS, diameters in **µm** |
| **Counting efficiency** | the APS under-counts at both ends — 85–99 % for solid particles, but falling from 75 % at 0.8 µm to 25 % at 10 µm for droplets (Volckens & Peters 2005). Not corrected for; see [Counting Efficiency](counting-efficiency.md). |

### GRIMM

| | |
|---|---|
| **Pattern** | `*.dat`; native `6min` |
| **Parse** | `read_csv(header=233, delimiter='\t', index_col=0, parse_dates=[0], encoding='ISO-8859-1', dayfirst=True)` — the header row is a **hard-coded line number**; then columns 0–10 and the trailing 5 (or from column 128 for files named `A407ST*`) are dropped, and all values are divided by `0.035`. Empty files are reported with `print` (not the logger) and skipped. |
| **Status** | none |
| **QC rules** | `No Data` (all channels NaN), `Negative Conc` (any channel < 0 — impossible for a counter), `Insufficient` |
| **Deliberately absent** | concentration *range* limits, the equivalent of SMPS's `MIN_TOTAL_CONC` / APS's `MAX_TOTAL_CONC`. There is no GRIMM sample corpus to calibrate a plausible range against, and a wrong threshold silently deletes good data. The three rules above need no site-specific tuning. |
| **Note** | like every reader, the completeness rule measures against the **detected** frequency (`_resolved_freq`), falling back to the config value only when detection fails. |

---

## 5. Nephelometers, mass, chemistry, external sources

### Aurora

| | |
|---|---|
| **Pattern** | `*.csv`; native `1min` |
| **Parse** | `read_csv(low_memory=False, index_col=0)`; index coerced to datetime; column aliases `0°σspB/G/R`→`B/G/R`, `90°σspB/G/R`→`BB/BG/BR`, and `Blue/Green/Red`→`B/G/R`, `B_Blue/B_Green/B_Red`→`BB/BG/BR`; `Raw_Data_Time` dropped |
| **Status** | first match among `Status`, `status`, `Error`, `error`, `Flag`, `flag`, **`S1`** is renamed to `Status`; mode `numeric`, `ok_value=0` |
| **QC rules** | `Status Error`, `No Data`, `Invalid Scat Value` (0–2 000 Mm⁻¹), `Invalid Scat Rel` (`B < G & G < R`), `Insufficient` |
| **L2 output** | `sca_550`, `SAE` (positive by convention), plus all non-scattering columns (T1, T2, RH, P, S1, S2, …), `QC_Flag` |
| **`S1` is the status** | the production CSV (`Data_Time, Raw_Data_Time, Red, Green, Blue, B_Red, B_Green, B_Blue, T1, T2, RH, P, S1, S2`) contains none of the *obvious* status names — the status is `S1`, and it is now recognised. Evidence from 120 one-minute scans: `S1 ∈ {0, 4}`; the 17 rows with `S1 == 4` are **contiguous** (00:06–00:22) and their scattering decays 185 → 0.78 Mm⁻¹ while `S1 == 0` rows average 193 Mm⁻¹ — the signature of the **zero/span check**, where the instrument samples filtered air. Those rows pass the 0–2000 range check happily, so before this fix they were averaged into ambient means: on that fixture, dropping them raises the green-channel mean from 170.8 to 193.2 Mm⁻¹, i.e. a **13% low bias** removed. |
| **`S2`** | moves in step (`0x07` while ambient, `0xAB`/`0xA8` during the check) and is evidently a bitfield. Its individual bits are **not** decoded — no manual to hand, and guessing bit meanings would be worse than leaving it as data. |

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
| **Parse** | `read_csv(skiprows=3, index_col=False)`; **both** alias maps are applied to every file because real exports mix conventions. `remote`/GUI names (`Time Stamp`→`time`, `System status`→`status`, `PM-2.5 base MC`→`PM_NV`, `PM-2.5 MC`→`PM_Total`, `PM-2.5 TEOM noise`→`noise`, …) and `usb`/SNMP names (`tmoStatusCondition_0`→`status`, `tmoTEOMABaseMC_0`→`PM_NV`, `tmoTEOMAMC_0`→`PM_Total`, `tmoTEOMANoise_0`→`noise`, …) land on the same canonical short names. Format is then detected post-rename and logged: `time` present ⇒ remote (timestamps like `07 - 六月 - 2025 12:00:00` or `10 - Aug - 2026 00:00:01` — the host writes the month in the OS language, so Chinese *and* English names are mapped to a number before `format='%d - %m - %Y %H:%M:%S'`; `%b`/`%X` are avoided because they follow the *reading* machine's locale); `Date`+`Time` ⇒ usb. Neither ⇒ a file-named `NotImplementedError`. A file whose timestamps all fail to parse is logged by name at ERROR before it is dropped as empty. |
| **Status** | column `status`, mode **`bitwise`** — this is the subtle one: the TEOM `status condition` register is a **32-bit bitfield** (TEOM 1405 / 1405-F manual, Appendix A, Table A-1), so the instrument reports the *decimal sum* of every active warning. Treating it as a flat code (`status != 0`) makes any co-set bit unmaskable; bitwise mode lets one condition be whitelisted regardless of what else is set. `ERROR_STATES = [1 << b for b in range(32)]` — every bit counts as an error by default. |
| **Documented bits** | 29 named conditions across bits 0–30 (15/23/31 unassigned). Full table — bit, decimal and condition — in [the TEOM reference](../api/instruments/mass/TEOM.md#status-condition-register); it is generated from `Reader.STATUS_BITS` and a test pins the two together. |
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
| **MDL / MR** | from `meta['IGAC']` — the [vendor specification](https://www.yangyao-env.com/web/product/product_in2.jsp?pd_id=PD1640151884502), 17 species covering **gases and aerosol ions**, exposed as `reader.MDL` / `reader.MR`. Species whose spec entry is `None` (HF, F⁻, PO₄³⁻ — not measured) are skipped everywhere. This replaced a second, disagreeing class-level copy of the 9 aerosol ions. |
| **QC rules** | `Mass Closure` (Σ *aerosol ions* > `PM2.5` when that column exists — gases are not part of the PM budget), `Missing Main` (NH₄⁺/SO₄²⁻/NO₃⁻), `Above MR` (any species above its stated measurement range), `Ion Balance` (cation/anion ratio outside 1.5 × IQR) |
| **Below MDL** | a **per-species diagnostic**, not a flag: the log reports what fraction of each species sits below its limit, worst-first. (OCEC keeps a `Below MDL` flag, but at `severity='warning'` — same outcome by a different route. IGAC has 17 species, so a per-column count is more useful than one row-level flag.) |
| **L2 output** | every spec species present in the file (gases included — they used to be dropped) + `QC_Flag` |

### Xact

| | |
|---|---|
| **Pattern** | `*.csv`; native `1h` |
| **Parse** | **two** header rows: line 0 is element names in caps (`MAGNESIUM,,ALUMINIUM,,…`), line 1 is the real header; the data rows carry one extra trailing field, absorbed as `_extra_` and dropped. `TIME` parsed as `%m/%d/%Y %H:%M:%S`. Rows with `Sample Type != 1` are dropped **before** rounding to `1h` (the daily 00:00–00:30 QA check would otherwise displace a valid 00:30 sample). Element columns are matched by pattern (`Mg 12 (ng/m3)`→`Mg`, `Al Uncert (ng/m3)`→`Al_uncert`); environment columns are renamed to short forms (`AT (C)`→`AT`, `FLOW 25 (slpm)`→`FLOW_25`, …); `PUMP START TIME`, `Output Pin 7`, `XC VER` dropped. |
| **Status** | column `ALARM`, matched by **exact code**, not bitwise; `0` = normal. `decode_alarm()` turns a code into text. |
| **Alarm codes** | errors 100 X-ray voltage · 101 X-ray current · 102 tube temperature · 103 enclosure temperature · 104 tape · 105 pump · 106 filter wheel · 107 dynamic rod · 108 nozzle · 109 energy calibration · 110 software. Warnings 200 upscale Cr · 201 upscale Pb · 202 upscale Cd · 203 upscale Nb. |
| **QC rules** | `Calibration Mode`, `Instrument Error` (100–110), `Upscale Warning` (200–203), `Invalid Value` (0–100 000 ng/m³), `Internal Std Drift` (Nb ±20 % of median). Each is registered only if its source column exists. |
| **MDL** | the **manual's own table** (Operation Manual Appendix p.73, `Xact.MANUAL_MDL`) for the 29 elements it covers, selected by the file's `SAMPLE_TIME` — the limits vary ~8× between a 15-min and a 240-min sample, so one fixed number is right for only one configuration. `meta['Xact']['MDL']` supplies the other 16, for which CES publishes nothing. Exposed as `reader.MDL` / `reader.manual_mdl(minutes)`. |
| **Uncertainty** | every element has a paired `{element}_uncert` column. The manual's limits are *"interference free **one sigma** detection limits … at 68 % Confidence Level (C1σ) per US EPA IO 3.3 and Currie, 1968"*, and that uncertainty column is the same 1σ quantity — which is what lets Currie's criteria apply to it directly: **detected** at `value ≥ 3σ`, **quantifiable** at `value ≥ 10σ`. |
| **Element reliability** | `element_reliability(df)` classifies each element from the fraction of samples meeting those criteria — `quantitative` / `semi-quantitative` / `below-detection` — and reports *separately* whether the manual publishes a limit for it at all (the two are independent: Nb, the internal standard, is measured superbly and has no published limit). Written to `{prefix}_element_reliability.csv` and summarised in the log. On the test corpus: 11 quantitative (S, K, Ca, Cl, Fe, Cu, Zn, Br, Mn, Pb, As), 7 semi-quantitative (Ti, Cr, Ni, Se, Ba, Bi, Sr), the rest below detection. |
| **Below MDL** | a **diagnostic, not a flag** (same reasoning as IGAC, and more acute here): in the test fixture alone a dozen elements sit 100 % below their limit, so an "any element below MDL" rule would flag — and therefore NaN — every single row. The log reports the per-element fraction instead. |
| **Why `High Uncertainty` is scoped** | the same trap. A rule firing when *any* element fails the 3σ test hits **96–100 % of rows** on both fixtures, because a dozen elements are permanently below detection at any real site — a property of the element, not of the row. Scoped to elements this run measures well *and* the manual specifies, it fires on 0 % of clean rows and 8 % of the degraded fixture, where it caught S, K, Ca, Fe, Zn and Br degrading together: an instrument event rather than element noise. |
| **L2 output** | all columns + `QC_Flag` |

### EPA — external, pre-aggregated

`*.csv`, native `1h`, `encoding='big5'`. Accepts the Taiwan EPA hourly exports
(測項 / 直式). Raises if more than one 測站 is present; drops 測站; pivots
`測項`/`資料` into columns when present; renames `AMB_TEMP`→`AT`,
`WIND_SPEED`→`WS`, `WIND_DIREC`→`WD`. Invalid-value markers are normalised by
regex (`…#`→`#`, `…L`→`_`) and then coerced to NaN. Columns reordered to
`SO2, NO, NOx, NO2, CO, O3, THC, NMHC, CH4, PM10, PM2.5, PM1, WS, WD, AT, RH`.
No status; one QC rule: `Negative`.

### Removed: VOC and Minion

Both were **pre-aggregated, second-hand data** — somebody else's processed
output, not an instrument's raw log — so there was no raw format for a reader to
parse and the readers only ran generic checks. They were withdrawn from
`RawDataReader`; `RawDataReader('VOC', …)` / `('Minion', …)` now raises a
`KeyError` carrying migration advice.

Read them yourself and go straight to the analysis functions:

```python
import pandas as pd
from AeroViz import voc_potentials

df = pd.read_csv('voc.csv', index_col=0, parse_dates=True,
                 na_values=('-', 'N.D.'))
df.columns = df.columns.str.strip()
out = voc_potentials(df)      # validates species against support_voc.json
```

Minion arrives as a monthly report spreadsheet (`read_excel`), with a units row
at the top and site-specific invalid markers (`維護校正`, `Nodata`, `0L`); the
handling depends on who produced that particular report, which is exactly why it
does not belong behind a general-purpose reader.

### Q-ACSM — reader not implemented yet

A **real instrument**, but no reader exists: no sample export has been available
to write and test a parser against. It stays in `meta` (the 30-min native
frequency is known) and is registered in `supported_instruments.pending`, so
`RawDataReader('Q-ACSM', …)` raises a plain

```
NotImplementedError: Q-ACSM is a real instrument, but its reader is not
implemented yet — no sample export has been available to write and test a parser
against. Contribute one by adding AeroViz/rawDataReader/script/Q-ACSM.py with
_raw_reader and _QC ...
```

rather than the abstract-class `TypeError` it used to. Removing the `pending`
entry is all that is needed once a reader lands.

---

## 6. Coverage gaps

Where the status/QC machinery was, or still is, doing less than it appears to:

| Instrument | Symptom | Status |
|---|---|---|
| **Aurora** | `Status Error` never fired — no obvious status column | **fixed**: `S1` recognised; the zero/span-check rows it marks were biasing ambient means 13% low |
| **SMPS** (AIM 11.x CSV) | `Status Error` never fired — 10.3 names absent | **fixed**: all six column names across both AIM dialects are checked |
| **Any reader whose status column gets renamed** | degraded silently to "no errors ever" | **fixed**: `check_status_columns` warns, naming what it looked for and what the file has |
| **MA350** | `Status` column presence never verified against a real export | **open** — no fixture. The warning above will now say so at runtime instead of passing everything |
| **GRIMM** | no concentration range check | **open by choice**: no sample corpus to calibrate one against, and a guessed threshold silently deletes good data |
| **Any reader using `Insufficient`** | partial first/last hours look sparse merely because the data starts mid-hour | **open** — see P2-i in [Data Levels §7](data-levels.md#7-non-conformance-what-still-needs-fixing) |

Full remediation list, with priorities and suggested order:
[Data Levels §7](data-levels.md#7-non-conformance-what-still-needs-fixing).

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
| GRIMM | `*.dat` | 6 min | — | — | 3 | ❌ |
| TEOM | `*.csv` | 6 min | `status` | bitwise (32-bit) | 6 | ✅ |
| BAM1020 | `*.csv` | 1 h | — | — | 2 | ❌ |
| OCEC | `*LCRes.csv` | 1 h | — | — | 4 | ❌ |
| IGAC | `*.csv` | 1 h | — | — | 4 | ❌ |
| Xact | `*.csv` | 1 h | `ALARM` | exact code | 5 | ❌ |
| EPA | `*.csv` | 1 h | — | — | 1 | ❌ |
| Q-ACSM | `*.csv` | 30 min | — | — | *reader pending* | — |

`Native` is the `meta['freq']` fallback; the grid actually used is detected per
file at run time and reported as `df.attrs['raw_freq']`.

**Three registry categories** (`config/supported_instruments.py`):

- **supported** — every row above except Q-ACSM: a module in `script/` plus a
  `meta` entry.
- **pending** — `Q-ACSM`: a real instrument, reader not written yet →
  `NotImplementedError`.
- **removed** — `VOC`, `Minion`: pre-aggregated second-hand data, no raw log to
  parse → `KeyError` with migration advice, see
  [above](#removed-voc-and-minion).
