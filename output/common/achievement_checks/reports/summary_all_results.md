# 测试结果汇总报告
**生成时间**: 2026-01-05 11:29:16
**测试用例数量**: 14

---
## 全局 KPI Top3（按优先级排序）
| 测试用例 | Top1 KPI | Top1 达成率 | Top1 状态 | Top2 KPI | Top2 达成率 | Top2 状态 | Top3 KPI | Top3 达成率 | Top3 状态 |
|----------|----------|-------------|----------|----------|-------------|----------|----------|-------------|----------|
| 大小关系匹配-不勾选必须达成-KPI第一 | Impression | 178.00% | ✓ 达成 | VideoViews | 121.00% | ✓ 达成 | Engagement | 108.00% | ✓ 达成 |
| 大小关系匹配-不勾选必须达成-区域第一 | Impression | 178.00% | ✓ 达成 | VideoViews | 121.00% | ✓ 达成 | Engagement | 108.00% | ✓ 达成 |
| 大小关系匹配-勾选必须达成-KPI第一 | Impression | 160.00% | ✓ 达成 | VideoViews | 124.00% | ✓ 达成 | Engagement | 111.00% | ✓ 达成 |
| 大小关系匹配-勾选必须达成-区域第一 | Impression | 163.00% | ✓ 达成 | VideoViews | 124.00% | ✓ 达成 | Engagement | 111.00% | ✓ 达成 |
| 完全匹配-10%-KPI第一 | Impression | 202.00% | ✓ 达成 | VideoViews | 129.00% | ✓ 达成 | Engagement | 119.00% | ✓ 达成 |
| 完全匹配-10%-区域第一 | Impression | 206.00% | ✓ 达成 | VideoViews | 111.00% | ✓ 达成 | Engagement | 115.00% | ✓ 达成 |
| 完全匹配-5%-KPI第一-Engagement优先-Impression第二 | Engagement | 163.00% | ✓ 达成 | Impression | 132.00% | ✓ 达成 | VideoViews | 128.00% | ✓ 达成 |
| 完全匹配-5%-KPI第一-Engagement优先 | Engagement | 162.00% | ✓ 达成 | VideoViews | 162.00% | ✓ 达成 | Impression | 118.00% | ✓ 达成 |
| 完全匹配-5%-KPI第一-Impression优先-Engagement第二 | Impression | 202.00% | ✓ 达成 | Engagement | 115.00% | ✓ 达成 | VideoViews | 118.00% | ✓ 达成 |
| 完全匹配-5%-KPI第一-VideoViews优先-Engagement第二 | VideoViews | 177.00% | ✓ 达成 | Engagement | 120.00% | ✓ 达成 | Impression | 124.00% | ✓ 达成 |
| 完全匹配-5%-KPI第一-VideoViews优先 | VideoViews | 179.00% | ✓ 达成 | Impression | 130.00% | ✓ 达成 | Engagement | 115.00% | ✓ 达成 |
| 完全匹配-5%-KPI第一 | Impression | 199.00% | ✓ 达成 | VideoViews | 124.00% | ✓ 达成 | Engagement | 113.00% | ✓ 达成 |
| 完全匹配-5%-区域第一-允许0预算 | Impression | 218.00% | ✓ 达成 | VideoViews | 112.00% | ✓ 达成 | Engagement | 111.00% | ✓ 达成 |
| 完全匹配-5%-区域第一 | Impression | 210.00% | ✓ 达成 | VideoViews | 111.00% | ✓ 达成 | Engagement | 110.00% | ✓ 达成 |

---
## 各维度达成情况汇总
| 测试用例 | 全局 KPI | 区域预算 | 区域 KPI | 阶段预算 | 营销漏斗预算 | 媒体预算 | 广告类型 KPI | Adtype 预算分配 | 总 KPI 达成率 | 模块优先级 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 大小关系匹配-不勾选必须达成-KPI第一 | 3/3 (100.0%) | 0/10 (0.0%) | 30/30 (100.0%) | 10/10 (100.0%) | 13/30 (43.3%) | 4/28 (14.3%) | 106/312 (34.0%) | - | - | 134/134 (100.0%) | - | 139/345 (40.3%) | kpiInfo, regionBudget, media, marketingFunnel, stage, regionKPI, mediaMarketingFunnelAdtype |
| 大小关系匹配-不勾选必须达成-区域第一 | 3/3 (100.0%) | 0/10 (0.0%) | 30/30 (100.0%) | 10/10 (100.0%) | 13/30 (43.3%) | 4/28 (14.3%) | 100/312 (32.1%) | - | - | 134/134 (100.0%) | - | 133/345 (38.6%) | regionBudget, kpiInfo, media, marketingFunnel, stage, regionKPI, mediaMarketingFunnelAdtype |
| 大小关系匹配-勾选必须达成-KPI第一 | 3/3 (100.0%) | 0/10 (0.0%) | 30/30 (100.0%) | 10/10 (100.0%) | 15/30 (50.0%) | 6/28 (21.4%) | 112/312 (35.9%) | - | - | 134/134 (100.0%) | - | 145/345 (42.0%) | kpiInfo, regionBudget, media, marketingFunnel, stage, regionKPI, mediaMarketingFunnelAdtype |
| 大小关系匹配-勾选必须达成-区域第一 | 3/3 (100.0%) | 0/10 (0.0%) | 30/30 (100.0%) | 10/10 (100.0%) | 15/30 (50.0%) | 5/28 (17.9%) | 109/312 (34.9%) | - | - | 134/134 (100.0%) | - | 142/345 (41.2%) | regionBudget, kpiInfo, media, marketingFunnel, stage, regionKPI, mediaMarketingFunnelAdtype |
| 完全匹配-10%-KPI第一 | 3/3 (100.0%) | 10/10 (100.0%) | 30/30 (100.0%) | 10/10 (100.0%) | 12/30 (40.0%) | 5/28 (17.9%) | 109/312 (34.9%) | - | - | 134/134 (100.0%) | - | 142/345 (41.2%) | kpiInfo, regionBudget, media, marketingFunnel, stage, regionKPI, mediaMarketingFunnelAdtype |
| 完全匹配-10%-区域第一 | 3/3 (100.0%) | 10/10 (100.0%) | 30/30 (100.0%) | 10/10 (100.0%) | 14/30 (46.7%) | 6/28 (21.4%) | 109/312 (34.9%) | - | - | 134/134 (100.0%) | - | 142/345 (41.2%) | regionBudget, kpiInfo, media, marketingFunnel, stage, regionKPI, mediaMarketingFunnelAdtype |
| 完全匹配-5%-KPI第一-Engagement优先-Impression第二 | 3/3 (100.0%) | 10/10 (100.0%) | 30/30 (100.0%) | 10/10 (100.0%) | 16/30 (53.3%) | 6/28 (21.4%) | 109/312 (34.9%) | - | - | 134/134 (100.0%) | - | 142/345 (41.2%) | kpiInfo, regionBudget, media, marketingFunnel, stage, regionKPI, mediaMarketingFunnelAdtype |
| 完全匹配-5%-KPI第一-Engagement优先 | 3/3 (100.0%) | 10/10 (100.0%) | 30/30 (100.0%) | 10/10 (100.0%) | 17/30 (56.7%) | 4/28 (14.3%) | 100/312 (32.1%) | - | - | 134/134 (100.0%) | - | 133/345 (38.6%) | kpiInfo, regionBudget, media, marketingFunnel, stage, regionKPI, mediaMarketingFunnelAdtype |
| 完全匹配-5%-KPI第一-Impression优先-Engagement第二 | 3/3 (100.0%) | 10/10 (100.0%) | 30/30 (100.0%) | 10/10 (100.0%) | 10/30 (33.3%) | 3/28 (10.7%) | 100/312 (32.1%) | - | - | 134/134 (100.0%) | - | 133/345 (38.6%) | kpiInfo, regionBudget, media, marketingFunnel, stage, regionKPI, mediaMarketingFunnelAdtype |
| 完全匹配-5%-KPI第一-VideoViews优先-Engagement第二 | 3/3 (100.0%) | 10/10 (100.0%) | 30/30 (100.0%) | 10/10 (100.0%) | 18/30 (60.0%) | 8/28 (28.6%) | 103/312 (33.0%) | - | - | 134/134 (100.0%) | - | 136/345 (39.4%) | kpiInfo, regionBudget, media, marketingFunnel, stage, regionKPI, mediaMarketingFunnelAdtype |
| 完全匹配-5%-KPI第一-VideoViews优先 | 3/3 (100.0%) | 10/10 (100.0%) | 30/30 (100.0%) | 10/10 (100.0%) | 18/30 (60.0%) | 5/28 (17.9%) | 106/312 (34.0%) | - | - | 134/134 (100.0%) | - | 139/345 (40.3%) | kpiInfo, regionBudget, media, marketingFunnel, stage, regionKPI, mediaMarketingFunnelAdtype |
| 完全匹配-5%-KPI第一 | 3/3 (100.0%) | 10/10 (100.0%) | 30/30 (100.0%) | 10/10 (100.0%) | 11/30 (36.7%) | 4/28 (14.3%) | 106/312 (34.0%) | - | - | 134/134 (100.0%) | - | 139/345 (40.3%) | kpiInfo, regionBudget, media, marketingFunnel, stage, regionKPI, mediaMarketingFunnelAdtype |
| 完全匹配-5%-区域第一-允许0预算 | 3/3 (100.0%) | 10/10 (100.0%) | 30/30 (100.0%) | 10/10 (100.0%) | 9/30 (30.0%) | 4/28 (14.3%) | 92/312 (29.5%) | - | - | - | - | 125/345 (36.2%) | regionBudget, kpiInfo, media, marketingFunnel, stage, regionKPI, mediaMarketingFunnelAdtype |
| 完全匹配-5%-区域第一 | 3/3 (100.0%) | 10/10 (100.0%) | 30/30 (100.0%) | 10/10 (100.0%) | 12/30 (40.0%) | 4/28 (14.3%) | 111/312 (35.6%) | - | - | 134/134 (100.0%) | - | 144/345 (41.7%) | regionBudget, kpiInfo, media, marketingFunnel, stage, regionKPI, mediaMarketingFunnelAdtype |
---
## 说明
- **全局 KPI**: 全局 KPI 指标的达成情况
- **区域预算**: 各推广区域预算分配的达成情况
- **区域 KPI**: 各推广区域 KPI 指标的达成情况
- **阶段预算**: 各阶段预算分配的满足情况
- **营销漏斗预算**: 各营销漏斗预算分配的满足情况
- **媒体预算**: 各媒体预算分配的满足情况（统计到 platform 层级）
- **广告类型 KPI**: 各广告类型 KPI 指标的达成情况
- **adformat kpi**: adformat 维度 KPI 指标的达成情况
- **adformat预算**: adformat 维度预算分配的满足情况
- **Adtype 预算分配**: Adtype 预算分配检查（仅当 allow_zero_budget=False 时）
- **adformat预算非0**: adformat 预算非0检查（仅当 allow_zero_budget=False 时）
- **总 KPI 达成率**: 所有 KPI（全局、区域、广告类型、adformat）的总体达成情况
