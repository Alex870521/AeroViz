# In-situ Gas and Aerosol Composition Monitor (IGAC)

The IGAC monitor provides real-time measurements of water-soluble inorganic ions in particulate matter.

::: AeroViz.rawDataReader.script.IGAC.Reader

## Raw format

- File pattern: `*.csv`
- Native frequency: `1h`
- Encoding: `utf-8-sig` (a BOM is tolerated), undecodable bytes ignored
- Header layout: a single header row; the first column is the timestamp and
  becomes the index (`read_csv(parse_dates=True, index_col=0, na_values='-')`)
- Data structure:
    - Datetime index
    - Ion concentration columns (aerosol ions) and gas columns
    - PM2.5 mass concentration (used by `Mass Closure` when present)
    - Special values: `-` treated as NA

### Parse recipe

1. Column names are stripped of surrounding spaces.
2. Every column is coerced to numeric (`errors='coerce'`).
3. Duplicate and NaT indices are removed.

## Measurement Parameters

The IGAC provides measurements of water-soluble ions:

### Cations

| Ion | Unit | Description |
|-----|------|-------------|
| Na+ | μg/m³ | Sodium |
| NH4+ | μg/m³ | Ammonium |
| K+ | μg/m³ | Potassium |
| Mg2+ | μg/m³ | Magnesium |
| Ca2+ | μg/m³ | Calcium |

### Anions

| Ion | Unit | Description |
|-----|------|-------------|
| Cl- | μg/m³ | Chloride |
| NO2- | μg/m³ | Nitrite |
| NO3- | μg/m³ | Nitrate |
| PO43- | μg/m³ | Phosphate |
| SO42- | μg/m³ | Sulfate |

The vendor specification lists `PO43-` (and the gas `HF` / ion `F-`) as **not
measured** — their detection limit is `None` — so although `PO43-` is in the
reader's `ANION_COLUMNS`, it is not among the species the reader keeps (see
Output).

## Status & error codes

None. The export carries no status register; see
[status modes](../../../guide/reader-reference.md#3-how-a-status-judgement-is-made)
for the readers that do evaluate one.

## QC rules

| Rule | Condition | Severity |
|------|-----------|----------|
| `Mass Closure` | Σ *aerosol ions* (`Na+ NH4+ K+ Mg2+ Ca2+ Cl- NO2- NO3- SO42-` present) > `PM2.5`, when a `PM2.5` column exists — gases are not part of the PM budget; without `PM2.5` the rule never fires | error |
| `Missing Main` | any of `NH4+`, `SO42-`, `NO3-` is NaN (only evaluated when all three columns exist) | error |
| `Above MR` | any species above its stated measurement range (`reader.MR`) | error |
| `Ion Balance` | cation/anion ratio (Σ cation µg/m³ ÷ Σ anion µg/m³, mass not equivalents) outside **1.5 × IQR** (`QualityControl.iqr` on the ratio; an already-missing ratio also counts) | error |

Cation and anion sums use the columns of `CATION_COLUMNS` / `ANION_COLUMNS`
that are present; a zero anion sum gives a NaN ratio.

### Detection limits and measurement ranges

`reader.MDL` and `reader.MR` come from `meta['IGAC']` in
`config/supported_instruments.py` — the
[vendor specification](https://www.yangyao-env.com/web/product/product_in2.jsp?pd_id=PD1640151884502),
17 species covering **gases and aerosol ions**. This is the single source of
truth; the reader used to carry a second, disagreeing copy of the 9 aerosol
ions. `reader.MDL` drops the three whose limit is `None` (HF, F⁻, PO₄³⁻ — not
measured), and that **14-species** list is what the reader keeps and checks;
`reader.MR` is the spec's range table as-is (only PO₄³⁻ is `None` there).

| Species | MDL (μg/m³) | MR (μg/m³) |
|---------|-------------|------------|
| HF | None (not measured) | 200 |
| HCl | 0.05 | 200 |
| HNO2 | 0.01 | 200 |
| HNO3 | 0.05 | 200 |
| G-SO2 | 0.05 | 200 |
| NH3 | 0.1 | 300 |
| Na+ | 0.05 | 300 |
| NH4+ | 0.08 | 300 |
| K+ | 0.08 | 300 |
| Mg2+ | 0.05 | 300 |
| Ca2+ | 0.05 | 300 |
| F- | None (not measured) | 300 |
| Cl- | 0.05 | 300 |
| NO2- | 0.05 | 300 |
| NO3- | 0.01 | 300 |
| PO43- | None (not measured) | None |
| SO42- | 0.05 | 300 |

### Below MDL is a diagnostic, not a flag

The log reports, per species, what fraction of it sits below its detection
limit, worst first (`log_below_mdl`). With 17 species a per-column count says
more than one row-level flag — and because a non-`Valid` flag NaNs the whole row
at L3, a row-level `Below MDL` would delete every other species measured in
that hour. A below-MDL value is a valid measurement of a low concentration;
above-MR is different — it is outside what the instrument can report — so that
one *is* flagged.

## Output

L2 carries the 14 MDL species present in the file, gases included. Other
columns of the export (including `PM2.5`, which is consulted for `Mass Closure`
only) are not carried.

| Column | Unit | Description |
|--------|------|-------------|
| Na+, NH4+, K+, Mg2+, Ca2+ | μg/m³ | Cation concentrations |
| Cl-, NO2-, NO3-, SO42- | μg/m³ | Anion concentrations (`PO43-` is not measured and is dropped) |
| HCl, HNO2, HNO3, G-SO2, NH3 | μg/m³ | Gas-phase species |

Files written per read are listed in
[RawDataReader Reference §1](../../../guide/reader-reference.md#files-written).

## Notes

- Critical for secondary inorganic aerosol analysis
- Significant contributor to PM2.5 mass
- Comprehensive quality control procedures
- Ion balance validation ensures data integrity
- Main ion species (NH4+, SO42-, NO3-) typically dominate
