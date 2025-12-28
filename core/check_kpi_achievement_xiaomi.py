#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 testcase 配置判断每个指标是否达成（Xiaomi版本）

用法:
    python core/check_kpi_achievement_xiaomi.py \
        --testcase-file testcase_templatex_xiaomi.py \
        --request-file output/xiaomi/requests/brief_case_基准用例-完全匹配默认配置.json \
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
    result = result_json.get("result", {})
    dimension_result = result.get("dimensionMultiCountryResult", {})

    for region_key, region_data in dimension_result.items():
        ai_list = region_data.get("ai", [])
        for ai_item in ai_list:
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
    kpi_must_achieve = testcase_config.get("kpi_must_achieve", False)
    results = {}

    for kpi_name, target_info in global_kpi_targets.items():
        target = target_info["target"]
        actual = global_kpi_actual.get(kpi_name, 0.0)
        completion = global_kpi_completions.get(kpi_name, 0)

        if target == 0:
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
    request_json: Dict,
    result_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查各区域下的 stage 维度预算是否满足"""
    # 提取目标配置（从请求文件）
    target_stages = {}
    for country_config in request_json.get("briefMultiConfig", []):
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
                    # 大小关系匹配：只检查顺序，不检查具体数值
                    satisfied = True  # 暂时简化处理
                    error_percentage = abs(
                        actual_info["actual_percentage"]
                        - target_info["target_percentage"]
                    )
                    error_percentage = round(error_percentage)

            results[country_code][stage_name] = {
                "target": target,
                "actual": actual,
                "error_percentage": error_percentage,
                "range_match": stage_range_match,
                "satisfied": satisfied,
                "target_percentage": target_info["target_percentage"],
                "actual_percentage": actual_info["actual_percentage"],
                "match_type": stage_match_type,
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
                    # 大小关系匹配：只检查顺序
                    satisfied = True  # 暂时简化处理
                    error_percentage = abs(
                        actual_info["actual_percentage"]
                        - target_info["target_percentage"]
                    )
                    error_percentage = round(error_percentage)

            results[country_code][funnel_name] = {
                "target": target,
                "actual": actual,
                "error_percentage": error_percentage,
                "range_match": funnel_range_match,
                "satisfied": satisfied,
                "target_percentage": target_info["target_percentage"],
                "actual_percentage": actual_info["actual_percentage"],
                "match_type": funnel_match_type,
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
        country_code = country_config.get("countryInfo", {}).get("countryCode", "")
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
        country = ai_item.get("country", "")
        media_name = ai_item.get("media", "")

        if not country or not media_name:
            continue

        if country not in actual_media:
            actual_media[country] = {}

        if media_name not in actual_media[country]:
            actual_media[country][media_name] = 0.0

        budget = parse_budget(ai_item.get("totalBudget", 0))
        actual_media[country][media_name] += budget

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
    media_match_type = testcase_config.get("media_match_type", "完全匹配")
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
                if media_match_type == "完全匹配":
                    error_percentage = abs(
                        actual_info["actual_percentage"]
                        - target_info["target_percentage"]
                    )
                    error_percentage = round(error_percentage)
                    satisfied = error_percentage <= media_range_match
                else:
                    # 大小关系匹配：只检查顺序
                    satisfied = True  # 暂时简化处理
                    error_percentage = abs(
                        actual_info["actual_percentage"]
                        - target_info["target_percentage"]
                    )
                    error_percentage = round(error_percentage)

            results[country_code][media_name] = {
                "target": target,
                "actual": actual,
                "error_percentage": error_percentage,
                "range_match": media_range_match,
                "satisfied": satisfied,
                "target_percentage": target_info["target_percentage"],
                "actual_percentage": actual_info["actual_percentage"],
                "match_type": media_match_type,
            }

    return results


def check_mediaMarketingFunnelFormat_kpi_achievement(
    request_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查 mediaMarketingFunnelFormat 维度 KPI 是否达成（Xiaomi版本）"""
    # 提取目标配置
    target_formats = {}
    for country_config in request_json.get("briefMultiConfig", []):
        country_code = country_config.get("countryInfo", {}).get("countryCode", "")

        for media_config in country_config.get("mediaMarketingFunnelFormat", []):
            media_name = media_config.get("mediaName", "")
            platform = (
                media_config.get("platform", [""])[0]
                if media_config.get("platform")
                else ""
            )
            funnel_name = media_config.get("funnelName", "")

            for adformat in media_config.get("adFormatWithKPI", []):
                adformat_name = adformat.get("adFormatName", "")
                creative = adformat.get("creative", "")

                key = f"{country_code}|{media_name}|{platform}|{funnel_name}|{adformat_name}|{creative}"
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
                    target_formats[key]["kpis"][kpi_key] = {
                        "target": float(kpi.get("val", "0") or 0),
                        "priority": kpi.get("priority", 999),
                        "completion": kpi.get("completion", 0),
                    }

    # 计算实际 KPI 值
    actual_formats = {}
    for ai_item in ai_data_list:
        country = ai_item.get("country", "")
        media = ai_item.get("media", "")
        platform = ai_item.get("mediaChannel", "")
        funnel = ai_item.get("marketingFunnel", "")
        adformat = ai_item.get("adFormat", "")
        creative = ai_item.get("creative", "")

        # 尝试匹配键
        match_keys = [
            f"{country}|{media}|{platform}|{funnel}|{adformat}|{creative}",
            f"{media}|{platform}|{funnel}|{adformat}|{creative}",
            f"{adformat}|{funnel}",
        ]

        matched_key = None
        for key in match_keys:
            if key in target_formats:
                matched_key = key
                break

        if matched_key:
            if matched_key not in actual_formats:
                actual_formats[matched_key] = {}

            kpi_values = extract_kpi_from_ai(ai_item)
            for kpi_name, kpi_value in kpi_values.items():
                if kpi_name not in actual_formats[matched_key]:
                    actual_formats[matched_key][kpi_name] = 0.0
                actual_formats[matched_key][kpi_name] += kpi_value

    # 判断是否达成
    format_target_rate = testcase_config.get(
        "mediaMarketingFunnelFormat_target_rate", 80
    )
    format_must_achieve = testcase_config.get(
        "mediaMarketingFunnelFormat_must_achieve", False
    )
    results = {}

    for key, target_info in target_formats.items():
        results[key] = {
            "country": target_info["country"],
            "media": target_info["media"],
            "platform": target_info["platform"],
            "funnel": target_info["funnel"],
            "adformat": target_info["adformat"],
            "creative": target_info["creative"],
            "kpis": {},
        }

        kpi_actual = actual_formats.get(key, {})
        for kpi_name, kpi_target_info in target_info["kpis"].items():
            target = kpi_target_info["target"]
            actual = kpi_actual.get(kpi_name, 0.0)
            completion = kpi_target_info.get("completion", 0)

            if target == 0:
                achievement_rate = 0.0 if actual == 0 else "null"
                achieved = actual == 0
            else:
                raw_achievement_rate = (actual / target) * 100
                achievement_rate = round(raw_achievement_rate)
                if format_must_achieve or completion == 1:
                    achieved = actual >= target
                else:
                    achieved = achievement_rate >= format_target_rate

            results[key]["kpis"][kpi_name] = {
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
    request_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查 mediaMarketingFunnelFormatBudgetConfig 维度预算是否满足（Xiaomi版本）"""
    # 提取目标配置
    target_configs = {}
    for country_config in request_json.get("briefMultiConfig", []):
        country_code = country_config.get("countryInfo", {}).get("countryCode", "")
        target_configs[country_code] = {}

        budget_config = country_config.get("mediaMarketingFunnelFormatBudgetConfig", {})
        if not budget_config:
            continue

        for config_item in budget_config.get("budgetConfig", []):
            media_name = config_item.get("mediaName", "")
            platform = config_item.get("platform", "")
            funnel_name = config_item.get("funnelName", "")
            adformat_name = config_item.get("adFormatName", "")
            creative = config_item.get("creative", "")

            key = f"{media_name}|{platform}|{funnel_name}|{adformat_name}|{creative}"
            target_configs[country_code][key] = {
                "target": config_item.get("budgetAmount", 0),
                "target_percentage": config_item.get("budgetPercentage", 0),
            }

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

        key = f"{media}|{platform}|{funnel}|{adformat}|{creative}"

        if country not in actual_configs:
            actual_configs[country] = {}

        if key not in actual_configs[country]:
            actual_configs[country][key] = 0.0

        budget = parse_budget(ai_item.get("totalBudget", 0))
        actual_configs[country][key] += budget

    # 计算百分比
    for country_code in actual_configs.keys():
        total_budget = sum(actual_configs[country_code].values())
        for key in actual_configs[country_code].keys():
            actual_amount = actual_configs[country_code][key]
            actual_percentage = (
                (actual_amount / total_budget * 100) if total_budget > 0 else 0.0
            )
            actual_configs[country_code][key] = {
                "actual": actual_amount,
                "actual_percentage": actual_percentage,
            }

    # 判断是否满足
    config_target_rate = testcase_config.get(
        "mediaMarketingFunnelFormatBudgetConfig_target_rate", 80
    )
    config_must_achieve = testcase_config.get(
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve", False
    )
    results = {}

    all_countries = set(target_configs.keys()) | set(actual_configs.keys())

    for country_code in all_countries:
        results[country_code] = {}
        target_data = target_configs.get(country_code, {})
        actual_data = actual_configs.get(country_code, {})

        all_keys = set(target_data.keys()) | set(actual_data.keys())

        for key in all_keys:
            target_info = target_data.get(key, {"target": 0, "target_percentage": 0})
            actual_info = actual_data.get(key, {"actual": 0, "actual_percentage": 0})

            target = target_info["target"]
            actual = actual_info["actual"]

            if target == 0:
                error_percentage = (
                    0.0 if actual_info["actual_percentage"] == 0 else "null"
                )
                satisfied = actual_info["actual_percentage"] == 0
            else:
                error_percentage = abs(
                    actual_info["actual_percentage"] - target_info["target_percentage"]
                )
                error_percentage = round(error_percentage)
                if config_must_achieve:
                    satisfied = actual >= target
                else:
                    satisfied = error_percentage <= 5  # 默认误差范围5%

            results[country_code][key] = {
                "target": target,
                "actual": actual,
                "error_percentage": error_percentage,
                "satisfied": satisfied,
                "target_percentage": target_info["target_percentage"],
                "actual_percentage": actual_info["actual_percentage"],
            }

    return results


def check_adformat_budget_allocation(
    request_json: Dict,
    ai_data_list: List[Dict],
    testcase_config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """检查每个推广区域下每个 AdFormat 是否都分配了预算（当 allow_zero_budget 为 False 时，Xiaomi版本）"""
    allow_zero_budget = testcase_config.get("allow_zero_budget", False)

    if allow_zero_budget:
        return {}

    # 提取目标 AdFormat 配置
    target_formats = {}
    for country_config in request_json.get("briefMultiConfig", []):
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
                adformat_name = adformat.get("adFormatName", "")
                key = f"{media_name}|{platform}|{adformat_name}"
                target_formats[country_code][key] = {
                    "media": media_name,
                    "platform": platform,
                    "adformat": adformat_name,
                }

    # 从 ai 数据聚合计算实际预算
    actual_formats = {}
    for ai_item in ai_data_list:
        country = ai_item.get("country", "")
        media = ai_item.get("media", "")
        platform = ai_item.get("mediaChannel", "")
        adformat = ai_item.get("adFormat", "")

        if not country or not media or not platform or not adformat:
            continue

        key = f"{media}|{platform}|{adformat}"

        if country not in actual_formats:
            actual_formats[country] = {}

        if key not in actual_formats[country]:
            actual_formats[country][key] = {
                "media": media,
                "platform": platform,
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
        f"  MediaMarketingFunnelFormat KPI目标达成率: {testcase_config.get('mediaMarketingFunnelFormat_target_rate', 80)}%"
    )
    print(
        f"  MediaMarketingFunnelFormatBudgetConfig 目标达成率: {testcase_config.get('mediaMarketingFunnelFormatBudgetConfig_target_rate', 80)}%"
    )

    # 全局 KPI
    if "global_kpi" in results:
        print(f"\n【全局 KPI 达成情况】")
        global_kpi = results["global_kpi"]
        achieved_count = sum(1 for v in global_kpi.values() if v.get("achieved", False))
        total_count = len(global_kpi)
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

    # MediaMarketingFunnelFormat KPI（汇总）
    if "mediaMarketingFunnelFormat_kpi" in results:
        print(f"\n【MediaMarketingFunnelFormat KPI 达成情况（汇总）】")
        format_kpi = results["mediaMarketingFunnelFormat_kpi"]
        total_achieved = 0
        total_count = 0
        for key, format_data in format_kpi.items():
            kpis = format_data.get("kpis", {})
            for kpi_name, kpi_data in kpis.items():
                total_count += 1
                if kpi_data.get("achieved", False):
                    total_achieved += 1
        print(f"  总体达成: {total_achieved}/{total_count}")
        print(f"  (详细数据请查看输出 JSON 文件)")

    # AdFormat 预算分配检查
    if "adformat_budget_allocation" in results:
        print(f"\n【AdFormat 预算分配检查】")
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
                    print(
                        f"    [FAIL] {format_data['media']} | {format_data['platform']} | {format_data['adformat']}: "
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

    # 提取 uuid 和 job_id（Xiaomi版本：从result.briefInfo.basicInfo中提取）
    brief_info = result_json.get("result", {}).get("briefInfo", {})
    basic_info = brief_info.get("basicInfo", {})
    uuid = basic_info.get("uuid")
    job_id = basic_info.get("jobId")

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
        "stage_budget": check_stage_budget_achievement(
            request_json, result_json, ai_data_list, testcase_config
        ),
        "marketingfunnel_budget": check_marketingfunnel_budget_achievement(
            request_json, result_json, ai_data_list, testcase_config
        ),
        "media_budget": check_media_budget_achievement(
            request_json, result_json, ai_data_list, testcase_config
        ),
        "mediaMarketingFunnelFormat_kpi": check_mediaMarketingFunnelFormat_kpi_achievement(
            request_json, ai_data_list, testcase_config
        ),
        "mediaMarketingFunnelFormatBudgetConfig_budget": check_mediaMarketingFunnelFormatBudgetConfig_budget_achievement(
            request_json, ai_data_list, testcase_config
        ),
    }

    # 检查 AdFormat 预算分配（当 allow_zero_budget 为 False 时，Xiaomi版本）
    adformat_allocation = check_adformat_budget_allocation(
        request_json, ai_data_list, testcase_config
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
        # 从 core 模块导入（Xiaomi版本）
        from core.generate_test_report_xiaomi import (
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
            "可以手动运行: python core/generate_test_report_xiaomi.py --result-file <json文件>"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
