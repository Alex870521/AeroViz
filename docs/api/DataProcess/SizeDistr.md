# SizeDistr 模組

粒徑分布數據處理模組。

## 結構

```
SizeDistr/
├── __init__.py      # SizeDistr (Writer 入口)
├── _size_dist.py    # SizeDist 核心類
├── prop.py          # 統計計算函數
└── merge/           # SMPS-APS 合併演算法 (v0-v4)
```

---

## 快速開始

```python
from AeroViz.dataProcess.SizeDistr import SizeDist

psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')
surface = psd.to_surface()
volume = psd.to_volume()
props = psd.properties()
```

---

## SizeDist 類

### 屬性

| 屬性 | 類型 | 說明 |
|------|------|------|
| `data` | DataFrame | 原始數據 |
| `dp` | ndarray | 粒徑陣列 (nm) |
| `dlogdp` | ndarray | 對數間距 |
| `index` | DatetimeIndex | 時間索引 |
| `state` | str | 'dN', 'ddp', 'dlogdp' |
| `weighting` | str | 'n', 's', 'v', 'ext_in', 'ext_ex' |

### 方法

| 方法 | 說明 | 相關理論 |
|------|------|----------|
| `to_surface()` | 轉換為表面積分布 | → [對數常態分布](../../theory/lognormal.md) |
| `to_volume()` | 轉換為體積分布 | → [對數常態分布](../../theory/lognormal.md) |
| `to_extinction()` | Mie 消光計算 | → [Mie 理論](../../theory/mie.md) |
| `to_dry()` | 乾燥 PSD (吸濕校正) | → [κ-Köhler](../../theory/kappa.md) |
| `properties()` | 統計屬性 (GMD, GSD) | → [對數常態分布](../../theory/lognormal.md) |
| `mode_statistics()` | 模態統計 | → [對數常態分布](../../theory/lognormal.md) |
| `lung_deposition()` | 肺沉積計算 | → [ICRP 66](../../theory/icrp.md) |

### 模態定義

| 模態 | 粒徑範圍 |
|------|----------|
| Nucleation | 10-25 nm |
| Aitken | 25-100 nm |
| Accumulation | 100-1000 nm |
| Coarse | 1000-2500 nm |

---

## SizeDistr 入口類

```python
from pathlib import Path
from AeroViz.dataProcess import DataProcess

dp = DataProcess('SizeDistr', Path('./output'))
```

### 方法

| 方法 | 說明 |
|------|------|
| `basic(df)` | 基本處理 (number/surface/volume) |
| `merge_SMPS_APS(df_smps, df_aps)` | SMPS-APS 合併 (v1) |
| `merge_SMPS_APS_v4(df_smps, df_aps, df_pm25)` | SMPS-APS 合併 (v4, 推薦) |
| `distributions(df_pnsd)` | 分布計算 |
| `dry_psd(df_pnsd, df_gRH)` | 乾燥 PSD |
| `extinction_distribution(df_pnsd, df_RI)` | 消光分布 |

---

## SMPS-APS 合併演算法

| 版本 | 特點 |
|------|------|
| v0 | 原始版本 |
| v0.1 | 加入索引對齊 |
| v1 | 加入 shift_mode |
| v2 | 簡化輸出 |
| v3 | multiprocessing + dN/dS/dV |
| v4 | PM2.5 fitness 校正 (推薦) |

---

## 輸入格式

```python
# DataFrame 欄位為粒徑值 (nm)
df_pnsd.columns = [11.8, 13.6, 15.7, ..., 523.3]
df_pnsd.index = DatetimeIndex

# 成長因子
df_gRH = DataFrame({'gRH': [1.2, 1.3, ...]}, index=time_index)
```

---

## 相關資源

- **範例**: [粒徑分布分析](../../guide/size_distribution.md)
- **理論**: [對數常態分布](../../theory/lognormal.md) | [ICRP 66](../../theory/icrp.md) | [Mie 理論](../../theory/mie.md)

---

## API 參考

::: AeroViz.dataProcess.SizeDistr.SizeDist
    options:
      show_root_heading: true
      members:
        - to_surface
        - to_volume
        - to_extinction
        - to_dry
        - properties
        - mode_statistics
        - lung_deposition
