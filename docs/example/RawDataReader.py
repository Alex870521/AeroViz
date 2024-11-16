"""
AeroViz Example Usage Guide
==========================

This script demonstrates basic usage of RawDataReader class with AE33 data.
Author: Chan Chih Yu
GitHub: https://github.com/Alex870521/AeroViz
"""

from datetime import datetime
from pathlib import Path

from AeroViz import RawDataReader

# Set data path and time range
data_path = Path('/path/to/your/data')
start_time = datetime(2024, 2, 1)
end_time = datetime(2024, 3, 31, 23, 59, 59)

# Read and process AE33 data
ae33_data = RawDataReader(
    instrument_name='AE33',
    path=data_path / 'AE33',
    reset=True,
    qc=True,
    qc_freq='1MS',  # print qc each month
    rate=True,
    start=start_time,
    end=end_time,
    mean_freq='1h',
    csv_out=True
)

# Show processed data
print("\nProcessed AE33 data:")
print(ae33_data.head())

print("""
After processing, six files will be generated in the data directory:

1. _read_AE33_raw.csv: Raw merged data (original 1-min resolution)
2. _read_AE33_raw.pkl: Raw data in pickle format
3. _read_AE33.csv: QC processed data (original 1-min resolution)
4. _read_AE33.pkl: QC data in pickle format
5. Output_AE33: Final processed data (user-defined resolution)
6. AE33.log: Processing log file
""")
