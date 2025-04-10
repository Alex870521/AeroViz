# Volatile Organic Compounds Analyzer (VOC)

The VOC analyzer measures concentrations of various volatile organic compounds in air.

## Data Format

- File format: CSV file
- Sampling frequency: Variable
- File naming pattern: `*.csv`
- Data structure:
    - Datetime index
    - VOC species columns
    - Special values:
        - '-' treated as NA
        - 'N.D.' (Not Detected) treated as NA

## Measurement Parameters

The VOC analyzer provides:

- Multiple VOC species measurements
- Concentration data for each compound
- Supported species list required
- Species-specific detection limits

## Supported VOC Species

The analyzer supports the following VOC species:

|  class   |        Species         |  MIR  |   MW   | SOAP  |  KOH  |
|:--------:|:----------------------:|:-----:|:------:|:-----:|:-----:|
| aromatic |        Benzene         | 0.72  | 78.11  | 92.9  | 1.22  |
|          |        Toluene         |  4.0  | 92.14  | 100.0 | 5.63  |
|          |      Ethylbenzene      | 3.04  | 106.17 | 111.6 |  7.0  |
|          |       m/p-Xylene       |  7.8  | 106.2  | 75.8  | 18.95 |
|          |        o-Xylene        | 7.64  | 106.16 | 95.5  | 13.6  |
|  alkane  |         Ethane         | 0.28  | 30.07  |  0.1  | 0.248 |
|          |        Propane         | 0.49  |  44.1  |  0.0  | 1.09  |
|          |       Isobutane        | 1.23  | 58.12  |  0.0  | 2.12  |
|          |        n-Butane        | 1.15  | 58.12  |  0.3  | 2.36  |
|          |       Isopentane       | 1.45  | 72.15  |  0.2  |  3.6  |
|          |       n-Pentane        | 1.31  | 72.15  |  0.3  |  3.8  |
|          |        n-Hexane        | 1.24  | 86.18  |  0.1  |  5.2  |
|          |       n-Heptane        | 1.07  | 100.21 |  0.1  | 6.76  |
|          |        n-Octane        |  0.9  | 114.23 |  0.8  | 8.11  |
|          |        n-Nonane        | 0.78  | 128.2  |  1.9  |  9.7  |
|          |        n-Decane        | 0.68  | 142.29 |  7.0  | 11.0  |
|          |       n-Undecane       | 0.61  | 156.31 | 16.2  | 12.3  |
|          |       n-Dodecane       | 0.55  |  null  | null  | null  |
|  alkene  |        Ethylene        |  9.0  | 28.05  |  1.3  | 8.52  |
|          |  Propylene (Propene)   | 11.66 | 42.08  |  1.6  | 26.3  |
|          |        1-Butene        | 9.73  |  56.1  |  1.2  | 31.4  |
|          |       t-2-Butene       | 15.16 |  56.1  |  3.1  | 56.4  |
|          |      cis-2-Butene      | 14.24 |  56.1  |  3.6  | 64.0  |
|          |       1-Pentene        | 7.21  | 70.13  |  0.0  | 31.4  |
|          |      t-2-Pentene       | 10.56 | 70.13  |  4.0  | 67.0  |
|          |     cis-2-Pentene      | 10.38 | 70.13  |  3.6  | 65.0  |
|          |        1-Hexene        | 5.49  |  null  | null  | null  |
|          |        Isoprene        | 10.61 |  68.1  |  1.9  | 100.0 |
|  alkyne  |       Acetylene        | 0.95  | 26.04  |  0.1  | 0.85  |
|  alkane  |      Cyclopentane      | 2.39  |  70.1  |  0.0  | 4.97  |
|          |   Methylcyclopentane   | 2.19  | 84.16  |  0.0  |  5.2  |
|          |      Cyclohexane       | 1.25  | 84.16  |  0.0  | 6.97  |
|          |   Methylcyclohexane    |  1.7  | 98.19  |  0.0  | 4.97  |
|          |   2,2-Dimethylbutane   | 1.17  | 86.17  |  0.0  | 2.23  |
|          |   2,3-Dimethylbutane   | 0.97  | 86.18  |  0.0  | 5.78  |
|          |    2-Methylpentane     |  1.5  | 86.18  |  0.0  |  5.4  |
|          |    3-Methylpentane     |  1.8  | 86.18  |  0.2  |  5.2  |
|          |  2,3-Dimethylpentane   | 1.34  | 100.2  |  0.4  |  1.5  |
|          |  2,4-Dimethylpentane   | 1.55  | 100.2  |  0.0  | 4.77  |
|          |     2-Methylhexane     | 1.19  | 100.2  |  0.0  | 5.65  |
|          |    3-Methylheptane     | 1.24  | 114.23 |  0.0  |  5.6  |
|          | 2,2,4-Trimethylpentane | 1.26  | 114.23 |  0.0  | 3.34  |
|          | 2,3,4-Trimethylpentane | 1.03  | 114.23 |  0.0  |  6.6  |
|          |    2-Methylheptane     | 1.07  | 114.23 |  0.0  |  7.0  |
|          |     3-Methylhexane     | 1.61  | 100.2  |  0.0  |  7.0  |
| aromatic |        Styrene         | 1.73  | 104.15 | 212.3 | 58.0  |
|          |    Isopropylbenzene    | 2.52  | 120.19 | 95.5  |  6.3  |
|          |    n-Propylbenzene     | 2.03  |  null  | null  | null  |
|          |     m-Ethyltoluene     | 7.39  | 120.19 | 100.6 | 11.8  |
|          |     p-Ethyltoluene     | 4.44  | 120.19 | 69.7  | 18.6  |
|          |     o-Ethyltoluene     | 5.59  | 120.19 | 94.8  | 11.9  |
|          |    m-Diethylbenzene    |  7.1  | 134.22 |  0.0  | 32.5  |
|          |    p-Diethylbenzene    | 4.43  | 134.22 |  0.0  | 32.7  |
|          | 1,3,5-Trimethylbenzene | 11.76 | 120.19 | 13.5  | 56.7  |
|          | 1,2,4-Trimethylbenzene | 8.87  | 120.19 | 20.6  | 32.5  |
|          | 1,2,3-Trimethylbenzene | 11.97 | 120.19 | 43.9  | 32.7  |
|          |     1,3-Butadiene      | 12.61 |  54.1  |  1.8  | 66.6  |
|          |        1-Octene        | 3.25  | 112.2  | null  | 30.0  |
|          |     2-Ethyltoluene     | 5.59  | 120.2  | 94.8  | 11.9  |
|          |    3,4-Ethyltoluene    | 5.92  | 120.2  | 85.2  | 15.2  |
|   OVOC   |      Acetaldehyde      | 6.54  |  44.1  |  0.6  | 15.0  |
|   OVOC   |        Acetone         | 0.36  |  58.1  |  0.3  | 0.17  |
|   OVOC   |     Butyl Acetate      | 0.83  | 116.2  |  0.0  | null  |
|   OVOC   |        Ethanol         | 1.53  |  46.1  |  0.6  |  3.2  |
|   OVOC   |     Ethyl Acetate      | 0.63  |  88.1  |  0.1  | null  |
|   OVOC   |          IPA           | 0.61  |  60.1  |  0.4  |  5.1  |
|  ClVOC   |        1,2-DCB         | 0.18  | 147.0  | null  | null  |
|  ClVOC   |        1,4-DCB         | 0.18  | 147.0  | null  | null  |
|  ClVOC   |          PCE           | 0.03  | 165.8  | null  | 0.16  |
|  ClVOC   |          TCE           | 0.64  | 131.4  | null  |  1.9  |
|  ClVOC   |          VCM           | 2.83  |  62.5  | null  | null  |

### Species Parameters:

- MIR: Maximum Incremental Reactivity
- MW: Molecular Weight
- SOAP: Secondary Organic Aerosol Potential
- KOH: Rate constant for the reaction with OH radicals

## Data Processing

### Data Reading

- Processes CSV files with datetime index
- Handles special values as NA
- Standardizes column names
- Filters based on supported species list
- Warns about unsupported species
- Removes duplicate timestamps

### Quality Control

- Basic file validation
- No additional QC currently implemented
- Future QC possibilities:
    - Minimum detection limit filtering
    - Value range checks
    - Time-based outlier detection
    - Correlation checks between species

## Output Data

The processed data contains:

- Time index: Data acquisition time
- VOC species: Concentrations of supported compounds
- All measurements in standard units
- Validated species names

## Usage Example

```python
from datetime import datetime as dtm
from pathlib import Path

from AeroViz.dataProcess import *
from AeroViz.rawDataReader import *

start, end = dtm(2024, 2, 1), dtm(2024, 7, 31, 23)

path_raw = Path('data')
path_prcs = Path('prcs')

# read data
dt_VOC = RawDataReader('VOC', path_raw / 'VOC', reset=False, start=start, end=end)
dt_VOC.rename(columns={'isoprene': 'Isoprene', 'm,p-Xylene': 'm/p-Xylene'}, inplace=True)

voc_prcs = DataProcess('VOC', path_out=path_prcs, excel=False, csv=True)

df = voc_prcs.VOC_basic(dt_VOC)
```

## Notes

- Critical for air quality assessment
- Important for photochemical reaction studies
- Helps identify secondary organic aerosol sources
- Requires predefined species list
- Species name standardization essential
- Some species may have missing parameters (marked as "null")
- Analysis includes concentration, MIR, SOAP, and KOH values