"""
小米版测试用例模板 - 采用控制变量法设计
基准用例：所有字段使用默认值（完全匹配，默认误差范围）
其他用例：在基准用例基础上，只改变一个或几个字段，其他保持不变
"""

TEST_CASES = {
    # ========== 基准用例 ==========
    # 用例0：基准用例 - 所有字段使用默认值
    "基准用例-完全匹配默认配置": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "kpiInfo",
            "media",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # ========== 测试 KPI 相关字段 ==========
    # 用例1：KPI必须达成
    "测试-kpi_must_achieve-True": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": True,  # 改变
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "kpiInfo",
            "media",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # 用例2：KPI目标达成率改为90%
    "测试-kpi_target_rate-90": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 90,  # 改变
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "kpiInfo",
            "media",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # 用例3：KPI优先级改为Clicks第一
    "测试-kpi_priority_list-Clicks优先": {
        "kpi_priority_list": [
            "Clicks",
            "Impression",
            "VideoViews",
            "Engagement",
        ],  # 改变
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "kpiInfo",
            "media",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # ========== 测试 Stage 相关字段 ==========
    # 用例4：Stage匹配类型改为大小关系匹配
    "测试-stage_match_type-大小关系匹配": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "大小关系匹配",  # 改变
        "stage_range_match": None,  # 大小关系匹配时没有误差范围
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "stage",  # 提高优先级
            "kpiInfo",
            "media",
            "marketingFunnel",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # 用例5：Stage误差范围改为10%
    "测试-stage_range_match-10": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 10,  # 改变
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "stage",  # 提高优先级
            "kpiInfo",
            "media",
            "marketingFunnel",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # ========== 测试 MarketingFunnel 相关字段 ==========
    # 用例6：MarketingFunnel匹配类型改为大小关系匹配
    "测试-marketingfunnel_match_type-大小关系匹配": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "大小关系匹配",  # 改变
        "marketingfunnel_range_match": None,  # 大小关系匹配时没有误差范围
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "marketingFunnel",  # 提高优先级
            "kpiInfo",
            "media",
            "stage",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # 用例7：MarketingFunnel误差范围改为10%
    "测试-marketingfunnel_range_match-10": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 10,  # 改变
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "marketingFunnel",  # 提高优先级
            "kpiInfo",
            "media",
            "stage",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # ========== 测试 Media 相关字段 ==========
    # 用例8：Media匹配类型改为大小关系匹配
    "测试-media_match_type-大小关系匹配": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "大小关系匹配",  # 改变
        "media_range_match": None,  # 大小关系匹配时没有误差范围
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "media",  # 提高优先级
            "kpiInfo",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # 用例9：Media误差范围改为10%
    "测试-media_range_match-10": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 10,  # 改变
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "media",  # 提高优先级
            "kpiInfo",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # ========== 测试 allow_zero_budget ==========
    # 用例10：允许0预算
    "测试-allow_zero_budget-True": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": True,  # 改变
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "kpiInfo",
            "media",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # ========== 测试 mediaMarketingFunnelFormat 相关字段 ==========
    # 用例11：mediaMarketingFunnelFormat必须达成
    "测试-mediaMarketingFunnelFormat_must_achieve-True": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": True,  # 改变
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "mediaMarketingFunnelFormat",  # 提高优先级
            "kpiInfo",
            "media",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # 用例12：mediaMarketingFunnelFormat目标达成率改为90%
    "测试-mediaMarketingFunnelFormat_target_rate-90": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 90,  # 改变
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "mediaMarketingFunnelFormat",  # 提高优先级
            "kpiInfo",
            "media",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # ========== 测试 mediaMarketingFunnelFormatBudgetConfig 相关字段 ==========
    # 用例13：mediaMarketingFunnelFormatBudgetConfig必须达成
    "测试-mediaMarketingFunnelFormatBudgetConfig_must_achieve-True": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": True,  # 改变
        "module_priority_list": [
            "mediaMarketingFunnelFormatBudgetConfig",  # 提高优先级
            "kpiInfo",
            "media",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormat",
        ],
    },
    # 用例14：mediaMarketingFunnelFormatBudgetConfig目标达成率改为90%
    "测试-mediaMarketingFunnelFormatBudgetConfig_target_rate-90": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 90,  # 改变
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "mediaMarketingFunnelFormatBudgetConfig",  # 提高优先级
            "kpiInfo",
            "media",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormat",
        ],
    },
    # ========== 测试 module_priority_list ==========
    # 用例15：模块优先级改为media第一
    "测试-module_priority_list-media第一": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [  # 改变
            "media",
            "kpiInfo",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # 用例16：模块优先级改为stage第一
    "测试-module_priority_list-stage第一": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [  # 改变
            "stage",
            "kpiInfo",
            "media",
            "marketingFunnel",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # ========== 组合测试用例 ==========
    # 用例17：所有匹配类型都改为大小关系匹配
    "组合测试-所有匹配类型-大小关系匹配": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 80,
        "stage_match_type": "大小关系匹配",  # 改变
        "stage_range_match": None,
        "marketingfunnel_match_type": "大小关系匹配",  # 改变
        "marketingfunnel_range_match": None,
        "media_match_type": "大小关系匹配",  # 改变
        "media_range_match": None,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "kpiInfo",
            "media",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # 用例18：所有must_achieve都设为True
    "组合测试-所有must_achieve-True": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": True,  # 改变
        "kpi_target_rate": 80,
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 80,
        "mediaMarketingFunnelFormat_must_achieve": True,  # 改变
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 80,
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": True,  # 改变
        "module_priority_list": [
            "kpiInfo",
            "media",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # 用例19：所有target_rate都设为90%
    "组合测试-所有target_rate-90": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 90,  # 改变
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 15,
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 90,  # 改变
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 90,  # 改变
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "kpiInfo",
            "media",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # 用例20：严格模式：所有must_achieve=True，所有target_rate=90%，所有误差范围=5%
    "组合测试-严格模式": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": True,  # 改变
        "kpi_target_rate": 90,  # 改变
        "stage_match_type": "完全匹配",
        "stage_range_match": 5,  # 改变
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 5,  # 改变
        "media_match_type": "完全匹配",
        "media_range_match": 5,
        "allow_zero_budget": False,
        "mediaMarketingFunnelFormat_target_rate": 90,  # 改变
        "mediaMarketingFunnelFormat_must_achieve": True,  # 改变
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 90,  # 改变
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": True,  # 改变
        "module_priority_list": [
            "kpiInfo",
            "media",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
    # 用例21：宽松模式：所有must_achieve=False，所有target_rate=70%，所有误差范围=20%
    "组合测试-宽松模式": {
        "kpi_priority_list": ["Impression", "VideoViews", "Engagement", "Clicks"],
        "kpi_must_achieve": False,
        "kpi_target_rate": 70,  # 改变
        "stage_match_type": "完全匹配",
        "stage_range_match": 20,
        "marketingfunnel_match_type": "完全匹配",
        "marketingfunnel_range_match": 20,  # 改变
        "media_match_type": "完全匹配",
        "media_range_match": 20,  # 改变
        "allow_zero_budget": True,  # 改变
        "mediaMarketingFunnelFormat_target_rate": 70,  # 改变
        "mediaMarketingFunnelFormat_must_achieve": False,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": 70,  # 改变
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve": False,
        "module_priority_list": [
            "kpiInfo",
            "media",
            "marketingFunnel",
            "stage",
            "mediaMarketingFunnelFormat",
            "mediaMarketingFunnelFormatBudgetConfig",
        ],
    },
}
