# RawDataReader

`RawDataReader` is the factory that reads one instrument's raw files, applies
that instrument's QC and returns a time-indexed DataFrame with provenance in
`df.attrs`.

- **Using it** — every parameter, the date-range / resampling / `fill_missing`
  behaviour, the `df.attrs` keys and the files written:
  [RawDataReader Usage](../../guide/rawdatareader.md).
- **What it does to the data** — the four levels, what is cached and what is
  recomputed per call: [Data Levels (L0–L3)](../../guide/data-levels.md).
- **How it works inside** — QC machinery, status modes, the full flag
  vocabulary: [RawDataReader Reference](../../guide/reader-reference.md).
- **Per instrument** — file formats, status codes, QC rules and output
  columns: [Supported Instruments](../instruments/index.md).

!!! danger "Pass `start` / `end` as keywords"
    The third and fourth positional parameters are `reset` and `qc`.
    `RawDataReader('AE33', path, start, end)` does not raise — it sets
    `reset=start`, `qc=end` and applies no date filter.

## Signature

::: AeroViz.rawDataReader.RawDataReader
