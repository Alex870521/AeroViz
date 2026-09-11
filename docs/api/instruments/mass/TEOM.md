# TEOM (Tapered Element Oscillating Microbalance)

The TEOM is used for continuous monitoring of PM2.5 mass concentrations using microbalance technology.

::: AeroViz.rawDataReader.script.TEOM.Reader

## Raw format

- File pattern: `*.csv`
- Native frequency: `6min` (config `meta['freq']`; the grid actually found in a
  file is reported as `df.attrs['raw_freq']`)
- Header layout: three metadata rows, then the column header
  (`read_csv(skiprows=3, index_col=False)`)
- Two export dialects, auto-detected and logged per file:
    - **Remote download / GUI export** — a single timestamp column (`Time Stamp`,
      or the SNMP-named `time_stamp` some 1405 auto-exports use)
    - **USB download / auto export** — separate `Date` + `Time` columns and
      SNMP-style `tmoXxx_0` column names

### Parse recipe

1. **Both** alias maps below are applied to every file, unconditionally.
   Real exports mix conventions — a remote-download file may carry a stray
   `tmoTEOMAMC12Hr_0` column from firmware that pre-populates SNMP names — and
   every key lands on the same canonical short name, so downstream QC sees one
   schema regardless of source.
2. The dialect is detected **after** renaming and logged: a `time` column ⇒
   remote; `Date` + `Time` ⇒ usb; neither ⇒ a file-named `NotImplementedError`
   (the log lists the first columns seen so the offending file can be found).
3. **Remote timestamps** are written `DD - <month> - YYYY HH:MM:SS`, where the
   month may be a number, a Chinese name or an English name. The TEOM host
   writes the month in the operating system's language, so the same instrument
   emits `07 - 六月 - 2025 12:00:00` on a Chinese UI and `10 - Aug - 2026 00:00:01`
   after the machine is switched to English. Both name sets — plus a plain
   number — are mapped to `06` / `08` before parsing with
   `format='%d - %m - %Y %H:%M:%S'`, so a directory may freely mix them.
   `strptime`'s own `%b` / `%X` are deliberately avoided because they follow the
   *reading* machine's locale. The month-name alternation is matched
   longest-first (`十一月` before `一月`, `june` before `jun`) and
   case-insensitively.
4. **USB timestamps** are `Date + ' ' + Time` parsed by pandas; `Date` and
   `Time` are then dropped.
5. A file whose timestamps *all* fail to parse is logged by name at ERROR
   (with the first raw value) before it is dropped as empty.
6. Duplicate and NaT indices are removed. Every column is kept — there is no
   `OUTPUT_COLUMNS` narrowing — so the instrument's diagnostics stay reachable.

### Remote download / GUI export aliases

| Column | Mapping | Description |
|--------|---------|-------------|
| Time Stamp | time | Timestamp (`DD - MM - YYYY HH:MM:SS`; the month may be a number or a localized name, e.g. `六月` / `Aug`) |
| System status | status | Instrument status (32-bit condition register) |
| PM-2.5 base MC | PM_NV | Non-volatile PM2.5 |
| PM-2.5 reference MC | PM_ref | Reference-channel PM2.5 |
| PM-2.5 MC | PM_Total | Total PM2.5 |
| PM-2.5 1-Hr MC | PM_1Hr | 1-hour average PM2.5 |
| PM-2.5 24-Hr MC | PM_24Hr | 24-hour average PM2.5 |
| PM-2.5 TEOM frequency | frequency | Tapered-element oscillation frequency |
| PM-2.5 TEOM noise | noise | Measurement noise |
| PM-2.5 TEOM filter load | filter_load | Filter loading |
| PM-2.5 TEOM filter pressure | filter_pressure | Filter pressure |
| PM-2.5 vol. flow rate | flow_rate | Sample volumetric flow |
| Bypass volumetric flow rate | bypass_flow | Bypass volumetric flow |
| PM-2.5 air tube temp | air_tube_temp | Air-tube temperature |
| Cap temperature | cap_temp | Cap heater temperature |
| Case temperature | case_temp | Case heater temperature |
| PM-2.5 cooler temp | cooler_temp | Cooler temperature |
| PM-2.5 dryer dew point | dryer_dew_point | Dryer dew point |
| Ambient temperature | ambient_temp | Ambient temperature |
| Ambient relative humidity | ambient_RH | Ambient relative humidity |
| Ambient pressure | ambient_pressure | Ambient pressure |
| Vacuum pump pressure | pump_pressure | Vacuum pump pressure |

### USB / auto export aliases

| Column | Mapping | Description |
|--------|---------|-------------|
| Date, Time | time | Timestamp (two columns, joined) |
| time_stamp | time | Timestamp (single column, SNMP-named auto-export) |
| tmoStatusCondition_0 | status | Instrument status (32-bit condition register) |
| tmoTEOMABaseMC_0 | PM_NV | Non-volatile PM2.5 |
| tmoTEOMARefMC_0 | PM_ref | Reference-channel PM2.5 |
| tmoTEOMAMC_0 | PM_Total | Total PM2.5 |
| tmoTEOMAMC1Hr_0 | PM_1Hr | 1-hour average PM2.5 |
| tmoTEOMAMC12Hr_0 | PM_12Hr | 12-hour average PM2.5 |
| tmoTEOMAFrequency_0 | frequency | Tapered-element oscillation frequency |
| tmoTEOMANoise_0 | noise | Measurement noise |
| tmoTEOMAFilterLoad_0 | filter_load | Filter loading |
| tmoTEOMADryerDewPoint_0 | dryer_dew_point | Dryer dew point |
| tmoTEOMAFlowVolumetric_0 | flow_rate | Sample volumetric flow |
| tmoBypassFlowVolumetric_0 | bypass_flow | Bypass volumetric flow |
| tmoTEOMAAirTubeHeatTemp_0 | air_tube_temp | Air-tube heater temperature |
| tmoCapHeatTemp_0 | cap_temp | Cap heater temperature |
| tmoCaseHeatTemp_0 | case_temp | Case heater temperature |
| tmoAmbientTemp_0 | ambient_temp | Ambient temperature |
| tmoAmbientRH_0 | ambient_RH | Ambient relative humidity |
| tmoVacPumpPressure_0 | pump_pressure | Vacuum pump pressure |

## Measurement Parameters

| Parameter | Unit | Description |
|-----------|------|-------------|
| PM_Total | μg/m³ | Total PM2.5 mass concentration |
| PM_NV | μg/m³ | Non-volatile PM2.5 concentration |
| noise | - | TEOM measurement noise |

## Status & error codes

Column `status` (raw `System status` / `tmoStatusCondition_0`), mode
**`bitwise`** — see [status modes](../../../guide/reader-reference.md#3-how-a-status-judgement-is-made).
`STATUS_OK = 0` ("Normal status"). `ERROR_STATES = [1 << b for b in range(32)]`,
so every set bit counts as an error by default — the same verdict as the old
`status != 0` numeric test, but bitwise mode lets one condition be whitelisted
regardless of what else is co-set, which a flat comparison cannot do. Narrow the
list once a site decides which conditions are advisory. The reader calls
`check_status_columns` first, so a renamed status column is logged rather than
silently passing every fault.

#### Status Condition Register

`status` (`System status` / `tmoStatusCondition_0`) is a **32-bit bitfield**, not
a flat code: the instrument OR-sums every active warning and reports the decimal
sum. A status of `24` is therefore two conditions at once (`8 | 16`), not a
condition numbered 24.

The reader carries this table as `Reader.STATUS_BITS`, which is what decodes the
register into `df.attrs['status_conditions']` — so a status of `8` is reported as
*Ambient RH & Temp sensor* rather than left for the reader of a log to look up.
"A"/"B" denote the FDMS dual-channel sides. Source: TEOM 1405 / 1405-F manual,
Appendix A, Table A-1.

| Bit | Decimal | Condition |
|-----|---------|-----------|
| 30 | `1073741824` | %RH High Side A (>=98%) |
| 29 | `536870912` | Dryer A (>2) |
| 28 | `268435456` | Cooler A (>0.5C deviation) |
| 27 | `134217728` | Exchange Filter A (>90) |
| 26 | `67108864` | Flow A (>10% deviation) |
| 25 | `33554432` | Heaters Side A (>2% deviation) |
| 24 | `16777216` | Mass Transducer A (<10Hz) |
| 22 | `4194304` | %RH High Side B (>=98%) |
| 21 | `2097152` | Dryer B (>2) |
| 20 | `1048576` | Cooler B (>0.5C deviation) |
| 19 | `524288` | Exchange Filter B (>90) |
| 18 | `262144` | Flow B (>10% deviation) |
| 17 | `131072` | Heaters Side B (>2% deviation) |
| 16 | `65536` | Mass Transducer B (<10Hz) |
| 14 | `16384` | User I/O |
| 13 | `8192` | FDMS Device |
| 12 | `4096` | Head 1 |
| 11 | `2048` | Head 0 |
| 10 | `1024` | MFC 1 |
| 9 | `512` | MFC 0 |
| 8 | `256` | System Bus |
| 7 | `128` | Vacuum Pressure (<0.1 atm) |
| 6 | `64` | Case/Cap Heater (>2% deviation) |
| 5 | `32` | FDMS Valve |
| 4 | `16` | Bypass Flow (>10% deviation) |
| 3 | `8` | Ambient RH & Temp sensor |
| 2 | `4` | Database (log failure) |
| 1 | `2` | Enclosure Temp (>60C) |
| 0 | `1` | Power Failure |

Bits 15, 23 and 31 are not assigned in Table A-1. Any of them being set still
counts as a `Status Error` — `ERROR_STATES` covers all 32 bits — it simply has no
name to report.

To stop treating one condition as an error, whitelist its decimal value; bitwise
testing means it stays whitelisted no matter what else is co-set:

```python
RawDataReader('TEOM', path, ignored_status_errors=[536870912])  # ignore Dryer A
```


## QC rules

| Rule | Condition | Severity |
|------|-----------|----------|
| `Status Error` | any non-whitelisted bit of the 32-bit `status` register is set | error |
| `High Noise` | `noise >= 0.01` (`MAX_NOISE`) | error |
| `Non-positive` | `PM_NV <= 0` or `PM_Total <= 0` | error |
| `NV > Total` | `PM_NV > PM_Total` (physically impossible) | error |
| `Spike` | sudden change in `PM_NV` / `PM_Total` (`spike_detection`, `max_change_rate=3.0`) | error |
| `Insufficient` | an hour holds < 50 % of the points it could have held (`hourly_completeness_QC` over the PM columns at the resolved frequency) | advisory |

`Insufficient` is a statement about representativeness, not validity, which is
why it is advisory; promote it per run with
`flag_severity={'Insufficient': 'error'}` (see
[severity](../../../guide/reader-reference.md#severity-not-every-flag-is-fatal)).
There is no volatile-fraction range rule: `Volatile_Fraction` is derived in
`_process` after QC and is never tested.

## Output

L2 carries `Volatile_Fraction = (PM_Total − PM_NV) / PM_Total` (rounded to 4
decimals, added in `_process`) **plus every other column** of the raw file —
on purpose, so the instrument's diagnostics stay reachable.

| Column | Unit | Description |
|--------|------|-------------|
| PM_Total | μg/m³ | Total PM2.5 mass concentration |
| PM_NV | μg/m³ | Non-volatile PM2.5 concentration |
| Volatile_Fraction | - | `(PM_Total − PM_NV) / PM_Total`, derived |
| noise, status, frequency, flow_rate, … | as exported | every remaining aliased column (see the alias tables above) |

Files written per read are listed in
[RawDataReader Reference §1](../../../guide/reader-reference.md#files-written).

## Usage Example

```python
from datetime import datetime
from pathlib import Path

from AeroViz import RawDataReader

# Set data path and time range
data_path = Path('/path/to/your/data/folder')
start_time = datetime(2024, 2, 1)
end_time = datetime(2024, 3, 31, 23, 59, 59)

# Read and process TEOM data
teom_data = RawDataReader(
    instrument='TEOM',
    path=data_path,
    reset=True,
    qc='1MS',
    start=start_time,
    end=end_time,
    mean_freq='1h',
)

# Show processed data
print("\nProcessed TEOM data:")
print(teom_data.head())
```
