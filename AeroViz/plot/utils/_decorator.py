from functools import wraps

import matplotlib.pyplot as plt

__all__ = ['set_figure']


# For more details please see https://matplotlib.org/stable/users/explain/customizing.html


def set_figure(func=None,
			   *,
			   figsize: tuple | None = None,
			   fs: int | None = None,
			   fw: str = None,
			   autolayout: bool = True
			   ):
	def decorator(_func):
		@wraps(_func)
		def wrapper(*args, **kwargs):
			print(f'\t\t Plot: \033[96m{_func.__name__}\033[0m')

			plt.rcParams['mathtext.fontset'] = 'custom'
			plt.rcParams['mathtext.rm'] = 'Times New Roman'
			plt.rcParams['mathtext.it'] = 'Times New Roman: italic'
			plt.rcParams['mathtext.bf'] = 'Times New Roman: bold'
			plt.rcParams['mathtext.default'] = 'regular'

			# The font properties used by `text.Text`.
			# The text, annotate, label, title, ticks, are used to create text
			plt.rcParams['font.family'] = 'Times New Roman'
			plt.rcParams['font.weight'] = fw or 'normal'
			plt.rcParams['font.size'] = fs or 8

			plt.rcParams['axes.titlesize'] = 'large'
			plt.rcParams['axes.titleweight'] = 'bold'
			plt.rcParams['axes.labelweight'] = 'bold'

			# color
			plt.rcParams['axes.prop_cycle'] = plt.cycler(color=['b', 'g', 'r', 'c', 'm', 'y', 'k'])

			plt.rcParams['xtick.labelsize'] = 'medium'
			plt.rcParams['ytick.labelsize'] = 'medium'

			# matplotlib.font_manager.FontProperties ---> matplotlib.rcParams
			plt.rcParams['legend.loc'] = 'best'
			plt.rcParams['legend.frameon'] = False
			plt.rcParams['legend.fontsize'] = 'small'
			plt.rcParams['legend.title_fontsize'] = 'medium'
			plt.rcParams['legend.handlelength'] = 1.5
			plt.rcParams['legend.labelspacing'] = 0.7

			plt.rcParams['figure.figsize'] = figsize or (5, 4)
			plt.rcParams['figure.dpi'] = 200
			plt.rcParams['figure.autolayout'] = autolayout

			if ~autolayout:
				plt.rcParams['figure.subplot.left'] = 0.1
				plt.rcParams['figure.subplot.right'] = 0.875
				plt.rcParams['figure.subplot.top'] = 0.875
				plt.rcParams['figure.subplot.bottom'] = 0.125

			# plt.rcParams['figure.constrained_layout.use'] = True

			plt.rcParams['savefig.transparent'] = True

			return _func(*args, **kwargs)

		return wrapper

	if func is None:
		return decorator

	return decorator(func)
