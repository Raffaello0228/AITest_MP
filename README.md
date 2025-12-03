## 项目说明（README）

### 一、项目目的

本项目用于将历史投放数据（`data.csv`）和广告类型映射表（`adtype_dict.csv`）自动转换为媒体计划接口所需的 JSON 结构，格式参考 `brief_template.json` / `brief_template_structure.md`。  
核心脚本为：`csv_to_brief_template.py`。

---

### 二、输入文件说明

- **`data.csv`**：历史投放明细数据  
  - 关键字段（示例）：  
    - `country_code`：国家/区域代码（如 `US`、`GB`、`FR` 等）  
    - `channel_id`：渠道 ID（1=Meta，3=Google，18=TikTok 等，脚本内有映射）  
    - `media_channel`：平台（如 `FB&IG`、`FB`、`IG`、`YTB`、`GG`、`TT`，可为空）  
    - `ad_type`：广告类型名称（需能在 `adtype_dict.csv` 中找到）  
    - `month_`：年月，用于生成阶段（stage），格式类似 `202503`  
    - `spend`：花费  
    - `impressions` / `clicks` / `link_clicks` / `video_views` / `engagements` / `likes` / `purchases` / `follows` 等 KPI 字段  

- **`adtype_dict.csv`**：广告类型映射表  
  - 关键字段：`Media`、`Platform`、`Marketing Funnel`、`Objective`、`Ad Type`、`Media Buy Type`、`Key Measurement`  
  - 用于从 `ad_type` 反推：所属媒体（Meta/Google/TikTok）、平台、营销漏斗等。

- **`brief_template.json`**：JSON 模板  
  - 提供整体结构和默认配置（`basicInfo`、`moduleConfig`、预算校验配置等），脚本会在其基础上填充数据。

---

### 三、输出文件

- **`brief_from_data.json`**  
  - 结构与 `brief_template.json` 一致，主要包含：
    - `basicInfo`  
      - `totalBudget`：所有数据行 `spend` 之和  
      - `kpiInfo`：按全量数据聚合 8 个 KPI（Impression / Clicks / LinkClicks / VideoViews / Engagement / Followers / Like / Purchase）  
      - `regionBudget`：按 `country_code` 聚合的区域预算与 KPI  
      - 其他字段从模板继承，仅替换必要字段（如 `uuid`、`totalBudget`、`regionBudget`）
    - `briefMultiConfig`：按国家/区域拆分后的详细配置数组  
      - `country`：`code` + `groupName`  
      - `stage`：使用 `month_` 作为阶段名（每个月一个 stage）  
      - `marketingFunnel`：按 `Marketing Funnel` 聚合预算  
      - `media`：按媒体 + 平台聚合预算  
      - `mediaMarketingFunnelAdtype`：媒体-漏斗-广告类型层级的 KPI 汇总

---

### 四、核心脚本：`csv_to_brief_template.py`

#### 1. 主要逻辑

- **数据读取与清洗**
  - `load_data("data.csv")`  
    - 统一列名去空格  
    - 将 `\N` 视为缺失值  
    - 将花费与 KPI 列转为数值（非数值强制为 0）
  - `load_mapping("adtype_dict.csv")`  
    - 自动尝试 `utf-8` / `gbk` / `latin1` 编码读取，避免编码错误  
    - 去掉字段前后空格

- **媒体 / 平台 / 漏斗推断**
  - 通过 `infer_media`：
    - 根据 `channel_id`（1=Meta，3=Google，18=TikTok）  
    - 或 `media_channel`（`FB&IG`、`FB`、`IG`、`YTB`、`GG`、`TT`）  
    - 或 ad_type 在 `adtype_dict.csv` 中只属于单一媒体时兜底判断  
  - `attach_mapping` 合并映射表，生成：
    - `Media_final`：最终媒体名  
    - `Platform_final`：优先用 `data.csv` 里的 `media_channel`，为空再用映射表中的 `Platform`，并统一 `FBIGFB&IG` → `FB&IG`  
    - `Funnel_final`：对应的 `Marketing Funnel`

- **basicInfo 构建**
  - `build_basic_info(template_basic, merged_df)`：
    - 复制模板 `basicInfo` 作为基础  
    - `totalBudget` = 全量 `spend` 总和  
    - 聚合全局 8 个 KPI，按模板中的 `priority` 或默认顺序写入 `kpiInfo`  
    - `regionBudget`：按 `country_code` 聚合预算与 KPI，并设置 `country.code` / `groupName` / `budgetPercentage` / `budgetAmount`  
    - 生成新的 `uuid`

- **按国家构建 briefMultiConfig**
  - 使用模板第一个国家条目拷贝公共配置：
    - `moduleConfig`、`stageBudgetConfig`、`marketingFunnelBudgetConfig`、`mediaBudgetConfig`、`mediaMarketingFunnelAdtypeBudgetConfig`
  - 每个国家：
    - `stage`：`build_country_stage`  
      - 按 `month_` 分组  
      - 每个 `month_` 为一个 stage，`name`=month 字符串（如 `202503`）  
      - `budgetAmount` 为当月该国家 `spend` 总和  
      - `budgetPercentage` 为当月花费在该国家总花费中的占比  
      - `dates` / `marketingFunnel` / `mediaPlatform` 暂为 `None`
    - `marketingFunnel`：`build_country_marketing_funnel`  
      - 按 `Funnel_final` 聚合预算  
    - `media`：`build_country_media`  
      - 外层按 `Media_final` 聚合  
      - 内层 `children` 按 `Platform_final` 聚合
    - `mediaMarketingFunnelAdtype`：`build_country_media_marketing_adtype`  
      - 按 `(Media_final, Funnel_final, ad_type, Platform_final)` 聚合预算与 KPI  
      - 为每个组合生成 `kpiInfo`（8 个 KPI），`completion=0`

- **区域数量控制**
  - 顶部有全局变量：

```python
MAX_REGION_COUNT: int | None = None
```

  - 在 `convert(...)` 中有参数 `max_regions: int | None = None`  
  - 实际使用逻辑：
    - 若调用 `convert(max_regions=5)`，则按国家 `spend` 降序仅保留前 5 个国家  
    - 若不传入参数，则使用全局 `MAX_REGION_COUNT` 的值  
    - 二者都为 `None` 时不过滤，保留所有有花费的国家。

---

### 五、使用方法

#### 1. 环境依赖

- Python 3.9+（建议）
- 依赖库：
  - `pandas`
  - `numpy`

安装命令示例：

```bash
pip install pandas numpy
```

#### 2. 放置文件

在项目根目录（`mediaplan`）下保证存在：

- `data.csv`
- `adtype_dict.csv`
- `brief_template.json`
- `csv_to_brief_template.py`

#### 3. 运行脚本

在项目根目录执行：

```bash
python csv_to_brief_template.py
```

默认行为：

- 按所有国家生成 JSON
- 输出文件：`brief_from_data.json`

如需限制区域数量（例如只保留前 5 个国家）：

- 方法一：直接修改脚本最后一行：

```python
if __name__ == "__main__":
    convert(max_regions=5)
```

- 方法二：设置全局变量：

```python
MAX_REGION_COUNT = 5
if __name__ == "__main__":
    convert()
```

---

### 六、注意事项

- `data.csv` 中 `ad_type` 必须能在 `adtype_dict.csv` 中找到对应行，否则该行在合并后会缺少漏斗等信息，部分聚合结果会变少。  
- `month_` 必须存在且为类似 `YYYYMM` 的字符串，才能按月生成阶段；缺失时会退化为单一 “All” 阶段。  
- 如果有新增媒体或广告类型，需要先在 `adtype_dict.csv` 中补充映射配置。  
- 如需调整 KPI 口径或补充更多 KPI 字段，可在 `KPI_KEYS` 和各 `build_*` 函数中扩展。


