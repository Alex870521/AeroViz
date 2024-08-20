import json
from pathlib import Path

__all__ = ['Unit']


class Unit:
    file_path = Path(__file__).parent / 'units.json'
    data = None

    def __new__(cls, unit: str):
        cls.data = cls.load_jsonfile()
        try:
            value = cls.data[unit]
            return r'${}$'.format(value.replace(' ', r'\ '))
        except KeyError:
            print(f"Attribute '{unit}' not found. Using default value.")
            return r'${}$'.format(unit.replace(' ', r'\ ')) if unit is not None else 'None'

    @classmethod
    def load_jsonfile(cls):
        """ 讀取 JSON 檔中數據并將其變成屬性 """
        try:
            with open(cls.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        except FileNotFoundError:
            print(f"JSON file '{cls.file_path}' not found.")
        except json.JSONDecodeError:
            print(f"Invalid JSON format in '{cls.file_path}'.")

    @classmethod
    def update_jsonfile(cls, key, value):
        """ 更新JSON檔 """
        with open(cls.file_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)

        old_data[key] = value

        with open(cls.file_path, 'w', encoding='utf-8') as f:
            json.dump(old_data, f, indent=4)

    @classmethod
    def del_jsonfile(cls, key):
        """ 更新JSON檔 """
        with open(cls.file_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)

        if key in old_data:
            del old_data[key]

            with open(cls.file_path, 'w', encoding='utf-8') as f:
                json.dump(old_data, f, indent=4)
        else:
            print(f"Key '{key}' not found.")
