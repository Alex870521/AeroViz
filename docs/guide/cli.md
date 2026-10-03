# Command line: `aeroviz`

The reader from a terminal — for a field technician on the station PC, a cron
job, or a quick look at a folder before writing any Python. It is installed
with the package; every option maps one-to-one onto the Python API.

```bash
aeroviz instruments                                   # supported readers, native freq, globs
aeroviz inventory SMPS /data/NZ_SMPS                  # what is in the folder, without parsing
aeroviz read SMPS /data/NZ_SMPS --start 2026-01-01 --end 2026-01-31 --freq 1h \
        --out nz_smps_2026-01.nc --report nz_smps_2026-01.md
```

## `aeroviz read INSTRUMENT PATH`

| Option | Python equivalent |
|--------|-------------------|
| `--start`, `--end` | `start=`, `end=` |
| `--freq 1h` | `mean_freq='1h'` (omit for native resolution) |
| `--no-qc` | `qc=False` |
| `--reset` | `reset=True` |
| `--incremental --cache-dir DIR` | `reset='incremental', cache_dir=DIR` |
| `--qc-config qc.yaml` | `qc_config='qc.yaml'` |
| `--workers 4` | `parse_workers=4` |
| `--quiet` | `quiet=True` |
| `--out FILE` | `.csv` → `to_csv`; `.parquet` → `to_parquet` (needs pyarrow); `.nc` → [`to_netcdf`](rawdatareader.md#export-to-netcdf); `.pkl` → `to_pickle` |
| `--report FILE` | [`write_qc_report`](rawdatareader.md#write-a-qc-report) |

It prints a short summary — rows, files, native and output frequency,
coverage, the three QC rates, parse-cache reuse — then writes what was asked.

## `aeroviz inventory INSTRUMENT PATH [--out FILE]`

Prints the file table [`inventory()`](rawdatareader.md#inventory-a-folder-before-reading)
returns and its summary; `--out x.csv` / `x.json` saves them.

## Exit status

`0` on success. Argument problems and unsupported `--out` suffixes exit `2`
with a one-line message; reader errors propagate as Python exceptions so the
traceback says which file was at fault.
