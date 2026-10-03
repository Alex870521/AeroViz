# Contributing a Reader

How to add an instrument to `RawDataReader`. Everything below is checked
against the code as of v0.4.6; the base-class hooks are documented in the
[AbstractReader API](../api/AbstractReader.md), and the rules for *what belongs
at which level* are in [Data Levels (L0–L3)](data-levels.md).

## 1. Register it

Add an entry to `meta` in `AeroViz/rawDataReader/config/supported_instruments.py`:

```python
"MyInst": {
    "pattern": ["*.csv"],     # glob(s) the reader discovers, matched lower / upper / as written
    "freq": "1min",           # native resolution — a FALLBACK only; the real grid is detected per file
    # optional, read by the reader via self.meta:
    # "MDL": {...}, "MR": {...}
},
```

The factory builds its instrument map from `meta.keys()` and looks for a
module of the same name under `script/`, so the key must equal the file name.
Two other registries live in the same file: `pending` (a real instrument with
no reader yet → `NotImplementedError` naming what to contribute — remove the
entry once the reader lands) and `removed` (withdrawn readers → `KeyError`
with migration advice).

## 2. Write `script/MyInst.py`

`script/__init__.py` imports every non-underscore module in the directory
automatically; there is nothing to add there. The module must define a class
named `Reader`:

```python
from pandas import read_csv
from AeroViz.rawDataReader.core import AbstractReader, QCRule

class Reader(AbstractReader):
    """One paragraph on the instrument and export; point at the docs page."""
    nam = 'MyInst'                      # must equal the meta key

    # only if the instrument has a bitwise status register:
    STATUS_COLUMN = 'Status'            # default 'Status'
    STATUS_ENCODING = 'int'             # 'int' (decimal sum) or 'binary_string' ('0000 0000 …')
    STATUS_BITS = {1: 'Power failure', 2: 'Start up', ...}   # {decimal bit: condition}
    ERROR_STATES = [1, 2, ...]          # bits that count as errors (see step 4)

    # flags raised in _process rather than through a QCRule — lets flag_severity name them
    LATE_QC_FLAGS = ()

    def _raw_reader(self, file):
        """L1: one file -> DataFrame on a DatetimeIndex. Keep EVERY source column.
        Return None for an empty/unusable file; raise for a malformed one."""
        df = read_csv(file, index_col=0, parse_dates=True)
        return df.rename(columns={'Vendor Name (unit)': 'canonical'})

    def _QC(self, _df):
        """L2: judge, never destroy. Add QC_Flag / QC_Invalid; do not NaN values."""
        _index = _df.index.copy()
        df_qc = _df.copy()
        qc = self.qc_builder()          # a QCFlagBuilder pre-loaded with this run's flag_severity
        qc.add_rules([
            QCRule(name='Invalid Value',
                   condition=lambda df: (df['x'] <= 0) | (df['x'] > 1e4),   # True where the row FAILS
                   description='x outside 0–10 000'),
            QCRule(name='Insufficient',
                   condition=lambda df: self.QC_control().hourly_completeness_QC(
                       df, freq=self._resolved_freq or self.meta['freq']),
                   description='Less than 50% hourly data completeness',
                   severity='warning'),                                       # advisory
        ])
        df_qc = qc.apply(df_qc)
        self.log_qc_summary(qc.get_summary(df_qc))
        return df_qc.reindex(_index)

    # optional — derived, instrument-intrinsic quantities (abs coefficients, AAE …)
    # def _process(self, df): ...

    # optional — only if _raw_reader keeps side state or depends on a kwarg.
    # The per-file parse cache (cache_dir=) stores each file's frame; on a hit
    # _raw_reader never runs, so anything it would have set on self must travel
    # with the frame (SMPS: the CPC detector fields), and any kwarg that changes
    # what _raw_reader returns must be part of the key.
    # def _collect_parse_meta(self) -> dict: ...    # stored as attrs['parse_meta']
    # def _apply_parse_meta(self, meta): ...         # restore on a hit
    # def _parse_cache_salt(self) -> str: ...        # parse-affecting kwargs
```

Conventions the pipeline relies on:

- **`_raw_reader` keeps every column** (R1). Alias vendor names to canonical
  ones; never filter rows on quality here.
- **`_QC` writes flags, never NaN** (R2). Masking happens at L3 on
  `QC_Invalid` only. Default a rule to `severity='error'`; use `'warning'`
  when the *value* is trustworthy and the flag describes its context —
  `Insufficient`, a below-MDL value, a vendor "warning"-class alarm.
- **Completeness measures against the detected frequency** —
  `self._resolved_freq or self.meta['freq']`, never the config value alone.
- **Status checks go through `filter_error_status`** in one of the four modes
  (bitwise / numeric / text / binary_string), so `ignored_status_errors` works
  the same way everywhere. Call `self.check_status_columns(df, candidates)`
  first so a renamed column warns instead of silently passing every fault.
- **A flag added in `_process`** goes through `update_qc_flag(...)` and must be
  listed in `LATE_QC_FLAGS`; extend the summary with `extend_qc_summary` so
  `df.attrs['qc_rules']` sees it.
- **Derived quantities with tunable parameters** (an optimisation loop, a
  merge) do not belong in the reader — put them in `AeroViz.size` / `optical`
  / `chemistry` / `voc`.

## 3. Tests

`tests/test_readers/` has one file per reader built on `base.py`; copy the
closest one. Cover: a normal fixture, at least one dialect / malformed file,
the QC rules firing, and — if you declared `STATUS_BITS` — add the reader to
`READERS_WITH_TABLES` in `test_status_conditions.py`. That test also parses
the `#### Status Condition Register` table on the docs page (step 4) and asserts
it equals `STATUS_BITS`, so the two cannot drift.

Fixtures live outside the repo; keep `date_range` tight so cached pickles stay
small.

## 4. Docs

- Create `docs/api/instruments/<family>/MyInst.md` following the existing
  pages: raw format, **Status & error codes** (with the
  `#### Status Condition Register` table when there is a register — columns
  `Bit | Decimal | Condition`, decimal in backticks), QC rules with severity,
  output columns, notes.
- Add it to `mkdocs.yml` under *Supported Instruments*, to the list on
  [Supported Instruments](../api/instruments/index.md), and to the summary
  matrix in [RawDataReader Reference §7](reader-reference.md#7-summary-matrix).
- Add a `QC_Flag` vocabulary row in
  [Reference §4](reader-reference.md#4-qc_flag-vocabulary) for any new flag
  name.

## Where does a change go?

Not a new reader, but a change to one? Decide by what it is about:

- **Reading the vendor's bytes** (a header layout, a renamed column, a date
  format, an encoding, a firmware alias map) → L1, in `_raw_reader`.
- **A verdict about data quality** → L2, as a `QCRule` in `_QC`, with a stable
  name and a description that states the threshold.
- **A quantity computed from measurements** → L2 `_process` if cheap,
  deterministic and instrument-intrinsic; otherwise outside the reader.
- **Shape, resolution or range of the answer** → L3; recompute per call,
  never cache.
- **A file for a human or a downstream tool** → L3, next to
  `output_{inst}.csv`, registered in the file-output list.
