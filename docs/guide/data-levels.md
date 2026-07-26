# Data Levels (L0–L3)

> **Who is this for?** Anyone adding a reader, a QC rule, a derived parameter, or
> a new output file. It defines *which level* each of those belongs to, so new
> code has an obvious home and the pipeline stays auditable.
>
> For the mechanics of the existing pipeline see
> [RawDataReader Internals](rawdatareader-internals.md); for the per-instrument
> file formats and status-code tables see
> [Raw Formats & Status Codes](instrument-formats-and-qc.md).

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
| **L2** | **Quality-controlled + derived.** Adds `QC_Flag` (what fired) + `QC_Invalid` (the verdict) and instrument-derived quantities (abs coefficients, AAE, eBC, sca_550, SAE, Volatile_Fraction). Still native resolution, still the files' own coverage. **Nothing is deleted.** | `_QC` → `_process` | native | `_read_{inst}_qc.pkl` / `.csv` | ✅ |
| **L3** | **Presentation.** Places L2 on the *requested* range, applies `outlier.json`, masks every `QC_Invalid` row to NaN, drops both QC columns, resamples to `mean_freq`, computes rates, stamps `df.attrs`. | `_timeIndex_process(start, end)` → `_outlier_process` → mask → `resample` → `_generate_report` → `_stamp` | requested (`mean_freq`) | `output_{inst}.csv`, `report.json`, `{prefix}_dNdlogDp/dSdlogDp/dVdlogDp/_stats.csv`, `{inst}.log` | ❌ |

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
      │                          + QC_Invalid (True if an *error*-severity rule fired)
      │  _process — derived quantities, may add more flags
      ▼
L2  QC'd + derived      ── canonical, native res, flags ADDED not applied
      │  _read_{inst}_qc.pkl / .csv           ← cacheable
      ▼─────────────────── cache boundary ───────────────────
      │  _timeIndex_process(start, end, fill_missing)  — place on requested range
      │  _outlier_process                              — apply outlier.json
      │  QC_Invalid  →  row = NaN ;  drop QC_Flag + QC_Invalid
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
QC writes its findings into `QC_Flag` (the record: every rule that fired) and its
verdict into `QC_Invalid` (boolean: did an *invalidating* rule fire). It does not
NaN, drop, or overwrite values. Masking is L3's job, and only L3's, and it masks
on the verdict — never on the mere presence of a flag. Rationale: rates
(`acquisition` / `yield` / `total`) are computed by comparing L1 against the L2
verdict — if L2 has already destroyed the values, the yield rate is unknowable,
and the user can never see *why* a point was rejected.

**R2a — a flag is invalidating only if the measurement is untrustworthy.**
A rule declares `severity='error'` (default) or `severity='warning'`. Advisory
flags are recorded and reported but keep their data. Rationale: a value below a
detection limit, or a vendor alarm the instrument itself classes as a *warning*,
is a real measurement — and because masking is per row, invalidating it deletes
every other species measured at that timestamp too. Per-run reclassification:
`RawDataReader(..., flag_severity={'Insufficient': 'warning'})`.

**R3 — native resolution is stored once; anything coarser is derived.**
L1/L2 are always at the frequency detected from the files
(`_resolved_freq`; `meta['freq']` is only a last-resort fallback). `mean_freq`
resampling happens at L3 only. Rationale: re-deriving 1 h from 1 min is cheap;
recovering 1 min from a stored 1 h average is impossible.

*Native means native.* The grid must match the instrument's actual period, not a
tidier number near it: on a grid that drifts against the data, every reading
edges closer to its neighbour's bin until two collide and one is dropped. A
115 s APS on a 2-minute grid loses ~3 % of a day this way. Where the grid cannot
be trusted, the loss is reported rather than absorbed.

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
   else the median timestamp delta) *before* the merge. The median resolves to
   the nearest **second** once there are enough intervals to trust that
   precision (≥ 30), and to the nearest minute below that — an instrument whose
   period is not a whole number of minutes (the APS samples every 115 s) needs a
   grid that matches it.
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
   duplicated into two slots the way `reindex(method='nearest')` does). Rows that
   land in an already-occupied bin collapse, first wins — intended for genuine
   duplicates, but steady data loss when the grid does not match the true
   sampling period, so the count is **warned** with a pointer to `raw_freq=`.
9. **Coerce to numeric**, preserving columns that are genuinely textual (a
   status column that coerces entirely to NaN is kept as text).

→ **L1 frame.**

### L2 — quality control and derivation

10. **`_QC(raw.copy())`** — the reader builds `QCRule`s into a `QCFlagBuilder`;
    `apply` evaluates every rule as a vectorised mask, writes
    `QC_Flag = "Valid"` or a comma-joined list of the rules that fired, and sets
    `QC_Invalid` where at least one *invalidating* rule fired. A rule that raises
    is caught, warned, and treated as all-False. `get_summary` is stored on the
    reader for logging and reports both `Valid` (passed everything) and `Usable`
    (nothing invalidating).
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
15. **Apply the verdict** — rows where `QC_Invalid` → all columns NaN; both
    `QC_Flag` and `QC_Invalid` dropped from the public frame. A frame with no
    verdict column (a hand-built one, or a pre-severity cache) falls back to
    "any flag invalidates".
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
| `QC_Invalid` column | L2 | per-row boolean verdict — the only thing L3 masks on | dropped at L3 (present in `_read_*_qc.csv`) |
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

!!! success "Recently resolved"
    - **VOC and Minion withdrawn from the reader.** Both were pre-aggregated,
      second-hand data — somebody else's processed output, not an instrument's
      raw log — so there was nothing for a reader to parse and the readers only
      ran generic checks. `RawDataReader('VOC'|'Minion', …)` now raises a
      `KeyError` carrying migration advice.
    - **GRIMM has QC.** It is a real instrument with a raw format, so it kept its
      reader and gained three rules (`No Data`, `Negative Conc`,
      `Insufficient`) — no invented concentration thresholds. `report_dict` also
      defaults to `{}` now, so a future flag-less reader degrades to a rate-less
      report instead of crashing.
    - **Q-ACSM is registered as *pending*.** Also a real instrument, but with no
      sample export to write a parser against, so it has no reader yet and says
      so: `NotImplementedError` instead of an abstract-class `TypeError`.
    - **Xact and IGAC read their detection limits from `meta`.** One source of
      truth, `None` entries skipped; IGAC also stopped dropping its gas species
      and gained `Above MR`.

### P0 — live breakage

*None outstanding.* Both former P0 items are resolved (see the note above); the
labels **P0-a** and **P0-b** are retired rather than reused.

### P1 — rule violations

*None outstanding.* All six are resolved (see below); labels are retired, not
reused.

### P2 — consistency, dead code, doc drift

- **P2-i — hourly completeness penalises partial edge hours.** The rule measures
  each *clock hour* against `3600 s / freq`, so the first and last hour of any
  read look sparse simply because the data starts or ends mid-hour. Harmless on
  multi-day files, fatal on short ones: a 22-minute APS file has every row
  flagged. Consider exempting the edge hours, or scaling the expectation by the
  hour's overlap with the data's coverage.

- **P2-b — L2 column-narrowing policy differs per reader.** OCEC and BAM1020
  slice down to their output columns; TEOM, BC1054, MA350, Aurora and NEPH return
  every column. Decide one policy (recommended: keep metadata, since **R1**'s
  rationale applies to L2 consumers too) and apply it uniformly.

- **P2-f — BC1054 timestamp ambiguity.** `read_csv(..., index_col=0)` takes
  `Raw_Time` when the file has both, and then *drops* `Time`. In the NZ 2025
  fixture the two differ by hours on some rows. Decide which one is the
  measurement time and document it.

### Resolved

Kept as a record of what the labels used to mean:

| Was | What it was | How it was resolved |
|---|---|---|
| P0 | `Minion` could not read any file (`meta['XRF']`, a key that never existed) | reader removed — pre-aggregated second-hand data |
| P0-a | a reader with no `QC_Flag` crashed on the default `qc=True` | GRIMM gained three rules; `report_dict` defaults to `{}` so a flag-less reader degrades instead of crashing |
| P0-b | `Q-ACSM` raised an abstract-class `TypeError` | registered in `supported_instruments.pending` → `NotImplementedError` naming what to contribute |
| P1-a | R2 violated by GRIMM / VOC / Minion (no verdict, or destroyed values at L2) | GRIMM flags; the other two are gone |
| P2-c | `meta['Xact']['MDL']` / `meta['IGAC']['MDL']` had no consumer | both readers now source their limits from `meta` (`reader.MDL`, `reader.MR`), `None` entries skipped |
| P1-b | no flag severity — advisory flags (`Below MDL`, `Upscale Warning`, …) NaN'd the row as hard as `Status Error` | `QCRule(severity=...)` + a `QC_Invalid` verdict column; L3 masks on the verdict, not on the presence of a flag. `flag_severity={...}` reclassifies per run |
| P2-e | OCEC still flagged `Below MDL` row-level | now `severity='warning'` — recorded, kept. Xact's `Upscale Warning` likewise (the instrument calls 200–203 warnings, 100–110 errors) |
| P1-c | completeness QC measured against the *config* frequency | all nine callers now use `self._resolved_freq or self.meta['freq']`. The APS fixture showed why: it samples every 115 s while its config says 6 min, a 3× understatement |
| P1-d | `mean_freq` silently ignored when `qc=False` | both branches go through `_resample`, which also names the non-numeric columns it drops instead of losing them silently |
| P1-e | status QC silently inert for two real formats | Aurora recognises `S1`; SMPS knows all six column names across AIM 10.3/11.x; **every** status reader warns when no known column is present |
| P1-f | AE33 and AE43 disagreed on code `384` | AE43 aligned; a test pins the two lists equal |
| P2-a | `SMPS`/`APS.MIN_HOURLY_COUNT` and `TEOM.OUTPUT_COLUMNS` were never read | deleted, with a note saying what actually governs each (completeness is a *fraction* of the detected frequency's points; TEOM returns every column on purpose) |
| P2-d | `report.py` defaulted the known-issues file to one developer's home directory | opt-in via `KNOWN_ISSUES_PATH` only, and a set-but-unusable path now warns instead of being swallowed. A second hardcoded `~/Desktop` path in `plot/templates/corr_matrix.py` went with it |
| P2-g | `_process` was documented as being allowed to skip flagged rows | the docstring was the wrong half: skipping would violate R2 (a derived value belongs in `_read_*_qc.csv` whatever the verdict) and, since severity, would drop values for rows that are *kept*. Rewritten to say so, and to note that rule counts overlap by design |
| P2-h | docs drift | 13 reader docstrings repointed at pages that exist; `instruments/index.md` no longer claims instrument auto-detection and lists EPA / Q-ACSM / the removed readers; three broken cross-links and four malformed docstrings fixed — **`mkdocs build --strict` now passes with zero warnings**, for the first time |
| — | the native grid was rounded to whole minutes, so a 115 s APS was gridded at 2 min and ~3 % of each day's scans collapsed into an occupied bin, silently | `detect_freq` resolves to the second once ≥ 30 intervals support it; `snap_to_grid` warns whenever rows are actually lost |

### Suggested order

Three items left, and both of the remaining P2 entries above need a decision
that the code cannot make on its own:

1. **P2-i** — the only one with a data consequence. Decide whether partial edge
   hours are exempted or the expectation is scaled by the hour's overlap with
   coverage (the latter is more honest: a real mid-file gap still gets caught).
2. **P2-f** — needs the instrument manual or site knowledge: when a BC1054 file
   carries both `Raw_Time` and `Time`, which is the measurement time? They differ
   by hours on some rows, so this is a correctness question, not a style one.
3. **P2-b** — a policy call on whether L2 keeps instrument metadata. Changing it
   alters the output columns of OCEC and BAM1020 (or of five other readers,
   depending which way it goes).

### Classifying a new rule

Default to `severity='error'`. Choose `'warning'` only when the *value itself* is
trustworthy and the flag describes a circumstance around it. Two questions:

- *Would a careful analyst still use this number, given the flag?* If yes →
  advisory.
- *Does the flag describe this row's value, or its neighbours / its context?* A
  flag about context (hourly completeness, a nearby calibration) is a weak reason
  to delete a real measurement.

Currently advisory: OCEC `Below MDL`, Xact `Upscale Warning`. Deliberately still
invalidating, though arguable — flip them per run with `flag_severity=` if your
analysis wants them: `Insufficient` (the row is fine; the *hour* is sparse, and
demoting it changes every hourly mean and every rate in `report.json`) and
`Spike` (asserts the value is wrong, but the detector is a heuristic that can
catch real events).
