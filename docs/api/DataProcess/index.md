# DataProcess

數據處理模組，提供氣膠數據的計算與分析功能。

## 模組結構

```
dataProcess/
├── Chemistry/    # 化學成分處理
├── Optical/      # 光學特性處理
├── SizeDistr/    # 粒徑分布處理
└── VOC/          # 揮發性有機物處理
```

## 快速開始

```python
from pathlib import Path
from AeroViz.dataProcess import DataProcess

# 使用工廠函數建立處理器
dp = DataProcess(
    method='SizeDistr',      # 'Chemistry', 'Optical', 'SizeDistr', 'VOC'
    path_out=Path('./output'),
    csv=True,
    excel=False
)

# 或直接導入類
from AeroViz.dataProcess.SizeDistr import SizeDist
from AeroViz.dataProcess.Chemistry import Chemistry
```

## 模組列表

| 模組 | 說明 | 文檔 |
|------|------|------|
| [SizeDistr](SizeDistr.md) | 粒徑分布處理 | SizeDist 類、SMPS-APS 合併 |
| [Chemistry](Chemistry.md) | 化學成分處理 | 質量重建、氣粒分配、折射率 |
| [Optical](Optical.md) | 光學特性處理 | IMPROVE、Mie、折射率反演 |
| [VOC](VOC.md) | VOC 處理 | 臭氧生成潛勢 |

## API 參考

::: AeroViz.dataProcess.DataProcess
