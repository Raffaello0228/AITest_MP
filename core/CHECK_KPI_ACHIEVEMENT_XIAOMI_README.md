# Xiaomi 版本 KPI 达成情况检查脚本说明

## 概述

`check_kpi_achievement_xiaomi.py` 是一个用于检查 Xiaomi 版本媒体计划结果是否满足测试用例要求的脚本。该脚本会从请求文件和结果文件中提取数据，根据测试用例配置判断各项指标是否达成。

## 使用方法

```bash
python core/check_kpi_achievement_xiaomi.py \
    --testcase-file testcase_templatex_xiaomi.py \
    --request-file output/xiaomi/requests/brief_case_基准用例-完全匹配默认配置.json \
    --result-file output/xiaomi/results/mp_result_基准用例-完全匹配默认配置.json \
    --case-name "基准用例-完全匹配默认配置" \
    [--output <输出路径>]
```

### 参数说明

- `--testcase-file`: 测试用例配置文件路径（Python 文件，包含 `TEST_CASES` 字典）
- `--request-file`: 请求 JSON 文件路径（包含 `basicInfo` 和 `briefMultiConfig`）
- `--result-file`: 结果 JSON 文件路径（包含 `result.dimensionMultiCountryResult`）
- `--case-name`: 测试用例名称（必须在 `TEST_CASES` 中存在）
- `--output`: 可选，输出文件路径（目录或文件路径）

## 数据结构

### 结果文件结构（Xiaomi 版本）

```json
{
  "result": {
    "briefInfo": {
      "basicInfo": {
        "uuid": "...",
        "jobId": "...",
        "kpiInfo": [...],
        "regionBudget": [...]
      },
      "briefMultiConfig": [...]
    },
    "dimensionMultiCountryResult": {
      "WE_ES": {
        "ai": [
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
```

### 请求文件结构

```json
{
  "basicInfo": {
    "kpiInfo": [
      {
        "key": "Impression",
        "val": "100000",
        "priority": 1,
        "completion": 0
      }
    ],
    "regionBudget": [
      {
        "countryInfo": {
          "countryCode": "ES"
        }
      }
    ]
  },
  "briefMultiConfig": [
    {
      "countryInfo": {
        "countryCode": "ES"
      },
      "stage": [...],
      "marketingFunnel": [...],
      "media": [...],
      "mediaMarketingFunnelFormat": [...],
      "mediaMarketingFunnelFormatBudgetConfig": [...]
    }
  ]
}
```

## 数据提取逻辑

### 1. AI 维度数据提取

**函数**: `extract_ai_data(result_json)`

从结果文件中提取所有推广区域的 ai 维度数据：

- **路径**: `result.result.dimensionMultiCountryResult[region_key].ai`
- **处理**: 遍历所有区域，提取每个区域的 `ai` 数组，并为每条数据添加 `_region_key` 字段

### 2. KPI 值提取

**函数**: `extract_kpi_from_ai(ai_item)`

从 ai 数据项中提取 KPI 值，字段映射关系：

| 结果字段 | KPI 名称 |
|---------|---------|
| `estImpression` | `Impression` |
| `estViews` | `VideoViews` |
| `estEngagement` | `Engagement` |
| `estClicks` | `Clicks` |

**注意**: Xiaomi 版本使用 `estViews` 而不是 `estVideoViews`，使用 `estClicks` 而不是 `estClickAll`。

### 3. 预算解析

**函数**: `parse_budget(budget_str)`

解析预算值，支持多种格式：
- 数字类型：直接转换为浮点数
- 字符串：去除 `%`、`,` 等符号后转换为浮点数
- `None`、`"-"`、空字符串：返回 `0.0`

### 4. KPI 值解析

**函数**: `parse_kpi_value(kpi_obj)`

解析 KPI 值，支持两种格式：
- **对象格式**: `{"value": "100000", "isModified": 0}` → 提取 `value` 字段
- **直接值**: 字符串或数字直接使用

## 检查函数详解

### 1. 全局 KPI 检查

**函数**: `check_global_kpi_achievement(request_json, ai_data_list, testcase_config)`

**功能**: 检查全局 KPI 是否达成

**数据来源**:
- **目标值**: `request_json.basicInfo.kpiInfo`
- **实际值**: 从 `ai_data_list` 中聚合所有 ai 数据的 KPI 值

**判断逻辑**:

1. **目标值为 0**:
   - 如果实际值也为 0，达成率 = 0%，判定为达成
   - 如果实际值不为 0，达成率 = "null"，判定为未达成

2. **目标值不为 0**:
   - 计算达成率：`achievement_rate = round((actual / target) * 100)`
   - 判断是否达成：
     - 如果 `kpi_must_achieve=True` 或 `completion=1`（必须达成）：
       - 要求：`actual >= target`（实际值必须大于等于目标值）
     - 否则（非必须达成）：
       - 要求：`achievement_rate >= kpi_target_rate`（达成率必须大于等于目标达成率，默认 80%）

**配置参数**:
- `kpi_target_rate`: 目标达成率（默认 80%）
- `kpi_must_achieve`: 是否必须达成（默认 False）

### 2. 阶段预算检查

**函数**: `check_stage_budget_achievement(request_json, result_json, ai_data_list, testcase_config)`

**功能**: 检查各区域下的 stage 维度预算是否满足

**数据来源**:
- **目标配置**: `request_json.briefMultiConfig[].stage[]`
- **实际配置**: 从 `ai_data_list` 中按 `country` 和 `stage` 聚合 `totalBudget`

**判断逻辑**:

1. **目标值为 0**:
   - 如果实际占比为 0%，判定为满足
   - 否则判定为不满足

2. **目标值不为 0**:
   - 计算误差：`error_percentage = round(abs(actual_percentage - target_percentage))`
   - 根据匹配类型判断：
     - **完全匹配**（`stage_match_type="完全匹配"`）：
       - 要求：`error_percentage <= stage_range_match`（误差必须小于等于允许误差范围，默认 20%）
     - **大小关系匹配**（`stage_match_type="大小关系匹配"`）：
       - 暂时简化处理，只检查顺序（当前实现为 `satisfied = True`）

**配置参数**:
- `stage_match_type`: 匹配类型（"完全匹配" 或 "大小关系匹配"）
- `stage_range_match`: 允许误差范围（默认 20%）

### 3. 营销漏斗预算检查

**函数**: `check_marketingfunnel_budget_achievement(request_json, result_json, ai_data_list, testcase_config)`

**功能**: 检查各区域下的 marketingFunnel 维度预算是否满足

**数据来源**:
- **目标配置**: `request_json.briefMultiConfig[].marketingFunnel[]`
- **实际配置**: 从 `ai_data_list` 中按 `country` 和 `marketingFunnel` 聚合 `totalBudget`

**判断逻辑**: 与阶段预算检查类似

**配置参数**:
- `marketingfunnel_match_type`: 匹配类型
- `marketingfunnel_range_match`: 允许误差范围（默认 15%）

### 4. 媒体预算检查

**函数**: `check_media_budget_achievement(request_json, result_json, ai_data_list, testcase_config)`

**功能**: 检查各区域下的 media 维度预算是否满足

**数据来源**:
- **目标配置**: `request_json.briefMultiConfig[].media[]`
- **实际配置**: 从 `ai_data_list` 中按 `country` 和 `media` 聚合 `totalBudget`

**判断逻辑**: 与阶段预算检查类似

**配置参数**:
- `media_match_type`: 匹配类型
- `media_range_match`: 允许误差范围（默认 5%）

### 5. MediaMarketingFunnelFormat KPI 检查

**函数**: `check_mediaMarketingFunnelFormat_kpi_achievement(request_json, ai_data_list, testcase_config)`

**功能**: 检查 mediaMarketingFunnelFormat 维度 KPI 是否达成（Xiaomi 版本特有）

**数据来源**:
- **目标配置**: `request_json.briefMultiConfig[].mediaMarketingFunnelFormat[].adFormatWithKPI[]`
- **实际配置**: 从 `ai_data_list` 中按 `country`、`media`、`mediaChannel`、`marketingFunnel`、`adFormat`、`creative` 匹配并聚合 KPI 值

**匹配策略**:
1. 完整匹配：`{country}|{media}|{platform}|{funnel}|{adformat}|{creative}`
2. 无国家匹配：`{media}|{platform}|{funnel}|{adformat}|{creative}`
3. 简化匹配：`{adformat}|{funnel}`

**判断逻辑**: 与全局 KPI 检查类似

**配置参数**:
- `mediaMarketingFunnelFormat_target_rate`: 目标达成率（默认 80%）
- `mediaMarketingFunnelFormat_must_achieve`: 是否必须达成（默认 False）

### 6. MediaMarketingFunnelFormatBudgetConfig 预算检查

**函数**: `check_mediaMarketingFunnelFormatBudgetConfig_budget_achievement(request_json, ai_data_list, testcase_config)`

**功能**: 检查 mediaMarketingFunnelFormatBudgetConfig 维度预算是否满足（Xiaomi 版本特有）

**数据来源**:
- **目标配置**: `request_json.briefMultiConfig[].mediaMarketingFunnelFormatBudgetConfig.budgetConfig[]`
- **实际配置**: 从 `ai_data_list` 中按 `country`、`media`、`mediaChannel`、`marketingFunnel`、`adFormat`、`creative` 聚合 `totalBudget`

**判断逻辑**:
- 如果 `config_must_achieve=True`：要求 `actual >= target`
- 否则：要求误差百分比 <= 5%（默认误差范围）

**配置参数**:
- `mediaMarketingFunnelFormatBudgetConfig_target_rate`: 目标达成率（默认 80%）
- `mediaMarketingFunnelFormatBudgetConfig_must_achieve`: 是否必须达成（默认 False）

### 7. AdFormat 预算分配检查

**函数**: `check_adformat_budget_allocation(request_json, ai_data_list, testcase_config)`

**功能**: 检查每个推广区域下每个 AdFormat 是否都分配了预算（当 `allow_zero_budget=False` 时）

**数据来源**:
- **目标配置**: `request_json.briefMultiConfig[].mediaMarketingFunnelFormat[].adFormatWithKPI[]`
- **实际配置**: 从 `ai_data_list` 中按 `country`、`media`、`mediaChannel`、`adFormat` 聚合 `totalBudget`（跨所有 stage）

**判断逻辑**:
- 如果 `allow_zero_budget=True`：不进行检查，返回空字典
- 如果 `allow_zero_budget=False`：要求每个目标 AdFormat 的预算 > 0

**配置参数**:
- `allow_zero_budget`: 是否允许 0 预算（默认 False）

## 判断标准总结

### KPI 达成判断

| 条件 | 判断标准 |
|------|---------|
| `target = 0` | `actual = 0` → 达成 |
| `target > 0` 且 `must_achieve=True` 或 `completion=1` | `actual >= target` → 达成 |
| `target > 0` 且 `must_achieve=False` 且 `completion=0` | `achievement_rate >= target_rate` → 达成 |

### 预算匹配判断

| 匹配类型 | 判断标准 |
|---------|---------|
| 完全匹配 | `abs(actual_percentage - target_percentage) <= range_match` |
| 大小关系匹配 | 检查顺序一致性（当前实现简化处理） |

### 特殊值处理

- **目标值为 0**:
  - 如果实际值也为 0，判定为达成/满足
  - 如果实际值不为 0，达成率/误差显示为 "null"

- **达成率计算**:
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
  "stage_budget": {...},
  "marketingfunnel_budget": {...},
  "media_budget": {...},
  "mediaMarketingFunnelFormat_kpi": {...},
  "mediaMarketingFunnelFormatBudgetConfig_budget": {...},
  "adformat_budget_allocation": {...}
}
```

### 输出文件位置

默认输出到：`output/xiaomi/achievement_checks/json/{base_name}_{job_id}_achievement_check.json`

如果指定了 `--output` 参数，则输出到指定路径。

## 测试用例配置说明

测试用例配置在 `testcase_templatex_xiaomi.py` 文件中定义，主要配置项：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `kpi_target_rate` | KPI 目标达成率 | 80 |
| `kpi_must_achieve` | KPI 是否必须达成 | False |
| `stage_match_type` | Stage 匹配类型 | "完全匹配" |
| `stage_range_match` | Stage 预算误差范围 | 20 |
| `marketingfunnel_match_type` | MarketingFunnel 匹配类型 | "完全匹配" |
| `marketingfunnel_range_match` | MarketingFunnel 预算误差范围 | 15 |
| `media_match_type` | Media 匹配类型 | "完全匹配" |
| `media_range_match` | Media 预算误差范围 | 5 |
| `allow_zero_budget` | 是否允许 0 预算 | False |
| `mediaMarketingFunnelFormat_target_rate` | MediaMarketingFunnelFormat KPI 目标达成率 | 80 |
| `mediaMarketingFunnelFormat_must_achieve` | MediaMarketingFunnelFormat 是否必须达成 | False |
| `mediaMarketingFunnelFormatBudgetConfig_target_rate` | MediaMarketingFunnelFormatBudgetConfig 目标达成率 | 80 |
| `mediaMarketingFunnelFormatBudgetConfig_must_achieve` | MediaMarketingFunnelFormatBudgetConfig 是否必须达成 | False |
| `kpi_priority_list` | KPI 优先级列表 | [] |
| `module_priority_list` | 模块优先级列表 | [] |

## 注意事项

1. **数据格式差异**: Xiaomi 版本的结果文件结构与 Common 版本不同，使用 `result.result.dimensionMultiCountryResult[].ai` 而不是 `data.result.dimensionMultiCountryResult[].corporation`

2. **字段名称差异**: 
   - 使用 `adFormat` 而不是 `adType`
   - 使用 `estViews` 而不是 `estVideoViews`
   - 使用 `estClicks` 而不是 `estClickAll`
   - 使用 `totalBudget` 而不是 `adTypeBudget`
   - 使用 `countryInfo.countryCode` 而不是 `country.code`

3. **精度处理**: 所有百分比计算都使用 `round()` 函数转换为整数，避免浮点数精度问题

4. **特殊值处理**: 当目标值为 0 时，如果实际值也为 0，判定为达成；如果实际值不为 0，达成率显示为 "null"

5. **匹配策略**: MediaMarketingFunnelFormat 相关检查使用多级匹配策略，从完整匹配到简化匹配依次尝试

## 示例

### 基本使用

```bash
python core/check_kpi_achievement_xiaomi.py \
    --testcase-file testcase_templatex_xiaomi.py \
    --request-file output/xiaomi/requests/brief_case_基准用例-完全匹配默认配置.json \
    --result-file result_example.json \
    --case-name "基准用例-完全匹配默认配置"
```

### 指定输出路径

```bash
python core/check_kpi_achievement_xiaomi.py \
    --testcase-file testcase_templatex_xiaomi.py \
    --request-file output/xiaomi/requests/brief_case_基准用例-完全匹配默认配置.json \
    --result-file result_example.json \
    --case-name "基准用例-完全匹配默认配置" \
    --output output/xiaomi/custom_output/
```

## 错误处理

脚本会在以下情况返回错误：

1. 测试用例文件不存在或无法加载
2. 请求文件不存在
3. 结果文件不存在
4. 测试用例名称不存在于 `TEST_CASES` 中
5. 数据格式不正确导致解析失败

所有错误信息都会在控制台输出，帮助定位问题。

