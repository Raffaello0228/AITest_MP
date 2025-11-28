# 媒体计划接口入参结构说明

## 概述
本接口用于创建或更新媒体计划，包含全局基本信息和按国家/地区的详细配置。

## 数据结构

### 顶层结构
```json
{
  "basicInfo": {},      // 基本信息对象
  "briefMultiConfig": [] // 多国家配置数组
}
```

---

## 1. basicInfo（基本信息）

### 1.1 kpiInfo（KPI信息数组）
全局KPI目标配置，按优先级排序。

| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| key | String | 是 | KPI指标名称 | "Impression", "Clicks", "LinkClicks", "VideoViews", "Engagement", "Followers", "Like", "Purchase" |
| val | String | 是 | KPI目标值 | "100000" |
| priority | Number | 是 | 优先级（数字越小优先级越高） | 1 |
| completion | Number | 是 | 完成状态（0=未完成，1=已完成） | 1 |

### 1.2 kpiInfoBudgetConfig（KPI预算配置）
| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| rangeMatch | Number | 是 | 范围匹配度 | 80 |

### 1.3 regionBudgetConfig（区域预算配置）
| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| consistentMatch | Number | 是 | 一致性匹配度 | 1 |
| rangeMatch | Number | 是 | 范围匹配度 | 10 |
| budgetCompletionRule | Number | 是 | 预算完成规则阈值 | 90 |
| kpiCompletionRule | Number | 是 | KPI完成规则阈值 | 80 |

### 1.4 dimension（维度数组）
分析维度列表，用于数据筛选和分析。

| 类型 | 说明 | 可选值 |
|------|------|--------|
| String[] | 维度名称数组 | "corporation", "competitor", "category", "ai" |

### 1.5 moduleConfig（模块配置数组）
各模块的优先级配置。

| 字段 | 类型 | 必填 | 说明 | 可选值 |
|------|------|------|------|--------|
| moduleName | String | 是 | 模块名称 | "regionBudget", "mediaMarketingFunnelAdtype", "kpiInfo", "regionKPI", "media", "stage", "marketingFunnel" |
| priority | Number | 是 | 优先级（数字越小优先级越高） | 1-7 |

### 1.6 基础字段
| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| isHistoryMp | Number | 是 | 是否为历史媒体计划（0=否，1=是） | 0 |
| mediaPlanName | String | 是 | 媒体计划名称 | "test_script" |
| corporationId | String | 是 | 公司ID | "29887" |
| currency | String | 是 | 货币代码 | "USD" |
| totalBudget | Number | 是 | 总预算金额 | 10000000 |
| usedHistoryMp | Number | 是 | 是否使用历史媒体计划（0=否，1=是） | 0 |
| corporationName | String | 是 | 公司名称 | "Trip.com Travel Singapore Pte. Ltd." |
| accountId | String | 是 | 账户ID（多个用逗号分隔） | "6458679086,6462083221" |
| categoryLevel1Id | String | 是 | 一级分类ID | "1" |
| categoryLevel2Id | String | 是 | 二级分类ID | "101" |
| categoryLevel3Id | String | 是 | 三级分类ID | "3016" |
| categoryLevel4Id | String\|null | 否 | 四级分类ID | null |
| campaignId | String\|null | 否 | 活动ID（多个用逗号分隔） | null |
| competitorCorporationId | String | 是 | 竞争对手公司ID（多个用逗号分隔） | "294697,256233" |
| uuid | String | 是 | 唯一标识符 | "4808e3b7-df85-4249-8b59-d66cf0e5" |

### 1.7 regionBudget（区域预算数组）
按国家/地区配置的预算和KPI信息。

| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| country | Object | 是 | 国家/区域信息 | 见下方 |
| country.code | String | 是 | 国家/区域代码（ISO国家代码或区域代码） | "US", "GB", "FR", "DE", "ME&NA", "LATAM" |
| country.groupName | String | 是 | 分组名称 | "CountrySimpleCode"（国家）或 "RegionSimpleCode"（区域） |
| budgetPercentage | Number | 是 | 预算百分比 | 21.59 |
| budgetAmount | Number | 是 | 预算金额 | 2159000 |
| kpiInfo | Array | 是 | 该区域的KPI信息数组 | 同1.1 kpiInfo结构 |
| completion | Number | 是 | 完成状态（0=未完成，1=已完成） | 0 |

---

## 2. briefMultiConfig（多国家配置数组）

每个元素代表一个国家/地区的详细配置。

### 2.1 country（国家/区域信息）
| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| code | String | 是 | 国家/区域代码 | "US", "GB", "FR", "DE"（国家）或 "ME&NA", "LATAM"（区域） |
| groupName | String | 是 | 分组名称 | "CountrySimpleCode"（国家）或 "RegionSimpleCode"（区域） |

### 2.2 stage（阶段数组）
营销活动阶段配置。

| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| name | String | 是 | 阶段名称 | "1st", "2rd", "3th" |
| nameKey | String | 否 | 阶段名称键值 | "X", "2025 AWE Campaign" |
| budgetPercentage | Number | 是 | 预算百分比 | 20, 50, 30 |
| budgetAmount | Number | 是 | 预算金额 | 297400, 743500 |
| dates | String[]\|null | 否 | 日期范围数组（格式：["YYYYMMDD", "YYYYMMDD"]） | ["20260101", "20260131"] |
| marketingFunnel | String[]\|null | 否 | 关联的营销漏斗数组 | ["Awareness"], ["Conversion", "Traffic"], ["Consideration"] |
| mediaPlatform | Array[]\|null | 否 | 媒体平台数组（二维数组） | [["Meta", "FB&IG"]], null |

### 2.3 moduleConfig（模块配置数组）
同 1.5 moduleConfig 结构。

### 2.4 stageBudgetConfig（阶段预算配置）
| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| consistentMatch | Number | 是 | 一致性匹配度 | 1 |
| rangeMatch | Number | 是 | 范围匹配度 | 20 |

### 2.5 marketingFunnel（营销漏斗数组）
营销漏斗配置。

| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| name | String | 是 | 漏斗名称 | "Awareness", "Consideration", "Traffic", "Conversion" |
| nameKey | String | 否 | 漏斗名称键值（大写） | "AWARENESS", "CONSIDERATION", "TRAFFIC", "CONVERSION" |
| budgetPercentage | Number | 是 | 预算百分比 | 10, 20, 30, 40 |
| budgetAmount | Number | 是 | 预算金额 | 148700, 297400 |

### 2.6 marketingFunnelBudgetConfig（营销漏斗预算配置）
| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| consistentMatch | Number | 是 | 一致性匹配度 | 1 |
| rangeMatch | Number | 是 | 范围匹配度 | 15 |

### 2.7 media（媒体数组）
媒体平台配置，支持层级结构（父媒体-子平台）。

| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| name | String | 是 | 媒体名称 | "Meta", "Google", "TikTok" |
| budgetPercentage | Number | 是 | 预算百分比 | 99, 97.05 |
| budgetAmount | Number | 是 | 预算金额 | 0 |
| children | Array | 是 | 子平台数组 | 见下方 |

#### 2.7.1 media.children（子平台）
| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| name | String | 是 | 平台名称 | "FB&IG"（Meta合并平台）, "FB", "IG", "YTB", "GG"（Google搜索）, "TT" |
| budgetPercentage | Number | 是 | 预算百分比 | 50, 10, 30 |
| budgetAmount | Number | 是 | 预算金额 | 743500, 148700 |

### 2.8 mediaBudgetConfig（媒体预算配置）
| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| consistentMatch | Number | 是 | 一致性匹配度 | 1 |
| rangeMatch | Number | 是 | 范围匹配度 | 5 |

### 2.9 mediaMarketingFunnelAdtype（媒体-营销漏斗-广告类型配置数组）
媒体、营销漏斗和广告类型的关联配置。

| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| mediaName | String | 是 | 媒体名称 | "Meta", "Google", "TikTok" |
| platform | String[] | 是 | 平台数组 | ["FB&IG"], ["YTB", "GG"], ["TT"] |
| marketingFunnels | Array | 是 | 营销漏斗配置数组 | 见下方 |
| adTypeWithKPI | Array | 是 | 带KPI的广告类型数组 | 见下方 |

#### 2.9.1 marketingFunnels（营销漏斗配置）
| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| funnelName | String | 是 | 漏斗名称 | "Awareness", "Consideration", "Traffic", "Conversion" |
| funnelNameKey | String | 是 | 漏斗名称键值 | "Awareness", "Consideration" |
| adType | Array | 是 | 广告类型数组（通常为空） | [] |

#### 2.9.2 adTypeWithKPI（带KPI的广告类型）
| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| adTypeName | String | 是 | 广告类型名称 | "Video Action Campaign", "Reach", "Post Engagement", "Traffic", "Video Views", "Video Ads Sequencing", "Page Likes", "CI Follows", "CI to Live", "Video Shopping Ads", "LIVE Shopping Ads", "Conversion" |
| funnelName | String | 是 | 所属营销漏斗 | "Conversion", "Awareness", "Consideration", "Traffic" |
| kpiInfo | Array | 是 | adtype层级KPI信息数组 | 同 1.1 kpiInfo 结构（包含所有8种KPI类型） |

### 2.10 mediaMarketingFunnelAdtypeBudgetConfig（媒体-营销漏斗-广告类型预算配置）
| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| precision | Number | 是 | 精度（小数位数） | 2 |
| rangeMatch | Number | 是 | 范围匹配度 | 80 |

---

## 3. 数据说明

### 3.1 KPI指标类型
- **Impression**: 展示次数（优先级1）
- **Clicks**: 点击次数（优先级2）
- **LinkClicks**: 链接点击（优先级3）
- **VideoViews**: 视频观看次数（优先级4）
- **Engagement**: 互动次数（优先级5）
- **Followers**: 关注数（优先级6）
- **Like**: 点赞数（优先级7）
- **Purchase**: 购买转化（优先级8）

### 3.2 营销漏斗类型
- **Awareness**: 认知阶段
- **Consideration**: 考虑阶段
- **Traffic**: 流量阶段
- **Conversion**: 转化阶段

### 3.3 媒体平台
- **Meta**: Facebook/Instagram 的父媒体
  - **FB&IG**: Facebook和Instagram合并平台
  - **FB**: Facebook（单独）
  - **IG**: Instagram（单独）
- **Google**: Google 的父媒体
  - **YTB**: YouTube
  - **GG**: Google搜索
- **TikTok**: TikTok 的父媒体
  - **TT**: TikTok

### 3.4 广告类型示例
- **Video Action Campaign**: 视频行动广告（Google）
- **Video Ads Sequencing**: 视频广告序列（Google）
- **Video Views**: 视频观看广告（Meta）
- **Reach**: 覆盖广告（Meta/TikTok）
- **Post Engagement**: 帖子互动广告（Meta）
- **Page Likes**: 页面点赞广告（Meta）
- **Traffic**: 流量广告（Meta/TikTok）
- **Conversion**: 转化广告（Meta）
- **CI Follows**: 关注广告（TikTok）
- **CI to Live**: 直播广告（TikTok）
- **Video Shopping Ads**: 视频购物广告（TikTok）
- **LIVE Shopping Ads**: 直播购物广告（TikTok）

---

## 4. 注意事项

1. **必填字段**: 标记为"是"的字段必须提供，否则接口可能返回错误
2. **null值处理**: 某些字段允许为 `null`，表示未设置或使用默认值（如 `categoryLevel4Id`, `campaignId`）
3. **空字符串**: 某些字段可能为空字符串 `""`，与 `null` 含义不同
4. **数组顺序**: `moduleConfig` 中的优先级顺序很重要，影响处理逻辑
5. **预算一致性**: 各层级的预算百分比总和应接近100%，但允许一定误差
6. **国家/区域代码**: 
   - 使用ISO标准国家代码（如 US, GB, FR, DE 等）
   - 支持区域代码（如 ME&NA, LATAM），此时 `groupName` 应为 "RegionSimpleCode"
7. **ID格式**: 多个ID用逗号分隔，如 `accountId`, `competitorCorporationId`
8. **精度**: 百分比字段通常保留2位小数
9. **日期格式**: `stage.dates` 使用数组格式 `["YYYYMMDD", "YYYYMMDD"]`，表示开始和结束日期
10. **预算字段**: `budgetAmount` 和 `budgetPercentage` 通常同时存在，系统会优先使用 `budgetAmount`
11. **平台合并**: Meta 平台支持 "FB&IG" 表示 Facebook 和 Instagram 合并配置

---

## 5. 示例数据说明

### 5.1 完整示例
参考 `brief_template.json` 文件，包含：
- 多个国家/区域的配置（US, GB, FR, DE, ME&NA, LATAM 等）
- 每个国家/区域包含完整的阶段、漏斗、媒体和广告类型配置
- 阶段包含日期范围和预算金额
- 营销漏斗和媒体平台都包含预算金额
- 广告类型包含完整的8种KPI目标值配置

### 5.2 最小化示例
至少需要包含：
- `basicInfo` 中的必填字段
- `briefMultiConfig` 中至少一个国家的完整配置

---

## 6. 常见问题

**Q: budgetAmount 和 budgetPercentage 的关系？**  
A: 两者可以同时存在，也可以只存在一个。如果同时存在，系统会优先使用 budgetAmount。

**Q: completion 字段的作用？**  
A: 表示该KPI或区域是否已完成配置，0表示未完成，1表示已完成。用于标识配置状态。

**Q: priority 字段的作用？**  
A: 优先级数字越小，优先级越高。用于确定处理顺序和权重计算。

**Q: 为什么有些数组为空？**  
A: 空数组 `[]` 表示该配置项存在但未设置具体值，与 `null` 或未定义不同。

**Q: dates 字段的格式是什么？**  
A: `dates` 是一个字符串数组，格式为 `["YYYYMMDD", "YYYYMMDD"]`，第一个元素是开始日期，第二个元素是结束日期。例如 `["20260101", "20260131"]` 表示2026年1月1日到1月31日。

**Q: 区域代码和国家代码有什么区别？**  
A: 国家代码使用ISO标准代码（如 US, GB），`groupName` 为 "CountrySimpleCode"；区域代码是自定义的区域标识（如 ME&NA, LATAM），`groupName` 为 "RegionSimpleCode"。

**Q: FB&IG 是什么意思？**  
A: "FB&IG" 表示 Facebook 和 Instagram 的合并平台配置，用于同时配置两个平台的预算和设置。

