# EPA (Taiwan EPA hourly air-quality export)

The EPA reader ingests the Taiwan EPA's hourly monitoring-station exports (測項 / 直式 layouts) into a fixed set of gas, PM and meteorology columns.

::: AeroViz.rawDataReader.script.EPA.Reader

## Raw format

- File pattern: `*.csv`
- Native frequency: `1h`
- Encoding: `big5` (undecodable bytes ignored); malformed lines skipped
- Header layout: a single header row; the first column is the timestamp and
  becomes the index (`read_csv(index_col=0, parse_dates=True, on_bad_lines='skip')`)
- Two layouts accepted — 查詢小時值(測項).csv (one row per timestamp, one
  column per pollutant) and 查詢小時值(直式).csv (long format, a `測項` column
  naming the pollutant and a `資料` column holding the value) — exported with
  or without the EPA's "output valid values" option

### Parse recipe

1. The file must hold exactly one station: more than one distinct `測站`
   raises `ValueError` naming them. The `測站` column is then dropped.
2. If a `測項` column is present (直式 layout) the frame is pivoted:
   `測項` values become columns, `資料` supplies the values.
3. `AMB_TEMP` → `AT`, `WIND_SPEED` → `WS`, `WIND_DIREC` → `WD`; the index is
   named `Time`.
4. Invalid-value markers that survive when the export was not pre-cleaned are
   normalised by regex — a number suffixed `#` (e.g. `12.3#`) becomes `#`, a
   number suffixed `L` becomes `_` — and then coerced to NaN with everything
   else that is not numeric.
5. The frame is **restricted** to `SO2, NO, NOx, NO2, CO, O3, THC, NMHC, CH4,
   PM10, PM2.5, PM1, WS, WD, AT, RH`, in that order
   (`reorder_dataframe_columns(..., keep_others=False)`). Any other column in
   the export — the VOC species, for instance — is **dropped**, not reordered
   to the end. Columns from the list that the export lacks are simply absent.
6. No unit conversion is applied; values are as the EPA exported them.

## Status & error codes

None. The export carries no instrument status; see
[status modes](../../../guide/reader-reference.md#3-how-a-status-judgement-is-made)
for the readers that do evaluate one.

## QC rules

| Rule | Condition | Severity |
|------|-----------|----------|
| `Negative` | any numeric column `< 0` (evaluated over the numeric columns present; never fires if there are none) | error |

## Output

L2 carries whichever of the 16 columns below the export contained, in this
order.

| Column | Description |
|--------|-------------|
| SO2 | Sulfur dioxide |
| NO | Nitric oxide |
| NOx | Nitrogen oxides |
| NO2 | Nitrogen dioxide |
| CO | Carbon monoxide |
| O3 | Ozone |
| THC | Total hydrocarbons |
| NMHC | Non-methane hydrocarbons |
| CH4 | Methane |
| PM10 | PM10 mass concentration |
| PM2.5 | PM2.5 mass concentration |
| PM1 | PM1 mass concentration |
| WS | Wind speed (from `WIND_SPEED`) |
| WD | Wind direction (from `WIND_DIREC`) |
| AT | Ambient temperature (from `AMB_TEMP`) |
| RH | Relative humidity |

Files written per read are listed in
[RawDataReader Reference §1](../../../guide/reader-reference.md#files-written).

## Notes

- This is pre-aggregated regulatory data, not an instrument log: the reader
  standardises column names and invalid markers and applies one sanity rule,
  nothing more.
- VOC species in an EPA export are dropped by the column restriction; read
  them with pandas and pass the frame to `voc_potentials` (see
  [Removed: VOC and Minion](../../../guide/reader-reference.md#removed-voc-and-minion)).
