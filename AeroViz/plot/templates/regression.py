import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.pyplot import Figure, Axes
from sklearn.linear_model import LinearRegression
from tabulate import tabulate

from AeroViz.plot.utils import *

__all__ = [
	'linear_regression',
	'multiple_linear_regression',
]


def _linear_regression(x_array: np.ndarray,
					   y_array: np.ndarray,
					   columns: str | list[str] | None = None,
					   positive: bool = True,
					   fit_intercept: bool = True):
	if len(x_array.shape) > 1 and x_array.shape[1] >= 2:
		model = LinearRegression(positive=positive, fit_intercept=fit_intercept).fit(x_array, y_array)

		coefficients = model.coef_[0].round(3)
		intercept = model.intercept_[0].round(3) if fit_intercept else 'None'
		r_square = model.score(x_array, y_array).round(3)
		y_predict = model.predict(x_array)

		equation = ' + '.join([f'{coeff:.3f} * {col}' for coeff, col in zip(coefficients, columns)])
		equation = equation.replace(' + 0.000 * Const', '')  # Remove terms with coefficient 0

		text = 'y = ' + str(equation) + '\n' + r'$\bf R^2 = $' + str(r_square)
		tab = tabulate([[*coefficients, intercept, r_square]], headers=[*columns, 'intercept', 'R^2'], floatfmt=".3f",
					   tablefmt="fancy_grid")
		print('\n' + tab)

		return text, y_predict, coefficients

	else:
		x_array = x_array.reshape(-1, 1)
		y_array = y_array.reshape(-1, 1)

		model = LinearRegression(positive=positive, fit_intercept=fit_intercept).fit(x_array, y_array)

		slope = model.coef_[0][0].round(3)
		intercept = model.intercept_[0].round(3) if fit_intercept else 'None'
		r_square = model.score(x_array, y_array).round(3)
		y_predict = model.predict(x_array)

		text = np.poly1d([slope, intercept])
		text = 'y = ' + str(text).replace('\n', "") + '\n' + r'$\bf R^2 = $' + str(r_square)

		tab = tabulate([[slope, intercept, r_square]], headers=['slope', 'intercept', 'R^2'], floatfmt=".3f",
					   tablefmt="fancy_grid")
		print('\n' + tab)

		return text, y_predict, slope


@set_figure
def linear_regression(df: pd.DataFrame,
					  x: str | list[str],
					  y: str | list[str],
					  labels: str | list[str] = None,
					  ax: Axes | None = None,
					  diagonal=False,
					  positive: bool = True,
					  fit_intercept: bool = True,
					  **kwargs
					  ) -> tuple[Figure, Axes]:
	"""
	Create a scatter plot with multiple regression lines for the given data.

	Parameters
	----------
	df : DataFrame
		Input DataFrame containing the data.

	x : str or list of str
		Column name(s) for the x-axis variable(s).

	y : str or list of str
		Column name(s) for the y-axis variable(s).

	labels : str or list of str, optional
		Labels for the y-axis variable(s). If None, column names are used as labels. Default is None.

	ax : AxesSubplot, optional
		Matplotlib AxesSubplot to use for the plot. If None, a new subplot is created. Default is None.

	diagonal : bool, optional
		If True, a diagonal line (1:1 line) is added to the plot. Default is False.

	positive : bool, optional
	   Whether to let coefficient positive. Default is True.

	fit_intercept: bool, optional
		Whether to fit intercept. Default is True.

	**kwargs
		Additional keyword arguments to customize the plot.

	Returns
	-------
	AxesSubplot
		Matplotlib AxesSubplot containing the scatter plot.

	Notes
	-----
	- The function creates a scatter plot with the option to include multiple regression lines.
	- If regression is True, regression lines are fitted for each y variable.
	- Additional customization can be done using the **kwargs.

	Example
	-------
	>>> linear_regression(df, x='X', y=['Y1', 'Y2'], labels=['Label1', 'Label2'],
	...                      regression=True, diagonal=True, xlim=(0, 10), ylim=(0, 20),
	...                      xlabel="X-axis", ylabel="Y-axis", title="Scatter Plot with Regressions")
	"""
	fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

	if not isinstance(x, str):
		x = x[0]

	if not isinstance(y, list):
		y = [y]

	if labels is None:
		labels = y

	df = df.dropna(subset=[x, *y])
	x_array = df[[x]].to_numpy()

	color_cycle = Color.linecolor

	handles, text_list = [], []

	for i, y_var in enumerate(y):
		y_array = df[[y_var]].to_numpy()

		color = color_cycle[i % len(color_cycle)]

		scatter = ax.scatter(x_array, y_array, s=25, color=color['face'], edgecolors=color['edge'], alpha=0.8,
							 label=labels[i])
		handles.append(scatter)

		text, y_predict, slope = _linear_regression(x_array, y_array,
													columns=labels[i],
													positive=positive,
													fit_intercept=fit_intercept)

		text_list.append(f'{labels[i]}: {text}')
		plt.plot(x_array, y_predict, linewidth=3, color=color['line'], alpha=1, zorder=3)

	ax.set(xlim=kwargs.get('xlim'), ylim=kwargs.get('ylim'), xlabel=Unit(x), ylabel=Unit(y[0]),
		   title=kwargs.get('title'))

	# Add regression info to the legend
	leg = plt.legend(handles=handles, labels=text_list, loc='upper left', prop={'weight': 'bold', 'size': 10})

	for text, color in zip(leg.get_texts(), [color['line'] for color in color_cycle]):
		text.set_color(color)

	if diagonal:
		ax.axline((0, 0), slope=1., color='k', lw=2, ls='--', alpha=0.5, label='1:1')
		plt.text(0.97, 0.97, r'$\bf 1:1\ Line$', color='k', ha='right', va='top', transform=ax.transAxes)

	plt.show()

	return fig, ax


@set_figure
def multiple_linear_regression(df: pd.DataFrame,
							   x: str | list[str],
							   y: str | list[str],
							   labels: str | list[str] = None,
							   ax: Axes | None = None,
							   diagonal=False,
							   positive: bool = True,
							   fit_intercept: bool = True,
							   **kwargs
							   ) -> tuple[Figure, Axes]:
	"""
	Perform multiple linear regression analysis and plot the results.

	Parameters
	----------
	df : pandas.DataFrame
	   Input DataFrame containing the data.

	x : str or list of str
	   Column name(s) for the independent variable(s). Can be a single string or a list of strings.

	y : str or list of str
	   Column name(s) for the dependent variable(s). Can be a single string or a list of strings.

	labels : str or list of str, optional
	   Labels for the dependent variable(s). If None, column names are used as labels. Default is None.

	ax : matplotlib.axes.Axes or None, optional
	   Matplotlib Axes object to use for the plot. If None, a new subplot is created. Default is None.

	diagonal : bool, optional
	   Whether to include a diagonal line (1:1 line) in the plot. Default is False.

	positive : bool, optional
	   Whether to let coefficient positive. Default is True.

	fit_intercept: bool, optional
		Whether to fit intercept. Default is True.

	**kwargs
	   Additional keyword arguments to customize the plot.

	Returns
	-------
	matplotlib.axes.Axes
	   Matplotlib Axes object containing the regression plot.

	Notes
	-----
	This function performs multiple linear regression analysis using the input DataFrame.
	It supports multiple independent variables and can plot the regression results.

	Example
	-------
	>>> multiple_linear_regression(df, x=['X1', 'X2'], y='Y', labels=['Y1', 'Y2'],
	...                             diagonal=True, add_constant=True,
	...                             xlabel="X-axis", ylabel="Y-axis", title="Multiple Linear Regression Plot")
	"""
	fig, ax = plt.subplots(**kwargs.get('fig_kws', {})) if ax is None else (ax.get_figure(), ax)

	if not isinstance(x, list):
		x = [x]

	if not isinstance(y, str):
		y = y[0]

	if labels is None:
		labels = x

	df = df[[*x, y]].dropna()
	x_array = df[[*x]].to_numpy()
	y_array = df[[y]].to_numpy()

	text, y_predict, coefficients = _linear_regression(x_array, y_array,
													   columns=labels,
													   positive=positive,
													   fit_intercept=fit_intercept)

	df = pd.DataFrame(np.concatenate([y_array, y_predict], axis=1), columns=['y_actual', 'y_predict'])

	linear_regression(df, x='y_actual', y='y_predict', ax=ax, regression=True, diagonal=diagonal)

	return fig, ax
