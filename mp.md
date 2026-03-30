该项目的核心功能是：基于用户输入的总预算、KPI 指标、推广区域占比、推广周期（stage）占比、推广目标（marketing funnel）占比、推广媒体（media-platform）占比及 adtype（adformat）配置，结合算法对 adtype 成效指标的预估，将预算分配到最细粒度，生成可满足 KPI 目标的 Media Plan。

其中，stage、marketing funnel、media-platform 为同级预算维度；marketing funnel、media-platform 与 adtype（adformat）存在映射关系。算法在分配过程中支持完全匹配/大小关系匹配、容差控制与不可行场景下的松弛兜底，并可对分配结果进行 KPI 与各维度达成检查，输出结构化报告。

