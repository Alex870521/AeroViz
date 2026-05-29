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
from AeroViz import voc_potentials

result = voc_potentials(df_voc)   # df_voc: 物種為欄、datetime index 的 DataFrame
```

!!! note "API 更新"
    舊的 `DataProcess('VOC', ...).VOC_basic(df_voc)` 已**棄用**,改用頂層函式
    `voc_potentials(df_voc)`(`AeroViz.voc` 命名空間下亦同)。它會以
    `support_voc.json` 驗證每個物種欄名(未知物種直接 raise)。

---

## 方法列表

| 函式 | 說明 | 相關理論 |
|------|------|----------|
| `voc_potentials(df_voc)` | OFP / SOAP / LOH 計算 | → [OFP/SOAP](../../theory/ofp.md) |

---

## 輸出說明

`voc_potentials` 回傳一個 dict,含四個 time-indexed DataFrame;每個 frame 的欄位
為個別物種 + 各分類小計(`*_total`,如 `alkane_total`)+ 總計 `Total`:

| key | 說明 |
|------|------|
| `Conc` | 質量濃度 (μg/m³) |
| `OFP` | 臭氧生成潛勢 (μg O₃/m³) |
| `SOAP` | 二次有機氣膠生成潛勢 |
| `LOH` | OH 反應性 (loss rate) |

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
