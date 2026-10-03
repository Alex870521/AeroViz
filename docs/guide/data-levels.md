# Data Levels (L0–L3)

> **Start here after your first read.** The frame `RawDataReader` hands back has
> been through four stages, and this page says what each one did to it: which
> columns were kept, where a value became NaN and why, what was cached and what
> is recomputed on every call, and what `df.attrs` is telling you. Read it once
> and the rest of the reader's behaviour — a mostly-NaN frame, a cache hit that
> still honours a new date range, a flag that did not delete its row — stops
> being surprising.
>
> The same four levels are the rules for anyone *adding* a reader, a QC rule or
> a derived parameter (§5 says where new code goes). Per-instrument file
> formats, status codes and the full flag vocabulary are in the
> [RawDataReader Reference](reader-reference.md).

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
| **L3** | **Presentation.** Places L2 on the *requested* range, applies `outlier.json`, masks every `QC_Invalid` row to NaN, drops both QC columns, resamples to `mean_freq`, computes rates, stamps `df.attrs`. | `_timeIndex_process(start, end)` → `_outlier_process` → mask → `_generate_report` → `resample` → `_stamp` | requested (`mean_freq`) | `output_{inst}.csv`, `report.json`, `{prefix}_dNdlogDp/dSdlogDp/dVdlogDp/_stats.csv`, `{inst}.log` | ❌ |

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
`RawDataReader(..., flag_severity={'Insufficient': 'error'})`.

The clearest test is to ask what the flag is *about*. `Insufficient` says an hour
is thinly covered — a statement about whether an **average over that hour** would
be representative, not about whether the readings in it are real. They are real,
so it is advisory. `Invalid BC` says the number itself is impossible; that one
invalidates.

*Classifying a new rule.* Default to `severity='error'`. Choose `'warning'`
only when the *value itself* is trustworthy and the flag describes a
circumstance around it. Two questions:

- *Would a careful analyst still use this number, given the flag?* If yes →
  advisory.
- *Does the flag describe this row's value, or its neighbours / its context?* A
  flag about context (hourly completeness, a nearby calibration) is a weak reason
  to delete a real measurement.

Advisory today: `Insufficient` (every reader that has it), OCEC `Below MDL`,
Xact `Upscale Warning` and `High Uncertainty`. `Spike` stays invalidating,
though arguably: it asserts the value is wrong, but the detector is a heuristic
that can catch real events — demote it per run with `flag_severity=` if your
analysis wants those points.

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

→ **L2 frame.** Everything up to here is skipped entirely on a whole-frame
cache hit. With `cache_dir=` and `reset='incremental'` there is a finer cache
one level down: step 1 loads each *unchanged* file's parsed frame instead of
parsing it, and steps 2–12 run as usual (see §4).

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
    range, native freq, rates, and `qc_rules`) and removes the internal
    `cache_format` marker.

    `qc_rules` is the QC summary as JSON-ready rows —
    `{rule, count, percentage, severity, description}` per rule, plus the
    `Valid` and `Usable` totals. The rates say *how much* was lost, these say
    *which rule* lost it, which is the difference between a consumer being able
    to report an outage and being able to explain one. Captured from whatever
    `log_qc_summary` was last handed, so readers that add a rule in `_process`
    (via `extend_qc_summary`) contribute their rule too. Absent from `df.attrs` when `qc=False`.

    `status_conditions` goes one level further for readers with a bitwise
    status register and a transcribed `STATUS_BITS` table (AE33, AE43, BC1054,
    MA350, APS, TEOM):
    `{code, name, count, percentage}` per condition that actually fired,
    busiest first. `Status Error` can only report that *a* bit was set — the QC
    verdict is a boolean, so the identity of the bit is gone the moment it is
    computed. This is what makes a status of `8` legible as
    *Ambient RH & Temp sensor*. Absent from `df.attrs` where no table exists (an
    incomplete map would read as "that condition never fired") or the status
    column is missing; `[]` where the register was clean.

!!! warning "`qc=False` returns L1, not \"the same data without filtering\""
    With `qc=False`, `__call__` returns the **L1** frame placed on the requested
    range and resampled to `mean_freq` if given — but no masking, no
    `outlier.json`, no report. On a fresh parse `_QC` and `_process` still run
    and the L2 cache is still written; the switch only changes which frame
    comes back. Use it to inspect raw parsed data.

---

## 4. Caching semantics

| | L1 / L2 (canonical) | L3 (presentation) |
|---|---|---|
| Stored | `_read_*_raw.pkl`, `_read_*_qc.pkl` | never |
| Keyed by | instrument + folder | — |
| Depends on `start`/`end`/`mean_freq`/`fill_missing` | **no** | yes |
| Invalidated by | `reset=True`, `cache_format` mismatch | — |
| Extended by | `reset='append'` (parses new files, concats, re-saves); `reset='incremental'` + `cache_dir` (per-file cache, see below) | — |

`CACHE_FORMAT = 4` is stamped into `df.attrs['cache_format']`; a pickle written
by an older layout is detected as stale and re-parsed automatically. Parse
provenance (`n_files`, `raw_freq`, `freq_mixed`) round-trips through the pickle
so a cache hit still reports it in `df.attrs`.

**Per-file parse cache** (`core/parse_cache.py`, opt-in with `cache_dir=`).
Below the whole-frame pkl sits a cache of each raw file's L1 parse — one pickle
per file under `{cache_dir}/{INSTRUMENT}/{source-folder hash}/`, keyed by file
name, size, mtime, reader, AeroViz version and a reader salt
(`_parse_cache_salt`). `reset='incremental'` bypasses the whole-frame pkl,
reuses every unchanged file and parses the rest; stale entries are pruned;
`reset=True` rebuilds it. Readers whose `_raw_reader` keeps side state (SMPS:
the CPC detector fields) carry it in the cached frame's `attrs['parse_meta']`
via `_collect_parse_meta` / `_apply_parse_meta`. The entries are pickles —
keep `cache_dir` on a local disk nobody else writes to.

---

## 5. Placement rules — where does new code go?

The level a change belongs to follows from what it is about — reading the
vendor's bytes (L1), judging quality (L2), deriving a quantity (L2 `_process`,
or outside the reader), shaping the answer (L3), writing a file (L3). The
decision list, together with the registry entry, hook contract, tests and docs
a new reader needs, is in [Contributing a Reader](contributing-reader.md).

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

Rate definitions (all from the `QC_Invalid` verdict, on a 1 h resample — rows
carrying only advisory flags count as valid; a period counts as
valid when **> 50 %** of its points are `Valid`):

| Rate | Definition |
|------|-----------|
| Acquisition | periods with data / expected periods |
| Yield | periods passing QC / periods with data |
| Total | periods passing QC / expected periods |
