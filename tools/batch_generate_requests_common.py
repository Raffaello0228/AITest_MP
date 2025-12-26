import json
import uuid
import importlib.util
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import random
import traceback
import sys

import numpy as np
import pandas as pd

# 添加项目根目录到路径，以便导入 core 模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core import (
    KPI_KEYS,
    MAX_REGION_COUNT,
    load_data,
    load_mapping,
    normalize_percentage_sum,
    reorder_priorities,
    safe_sum,
)

# 注意：load_data, load_mapping, normalize_percentage_sum, reorder_priorities, safe_sum 已从 core 模块导入


def infer_media(row: pd.Series, adtype_map_medias: dict) -> str | None:
    """
    根据 channel_id / media_channel / ad_type 推断媒体名称（Meta / Google / Tiktok）。
    """
    ch_id = row.get("channel_id")
    media_channel = str(row.get("media_channel") or "").strip()
    ad_type = str(row.get("ad_type") or "").strip()

    # 显式 channel_id 映射（按当前数据习惯）
    if ch_id == 1:
        return "Meta"
    if ch_id == 3:
        return "Google"
    if ch_id == 18:
        return "TikTok"

    # 根据 media_channel 直接判断
    if media_channel in {"FB", "IG", "FB&IG", "FBIGFB&IG"}:
        return "Meta"
    if media_channel in {"YTB", "GG"}:
        return "Google"
    if media_channel == "TT":
        return "TikTok"

    # 兜底：如果某个 ad_type 只在一个 Media 中出现，就用它
    medias = adtype_map_medias.get(ad_type)
    if medias and len(medias) == 1:
        return list(medias)[0]

    return None


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


def attach_mapping(data_df: pd.DataFrame, map_df: pd.DataFrame) -> pd.DataFrame:
    """
    为 data_df 追加 Media / Platform / Marketing Funnel 等信息。
    """
    # 建立 ad_type -> 多个 media 的集合，用于兜底推断
    adtype_map_medias: dict[str, set[str]] = defaultdict(set)
    for _, r in map_df.iterrows():
        adtype_map_medias[str(r["Ad Type"]).strip()].add(str(r["Media"]).strip())

    # 先推断 Media
    data_df = data_df.copy()
    data_df["channel_id"] = pd.to_numeric(data_df.get("channel_id"), errors="coerce")
    data_df["inferred_media"] = data_df.apply(
        lambda r: infer_media(r, adtype_map_medias), axis=1
    )

    # 按 (Media, Ad Type) 合并
    map_df_small = map_df[
        [
            "Media",
            "Platform",
            "Marketing Funnel",
            "Objective",
            "Ad Type",
            "Media Buy Type",
            "Key Measurement",
        ]
    ].copy()
    map_df_small.rename(
        columns={
            "Marketing Funnel": "mapping_funnel",
            "Objective": "mapping_objective",
            "Media Buy Type": "mapping_buy_type",
            "Key Measurement": "mapping_key_measurement",
        },
        inplace=True,
    )

    merged = data_df.merge(
        map_df_small,
        left_on=["inferred_media", "ad_type"],
        right_on=["Media", "Ad Type"],
        how="left",
    )

    # 最终 Media / Platform / Funnel
    merged["Media_final"] = merged["inferred_media"]

    # 平台优先用数据里的 media_channel，否则用映射
    merged["Platform_final"] = merged["media_channel"].astype(str).str.strip()
    mask_empty_platform = merged["Platform_final"].eq("") | merged["Platform_final"].eq(
        "nan"
    )
    merged.loc[mask_empty_platform, "Platform_final"] = merged.loc[
        mask_empty_platform, "Platform"
    ]
    merged["Platform_final"] = (
        merged["Platform_final"].fillna("").map(normalize_platform)
    )

    merged["Funnel_final"] = merged["mapping_funnel"]

    return merged


# safe_sum 已从 core 模块导入


def build_basic_info(template_basic: dict, df: pd.DataFrame) -> dict:
    """
    构建 basicInfo：总预算 + 全局 KPI 聚合 + 区域预算。
    """
    basic = deepcopy(template_basic)

    total_budget = float(df["spend"].sum())
    basic["totalBudget"] = round(total_budget, 2)

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

    for key in KPI_KEYS:
        val = kpi_agg.get(key, 0.0)
        kpi_info.append(
            {
                "key": key,
                "val": str(int(val)),
                "priority": tmpl_priority_map.get(key, KPI_KEYS.index(key) + 1),
                "completion": 0,  # 初始值为0，后续在 apply_testcase_template_config 中根据 kpi_must_achieve 随机勾选
            }
        )
    basic["kpiInfo"] = kpi_info

    # 区域预算 regionBudget
    region_items = []
    for code, g in df.groupby("country_code"):
        country_budget = float(g["spend"].sum())
        if country_budget <= 0:
            continue

        budget_percentage = (
            country_budget / total_budget * 100 if total_budget > 0 else 0.0
        )

        kpi_country = {
            "Impression": safe_sum(g, "impressions"),
            "Clicks": safe_sum(g, "clicks"),
            "LinkClicks": safe_sum(g, "link_clicks"),
            "VideoViews": safe_sum(g, "video_views"),
            "Engagement": safe_sum(g, "engagements"),
            "Followers": safe_sum(g, "follows"),
            "Like": safe_sum(g, "likes"),
            "Purchase": safe_sum(g, "purchases"),
        }

        kpi_list = []
        for key in KPI_KEYS:
            kpi_list.append(
                {
                    "key": key,
                    "val": str(int(kpi_country.get(key, 0.0))),
                    "completion": 0,
                    "priority": tmpl_priority_map.get(key, KPI_KEYS.index(key) + 1),
                }
            )

        region_items.append(
            {
                "country": {
                    "code": code,
                    "groupName": "CountrySimpleCode",
                },
                "budgetPercentage": round(budget_percentage, 2),
                "budgetAmount": round(country_budget, 2),
                "kpiInfo": kpi_list,
                "completion": 0,
            }
        )

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
                "budgetPercentage": round(pct, 2),
                "budgetAmount": round(budget, 2),
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
                    "budgetPercentage": round(plat_pct, 2),
                    "budgetAmount": round(plat_budget, 2),
                }
            )
            all_children_refs.append(children[-1])

        res.append(
            {
                "name": media,
                "budgetPercentage": round(media_pct, 2),
                "budgetAmount": round(media_budget, 2),
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
                "budgetPercentage": 100,
                "budgetAmount": round(total, 2),
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
                "budgetPercentage": round(pct, 2),
                "budgetAmount": round(budget, 2),
                "dates": None,
                "marketingFunnel": None,
                "mediaPlatform": None,
            }
        )

    # 按时间排序（字符串排序即可，因为是 YYYYMM）
    stages.sort(key=lambda x: x["name"])
    return stages


def build_country_media_marketing_adtype(country_df: pd.DataFrame) -> list[dict]:
    """
    构造 mediaMarketingFunnelAdtype 结构：
    - 每个 (media, platform) 组合一个对象
    - platform: 单个平台名称（数组形式，但只包含一个元素）
    - marketingFunnels: 当前 media-platform 相关的所有 funnel
    - adTypeWithKPI: 按 (funnel, ad_type) 聚合 KPI（platform 已在对象层级）
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
            "adTypeWithKPI": [],
        }

        # marketingFunnels 列表：当前 media-platform 下的所有 funnel
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
                    "adType": [],
                }
            )

        # adTypeWithKPI：按 (funnel, ad_type) 聚合（platform 已在对象层级）
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
                for key in KPI_KEYS:
                    kpi_list.append(
                        {
                            "key": key,
                            "val": str(int(kpi_vals.get(key, 0.0))),
                            # "val": None,
                            "priority": KPI_KEYS.index(key) + 1,
                            "completion": 0,
                        }
                    )

                media_entry["adTypeWithKPI"].append(
                    {
                        "funnelName": funnel,
                        "adTypeName": ad_type,
                        "platform": platform,  # 保留 platform 字段用于兼容
                        "spend": round(spend, 2),
                        "kpiInfo": kpi_list,
                    }
                )

        result.append(media_entry)

    return result


def load_testcase_template(template_path: str = "testcase_template.py"):
    """
    从 testcase_template.py 文件加载测试用例配置。

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
    根据 testcase_template.py 格式的配置修改生成的JSON数据。

    Args:
        result: 生成的JSON数据
        case_config: 测试用例配置字典（testcase_template.py 格式）
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

    # 3. 配置 regionBudgetConfig
    region_match_type = case_config.get("region_match_type", "完全匹配")
    region_budget_range_match = case_config.get("region_budget_range_match")
    region_budget_must_achieve = case_config.get("region_budget_must_achieve", False)
    region_budget_target_rate = case_config.get("region_budget_target_rate")
    region_kpi_target_rate = case_config.get("region_kpi_target_rate")

    region_config = {
        "consistentMatch": 1 if region_match_type == "完全匹配" else 0,
    }
    if region_match_type == "完全匹配" and region_budget_range_match is not None:
        region_config["rangeMatch"] = region_budget_range_match
    # 无论是否 must_achieve，只要提供了目标达成率就写入，避免遗漏
    if region_budget_target_rate is not None:
        region_config["budgetCompletionRule"] = region_budget_target_rate
    if region_kpi_target_rate is not None:
        region_config["kpiCompletionRule"] = region_kpi_target_rate
    basic_info["regionBudgetConfig"] = region_config

    # 4. 配置 moduleConfig 优先级
    module_priority_list = case_config.get("module_priority_list", [])
    module_config = basic_info.get("moduleConfig", [])
    for module in module_config:
        module_name = module.get("moduleName")
        if module_name in module_priority_list:
            module["priority"] = module_priority_list.index(module_name) + 1
        else:
            module["priority"] = 999

    # 5. 更新 regionBudget 中每个国家的 KPI 优先级和 completion
    # 为区域 completion 生成随机标记（若必须达成为 True）
    regions = basic_info.get("regionBudget", [])
    region_flags = (
        choose_completion_flags(len(regions))
        if region_budget_must_achieve
        else [0] * len(regions)
    )

    for r_idx, region in enumerate(regions):
        # 设置 region 的 completion（根据 region_budget_must_achieve，并随机选择）
        region["completion"] = region_flags[r_idx]

        # 区域 KPI 同样按全局 KPI 优先级映射，且当 kpi_must_achieve 为 True 时随机选择部分勾选
        # 只保留 kpi_priority_list 中指定的 KPI
        kpi_list = region.get("kpiInfo", [])
        kpi_list_filtered = [
            kpi_item for kpi_item in kpi_list if kpi_item["key"] in kpi_priority_map
        ]

        region_kpi_flags = (
            choose_completion_flags(len(kpi_list_filtered))
            if kpi_must_achieve
            else [0] * len(kpi_list_filtered)
        )

        for k_idx, region_kpi in enumerate(kpi_list_filtered):
            kpi_key = region_kpi["key"]
            region_kpi["priority"] = kpi_priority_map[kpi_key]
            region_kpi["completion"] = (
                region_kpi_flags[k_idx] if kpi_must_achieve else 0
            )

        # 更新 region 的 kpiInfo，只保留过滤后的 KPI
        region["kpiInfo"] = kpi_list_filtered

    # 6. 配置每个国家的 briefMultiConfig
    stage_match_type = case_config.get("stage_match_type", "完全匹配")
    stage_range_match = case_config.get("stage_range_match")
    marketingfunnel_match_type = case_config.get(
        "marketingfunnel_match_type", "完全匹配"
    )
    marketingfunnel_range_match = case_config.get("marketingfunnel_range_match")
    media_match_type = case_config.get("media_match_type", "完全匹配")
    media_range_match = case_config.get("media_range_match")
    allow_zero_budget = case_config.get("allow_zero_budget", False)
    mediaMarketingFunnelAdtype_target_rate = case_config.get(
        "mediaMarketingFunnelAdtype_target_rate"
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

        # 配置 mediaMarketingFunnelAdtypeBudgetConfig
        mmfa_config = {}
        if allow_zero_budget:
            mmfa_config["precision"] = 1  # 允许为0
        else:
            mmfa_config["precision"] = 2  # 不允许为0
        if mediaMarketingFunnelAdtype_target_rate is not None:
            mmfa_config["rangeMatch"] = mediaMarketingFunnelAdtype_target_rate
        country_config["mediaMarketingFunnelAdtypeBudgetConfig"] = mmfa_config

        # 配置国家级别的 moduleConfig
        country_module_config = country_config.get("moduleConfig", [])
        for module in country_module_config:
            module_name = module.get("moduleName")
            if module_name in module_priority_list:
                module["priority"] = module_priority_list.index(module_name) + 1
            else:
                module["priority"] = 999

        # 过滤 mediaMarketingFunnelAdtype 中的 KPI，只保留 kpi_priority_list 中指定的
        for mmfa in country_config.get("mediaMarketingFunnelAdtype", []):
            for adtype in mmfa.get("adTypeWithKPI", []):
                kpi_list = adtype.get("kpiInfo", [])
                kpi_list_filtered = [
                    kpi_item
                    for kpi_item in kpi_list
                    if kpi_item["key"] in kpi_priority_map
                ]
                # 更新优先级（只保留过滤后的 KPI）
                for kpi_item in kpi_list_filtered:
                    kpi_key = kpi_item["key"]
                    kpi_item["priority"] = kpi_priority_map[kpi_key]
                adtype["kpiInfo"] = kpi_list_filtered

    return result


def build_brief_multi_config(
    template_first_country: dict, df: pd.DataFrame
) -> list[dict]:
    """
    构建 briefMultiConfig 数组，每个国家一条。
    """
    res = []

    # 通用配置从模板第一个国家拷贝
    tmpl = template_first_country
    common_module_config = tmpl.get("moduleConfig") or []
    common_stage_cfg = tmpl.get("stageBudgetConfig") or {}
    common_mf_cfg = tmpl.get("marketingFunnelBudgetConfig") or {}
    common_media_cfg = tmpl.get("mediaBudgetConfig") or {}
    common_mmfa_cfg = tmpl.get("mediaMarketingFunnelAdtypeBudgetConfig") or {}

    for code, g in df.groupby("country_code"):
        country_entry: dict = {
            "country": {
                "code": code,
                "groupName": "CountrySimpleCode",
            },
            "moduleConfig": deepcopy(common_module_config),
            "stageBudgetConfig": deepcopy(common_stage_cfg),
            "marketingFunnelBudgetConfig": deepcopy(common_mf_cfg),
            "mediaBudgetConfig": deepcopy(common_media_cfg),
            "mediaMarketingFunnelAdtypeBudgetConfig": deepcopy(common_mmfa_cfg),
        }

        country_entry["stage"] = build_country_stage(g)
        country_entry["marketingFunnel"] = build_country_marketing_funnel(g)
        country_entry["media"] = build_country_media(g)
        country_entry["mediaMarketingFunnelAdtype"] = (
            build_country_media_marketing_adtype(g)
        )

        res.append(country_entry)

    return res


def convert(
    data_path: str = "data.csv",
    adtype_path: str = "adtype_dict.csv",
    template_path: str = "brief_template.json",
    output_path: str = "cases/brief_from_data.json",
    max_regions: int | None = None,
    test_case_id: str | int | None = None,
    use_testcase_template: bool = False,
    testcase_template_path: str = "testcase_template.py",
) -> dict:
    """
    主入口：将 data.csv 转成符合 brief_template 结构的 JSON。

    Args:
        data_path: 数据CSV文件路径
        adtype_path: adtype映射表CSV文件路径
        template_path: 模板JSON文件路径
        output_path: 输出JSON文件路径
        max_regions: 最大区域数量限制
        test_case_id: 测试用例编号或名称（字符串），如果提供则应用测试用例配置
        use_testcase_template: 是否使用 testcase_template.py 格式的测试用例
        testcase_template_path: testcase_template.py 文件路径

    Returns:
        生成的JSON数据字典
    """
    try:
        # 读取模板
        with open(template_path, "r", encoding="utf-8") as f:
            template = json.load(f)

        template_basic = template["basicInfo"]
        template_first_country = template["briefMultiConfig"][0]

        # 读取数据与映射
        map_df = load_mapping(adtype_path)
        data_df = load_data(data_path)
        merged_df = attach_mapping(data_df, map_df)

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
        basic_info = build_basic_info(template_basic, merged_df)

        # briefMultiConfig
        brief_multi = build_brief_multi_config(template_first_country, merged_df)

        result = {
            "basicInfo": basic_info,
            "briefMultiConfig": brief_multi,
        }

        # 如果指定了测试用例编号，应用测试用例配置
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
    data_path: str = "data_haier.csv",
    adtype_path: str = "doc/common/adtype_dict.csv",
    template_path: str = "brief_template.json",
    output_dir: str = "output/common/requests",
    max_regions: int | None = None,
    testcase_template_path: str = "testcase_template.py",
    test_case_ids: list[str] | None = None,
) -> list[dict]:
    """
    批量生成多个测试用例的JSON文件。

    Args:
        data_path: 数据CSV文件路径
        adtype_path: adtype映射表CSV文件路径
        template_path: 模板JSON文件路径
        output_dir: 输出目录
        max_regions: 最大区域数量限制
        testcase_template_path: testcase_template.py 文件路径
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
                adtype_path=adtype_path,
                template_path=template_path,
                output_path=str(output_file),
                max_regions=max_regions,
                test_case_id=case_id,
                use_testcase_template=True,
                testcase_template_path=testcase_template_path,
            )
            results.append(result)
            print(f"✓ 已生成测试用例 {case_id}: {output_file}")
        except Exception as e:
            print(f"✗ 生成测试用例 {case_id} 失败: {e}")
            print(f"详细错误信息:")
            traceback.print_exc()

    print(f"\n批量生成完成，共生成 {len(results)} 个文件")
    return results


if __name__ == "__main__":
    import sys

    # 解析命令行参数
    test_case_id = None
    max_regions = 10
    batch_mode = True
    use_testcase_template = False
    testcase_template_path = "testcase_template.py"

    # 批量生成模式
    if batch_mode:
        print("批量生成模式")
        print(f"测试用例模板: {testcase_template_path}")
        print(f"最大区域数: {max_regions}")

        # 如果指定了测试用例名称，只生成指定的用例
        test_case_ids = None
        if test_case_id is not None:
            test_case_ids = [test_case_id]
            print(f"生成指定测试用例: {test_case_id}")
        else:
            print("生成所有测试用例")

        try:
            batch_generate(
                max_regions=max_regions,
                testcase_template_path=testcase_template_path,
                test_case_ids=test_case_ids,
            )
        except Exception as e:
            print(f"批量生成失败: {e}")
            print("\n详细错误堆栈:")
            traceback.print_exc()
            sys.exit(1)
