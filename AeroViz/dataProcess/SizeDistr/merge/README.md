# SMPS-APS Merge Algorithms

本資料夾包含 SMPS 與 APS 粒徑分布合併演算法的各版本實現。

## 版本演進

| 版本 | 檔案 | 主要特點 |
|------|------|----------|
| v0 | `_merge_v0.py` | 最原始版本，無 `union_index` 索引對齊 |
| v0.1 | `_merge_v0_1.py` | 加入 `union_index` 索引對齊功能 |
| v1 | `_merge_v1.py` | 加入 `shift_mode` 參數 (mobility/aerodynamic) |
| v2 | `_merge_v2.py` | 簡化輸出，移除 qc_cond 過濾 |
| v3 | `_merge_v3.py` | 加入 multiprocessing 平行運算 + dN/dS/dV 演算法 |
| v4 | `_merge_v4.py` | 加入 PM2.5 fitness 函數 + SMPS times 校正 |

## 版本詳細說明

### v0 (原始版本)
- 基本的 power law fitting 密度估算
- 使用 UnivariateSpline 進行重疊區域平滑
- rho 閾值: 0.3 < ρ² < 2.0
- 輸出: `data_all`, `data_qc`, `density_all`, `density_qc`

### v0.1
- 加入 `union_index` 確保 SMPS 與 APS 時間索引對齊
- 導出函數名稱改為 `merge_SMPS_APS`（無底線前綴）

### v1
- 加入 `shift_mode` 參數，支援：
  - `'mobility'`: 移動 APS 粒徑到 mobility diameter
  - `'aerodynamic'`: 移動 SMPS 粒徑到 aerodynamic diameter
- rho 閾值放寬: 0.3 < ρ² < 2.6

### v2
- 移除 `shift_mode` 參數（固定使用 mobility）
- 簡化輸出結構，移除 `_qc` 過濾版本
- 加入 APS 校正迭代（2次）
- 輸出: `data_all`, `data_all_aer`, `density_all`

### v3
- 引入 multiprocessing 平行運算加速
- 新增 dN/dS/dV 相關性演算法 (`_corr_with_dNdSdV`)
- 同時計算多種演算法結果：
  - `dn`: 純 power law fitting
  - `dndsdv`: dN/dS/dV 相關性
  - `cor_dn`: APS 校正後的 power law
  - `cor_dndsdv`: APS 校正後的 dN/dS/dV
- 輸出: `data_dn`, `data_dndsdv`, `data_cor_dn`, `data_cor_dndsdv`, `density`

### v4 (最新版本)
- 加入 PM2.5 質量約束的 fitness 函數
- 引入 SMPS times 校正因子（搜尋最佳倍率）
- 參數 `times_range`: SMPS 數據乘數範圍 (預設 0.8~1.25)
- 輸出新增 `times` 欄位記錄各時間點的最佳校正倍率

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
