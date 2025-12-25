# Chemistry 模組

化學成分數據處理模組。

## 結構

```
Chemistry/
├── __init__.py       # Chemistry (Writer 入口)
├── _mass_volume.py   # 質量重建、體積計算、折射率
├── _calculate.py     # 衍生參數、氣粒分配比
├── _ocec.py          # OC/EC 比值計算
└── _isoropia.py      # ISORROPIA 熱力學模型
```

---

## 快速開始

```python
from pathlib import Path
from AeroViz.dataProcess import DataProcess

dp = DataProcess('Chemistry', Path('./output'))
result = dp.reconstruction_basic(df_chem)
```

---

## 方法列表

| 方法 | 說明 | 相關理論 |
|------|------|----------|
| `reconstruction_basic(df)` | 基本質量重建 | → [質量重建](../../theory/mass_reconstruction.md) |
| `reconstruction_full(df)` | 完整質量重建 (含 ite) | → [質量重建](../../theory/mass_reconstruction.md) |
| `volume_RI(df)` | 體積分率與折射率 | → [Mie 理論](../../theory/mie.md) |
| `kappa(df, df_RH)` | κ 吸濕參數 | → [κ-Köhler](../../theory/kappa.md) |
| `derived(df)` | 衍生化學參數 | - |
| `partition_ratios(df)` | 氣粒分配比 (SOR, NOR) | - |
| `ocec_ratio(df)` | OC/EC 比值分析 | - |
| `ISORROPIA(df)` | 熱力學平衡計算 | - |

---

## 輸出說明

### reconstruction_basic

| 輸出 | 欄位 |
|------|------|
| `mass` | AS, AN, OM, EC, Soil, SS, PM25_rc |
| `NH4_status` | Excess / Balance / Deficiency |

### volume_RI

| 輸出 | 欄位 |
|------|------|
| `volume` | {species}_volume |
| `RI` | n, k |

### kappa

| 輸出 | 說明 |
|------|------|
| `kappa` | κ 值 |
| `gRH` | 成長因子 |

### partition_ratios

| 輸出 | 公式 |
|------|------|
| SOR | SO₄²⁻/(SO₄²⁻+SO₂) |
| NOR | NO₃⁻/(NO₃⁻+NO₂) |
| NTR | NO₃⁻/(NO₃⁻+HNO₃) |
| epsilon_ite | NO₃⁻/(NO₃⁻+Cl⁻) |
| epsilon_ss | Cl⁻/(NO₃⁻+Cl⁻) |

---

## 輸入格式

### 基本化學成分

```python
required_columns = [
    'SO42-', 'NO3-', 'Cl-', 'Na+', 'NH4+', 'K+', 'Mg2+', 'Ca2+',
    'OC', 'EC', 'Al', 'Fe', 'Ti', 'PM25'
]
```

### 氣體成分（氣粒分配用）

```python
gas_columns = ['SO2', 'NO2', 'HNO3', 'NH3']  # ppb 或 μg/m³
```

---

## 相關資源

- **範例**: [化學成分分析](../../guide/chemical_analysis.md)
- **理論**: [質量重建](../../theory/mass_reconstruction.md) | [κ-Köhler](../../theory/kappa.md)

---

## API 參考

::: AeroViz.dataProcess.Chemistry.Chemistry
    options:
      show_root_heading: true
