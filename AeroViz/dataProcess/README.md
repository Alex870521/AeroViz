# AeroViz DataProcess Module

數據處理模組，提供氣膠數據的計算與分析功能。

## 模組結構

```
dataProcess/
├── __init__.py      # DataProcess 工廠函數
├── core/            # 共用工具 (Writer, run_process, validate_inputs)
├── Chemistry/       # 化學成分處理
├── Optical/         # 光學特性處理
├── SizeDistr/       # 粒徑分布處理
└── VOC/             # 揮發性有機物處理
```

## 快速開始

```python
from pathlib import Path
from AeroViz.dataProcess import DataProcess

# 建立處理器
dp = DataProcess(method='SizeDistr', path_out=Path('./output'))

# 或直接導入類
from AeroViz.dataProcess.SizeDistr import SizeDist
```

---

## SizeDistr 模組

粒徑分布數據處理。

### 結構
```
SizeDistr/
├── __init__.py      # SizeDistr (Writer 入口)
├── _size_dist.py    # SizeDist 核心類
├── prop.py          # 統計計算函數
└── merge/           # SMPS-APS 合併演算法 (v0-v4)
```

### SizeDist 類

```python
from AeroViz.dataProcess.SizeDistr import SizeDist

# 建立物件
psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')

# 屬性
psd.data       # DataFrame - 原始數據
psd.dp         # ndarray - 粒徑陣列 (nm)
psd.dlogdp     # ndarray - 對數間距
psd.index      # DatetimeIndex - 時間索引

# 分布轉換
psd.to_surface()           # 表面積分布 (dS/dlogDp)
psd.to_volume()            # 體積分布 (dV/dlogDp)
psd.to_extinction(df_RI)   # 消光分布 (Mie 理論)
psd.to_dry(df_gRH)         # 乾燥分布 (吸濕校正)

# 統計計算
psd.properties()           # GMD, GSD, mode, contribution
psd.mode_statistics()      # 各模態統計 (Nucleation/Aitken/Accumulation/Coarse)

# 應用
psd.lung_deposition()      # ICRP 66 肺沉積模型
```

### SizeDistr 入口方法

```python
dp = DataProcess('SizeDistr', Path('./output'))

# 基本處理
dp.basic(df)

# SMPS-APS 合併
dp.merge_SMPS_APS(df_smps, df_aps)           # v1
dp.merge_SMPS_APS_v2(df_smps, df_aps)        # v2
dp.merge_SMPS_APS_v3(df_smps, df_aps)        # v3 (multiprocessing)
dp.merge_SMPS_APS_v4(df_smps, df_aps, df_pm25)  # v4 (PM2.5 校正)

# 分布計算
dp.distributions(df_pnsd)
dp.dry_psd(df_pnsd, df_gRH)
dp.extinction_distribution(df_pnsd, df_RI)
dp.extinction_full(df_pnsd, df_RI)
```

---

## Chemistry 模組

化學成分數據處理。

### 結構
```
Chemistry/
├── __init__.py       # Chemistry (Writer 入口)
├── _mass_volume.py   # 質量重建、體積計算、折射率
├── _calculate.py     # 衍生參數、氣粒分配比
├── _ocec.py          # OC/EC 比值計算
└── _isoropia.py      # ISORROPIA 熱力學模型
```

### Chemistry 入口方法

```python
dp = DataProcess('Chemistry', Path('./output'))

# 質量重建
dp.reconstruction_basic(df_chem)   # 基本重建 (AS, AN, OM, Soil, SS, EC)
dp.reconstruction_full(df_chem)    # 完整重建 (含 ite,ite_ox)

# 體積與折射率
dp.volume_RI(df_chem)              # 體積分率 + 折射率計算
dp.kappa(df_chem, df_RH)           # κ-Köhler 吸濕參數

# 衍生參數
dp.derived(df_chem)                # 衍生化學參數
dp.partition_ratios(df_chem)       # 氣粒分配比 (SOR, NOR, NTR, epsilon)

# OC/EC
dp.ocec_ratio(df_ocec)             # OC/EC 比值分析

# ISORROPIA
dp.ISORROPIA(df_chem)              # 熱力學平衡計算
```

### 輸出欄位說明

**質量重建:**
| 欄位 | 說明 |
|------|------|
| AS | 硫酸銨 (μg/m³) |
| AN | 硝酸銨 (μg/m³) |
| OM | 有機物 (μg/m³) |
| Soil | 土壤塵 (μg/m³) |
| SS | 海鹽 (μg/m³) |
| EC | 元素碳 (μg/m³) |
| PM25_rc | 重建 PM2.5 (μg/m³) |

**氣粒分配比:**
| 欄位 | 說明 |
|------|------|
| SOR | 硫氧化比 SO₄²⁻/(SO₄²⁻+SO₂) |
| NOR | 氮氧化比 NO₃⁻/(NO₃⁻+NO₂) |
| epsilon_ite | 硝酸鹽分配係數 |

---

## Optical 模組

光學特性數據處理。

### 結構
```
Optical/
├── __init__.py       # Optical (Writer 入口)
├── _IMPROVE.py       # IMPROVE 消光方程
├── _mie.py           # Mie 理論計算
├── _retrieve_RI.py   # 折射率反演
├── _derived.py       # 衍生光學參數
├── mie_theory.py     # Mie 混合模式
└── coefficient.py    # 散射/吸收係數
```

### Optical 入口方法

```python
dp = DataProcess('Optical', Path('./output'))

# 消光計算
dp.basic(df_sca, df_abs)                    # 基本消光特性
dp.IMPROVE(df_mass, df_RH)                  # IMPROVE 方程 (revised/modified)
dp.gas_extinction(df_no2, df_temp)          # 氣體消光貢獻

# Mie 計算
dp.Mie(df_psd, df_m)                        # Mie 理論消光

# 折射率反演
dp.retrieve_RI(df_optical, df_pnsd)         # 從光學+PSD 反演折射率

# 衍生參數
dp.derived(df_sca, df_abs, ...)             # PG, MAC, Ox, 能見度等
```

### IMPROVE 輸出

```python
result = dp.IMPROVE(df_mass, df_RH, method='revised')

result['dry']    # 乾燥消光 DataFrame
result['wet']    # 濕消光 DataFrame (含 ALWC)
result['ALWC']   # 液態水貢獻
result['fRH']    # 吸濕成長因子
```

---

## VOC 模組

揮發性有機物數據處理。

### VOC 入口方法

```python
dp = DataProcess('VOC', Path('./output'))

dp.potential(df_voc)   # 臭氧生成潛勢 (OFP, SOAP)
```

---

## 共用功能

### Writer 基類

所有處理模組繼承自 `Writer`，提供：
- 自動輸出 CSV/Excel
- 處理進度顯示
- 錯誤處理

### run_process 裝飾器

```python
@run_process('處理名稱', '輸出檔名')
def method(self, ...):
    ...
    return self, output_data
```

### validate_inputs 驗證器

```python
from AeroViz.dataProcess.core import validate_inputs

validate_inputs(df, ['SO42-', 'NO3-'], 'Chemistry', COLUMN_DESCRIPTIONS)
```

---

## 資料格式要求

### 通用格式
- **Index**: `DatetimeIndex` (時間索引)
- **Columns**: 依模組需求

### SizeDist 格式
```python
# 欄位為粒徑值 (nm)
df.columns = [11.8, 13.6, 15.7, ..., 523.3]
```

### Chemistry 格式
```python
# 化學成分欄位
required = ['SO42-', 'NO3-', 'Cl-', 'Na+', 'NH4+', 'K+', 'Mg2+', 'Ca2+',
            'OC', 'EC', 'Al', 'Fe', 'Ti', 'PM25']
```

### Optical 格式
```python
# 散射/吸收係數
df_sca.columns = ['G_550', 'R_700', 'B_450']  # Mm⁻¹
df_abs.columns = ['Abs_880']  # Mm⁻¹
```
