#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 testcase 配置判断每个指标是否达成

用法:
    python core/check_kpi_achievement.py \
        --testcase-file testcase_template.py \
        --request-file single/brief_case_全部填写-完全匹配-5%-区域第一-KPI第二.json \
        --result-file single/batch_query_results/batch_query_全部填写-完全匹配-5%-区域第一-KPI第二.json \
        --case-name "全部填写-完全匹配-5%-区域第一-KPI第二"
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
    """从 batch_query 结果中提取所有推广区域的 ai 维度数据"""
    ai_data_list = []

    data = result_json.get("data", {})
    result = data.get("result", {})
    dimension_result = result.get("dimensionMultiCountryResult", {})

    for region_key, region_data in dimension_result.items():
        ai_list = region_data.get("corporation", [])
        for ai_item in ai_list:
            ai_item["_region_key"] = region_key
            ai_data_list.append(ai_item)

    return ai_data_list


def parse_budget(budget_str: str) -> float:
    """解析预算字符串为浮点数"""
    if not budget_str or budget_str == "-":
        return 0.0
    budget_str = budget_str.replace("%", "").replace(",", "").strip()
    try:
        return float(budget_str)
    except (ValueError, TypeError):
        return 0.0


def parse_kpi_value(kpi_obj: Dict) -> float:
    """解析 KPI 值"""
    if isinstance(kpi_obj, dict):
        value = kpi_obj.get("value", "0")
    else:
        value = str(kpi_obj)

    if not value or value == "-" or value == "0":
        return 0.0

    value = str(value).replace("%", "").replace(",", "").strip()
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def extract_kpi_from_ai(ai_item: Dict) -> Dict[str, float]:
    """从 ai 数据项中提取 KPI 值"""
    kpi_values = {}

    kpi_mapping = {
        "estImpression": "Impression",
        "estVideoViews": "VideoViews",
        "estEngagement": "Engagement",
        "estClickAll": "Clicks",
        "estLinkClicks": "LinkClicks",
        "estFollowers": "Followers",
        "estLike": "Like",
        "estPurchase": "Purchase",
    }

    for est_field, kpi_name in kpi_mapping.items():
        if est_field in ai_item:
            kpi_values[kpi_name] = parse_kpi_value(ai_item[est_field])

    return kpi_values


def check_global_kpi_achievement(
    request_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Any]:
    """检查全局 KPI 是否达成"""
    basic_info = request_json.get("basicInfo", {})

    # 提取全局 KPI 目标和 completion
    global_kpi_targets = {}
    global_kpi_completions = {}
    for kpi in basic_info.get("kpiInfo", []):
        kpi_key = kpi.get("key", "")
        global_kpi_targets[kpi_key] = {
            "target": float(kpi.get("val", "0") or 0),
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
    results = {}

    for kpi_name, target_info in global_kpi_targets.items():
        target = target_info["target"]
        actual = global_kpi_actual.get(kpi_name, 0.0)
        completion = global_kpi_completions.get(kpi_name, 0)

        if target == 0:
            achievement_rate = 0.0 if actual == 0 else "null"
            # target 为 0 时，只要 actual 也为 0 即达成，不再区分 completion
            achieved = actual == 0
        else:
            # 使用整数百分比进行判断，避免精度问题
            raw_achievement_rate = (actual / target) * 100
            achievement_rate = round(raw_achievement_rate)
            # 无论 completion 是否为 1，一律按整数达成率与 target_rate 判断
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


def check_region_budget_achievement(
    request_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Any]:
    """检查区域预算是否达成"""
    basic_info = request_json.get("basicInfo", {})

    # 提取区域预算目标和 completion
    region_budget_targets = {}
    region_completions = {}
    for region in basic_info.get("regionBudget", []):
        country_code = region.get("country", {}).get("code", "")
        region_budget_targets[country_code] = {
            "target": region.get("budgetAmount", 0),
            "budget_percentage": region.get("budgetPercentage", 0),
        }
        region_completions[country_code] = region.get("completion", 0)

    # 计算实际区域预算
    region_budget_actual = {}
    total_actual_budget = 0.0
    for ai_item in ai_data_list:
        region = ai_item.get("region", "")
        country_code = region.split("_")[0] if "_" in region else region

        if country_code not in region_budget_actual:
            region_budget_actual[country_code] = 0.0

        budget = parse_budget(ai_item.get("adTypeBudget", "0"))
        region_budget_actual[country_code] += budget
        total_actual_budget += budget

    # 计算实际预算占比
    region_budget_actual_percentage = {}
    for country_code, actual_budget in region_budget_actual.items():
        if total_actual_budget > 0:
            region_budget_actual_percentage[country_code] = (
                actual_budget / total_actual_budget * 100
            )
        else:
            region_budget_actual_percentage[country_code] = 0.0

    # 获取匹配类型和配置
    region_match_type = testcase_config.get("region_match_type", "完全匹配")
    region_budget_range_match = testcase_config.get("region_budget_range_match")
    region_budget_target_rate = testcase_config.get("region_budget_target_rate", 90)

    results = {}

    if region_match_type == "完全匹配":
        # 完全匹配：判断预算占比是否在 range_match 范围内
        if region_budget_range_match is None:
            region_budget_range_match = 5  # 默认值

        for country_code, target_info in region_budget_targets.items():
            target_percentage = target_info["budget_percentage"]
            actual_percentage = region_budget_actual_percentage.get(country_code, 0.0)
            target = target_info["target"]
            actual = region_budget_actual.get(country_code, 0.0)

            # 使用整数百分比误差进行判断，避免精度问题
            error_percentage = abs(actual_percentage - target_percentage)
            error_percentage = round(error_percentage)
            achieved = error_percentage <= region_budget_range_match

            if target == 0:
                achievement_rate = 0.0 if actual == 0 else "null"
            else:
                # achievement_rate 也统一保留为整数百分比
                raw_achievement_rate = (actual / target) * 100
                achievement_rate = round(raw_achievement_rate)

            results[country_code] = {
                "target": target,
                "actual": actual,
                "target_percentage": target_percentage,
                "actual_percentage": actual_percentage,
                "error_percentage": error_percentage,
                "range_match": region_budget_range_match,
                "achievement_rate": achievement_rate,
                "target_rate": region_budget_target_rate,
                "achieved": achieved,
                "match_type": "完全匹配",
            }

    elif region_match_type == "大小关系匹配":
        # 大小关系匹配：判断大小顺序是否一致，如果有 completion=1 的，判断是否达成 target_rate
        # 目标 & 实际预算都接近（diff < 总预算的 1/10000）的地区视为“并列”，允许排序互换
        total_target_budget = sum(
            info["target"] for info in region_budget_targets.values()
        )
        target_diff_threshold = (
            total_target_budget / 10000.0 if total_target_budget > 0 else 0.0
        )
        actual_diff_threshold = (
            total_actual_budget / 10000.0 if total_actual_budget > 0 else 0.0
        )

        # 构建目标大小顺序（按 budget_percentage 降序）
        target_order = sorted(
            region_budget_targets.items(),
            key=lambda x: x[1]["budget_percentage"],
            reverse=True,
        )
        target_rank = {
            country_code: rank for rank, (country_code, _) in enumerate(target_order)
        }

        # 构建实际大小顺序（按 actual_percentage 降序）
        actual_order = sorted(
            region_budget_actual_percentage.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        actual_rank = {
            country_code: rank for rank, (country_code, _) in enumerate(actual_order)
        }

        # 判断顺序是否一致：
        # - 对于目标 & 实际预算差都很小的地区对，允许它们在排序中互换位置（视为并列）
        order_consistent = True
        country_codes = list(region_budget_targets.keys())
        n = len(country_codes)
        for i in range(n):
            if not order_consistent:
                break
            for j in range(i + 1, n):
                ci = country_codes[i]
                cj = country_codes[j]
                ti = target_rank.get(ci)
                tj = target_rank.get(cj)
                ai = actual_rank.get(ci)
                aj = actual_rank.get(cj)
                if ti is None or tj is None or ai is None or aj is None:
                    continue

                # 是否存在“相对顺序相反”的情况
                inverted = (ti < tj and ai > aj) or (ti > tj and ai < aj)
                if not inverted:
                    continue

                # 检查两地区是否可视为“并列”
                target_diff = abs(
                    region_budget_targets[ci]["target"]
                    - region_budget_targets[cj]["target"]
                )
                actual_diff = abs(
                    region_budget_actual.get(ci, 0.0)
                    - region_budget_actual.get(cj, 0.0)
                )
                can_treat_as_tie = (
                    total_target_budget > 0
                    and total_actual_budget > 0
                    and target_diff < target_diff_threshold
                    and actual_diff < actual_diff_threshold
                )

                if not can_treat_as_tie:
                    order_consistent = False
                    break

        # 检查是否有 completion=1 的区域
        has_must_achieve = any(
            completion == 1 for completion in region_completions.values()
        )

        for country_code, target_info in region_budget_targets.items():
            target = target_info["target"]
            actual = region_budget_actual.get(country_code, 0.0)
            target_percentage = target_info["budget_percentage"]
            actual_percentage = region_budget_actual_percentage.get(country_code, 0.0)
            completion = region_completions.get(country_code, 0)

            # 计算达成率
            if target == 0:
                achievement_rate = 0.0 if actual == 0 else "null"
            else:
                # 统一使用整数百分比，避免精度问题
                raw_achievement_rate = (actual / target) * 100
                achievement_rate = round(raw_achievement_rate)

            # 判断是否达成
            if not order_consistent:
                # 顺序不一致，不达成
                achieved = False
            elif has_must_achieve and completion == 1:
                # 有必须达成的区域，且当前区域必须达成
                # 先保证顺序一致，然后再看该区域自身是否达到达成率阈值
                if isinstance(achievement_rate, (int, float)):
                    achieved = achievement_rate >= region_budget_target_rate
                else:
                    achieved = False
            elif has_must_achieve and completion == 0:
                # 有必须达成的区域，但当前区域不需要必须达成，只要顺序一致即可
                achieved = True
            else:
                # 没有必须达成的区域，只要顺序一致即可
                achieved = True

            results[country_code] = {
                "target": target,
                "actual": actual,
                "target_percentage": target_percentage,
                "actual_percentage": actual_percentage,
                "target_rank": target_rank.get(country_code, -1),
                "actual_rank": actual_rank.get(country_code, -1),
                "achievement_rate": achievement_rate,
                "target_rate": region_budget_target_rate,
                "completion": completion,
                "order_consistent": order_consistent,
                "achieved": achieved,
                "match_type": "大小关系匹配",
            }

    else:
        # 未知的匹配类型，使用默认逻辑
        for country_code, target_info in region_budget_targets.items():
            target = target_info["target"]
            actual = region_budget_actual.get(country_code, 0.0)

            if target == 0:
                achievement_rate = 0.0 if actual == 0 else "null"
                achieved = actual == 0
            else:
                # 统一使用整数百分比进行判断，避免精度问题
                raw_achievement_rate = (actual / target) * 100
                achievement_rate = round(raw_achievement_rate)
                achieved = achievement_rate >= region_budget_target_rate

            results[country_code] = {
                "target": target,
                "actual": actual,
                "achievement_rate": achievement_rate,
                "target_rate": region_budget_target_rate,
                "achieved": achieved,
                "budget_percentage": target_info["budget_percentage"],
                "match_type": region_match_type,
            }

    return results


def check_region_kpi_achievement(
    request_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查区域 KPI 是否达成"""
    basic_info = request_json.get("basicInfo", {})

    # 提取区域 KPI 目标和 completion
    region_kpi_targets = {}
    region_kpi_completions = {}
    for region in basic_info.get("regionBudget", []):
        country_code = region.get("country", {}).get("code", "")
        region_kpi_targets[country_code] = {}
        if country_code not in region_kpi_completions:
            region_kpi_completions[country_code] = {}

        for kpi in region.get("kpiInfo", []):
            kpi_key = kpi.get("key", "")
            region_kpi_targets[country_code][kpi_key] = {
                "target": float(kpi.get("val", "0") or 0),
                "priority": kpi.get("priority", 999),
            }
            region_kpi_completions[country_code][kpi_key] = kpi.get("completion", 0)

    # 计算实际区域 KPI 值
    region_kpi_actual = {}
    for ai_item in ai_data_list:
        region = ai_item.get("region", "")
        country_code = region.split("_")[0] if "_" in region else region

        if country_code not in region_kpi_actual:
            region_kpi_actual[country_code] = {}

        kpi_values = extract_kpi_from_ai(ai_item)
        for kpi_name, kpi_value in kpi_values.items():
            if kpi_name not in region_kpi_actual[country_code]:
                region_kpi_actual[country_code][kpi_name] = 0.0
            region_kpi_actual[country_code][kpi_name] += kpi_value

    # 判断是否达成
    region_kpi_target_rate = testcase_config.get("region_kpi_target_rate", 80)
    results = {}

    for country_code, kpi_targets in region_kpi_targets.items():
        results[country_code] = {}
        kpi_actual = region_kpi_actual.get(country_code, {})

        for kpi_name, target_info in kpi_targets.items():
            target = target_info["target"]
            actual = kpi_actual.get(kpi_name, 0.0)
            completion = region_kpi_completions.get(country_code, {}).get(kpi_name, 0)

            if target == 0:
                achievement_rate = 0.0 if actual == 0 else "null"
                # target 为 0 时，只要 actual 也为 0 即达成，不再区分 completion
                achieved = actual == 0
            else:
                # 统一使用整数百分比进行判断，避免精度问题
                raw_achievement_rate = (actual / target) * 100
                achievement_rate = round(raw_achievement_rate)
                # 无论 completion 是否为 1，一律按整数达成率与 target_rate 判断
                achieved = achievement_rate >= region_kpi_target_rate

            results[country_code][kpi_name] = {
                "target": target,
                "actual": actual,
                "achievement_rate": achievement_rate,
                "target_rate": region_kpi_target_rate,
                "achieved": achieved,
                "priority": target_info["priority"],
                "completion": completion,
            }

    return results


def check_stage_budget_achievement(
    request_json: Dict,
    result_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查各区域下的 stage 维度预算是否满足"""
    # 提取目标配置（从请求文件）
    target_stages = {}
    for country_config in request_json.get("briefMultiConfig", []):
        country_code = country_config.get("country", {}).get("code", "")
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
        region = ai_item.get("region", "")
        country_code = region.split("_")[0] if "_" in region else region
        stage_name = ai_item.get("stage", "")

        if not country_code or not stage_name:
            continue

        if country_code not in actual_stages:
            actual_stages[country_code] = {}

        if stage_name not in actual_stages[country_code]:
            actual_stages[country_code][stage_name] = 0.0

        budget = parse_budget(ai_item.get("adTypeBudget", "0"))
        actual_stages[country_code][stage_name] += budget

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
                # range_match 以预算占比的上下浮动范围判定，统一使用整数百分比
                error_percentage = abs(
                    actual_info["actual_percentage"] - target_info["target_percentage"]
                )
                error_percentage = round(error_percentage)
                satisfied = error_percentage <= stage_range_match

            results[country_code][stage_name] = {
                "target": target,
                "actual": actual,
                "error_percentage": error_percentage,
                "range_match": stage_range_match,
                "satisfied": satisfied,
                "target_percentage": target_info["target_percentage"],
                "actual_percentage": actual_info["actual_percentage"],
            }

    return results


def check_marketingfunnel_budget_achievement(
    request_json: Dict,
    result_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查各区域下的 marketingFunnel 维度预算是否满足"""
    # 提取目标配置（从请求文件）
    target_funnels = {}
    for country_config in request_json.get("briefMultiConfig", []):
        country_code = country_config.get("country", {}).get("code", "")
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
        region = ai_item.get("region", "")
        country_code = region.split("_")[0] if "_" in region else region
        funnel_name = ai_item.get("marketingFunnel", "")

        if not country_code or not funnel_name:
            continue

        if country_code not in actual_funnels:
            actual_funnels[country_code] = {}

        if funnel_name not in actual_funnels[country_code]:
            actual_funnels[country_code][funnel_name] = 0.0

        budget = parse_budget(ai_item.get("adTypeBudget", "0"))
        actual_funnels[country_code][funnel_name] += budget

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
                # 以预算占比浮动范围判定，统一使用整数百分比
                error_percentage = abs(
                    actual_info["actual_percentage"] - target_info["target_percentage"]
                )
                error_percentage = round(error_percentage)
                satisfied = error_percentage <= funnel_range_match

            results[country_code][funnel_name] = {
                "target": target,
                "actual": actual,
                "error_percentage": error_percentage,
                "range_match": funnel_range_match,
                "satisfied": satisfied,
                "target_percentage": target_info["target_percentage"],
                "actual_percentage": actual_info["actual_percentage"],
            }

    return results


def check_media_budget_achievement(
    request_json: Dict,
    result_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查各区域下的 media 维度预算是否满足"""
    # 提取目标配置（从请求文件）
    target_media = {}
    for country_config in request_json.get("briefMultiConfig", []):
        country_code = country_config.get("country", {}).get("code", "")
        target_media[country_code] = {}

        for media in country_config.get("media", []):
            media_name = media.get("name", "")
            target_media[country_code][media_name] = {
                "target": media.get("budgetAmount", 0),
                "target_percentage": media.get("budgetPercentage", 0),
            }

    # 从 ai 数据聚合计算实际配置
    actual_media = {}
    for ai_item in ai_data_list:
        region = ai_item.get("region", "")
        country_code = region.split("_")[0] if "_" in region else region
        media_name = ai_item.get("media", "")

        if not country_code or not media_name:
            continue

        if country_code not in actual_media:
            actual_media[country_code] = {}

        if media_name not in actual_media[country_code]:
            actual_media[country_code][media_name] = 0.0

        budget = parse_budget(ai_item.get("adTypeBudget", "0"))
        actual_media[country_code][media_name] += budget

    # 计算百分比
    for country_code in actual_media.keys():
        total_budget = sum(actual_media[country_code].values())
        for media_name in actual_media[country_code].keys():
            actual_amount = actual_media[country_code][media_name]
            actual_percentage = (
                (actual_amount / total_budget * 100) if total_budget > 0 else 0.0
            )
            actual_media[country_code][media_name] = {
                "actual": actual_amount,
                "actual_percentage": actual_percentage,
            }

    # 判断是否满足
    media_range_match = testcase_config.get("media_range_match", 5)
    results = {}

    # 合并所有国家代码
    all_countries = set(target_media.keys()) | set(actual_media.keys())

    for country_code in all_countries:
        results[country_code] = {}
        target_media_data = target_media.get(country_code, {})
        actual_media_data = actual_media.get(country_code, {})

        # 合并所有 media 名称
        all_media = set(target_media_data.keys()) | set(actual_media_data.keys())

        for media_name in all_media:
            target_info = target_media_data.get(
                media_name, {"target": 0, "target_percentage": 0}
            )
            actual_info = actual_media_data.get(
                media_name, {"actual": 0, "actual_percentage": 0}
            )

            target = target_info["target"]
            actual = actual_info["actual"]

            if target == 0:
                error_percentage = (
                    0.0 if actual_info["actual_percentage"] == 0 else "null"
                )
                satisfied = actual_info["actual_percentage"] == 0
            else:
                # 以预算占比浮动范围判定，统一使用整数百分比
                error_percentage = abs(
                    actual_info["actual_percentage"] - target_info["target_percentage"]
                )
                error_percentage = round(error_percentage)
                satisfied = error_percentage <= media_range_match

            results[country_code][media_name] = {
                "target": target,
                "actual": actual,
                "error_percentage": error_percentage,
                "range_match": media_range_match,
                "satisfied": satisfied,
                "target_percentage": target_info["target_percentage"],
                "actual_percentage": actual_info["actual_percentage"],
            }

    return results


def check_adtype_kpi_achievement(
    request_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查广告类型 KPI 是否达成"""
    # 提取广告类型 KPI 目标和 completion
    adtype_kpi_targets = {}
    adtype_kpi_completions = {}
    for country_config in request_json.get("briefMultiConfig", []):
        country_code = country_config.get("country", {}).get("code", "")

        for media_config in country_config.get("mediaMarketingFunnelAdtype", []):
            media_name = media_config.get("mediaName", "")

            for adtype in media_config.get("adTypeWithKPI", []):
                adtype_name = adtype.get("adTypeName", "")
                funnel_name = adtype.get("funnelName", "")
                platform = adtype.get("platform", "")

                key = f"{country_code}|{media_name}|{platform}|{funnel_name}|{adtype_name}"
                adtype_kpi_targets[key] = {
                    "country": country_code,
                    "media": media_name,
                    "platform": platform,
                    "funnel": funnel_name,
                    "adtype": adtype_name,
                    "kpis": {},
                }
                if key not in adtype_kpi_completions:
                    adtype_kpi_completions[key] = {}

                for kpi in adtype.get("kpiInfo", []):
                    kpi_key = kpi.get("key", "")
                    adtype_kpi_targets[key]["kpis"][kpi_key] = {
                        "target": float(kpi.get("val", "0") or 0),
                        "priority": kpi.get("priority", 999),
                    }
                    adtype_kpi_completions[key][kpi_key] = kpi.get("completion", 0)

    # 计算实际广告类型 KPI 值
    adtype_kpi_actual = {}
    for ai_item in ai_data_list:
        region = ai_item.get("region", "")
        country_code = region.split("_")[0] if "_" in region else region
        media = ai_item.get("media", "")
        platform = ai_item.get("mediaChannel", "")
        funnel = ai_item.get("marketingFunnel", "")
        adtype = ai_item.get("adType", "")

        # 尝试匹配键
        match_keys = [
            f"{country_code}|{media}|{platform}|{funnel}|{adtype}",
            f"{media}|{platform}|{funnel}|{adtype}",
            f"{adtype}|{funnel}",
        ]

        matched_key = None
        for key in match_keys:
            if key in adtype_kpi_targets:
                matched_key = key
                break

        if matched_key:
            if matched_key not in adtype_kpi_actual:
                adtype_kpi_actual[matched_key] = {}

            kpi_values = extract_kpi_from_ai(ai_item)
            for kpi_name, kpi_value in kpi_values.items():
                if kpi_name not in adtype_kpi_actual[matched_key]:
                    adtype_kpi_actual[matched_key][kpi_name] = 0.0
                adtype_kpi_actual[matched_key][kpi_name] += kpi_value

    # 判断是否达成
    adtype_target_rate = testcase_config.get(
        "mediaMarketingFunnelAdtype_target_rate", 80
    )
    results = {}

    for key, target_info in adtype_kpi_targets.items():
        results[key] = {
            "country": target_info["country"],
            "media": target_info["media"],
            "platform": target_info["platform"],
            "funnel": target_info["funnel"],
            "adtype": target_info["adtype"],
            "kpis": {},
        }

        kpi_actual = adtype_kpi_actual.get(key, {})
        for kpi_name, kpi_target_info in target_info["kpis"].items():
            target = kpi_target_info["target"]
            actual = kpi_actual.get(kpi_name, 0.0)
            completion = adtype_kpi_completions.get(key, {}).get(kpi_name, 0)

            if target == 0:
                achievement_rate = 0.0 if actual == 0 else "null"
                # target 为 0 时，只要 actual 也为 0 即达成，不再区分 completion
                achieved = actual == 0
            else:
                # 统一使用整数百分比进行判断，避免精度问题
                raw_achievement_rate = (actual / target) * 100
                achievement_rate = round(raw_achievement_rate)
                # 无论 completion 是否为 1，一律按整数达成率与 target_rate 判断
                achieved = achievement_rate >= adtype_target_rate

            results[key]["kpis"][kpi_name] = {
                "target": target,
                "actual": actual,
                "achievement_rate": achievement_rate,
                "target_rate": adtype_target_rate,
                "achieved": achieved,
                "priority": kpi_target_info["priority"],
                "completion": completion,
            }

    return results


def check_adtype_budget_allocation(
    request_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查每个推广区域下每个 Adtype 是否都分配了预算（当 allow_zero_budget 为 False 时）

    按 media、platform、adtype 聚合求和预算，只要任意 stage 下满足预算 > 0 即可
    """
    allow_zero_budget = testcase_config.get("allow_zero_budget", False)

    # 如果允许为0，则不需要检查
    if allow_zero_budget:
        return {}

    # 提取目标 Adtype 配置（从请求文件中）
    target_adtypes = {}
    for country_config in request_json.get("briefMultiConfig", []):
        country_code = country_config.get("country", {}).get("code", "")
        target_adtypes[country_code] = {}

        for media_config in country_config.get("mediaMarketingFunnelAdtype", []):
            media_name = media_config.get("mediaName", "")

            for adtype in media_config.get("adTypeWithKPI", []):
                adtype_name = adtype.get("adTypeName", "")
                platform = adtype.get("platform", "")

                # 使用 (media, platform, adtype) 作为键
                key = f"{media_name}|{platform}|{adtype_name}"
                target_adtypes[country_code][key] = {
                    "media": media_name,
                    "platform": platform,
                    "adtype": adtype_name,
                }

    # 从 ai 数据聚合计算实际预算（按 media、platform、adtype 聚合，跨所有 stage）
    actual_adtype_budgets = {}
    for ai_item in ai_data_list:
        region = ai_item.get("region", "")
        country_code = region.split("_")[0] if "_" in region else region
        media = ai_item.get("media", "")
        platform = ai_item.get("mediaChannel", "")
        adtype = ai_item.get("adType", "")

        if not country_code or not media or not platform or not adtype:
            continue

        # 使用 (media, platform, adtype) 作为键
        key = f"{media}|{platform}|{adtype}"

        if country_code not in actual_adtype_budgets:
            actual_adtype_budgets[country_code] = {}

        if key not in actual_adtype_budgets[country_code]:
            actual_adtype_budgets[country_code][key] = {
                "media": media,
                "platform": platform,
                "adtype": adtype,
                "budget": 0.0,
            }

        budget = parse_budget(ai_item.get("adTypeBudget", "0"))
        actual_adtype_budgets[country_code][key]["budget"] += budget

    # 判断是否满足（每个目标 Adtype 都应该有预算 > 0）
    results = {}

    # 合并所有国家代码
    all_countries = set(target_adtypes.keys()) | set(actual_adtype_budgets.keys())

    for country_code in all_countries:
        results[country_code] = {}
        target_adtype_data = target_adtypes.get(country_code, {})
        actual_adtype_data = actual_adtype_budgets.get(country_code, {})

        # 合并所有 adtype 键
        all_adtype_keys = set(target_adtype_data.keys()) | set(
            actual_adtype_data.keys()
        )

        for key in all_adtype_keys:
            target_info = target_adtype_data.get(key, {})
            actual_info = actual_adtype_data.get(key, {"budget": 0.0})

            budget = actual_info.get("budget", 0.0)
            # 只要预算 > 0 就满足
            satisfied = budget > 0

            results[country_code][key] = {
                "media": target_info.get("media") or actual_info.get("media", ""),
                "platform": target_info.get("platform")
                or actual_info.get("platform", ""),
                "adtype": target_info.get("adtype") or actual_info.get("adtype", ""),
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
    print(
        f"  区域预算目标达成率: {testcase_config.get('region_budget_target_rate', 90)}%"
    )
    print(f"  区域KPI目标达成率: {testcase_config.get('region_kpi_target_rate', 80)}%")
    print(
        f"  广告类型KPI目标达成率: {testcase_config.get('mediaMarketingFunnelAdtype_target_rate', 80)}%"
    )
    print(f"  阶段预算误差范围: {testcase_config.get('stage_range_match', 20)}%")
    print(
        f"  营销漏斗预算误差范围: {testcase_config.get('marketingfunnel_range_match', 15)}%"
    )
    print(f"  媒体预算误差范围: {testcase_config.get('media_range_match', 5)}%")

    # 全局 KPI
    if "global_kpi" in results:
        print(f"\n【全局 KPI 达成情况】")
        global_kpi = results["global_kpi"]
        achieved_count = sum(1 for v in global_kpi.values() if v.get("achieved", False))
        total_count = len(global_kpi)

        print(f"  达成: {achieved_count}/{total_count}")
        for kpi_name in sorted(
            global_kpi.keys(),
            key=lambda x: global_kpi[x].get("priority", 999),
        ):
            kpi_data = global_kpi[kpi_name]
            status = "[OK]" if kpi_data["achieved"] else "[FAIL]"
            print(
                f"  {status} {kpi_name} (优先级 {kpi_data['priority']}): "
                f"实际={kpi_data['actual']:,.0f}, 目标={kpi_data['target']:,.0f}, "
                f"达成率={kpi_data['achievement_rate']:.2f}% "
                f"(目标达成率: {kpi_data['target_rate']}%)"
            )

    # 区域预算
    if "region_budget" in results:
        print(f"\n【区域预算达成情况】")
        region_budget = results["region_budget"]
        achieved_count = sum(
            1 for v in region_budget.values() if v.get("achieved", False)
        )
        total_count = len(region_budget)

        # 获取匹配类型（从第一个区域获取）
        match_type = None
        if region_budget:
            first_region = next(iter(region_budget.values()))
            match_type = first_region.get("match_type", "完全匹配")

        print(f"  匹配类型: {match_type}")
        print(f"  达成: {achieved_count}/{total_count}")

        if match_type == "完全匹配":
            for country_code in sorted(region_budget.keys()):
                budget_data = region_budget[country_code]
                status = "[OK]" if budget_data["achieved"] else "[FAIL]"
                print(
                    f"  {status} {country_code}: "
                    f"实际占比={budget_data.get('actual_percentage', 0):.2f}%, "
                    f"目标占比={budget_data.get('target_percentage', 0):.2f}%, "
                    f"误差={budget_data.get('error_percentage', 0):.2f}% "
                    f"(允许误差: {budget_data.get('range_match', 0)}%)"
                )
        elif match_type == "大小关系匹配":
            # 显示顺序一致性
            order_consistent = None
            if region_budget:
                first_region = next(iter(region_budget.values()))
                order_consistent = first_region.get("order_consistent", False)

            order_status = "[OK]" if order_consistent else "[FAIL]"
            print(
                f"  顺序一致性: {order_status} {'一致' if order_consistent else '不一致'}"
            )

            # 按目标排名排序显示
            sorted_regions = sorted(
                region_budget.items(),
                key=lambda x: x[1].get("target_rank", 999),
            )

            for country_code, budget_data in sorted_regions:
                status = "[OK]" if budget_data["achieved"] else "[FAIL]"
                completion = budget_data.get("completion", 0)
                must_achieve = "必须达成" if completion == 1 else "非必须"
                print(
                    f"  {status} {country_code} ({must_achieve}): "
                    f"目标排名={budget_data.get('target_rank', -1) + 1}, "
                    f"实际排名={budget_data.get('actual_rank', -1) + 1}, "
                    f"实际={budget_data['actual']:,.2f}, 目标={budget_data['target']:,.2f}"
                )
                if completion == 1:
                    achievement_rate = budget_data.get("achievement_rate", 0)
                    if isinstance(achievement_rate, (int, float)):
                        print(
                            f"    达成率={achievement_rate:.2f}% "
                            f"(目标达成率: {budget_data['target_rate']}%)"
                        )
        else:
            # 默认显示方式
            for country_code in sorted(region_budget.keys()):
                budget_data = region_budget[country_code]
                status = "[OK]" if budget_data["achieved"] else "[FAIL]"
                print(
                    f"  {status} {country_code}: "
                    f"实际={budget_data['actual']:,.2f}, 目标={budget_data['target']:,.2f}, "
                    f"达成率={budget_data.get('achievement_rate', 0):.2f}% "
                    f"(目标达成率: {budget_data['target_rate']}%)"
                )

    # 区域 KPI
    if "region_kpi" in results:
        print(f"\n【区域 KPI 达成情况】")
        region_kpi = results["region_kpi"]
        for country_code in sorted(region_kpi.keys()):
            country_kpis = region_kpi[country_code]
            achieved_count = sum(
                1 for v in country_kpis.values() if v.get("achieved", False)
            )
            total_count = len(country_kpis)

            print(f"\n  {country_code}: 达成 {achieved_count}/{total_count}")
            for kpi_name in sorted(
                country_kpis.keys(),
                key=lambda x: country_kpis[x].get("priority", 999),
            ):
                kpi_data = country_kpis[kpi_name]
                status = "[OK]" if kpi_data["achieved"] else "[FAIL]"
                print(
                    f"    {status} {kpi_name} (优先级 {kpi_data['priority']}): "
                    f"实际={kpi_data['actual']:,.0f}, 目标={kpi_data['target']:,.0f}, "
                    f"达成率={kpi_data['achievement_rate']:.2f}% "
                    f"(目标达成率: {kpi_data['target_rate']}%)"
                )

    # 广告类型 KPI（只显示汇总）
    if "adtype_kpi" in results:
        print(f"\n【广告类型 KPI 达成情况（汇总）】")
        adtype_kpi = results["adtype_kpi"]
        total_achieved = 0
        total_count = 0

        for key, adtype_data in adtype_kpi.items():
            kpis = adtype_data.get("kpis", {})
            for kpi_name, kpi_data in kpis.items():
                total_count += 1
                if kpi_data.get("achieved", False):
                    total_achieved += 1

        print(f"  总体达成: {total_achieved}/{total_count}")
        print(f"  (详细数据请查看输出 JSON 文件)")

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
                print(
                    f"    {status} {stage_name}: "
                    f"实际={stage_data['actual']:,.2f}, 目标={stage_data['target']:,.2f}, "
                    f"误差={stage_data['error_percentage']:.2f}% "
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
                print(
                    f"    {status} {funnel_name}: "
                    f"实际={funnel_data['actual']:,.2f}, 目标={funnel_data['target']:,.2f}, "
                    f"误差={funnel_data['error_percentage']:.2f}% "
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
                print(
                    f"    {status} {media_name}: "
                    f"实际={media_data['actual']:,.2f}, 目标={media_data['target']:,.2f}, "
                    f"误差={media_data['error_percentage']:.2f}% "
                    f"(允许误差: {media_data['range_match']}%)"
                )

        print(f"\n  总体满足: {total_satisfied}/{total_count}")

    # Adtype 预算分配检查（当 allow_zero_budget 为 False 时）
    if "adtype_budget_allocation" in results:
        print(f"\n【Adtype 预算分配检查】")
        adtype_allocation = results["adtype_budget_allocation"]
        total_satisfied = 0
        total_count = 0

        for country_code in sorted(adtype_allocation.keys()):
            country_adtypes = adtype_allocation[country_code]
            country_satisfied = sum(
                1 for v in country_adtypes.values() if v.get("satisfied", False)
            )
            country_total = len(country_adtypes)
            total_satisfied += country_satisfied
            total_count += country_total

            print(f"\n  {country_code}: 满足 {country_satisfied}/{country_total}")
            # 只显示未满足的 Adtype
            unsatisfied = [
                (k, v)
                for k, v in country_adtypes.items()
                if not v.get("satisfied", False)
            ]
            if unsatisfied:
                for key, adtype_data in sorted(unsatisfied, key=lambda x: x[0]):
                    print(
                        f"    [FAIL] {adtype_data['media']} | {adtype_data['platform']} | {adtype_data['adtype']}: "
                        f"预算={adtype_data['budget']:,.2f}"
                    )

        print(f"\n  总体满足: {total_satisfied}/{total_count}")


def main():
    parser = argparse.ArgumentParser(
        description="根据 testcase 配置判断每个指标是否达成"
    )
    parser.add_argument(
        "--testcase-file",
        type=str,
        required=True,
        help="测试用例文件路径（Python文件）",
    )
    parser.add_argument(
        "--request-file",
        type=str,
        required=True,
        help="请求 JSON 文件路径",
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
        required=True,
        help="测试用例名称",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出文件路径（可选）",
    )

    args = parser.parse_args()

    # 加载文件
    testcase_file = Path(args.testcase_file)
    request_file = Path(args.request_file)
    result_file = Path(args.result_file)

    if not testcase_file.exists():
        print(f"错误：测试用例文件不存在: {testcase_file}")
        return 1

    if not request_file.exists():
        print(f"错误：请求文件不存在: {request_file}")
        return 1

    if not result_file.exists():
        print(f"错误：结果文件不存在: {result_file}")
        return 1

    # 加载测试用例配置
    testcase_config = load_testcase(testcase_file, args.case_name)
    if testcase_config is None:
        return 1

    # 加载请求和结果文件
    request_json = load_json(request_file)
    result_json = load_json(result_file)

    # 提取 uuid 和 job_id
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
        "case_name": args.case_name,
        "uuid": uuid,
        "job_id": job_id,
        "testcase_config": {
            "kpi_target_rate": testcase_config.get("kpi_target_rate", 80),
            "region_budget_target_rate": testcase_config.get(
                "region_budget_target_rate", 90
            ),
            "region_kpi_target_rate": testcase_config.get("region_kpi_target_rate", 80),
            "mediaMarketingFunnelAdtype_target_rate": testcase_config.get(
                "mediaMarketingFunnelAdtype_target_rate", 80
            ),
            "stage_range_match": testcase_config.get("stage_range_match", 20),
            "marketingfunnel_range_match": testcase_config.get(
                "marketingfunnel_range_match", 15
            ),
            "media_range_match": testcase_config.get("media_range_match", 5),
            "kpi_priority_list": testcase_config.get("kpi_priority_list", []),
            "module_priority_list": testcase_config.get("module_priority_list", []),
        },
        "global_kpi": check_global_kpi_achievement(
            request_json, ai_data_list, testcase_config
        ),
        "region_budget": check_region_budget_achievement(
            request_json, ai_data_list, testcase_config
        ),
        "region_kpi": check_region_kpi_achievement(
            request_json, ai_data_list, testcase_config
        ),
        "adtype_kpi": check_adtype_kpi_achievement(
            request_json, ai_data_list, testcase_config
        ),
        "stage_budget": check_stage_budget_achievement(
            request_json, result_json, ai_data_list, testcase_config
        ),
        "marketingfunnel_budget": check_marketingfunnel_budget_achievement(
            request_json, result_json, ai_data_list, testcase_config
        ),
        "media_budget": check_media_budget_achievement(
            request_json, result_json, ai_data_list, testcase_config
        ),
    }

    # 检查 Adtype 预算分配（当 allow_zero_budget 为 False 时）
    adtype_allocation = check_adtype_budget_allocation(
        request_json, ai_data_list, testcase_config
    )
    if adtype_allocation:
        results["adtype_budget_allocation"] = adtype_allocation

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
        # 从 core 模块导入
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
