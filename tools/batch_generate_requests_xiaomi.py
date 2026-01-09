import json
import uuid
import importlib.util
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import random
import traceback
import sys
import os

import warnings

import numpy as np
import pandas as pd

# 添加项目根目录到路径，以便导入 core 模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core import (
    KPI_KEYS,
    MAX_REGION_COUNT,
    load_country_dict,
    load_adformat_dict,
    normalize_percentage_sum,
    reorder_priorities,
    safe_sum,
)
from core.data_loader import load_data_xiaomi

# 为了保持代码兼容性，创建别名
load_data = load_data_xiaomi

# load_country_dict, load_adformat_dict, normalize_percentage_sum, reorder_priorities 已从 core 模块导入
# 注意：reorder_priorities 函数在 xiaomi 版本中有特殊处理，所以保留本地实现


def normalize_platform(raw_platform: str) -> str:
    """
    规范化 platform 名称，比如 adtype_dict 里的 'FBIGFB&IG' -> 'FB&IG'。
    """
    if not raw_platform:
        return raw_platform
    p = raw_platform.strip()
    if p.upper() in {"FBIGFB&IG", "FB&IG"}:
        return "FB&IG"
    return p


def attach_mapping(
    data_df: pd.DataFrame, map_df: pd.DataFrame, adformat_df: pd.DataFrame = None
) -> pd.DataFrame:
    """
    为 data_df 追加 Media / Platform / Marketing Funnel / Creative 等信息。
    处理新格式（data_xiaomi.csv）。
    """
    data_df = data_df.copy()

    # 直接使用数据中的 Media 字段
    data_df["Media_final"] = data_df["Media"].astype(str).str.strip()

    # 平台：使用 Media Channel
    data_df["Platform_final"] = data_df["media_channel"].astype(str).str.strip()
    data_df["Platform_final"] = data_df["Platform_final"].map(normalize_platform)

    # 从 adformat.csv 中获取 Marketing Funnel
    # 建立 (Media, Media Channel, Objective, Ad format) -> Marketing Funnel 的映射
    funnel_map = {}  # (media, media_channel, objective, ad_format) -> marketing_funnel
    if adformat_df is not None and not adformat_df.empty:
        for _, r in adformat_df.iterrows():
            media = str(r.get("Media", "")).strip()
            media_channel = str(r.get("Media Channel", "")).strip()
            objective = str(r.get("Objective", "")).strip()
            ad_format = str(r.get("Ad format", "")).strip()
            marketing_funnel = str(r.get("Marketing Funnel", "")).strip()

            if media and media_channel and objective and ad_format and marketing_funnel:
                # 规范化 media_channel（处理可能的多个值，用 "/" 分隔）
                channels = [
                    normalize_platform(p.strip())
                    for p in media_channel.split("/")
                    if p.strip()
                ]
                # 为每个 channel 建立映射
                for channel in channels:
                    key = (media, channel, objective, ad_format)
                    funnel_map[key] = marketing_funnel

    # 合并数据（map_df 为空，所以直接使用 data_df）
    merged = data_df.copy()

    # 从 adformat.csv 匹配 Marketing Funnel
    def get_marketing_funnel(row):
        media = row.get("Media_final", "")
        media_channel = row.get("media_channel", "")
        objective = row.get("objective", "")
        ad_type = row.get("ad_type", "")

        # 规范化 media_channel
        channel_normalized = normalize_platform(media_channel) if media_channel else ""

        # 使用唯一键匹配：(Media, Media Channel, Objective, Ad format)
        if media and channel_normalized and objective and ad_type:
            key = (media, channel_normalized, objective, ad_type)
            if key in funnel_map:
                return funnel_map[key]

        # 如果匹配不到，根据 Objective 推断（兜底逻辑）
        if objective:
            obj_str = str(objective).strip()
            obj_lower = obj_str.lower()
            mapping = {
                "awareness": "Awareness",
                "video view": "Consideration",
                "video views": "Consideration",
                "traffic": "Traffic",
                "conversion": "Conversion",
                "reach": "Awareness",
                "consideration": "Consideration",
            }
            return mapping.get(obj_lower, "Awareness")  # 默认返回 Awareness

        return "Awareness"  # 最终兜底

    merged["Funnel_final"] = merged.apply(get_marketing_funnel, axis=1)

    # Creative 字段处理：优先使用数据中的 creative 字段
    # 如果数据中已有 creative 字段，直接使用（新格式数据文件已包含）
    if "creative" in merged.columns:
        # 数据中已有 creative，直接使用，不需要从字典或推断
        merged["creative"] = merged["creative"].astype(str).str.strip()
    # 从 adformat.csv 获取 creative（如果数据中没有且提供了字典）
    elif adformat_df is not None and not adformat_df.empty:
        # 建立 (Media, Media Channel, Objective, Ad format) -> Creative 的映射
        # 唯一键：Media, Media Channel, Objective, Ad format
        adformat_map = {}  # (media, media_channel, objective, ad_format) -> creative

        for _, r in adformat_df.iterrows():
            media = str(r.get("Media", "")).strip()
            media_channel = str(r.get("Media Channel", "")).strip()
            objective = str(r.get("Objective", "")).strip()
            ad_format = str(r.get("Ad format", "")).strip()
            creative = str(r.get("Creative", "")).strip()

            if media and media_channel and objective and ad_format and creative:
                # 规范化 media_channel（处理可能的多个值，用 "/" 分隔）
                channels = [
                    normalize_platform(p.strip())
                    for p in media_channel.split("/")
                    if p.strip()
                ]
                # 为每个 channel 建立映射
                for channel in channels:
                    key = (media, channel, objective, ad_format)
                    adformat_map[key] = creative

        # 合并 creative
        def get_creative(row):
            media = row.get("Media_final", "")
            media_channel = row.get("media_channel", "")
            objective = row.get("objective", "")
            ad_type = row.get("ad_type", "")

            # 规范化 media_channel
            channel_normalized = (
                normalize_platform(media_channel) if media_channel else ""
            )

            # 使用唯一键匹配：(Media, Media Channel, Objective, Ad format)
            if media and channel_normalized and objective and ad_type:
                key = (media, channel_normalized, objective, ad_type)
                if key in adformat_map:
                    return adformat_map[key]

            # 如果都不匹配，返回空字符串
            return ""

        merged["creative"] = merged.apply(get_creative, axis=1)
    else:
        # 如果数据中没有 creative 且没有提供 adformat 字典，设为空字符串
        merged["creative"] = ""

    return merged


def safe_sum(df: pd.DataFrame, col_name: str) -> float:
    """
    安全地获取DataFrame列的sum值，如果列不存在则返回0.0。

    Args:
        df: DataFrame
        col_name: 列名

    Returns:
        列的总和，如果列不存在则返回0.0
    """
    if col_name in df.columns:
        return float(df[col_name].sum())
    return 0.0


def build_basic_info(
    template_basic: dict, df: pd.DataFrame, country_df: pd.DataFrame = None
) -> dict:
    """
    构建 basicInfo：总预算 + 全局 KPI 聚合 + 区域预算。
    新版本增加了更多字段。
    """
    basic = deepcopy(template_basic)

    total_budget = float(df["spend"].sum())
    basic["totalBudget"] = int(round(total_budget))  # 预算金额保留整数

    # 全局 KPI 聚合（如果列不存在则视为0）
    kpi_agg = {
        "Impression": safe_sum(df, "impressions"),
        "Clicks": safe_sum(df, "clicks"),
        "LinkClicks": safe_sum(df, "link_clicks"),
        "VideoViews": safe_sum(df, "video_views"),
        "Engagement": safe_sum(df, "engagements"),
        "Followers": safe_sum(df, "follows"),
        "Like": safe_sum(df, "likes"),
        "Purchase": safe_sum(df, "purchases"),
    }

    kpi_info = []
    # 使用模板里的顺序和 priority，如果存在
    tmpl_kpi_list = basic.get("kpiInfo") or []
    tmpl_priority_map = {item["key"]: item.get("priority") for item in tmpl_kpi_list}

    # 记录有效的KPI键（val不为null的KPI）
    valid_kpi_keys = set()

    for key in KPI_KEYS:
        val = kpi_agg.get(key, 0.0)
        int_val = int(val)
        # 如果值为0，val为null，则不添加到全局KPI列表
        if int_val == 0:
            continue
        valid_kpi_keys.add(key)
        kpi_info.append(
            {
                "key": key,
                "val": str(int_val),
                "priority": tmpl_priority_map.get(key, KPI_KEYS.index(key) + 1),
                "completion": 0,
            }
        )
    basic["kpiInfo"] = kpi_info

    # 区域预算 regionBudget（新版本只包含 countryInfo，不包含预算和KPI）
    # 建立国家信息映射
    country_map = {}
    if country_df is not None and not country_df.empty:
        for _, r in country_df.iterrows():
            code = str(r.get("countryCode", "")).strip()
            if code:
                country_map[code] = {
                    "countryCode": code,
                    "countryNameCN": str(r.get("countryNameCN", "")).strip(),
                    "countryNameEn": str(r.get("countryNameEn", "")).strip(),
                    "regionCode": str(r.get("regionCode", "")).strip(),
                    "regionNameCN": str(r.get("regionNameCN", "")).strip(),
                    "mpCode": str(r.get("mpCode", code)).strip(),
                }

    region_items = []
    for code, g in df.groupby("country_code"):
        country_budget = float(g["spend"].sum())
        if country_budget <= 0:
            continue

        # 从字典获取国家信息，如果不存在则使用默认值
        if code in country_map:
            country_info = country_map[code].copy()
        else:
            # 默认值
            country_info = {
                "countryCode": code,
                "countryNameCN": "",
                "countryNameEn": "",
                "regionCode": "",
                "regionNameCN": "",
                "mpCode": code,
            }

        # 新版本：regionBudget 只包含 countryInfo
        region_items.append({"countryInfo": country_info})

    basic["regionBudget"] = region_items
    basic["uuid"] = str(uuid.uuid4())

    return basic


def build_country_marketing_funnel(country_df: pd.DataFrame) -> list[dict]:
    res = []
    total = float(country_df["spend"].sum())
    if total <= 0:
        return res

    grouped = country_df.dropna(subset=["Funnel_final"]).groupby("Funnel_final")
    for funnel, g in grouped:
        budget = float(g["spend"].sum())
        if budget <= 0:
            continue
        pct = budget / total * 100
        res.append(
            {
                "name": funnel,
                "budgetPercentage": round(pct, 2),  # 预算比例保留2位小数
                "budgetAmount": int(round(budget)),  # 预算金额保留整数
            }
        )
    return res


def build_country_media(country_df: pd.DataFrame) -> list[dict]:
    res = []
    total = float(country_df["spend"].sum())
    if total <= 0:
        return res

    grouped_media = country_df.dropna(subset=["Media_final"]).groupby("Media_final")
    # 收集所有子平台，用于全局归一化（所有 children 的百分比之和=100）
    all_children_refs: list[dict] = []
    for media, g_media in grouped_media:
        media_budget = float(g_media["spend"].sum())
        if media_budget <= 0:
            continue
        media_pct = media_budget / total * 100

        children = []
        grouped_platform = g_media.groupby("Platform_final")
        for platform, g_plat in grouped_platform:
            plat_budget = float(g_plat["spend"].sum())
            if plat_budget <= 0:
                continue
            # 平台预算百分比改为「占国家总预算的比例」
            plat_pct = plat_budget / total * 100 if total > 0 else 0
            children.append(
                {
                    "name": platform,
                    "budgetPercentage": round(plat_pct, 2),  # 预算比例保留2位小数
                    "budgetAmount": int(round(plat_budget)),  # 预算金额保留整数
                }
            )
            all_children_refs.append(children[-1])

        res.append(
            {
                "name": media,
                "budgetPercentage": round(media_pct, 2),  # 预算比例保留2位小数
                "budgetAmount": int(round(media_budget)),  # 预算金额保留整数
                "children": children,
            }
        )

    # 确保所有媒体下的 children 预算百分比总和为 100
    normalize_percentage_sum(all_children_refs, "budgetPercentage")
    return res


def build_country_stage(country_df: pd.DataFrame) -> list[dict]:
    """
    使用 month_ 作为 stage 维度：
    - 每个国家按 month_ 分组
    - 每个 month_ 生成一个阶段
    """
    # 如果没有 month_ 列，则退化为单一汇总阶段
    if "month_" not in country_df.columns:
        total = float(country_df["spend"].sum())
        if total <= 0:
            return []
        return [
            {
                "name": "All",
                "budgetPercentage": 100.0,  # 预算比例保留2位小数
                "budgetAmount": int(round(total)),  # 预算金额保留整数
                "dates": None,
                "marketingFunnel": None,
                "mediaPlatform": None,
            }
        ]

    # 过滤掉无效 month_
    df = country_df.copy()
    df["month_"] = df["month_"].astype(str).str.strip()
    df = df[df["month_"] != ""]

    total = float(df["spend"].sum())
    if total <= 0:
        return []

    stages: list[dict] = []
    for month, g in df.groupby("month_"):
        budget = float(g["spend"].sum())
        if budget <= 0:
            continue
        pct = budget / total * 100 if total > 0 else 0.0
        stages.append(
            {
                "name": month,  # 直接用 month_ 作为阶段名，例如 "202503"
                "budgetPercentage": round(pct, 2),  # 预算比例保留2位小数
                "budgetAmount": int(round(budget)),  # 预算金额保留整数
                "dates": None,
                "marketingFunnel": None,
                "mediaPlatform": None,
            }
        )

    # 按时间排序（字符串排序即可，因为是 YYYYMM）
    stages.sort(key=lambda x: x["name"])
    return stages


def build_country_media_marketing_format(
    country_df: pd.DataFrame, valid_kpi_keys: set = None
) -> list[dict]:
    """
    构造 mediaMarketingFunnelFormat 结构（新版本）：
    - 每个 (media, platform) 组合一个对象
    - platform: 平台名称数组
    - marketingFunnels: 当前 media-platform 相关的所有 funnel（adFormat 替代 adType）
    - adFormatWithKPI: 按 (funnel, ad_type) 聚合 KPI，新增字段 creative, adFormatTotalBudget, completion
    """
    result = []

    # 先按 (media, platform) 切分，每个组合一个对象
    for (media, platform), g_media_platform in country_df.dropna(
        subset=["Media_final", "Platform_final"]
    ).groupby(["Media_final", "Platform_final"]):
        # 确保 platform 是字符串且非空
        if not isinstance(platform, str) or not platform:
            continue

        media_entry: dict = {
            "mediaName": media,
            "platform": [platform],  # 单个平台，但保持数组格式
            "marketingFunnels": [],
            "adFormatWithKPI": [],
        }

        # marketingFunnels 列表：当前 media-platform 下的所有 funnel（adFormat 替代 adType）
        funnels = sorted(
            {
                f
                for f in g_media_platform["Funnel_final"].unique().tolist()
                if isinstance(f, str) and f
            }
        )
        for funnel in funnels:
            media_entry["marketingFunnels"].append(
                {
                    "funnelName": funnel,
                    "funnelNameKey": funnel,
                    "adFormat": [],  # 新版本：adFormat 替代 adType
                }
            )

        # adFormatWithKPI：按 (funnel, ad_type) 聚合（platform 已在对象层级）
        key_cols = ["Funnel_final", "ad_type"]
        g_valid = g_media_platform.dropna(subset=["Funnel_final", "ad_type"])
        if not g_valid.empty:
            grouped = g_valid.groupby(key_cols)
            for (funnel, ad_type), g_combo in grouped:
                spend = float(g_combo["spend"].sum())
                # KPI 聚合（如果列不存在则视为0）
                kpi_vals = {
                    "Impression": safe_sum(g_combo, "impressions"),
                    "Clicks": safe_sum(g_combo, "clicks"),
                    "LinkClicks": safe_sum(g_combo, "link_clicks"),
                    "VideoViews": safe_sum(g_combo, "video_views"),
                    "Engagement": safe_sum(g_combo, "engagements"),
                    "Followers": safe_sum(g_combo, "follows"),
                    "Like": safe_sum(g_combo, "likes"),
                    "Purchase": safe_sum(g_combo, "purchases"),
                }
                kpi_list = []
                # 如果提供了有效的KPI键集合，只包含有效的KPI；否则包含所有KPI
                kpi_keys_to_process = (
                    [k for k in KPI_KEYS if k in valid_kpi_keys]
                    if valid_kpi_keys
                    else KPI_KEYS
                )
                for key in kpi_keys_to_process:
                    val = kpi_vals.get(key, 0.0)
                    int_val = int(val)
                    # 如果值为0，则不添加该KPI（不传该KPI）
                    if int_val == 0:
                        continue
                    kpi_list.append(
                        {
                            "key": key,
                            "val": str(int_val),
                            "priority": KPI_KEYS.index(key) + 1,
                            "completion": 0,
                        }
                    )

                # 获取 creative（从数据中获取，按 media、media_channel、objective、ad_format 聚合后取第一个值）
                # 不再使用推断，直接从数据文件中获取
                if "creative" in g_combo.columns:
                    creative = str(g_combo["creative"].iloc[0]).strip()
                else:
                    creative = ""  # 如果数据中没有，设为空字符串

                # 如果预算为0，则传null
                ad_format_total_budget = int(round(spend))
                ad_format_total_budget_value = (
                    None if ad_format_total_budget == 0 else ad_format_total_budget
                )

                media_entry["adFormatWithKPI"].append(
                    {
                        "funnelName": funnel,
                        "adFormatName": ad_type,  # 新版本：adFormatName 替代 adTypeName
                        "creative": creative,  # 新增字段
                        "adFormatTotalBudget": ad_format_total_budget_value,  # 预算金额保留整数，如果为0则传null
                        "completion": 0,  # 新增字段
                        "kpiInfo": kpi_list,
                    }
                )

        result.append(media_entry)

    return result


def load_testcase_template(template_path: str = "testcase_templatex_xiaomi.py"):
    """
    从 testcase_templatex_xiaomi.py 文件加载测试用例配置。

    Args:
        template_path: 测试用例模板文件路径

    Returns:
        测试用例字典，如果文件不存在或加载失败则返回 None
    """
    try:
        spec = importlib.util.spec_from_file_location(
            "testcase_template", template_path
        )
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "TEST_CASES", None)
    except Exception as e:
        print(f"警告：无法加载测试用例模板 {template_path}: {e}")
        return None


def apply_testcase_template_config(
    result: dict, case_config: dict, case_name: str = None
) -> dict:
    """
    根据 testcase_templatex_xiaomi.py 格式的配置修改生成的JSON数据（适配新版本 format.json 结构）。

    Args:
        result: 生成的JSON数据
        case_config: 测试用例配置字典（testcase_templatex_xiaomi.py 格式）
        case_name: 测试用例名称，将作为 mediaPlanName（可选）

    Returns:
        修改后的JSON数据
    """
    result = deepcopy(result)
    basic_info = result["basicInfo"]

    # 设置 mediaPlanName（如果提供了用例名称）
    if case_name:
        basic_info["mediaPlanName"] = case_name

    # 为随机勾选 completion 生成可复现的随机数实例（基于用例名）
    rng = random.Random(case_name or "default_seed")

    def choose_completion_flags(n: int) -> list[int]:
        """
        返回长度为 n 的 0/1 列表：
        - 如果 n <= 1，全 1（无法部分勾选）
        - 否则随机选择 1..n-1 个位置为 1，保证不是全 1 也不是全 0
        """
        if n <= 1:
            return [1] * n
        ones_count = rng.randint(1, n - 1)
        indices = list(range(n))
        rng.shuffle(indices)
        flags = [0] * n
        for idx in indices[:ones_count]:
            flags[idx] = 1
        return flags

    # 1. 配置 KPI 优先级和 completion
    kpi_info = basic_info.get("kpiInfo", [])
    kpi_priority_list = case_config.get("kpi_priority_list", [])
    kpi_must_achieve = case_config.get("kpi_must_achieve", False)

    # 创建KPI优先级映射（只包含 testcase 中指定的 KPI）
    kpi_priority_map = {}
    for idx, kpi_key in enumerate(kpi_priority_list, 1):
        kpi_priority_map[kpi_key] = idx

    # 只保留 kpi_priority_list 中指定的 KPI
    kpi_info_filtered = [
        kpi_item for kpi_item in kpi_info if kpi_item["key"] in kpi_priority_map
    ]

    # 更新KPI配置
    # 如果必须达成，则随机选择部分 KPI 勾选 completion=1（避免全勾选/全不勾选）
    kpi_flags = (
        choose_completion_flags(len(kpi_info_filtered))
        if kpi_must_achieve
        else [0] * len(kpi_info_filtered)
    )

    for idx, kpi_item in enumerate(kpi_info_filtered):
        kpi_key = kpi_item["key"]
        kpi_item["priority"] = kpi_priority_map[kpi_key]
        kpi_item["completion"] = kpi_flags[idx] if kpi_must_achieve else 0

    # 更新 basicInfo.kpiInfo，只保留过滤后的 KPI
    basic_info["kpiInfo"] = kpi_info_filtered

    # 2. 配置 kpiInfoBudgetConfig
    kpi_target_rate = case_config.get("kpi_target_rate")
    if kpi_target_rate is not None:
        basic_info["kpiInfoBudgetConfig"] = {"rangeMatch": kpi_target_rate}
    else:
        basic_info["kpiInfoBudgetConfig"] = {}

    # 3. 配置 moduleConfig 优先级（basicInfo 级别）
    module_priority_list = case_config.get("module_priority_list", [])
    module_config = basic_info.get("moduleConfig", [])
    for module in module_config:
        module_name = module.get("moduleName")
        if module_name in module_priority_list:
            module["priority"] = module_priority_list.index(module_name) + 1
        else:
            module["priority"] = 999

    # 4. 配置每个国家的 briefMultiConfig
    stage_match_type = case_config.get("stage_match_type", "完全匹配")
    stage_range_match = case_config.get("stage_range_match")
    marketingfunnel_match_type = case_config.get(
        "marketingfunnel_match_type", "完全匹配"
    )
    marketingfunnel_range_match = case_config.get("marketingfunnel_range_match")
    media_match_type = case_config.get("media_match_type", "完全匹配")
    media_range_match = case_config.get("media_range_match")
    allow_zero_budget = case_config.get("allow_zero_budget", False)
    mediaMarketingFunnelFormat_target_rate = case_config.get(
        "mediaMarketingFunnelFormat_target_rate"
    )
    mediaMarketingFunnelFormat_must_achieve = case_config.get(
        "mediaMarketingFunnelFormat_must_achieve", False
    )
    mediaMarketingFunnelFormatBudgetConfig_target_rate = case_config.get(
        "mediaMarketingFunnelFormatBudgetConfig_target_rate"
    )
    mediaMarketingFunnelFormatBudgetConfig_must_achieve = case_config.get(
        "mediaMarketingFunnelFormatBudgetConfig_must_achieve", False
    )

    for country_config in result.get("briefMultiConfig", []):
        # 配置 stageBudgetConfig
        stage_config = {
            "consistentMatch": 1 if stage_match_type == "完全匹配" else 0,
        }
        if stage_match_type == "完全匹配" and stage_range_match is not None:
            stage_config["rangeMatch"] = stage_range_match
        country_config["stageBudgetConfig"] = stage_config

        # 配置 marketingFunnelBudgetConfig
        mf_config = {
            "consistentMatch": 1 if marketingfunnel_match_type == "完全匹配" else 0,
        }
        if (
            marketingfunnel_match_type == "完全匹配"
            and marketingfunnel_range_match is not None
        ):
            mf_config["rangeMatch"] = marketingfunnel_range_match
        country_config["marketingFunnelBudgetConfig"] = mf_config

        # 配置 mediaBudgetConfig
        media_config = {
            "consistentMatch": 1 if media_match_type == "完全匹配" else 0,
        }
        if media_match_type == "完全匹配" and media_range_match is not None:
            media_config["rangeMatch"] = media_range_match
        country_config["mediaBudgetConfig"] = media_config

        # 配置 mediaMarketingFunnelFormatBudgetConfig
        mmff_config = {}
        if allow_zero_budget:
            mmff_config["precision"] = 1  # 允许为0
        else:
            mmff_config["precision"] = 2  # 不允许为0
        # mediaMarketingFunnelFormat_target_rate 对应 kpiFlexibility
        if mediaMarketingFunnelFormat_target_rate is not None:
            mmff_config["kpiFlexibility"] = mediaMarketingFunnelFormat_target_rate
        # mediaMarketingFunnelFormatBudgetConfig_target_rate 对应 totalBudgetFlexibility
        if mediaMarketingFunnelFormatBudgetConfig_target_rate is not None:
            mmff_config["totalBudgetFlexibility"] = (
                mediaMarketingFunnelFormatBudgetConfig_target_rate
            )
        country_config["mediaMarketingFunnelFormatBudgetConfig"] = mmff_config

        # 配置国家级别的 moduleConfig
        country_module_config = country_config.get("moduleConfig", [])
        for module in country_module_config:
            module_name = module.get("moduleName")
            if module_name in module_priority_list:
                module["priority"] = module_priority_list.index(module_name) + 1
            else:
                module["priority"] = 999

        # 过滤 mediaMarketingFunnelFormat 中的 KPI，只保留 kpi_priority_list 中指定的
        # 新版本使用 mediaMarketingFunnelFormat -> adFormatWithKPI
        # 收集所有 adFormatWithKPI 项，用于随机设置 completion
        all_adformats = []
        for mmff in country_config.get("mediaMarketingFunnelFormat", []):
            for adformat in mmff.get("adFormatWithKPI", []):
                all_adformats.append(adformat)
                kpi_list = adformat.get("kpiInfo", [])
                kpi_list_filtered = [
                    kpi_item
                    for kpi_item in kpi_list
                    if kpi_item["key"] in kpi_priority_map
                ]
                # 更新优先级（只保留过滤后的 KPI）
                # 如果 mediaMarketingFunnelFormat_must_achieve 为 True，随机设置 KPI 的 completion
                if mediaMarketingFunnelFormat_must_achieve:
                    kpi_flags = choose_completion_flags(len(kpi_list_filtered))
                    for idx, kpi_item in enumerate(kpi_list_filtered):
                        kpi_key = kpi_item["key"]
                        kpi_item["priority"] = kpi_priority_map[kpi_key]
                        kpi_item["completion"] = kpi_flags[idx]
                else:
                    for kpi_item in kpi_list_filtered:
                        kpi_key = kpi_item["key"]
                        kpi_item["priority"] = kpi_priority_map[kpi_key]
                        kpi_item["completion"] = 0
                adformat["kpiInfo"] = kpi_list_filtered

        # 如果 mediaMarketingFunnelFormatBudgetConfig_must_achieve 为 True，随机设置 completion
        # 只对 adFormatTotalBudget 不为 null 的项设置 completion
        # 不能全部为必须达成，也不能全部不为必须达成
        if mediaMarketingFunnelFormatBudgetConfig_must_achieve:
            # 只收集有 adFormatTotalBudget 的项
            adformats_with_budget = [
                adformat
                for adformat in all_adformats
                if adformat.get("adFormatTotalBudget") is not None
            ]
            if adformats_with_budget:
                budget_completion_flags = choose_completion_flags(
                    len(adformats_with_budget)
                )
                for idx, adformat in enumerate(adformats_with_budget):
                    adformat["completion"] = budget_completion_flags[idx]
            # 对于没有预算的项，completion 保持为 0
            for adformat in all_adformats:
                if adformat.get("adFormatTotalBudget") is None:
                    adformat["completion"] = 0
        else:
            for adformat in all_adformats:
                adformat["completion"] = 0

    return result


def build_brief_multi_config(
    template_first_country: dict,
    df: pd.DataFrame,
    country_df: pd.DataFrame = None,
    valid_kpi_keys: set = None,
) -> list[dict]:
    """
    构建 briefMultiConfig 数组，每个国家一条。
    新版本使用 countryInfo 和 mediaMarketingFunnelFormat。
    """
    res = []

    # 通用配置从模板第一个国家拷贝
    tmpl = template_first_country
    common_module_config = tmpl.get("moduleConfig") or []
    common_stage_cfg = tmpl.get("stageBudgetConfig") or {}
    common_mf_cfg = tmpl.get("marketingFunnelBudgetConfig") or {}
    common_media_cfg = tmpl.get("mediaBudgetConfig") or {}
    common_mmff_cfg = (
        tmpl.get("mediaMarketingFunnelFormatBudgetConfig") or {}
    )  # 新版本字段名

    # 建立国家信息映射
    country_map = {}
    if country_df is not None and not country_df.empty:
        for _, r in country_df.iterrows():
            code = str(r.get("countryCode", "")).strip()
            if code:
                country_map[code] = {
                    "countryCode": code,
                    "countryNameCN": str(r.get("countryNameCN", "")).strip(),
                    "countryNameEn": str(r.get("countryNameEn", "")).strip(),
                    "regionCode": str(r.get("regionCode", "")).strip(),
                    "regionNameCN": str(r.get("regionNameCN", "")).strip(),
                    "mpCode": str(r.get("mpCode", code)).strip(),
                }

    for code, g in df.groupby("country_code"):
        # 从字典获取国家信息，如果不存在则使用默认值
        if code in country_map:
            country_info = country_map[code].copy()
        else:
            # 默认值
            country_info = {
                "countryCode": code,
                "countryNameCN": "",
                "countryNameEn": "",
                "regionCode": "",
                "regionNameCN": "",
                "mpCode": code,
            }

        # 新版本：使用 countryInfo 结构
        country_entry: dict = {
            "countryInfo": country_info,
            "moduleConfig": deepcopy(common_module_config),
            "stageBudgetConfig": deepcopy(common_stage_cfg),
            "marketingFunnelBudgetConfig": deepcopy(common_mf_cfg),
            "mediaBudgetConfig": deepcopy(common_media_cfg),
            "mediaMarketingFunnelFormatBudgetConfig": deepcopy(
                common_mmff_cfg
            ),  # 新版本字段名
        }

        country_entry["stage"] = build_country_stage(g)
        country_entry["marketingFunnel"] = build_country_marketing_funnel(g)
        country_entry["media"] = build_country_media(g)
        country_entry["mediaMarketingFunnelFormat"] = (  # 新版本字段名
            build_country_media_marketing_format(g, valid_kpi_keys)
        )

        res.append(country_entry)

    return res


def convert(
    data_path: str = "data_xiaomi.csv",
    template_path: str = "format.json",
    output_path: str = "cases/brief_from_data_v2.json",
    max_regions: int | None = None,
    country_path: str = None,  # 国家字典路径
    adformat_path: str = None,  # 广告格式字典路径
    test_case_id: str | None = None,  # 测试用例编号或名称
    use_testcase_template: bool = False,  # 是否使用测试用例模板
    testcase_template_path: str = "testcase_templatex_xiaomi.py",  # 测试用例模板路径
) -> dict:
    """
    主入口：将 data_xiaomi.csv 转成符合新版本 format.json 结构的 JSON。

    Args:
        data_path: 数据CSV文件路径
        template_path: 模板JSON文件路径
        output_path: 输出JSON文件路径
        max_regions: 最大区域数量限制
        country_path: 国家字典路径
        adformat_path: 广告格式字典路径

    Returns:
        生成的JSON数据字典
    """
    try:
        # 读取模板
        with open(template_path, "r", encoding="utf-8") as f:
            template = json.load(f)

        template_basic = template["basicInfo"]
        template_first_country = template["briefMultiConfig"][0]

        # 读取国家字典
        country_df = None
        if country_path:
            country_df = load_country_dict(country_path)

        # 读取广告格式字典
        adformat_df = None
        if adformat_path:
            adformat_df = load_adformat_dict(adformat_path)

        data_df = load_data(data_path)

        # 创建空的 map_df（Marketing Funnel 将从 Objective 推断）
        map_df = pd.DataFrame()

        merged_df = attach_mapping(data_df, map_df, adformat_df)

        # 控制区域数量：只保留花费最高的前 max_regions 个国家
        # 优先使用函数参数 max_regions，其次使用全局常量 MAX_REGION_COUNT
        limit = max_regions if max_regions is not None else MAX_REGION_COUNT
        if limit is not None and "country_code" in merged_df.columns:
            country_spend = (
                merged_df.groupby("country_code")["spend"]
                .sum()
                .sort_values(ascending=False)
            )
            top_countries = country_spend.head(limit).index.tolist()
            merged_df = merged_df[merged_df["country_code"].isin(top_countries)]

        # 构建 basicInfo
        basic_info = build_basic_info(template_basic, merged_df, country_df)

        # 获取有效的KPI键（从basicInfo的kpiInfo中提取，只包含val不为null的KPI）
        valid_kpi_keys = {item["key"] for item in basic_info.get("kpiInfo", [])}

        # briefMultiConfig
        brief_multi = build_brief_multi_config(
            template_first_country, merged_df, country_df, valid_kpi_keys
        )

        result = {
            "basicInfo": basic_info,
            "briefMultiConfig": brief_multi,
        }

        # 应用测试用例配置（如果指定）
        if test_case_id is not None and use_testcase_template:
            test_cases = load_testcase_template(testcase_template_path)
            if test_cases is None:
                raise ValueError(f"无法加载测试用例模板: {testcase_template_path}")
            if test_case_id not in test_cases:
                raise ValueError(f"测试用例编号 {test_case_id} 不存在于模板中")
            # 传递用例名称（用例ID就是用例名称）
            result = apply_testcase_template_config(
                result, test_cases[test_case_id], case_name=str(test_case_id)
            )

        # 统一按 priority 排序（升序）
        reorder_priorities(result)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result
    except FileNotFoundError as e:
        print(f"[ERROR] 文件未找到: {e}")
        traceback.print_exc()
        raise
    except KeyError as e:
        print(f"[ERROR] 键错误（可能是模板或数据格式问题）: {e}")
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"[ERROR] 转换过程中发生错误: {e}")
        traceback.print_exc()
        raise


def batch_generate(
    data_path: str = "data_xiaomi.csv",
    template_path: str = "format.json",
    output_dir: str = "output/xiaomi/requests",
    max_regions: int | None = None,
    country_path: str = None,
    adformat_path: str = None,
    testcase_template_path: str = "testcase_templatex_xiaomi.py",
    test_case_ids: list[str] | None = None,
) -> list[dict]:
    """
    批量生成多个测试用例的JSON文件。

    Args:
        data_path: 数据CSV文件路径
        template_path: 模板JSON文件路径
        output_dir: 输出目录
        max_regions: 最大区域数量限制
        country_path: 国家字典路径
        adformat_path: 广告格式字典路径
        testcase_template_path: testcase_templatex_xiaomi.py 文件路径
        test_case_ids: 要生成的测试用例名称列表，如果为None则生成所有用例

    Returns:
        生成的JSON数据字典列表
    """
    # 加载测试用例模板
    test_cases = load_testcase_template(testcase_template_path)
    if test_cases is None:
        raise ValueError(f"无法加载测试用例模板: {testcase_template_path}")

    # 确定要生成的测试用例列表
    if test_case_ids is None:
        test_case_ids = sorted(test_cases.keys())

    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = []
    for case_id in test_case_ids:
        if case_id not in test_cases:
            print(f"警告：跳过不存在的测试用例 {case_id}")
            continue

        print(f"正在生成测试用例 {case_id}...")
        # 使用用例名称作为文件名（替换特殊字符）
        safe_filename = case_id.replace("/", "_").replace("\\", "_").replace(":", "_")
        output_file = output_path / f"brief_case_{safe_filename}.json"

        try:
            result = convert(
                data_path=data_path,
                template_path=template_path,
                output_path=str(output_file),
                max_regions=max_regions,
                country_path=country_path,
                adformat_path=adformat_path,
                test_case_id=case_id,
                use_testcase_template=True,
                testcase_template_path=testcase_template_path,
            )
            results.append(result)
            print(f"[OK] 已生成测试用例 {case_id}: {output_file}")
        except Exception as e:
            print(f"✗ 生成测试用例 {case_id} 失败: {e}")
            print(f"详细错误信息:")
            traceback.print_exc()

    print(f"\n批量生成完成，共生成 {len(results)} 个文件")
    return results


if __name__ == "__main__":
    import sys

    # 解析命令行参数
    max_regions = 1
    data_path = "data_xiaomi.csv"  # 默认使用新格式数据文件
    template_path = "format.json"
    output_path = "cases/brief_from_data_v2.json"
    output_dir = "output/xiaomi/requests"
    country_path = "doc/xiaomi/country.csv"
    adformat_path = "doc/xiaomi/adformat.csv"
    test_case_id = None
    use_testcase_template = True
    testcase_template_path = "testcase_templatex_xiaomi.py"
    batch_mode = True

    try:
        if batch_mode:
            # 批量生成所有测试用例
            batch_generate(
                data_path=data_path,
                template_path=template_path,
                output_dir=output_dir,
                max_regions=max_regions,
                country_path=country_path,
                adformat_path=adformat_path,
                testcase_template_path=testcase_template_path,
                test_case_ids=None,  # None 表示生成所有用例
            )
        else:
            # 单个生成
            convert(
                data_path=data_path,
                template_path=template_path,
                output_path=output_path,
                max_regions=max_regions,
                country_path=country_path,
                adformat_path=adformat_path,
                test_case_id=test_case_id,
                use_testcase_template=use_testcase_template,
                testcase_template_path=testcase_template_path,
            )
            print("转换完成！")
    except Exception as e:
        print(f"转换失败: {e}")
        print("\n详细错误堆栈:")
        traceback.print_exc()
        sys.exit(1)
