#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 testcase 配置判断每个指标是否达成（Xiaomi版本）

注意：testcase_config 和所有配置信息现在直接从 result_json 中提取，不再需要 testcase_file 和 request_file。

用法:
    python core/check_kpi_achievement_xiaomi.py \
        --result-file output/xiaomi/results/mp_result_基准用例-完全匹配默认配置.json \
        --case-name "基准用例-完全匹配默认配置"
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional


def load_json(filepath: Path) -> Any:
    """加载JSON文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_testcase_config_from_result(result_json: Dict) -> Dict[str, Any]:
    """从 result_json 中提取 testcase_config"""
    # Xiaomi版本：result_json.data.result.briefInfo
    data = result_json.get("data", {})
    result = data.get("result", {})
    brief_info = result.get("briefInfo", {})
    basic_info = brief_info.get("basicInfo", {})
    brief_multi_config = brief_info.get("briefMultiConfig", [])

    # 从 basicInfo 中提取 KPI 配置
    kpi_info_budget_config = basic_info.get("kpiInfoBudgetConfig", {})
    kpi_target_rate = kpi_info_budget_config.get("rangeMatch", 80)

    # 从 basicInfo 中提取 KPI 优先级列表（按 priority 排序）
    kpi_info_list = basic_info.get("kpiInfo", [])
    kpi_priority_list = []
    if kpi_info_list:
        # 按 priority 排序
        sorted_kpis = sorted(kpi_info_list, key=lambda x: x.get("priority", 999))
        for kpi in sorted_kpis:
            kpi_key = kpi.get("key", "")
            if kpi_key:
                kpi_priority_list.append(kpi_key)

    # 从 basicInfo 中提取模块优先级列表（按 priority 排序）
    module_config_list = basic_info.get("moduleConfig", [])
    module_priority_list = []
    if module_config_list:
        # 按 priority 排序
        sorted_modules = sorted(
            module_config_list, key=lambda x: x.get("priority", 999)
        )
        for module in sorted_modules:
            module_name = module.get("moduleName", "")
            if module_name:
                module_priority_list.append(module_name)

    # 从 briefMultiConfig 中提取配置（取第一个配置，通常所有国家配置相同）
    if brief_multi_config:
        config = brief_multi_config[0]

        # Stage 配置
        stage_budget_config = config.get("stageBudgetConfig", {})
        stage_range_match = stage_budget_config.get("rangeMatch", 20)
        stage_consistent_match = stage_budget_config.get("consistentMatch", 1)
        stage_match_type = "完全匹配" if stage_consistent_match == 1 else "大小关系匹配"

        # Marketing Funnel 配置
        marketing_funnel_budget_config = config.get("marketingFunnelBudgetConfig", {})
        marketingfunnel_range_match = marketing_funnel_budget_config.get(
            "rangeMatch", 15
        )
        marketingfunnel_consistent_match = marketing_funnel_budget_config.get(
            "consistentMatch", 1
        )
        marketingfunnel_match_type = (
            "完全匹配" if marketingfunnel_consistent_match == 1 else "大小关系匹配"
        )

        # Media 配置
        media_budget_config = config.get("mediaBudgetConfig", {})
        media_range_match = media_budget_config.get("rangeMatch", 5)
        media_consistent_match = media_budget_config.get("consistentMatch", 1)
        media_match_type = "完全匹配" if media_consistent_match == 1 else "大小关系匹配"

        # MediaMarketingFunnelFormatBudgetConfig 配置
        media_marketing_funnel_format_budget_config = config.get(
            "mediaMarketingFunnelFormatBudgetConfig", {}
        )
        media_marketing_funnel_format_target_rate = (
            media_marketing_funnel_format_budget_config.get("kpiFlexibility", 80)
        )
        media_marketing_funnel_format_budget_config_target_rate = (
            media_marketing_funnel_format_budget_config.get(
                "totalBudgetFlexibility", 80
            )
        )
    else:
        # 默认值
        stage_range_match = 20
        stage_match_type = "完全匹配"
        marketingfunnel_range_match = 15
        marketingfunnel_match_type = "完全匹配"
        media_range_match = 5
        media_match_type = "完全匹配"
        media_marketing_funnel_format_target_rate = 80
        media_marketing_funnel_format_budget_config_target_rate = 80

    return {
        "kpi_target_rate": kpi_target_rate,
        "region_budget_target_rate": 90,  # 默认值，Xiaomi版本不使用
        "region_kpi_target_rate": 80,  # 默认值，Xiaomi版本不使用
        "mediaMarketingFunnelAdtype_target_rate": media_marketing_funnel_format_target_rate,
        "stage_range_match": stage_range_match,
        "stage_match_type": stage_match_type,
        "marketingfunnel_range_match": marketingfunnel_range_match,
        "marketingfunnel_match_type": marketingfunnel_match_type,
        "media_range_match": media_range_match,
        "media_match_type": media_match_type,
        "kpi_priority_list": kpi_priority_list,
        "module_priority_list": module_priority_list,
        "mediaMarketingFunnelFormat_target_rate": media_marketing_funnel_format_target_rate,
        "mediaMarketingFunnelFormatBudgetConfig_target_rate": media_marketing_funnel_format_budget_config_target_rate,
    }


def load_testcase(testcase_file: Path, case_name: str) -> Optional[Dict[str, Any]]:
    """加载测试用例配置"""
    # 动态导入测试用例文件
    import importlib.util

    spec = importlib.util.spec_from_file_location("testcase", testcase_file)
    if spec is None or spec.loader is None:
        print(f"错误：无法加载测试用例文件 {testcase_file}")
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "TEST_CASES"):
        print(f"错误：测试用例文件中未找到 TEST_CASES")
        return None

    test_cases = module.TEST_CASES
    if case_name not in test_cases:
        print(f"错误：用例名称 '{case_name}' 不存在于测试用例文件中")
        print(f"可用的用例名称: {list(test_cases.keys())}")
        return None

    return test_cases[case_name]


def extract_ai_data(result_json: Dict) -> List[Dict]:
    """从 batch_query 结果中提取所有推广区域的 ai 维度数据（Xiaomi版本）"""
    ai_data_list = []

    # Xiaomi版本：result.result.dimensionMultiCountryResult
    result = result_json.get("data", {}).get("result", {})
    dimension_result = result.get("dimensionMultiCountryResult", {})

    for region_key, region_data in dimension_result.items():
        ai_list = region_data.get("corporation", [])
        # ai_list = region_data.get("ai", [])
        for ai_item in ai_list:
            # 过滤掉 media 列包含 TTL 的总计行
            media = ai_item.get("media", "")
            if media and "TTL" in media:
                continue

            ai_item["_region_key"] = region_key
            ai_data_list.append(ai_item)

    return ai_data_list


def parse_budget(budget_str: Any) -> float:
    """解析预算为浮点数"""
    if budget_str is None:
        return 0.0
    if isinstance(budget_str, (int, float)):
        return float(budget_str)
    if isinstance(budget_str, str):
        if not budget_str or budget_str == "-":
            return 0.0
        budget_str = budget_str.replace("%", "").replace(",", "").strip()
        try:
            return float(budget_str)
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def parse_kpi_value(kpi_obj: Any) -> float:
    """解析 KPI 值（Xiaomi版本：可能是对象或直接值）"""
    if isinstance(kpi_obj, dict):
        value = kpi_obj.get("value", "0")
    else:
        value = kpi_obj

    if value is None or value == "-" or value == "0":
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).replace("%", "").replace(",", "").strip()
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def extract_kpi_from_ai(ai_item: Dict) -> Dict[str, float]:
    """从 ai 数据项中提取 KPI 值（Xiaomi版本）"""
    kpi_values = {}

    # Xiaomi版本的KPI字段映射
    kpi_mapping = {
        "estImpression": "Impression",
        "estViews": "VideoViews",  # Xiaomi版本使用estViews而不是estVideoViews
        "estEngagement": "Engagement",
        "estClicks": "Clicks",  # Xiaomi版本使用estClicks而不是estClickAll
    }

    for est_field, kpi_name in kpi_mapping.items():
        if est_field in ai_item:
            kpi_values[kpi_name] = parse_kpi_value(ai_item[est_field])

    return kpi_values


def check_region_budget_achievement(
    result_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Any]:
    """检查区域预算是否达成（Xiaomi版本：已移除，返回空字典）"""
    # Xiaomi版本不再使用 regionBudget，此函数保留以兼容接口
    return {}


def check_region_kpi_achievement(
    result_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查区域 KPI 是否达成（Xiaomi版本：已移除，返回空字典）"""
    # Xiaomi版本不再使用 regionKPI，此函数保留以兼容接口
    return {}


def check_global_kpi_achievement(
    result_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Any]:
    """检查全局 KPI 是否达成"""
    # 从 result_json 中提取 basicInfo
    data = result_json.get("data", {})
    result = data.get("result", {})
    brief_info = result.get("briefInfo", {})
    basic_info = brief_info.get("basicInfo", {})

    # 提取全局 KPI 目标和 completion
    global_kpi_targets = {}
    global_kpi_completions = {}
    for kpi in basic_info.get("kpiInfo", []):
        kpi_key = kpi.get("key", "")
        kpi_val = kpi.get("val")
        # 区分 null 和 0：如果 val 是 None 或 "null"，则保留为 None；否则转换为 float
        if (
            kpi_val is None
            or kpi_val == "null"
            or (isinstance(kpi_val, str) and kpi_val.strip() == "")
        ):
            target_value = None
        else:
            try:
                # 如果 val 是字符串 "0"，转换为 0.0；如果是数字 0，保持为 0.0
                target_value = float(kpi_val)
            except (ValueError, TypeError):
                target_value = None

        global_kpi_targets[kpi_key] = {
            "target": target_value,
            "priority": kpi.get("priority", 999),
        }
        global_kpi_completions[kpi_key] = kpi.get("completion", 0)

    # 计算实际 KPI 值
    global_kpi_actual = {}
    for ai_item in ai_data_list:
        kpi_values = extract_kpi_from_ai(ai_item)
        for kpi_name, kpi_value in kpi_values.items():
            if kpi_name not in global_kpi_actual:
                global_kpi_actual[kpi_name] = 0.0
            global_kpi_actual[kpi_name] += kpi_value

    # 判断是否达成
    kpi_target_rate = testcase_config.get("kpi_target_rate", 80)
    kpi_must_achieve = testcase_config.get("kpi_must_achieve", False)
    results = {}

    for kpi_name, target_info in global_kpi_targets.items():
        target = target_info["target"]
        actual = global_kpi_actual.get(kpi_name, 0.0)
        completion = global_kpi_completions.get(kpi_name, 0)

        if target is None:
            # target 为 null 时，不进行判断
            achievement_rate = "null"
            achieved = False
        elif target == 0:
            achievement_rate = 0.0 if actual == 0 else "null"
            achieved = actual == 0
        else:
            raw_achievement_rate = (actual / target) * 100
            achievement_rate = round(raw_achievement_rate)
            if kpi_must_achieve or completion == 1:
                # 必须达成：要求实际值 >= 目标值
                achieved = actual >= target
            else:
                # 非必须达成：满足达成率条件即可
                achieved = achievement_rate >= kpi_target_rate

        results[kpi_name] = {
            "target": target,
            "actual": actual,
            "achievement_rate": achievement_rate,
            "target_rate": kpi_target_rate,
            "achieved": achieved,
            "priority": target_info["priority"],
            "completion": completion,
        }

    return results


def check_stage_budget_achievement(
    result_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查各区域下的 stage 维度预算是否满足"""
    # 从 result_json 中提取目标配置
    data = result_json.get("data", {})
    result = data.get("result", {})
    brief_info = result.get("briefInfo", {})
    brief_multi_config = brief_info.get("briefMultiConfig", [])

    target_stages = {}
    for country_config in brief_multi_config:
        country_code = country_config.get("countryInfo", {}).get("countryCode", "")
        target_stages[country_code] = {}

        for stage in country_config.get("stage", []):
            stage_name = stage.get("name", "")
            target_stages[country_code][stage_name] = {
                "target": stage.get("budgetAmount", 0),
                "target_percentage": stage.get("budgetPercentage", 0),
            }

    # 从 ai 数据聚合计算实际配置
    actual_stages = {}
    for ai_item in ai_data_list:
        country = ai_item.get("country", "")
        stage_name = ai_item.get("stage", "")

        if not country or not stage_name:
            continue

        if country not in actual_stages:
            actual_stages[country] = {}

        if stage_name not in actual_stages[country]:
            actual_stages[country][stage_name] = 0.0

        budget = parse_budget(ai_item.get("totalBudget", 0))
        actual_stages[country][stage_name] += budget

    # 计算百分比
    for country_code in actual_stages.keys():
        total_budget = sum(actual_stages[country_code].values())
        for stage_name in actual_stages[country_code].keys():
            actual_amount = actual_stages[country_code][stage_name]
            actual_percentage = (
                (actual_amount / total_budget * 100) if total_budget > 0 else 0.0
            )
            actual_stages[country_code][stage_name] = {
                "actual": actual_amount,
                "actual_percentage": actual_percentage,
            }

    # 判断是否满足
    stage_match_type = testcase_config.get("stage_match_type", "完全匹配")
    stage_range_match = testcase_config.get("stage_range_match", 20)
    results = {}

    # 合并所有国家代码
    all_countries = set(target_stages.keys()) | set(actual_stages.keys())

    for country_code in all_countries:
        results[country_code] = {}
        target_stage_data = target_stages.get(country_code, {})
        actual_stage_data = actual_stages.get(country_code, {})

        # 合并所有 stage 名称
        all_stages = set(target_stage_data.keys()) | set(actual_stage_data.keys())

        if stage_match_type == "大小关系匹配":
            # 大小关系匹配：检查顺序是否一致
            # 计算总预算用于判断"并列"阈值
            total_target_budget = sum(
                info.get("target", 0) for info in target_stage_data.values()
            )
            total_actual_budget = sum(
                info.get("actual", 0) for info in actual_stage_data.values()
            )
            target_diff_threshold = (
                total_target_budget / 10000.0 if total_target_budget > 0 else 0.0
            )
            actual_diff_threshold = (
                total_actual_budget / 10000.0 if total_actual_budget > 0 else 0.0
            )

            # 构建目标大小顺序（按 target_percentage 降序）
            target_order = sorted(
                target_stage_data.items(),
                key=lambda x: x[1].get("target_percentage", 0),
                reverse=True,
            )
            target_rank = {
                stage_name: rank for rank, (stage_name, _) in enumerate(target_order)
            }

            # 构建实际大小顺序（按 actual_percentage 降序）
            actual_order = sorted(
                actual_stage_data.items(),
                key=lambda x: x[1].get("actual_percentage", 0),
                reverse=True,
            )
            actual_rank = {
                stage_name: rank for rank, (stage_name, _) in enumerate(actual_order)
            }

            # 判断顺序是否一致
            order_consistent = True
            stage_list = list(all_stages)
            n = len(stage_list)
            for i in range(n):
                if not order_consistent:
                    break
                for j in range(i + 1, n):
                    si = stage_list[i]
                    sj = stage_list[j]
                    ti = target_rank.get(si, -1)
                    tj = target_rank.get(sj, -1)
                    ai = actual_rank.get(si, -1)
                    aj = actual_rank.get(sj, -1)
                    if ti < 0 or tj < 0 or ai < 0 or aj < 0:
                        continue

                    # 是否存在"相对顺序相反"的情况
                    inverted = (ti < tj and ai > aj) or (ti > tj and ai < aj)
                    if not inverted:
                        continue

                    # 检查两个 stage 是否可视为"并列"
                    target_i = target_stage_data.get(si, {}).get("target", 0)
                    target_j = target_stage_data.get(sj, {}).get("target", 0)
                    actual_i = actual_stage_data.get(si, {}).get("actual", 0)
                    actual_j = actual_stage_data.get(sj, {}).get("actual", 0)
                    target_diff = abs(target_i - target_j)
                    actual_diff = abs(actual_i - actual_j)
                    can_treat_as_tie = (
                        total_target_budget > 0
                        and total_actual_budget > 0
                        and target_diff < target_diff_threshold
                        and actual_diff < actual_diff_threshold
                    )

                    if not can_treat_as_tie:
                        order_consistent = False
                        break

        for stage_name in all_stages:
            target_info = target_stage_data.get(
                stage_name, {"target": 0, "target_percentage": 0}
            )
            actual_info = actual_stage_data.get(
                stage_name, {"actual": 0, "actual_percentage": 0}
            )

            target = target_info["target"]
            actual = actual_info["actual"]

            if target == 0:
                error_percentage = (
                    0.0 if actual_info["actual_percentage"] == 0 else "null"
                )
                satisfied = actual_info["actual_percentage"] == 0
            else:
                if stage_match_type == "完全匹配":
                    error_percentage = abs(
                        actual_info["actual_percentage"]
                        - target_info["target_percentage"]
                    )
                    error_percentage = round(error_percentage)
                    satisfied = error_percentage <= stage_range_match
                else:
                    # 大小关系匹配：检查顺序是否一致
                    satisfied = order_consistent
                    error_percentage = abs(
                        actual_info["actual_percentage"]
                        - target_info["target_percentage"]
                    )
                    error_percentage = round(error_percentage)

            result_item = {
                "target": target,
                "actual": actual,
                "error_percentage": error_percentage,
                "range_match": stage_range_match,
                "satisfied": satisfied,
                "target_percentage": target_info["target_percentage"],
                "actual_percentage": actual_info["actual_percentage"],
                "match_type": stage_match_type,
            }

            # 如果是大小关系匹配，添加排名信息
            if stage_match_type == "大小关系匹配":
                result_item["target_rank"] = target_rank.get(stage_name, -1)
                result_item["actual_rank"] = actual_rank.get(stage_name, -1)
                result_item["order_consistent"] = order_consistent

            results[country_code][stage_name] = result_item

    return results


def check_marketingfunnel_budget_achievement(
    result_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查各区域下的 marketingFunnel 维度预算是否满足"""
    # 从 result_json 中提取目标配置
    data = result_json.get("data", {})
    result = data.get("result", {})
    brief_info = result.get("briefInfo", {})
    brief_multi_config = brief_info.get("briefMultiConfig", [])

    target_funnels = {}
    for country_config in brief_multi_config:
        country_code = country_config.get("countryInfo", {}).get("countryCode", "")
        target_funnels[country_code] = {}

        for funnel in country_config.get("marketingFunnel", []):
            funnel_name = funnel.get("name", "")
            target_funnels[country_code][funnel_name] = {
                "target": funnel.get("budgetAmount", 0),
                "target_percentage": funnel.get("budgetPercentage", 0),
            }

    # 从 ai 数据聚合计算实际配置
    actual_funnels = {}
    for ai_item in ai_data_list:
        country = ai_item.get("country", "")
        funnel_name = ai_item.get("marketingFunnel", "")

        if not country or not funnel_name:
            continue

        if country not in actual_funnels:
            actual_funnels[country] = {}

        if funnel_name not in actual_funnels[country]:
            actual_funnels[country][funnel_name] = 0.0

        budget = parse_budget(ai_item.get("totalBudget", 0))
        actual_funnels[country][funnel_name] += budget

    # 计算百分比
    for country_code in actual_funnels.keys():
        total_budget = sum(actual_funnels[country_code].values())
        for funnel_name in actual_funnels[country_code].keys():
            actual_amount = actual_funnels[country_code][funnel_name]
            actual_percentage = (
                (actual_amount / total_budget * 100) if total_budget > 0 else 0.0
            )
            actual_funnels[country_code][funnel_name] = {
                "actual": actual_amount,
                "actual_percentage": actual_percentage,
            }

    # 判断是否满足
    funnel_match_type = testcase_config.get("marketingfunnel_match_type", "完全匹配")
    funnel_range_match = testcase_config.get("marketingfunnel_range_match", 15)
    results = {}

    # 合并所有国家代码
    all_countries = set(target_funnels.keys()) | set(actual_funnels.keys())

    for country_code in all_countries:
        results[country_code] = {}
        target_funnel_data = target_funnels.get(country_code, {})
        actual_funnel_data = actual_funnels.get(country_code, {})

        # 合并所有 funnel 名称
        all_funnels = set(target_funnel_data.keys()) | set(actual_funnel_data.keys())

        if funnel_match_type == "大小关系匹配":
            # 大小关系匹配：检查顺序是否一致
            # 计算总预算用于判断"并列"阈值
            total_target_budget = sum(
                info.get("target", 0) for info in target_funnel_data.values()
            )
            total_actual_budget = sum(
                info.get("actual", 0) for info in actual_funnel_data.values()
            )
            target_diff_threshold = (
                total_target_budget / 10000.0 if total_target_budget > 0 else 0.0
            )
            actual_diff_threshold = (
                total_actual_budget / 10000.0 if total_actual_budget > 0 else 0.0
            )

            # 构建目标大小顺序（按 target_percentage 降序）
            target_order = sorted(
                target_funnel_data.items(),
                key=lambda x: x[1].get("target_percentage", 0),
                reverse=True,
            )
            target_rank = {
                funnel_name: rank for rank, (funnel_name, _) in enumerate(target_order)
            }

            # 构建实际大小顺序（按 actual_percentage 降序）
            actual_order = sorted(
                actual_funnel_data.items(),
                key=lambda x: x[1].get("actual_percentage", 0),
                reverse=True,
            )
            actual_rank = {
                funnel_name: rank for rank, (funnel_name, _) in enumerate(actual_order)
            }

            # 判断顺序是否一致
            order_consistent = True
            funnel_list = list(all_funnels)
            n = len(funnel_list)
            for i in range(n):
                if not order_consistent:
                    break
                for j in range(i + 1, n):
                    fi = funnel_list[i]
                    fj = funnel_list[j]
                    ti = target_rank.get(fi, -1)
                    tj = target_rank.get(fj, -1)
                    ai = actual_rank.get(fi, -1)
                    aj = actual_rank.get(fj, -1)
                    if ti < 0 or tj < 0 or ai < 0 or aj < 0:
                        continue

                    # 是否存在"相对顺序相反"的情况
                    inverted = (ti < tj and ai > aj) or (ti > tj and ai < aj)
                    if not inverted:
                        continue

                    # 检查两个 funnel 是否可视为"并列"
                    target_i = target_funnel_data.get(fi, {}).get("target", 0)
                    target_j = target_funnel_data.get(fj, {}).get("target", 0)
                    actual_i = actual_funnel_data.get(fi, {}).get("actual", 0)
                    actual_j = actual_funnel_data.get(fj, {}).get("actual", 0)
                    target_diff = abs(target_i - target_j)
                    actual_diff = abs(actual_i - actual_j)
                    can_treat_as_tie = (
                        total_target_budget > 0
                        and total_actual_budget > 0
                        and target_diff < target_diff_threshold
                        and actual_diff < actual_diff_threshold
                    )

                    if not can_treat_as_tie:
                        order_consistent = False
                        break

        for funnel_name in all_funnels:
            target_info = target_funnel_data.get(
                funnel_name, {"target": 0, "target_percentage": 0}
            )
            actual_info = actual_funnel_data.get(
                funnel_name, {"actual": 0, "actual_percentage": 0}
            )

            target = target_info["target"]
            actual = actual_info["actual"]

            if target == 0:
                error_percentage = (
                    0.0 if actual_info["actual_percentage"] == 0 else "null"
                )
                satisfied = actual_info["actual_percentage"] == 0
            else:
                if funnel_match_type == "完全匹配":
                    error_percentage = abs(
                        actual_info["actual_percentage"]
                        - target_info["target_percentage"]
                    )
                    error_percentage = round(error_percentage)
                    satisfied = error_percentage <= funnel_range_match
                else:
                    # 大小关系匹配：检查顺序是否一致
                    satisfied = order_consistent
                    error_percentage = abs(
                        actual_info["actual_percentage"]
                        - target_info["target_percentage"]
                    )
                    error_percentage = round(error_percentage)

            result_item = {
                "target": target,
                "actual": actual,
                "error_percentage": error_percentage,
                "range_match": funnel_range_match,
                "satisfied": satisfied,
                "target_percentage": target_info["target_percentage"],
                "actual_percentage": actual_info["actual_percentage"],
                "match_type": funnel_match_type,
            }

            # 如果是大小关系匹配，添加排名信息
            if funnel_match_type == "大小关系匹配":
                result_item["target_rank"] = target_rank.get(funnel_name, -1)
                result_item["actual_rank"] = actual_rank.get(funnel_name, -1)
                result_item["order_consistent"] = order_consistent

            results[country_code][funnel_name] = result_item

    return results


def check_media_budget_achievement(
    result_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """检查各区域下的 media 维度预算是否满足（统计到 platform 层级）"""
    # 从 result_json 中提取目标配置（platform 层级）
    data = result_json.get("data", {})
    result = data.get("result", {})
    brief_info = result.get("briefInfo", {})
    brief_multi_config = brief_info.get("briefMultiConfig", [])

    target_media = {}
    for country_config in brief_multi_config:
        country_code = country_config.get("countryInfo", {}).get("countryCode", "")
        target_media[country_code] = {}

        for media in country_config.get("media", []):
            media_name = media.get("name", "")
            # 提取 platform 层级的预算配置
            for platform in media.get("children", []):
                platform_name = platform.get("name", "")
                key = f"{media_name}|{platform_name}"
                target_media[country_code][key] = {
                    "media": media_name,
                    "platform": platform_name,
                    "target": platform.get("budgetAmount", 0),
                    "target_percentage": platform.get("budgetPercentage", 0),
                }

    # 从 ai 数据聚合计算实际配置（按 country、media、platform 聚合）
    actual_media = {}
    for ai_item in ai_data_list:
        country = ai_item.get("country", "")
        media_name = ai_item.get("media", "")
        platform = ai_item.get("mediaChannel", "")

        if not country or not media_name or not platform:
            continue

        if country not in actual_media:
            actual_media[country] = {}

        key = f"{media_name}|{platform}"
        if key not in actual_media[country]:
            actual_media[country][key] = 0.0

        budget = parse_budget(ai_item.get("totalBudget", 0))
        actual_media[country][key] += budget

    # 计算百分比
    for country_code in actual_media.keys():
        total_budget = sum(actual_media[country_code].values())
        for key in actual_media[country_code].keys():
            actual_amount = actual_media[country_code][key]
            actual_percentage = (
                (actual_amount / total_budget * 100) if total_budget > 0 else 0.0
            )
            # 解析 media 和 platform
            parts = key.split("|")
            media_name = parts[0] if len(parts) > 0 else ""
            platform_name = parts[1] if len(parts) > 1 else ""
            actual_media[country_code][key] = {
                "media": media_name,
                "platform": platform_name,
                "actual": actual_amount,
                "actual_percentage": actual_percentage,
            }

    # 判断是否满足
    media_match_type = testcase_config.get("media_match_type", "完全匹配")
    media_range_match = testcase_config.get("media_range_match", 5)
    results = {}

    # 合并所有国家代码
    all_countries = set(target_media.keys()) | set(actual_media.keys())

    for country_code in all_countries:
        results[country_code] = {}
        target_media_data = target_media.get(country_code, {})
        actual_media_data = actual_media.get(country_code, {})

        # 合并所有 media|platform 键
        all_keys = set(target_media_data.keys()) | set(actual_media_data.keys())

        if media_match_type == "大小关系匹配":
            # 大小关系匹配：检查顺序是否一致
            # 计算总预算用于判断"并列"阈值
            total_target_budget = sum(
                info.get("target", 0) for info in target_media_data.values()
            )
            total_actual_budget = sum(
                info.get("actual", 0) for info in actual_media_data.values()
            )
            target_diff_threshold = (
                total_target_budget / 10000.0 if total_target_budget > 0 else 0.0
            )
            actual_diff_threshold = (
                total_actual_budget / 10000.0 if total_actual_budget > 0 else 0.0
            )

            # 构建目标大小顺序（按 target_percentage 降序）
            target_order = sorted(
                target_media_data.items(),
                key=lambda x: x[1].get("target_percentage", 0),
                reverse=True,
            )
            target_rank = {key: rank for rank, (key, _) in enumerate(target_order)}

            # 构建实际大小顺序（按 actual_percentage 降序）
            actual_order = sorted(
                actual_media_data.items(),
                key=lambda x: x[1].get("actual_percentage", 0),
                reverse=True,
            )
            actual_rank = {key: rank for rank, (key, _) in enumerate(actual_order)}

            # 判断顺序是否一致
            order_consistent = True
            key_list = list(all_keys)
            n = len(key_list)
            for i in range(n):
                if not order_consistent:
                    break
                for j in range(i + 1, n):
                    ki = key_list[i]
                    kj = key_list[j]
                    ti = target_rank.get(ki, -1)
                    tj = target_rank.get(kj, -1)
                    ai = actual_rank.get(ki, -1)
                    aj = actual_rank.get(kj, -1)
                    if ti < 0 or tj < 0 or ai < 0 or aj < 0:
                        continue

                    # 是否存在"相对顺序相反"的情况
                    inverted = (ti < tj and ai > aj) or (ti > tj and ai < aj)
                    if not inverted:
                        continue

                    # 检查两个 media|platform 是否可视为"并列"
                    target_i = target_media_data.get(ki, {}).get("target", 0)
                    target_j = target_media_data.get(kj, {}).get("target", 0)
                    actual_i = actual_media_data.get(ki, {}).get("actual", 0)
                    actual_j = actual_media_data.get(kj, {}).get("actual", 0)
                    target_diff = abs(target_i - target_j)
                    actual_diff = abs(actual_i - actual_j)
                    can_treat_as_tie = (
                        total_target_budget > 0
                        and total_actual_budget > 0
                        and target_diff < target_diff_threshold
                        and actual_diff < actual_diff_threshold
                    )

                    if not can_treat_as_tie:
                        order_consistent = False
                        break

        for key in all_keys:
            target_info = target_media_data.get(
                key, {"media": "", "platform": "", "target": 0, "target_percentage": 0}
            )
            actual_info = actual_media_data.get(
                key, {"media": "", "platform": "", "actual": 0, "actual_percentage": 0}
            )

            # 使用 target_info 中的 media 和 platform（如果存在），否则使用 actual_info
            media_name = target_info.get("media") or actual_info.get("media", "")
            platform_name = target_info.get("platform") or actual_info.get(
                "platform", ""
            )

            target = target_info["target"]
            actual = actual_info["actual"]

            if target == 0:
                error_percentage = (
                    0.0 if actual_info["actual_percentage"] == 0 else "null"
                )
                satisfied = actual_info["actual_percentage"] == 0
            else:
                if media_match_type == "完全匹配":
                    error_percentage = abs(
                        actual_info["actual_percentage"]
                        - target_info["target_percentage"]
                    )
                    error_percentage = round(error_percentage)
                    satisfied = error_percentage <= media_range_match
                else:
                    # 大小关系匹配：检查顺序是否一致
                    satisfied = order_consistent
                    error_percentage = abs(
                        actual_info["actual_percentage"]
                        - target_info["target_percentage"]
                    )
                    error_percentage = round(error_percentage)

            result_item = {
                "media": media_name,
                "platform": platform_name,
                "target": target,
                "actual": actual,
                "error_percentage": error_percentage,
                "range_match": media_range_match,
                "satisfied": satisfied,
                "target_percentage": target_info["target_percentage"],
                "actual_percentage": actual_info["actual_percentage"],
                "match_type": media_match_type,
            }

            # 如果是大小关系匹配，添加排名信息
            if media_match_type == "大小关系匹配":
                result_item["target_rank"] = target_rank.get(key, -1)
                result_item["actual_rank"] = actual_rank.get(key, -1)
                result_item["order_consistent"] = order_consistent

            results[country_code][key] = result_item

    return results


def check_mediaMarketingFunnelFormat_kpi_achievement(
    result_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查 mediaMarketingFunnelFormat 维度 KPI 是否达成（Xiaomi版本）"""
    # 从 result_json 中提取目标配置
    data = result_json.get("data", {})
    result = data.get("result", {})
    brief_info = result.get("briefInfo", {})
    brief_multi_config = brief_info.get("briefMultiConfig", [])

    target_formats = {}
    for country_config in brief_multi_config:
        country_code = country_config.get("countryInfo", {}).get("countryCode", "")

        for media_config in country_config.get("mediaMarketingFunnelFormat", []):
            media_name = media_config.get("mediaName", "")
            platform = (
                media_config.get("platform", [""])[0]
                if media_config.get("platform")
                else ""
            )

            for adformat in media_config.get("adFormatWithKPI", []):
                funnel_name = adformat.get("funnelName", "")
                adformat_name = adformat.get("adFormatName", "")
                creative = adformat.get("creative", "")

                key = f"{country_code}|{media_name}|{platform}|{funnel_name}|{adformat_name}"
                target_formats[key] = {
                    "country": country_code,
                    "media": media_name,
                    "platform": platform,
                    "funnel": funnel_name,
                    "adformat": adformat_name,
                    "creative": creative,
                    "kpis": {},
                }

                for kpi in adformat.get("kpiInfo", []):
                    kpi_key = kpi.get("key", "")
                    kpi_val = kpi.get("val")
                    # 区分 null 和 0：如果 val 是 None 或 "null"，则保留为 None；否则转换为 float
                    if (
                        kpi_val is None
                        or kpi_val == "null"
                        or (isinstance(kpi_val, str) and kpi_val.strip() == "")
                    ):
                        target_value = None
                    else:
                        try:
                            # 如果 val 是字符串 "0"，转换为 0.0；如果是数字 0，保持为 0.0
                            target_value = float(kpi_val)
                        except (ValueError, TypeError):
                            target_value = None

                    target_formats[key]["kpis"][kpi_key] = {
                        "target": target_value,
                        "priority": kpi.get("priority", 999),
                        "completion": kpi.get("completion", 0),
                    }

    # 从 ai 数据建立 (media, platform, objective, adformat) -> marketingFunnel 的映射
    funnel_mapping = {}  # (media, platform, objective, adformat) -> marketingFunnel
    for ai_item in ai_data_list:
        media = ai_item.get("media", "")
        platform = ai_item.get("mediaChannel", "")
        objective = ai_item.get("objective", "")
        adformat = ai_item.get("adFormat", "")
        funnel = ai_item.get("marketingFunnel", "")

        if media and platform and objective and adformat and funnel:
            mapping_key = (media, platform, objective, adformat)
            if mapping_key not in funnel_mapping:
                funnel_mapping[mapping_key] = funnel

    # 从 ai 数据聚合计算实际配置
    actual_formats = {}
    for ai_item in ai_data_list:
        country = ai_item.get("country", "")
        media = ai_item.get("media", "")
        platform = ai_item.get("mediaChannel", "")
        funnel = ai_item.get("marketingFunnel", "")
        adformat = ai_item.get("adFormat", "")
        creative = ai_item.get("creative", "")

        if not country:
            continue

        key = f"{country}|{media}|{platform}|{funnel}|{adformat}"

        if key not in actual_formats:
            actual_formats[key] = {}

        kpi_values = extract_kpi_from_ai(ai_item)
        for kpi_name, kpi_value in kpi_values.items():
            if kpi_name not in actual_formats[key]:
                actual_formats[key][kpi_name] = 0.0
            actual_formats[key][kpi_name] += kpi_value

    # 判断是否达成
    format_target_rate = testcase_config.get(
        "mediaMarketingFunnelFormat_target_rate", 80
    )
    format_must_achieve = testcase_config.get(
        "mediaMarketingFunnelFormat_must_achieve", False
    )
    results = {}

    # 为每个 target key 尝试匹配 actual key
    for target_key, target_info in target_formats.items():
        # 解析 target key
        target_key_parts = target_key.split("|")
        if len(target_key_parts) < 5:
            continue

        country_code = target_key_parts[0]
        media_name = target_key_parts[1]
        platform = target_key_parts[2]
        funnel_name = target_key_parts[3]  # 可能为空
        adformat_name = target_key_parts[4]
        # creative 从 target_info 中获取
        creative = target_info.get("creative", "")

        # 如果 target 的 funnel 为空，需要通过 media, platform, objective, adformat 推导
        if not funnel_name:
            # 从 ai_data_list 中找到对应的 objective
            objective = None
            for ai_item in ai_data_list:
                if (
                    ai_item.get("country") == country_code
                    and ai_item.get("media") == media_name
                    and ai_item.get("mediaChannel") == platform
                    and ai_item.get("adFormat") == adformat_name
                ):
                    objective = ai_item.get("objective", "")
                    break

            # 通过映射推导 marketingFunnel
            if objective:
                mapping_key = (media_name, platform, objective, adformat_name)
                if mapping_key in funnel_mapping:
                    funnel_name = funnel_mapping[mapping_key]

        # 构建匹配的 actual key（不包含 creative）
        actual_key = (
            f"{country_code}|{media_name}|{platform}|{funnel_name}|{adformat_name}"
        )

        # 获取 actual 数据
        kpi_actual = actual_formats.get(actual_key, {})

        # 构建结果（不包含 creative）
        result_key = (
            f"{country_code}|{media_name}|{platform}|{funnel_name}|{adformat_name}"
        )
        results[result_key] = {
            "country": country_code,
            "media": media_name,
            "platform": platform,
            "funnel": funnel_name,
            "adformat": adformat_name,
            "creative": creative,
            "kpis": {},
        }

        for kpi_name, kpi_target_info in target_info["kpis"].items():
            target = kpi_target_info["target"]
            actual = kpi_actual.get(kpi_name, 0.0)
            completion = kpi_target_info.get("completion", 0)

            if target is None:
                # target 为 null 时，不进行判断
                achievement_rate = "null"
                achieved = False
            elif target == 0:
                achievement_rate = 0.0 if actual == 0 else "null"
                achieved = actual == 0
            else:
                raw_achievement_rate = (actual / target) * 100
                achievement_rate = round(raw_achievement_rate)
                if format_must_achieve or completion == 1:
                    achieved = actual >= target
                else:
                    achieved = achievement_rate >= format_target_rate

            results[result_key]["kpis"][kpi_name] = {
                "target": target,
                "actual": actual,
                "achievement_rate": achievement_rate,
                "target_rate": format_target_rate,
                "achieved": achieved,
                "priority": kpi_target_info["priority"],
                "completion": completion,
            }

    return results


def check_mediaMarketingFunnelFormatBudgetConfig_budget_achievement(
    result_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查 mediaMarketingFunnelFormatBudgetConfig 维度预算是否满足（Xiaomi版本）"""
    # 从 result_json 中提取配置
    data = result_json.get("data", {})
    result = data.get("result", {})
    brief_info = result.get("briefInfo", {})
    brief_multi_config = brief_info.get("briefMultiConfig", [])

    # 从 result_json 中提取 totalBudgetFlexibility
    total_budget_flexibility = 80  # 默认值
    for country_config in brief_multi_config:
        budget_config = country_config.get("mediaMarketingFunnelFormatBudgetConfig", {})
        if budget_config and "totalBudgetFlexibility" in budget_config:
            total_budget_flexibility = budget_config.get("totalBudgetFlexibility", 80)
            break

    # 从 result_json 的 adFormatWithKPI 中提取目标配置
    target_configs = {}
    for country_config in brief_multi_config:
        country_code = country_config.get("countryInfo", {}).get("countryCode", "")
        target_configs[country_code] = {}

        for media_config in country_config.get("mediaMarketingFunnelFormat", []):
            media_name = media_config.get("mediaName", "")
            platform = (
                media_config.get("platform", [""])[0]
                if media_config.get("platform")
                else ""
            )

            for adformat in media_config.get("adFormatWithKPI", []):
                funnel_name = adformat.get("funnelName", "")
                adformat_name = adformat.get("adFormatName", "")
                creative = adformat.get("creative", "")
                ad_format_total_budget = adformat.get("adFormatTotalBudget")
                completion = adformat.get("completion", 0)

                key = f"{media_name}|{platform}|{funnel_name}|{adformat_name}"
                target_configs[country_code][key] = {
                    "target": (
                        float(ad_format_total_budget)
                        if ad_format_total_budget
                        else None
                    ),
                    "completion": completion,
                    "creative": creative,  # 保存 creative 以便后续使用
                }

    # 从 ai 数据建立 (media, platform, objective, adformat) -> marketingFunnel 的映射
    funnel_mapping = {}  # (media, platform, objective, adformat) -> marketingFunnel
    for ai_item in ai_data_list:
        media = ai_item.get("media", "")
        platform = ai_item.get("mediaChannel", "")
        objective = ai_item.get("objective", "")
        adformat = ai_item.get("adFormat", "")
        funnel = ai_item.get("marketingFunnel", "")

        if media and platform and objective and adformat and funnel:
            mapping_key = (media, platform, objective, adformat)
            if mapping_key not in funnel_mapping:
                funnel_mapping[mapping_key] = funnel

    # 从 ai 数据聚合计算实际配置
    actual_configs = {}
    for ai_item in ai_data_list:
        country = ai_item.get("country", "")
        media = ai_item.get("media", "")
        platform = ai_item.get("mediaChannel", "")
        funnel = ai_item.get("marketingFunnel", "")
        adformat = ai_item.get("adFormat", "")
        creative = ai_item.get("creative", "")

        if not country:
            continue

        key = f"{media}|{platform}|{funnel}|{adformat}"

        if country not in actual_configs:
            actual_configs[country] = {}

        if key not in actual_configs[country]:
            actual_configs[country][key] = 0.0

        budget = parse_budget(ai_item.get("totalBudget", 0))
        actual_configs[country][key] += budget

    # 判断是否满足
    results = {}

    all_countries = set(target_configs.keys()) | set(actual_configs.keys())

    for country_code in all_countries:
        target_data = target_configs.get(country_code, {})
        actual_data = actual_configs.get(country_code, {})

        # 为每个 target key 尝试匹配 actual key
        for target_key, target_info in target_data.items():
            # 解析 target key（不包含 creative）
            target_key_parts = target_key.split("|")
            if len(target_key_parts) < 4:
                continue

            media_name = target_key_parts[0]
            platform = target_key_parts[1]
            funnel_name = target_key_parts[2]  # 可能为空
            adformat_name = target_key_parts[3]
            # creative 从 target_info 中获取（不再作为 key 的一部分）
            creative = target_info.get("creative", "")

            # 如果 target 的 funnel 为空，需要通过 media, platform, objective, adformat 推导
            if not funnel_name:
                # 从 ai_data_list 中找到对应的 objective
                objective = None
                for ai_item in ai_data_list:
                    if (
                        ai_item.get("country") == country_code
                        and ai_item.get("media") == media_name
                        and ai_item.get("mediaChannel") == platform
                        and ai_item.get("adFormat") == adformat_name
                    ):
                        objective = ai_item.get("objective", "")
                        break

                # 通过映射推导 marketingFunnel
                if objective:
                    mapping_key = (media_name, platform, objective, adformat_name)
                    if mapping_key in funnel_mapping:
                        funnel_name = funnel_mapping[mapping_key]

            # 构建匹配的 actual key（不包含 creative）
            actual_key = f"{media_name}|{platform}|{funnel_name}|{adformat_name}"

            # 获取 actual 数据
            actual_amount = actual_data.get(actual_key, 0.0)
            if isinstance(actual_amount, dict):
                actual_amount = actual_amount.get("actual", 0.0)

            target = target_info["target"]
            actual = actual_amount
            completion = target_info.get("completion", 0)

            # 计算达成率和判断是否满足
            if target is None:
                achievement_rate = "null"
                achieved = True
                min_required = 0
            elif target == 0:
                achievement_rate = 0.0 if actual == 0 else "null"
                achieved = actual == 0
                min_required = 0
            else:
                # 计算达成率
                raw_achievement_rate = (actual / target) * 100
                achievement_rate = round(raw_achievement_rate)

                # 根据 completion 判断：
                # completion = 1: actual >= target
                # completion = 0: actual >= target * totalBudgetFlexibility / 100
                if completion == 1:
                    min_required = target
                    achieved = actual >= target
                else:
                    min_required = target * total_budget_flexibility / 100
                    # 使用达成率判断，避免浮点数精度问题
                    # 如果达成率 >= target_rate，则认为达成
                    achieved = achievement_rate >= total_budget_flexibility

            # 构建结果键（包含 country_code，与 KPI 检查保持一致）
            # 使用推导出的 funnel_name（如果为空则保持为空）
            result_key = (
                f"{country_code}|{media_name}|{platform}|{funnel_name}|{adformat_name}"
            )

            results[result_key] = {
                "country": country_code,
                "media": media_name,
                "platform": platform,
                "funnel": funnel_name,
                "adformat": adformat_name,
                "creative": creative,
                "target": target,
                "actual": actual,
                "achievement_rate": achievement_rate,
                "target_rate": total_budget_flexibility,
                "achieved": achieved,
                "completion": completion,
                "min_required": min_required,
                "total_budget_flexibility": total_budget_flexibility,
            }

        # 处理只有 actual 但没有 target 的情况（可选，根据需求决定是否保留）
        for actual_key, actual_amount in actual_data.items():
            # 检查是否已经在 results 中处理过
            actual_key_parts = actual_key.split("|")
            if len(actual_key_parts) >= 5:
                media_name = actual_key_parts[0]
                platform = actual_key_parts[1]
                funnel_name = actual_key_parts[2]
                adformat_name = actual_key_parts[3]
                creative = actual_key_parts[4]

                result_key = f"{country_code}|{media_name}|{platform}|{funnel_name}|{adformat_name}"
                if result_key not in results:
                    # 没有对应的 target，标记为未达成
                    if isinstance(actual_amount, dict):
                        actual_amount = actual_amount.get("actual", 0.0)

                    results[result_key] = {
                        "country": country_code,
                        "media": media_name,
                        "platform": platform,
                        "funnel": funnel_name,
                        "adformat": adformat_name,
                        "creative": creative,
                        "target": None,
                        "actual": actual_amount,
                        "achievement_rate": "null",
                        "target_rate": total_budget_flexibility,
                        "achieved": False,
                        "completion": 0,
                        "min_required": 0,
                        "total_budget_flexibility": total_budget_flexibility,
                    }

    return results


def check_adformat_budget_allocation(
    result_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查每个推广区域下每个 AdFormat 是否都分配了预算（当 allow_zero_budget 为 False 时，Xiaomi版本）"""
    allow_zero_budget = testcase_config.get("allow_zero_budget", False)

    if allow_zero_budget:
        return {}

    # 从 result_json 中提取目标配置
    data = result_json.get("data", {})
    result = data.get("result", {})
    brief_info = result.get("briefInfo", {})
    brief_multi_config = brief_info.get("briefMultiConfig", [])

    # 提取目标 AdFormat 配置
    target_formats = {}
    for country_config in brief_multi_config:
        country_code = country_config.get("countryInfo", {}).get("countryCode", "")
        target_formats[country_code] = {}

        for media_config in country_config.get("mediaMarketingFunnelFormat", []):
            media_name = media_config.get("mediaName", "")
            platform = (
                media_config.get("platform", [""])[0]
                if media_config.get("platform")
                else ""
            )

            for adformat in media_config.get("adFormatWithKPI", []):
                funnel_name = adformat.get("funnelName", "")
                adformat_name = adformat.get("adFormatName", "")
                key = f"{media_name}|{platform}|{funnel_name}|{adformat_name}"
                target_formats[country_code][key] = {
                    "media": media_name,
                    "platform": platform,
                    "funnel": funnel_name,
                    "adformat": adformat_name,
                }

    # 从 ai 数据聚合计算实际预算
    actual_formats = {}
    for ai_item in ai_data_list:
        country = ai_item.get("country", "")
        media = ai_item.get("media", "")
        platform = ai_item.get("mediaChannel", "")
        funnel = ai_item.get("marketingFunnel", "")
        adformat = ai_item.get("adFormat", "")

        if not country or not media or not platform or not adformat:
            continue

        key = f"{media}|{platform}|{funnel}|{adformat}"

        if country not in actual_formats:
            actual_formats[country] = {}

        if key not in actual_formats[country]:
            actual_formats[country][key] = {
                "media": media,
                "platform": platform,
                "funnel": funnel,
                "adformat": adformat,
                "budget": 0.0,
            }

        budget = parse_budget(ai_item.get("totalBudget", 0))
        actual_formats[country][key]["budget"] += budget

    # 判断是否满足
    results = {}
    all_countries = set(target_formats.keys()) | set(actual_formats.keys())

    for country_code in all_countries:
        results[country_code] = {}
        target_data = target_formats.get(country_code, {})
        actual_data = actual_formats.get(country_code, {})

        all_keys = set(target_data.keys()) | set(actual_data.keys())

        for key in all_keys:
            target_info = target_data.get(key, {})
            actual_info = actual_data.get(key, {"budget": 0.0})

            budget = actual_info.get("budget", 0.0)
            satisfied = budget > 0

            results[country_code][key] = {
                "media": target_info.get("media") or actual_info.get("media", ""),
                "platform": target_info.get("platform")
                or actual_info.get("platform", ""),
                "funnel": target_info.get("funnel") or actual_info.get("funnel", ""),
                "adformat": target_info.get("adformat")
                or actual_info.get("adformat", ""),
                "budget": budget,
                "satisfied": satisfied,
            }

    return results


def print_achievement_summary(results: Dict[str, Any], testcase_config: Dict[str, Any]):
    """打印达成情况摘要"""
    print("\n" + "=" * 80)
    print("指标达成情况判断")
    print("=" * 80)

    print(f"\n测试用例配置:")
    print(f"  KPI目标达成率: {testcase_config.get('kpi_target_rate', 80)}%")
    print(f"  阶段预算误差范围: {testcase_config.get('stage_range_match', 20)}%")
    print(
        f"  营销漏斗预算误差范围: {testcase_config.get('marketingfunnel_range_match', 15)}%"
    )
    print(f"  媒体预算误差范围: {testcase_config.get('media_range_match', 5)}%")
    print(
        f"  adformat KPI目标达成率: {testcase_config.get('mediaMarketingFunnelFormat_target_rate', 80)}%"
    )
    print(
        f"  adformat预算目标达成率: {testcase_config.get('mediaMarketingFunnelFormatBudgetConfig_target_rate', 80)}%"
    )

    # 全局 KPI
    if "global_kpi" in results:
        print(f"\n【全局 KPI 达成情况】")
        global_kpi = results["global_kpi"]
        # 过滤掉target为0的KPI，不计入统计
        valid_kpis = {k: v for k, v in global_kpi.items() if v.get("target", 0) != 0}
        achieved_count = sum(1 for v in valid_kpis.values() if v.get("achieved", False))
        total_count = len(valid_kpis)
        print(f"  达成: {achieved_count}/{total_count}")
        for kpi_name in sorted(
            global_kpi.keys(), key=lambda x: global_kpi[x].get("priority", 999)
        ):
            kpi_data = global_kpi[kpi_name]
            status = "[OK]" if kpi_data["achieved"] else "[FAIL]"
            print(
                f"  {status} {kpi_name} (优先级 {kpi_data['priority']}): "
                f"实际={kpi_data['actual']:,.0f}, 目标={kpi_data['target']:,.0f}, "
                f"达成率={kpi_data['achievement_rate']:.2f}% "
                f"(目标达成率: {kpi_data['target_rate']}%)"
            )

    # Stage 预算
    if "stage_budget" in results:
        print(f"\n【阶段预算满足情况】")
        stage_budget = results["stage_budget"]
        total_satisfied = 0
        total_count = 0
        for country_code in sorted(stage_budget.keys()):
            country_stages = stage_budget[country_code]
            country_satisfied = sum(
                1 for v in country_stages.values() if v.get("satisfied", False)
            )
            country_total = len(country_stages)
            total_satisfied += country_satisfied
            total_count += country_total
            print(f"\n  {country_code}: 满足 {country_satisfied}/{country_total}")
            for stage_name in sorted(country_stages.keys()):
                stage_data = country_stages[stage_name]
                status = "[OK]" if stage_data["satisfied"] else "[FAIL]"
                error = stage_data["error_percentage"]
                error_str = (
                    f"{error:.2f}%" if isinstance(error, (int, float)) else str(error)
                )
                print(
                    f"    {status} {stage_name}: "
                    f"实际={stage_data['actual']:,.2f}, 目标={stage_data['target']:,.2f}, "
                    f"误差={error_str} "
                    f"(允许误差: {stage_data['range_match']}%)"
                )
        print(f"\n  总体满足: {total_satisfied}/{total_count}")

    # MarketingFunnel 预算
    if "marketingfunnel_budget" in results:
        print(f"\n【营销漏斗预算满足情况】")
        funnel_budget = results["marketingfunnel_budget"]
        total_satisfied = 0
        total_count = 0
        for country_code in sorted(funnel_budget.keys()):
            country_funnels = funnel_budget[country_code]
            country_satisfied = sum(
                1 for v in country_funnels.values() if v.get("satisfied", False)
            )
            country_total = len(country_funnels)
            total_satisfied += country_satisfied
            total_count += country_total
            print(f"\n  {country_code}: 满足 {country_satisfied}/{country_total}")
            for funnel_name in sorted(country_funnels.keys()):
                funnel_data = country_funnels[funnel_name]
                status = "[OK]" if funnel_data["satisfied"] else "[FAIL]"
                error = funnel_data["error_percentage"]
                error_str = (
                    f"{error:.2f}%" if isinstance(error, (int, float)) else str(error)
                )
                print(
                    f"    {status} {funnel_name}: "
                    f"实际={funnel_data['actual']:,.2f}, 目标={funnel_data['target']:,.2f}, "
                    f"误差={error_str} "
                    f"(允许误差: {funnel_data['range_match']}%)"
                )
        print(f"\n  总体满足: {total_satisfied}/{total_count}")

    # Media 预算
    if "media_budget" in results:
        print(f"\n【媒体预算满足情况】")
        media_budget = results["media_budget"]
        total_satisfied = 0
        total_count = 0
        for country_code in sorted(media_budget.keys()):
            country_media = media_budget[country_code]
            country_satisfied = sum(
                1 for v in country_media.values() if v.get("satisfied", False)
            )
            country_total = len(country_media)
            total_satisfied += country_satisfied
            total_count += country_total
            print(f"\n  {country_code}: 满足 {country_satisfied}/{country_total}")
            for media_name in sorted(country_media.keys()):
                media_data = country_media[media_name]
                status = "[OK]" if media_data["satisfied"] else "[FAIL]"
                error = media_data["error_percentage"]
                error_str = (
                    f"{error:.2f}%" if isinstance(error, (int, float)) else str(error)
                )
                print(
                    f"    {status} {media_name}: "
                    f"实际={media_data['actual']:,.2f}, 目标={media_data['target']:,.2f}, "
                    f"误差={error_str} "
                    f"(允许误差: {media_data['range_match']}%)"
                )
        print(f"\n  总体满足: {total_satisfied}/{total_count}")

    # adformat kpi（汇总）
    if "mediaMarketingFunnelFormat_kpi" in results:
        print(f"\n【adformat KPI 达成情况（汇总）】")
        format_kpi = results["mediaMarketingFunnelFormat_kpi"]
        total_achieved = 0
        total_count = 0
        for key, format_data in format_kpi.items():
            kpis = format_data.get("kpis", {})
            for kpi_name, kpi_data in kpis.items():
                # 过滤掉target为0的KPI，不计入统计
                if kpi_data.get("target", 0) != 0:
                    total_count += 1
                    if kpi_data.get("achieved", False):
                        total_achieved += 1
        print(f"  总体达成: {total_achieved}/{total_count}")
        print(f"  (详细数据请查看输出 JSON 文件)")

    # adformat预算非0检查
    if "adformat_budget_allocation" in results:
        print(f"\n【adformat预算非0检查】")
        adformat_allocation = results["adformat_budget_allocation"]
        total_satisfied = 0
        total_count = 0
        for country_code in sorted(adformat_allocation.keys()):
            country_formats = adformat_allocation[country_code]
            country_satisfied = sum(
                1 for v in country_formats.values() if v.get("satisfied", False)
            )
            country_total = len(country_formats)
            total_satisfied += country_satisfied
            total_count += country_total
            print(f"\n  {country_code}: 满足 {country_satisfied}/{country_total}")
            unsatisfied = [
                (k, v)
                for k, v in country_formats.items()
                if not v.get("satisfied", False)
            ]
            if unsatisfied:
                for key, format_data in sorted(unsatisfied, key=lambda x: x[0]):
                    funnel_str = (
                        f" | {format_data.get('funnel', '')}"
                        if format_data.get("funnel")
                        else ""
                    )
                    print(
                        f"    [FAIL] {format_data['media']} | {format_data['platform']}{funnel_str} | {format_data['adformat']}: "
                        f"预算={format_data['budget']:,.2f}"
                    )
        print(f"\n  总体满足: {total_satisfied}/{total_count}")


def main():
    parser = argparse.ArgumentParser(
        description="根据 testcase 配置判断每个指标是否达成"
    )
    parser.add_argument(
        "--testcase-file",
        type=str,
        required=False,
        help="测试用例文件路径（Python文件，已废弃，将从 result_json 中提取）",
    )
    parser.add_argument(
        "--request-file",
        type=str,
        required=False,
        help="请求 JSON 文件路径（已废弃，将从 result_json 中提取）",
    )
    parser.add_argument(
        "--result-file",
        type=str,
        required=True,
        help="batch_query 结果 JSON 文件路径",
    )
    parser.add_argument(
        "--case-name",
        type=str,
        required=False,
        help="测试用例名称（可选，将从文件名中提取）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出文件路径（可选）",
    )

    args = parser.parse_args()

    # 加载文件
    result_file = Path(args.result_file)

    if not result_file.exists():
        print(f"错误：结果文件不存在: {result_file}")
        return 1

    # 加载结果文件
    result_json = load_json(result_file)

    # 从 result_json 中提取 testcase_config
    testcase_config = extract_testcase_config_from_result(result_json)

    # 从文件名中提取 case_name（如果未提供）
    if not args.case_name:
        case_name = result_file.stem.replace("mp_result_", "")
    else:
        case_name = args.case_name

    # 提取 uuid 和 job_id（Xiaomi版本：从result.briefInfo.basicInfo中提取）
    brief_info = result_json.get("result", {}).get("briefInfo", {})
    basic_info = brief_info.get("basicInfo", {})
    uuid = result_json.get("uuid")
    job_id = result_json.get("job_id")

    # 提取 ai 数据
    ai_data_list = extract_ai_data(result_json)
    print(f"提取到 {len(ai_data_list)} 条 ai 维度数据")
    if uuid:
        print(f"UUID: {uuid}")
    if job_id:
        print(f"Job ID: {job_id}")

    # 检查各项指标
    results = {
        "case_name": case_name,
        "uuid": uuid,
        "job_id": job_id,
        "testcase_config": testcase_config,
        "global_kpi": check_global_kpi_achievement(
            result_json, ai_data_list, testcase_config
        ),
        "region_budget": check_region_budget_achievement(
            result_json, ai_data_list, testcase_config
        ),
        "region_kpi": check_region_kpi_achievement(
            result_json, ai_data_list, testcase_config
        ),
        "stage_budget": check_stage_budget_achievement(
            result_json, ai_data_list, testcase_config
        ),
        "marketingfunnel_budget": check_marketingfunnel_budget_achievement(
            result_json, ai_data_list, testcase_config
        ),
        "media_budget": check_media_budget_achievement(
            result_json, ai_data_list, testcase_config
        ),
        "mediaMarketingFunnelFormat_kpi": check_mediaMarketingFunnelFormat_kpi_achievement(
            result_json, ai_data_list, testcase_config
        ),
        "mediaMarketingFunnelFormatBudgetConfig_budget": check_mediaMarketingFunnelFormatBudgetConfig_budget_achievement(
            result_json, ai_data_list, testcase_config
        ),
    }

    # 检查 AdFormat 预算分配（当 allow_zero_budget 为 False 时，Xiaomi版本）
    adformat_allocation = check_adformat_budget_allocation(
        result_json, ai_data_list, testcase_config
    )
    if adformat_allocation:
        results["adformat_budget_allocation"] = adformat_allocation

    # 打印摘要
    print_achievement_summary(results, testcase_config)

    # 保存结果
    if args.output:
        # 如果传入的是目录，则在目录下生成默认文件名；如果是文件，则直接使用
        output_base = Path(args.output)
        if output_base.is_dir() or output_base.suffix == "":
            output_base.mkdir(parents=True, exist_ok=True)
            base_name = result_file.stem.replace("mp_result_", "")
            if job_id:
                output_file = (
                    output_base / f"{base_name}_{job_id}_achievement_check.json"
                )
            else:
                output_file = output_base / f"{result_file.stem}_achievement_check.json"
        else:
            output_base.parent.mkdir(parents=True, exist_ok=True)
            output_file = output_base
    else:
        # 默认输出到 output/{common|xiaomi}/achievement_checks/json/ 目录
        # 根据结果文件路径判断是 common 还是 xiaomi
        result_parent = result_file.parent
        if result_parent.name == "results":
            # 新结构：output/common/results 或 output/xiaomi/results
            output_base = result_parent.parent  # output/common 或 output/xiaomi
        elif result_parent.name == "batch_query_results":
            # 旧结构兼容
            output_base = result_parent.parent
        else:
            output_base = result_parent

        achievement_checks_dir = output_base / "achievement_checks"
        json_dir = achievement_checks_dir / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        # 构建文件名，如果存在 job_id 则包含在文件名中
        base_name = result_file.stem.replace("mp_result_", "")
        if job_id:
            output_file = json_dir / f"{base_name}_{job_id}_achievement_check.json"
        else:
            output_file = json_dir / f"{result_file.stem}_achievement_check.json"

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存到: {output_file}")

    # 自动生成测试报告
    try:
        # 从 core 模块导入（使用通用报告生成器，支持 xiaomi 结构）
        from core.generate_test_report import (
            generate_markdown_report,
            generate_html_report,
        )

        # 报告文件输出到 achievement_checks/reports/ 目录
        achievement_checks_dir = output_file.parent.parent
        reports_dir = achievement_checks_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        md_path = reports_dir / f"{output_file.stem}.md"
        html_path = reports_dir / f"{output_file.stem}.html"
        generate_markdown_report(results, md_path)
        generate_html_report(results, html_path)
        print(f"测试报告已生成:")
        print(f"  - Markdown: {md_path}")
        print(f"  - HTML: {html_path}")
    except Exception as e:
        print(f"警告: 生成测试报告时出错: {e}")
        print(
            "可以手动运行: python core/generate_test_report.py --result-file <json文件>"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
