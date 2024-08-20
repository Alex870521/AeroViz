import matplotlib.colors as plc
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from cycler import cycler
from matplotlib import colormaps

__all__ = ['Color']


class Color:
    color_cycle = cycler(color=['b', 'g', 'r', 'c', 'm', 'y', 'k'])

    linecolor = [{'line': '#1a56db', 'edge': '#0F50A6', 'face': '#5983D9'},
                 {'line': '#046c4e', 'edge': '#1B591F', 'face': '#538C4A'},
                 {'line': '#c81e1e', 'edge': '#f05252', 'face': '#f98080'}]

    # colors = ['#FF3333', '#33FF33', '#FFFF33', '#5555FF', '#B94FFF', '#AAAAAA', '#748690'] # the last one is "unknown"

    colors1 = ['#A65E58', '#A5BF6B', '#F2BF5E', '#3F83BF', '#B777C2', '#D1CFCB']
    colors2 = ['#A65E58', '#A5BF6B', '#F2BF5E', '#3F83BF', '#B777C2', '#D1CFCB', '#96c8e6']
    colors3 = ['#A65E58', '#A5BF6B', '#a6710d', '#F2BF5E', '#3F83BF', '#B777C2', '#D1CFCB', '#96c8e6']  # POC SOC

    colors_mutiWater = ['#A65E58', '#c18e8a', '#A5BF6B', '#c5d6a0', '#F2BF5E', '#3F83BF', '#c089ca', '#d3acda',
                        '#D1CFCB']
    colors_mutiWater2 = ['#A65E58', '#96c8e6', '#A5BF6B', '#96c8e6', '#F2BF5E', '#3F83BF', '#c089ca', '#96c8e6',
                         '#D1CFCB']  # water

    color_choose = {'Clean': ['#1d4a9f', '#84a7e9'],
                    'Transition': ['#4a9f1d', '#a7e984'],
                    'Event': ['#9f1d4a', '#e984a7']}

    paired = [plt.get_cmap('Paired')(i) for i in range(4)]

    @staticmethod
    def getColor(num: int = 6, cmap: str = 'jet_r'):
        category_colors = plt.colormaps[cmap](np.linspace(0.1, 0.9, num))
        return [plc.to_hex(category_colors[i]) for i in range(num)]

    @staticmethod
    def palplot(*args, **kwargs):
        sns.palplot(*args, **kwargs)

    @staticmethod
    def adjust_opacity(colors: str | list[str], alpha: float):
        if isinstance(colors, str):
            colors = [colors]

        adjusted_colors = []
        for color in colors:
            # 將顏色轉換為RGB表示
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            # 調整透明度
            r_new = int(alpha * r + (1 - alpha) * 255)
            g_new = int(alpha * g + (1 - alpha) * 255)
            b_new = int(alpha * b + (1 - alpha) * 255)
            # 轉換為新的色碼
            new_color = '#{:02X}{:02X}{:02X}'.format(r_new, g_new, b_new)
            adjusted_colors.append(new_color)
        return adjusted_colors

    @staticmethod
    def color_maker(obj, cmap='Blues'):
        colors = np.nan_to_num(obj, nan=0)
        scalar_map = plt.cm.ScalarMappable(cmap=colormaps[cmap])  # create a scalar map for the colorbar
        scalar_map.set_array(colors)
        return scalar_map, colors


if __name__ == '__main__':
    Color.palplot(Color.colors2)
