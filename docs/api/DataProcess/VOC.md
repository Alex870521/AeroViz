# VOC 模組

揮發性有機物數據處理模組。

## 結構

```
VOC/
├── __init__.py         # VOC (Writer 入口)
├── _potential_par.py   # 臭氧生成潛勢計算
└── support_voc.json    # VOC 物種參數表
```

---

## 快速開始

```python
from pathlib import Path
from AeroViz.dataProcess import DataProcess

dp = DataProcess('VOC', Path('./output'))
result = dp.potential(df_voc)
```

---

## 方法列表

| 方法 | 說明 | 相關理論 |
|------|------|----------|
| `potential(df_voc)` | OFP/SOAP 計算 | → [OFP/SOAP](../../theory/ofp.md) |

---

## 輸出說明

### potential

| 輸出 | 說明 |
|------|------|
| `OFP` | 各物種 OFP 貢獻 (μg O₃/m³) |
| `SOAP` | 各物種 SOAP 貢獻 |
| `total` | 總 OFP/SOAP |

---

## 計算指標

| 指標 | 全名 | 說明 |
|------|------|------|
| OFP | Ozone Formation Potential | 臭氧生成潛勢 |
| SOAP | Secondary Organic Aerosol Potential | 二次有機氣膠生成潛勢 |
| MIR | Maximum Incremental Reactivity | 最大增量反應性 |

---

## 輸入格式

```python
# 欄位為 VOC 物種名稱
df_voc.columns = ['Benzene', 'Toluene', 'Ethylbenzene', 'Xylene', ...]

# 單位: ppb 或 μg/m³
```

### 支援物種

詳見 `support_voc.json`：

- 烷烴 (Alkanes)
- 烯烴 (Alkenes)
- 芳香烴 (Aromatics)
- 鹵代烴 (Halocarbons)
- 含氧 VOC (OVOCs)

---

## 相關資源

- **範例**: [VOC 分析](../../guide/voc_analysis.md)
- **理論**: [OFP/SOAP](../../theory/ofp.md)

---

## API 參考

::: AeroViz.dataProcess.VOC.VOC
    options:
      show_root_heading: true
