# Xiaomi 版本 KPI 达成情况检查脚本说明

## 概述

`check_kpi_achievement_xiaomi.py` 是一个用于检查 Xiaomi 版本媒体计划结果是否满足测试用例要求的脚本。该脚本会从结果文件中提取数据，根据配置判断各项指标是否达成。

**重要特性**：
- ✅ 配置信息直接从结果文件（`result_json`）中提取，无需单独的测试用例文件
- ✅ 支持多维度检查：全局 KPI、阶段预算、营销漏斗预算、媒体预算、广告格式 KPI 和预算
- ✅ 支持完全匹配和大小关系匹配两种模式
- ✅ 自动生成测试报告（Markdown 和 HTML 格式）

## 使用方法

```bash
python core/check_kpi_achievement_xiaomi.py \
    --result-file output/xiaomi/results/mp_result_基准用例-完全匹配默认配置.json \
    --case-name "基准用例-完全匹配默认配置" \
    [--output <输出路径>]
```

### 参数说明

- `--result-file`：**必需**，结果 JSON 文件路径（包含 `data.result.briefInfo` 和 `data.result.dimensionMultiCountryResult`）
- `--case-name`：可选，测试用例名称（如果未提供，将从文件名中提取）
- `--output`：可选，输出文件路径（目录或文件路径）
- `--testcase-file`：已废弃，保留以兼容旧版本
- `--request-file`：已废弃，保留以兼容旧版本

## 数据结构

### 结果文件结构（Xiaomi 版本）

```json
{
  "uuid": "...",
  "job_id": "...",
  "data": {
    "result": {
      "briefInfo": {
        "basicInfo": {
          "uuid": "...",
          "jobId": "...",
          "kpiInfo": [
            {
              "key": "Impression",
              "val": "100000",
              "priority": 1,
              "completion": 0
            }
          ],
          "kpiInfoBudgetConfig": {
            "rangeMatch": 80
          },
          "moduleConfig": [
            {
              "moduleName": "kpiInfo",
              "priority": 1
            }
          ]
        },
        "briefMultiConfig": [
          {
            "countryInfo": {
              "countryCode": "ES"
            },
            "stage": [
              {
                "name": "EARLYBIRD",
                "budgetAmount": 12345,
                "budgetPercentage": 50
              }
            ],
            "marketingFunnel": [...],
            "media": [...],
            "mediaMarketingFunnelFormat": [
              {
                "mediaName": "Meta",
                "platform": ["FB&IG"],
                "adFormatWithKPI": [
                  {
                    "funnelName": "Awareness",
                    "adFormatName": "Image&Video Link Ads",
                    "creative": "Image&Video",
                    "kpiInfo": [...],
                    "adFormatTotalBudget": 1000
                  }
                ]
              }
            ],
            "mediaMarketingFunnelFormatBudgetConfig": {
              "totalBudgetFlexibility": 80
            },
            "stageBudgetConfig": {
              "rangeMatch": 20,
              "consistentMatch": 1
            },
            "marketingFunnelBudgetConfig": {
              "rangeMatch": 15,
              "consistentMatch": 1
            },
            "mediaBudgetConfig": {
              "rangeMatch": 5,
              "consistentMatch": 1
            }
          }
        ]
      },
      "dimensionMultiCountryResult": {
        "WE_ES": {
          "corporation": [
            {
              "country": "ES",
              "media": "Meta",
              "mediaChannel": "FB&IG",
              "stage": "EARLYBIRD",
              "marketingFunnel": "Awareness",
              "adFormat": "Image&Video Link Ads",
              "creative": "Image&Video",
              "totalBudget": 12345,
              "estImpression": {"value": "100000"},
              "estViews": {"value": "5000"},
              "estEngagement": {"value": "2000"},
              "estClicks": {"value": "1000"}
            }
          ]
        }
      }
    }
  }
}
```

### 关键字段说明

#### 结果数据路径

- **配置信息**：`data.result.briefInfo.basicInfo` 和 `data.result.briefInfo.briefMultiConfig`
- **实际数据**：`data.result.dimensionMultiCountryResult[region_key].corporation`
- **注意**：Xiaomi 版本使用 `corporation` 而不是 `ai` 作为数据维度

#### KPI 字段映射

| 结果字段 | KPI 名称 | 说明 |
|---------|---------|------|
| `estImpression` | `Impression` | 展示数 |
| `estViews` | `VideoViews` | 视频观看数（Xiaomi 版本使用 `estViews` 而不是 `estVideoViews`） |
| `estEngagement` | `Engagement` | 互动数 |
| `estClicks` | `Clicks` | 点击数（Xiaomi 版本使用 `estClicks` 而不是 `estClickAll`） |

## 配置提取逻辑

### 从结果文件提取配置

脚本会自动从 `result_json` 中提取测试用例配置，无需单独的测试用例文件：

#### 1. 全局 KPI 配置

- **路径**：`data.result.briefInfo.basicInfo.kpiInfoBudgetConfig.rangeMatch`
- **默认值**：80
- **用途**：全局 KPI 目标达成率

#### 2. KPI 优先级列表

- **路径**：`data.result.briefInfo.basicInfo.kpiInfo`
- **提取方式**：按 `priority` 字段排序后提取 `key` 字段
- **用途**：确定 KPI 检查的优先级顺序

#### 3. 模块优先级列表

- **路径**：`data.result.briefInfo.basicInfo.moduleConfig`
- **提取方式**：按 `priority` 字段排序后提取 `moduleName` 字段
- **用途**：确定模块检查的优先级顺序

#### 4. 阶段预算配置

- **路径**：`data.result.briefInfo.briefMultiConfig[0].stageBudgetConfig`
- **字段**：
  - `rangeMatch`：允许误差范围（默认 20%）
  - `consistentMatch`：匹配类型（1=完全匹配，0=大小关系匹配）

#### 5. 营销漏斗预算配置

- **路径**：`data.result.briefInfo.briefMultiConfig[0].marketingFunnelBudgetConfig`
- **字段**：
  - `rangeMatch`：允许误差范围（默认 15%）
  - `consistentMatch`：匹配类型（1=完全匹配，0=大小关系匹配）

#### 6. 媒体预算配置

- **路径**：`data.result.briefInfo.briefMultiConfig[0].mediaBudgetConfig`
- **字段**：
  - `rangeMatch`：允许误差范围（默认 5%）
  - `consistentMatch`：匹配类型（1=完全匹配，0=大小关系匹配）

#### 7. 广告格式配置

- **KPI 目标达成率**：`data.result.briefInfo.briefMultiConfig[0].mediaMarketingFunnelFormatBudgetConfig.kpiFlexibility`（默认 80%）
- **预算目标达成率**：`data.result.briefInfo.briefMultiConfig[0].mediaMarketingFunnelFormatBudgetConfig.totalBudgetFlexibility`（默认 80%）

## 数据提取逻辑

### 1. AI 维度数据提取

**函数**：`extract_ai_data(result_json)`

从结果文件中提取所有推广区域的 `corporation` 维度数据：

- **路径**：`data.result.dimensionMultiCountryResult[region_key].corporation`
- **处理**：
  - 遍历所有区域，提取每个区域的 `corporation` 数组
  - 为每条数据添加 `_region_key` 字段
  - **过滤**：自动过滤掉 `media` 字段包含 "TTL" 的总计行

### 2. KPI 值提取

**函数**：`extract_kpi_from_ai(ai_item)`

从 `corporation` 数据项中提取 KPI 值，字段映射关系：

| 结果字段 | KPI 名称 |
|---------|---------|
| `estImpression` | `Impression` |
| `estViews` | `VideoViews` |
| `estEngagement` | `Engagement` |
| `estClicks` | `Clicks` |

**注意**：Xiaomi 版本使用 `estViews` 而不是 `estVideoViews`，使用 `estClicks` 而不是 `estClickAll`。

### 3. 预算解析

**函数**：`parse_budget(budget_str)`

解析预算值，支持多种格式：
- 数字类型：直接转换为浮点数
- 字符串：去除 `%`、`,` 等符号后转换为浮点数
- `None`、`"-"`、空字符串：返回 `0.0`

### 4. KPI 值解析

**函数**：`parse_kpi_value(kpi_obj)`

解析 KPI 值，支持两种格式：
- **对象格式**：`{"value": "100000", "isModified": 0}` → 提取 `value` 字段
- **直接值**：字符串或数字直接使用

## 检查函数详解

### 1. 全局 KPI 检查

**函数**：`check_global_kpi_achievement(result_json, ai_data_list, testcase_config)`

**功能**：检查全局 KPI 是否达成

**数据来源**：
- **目标值**：`data.result.briefInfo.basicInfo.kpiInfo[]`
- **实际值**：从 `ai_data_list` 中聚合所有 `corporation` 数据的 KPI 值

**判断逻辑**：

1. **目标值为 null**：
   - 不进行判断，`achievement_rate = "null"`，`achieved = False`

2. **目标值为 0**：
   - 如果实际值也为 0，达成率 = 0%，判定为达成
   - 如果实际值不为 0，达成率 = "null"，判定为未达成

3. **目标值不为 0**：
   - 计算达成率：`achievement_rate = round((actual / target) * 100)`
   - 判断是否达成：
     - 如果 `kpi_must_achieve=True` 或 `completion=1`（必须达成）：
       - 要求：`actual >= target`（实际值必须大于等于目标值）
     - 否则（非必须达成）：
       - 要求：`achievement_rate >= kpi_target_rate`（达成率必须大于等于目标达成率，默认 80%）

**配置参数**：
- `kpi_target_rate`：目标达成率（默认 80%）
- `kpi_must_achieve`：是否必须达成（默认 False，从配置中提取）

### 2. 阶段预算检查

**函数**：`check_stage_budget_achievement(result_json, ai_data_list, testcase_config)`

**功能**：检查各区域下的 stage 维度预算是否满足

**数据来源**：
- **目标配置**：`data.result.briefInfo.briefMultiConfig[].stage[]`
- **实际配置**：从 `ai_data_list` 中按 `country` 和 `stage` 聚合 `totalBudget`

**判断逻辑**：

1. **目标值为 0**：
   - 如果实际占比为 0%，判定为满足
   - 否则判定为不满足

2. **目标值不为 0**：
   - 计算误差：`error_percentage = round(abs(actual_percentage - target_percentage))`
   - 根据匹配类型判断：
     - **完全匹配**（`stage_match_type="完全匹配"`）：
       - 要求：`error_percentage <= stage_range_match`（误差必须小于等于允许误差范围，默认 20%）
     - **大小关系匹配**（`stage_match_type="大小关系匹配"`）：
       - 检查顺序一致性：比较目标顺序和实际顺序
       - 允许"并列"情况（两个 stage 的预算差异小于总预算的 0.01%）

**配置参数**：
- `stage_match_type`：匹配类型（"完全匹配" 或 "大小关系匹配"）
- `stage_range_match`：允许误差范围（默认 20%）

### 3. 营销漏斗预算检查

**函数**：`check_marketingfunnel_budget_achievement(result_json, ai_data_list, testcase_config)`

**功能**：检查各区域下的 marketingFunnel 维度预算是否满足

**数据来源**：
- **目标配置**：`data.result.briefInfo.briefMultiConfig[].marketingFunnel[]`
- **实际配置**：从 `ai_data_list` 中按 `country` 和 `marketingFunnel` 聚合 `totalBudget`

**判断逻辑**：与阶段预算检查类似

**配置参数**：
- `marketingfunnel_match_type`：匹配类型
- `marketingfunnel_range_match`：允许误差范围（默认 15%）

### 4. 媒体预算检查

**函数**：`check_media_budget_achievement(result_json, ai_data_list, testcase_config)`

**功能**：检查各区域下的 media 维度预算是否满足（统计到 platform 层级）

**数据来源**：
- **目标配置**：`data.result.briefInfo.briefMultiConfig[].media[].children[]`（platform 层级）
- **实际配置**：从 `ai_data_list` 中按 `country`、`media`、`mediaChannel` 聚合 `totalBudget`

**判断逻辑**：与阶段预算检查类似

**配置参数**：
- `media_match_type`：匹配类型
- `media_range_match`：允许误差范围（默认 5%）

### 5. MediaMarketingFunnelFormat KPI 检查

**函数**：`check_mediaMarketingFunnelFormat_kpi_achievement(result_json, ai_data_list, testcase_config)`

**功能**：检查 mediaMarketingFunnelFormat 维度 KPI 是否达成（Xiaomi 版本特有）

**数据来源**：
- **目标配置**：`data.result.briefInfo.briefMultiConfig[].mediaMarketingFunnelFormat[].adFormatWithKPI[]`
- **实际配置**：从 `ai_data_list` 中按 `country`、`media`、`mediaChannel`、`marketingFunnel`、`adFormat`、`creative` 匹配并聚合 KPI 值

**匹配策略**：
1. 完整匹配：`{country}|{media}|{platform}|{funnel}|{adformat}`
2. 如果 `funnel` 为空，通过 `(media, platform, objective, adformat)` 映射推导 `marketingFunnel`

**判断逻辑**：与全局 KPI 检查类似

**配置参数**：
- `mediaMarketingFunnelFormat_target_rate`：目标达成率（默认 80%）
- `mediaMarketingFunnelFormat_must_achieve`：是否必须达成（默认 False）

### 6. MediaMarketingFunnelFormatBudgetConfig 预算检查

**函数**：`check_mediaMarketingFunnelFormatBudgetConfig_budget_achievement(result_json, ai_data_list, testcase_config)`

**功能**：检查 mediaMarketingFunnelFormatBudgetConfig 维度预算是否满足（Xiaomi 版本特有）

**数据来源**：
- **目标配置**：`data.result.briefInfo.briefMultiConfig[].mediaMarketingFunnelFormat[].adFormatWithKPI[].adFormatTotalBudget`
- **实际配置**：从 `ai_data_list` 中按 `country`、`media`、`mediaChannel`、`marketingFunnel`、`adFormat` 聚合 `totalBudget`

**判断逻辑**：
- 如果 `target` 为 `null`：判定为达成（`achieved = True`）
- 如果 `target = 0`：要求 `actual = 0`
- 如果 `completion = 1`：要求 `actual >= target`
- 如果 `completion = 0`：要求 `achievement_rate >= totalBudgetFlexibility`（默认 80%）

**配置参数**：
- `mediaMarketingFunnelFormatBudgetConfig_target_rate`：目标达成率（从 `totalBudgetFlexibility` 提取，默认 80%）
- `totalBudgetFlexibility`：预算灵活性（从配置中提取，默认 80%）

### 7. AdFormat 预算分配检查

**函数**：`check_adformat_budget_allocation(result_json, ai_data_list, testcase_config)`

**功能**：检查每个推广区域下每个 AdFormat 是否都分配了预算（当 `allow_zero_budget=False` 时）

**数据来源**：
- **目标配置**：`data.result.briefInfo.briefMultiConfig[].mediaMarketingFunnelFormat[].adFormatWithKPI[]`
- **实际配置**：从 `ai_data_list` 中按 `country`、`media`、`mediaChannel`、`adFormat` 聚合 `totalBudget`（跨所有 stage）

**判断逻辑**：
- 如果 `allow_zero_budget=True`：不进行检查，返回空字典
- 如果 `allow_zero_budget=False`：要求每个目标 AdFormat 的预算 > 0

**配置参数**：
- `allow_zero_budget`：是否允许 0 预算（默认 False）

## 判断标准总结

### KPI 达成判断

| 条件 | 判断标准 |
|------|---------|
| `target = null` | `achieved = False`（不进行判断） |
| `target = 0` | `actual = 0` → 达成 |
| `target > 0` 且 `must_achieve=True` 或 `completion=1` | `actual >= target` → 达成 |
| `target > 0` 且 `must_achieve=False` 且 `completion=0` | `achievement_rate >= target_rate` → 达成 |

### 预算匹配判断

| 匹配类型 | 判断标准 |
|---------|---------|
| 完全匹配 | `abs(actual_percentage - target_percentage) <= range_match` |
| 大小关系匹配 | 检查顺序一致性，允许"并列"情况（差异小于总预算的 0.01%） |

### 特殊值处理

- **目标值为 null**：
  - 不进行判断，`achievement_rate = "null"`，`achieved = False`

- **目标值为 0**：
  - 如果实际值也为 0，判定为达成/满足
  - 如果实际值不为 0，达成率/误差显示为 "null"

- **达成率计算**：
  - 使用整数百分比：`round((actual / target) * 100)`
  - 避免浮点数精度问题

## 输出格式

### 控制台输出

脚本会在控制台输出详细的检查摘要，包括：
- 测试用例配置
- 各维度达成情况汇总
- 详细的达成/未达成项列表

### JSON 输出

结果保存为 JSON 文件，包含以下结构：

```json
{
  "case_name": "基准用例-完全匹配默认配置",
  "uuid": "...",
  "job_id": "...",
  "testcase_config": {
    "kpi_target_rate": 80,
    "stage_range_match": 20,
    "marketingfunnel_range_match": 15,
    "media_range_match": 5,
    "mediaMarketingFunnelFormat_target_rate": 80,
    "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
    "kpi_priority_list": [...],
    "module_priority_list": [...]
  },
  "global_kpi": {
    "Impression": {
      "target": 367908213.0,
      "actual": 681554619.0,
      "achievement_rate": 185,
      "target_rate": 80,
      "achieved": true,
      "priority": 1,
      "completion": 0
    }
  },
  "stage_budget": {
    "ES": {
      "EARLYBIRD": {
        "target": 10000,
        "actual": 10500,
        "error_percentage": 2,
        "range_match": 20,
        "satisfied": true,
        "target_percentage": 50,
        "actual_percentage": 52,
        "match_type": "完全匹配"
      }
    }
  },
  "marketingfunnel_budget": {...},
  "media_budget": {...},
  "mediaMarketingFunnelFormat_kpi": {
    "ES|Meta|FB&IG|Awareness|Image&Video Link Ads": {
      "country": "ES",
      "media": "Meta",
      "platform": "FB&IG",
      "funnel": "Awareness",
      "adformat": "Image&Video Link Ads",
      "creative": "Image&Video",
      "kpis": {
        "Impression": {
          "target": 100000,
          "actual": 120000,
          "achievement_rate": 120,
          "target_rate": 80,
          "achieved": true,
          "priority": 1,
          "completion": 0
        }
      }
    }
  },
  "mediaMarketingFunnelFormatBudgetConfig_budget": {
    "ES|Meta|FB&IG|Awareness|Image&Video Link Ads": {
      "country": "ES",
      "media": "Meta",
      "platform": "FB&IG",
      "funnel": "Awareness",
      "adformat": "Image&Video Link Ads",
      "creative": "Image&Video",
      "target": 1000,
      "actual": 950,
      "achievement_rate": 95,
      "target_rate": 80,
      "achieved": true,
      "completion": 0,
      "min_required": 800,
      "total_budget_flexibility": 80
    }
  },
  "adformat_budget_allocation": {
    "ES": {
      "Meta|FB&IG|Image&Video Link Ads": {
        "media": "Meta",
        "platform": "FB&IG",
        "adformat": "Image&Video Link Ads",
        "budget": 1000,
        "satisfied": true
      }
    }
  }
}
```

### 输出文件位置

默认输出到：`output/xiaomi/achievement_checks/json/{base_name}_{job_id}_achievement_check.json`

如果指定了 `--output` 参数，则输出到指定路径。

### 自动生成报告

脚本会自动生成测试报告：
- **Markdown 报告**：`output/xiaomi/achievement_checks/reports/{base_name}_{job_id}_achievement_check.md`
- **HTML 报告**：`output/xiaomi/achievement_checks/reports/{base_name}_{job_id}_achievement_check.html`

## 注意事项

1. **数据格式差异**：Xiaomi 版本的结果文件结构与 Common 版本不同，使用 `data.result.dimensionMultiCountryResult[].corporation` 而不是 `data.result.dimensionMultiCountryResult[].ai`

2. **字段名称差异**：
   - 使用 `adFormat` 而不是 `adType`
   - 使用 `estViews` 而不是 `estVideoViews`
   - 使用 `estClicks` 而不是 `estClickAll`
   - 使用 `totalBudget` 而不是 `adTypeBudget`
   - 使用 `countryInfo.countryCode` 而不是 `country.code`

3. **配置提取**：所有配置信息都从结果文件中提取，无需单独的测试用例文件

4. **精度处理**：所有百分比计算都使用 `round()` 函数转换为整数，避免浮点数精度问题

5. **特殊值处理**：
   - 当目标值为 `null` 时，不进行判断
   - 当目标值为 0 时，如果实际值也为 0，判定为达成；如果实际值不为 0，达成率显示为 "null"

6. **匹配策略**：MediaMarketingFunnelFormat 相关检查使用多级匹配策略，如果 `funnel` 为空，会通过 `(media, platform, objective, adformat)` 映射推导

7. **TTL 过滤**：自动过滤掉 `media` 字段包含 "TTL" 的总计行

## 示例

### 基本使用

```bash
python core/check_kpi_achievement_xiaomi.py \
    --result-file output/xiaomi/results/mp_result_基准用例-完全匹配默认配置.json \
    --case-name "基准用例-完全匹配默认配置"
```

### 指定输出路径

```bash
python core/check_kpi_achievement_xiaomi.py \
    --result-file output/xiaomi/results/mp_result_基准用例-完全匹配默认配置.json \
    --case-name "基准用例-完全匹配默认配置" \
    --output output/xiaomi/custom_output/
```

## 错误处理

脚本会在以下情况返回错误：

1. 结果文件不存在或无法加载
2. 数据格式不正确导致解析失败
3. 配置信息缺失导致无法提取测试用例配置

所有错误信息都会在控制台输出，帮助定位问题。
