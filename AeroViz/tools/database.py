from io import StringIO
from pathlib import Path
from typing import Literal

from pandas import read_csv, DataFrame


def load_default_chemical_data():
    # The following data is from the chemical composition of real atmospheric particles.
    #
    # The six main chemical components that comprised PM2.5 are listed in the data.
    # Here, we test the radar charts to see if we can clearly identify how the
    # chemical components vary between the three pollutant scenarios:
    #
    #  1) Whole sampling period (Total)
    #  2) Clean period (Clean)
    #  3) Transition period (Transition)
    #  4) Event period (Event)

    data = {
        'Sulfate': [0.01, 0.34, 0.02, 0.71],
        'Nitrate': [0.88, 0.13, 0.34, 0.13],
        'OC': [0.07, 0.95, 0.04, 0.05],
        'EC': [0.20, 0.02, 0.85, 0.19],
        'Soil': [0.20, 0.10, 0.07, 0.01],
        'SS': [0.20, 0.10, 0.07, 0.01]
    }

    return DataFrame(data, index=['Total', 'Clean', 'Transition', 'Event'])


def load_dataset_by_url(dataset_name: Literal["Tunghai", "Taipei"] = "Tunghai") -> DataFrame:
    import requests
    dataset_uris = {
        "Tunghai": "https://raw.githubusercontent.com/alex870521/DataPlot/main/DataPlot/config/default_data.csv"
    }

    # Ensure the dataset name is valid
    if dataset_name not in dataset_uris:
        raise ValueError(f"Dataset {dataset_name} is not supported.")

    url = dataset_uris[dataset_name]

    # Make a request to the URL
    response = requests.get(url)

    if response.status_code == 200:
        return read_csv(StringIO(response.text), na_values=('E', 'F', '-', '_', '#', '*'), index_col=0,
                        parse_dates=True, low_memory=False)
    else:
        print(f"Failed to download file: {response.status_code}")
        print(response.text)  # Print the response text for debugging
        return DataFrame()  # Return an empty DataFrame in case of failure


def load_dataset_local(dataset_name: Literal["Tunghai", "Taipei", "PNSD"] = "Tunghai") -> DataFrame:
    base_dir = Path(__file__).resolve().parent.parent
    config_dir = base_dir / 'data'

    dataset_paths = {
        "Tunghai": config_dir / 'DEFAULT_DATA.csv',
        "Taipei": config_dir / 'DEFAULT_DATA.csv',
        "PNSD": config_dir / 'DEFAULT_PNSD_DATA.csv'
    }

    if dataset_name not in dataset_paths:
        raise ValueError(f"Dataset {dataset_name} is not supported.")

    file_path = dataset_paths[dataset_name]

    if not file_path.exists():
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    return read_csv(file_path, na_values=('E', 'F', '-', '_', '#', '*'), index_col=0, parse_dates=True,
                    low_memory=False)


class DataBase:
    def __new__(cls, file_path: Path | str = None, load_data: bool = False, load_PSD: bool = False):
        print(f'Loading:\033[96m Default Data\033[0m')
        if file_path is not None:
            file_path = Path(file_path)
            if file_path.exists():
                return read_csv(file_path, na_values=('E', 'F', '-', '_', '#', '*'), index_col=0, parse_dates=True,
                                low_memory=False)

        if load_data ^ load_PSD:
            return load_dataset_local("Tunghai") if load_data else load_dataset_local("PNSD")

        else:
            raise ValueError("Exactly one of 'load_data' or 'load_PSD' must be True.")


if __name__ == '__main__':
    df = DataBase("Tunghai")
