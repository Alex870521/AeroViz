# Optical 模組

光學特性數據處理模組。

## 結構

```
Optical/
├── __init__.py       # Optical (Writer 入口)
├── _IMPROVE.py       # IMPROVE 消光方程
├── _mie.py           # Mie 理論計算
├── _mie_sd.py        # Mie 粒徑分布計算
├── _retrieve_RI.py   # 折射率反演
├── _derived.py       # 衍生光學參數
├── mie_theory.py     # Mie 混合模式
└── coefficient.py    # 散射/吸收係數
```

---

## 快速開始

```python
from pathlib import Path
from AeroViz.dataProcess import DataProcess

dp = DataProcess('Optical', Path('./output'))
result = dp.IMPROVE(df_mass, df_RH, method='revised')
```

---

## 方法列表

| 方法 | 說明 | 相關理論 |
|------|------|----------|
| `basic(df_sca, df_abs)` | 基本消光特性 | - |
| `IMPROVE(df_mass, df_RH, method)` | IMPROVE 消光方程 | → [IMPROVE](../../theory/improve.md) |
| `gas_extinction(df_no2, df_temp)` | 氣體消光貢獻 | → [IMPROVE](../../theory/improve.md) |
| `Mie(df_pnsd, df_m, wave_length)` | Mie 消光計算 | → [Mie 理論](../../theory/mie.md) |
| `retrieve_RI(df_optical, df_pnsd)` | 折射率反演 | → [Mie 理論](../../theory/mie.md) |
| `derived(...)` | 衍生光學參數 | - |

---

## 輸出說明

### IMPROVE

| 輸出 | 說明 |
|------|------|
| `dry` | 乾燥消光 (AS_ext, AN_ext, OM_ext, Soil_ext, SS_ext, EC_ext, Total_ext) |
| `wet` | 濕消光 |
| `ALWC` | 液態水貢獻 (wet - dry) |
| `fRH` | 吸濕成長因子 |

### Mie

| 輸出 | 說明 |
|------|------|
| `extinction` | 消光係數 (Mm⁻¹) |
| `scattering` | 散射係數 (Mm⁻¹) |
| `absorption` | 吸收係數 (Mm⁻¹) |

### retrieve_RI

| 輸出 | 說明 |
|------|------|
| `n` | 實部 |
| `k` | 虛部 |

### derived

| 輸出 | 說明 |
|------|------|
| PG | 總消光 (Sca + Abs + Gas) |
| MAC | 質量吸收截面 (m²/g) |
| Ox | 氧化劑濃度 (NO₂ + O₃) |
| Vis_cal | 計算能見度 (km) |
| fRH_IMPR | IMPROVE fRH |
| OCEC_ratio | OC/EC 比值 |
| PM1_PM25 | PM1/PM2.5 比值 |

---

## Mie 混合模式

| 模式 | 說明 |
|------|------|
| `internal` | 內混合：體積加權平均折射率 |
| `external` | 外混合：分別計算後加總 |
| `core_shell` | 核殼結構：EC 核心 + 其他殼層 |
| `sensitivity` | 敏感度分析 |

---

## 輸入格式

### 散射係數

```python
df_sca.columns = ['G_550', 'R_700', 'B_450']  # 或 ['Sca_550']
```

### 吸收係數

```python
df_abs.columns = ['Abs_370', 'Abs_880', ...]  # Mm⁻¹
```

### 質量濃度（IMPROVE 用）

```python
required = ['AS', 'AN', 'OM', 'Soil', 'SS', 'EC']  # μg/m³
```

---

## 相關資源

- **範例**: [光學閉合分析](../../guide/optical_closure.md)
- **理論**: [IMPROVE 方程](../../theory/improve.md) | [Mie 理論](../../theory/mie.md)

---

## API 參考

::: AeroViz.dataProcess.Optical.Optical
    options:
      show_root_heading: true
