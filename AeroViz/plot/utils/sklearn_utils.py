import numpy as np
from sklearn.linear_model import LinearRegression
from tabulate import tabulate

__all__ = ['linear_regression_base']


def linear_regression_base(x_array: np.ndarray,
                           y_array: np.ndarray,
                           columns: str | list[str] | None = None,
                           positive: bool = True,
                           fit_intercept: bool = True):
    if len(x_array.shape) > 1 and x_array.shape[1] >= 2:
        model = LinearRegression(positive=positive, fit_intercept=fit_intercept).fit(x_array, y_array)

        coefficients = model.coef_[0].round(3)
        intercept = model.intercept_[0].round(3) if fit_intercept else 'None'
        r_square = model.score(x_array, y_array).__round__(3)
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
        r_square = model.score(x_array, y_array).__round__(3)
        y_predict = model.predict(x_array)

        text = np.poly1d([slope, intercept])
        text = 'y = ' + str(text).replace('\n', "") + '\n' + r'$\bf R^2 = $' + str(r_square)

        tab = tabulate([[slope, intercept, r_square]], headers=['slope', 'intercept', 'R^2'], floatfmt=".3f",
                       tablefmt="fancy_grid")
        print('\n' + tab)

        return text, y_predict, slope
