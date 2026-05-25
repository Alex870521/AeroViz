import json
from pathlib import Path

__all__ = ['Unit']


class Unit:
    file_path = Path(__file__).parent / 'units.json'
    data = None

    def __new__(cls, unit: str):
        cls.data = cls.load_jsonfile() or {}
        if unit is None:
            return ''
        # Unknown labels fall back to the label itself (no console noise — a
        # label simply not being in units.json is normal, not an error).
        value = cls.data.get(unit, unit)
        # '%' starts a comment in matplotlib mathtext, so a bare '%' inside the
        # $...$ wrapper raises a ParseException (e.g. unit='%' or 'OM ratio (%)').
        # Escape it so the label renders literally.
        value = value.replace(' ', r'\ ').replace('%', r'\%')
        return r'${}$'.format(value)

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
