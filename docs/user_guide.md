## <div align="center">RawDataReader Usage</div>

```python
from datetime import datetime as dtm
from pathlib import Path
from AeroViz.rawDataReader import RawDataReader

# 設定資料的起始和結束時間
start, end = dtm(2024, 2, 1), dtm(2024, 7, 31)

# 設定資料路徑
path_raw = Path('/path/to/data')

# 讀取 AE33 資料
dt_ae33 = RawDataReader('AE33', path_raw / 'AE33', reset=False, start=start, end=end)

dt_neph = RawDataReader('NEPH', path_raw / 'NEPH', reset=False, start=start, end=end)
```

## <div align="center">DataProcess Usage</div>

```python
```

## <div align="center">AeroViz.plot Usage</div>

### <div align="center">WindRose and Conditional Bivariate Probability Function (CBPF)</div>

![WindRose](https://github.com/Alex870521/AeroViz/blob/main/assets/figure/windrose_CBPF.png?raw=true)

```python
from AeroViz import plot, DataBase

df = DataBase() # build default data, uers can use their own data

# wind rose
plot.meteorology.wind_rose(df, 'WS', 'WD', typ='bar')
plot.meteorology.wind_rose(df, 'WS', 'WD', 'PM25', typ='scatter')

plot.meteorology.CBPF(df, 'WS', 'WD', 'PM25')
plot.meteorology.CBPF(df, 'WS', 'WD', 'PM25', percentile=[75, 100])
```

### <div align="center">Linear Regression</div>

```python
from AeroViz import plot, DataBase
df = DataBase() # build default data, uers can use their own data

# regression
plot.linear_regression(df, x='PM25', y='Extinction')
plot.linear_regression(df, x='PM25', y=['Extinction', 'Scattering', 'Absorption'])

plot.multiple_linear_regression(df, x=['AS', 'AN', 'OM', 'EC', 'SS', 'Soil'], y=['Extinction'])
plot.multiple_linear_regression(df, x=['NO', 'NO2', 'CO', 'PM1'], y=['PM25'])


```

### <div align="center">Timeseries</div>

```python
from AeroViz import plot, DataBase
df = DataBase() # build default data, uers can use their own data

# timeseries
plot.timeseries.timeseries(df,
                           y=['Extinction', 'Scattering'],
                           c=[None, None],
                           style=['line', 'line'],
                           times=('2021-02-01', '2021-03-31'), ylim=[0, None], ylim2=[0, None], rolling=50,
                           inset_kws2=dict(bbox_to_anchor=(1.12, 0, 1.2, 1)))

plot.timeseries.timeseries(df, y='WS', c='WD', style='scatter', times=('2020-10-01', '2020-11-30'),
                           scatter_kws=dict(cmap='hsv'), cbar_kws=dict(ticks=[0, 90, 180, 270, 360]),
                           ylim=[0, None])

plot.timeseries.timeseries_template(df.loc['2021-02-01', '2021-03-31'])
```

### <div align="center">Particle Size Distribution</div>

> [!IMPORTANT]\
> The provided code of distribution suitable for SMPS and APS data in "dX/dlogdp" unit.
> It can be converted into surface area and volume distribution. At the same time,
> chemical composition data can also be used to calculate particle extinction through Mie theory.

![PNSD](https://github.com/Alex870521/AeroViz/blob/main/assets/figure/OverPSD.png?raw=true)

```python
from pathlib import Path
from AeroViz import plot
from AeroViz.tools import DataBase, DataReader

df = DataBase() # build default data, uers can use their own data

PNSD = DataReader(Path(__file__)/'AeroViz'/'config'/'DEFAULT_PNSD_DATA.csv')

plot.distribution.distribution.heatmap(PNSD, unit='Number')
plot.distribution.distribution.heatmap_tms(PNSD, unit='Number', freq='60d')
```

### <div align="center">For some basic plot</div>

|                                             **Three_dimension**                                             |                                            **Correlation Matrix**                                             |                                     **Mutiply Linear Regression**                                      |
|:-----------------------------------------------------------------------------------------------------------:|:-------------------------------------------------------------------------------------------------------------:|:------------------------------------------------------------------------------------------------------:|
|        ![PSD 3D](https://github.com/Alex870521/AeroViz/blob/main/assets/figure/psd_3D.png?raw=true)         | ![Correlation Matrix](https://github.com/Alex870521/AeroViz/blob/main/assets/figure/corr_matrix.png?raw=true) | ![IMPROVE MLR](https://github.com/Alex870521/AeroViz/blob/main/assets/figure/IMPROVE_MLR.png?raw=true) |
|                                               **Pie & Donut**                                               |                                                  **Dounts**                                                   |                                              **Scatter**                                               |
| ![IMPROVE donuts](https://github.com/Alex870521/AeroViz/blob/main/assets/figure/IMPROVE_donut.png?raw=true) |   ![IMPROVE bar](https://github.com/Alex870521/AeroViz/blob/main/assets/figure/IMPROVE_donuts.png?raw=true)   |     ![scatter](https://github.com/Alex870521/AeroViz/blob/main/assets/figure/scatter.png?raw=true)     |

### <div align="center">PyMieScatt</div>

|                                         **Mie_Q**                                          |                                          **Mie_MEE**                                           |
|:------------------------------------------------------------------------------------------:|:----------------------------------------------------------------------------------------------:|
| ![Mie Q](https://github.com/Alex870521/AeroViz/blob/main/assets/figure/Mie_Q.png?raw=true) | ![Mie MEE](https://github.com/Alex870521/AeroViz/blob/main/assets/figure/Mie_MEE.png?raw=true) |     |
