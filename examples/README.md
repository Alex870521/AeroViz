# AeroViz Examples

本資料夾包含 AeroViz 的使用範例。
This folder contains runnable AeroViz usage examples.

## 範例列表 / Example list

| 檔案 / File | 說明 / Description | `--demo` |
|------|------|:---:|
| `01_basic_reading.py` | 基本儀器數據讀取 / Basic instrument data reading | ✅ |
| `02_multiple_instruments.py` | 多儀器數據整合 / Combining multiple instruments | |
| `03_quality_control.py` | 品質控制設定 / Quality-control options | |
| `04_size_distribution.py` | 粒徑分布處理 / Size-distribution processing | ✅ |
| `05_chemical_analysis.py` | 化學成分分析 / Chemical-composition analysis | |
| `06_optical_properties.py` | 光學特性計算 / Optical-property calculations | |
| `07_plotting.py` | 視覺化繪圖 / Plotting | ✅ |

## 執行範例 / Running the examples

Most examples read raw instrument files, so they need a data directory.
大部分範例會讀取原始儀器檔案，需要先指定資料夾。

**1. With your own data / 使用你自己的資料**

Edit the `DATA_PATH` near the top of the file to point at your data directory,
then uncomment the call(s) you want in the `if __name__ == '__main__':` block:

編輯檔案頂端的 `DATA_PATH`，指向你的資料夾，再取消註解 `__main__` 內要執行的呼叫：

```bash
python examples/01_basic_reading.py
```

**2. Synthetic demo — no data files needed / 合成資料 demo（不需要資料檔）**

Examples marked `--demo` above can run on synthetic data with no setup:

標示 `--demo` 的範例可直接用合成資料執行，無須任何設定：

```bash
python examples/01_basic_reading.py --demo
python examples/04_size_distribution.py --demo
python examples/07_plotting.py            # 07 always uses synthetic data
```

## 支援儀器 / Supported instruments

### 黑碳/吸收 / Black carbon & absorption
- AE33, AE43, BC1054, MA350

### 散射 / Scattering
- NEPH, Aurora

### 粒徑分布 / Size distribution
- SMPS, APS, GRIMM

### 化學成分 / Chemical composition
- IGAC, OCEC, VOC

### 質量濃度 / Mass concentration
- TEOM, BAM1020

### 其他 / Other
- EPA, Minion
