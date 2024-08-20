import numpy as np
import pandas as pd

from AeroViz.plot import scatter

# Set random seed to ensure reproducibility
np.random.seed(0)

# Example 1: Basic Scatter Plot
print("Example 1: Basic Scatter Plot")
df = pd.DataFrame({
    'x': np.random.rand(50),
    'y': np.random.rand(50)
})

fig, ax = scatter(df, x='x', y='y', title='Basic Scatter Plot')
fig.savefig('basic_scatter_plot.png')
print("Basic scatter plot saved as 'basic_scatter_plot.png'")

# Example 2: Scatter Plot with Color and Size Encoding
print("\nExample 2: Scatter Plot with Color and Size Encoding")
df['color'] = np.random.rand(50)
df['size'] = np.random.randint(10, 100, 50)

fig, ax = scatter(df, x='x', y='y', c='color', s='size', fig_kws={'figsize': (5, 4)},
                  title='Scatter Plot with Color and Size Encoding')
fig.savefig('color_size_scatter_plot.png')
print("Scatter plot with color and size encoding saved as 'color_size_scatter_plot.png'")

# Example 3: Scatter Plot with Regression Line and Diagonal
print("\nExample 3: Scatter Plot with Regression Line and Diagonal")
df = pd.DataFrame({
    'x': np.arange(0, 10, 0.2),
    'y': np.arange(0, 10, 0.2) + np.random.normal(0, 1, 50)
})

fig, ax = scatter(df, x='x', y='y', regression=True, diagonal=True,
                  title='Scatter Plot with Regression and Diagonal Lines')
fig.savefig('regression_diagonal_scatter_plot.png')
print("Scatter plot with regression and diagonal lines saved as 'regression_diagonal_scatter_plot.png'")

print("\nAll example plots have been generated. Please check the PNG files in the current directory.")

# Additional usage instructions
print("\nUsage Instructions:")
print("1. Ensure that the AeroViz library is installed.")
print("2. Run this script to generate all example plots.")
print("3. View the generated PNG files to see different types of scatter plots.")
print("4. You can modify the parameters in this script to customize your own scatter plots.")
