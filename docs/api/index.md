# API 參考

本節提供 AeroViz 的 API 參考文檔。

## 核心模塊

### RawDataReader

用於讀取原始數據的模塊。

- [RawDataReader 指南](../guide/RawDataReader.md)
- [數據處理指南](../guide/DataProcess.md)
- [繪圖指南](../guide/plot.md)

### 儀器支持

AeroViz 支持多種儀器的數據讀取：

- [AE33](../instruments/AE33.md)
- [AE43](../instruments/AE43.md)
- [BC1054](../instruments/BC1054.md)
- [MA350](../instruments/MA350.md)

## 使用示例

```python
from AeroViz.rawDataReader import RawDataReader

# 創建讀取器實例
reader = RawDataReader()

# 讀取數據
data = reader.read("path/to/data.txt")
```

## 注意事項

- 所有時間序列數據都使用 pandas 的 DatetimeIndex
- 數據質量控制參數可以在配置文件中設置
- 支持自定義數據處理流程

### DataProcess

Class for advanced data processing and analysis.

```python
from AeroViz import DataProcess

processor = DataProcess(data)
processed_data = processor.process()
```

[View DataProcess Documentation](../guide/DataProcess.md)

### plot

Module for creating publication-quality visualizations.

```python
from AeroViz import plot

plot.time_series(data, 'BC')
plot.scatter(data, 'BC', 'PM2.5')
```

[View Plot Documentation](../guide/plot.md)

## Common Parameters

### Time Range Parameters

- `start` (datetime): Start time for data processing
- `end` (datetime): End time for data processing
- `mean_freq` (str): Time frequency for averaging (e.g., '1h', '1D')

### Data Processing Parameters

- `qc` (str): Quality control level ('1MS', '1D', '1W')
- `reset` (bool): Whether to reset previous processing

### Plot Parameters

- `variables` (list): Variables to plot
- `title` (str): Plot title
- `figsize` (tuple): Figure size
- `style` (str): Plot style

## Return Values

### RawDataReader

Returns a pandas DataFrame containing:

- Timestamp index
- Instrument-specific measurements
- Quality control flags
- Metadata

### DataProcess

Returns a processed DataFrame with:

- Cleaned data
- Transformed values
- Statistical summaries
- Quality metrics

### plot

Returns matplotlib figure objects that can be:

- Displayed directly
- Saved to files
- Further customized 