# RawDataReader Reference

> **What this page is.** The single reference for how `RawDataReader` works
> under the hood: the pipeline stages and the files they write, the QC
> machinery, how an instrument's status register is judged, the full `QC_Flag`
> vocabulary, and one table per instrument giving its raw format, status
> semantics and QC rules.
>
> You do not need it to *use* the reader — start with
> [RawDataReader Usage](rawdatareader.md) — and the level model that frames
> everything here is [Data Levels (L0–L3)](data-levels.md). Come here when a
> file will not parse, when `Status Error` fires on every row (or never fires),
> when you want to know exactly what a flag means, or when you are adding a
> reader or a rule.

---

## 1. Pipeline at a glance

```
RawDataReader(inst, path, start=…, end=…, mean_freq=…, qc=True)
        │
        ▼
 ┌─ L1  _raw_reader ───────────────────────────────────────────────────┐
 │  one parser per instrument, per file · every source column kept     │
 │  native frequency detected per file · scan groups partitioned       │
 │  stray dates flagged · rows snapped to the native grid              │
 └─────────────────────────────────────────────────────────────────────┘
        │  _read_{inst}_raw.pkl / .csv                    ← cache
        ▼
 ┌─ L2  _QC  →  _process ──────────────────────────────────────────────┐
 │  QCFlagBuilder evaluates every QCRule → QC_Flag  ("Valid" | names)  │
 │                                       → QC_Invalid (verdict)        │
 │  _process derives abs / AAE / eBC / sca_550 / SAE /                 │
 │  Volatile_Fraction, and may add late rules (Invalid AAE)            │
 └─────────────────────────────────────────────────────────────────────┘
        │  _read_{inst}_qc.pkl / .csv                     ← cache
        ▼  ─────────────────── cache boundary ───────────────────
 ┌─ L3  __call__ ──────────────────────────────────────────────────────┐
 │  place on the requested range (fill_missing) · apply outlier.json   │
 │  QC_Invalid rows → NaN · drop QC_Flag + QC_Invalid                  │
 │  _generate_report (rates, timeline) · resample(mean_freq) · _stamp  │
 └─────────────────────────────────────────────────────────────────────┘
        │  output_{inst}.csv · report.json · SMPS/APS sidecars · {inst}.log
        ▼
   returned DataFrame (+ df.attrs)
```

Everything above the cache boundary is skipped on a cache hit; everything below
it runs on every call, which is why a cached read still honours the current
`start` / `end` / `fill_missing` / `mean_freq`. The step-by-step version, with
the invariants each step must respect, is in
[Data Levels §3](data-levels.md#3-execution-flow).

### Files written

```
{inst}_outputs/                       # next to the raw files; output_dir= overrides
                                      # folder and file stems are lower-case (ae33_outputs/output_ae33.csv);
                                      # only the log keeps the reader's case (AE33.log)
├── _read_{inst}_raw.pkl / .csv       # L1 — parsed, all columns, native grid
├── _read_{inst}_qc.pkl  / .csv       # L2 — + QC_Flag, QC_Invalid (flag and value side by side)
├── output_{inst}.csv                 # L3 — what the call returns
├── output_{inst}_dNdlogDp.csv        # SMPS / APS only: the three weightings
├── output_{inst}_dSdlogDp.csv
├── output_{inst}_dVdlogDp.csv
├── output_{inst}_stats.csv           # SMPS / APS only: psd_stats output, QC-aligned
├── output_{inst}_element_reliability.csv   # Xact only: per-element quantitative / semi / below-detection
├── report.json                       # rates per period + up/down timeline
└── {inst}.log                        # parse warnings, dropped files, QC summary
```

`output_prefix=` renames the `output_{inst}` stem; `save_pkl`,
`save_intermediate_csv`, `save_report` switch the respective files off.

### What a column goes through

| Stage | AE33 example | APS example |
|---|---|---|
| `_raw_reader` (L1) | BC1–BC7, ATN, Flow, Status, … | size bins (0.5–20 µm) + metadata |
| `_QC` (L2) | + `QC_Flag`, `QC_Invalid` | + `QC_Flag`, `QC_Invalid` |
| `_process` (L2) | + abs_370…abs_950, abs_550, AAE, eBC | keeps the size bins only |
| `__call__` (L3) | invalid rows → NaN; both QC columns dropped | same |
| returned | BC, abs, AAE, eBC, metadata | dN/dlogDp matrix (statistics in `_stats.csv`, or appended with `append_stats=True`) |

`_raw_reader` deliberately keeps *all* source columns so instrument metadata
(flow, temperature, RH, pressure, status) survives to L2; the readers that
narrow the frame do so in `_process`, never at L1.

---

## 2. QC machinery

### Rules and the builder

Every reader declares its checks as `QCRule`s and hands them to a
`QCFlagBuilder` (`core/qc.py`):

```
QCRule                          QCFlagBuilder
  name         "Invalid BC"       rules[]
  condition    df -> bool mask    add_rule() / add_rules()
  description  "0–20 000 ng/m³"   apply(df)   -> QC_Flag, QC_Invalid
  severity     'error'|'warning'  get_summary()
```

`apply` evaluates every rule as a vectorised mask, writes `QC_Flag = "Valid"` or
the comma-joined names of every rule that fired, and sets `QC_Invalid = True`
where at least one **error**-severity rule fired. A rule that raises is caught,
warned about, and treated as all-False. Nothing is NaN'd or dropped here —
masking is L3's job, on the verdict alone (Data Levels
[R2](data-levels.md#2-the-rules-invariants)).

`_process` may add further rules after derived columns exist (`Invalid AAE`
needs `AAE`), via `update_qc_flag`, which appends to an existing non-`Valid`
flag and raises the verdict if the new rule is invalidating.

The generic filters the rules are built from — `n_sigma`, `iqr`,
`time_aware_rolling_iqr`, `time_aware_std_QC`, `bidirectional_trend_std_QC`,
`spike_detection`, `hourly_completeness_QC`, `filter_error_status` — are
documented in the [QualityControl API](../api/QualityControl.md).

### Severity — not every flag is fatal

| Severity | Effect at L3 | Ships as |
|---|---|---|
| `error` (default) | row masked to NaN | every rule not listed below |
| `warning` (advisory) | flag recorded, measurement kept | `Insufficient` (every reader that has it), OCEC `Below MDL`, Xact `Upscale Warning`, Xact `High Uncertainty` |

The test is what the flag is *about*. `Insufficient` says an hour is thinly
covered — a statement about whether an **average** over that hour is
representative, not about whether the readings are real. A value below a
detection limit, or a vendor notice the instrument itself classes as a warning,
is a real measurement, and because masking is per row, invalidating it would
delete every other species at that timestamp too.

Reclassify per run without editing a reader:

```python
# tighten an advisory flag back into an invalidating one
RawDataReader('SMPS', path, flag_severity={'Insufficient': 'error'})

# demote one — the closest thing to switching a check off
RawDataReader('AE33', path, flag_severity={'Invalid AAE': 'warning'})
```

Demoting does not stop the rule running: it still fires and still lands in
`QC_Flag`; the row just keeps its values. Nor does `qc=False`: on a fresh parse
`_QC` and `_process` run regardless and the L2 cache is written either way —
`qc=False` only changes what is *returned*, the parsed L1 frame with no masking,
no `outlier.json` and no report (`mean_freq` is still honoured).
A key naming no rule of the instrument being read raises `ValueError` listing
that instrument's flags, so a typo cannot silently do nothing.

### Lifecycle of one flag

```
_QC        QCRule.condition(df) → mask → QC_Flag    = "Below MDL, Status Error"
                                       → QC_Invalid = True   (Status Error is 'error';
                                                              Below MDL alone leaves it False)
_process   update_qc_flag(..., severity=...)        → "…, Invalid AAE"
log        "  Status Error: 24312 (4.9%)"  /  "  Below MDL: 1201 (2.4%) [advisory]"
report     yield counts rows that survived the verdict, so an advisory-only row counts
__call__   QC_Invalid → whole row NaN ; QC_Flag + QC_Invalid dropped
```

### The QC summary

```
AE33 QC Summary:
  Status Error: 24312 (4.9%)
  Invalid BC: 29265 (5.9%)
  Insufficient: 105481 (21.1%) [advisory]
  Invalid AAE: 25948 (5.2%)
  Valid: 356025 (71.2%)
  Usable: 461506 (92.3%)
```

`Valid` = passed every rule. `Usable` = no *invalidating* rule fired, i.e. what
survives into the output. They differ by exactly the rows carrying only advisory
flags. Rule counts overlap by design — a row can trip several.

Readers with a `_process` that reshapes the frame (AE33, AE43, BC1054, MA350,
SMPS, APS, Aurora, NEPH) store the summary in `_QC` and log it from `_process`
— the four aethalometers after adding `Invalid AAE`; TEOM, GRIMM, BAM1020,
OCEC, IGAC, Xact and EPA log it inside `_QC`. The same rows are also stamped into
`df.attrs['qc_rules']` as `{rule, count, percentage, severity, description}`,
so a consumer can explain an outage, not just measure it.

### Where a judgement is recorded

| Channel | Written by | Granularity | Content |
|---|---|---|---|
| `QC_Flag` column | `_QC` / `_process` (L2) | per row | `"Valid"`, or every rule that fired, advisory ones included |
| `QC_Invalid` column | `_QC` / `_process` (L2) | per row | boolean verdict — the only thing masking looks at |
| `_read_{inst}_qc.csv` | `_save_data` (L2) | per row | the flagged frame *before* masking — flag, verdict and value side by side |
| `{inst}.log` | all levels | per run | parse warnings, skipped/dropped files, mixed-resolution and stray-date warnings, QC summary, rates |
| `report.json` | `_generate_report` (L3) | per week / month + timeline | `rates.weekly` / `rates.monthly` (acquisition / yield / total), `timeline` of operational and down periods with reasons |
| `df.attrs` | `_stamp` (L3) | per call | provenance, `coverage_*` vs `requested_*`, `raw_freq`, rates, `qc_rules`, `status_conditions` |

Both QC columns are dropped from the returned frame and from
`output_{inst}.csv`. To see the values behind a flag, open
`_read_{inst}_qc.csv` or call with `qc=False`.

### Rates

All three are computed from the verdict on a 1 h resample; a period counts as
valid when more than 50 % of its points pass the verdict (rows carrying only
advisory flags count as passing).

| Rate | Definition |
|---|---|
| Acquisition | periods with data / expected periods |
| Yield | periods passing QC / periods with data |
| Total | periods passing QC / expected periods |

`report.json` always carries a weekly (`W-MON`) and a monthly (`MS`) breakdown;
a `qc` period string (`'W'`, `'2MS'`, …) adds a per-period breakdown to the
**log**; the overall rates land in
`df.attrs['acquisition_rate' / 'yield_rate' / 'total_rate']`.
`process_timeline_report` adds up/down periods and matches them against a
`known_issues.yml` named by the `KNOWN_ISSUES_PATH` environment variable.

---

## 3. How a status judgement is made

Every status check goes through one function —
`QualityControl.filter_error_status` — in one of **four modes**. The mode
decides how the raw value is interpreted *and* how the `ignored_status_errors`
whitelist is applied.

| Mode | Raw value looks like | Error when | Instruments | `ignored_status_errors` entries are… |
|---|---|---|---|---|
| `bitwise` | integer, OR-summed bits (`0`, `4`, `536870912`) | any non-whitelisted code in `ERROR_STATES` matches bitwise, or the value equals a `special_codes` entry | AE33, AE43, BC1054, MA350, **TEOM** | integer codes / bits **removed from the error definition** |
| `numeric` | flat integer code (`0`, `4`, `16`) | `status != ok_value` and not NaN | Aurora, NEPH | numeric codes **treated as OK** |
| `text` | free text, possibly comma-joined (`Normal Scan`, `Low aerosol flow,Neutralizer not active`) | any token is neither `ok_value` nor whitelisted | SMPS (six columns across two AIM dialects) | string tokens, matched **per token** |
| `binary_string` | space-grouped bit string (`0000 0000 0000 0000`) | any non-whitelisted bit remains set after clearing the whitelist mask | APS | integer bit masks **cleared before testing** |

Xact is the exception: its `ALARM` column is matched by **exact code** (errors
100–110, warnings 200–203), not through `filter_error_status`.

Two behaviours to know:

- **Empty means OK, always.** In `text` mode the sentinels `''`, `'nan'` and
  `'None'` are never errors. (`'None'` arrives when a column is missing from
  *some* files of a multi-file concat: pandas fills with `None`, which
  `astype(str)` renders as `'None'`.)
- **A missing status column reads as OK — but says so.** `filter_error_status`
  returns all-`False` for a column it cannot find, which is deliberate (mixed
  exports must not crash) but used to make a status rule *completely inert with
  no signal*. Every status reader now calls `check_status_columns` first and
  logs a warning naming what it looked for and what the file actually contains,
  so a new export dialect surfaces instead of silently passing every fault.

Entries that don't fit a reader's mode are skipped, so one whitelist can be
passed to any reader safely:

```python
RawDataReader('TEOM',   path, ignored_status_errors=[536870912])          # bitwise: ignore "Dryer A"
RawDataReader('SMPS',   path, ignored_status_errors=['Low aerosol flow']) # text: per token
RawDataReader('APS',    path, ignored_status_errors=[1, 2])               # binary_string: clear bits 0,1
RawDataReader('Aurora', path, ignored_status_errors=[4, 16])              # numeric: extra OK codes
```

### Which condition, not just *a* condition

`Status Error` is a boolean verdict — it cannot say which bit tripped it. A
reader that declares `STATUS_BITS` (`{decimal: condition_name}`) gets the
register decoded into `df.attrs['status_conditions']` as
`{code, name, count, percentage}` per condition that actually fired, busiest
first, so a TEOM status of `8` is reported as *Ambient RH & Temp sensor* rather
than left as a number.

| Reader | Column | Encoding | Named conditions |
|---|---|---|---|
| AE33 / AE43 | `Status` | `int` | 8 (`3` = `1｜2` stays unnamed) |
| BC1054 | `Status` | `int` | 12 |
| MA350 | `Status` | `int` | 14 |
| APS | `Status Flags` | `binary_string` | 9 |
| TEOM | `status` | `int` | 29 |
| Aurora / NEPH | `Status` / `status` | `numeric` | — flat codes, only `0` (OK) is defined |
| SMPS | six text columns | `text` | — free-text tokens, not codes |

Each of these six readers' API pages carries the full table under
`#### Status Condition Register`, and a test parses it back out and compares
it with `STATUS_BITS`, so the documented table cannot drift from the code. `percentage` shares its denominator with `qc_rules` (the whole frame,
padding included); `count` is the absolute and the one to trust for a sparse
reader. `status_conditions` is **absent** from `df.attrs` where no table exists
(an incomplete map would read as "that condition never fired") or the status
column is missing, and `[]` where the register was clean. `qc_rules` is
likewise absent, not `None`, when `qc=False`.

---

## 4. `QC_Flag` vocabulary

Severity is `error` unless marked **advisory**.

| Flag | Meaning | Used by |
|---|---|---|
| `Valid` | passed every rule | all |
| `Status Error` | instrument status register reports a non-whitelisted condition | AE33, AE43, BC1054, MA350, SMPS, APS, Aurora, NEPH, TEOM |
| `Insufficient` | an hour holds < 50 % of the points it could have held, given how much of that hour the read covers — **advisory** | AE33, AE43, BC1054, MA350, SMPS, APS, Aurora, NEPH, TEOM, GRIMM |
| `Invalid BC` | any BC channel ≤ 0 or > 20 000 ng/m³ | AE33, AE43, BC1054, MA350 |
| `Invalid AAE` | AAE outside 0.7–3.0 (added in `_process`) | AE33, AE43, BC1054, MA350 |
| `Invalid Number Conc` | total number concentration outside range (SMPS 10–1e6, APS 1–700 #/cm³; the SMPS bounds take `min_total_conc=` / `max_total_conc=` per run) | SMPS, APS |
| `CPC Over-range` | any bin's dN/dlogDp exceeds what the attached CPC is rated to count, given the recorded sheath ratio — inert (logged) when the file names no known detector model or has no flow columns | SMPS |
| `DMA Water Ingress` | any bin ≥ 400 nm exceeds 4 000 dN/dlogDp | SMPS |
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
| `Mass Closure` | Σ aerosol ions > PM2.5 | IGAC |
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

## 5. Per-instrument reference

Each instrument has one page that is the single home for its raw format and
parse recipe, status column and error codes (with the decoded register table
where one exists), QC rules with severities, and output columns:

| Family | Pages |
|---|---|
| Aethalometers / BC | [AE33](../api/instruments/aethalometers/AE33.md) · [AE43](../api/instruments/aethalometers/AE43.md) · [BC1054](../api/instruments/aethalometers/BC1054.md) · [MA350](../api/instruments/aethalometers/MA350.md) |
| Particle sizers | [SMPS](../api/instruments/particle-sizers/SMPS.md) · [APS](../api/instruments/particle-sizers/APS.md) · [GRIMM](../api/instruments/particle-sizers/GRIMM.md) |
| Nephelometers | [Aurora](../api/instruments/nephelometers/Aurora.md) · [NEPH](../api/instruments/nephelometers/NEPH.md) |
| Mass | [TEOM](../api/instruments/mass/TEOM.md) · [BAM1020](../api/instruments/mass/BAM1020.md) |
| Chemistry | [OCEC](../api/instruments/chemical/OCEC.md) · [IGAC](../api/instruments/chemical/IGAC.md) · [Xact](../api/instruments/chemical/Xact.md) |
| External | [EPA](../api/instruments/other/EPA.md) |

The [Supported Instruments](../api/instruments/index.md) page carries the
catalogue and a rule-name table; §7 below is the one-line-per-instrument
matrix.

### Not readable through `RawDataReader`

#### Removed: VOC and Minion

Both were **pre-aggregated, second-hand data** — somebody else's processed
output, not an instrument's raw log — so there was no raw format for a reader to
parse and the readers only ran generic checks. They were withdrawn from
`RawDataReader` in v0.4.0; `RawDataReader('VOC', …)` / `('Minion', …)` raise a
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

#### Q-ACSM — reader not implemented yet

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

rather than an abstract-class `TypeError`. Removing the `pending` entry is all
that is needed once a reader lands.

---

## 6. Known limitations

Where the status/QC machinery is still doing less than it appears to:

| Instrument | Symptom | Status |
|---|---|---|
| **MA350** | `Status` column presence never verified against a real export | **open** — no fixture. `check_status_columns` will say so at runtime instead of passing everything |
| **GRIMM** | no concentration range check | **open by choice**: no sample corpus to calibrate one against, and a guessed threshold silently deletes good data |
| **SMPS `CPC Over-range`** | inert on files whose detector model is not in `CPC_MAX_CONC`, or that carry no flow columns | **open by design** — logged, and `cpc_max_conc=` enables it per run |
| **SMPS / APS counting efficiency** | the lowest SMPS channels and both APS ends under-count | **not corrected** — recorded in [Counting Efficiency](../theory/counting_efficiency.md) so the bias is known |
| **Aurora `S2`** | evidently a status bitfield, moves with the zero/span check | **not decoded** — no manual; kept as data |

---

## 7. Summary matrix

| Instrument | Pattern | Native | Status column | Mode | Rules | `_process` | Main outputs |
|---|---|---|---|---|:---:|:---:|---|
| [AE33](../api/instruments/aethalometers/AE33.md) | `…_AE33*.dat` | 1 min | `Status` | bitwise | 4 | ✅ | BC1–7, abs, AAE, eBC, Delta-C |
| [AE43](../api/instruments/aethalometers/AE43.md) | `…_AE43*.dat` | 1 min | `Status` | bitwise | 4 | ✅ | BC1–7, abs, AAE, eBC + metadata |
| [BC1054](../api/instruments/aethalometers/BC1054.md) | `*.csv` | 1 min | `Status` | bitwise | 4 | ✅ | BC1–10, abs, AAE, eBC + metadata |
| [MA350](../api/instruments/aethalometers/MA350.md) | `*.csv` | 1 min | `Status` (unverified) | bitwise | 4 | ✅ | BC1–5, abs, AAE, eBC + metadata |
| [Aurora](../api/instruments/nephelometers/Aurora.md) | `*.csv` | 1 min | `S1` (renamed to `Status`) | numeric | 5 | ✅ | sca_550, SAE + B/G/R, BB/BG/BR |
| [NEPH](../api/instruments/nephelometers/NEPH.md) | `*.dat` | 5 min | `status` (`Y` row f9) | numeric | 5 | ✅ | sca_550, SAE + B/G/R, BB/BG/BR |
| [SMPS](../api/instruments/particle-sizers/SMPS.md) | `*.txt`, `*.csv` | 6 min | 6 text columns (AIM 10.3 / 11.x) | text | 5 | ✅ | dN/dlogDp matrix (nm) |
| [APS](../api/instruments/particle-sizers/APS.md) | `*.txt` | 6 min | `Status Flags` | binary_string | 3 | ✅ | dN/dlogDp matrix (µm) |
| [GRIMM](../api/instruments/particle-sizers/GRIMM.md) | `*.dat` | 6 min | — | — | 3 | ❌ | size-channel concentrations |
| [TEOM](../api/instruments/mass/TEOM.md) | `*.csv` | 6 min | `status` | bitwise (32-bit) | 6 | ✅ | PM_Total, PM_NV, Volatile_Fraction |
| [BAM1020](../api/instruments/mass/BAM1020.md) | `*.csv` | 1 h | — | — | 2 | ❌ | Conc (µg/m³) |
| [OCEC](../api/instruments/chemical/OCEC.md) | `*LCRes.csv` | 1 h | — | — | 4 | ❌ | thermal / optical OC & EC, OC1–4, PC |
| [IGAC](../api/instruments/chemical/IGAC.md) | `*.csv` | 1 h | — | — | 4 | ❌ | up to 14 ion / gas species |
| [Xact](../api/instruments/chemical/Xact.md) | `*.csv` | 1 h | `ALARM` | exact code | 6 | ❌ | element concentrations + `_uncert` |
| [EPA](../api/instruments/other/EPA.md) | `*.csv` | 1 h | — | — | 1 | ❌ | air-quality reference data |
| Q-ACSM | `*.csv` | 30 min | — | — | *reader pending* | — | — |

`Rules` counts every `QCRule`, advisory ones and late ones (`Invalid AAE`)
included.

**Three registry categories** (`config/supported_instruments.py`):

- **supported** — every row above except Q-ACSM: a module in `script/` plus a
  `meta` entry.
- **pending** — `Q-ACSM`: a real instrument, reader not written yet →
  `NotImplementedError`.
- **removed** — `VOC`, `Minion`: pre-aggregated second-hand data, no raw log to
  parse → `KeyError` with migration advice, see
  [above](#removed-voc-and-minion).
