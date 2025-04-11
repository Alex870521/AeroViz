# AeroViz

AeroViz 是一個用於氣溶膠數據處理和可視化的 Python 庫。

## 功能特點

- 支持多種氣溶膠儀器的數據讀取
- 自動化的數據質量控制
- 豐富的數據可視化功能
- 靈活的數據處理流程

## 快速開始

1. 安裝 AeroViz：

```bash
pip install aeroviz
```

2. 導入並使用：

```python
from AeroViz import RawDataReader

# 創建讀取器實例
reader = RawDataReader()

# 讀取數據
data = reader.read("path/to/data.txt")
```

## 文檔

- [用戶指南](guide/getting-started.md)
- [API 參考](api/index.md)
- [儀器概述](instruments/instrument_overview.md)

## 示例

查看我們的示例代碼：

- [數據讀取示例](example/RawDataReader.py)
- [繪圖示例](example/scatter_examples.py)

## 開發

AeroViz 是一個開源項目，歡迎貢獻代碼和提出建議。
