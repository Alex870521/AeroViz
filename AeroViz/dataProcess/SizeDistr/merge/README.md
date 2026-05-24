# SMPS-APS Merge Algorithms

本資料夾包含 SMPS 與 APS 粒徑分布合併演算法的各版本實現。

## 版本演進

> v0 / v0.1 已移除（死碼）。v0 是 v1 的嚴格子集；v0.1 的特色（APS 迭代校正、
> mobility+aerodynamic 雙輸出）已分別保留在 v2/v3/v4，故一併刪除。

| 版本 | 檔案 | 主要特點 |
|------|------|----------|
| v1 | `_merge_v1.py` | 基礎 power-law fit 合併 + `union_index` 對齊 + `shift_mode` (mobility/aerodynamic) |
| v2 | `_merge_v2.py` | APS 迭代校正 + mobility/aerodynamic 雙輸出，移除 qc_cond 過濾 |
| v3 | `_merge_v3.py` | 加入 multiprocessing 平行運算 + dN/dS/dV 演算法 |
| v4 | `_merge_v4.py` | 加入 PM2.5 fitness 函數 + SMPS times 校正 |

## 統一輸出與品質控制

所有版本都回傳 dict，並保證有兩個共通 key（存成 CSV 即 `data.csv` / `density.csv`，跨版本檔名一致）：

- **`data`**：建議使用的合併 dN/dlogDp（欄=直徑 nm）。v1＝單一 power-law 合併；v2＝mobility 合併；v3/v4＝APS 校正後的 dN/dS/dV（`cor_dndsdv`）。
- **`density`**：推估有效密度（g/cm³）。

品質控制統一用參數 **`density_range`（g/cm³，預設 `(0.6, 2.6)`）**：每個時間點的 `shift²` 即推估有效密度，超出範圍 → 該列遮成 NaN。放寬用 `(0.3, 2.6)`、收緊自訂。（取代舊 v1 的 `data_all`/`data_qc` 雙輸出。）

## 版本詳細說明

### v1 (基礎版本)
- 基本的 power law fitting 密度估算 + UnivariateSpline 重疊區平滑
- `union_index` 對齊 SMPS/APS 時間索引
- `shift_mode`：`'mobility'`（移 APS 到電移動度徑）/ `'aerodynamic'`（移 SMPS 到空氣動力徑）
- 輸出: `data`, `density`

### v2
- 固定 mobility + APS 校正迭代（2 次）
- 同時輸出 mobility 與 aerodynamic 兩種合併
- 輸出: `data`(mobility), `data_aero`, `density`

### v3
- 引入 multiprocessing 平行運算加速
- 新增 dN/dS/dV 相關性演算法 (`_corr_with_dNdSdV`)
- 同時計算四種演算法：`dn`(純 power-law) / `dndsdv` / `cor_dn`(APS 校正) / `cor_dndsdv`(校正+dNdSdV)
- 輸出: `data`(=cor_dndsdv), `data_dn`, `data_dndsdv`, `data_cor_dn`, `density`(4 欄)

### v4 (最新版本)
- v3 + PM2.5 質量約束 fitness 函數 + SMPS times 校正（`times_range` 搜尋最佳倍率，預設 0.8~1.25）
- 輸出: 同 v3 ＋ `times`（各演算法每個時間點選用的倍率）

## 使用方式

```python
from pathlib import Path
from AeroViz.dataProcess import DataProcess

dp = DataProcess('SizeDistr', Path('./output'))

# v1 (基本版)
result = dp.merge_SMPS_APS(df_smps, df_aps)

# v2
result = dp.merge_SMPS_APS_v2(df_smps, df_aps)

# v3 (含 dN/dS/dV 演算法)
result = dp.merge_SMPS_APS_v3(df_smps, df_aps, dndsdv_alg=True)

# v4 (含 PM2.5 校正，推薦)
result = dp.merge_SMPS_APS_v4(df_smps, df_aps, df_pm25)
```

## 演算法核心概念

### Power Law Fitting
利用 SMPS 上端粒徑的 power law 擬合（y = Ax^B），計算 APS 粒徑的位移因子（shift factor），用以估算有效密度。

### Shift Factor
位移因子的平方即為有效密度估計值：
- ρ_eff = shift_factor²
- 合理範圍: 0.6 ~ 2.6 g/cm³

### dN/dS/dV 相關性
v3+ 版本加入的演算法，同時考慮：
- dN/dlogDp (數量分布)
- dS/dlogDp (表面積分布)
- dV/dlogDp (體積分布)

通過最大化三者的相關性來決定最佳位移因子。
