# GRIMM Aerosol Spectrometer

The GRIMM is an optical particle counter that measures particle size distributions across multiple size channels.

::: AeroViz.rawDataReader.script.GRIMM.Reader

## Raw format

- File pattern: `*.dat` (the config glob; the content is tab-delimited text)
    - `A407ST*.dat` files use a wider channel layout (see below)
    - Other GRIMM formats
- Native frequency: `6min` is the config fallback; the grid actually used is
  detected per file and reported as `df.attrs['raw_freq']`
- Encoding: `ISO-8859-1`
- Header layout: 233 rows of metadata, then the header row at the
  **hard-coded** line index 233
- European date format (`DD/MM/YYYY HH:MM:SS`, `dayfirst=True`) in the first
  column, which becomes the `Time` index

### Parse recipe

- `read_csv(header=233, delimiter='\t', index_col=0, parse_dates=[0],
  encoding='ISO-8859-1', dayfirst=True)`
- Size distribution channels: columns 0–10 are dropped, and so are the
  trailing 5 columns — or every column from index 128 onwards for files named
  `A407ST*` (channels 11–127)
- All values are divided by `0.035` (the scaling factor to particles/cm³)
- Empty files are warned about by name and skipped

## Measurement parameters

The GRIMM provides:

- Size range: 0.25 to 32 μm
- Resolution: Multiple size channels
- Output: Number concentration for each size bin
- Units: particles/cm³ (after scaling)

## Status & error codes

None — the GRIMM export carries no status column, so there is no
`Status Error` rule and no
[status mode](../../../guide/reader-reference.md#3-how-a-status-judgement-is-made)
applies. `ignored_status_errors` has no effect on this reader.

## QC rules

The size channels are the numeric-valued columns left after the metadata
columns were dropped in `_raw_reader`.

| Rule | Condition | Severity |
|------|-----------|----------|
| **No Data** | every size channel is NaN (also fires on every row when the file has no numeric channel at all) | error |
| **Negative Conc** | any size channel < 0 — impossible for a counter under any configuration | error |
| **Insufficient** | an hour holds < 50 % of the points it could have held at the detected frequency (edge hours scaled by coverage) | advisory (`WARNING`) — recorded, data kept |

**Deliberately absent:** concentration *range* limits, the equivalent of
SMPS's `MIN_TOTAL_CONC` / APS's `MAX_TOTAL_CONC`. There is no GRIMM sample
corpus to calibrate a plausible range against, and a wrong threshold silently
deletes good data. The three rules above need no site-specific tuning.
Producing a `QC_Flag` at all is required by the pipeline contract (rates are
computed by comparing the raw frame against the flag), which is why the
reader has a `_QC` even though it is conservative. Total-concentration
consistency and time-based outlier checks remain possible future additions.

## Output

| Column | Unit | Description |
|--------|------|-------------|
| Time index | — | Data acquisition time |
| Size channels | particles/cm³ | Number concentration for each bin |

There is no `_process` step: L2 hands on the size channels unchanged.

Files written per read are listed in
[RawDataReader Reference §1](../../../guide/reader-reference.md#files-written).

## Notes

- High resolution size information
- Wide size range coverage
- Multiple size channels
- Standard scaling factor applied
- European date format support
