# Data Levels (L0–L3)

> **Who is this for?** Anyone adding a reader, a QC rule, a derived parameter, or
> a new output file. It defines *which level* each of those belongs to, so new
> code has an obvious home and the pipeline stays auditable.
>
> For the mechanics of the existing pipeline see
> [RawDataReader Internals](rawdatareader-internals.md); for the per-instrument
> file formats and status-code tables see
> [Raw Formats & Status Codes](../api/instruments/raw-formats-and-status.md).

`RawDataReader` is not a single transformation — it is a **four-level pipeline**,
each level with a different contract about what may be added, what may be
destroyed, and whether the result may be cached. The levels are deliberately
analogous to satellite data levels (L1 = calibrated/geolocated, L2 = retrieved
geophysical quantities + quality, L3 = gridded/aggregated), with one difference:
here the aggregation axis is **time**, not space.

The level names below are the vocabulary for this pipeline. In code the same
split appears under two older names — **canonical** (L1+L2, cacheable) versus
**presentation** (L3, recomputed on every call).

---

## 1. The four levels

| Level | What it is | Produced by | Time grid | Persisted as | Cached |
|-------|-----------|-------------|-----------|--------------|:------:|
| **L0** | Vendor raw files, exactly as the instrument / host software wrote them | — (input only) | whatever the file has | never written by AeroViz | — |
| **L1** | **Parsed measurement.** One frame per instrument, every source column kept, placed on the *native* grid over the *files' own* coverage. No quality judgement. | `_raw_reader` → `_partition_compatible_scans` → `_flag_outlier_dates` → `_timeIndex_process` → numeric coercion | native (detected per file) | `_read_{inst}_raw.pkl` / `.csv` | ✅ |
| **L2** | **Quality-controlled + derived.** Adds a `QC_Flag` column and instrument-derived quantities (abs coefficients, AAE, eBC, sca_550, SAE, Volatile_Fraction). Still native resolution, still the files' own coverage. **Nothing is deleted.** | `_QC` → `_process` | native | `_read_{inst}_qc.pkl` / `.csv` | ✅ |
| **L3** | **Presentation.** Places L2 on the *requested* range, applies `outlier.json`, masks every non-`Valid` row to NaN, drops `QC_Flag`, resamples to `mean_freq`, computes rates, stamps `df.attrs`. | `_timeIndex_process(start, end)` → `_outlier_process` → mask → `resample` → `_generate_report` → `_stamp` | requested (`mean_freq`) | `output_{inst}.csv`, `report.json`, `{prefix}_dNdlogDp/dSdlogDp/dVdlogDp/_stats.csv`, `{inst}.log` | ❌ |

L1 and L2 are what `_load_or_parse` returns; L3 is everything `_run` and
`__call__` do afterwards. That boundary is the reason a cache hit still honours
the current call's `start` / `end` / `fill_missing` / `mean_freq`.

```
L0  vendor files (*.dat *.txt *.csv *.xlsx)
      │  _raw_reader — one parser per instrument, per file
      │  (+ scan-group partitioning, stray-date detection, native-grid snap)
      ▼
L1  parsed measurement  ── canonical, native res, ALL source columns, no verdict
      │  _read_{inst}_raw.pkl / .csv          ← cacheable
      │
      │  _QC     — QCFlagBuilder → QC_Flag ("Valid" | "Rule1, Rule2")
      │  _process — derived quantities, may add more flags
      ▼
L2  QC'd + derived      ── canonical, native res, flags ADDED not applied
      │  _read_{inst}_qc.pkl / .csv           ← cacheable
      ▼─────────────────── cache boundary ───────────────────
      │  _timeIndex_process(start, end, fill_missing)  — place on requested range
      │  _outlier_process                              — apply outlier.json
      │  QC_Flag != "Valid"  →  row = NaN ;  drop QC_Flag
      │  _generate_report                              — acquisition/yield/total
      │  resample(mean_freq)                           — only if requested
      │  _stamp                                        — df.attrs provenance
      ▼
L3  presentation        ── output_{inst}.csv, report.json, sidecars, returned df
```

---

## 2. The rules (invariants)

These are the judgements the pipeline is built on. A change that breaks one of
them is a bug, not a preference.

**R1 — L1 keeps everything.**
`_raw_reader` returns *every* column in the source file, including instrument
metadata (flow, temperature, RH, pressure, status). Column selection is a L2
decision. Rationale: a column dropped at L1 is unrecoverable without a full
re-read of the raw archive.

**R2 — L2 judges but never destroys.**
QC writes a verdict into `QC_Flag`; it does not NaN, drop, or overwrite values.
Masking is L3's job, and only L3's. Rationale: rates (`acquisition` / `yield` /
`total`) are computed by comparing L1 against the L2 flag — if L2 has already
destroyed the values, the yield rate is unknowable, and the user can never see
*why* a point was rejected.

**R3 — native resolution is stored once; anything coarser is derived.**
L1/L2 are always at the frequency detected from the files
(`_resolved_freq`; `meta['freq']` is only a last-resort fallback). `mean_freq`
resampling happens at L3 only. Rationale: re-deriving 1 h from 1 min is cheap;
recovering 1 min from a stored 1 h average is impossible.

**R4 — canonical is range-independent; presentation is range-dependent.**
The cache stores L1/L2 over the *files' own* coverage, never padded to a
requested range. Every range/padding/resampling decision is re-applied on each
call. Rationale: otherwise a cache written by `start='2024-01-01'` would silently
answer a later `start='2023-01-01'` call.

**R5 — derived quantities live at L2, not L1.**
Anything computed *from* measurements (absorption coefficients, Ångström
exponents, volatile fraction, size-distribution statistics) belongs in `_process`
or downstream (`AeroViz.size` / `optical` / `chemistry`), never inside
`_raw_reader`. Rationale: algorithms iterate; re-deriving from L1/L2 must not
require touching the raw archive.

**R6 — provenance is stamped once, at the end.**
`df.attrs` is written exactly once, in `_stamp`, after every transformation.
Rationale: `concat` drops conflicting `attrs`, so threading metadata through the
pipeline is unreliable — see `core/metadata.py`.

---

## 3. Execution flow

What actually happens, in order, for `RawDataReader(inst, path, start, end, qc=True, mean_freq='1h')`.

### L1 — parse (`_read_raw_files`)

1. **Discover files** — glob every pattern in `meta[inst]['pattern']` (lower /
   upper / as-written), excluding the reader's own outputs.
2. **Parse each file** — `_raw_reader(file)`. A file that raises is logged as an
   error and skipped; a file that returns `None` / empty is logged at debug.
   If *every* file fails → `ValueError`.
3. **Detect the native frequency per file** — `detect_freq` (`inferred_freq`,
   else median timestamp delta rounded to the minute) *before* the merge.
4. **Resolve one grid frequency** — `resolve_freq`: `raw_freq=` override >
   unanimous detection > most-common (sets `freq_mixed`, warns with the
   breakdown) > `meta['freq']`.
5. **Partition incompatible scan groups** — `_partition_compatible_scans`
   (no-op by default; SMPS keeps the dominant size-bin grid and names every
   dropped file in a warning).
6. **Merge** — `concat(...).groupby(level=0).first()`.
7. **Flag stray timestamps** — `_flag_outlier_dates` (median/MAD, `k=10`).
   Warn by default; drop only with `drop_outlier_dates=True`.
8. **Snap to the native grid** — `_timeIndex_process` → `to_grid` → `snap_to_grid`:
   each row is *rounded* to its nearest bin (a push, so one reading can never be
   duplicated into two slots the way `reindex(method='nearest')` does).
9. **Coerce to numeric**, preserving columns that are genuinely textual (a
   status column that coerces entirely to NaN is kept as text).

→ **L1 frame.**

### L2 — quality control and derivation

10. **`_QC(raw.copy())`** — the reader builds `QCRule`s into a `QCFlagBuilder`;
    `apply` evaluates every rule as a vectorised mask and writes
    `QC_Flag = "Valid"` or a comma-joined list of the rules that fired. A rule
    that raises is caught, warned, and treated as all-False. `get_summary`
    is stored on the reader for logging.
11. **`_process(qc)`** — derived quantities; may add more flags via
    `update_qc_flag` (which appends to an existing non-`Valid` flag). Readers
    without derived quantities inherit the identity default and log the summary
    inside `_QC` instead.
12. **`_save_data`** — write `_read_*_raw.{pkl,csv}` and `_read_*_qc.{pkl,csv}`,
    stamped with `cache_format` and the parse provenance (`n_files`, `raw_freq`,
    `freq_mixed`).

→ **L2 frame.** Everything up to here is skipped entirely on a cache hit.

### L3 — presentation (every call, cache hit or not)

13. **Place on the requested range** — `_timeIndex_process(start, end)`;
    `fill_missing=True` pads out to `[start, end]`, `False` clamps to the data's
    coverage.
14. **Apply `outlier.json`** — `_outlier_process` NaNs operator-declared
    intervals found in `{path}/outlier.json` (**qc path only**).
15. **Apply the verdict** — rows with `QC_Flag != 'Valid'` → all columns NaN;
    `QC_Flag` dropped from the public frame.
16. **Report** — `_generate_report` computes acquisition / yield / total rates
    from L1-vs-flag on a 1 h resample, per `qc` period (`'W'`, `'MS'`, …) and
    overall; `process_timeline_report` adds up/down periods and matches them
    against `known_issues.yml` (path from `KNOWN_ISSUES_PATH`).
17. **Resample** — `resample(mean_freq).mean().round(4)` *only* if `mean_freq`
    was given; otherwise the native grid is returned.
18. **Write outputs** — `output_{inst}.csv`, `report.json`; SMPS/APS additionally
    write `_dNdlogDp` / `_dSdlogDp` / `_dVdlogDp` / `_stats` sidecars via
    `finalize_size_dist`.
19. **Stamp** — `_stamp` writes `df.attrs` (provenance, coverage, requested
    range, native freq, rates) and removes the internal `cache_format` marker.

!!! warning "`qc=False` short-circuits L2 and most of L3"
    With `qc=False`, `__call__` returns the **L1** frame placed on the requested
    range — no QC, no masking, no `outlier.json`, no report, **and no
    resampling** (`mean_freq` is silently ignored on that branch). Use
    `qc=False` to inspect raw parsed data, not as "the same data without
    filtering".

---

## 4. Caching semantics

| | L1 / L2 (canonical) | L3 (presentation) |
|---|---|---|
| Stored | `_read_*_raw.pkl`, `_read_*_qc.pkl` | never |
| Keyed by | instrument + folder | — |
| Depends on `start`/`end`/`mean_freq`/`fill_missing` | **no** | yes |
| Invalidated by | `reset=True`, `cache_format` mismatch | — |
| Extended by | `reset='append'` (parses new files, concats, re-saves) | — |

`CACHE_FORMAT = 2` is stamped into `df.attrs['cache_format']`; a pickle written
by an older layout is detected as stale and re-parsed automatically. Parse
provenance (`n_files`, `raw_freq`, `freq_mixed`) round-trips through the pickle
so a cache hit still reports it in `df.attrs`.

---

## 5. Placement rules — where does new code go?

**Is it about reading the vendor's bytes?** (a new header layout, a renamed
column, a date format, an encoding, a firmware alias map) → **L1**, in that
reader's `_raw_reader`. Keep all columns; alias to canonical names; never filter
rows on quality grounds here.

**Is it a verdict about data quality?** → **L2**, as a `QCRule` in `_QC`.
Give it a stable flag name, a `description` that states the threshold, and a
vectorised `condition`. Never NaN values yourself.

**Is it a quantity computed from measurements?** → **L2** `_process` if it is
cheap, deterministic, and instrument-intrinsic (absorption coefficients, AAE,
volatile fraction). Otherwise **outside the reader** entirely, in
`AeroViz.size` / `optical` / `chemistry` / `voc` — anything with tunable
parameters or an optimisation loop does not belong in a reader.

**Is it about shape, resolution, or range of the answer?** → **L3**. Do not
store it; recompute it per call.

**Is it a file for a human or a downstream tool?** → **L3**, next to
`output_{inst}.csv`, and register it in the file-output list.

---

## 6. Where each judgement is recorded

| Channel | Level | Content | Lifetime |
|---------|:-----:|---------|----------|
| `QC_Flag` column | L2 | per-row, comma-joined rule names, `"Valid"` when clean | dropped at L3 (present in `_read_*_qc.csv`) |
| `{inst}.log` | L1–L3 | parse warnings, dropped files, mixed-resolution / stray-date warnings, QC summary with counts + percentages, rates | persistent file |
| `report.json` | L3 | `startDate` / `endDate` / `instrument_id`, weekly + monthly `rates`, `timeline` of up/down periods with reasons | overwritten per run |
| `df.attrs` | L3 | provenance, `coverage_*` vs `requested_*`, `raw_freq`, `freq_mixed`, `fill_missing`, version, `acquisition_rate` / `yield_rate` / `total_rate` | in-memory; survives pickle + resample |
| `_read_*_raw.csv` / `_read_*_qc.csv` | L1 / L2 | the levels themselves, auditable side by side | until `reset=True` |

Rate definitions (all from `QC_Flag`, on a 1 h resample; a period counts as
valid when **> 50 %** of its points are `Valid`):

| Rate | Definition |
|------|-----------|
| Acquisition | periods with data / expected periods |
| Yield | periods passing QC / periods with data |
| Total | periods passing QC / expected periods |

---

## 7. Non-conformance — what still needs fixing

Audited against the rules above. **P0 items are reproducible failures**, verified
by running the code; P1 breaks a rule; P2 is consistency / dead code / doc drift.

!!! success "Resolved: VOC and Minion withdrawn from the reader"
    Both were pre-aggregated, second-hand data — somebody else's processed
    output, not an instrument's raw log — so there was nothing for a reader to
    parse and the readers only ran generic checks. Removing them cleared what
    were a P0 item (`Minion`'s `meta['XRF']` lookup, a key that never existed)
    and most of **P0-a** / **P1-a**. `RawDataReader('VOC'|'Minion', …)` now raises a
    `KeyError` carrying migration advice. **`GRIMM` is the remaining case**
    of both **P0-a** and **P1-a** — it *is* a real instrument with a raw format, so it
    needs a `QC_Flag`, not removal.

Each item carries a stable label (**P0-a**, **P1-c**, …) so other pages can cite
it; the labels never renumber when an item is resolved and removed.

### P0 — live breakage

- **P0-a — a reader with no `QC_Flag` crashes on the default `qc=True`.**
  `self.report_dict` is only assigned inside `_generate_report`, and only when
  `qc_flag is not None` (`core/__init__.py:391`); `__call__:213` then reads it
  unconditionally. `GRIMM` returns no `QC_Flag`, so:
  `AttributeError: 'Reader' object has no attribute 'report_dict'`.
  *Verified* (originally on a 3-row VOC CSV, before VOC was removed; GRIMM takes
  the identical path). Fix: satisfy **R2** — give GRIMM a `QC_Flag`, even an
  all-`Valid` one — and initialise `self.report_dict = {}` so a future
  flag-less reader degrades instead of crashing.

- **P0-b — `Q-ACSM` is an abstract stub in the supported list.**
  `script/Q-ACSM.py` defines only `nam`; `_raw_reader` / `_QC` are missing, so
  `RawDataReader('Q-ACSM', ...)` raises `TypeError: Can't instantiate abstract
  class Reader without an implementation for abstract methods '_QC',
  '_raw_reader'`. *Verified.* Either implement it or remove it from `meta` — if
  its data also turns out to be second-hand, the VOC/Minion precedent applies
  (move it to `removed` with migration advice).

### P1 — rule violations

- **P1-a — R2 violated by GRIMM.** `GRIMM._QC` returns the frame unchanged — no
  verdict at all, so nothing downstream can distinguish good data from bad and
  the yield rate is uncomputable.

- **P1-b — flag severity does not exist, so advisory flags delete data.**
  `__call__` NaNs the whole row for *any* non-`Valid` flag. That means
  `Below MDL` (OCEC, IGAC), `Upscale Warning` (Xact), `Insufficient` and `Spike`
  erase measurements that are merely uncertain. OCEC flags `Below MDL` with
  `value <= MDL` across four carbon fractions, so clean-air periods are wiped
  wholesale. Fix: split rules into *invalidating* and *advisory*; only the former
  should mask, both should be reported.

- **P1-c — completeness QC uses the config frequency, not the detected one.**
  All nine callers pass `freq=self.meta['freq']` to `hourly_completeness_QC`
  (AE33, AE43, BC1054, MA350, NEPH, Aurora, SMPS, APS, TEOM) while the rest of
  the pipeline uses `self._resolved_freq`. A folder whose true resolution differs
  from the config (e.g. AE33 logging at 5 min against a `1min` config) is judged
  against the wrong expected count and over-flags `Insufficient`.
  Fix: `freq=self._resolved_freq or self.meta['freq']`.

- **P1-d — `mean_freq` is silently ignored when `qc=False`** (`__call__` returns
  before the resample). Either apply it on that branch or raise.

- **P1-e — status QC is silently inert for two real-world formats** (details and
  evidence in
  [Raw Formats & Status Codes](../api/instruments/raw-formats-and-status.md)):
  Aurora's production CSV has no `Status`/`Error`/`Flag` column at all (its
  status lives in the undocumented hex `S1`/`S2` fields), and SMPS AIM 11.x CSV
  exports carry neither `Status Flag` nor `Instrument Errors` — the errors are
  split four ways into `Detector Status`, `Classifier Errors`,
  `Communication Status`, `Neutralizer Status`. In both cases
  `filter_error_status` finds no column and returns all-False, so `Status Error`
  can never fire and nothing says so. Fix: warn once per run when a configured
  status column is absent, and map the missing dialects.

- **P1-f — AE33 and AE43 disagree on the same status register.** AE33 removed
  code `384` (128/256 are tape-*low* warnings, data still valid); `AE43.py:42`
  still lists `384` as an error. Same instrument family, same manual — pick one.

### P2 — consistency, dead code, doc drift

- **P2-a — dead constants.** `SMPS.MIN_HOURLY_COUNT` and `APS.MIN_HOURLY_COUNT`
  are never read (the real threshold is `hourly_completeness_QC`'s
  `threshold=0.5`); `TEOM.OUTPUT_COLUMNS` is never read either.

- **P2-b — L2 column-narrowing policy differs per reader.** OCEC and BAM1020
  slice down to their output columns; TEOM, BC1054, MA350, Aurora and NEPH return
  every column. Decide one policy (recommended: keep metadata, since **R1**'s
  rationale applies to L2 consumers too) and apply it uniformly.

- **P2-c — two sources of truth for detection limits.** `meta['Xact']['MDL']`
  (45 elements) and `meta['IGAC']['MDL']` / `['MR']` (17 species) are now read by
  **nobody** — `Minion` was their only consumer, and it is gone. The live readers
  use class-level constants (`OCEC.MDL`, 4 fractions; `IGAC.MDL`, 9 ions).
  Either wire the config values into those readers or delete them.

- **P2-d — personal absolute path as a default.** `report.py:225` defaults the
  known-issues file to `/Users/chanchihyu/DataCenter/Config/known_issues.yml`
  (overridable via `KNOWN_ISSUES_PATH`). Default should be `None` or
  project-relative.

- **P2-e — one non-vectorised QC rule.** IGAC's `Below MDL` builds a per-row list
  comprehension over columns; every other rule in the codebase is vectorised.

- **P2-f — BC1054 timestamp ambiguity.** `read_csv(..., index_col=0)` takes
  `Raw_Time` when the file has both, and then *drops* `Time`. In the NZ 2025
  fixture the two differ by hours on some rows. Decide which one is the
  measurement time and document it.

- **P2-g — `_process` runs on rows already flagged invalid.** Its docstring
  offers skipping as an optimisation, but no reader does, so AE33 / AE43 /
  BC1054 / MA350 compute and count `Invalid AAE` on rows already rejected — QC
  summary percentages overlap and do not sum meaningfully.

- **P2-h — docs drift** (the reason this page exists):
    - 15 reader docstrings point at `docs/source/instruments/*.md`, a path that
      has never existed; the real pages are
      `docs/api/instruments/<category>/*.md`.
    - `docs/api/instruments/index.md` claims AeroViz "automatically detects
      instrument types … You don't need to specify the instrument type" and shows
      `RawDataReader("instrument_data.txt")`; both are wrong — `instrument=` is
      required and validated against `meta`.
    - The same page omits `EPA` and `Q-ACSM`, which are in `meta`.
    - `rawdatareader-internals.md` listed Xact as "QC not implemented" (it has
      five rules) and AE33's `384`, and described the SMPS/APS output as
      statistics with size bins removed (it is now the reverse: bins are the
      output, statistics are a sidecar). Corrected — but the page still
      duplicates per-instrument detail that now lives in
      [Raw Formats & Status Codes](../api/instruments/raw-formats-and-status.md),
      so it should eventually shrink to mechanics only.

### Resolved

- **VOC and Minion withdrawn from the reader** (see the note at the top of this
  section). Cleared the `Minion` `meta['XRF']` crash outright, removed two of the
  three `QC_Flag`-less readers, and left `meta['Xact']['MDL']` /
  `meta['IGAC']['MDL']` with no consumer at all — see **P2-c**.

### Suggested order

1. **P0-a** then **P0-b** — one reader unusable, one uninstantiable.
2. **P1-b + P1-a** together: introduce flag severity, then give GRIMM flag-only
   QC. Highest-value change — it makes "why is my data NaN?" answerable.
3. **P1-c**, **P1-d**, **P1-f** — one-line fixes each.
4. **P1-e** — warn on missing status columns, then add the Aurora `S1`/`S2` and
   SMPS AIM 11.x dialects.
5. P2 as cleanup, with **P2-c** and **P2-h** done alongside whichever reader is
   being touched.
