1.基于原始业务数据origin_data.csv转化json数据（模板如brief_template.json）
2.按照测试用例，补充预算分配规则
3.异步调用接口1生成结果
4.调用接口2查看统计结果
5.断言判断统计结果是否满足预算分配规则
6.生成可视化结果文档



## 测试用例表格

| 用例编号 | KPI指标 | 匹配类型 | 误差范围 | 必须达成 | 优先级设置 | 其他说明 |
|---------|---------|---------|---------|---------|-----------|---------|
| 1 | impression<br>views<br>engagement | 全部填写，完全匹配 | 5% | - | KPI指标第一<br>推广区域预算分配第二<br>其他同默认选择 | 每个kpi的达成率<br>推广区域的达成率 |
| 2 | impression<br>views<br>engagement | 全部填写，完全匹配 | 5% | - | 推广区域预算分配第一<br>KPI指标第二<br>其他同默认选择 | - |
| 3 | impression<br>views<br>engagement | 全部填写，完全匹配 | 10% | - | KPI指标第一<br>推广区域预算分配第二<br>其他同默认选择 | - |
| 4 | impression<br>views<br>engagement | 全部填写，完全匹配 | 10% | - | 推广区域预算分配第一<br>KPI指标第二<br>其他同默认选择 | - |
| 5 | impression<br>views<br>engagement | 部分填写，完全匹配 | 5% | - | KPI指标第一<br>推广区域预算分配第二<br>其他同默认选择 | （这个可以浅看） |
| 6 | impression<br>views<br>engagement | 部分填写，完全匹配 | 5% | - | 推广区域预算分配第一<br>KPI指标第二<br>其他同默认选择 | （这个可以浅看） |
| 7 | impression<br>views<br>engagement | 大小关系匹配 | - | 不勾选 | KPI指标第一<br>推广区域预算分配第二<br>其他同默认选择 | - |
| 8 | impression<br>views<br>engagement | 大小关系匹配 | - | 不勾选 | 推广区域预算分配第一<br>KPI指标第二<br>其他同默认选择 | - |
| 9 | impression<br>views<br>engagement | 大小关系匹配 | - | 勾选 | KPI指标第一<br>推广区域预算分配第二<br>其他同默认选择 | 增加一个必须达成的达成率 |
| 10 | impression<br>views<br>engagement | 大小关系匹配 | - | 勾选 | 推广区域预算分配第一<br>KPI指标第二<br>其他同默认选择 | 增加一个必须达成的达成率 |

**结果衡量标准：** 前三指标达成率（impression, views, engagement）


统计指标
