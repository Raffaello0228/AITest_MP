import json
import uuid
from collections import defaultdict
from copy import deepcopy

import numpy as np
import pandas as pd


KPI_KEYS = [
    "Impression",
    "Clicks",
    "LinkClicks",
    "VideoViews",
    "Engagement",
    "Followers",
    "Like",
    "Purchase",
]

# 若希望限制 JSON 中的推广区域（国家）数量，在此设置最大国家数；
# 例如设为 5 表示只保留花费最高的前 5 个国家；设为 None 则不过滤。
MAX_REGION_COUNT: int | None = None


def load_mapping(adtype_path: str) -> pd.DataFrame:
    """
    读取 adtype 映射表（CSV），标准化列名，主要按 (Media, Ad Type) 做映射。
    """
    # 先尝试 utf-8，如果失败再回退到常见的本地编码（如 gbk）
    try:
        df = pd.read_csv(adtype_path, encoding="utf-8")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(adtype_path, encoding="gbk")
        except UnicodeDecodeError:
            # 最后兜底：使用 latin1 防止再次抛错（可能会出现少量乱码，但不影响英文字段）
            df = pd.read_csv(adtype_path, encoding="latin1")
    # 去掉前后空格
    df.columns = [c.strip() for c in df.columns]
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()
    return df


def load_data(data_path: str) -> pd.DataFrame:
    """
    读取历史数据 CSV，并做基本清洗。
    """
    df = pd.read_csv(data_path)

    # 统一列名
    df.columns = [c.strip() for c in df.columns]

    # 将 \N 等视为缺失
    df = df.replace({"\\N": np.nan})

    # 数值列转浮点
    num_cols = [
        "spend",
        "impressions",
        "clicks",
        "link_clicks",
        "engagements",
        "likes",
        "video_views",
        "video_watched_2s",
        "purchases",
        "leads",
        "follows",
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    return df


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
        return "Tiktok"

    # 根据 media_channel 直接判断
    if media_channel in {"FB", "IG", "FB&IG", "FBIGFB&IG"}:
        return "Meta"
    if media_channel in {"YTB", "GG"}:
        return "Google"
    if media_channel == "TT":
        return "Tiktok"

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


def build_basic_info(template_basic: dict, df: pd.DataFrame) -> dict:
    """
    构建 basicInfo：总预算 + 全局 KPI 聚合 + 区域预算。
    """
    basic = deepcopy(template_basic)

    total_budget = float(df["spend"].sum())
    basic["totalBudget"] = round(total_budget, 2)

    # 全局 KPI 聚合
    kpi_agg = {
        "Impression": df["impressions"].sum(),
        "Clicks": df["clicks"].sum(),
        "LinkClicks": df["link_clicks"].sum(),
        "VideoViews": df["video_views"].sum(),
        "Engagement": df["engagements"].sum(),
        "Followers": df["follows"].sum(),
        "Like": df["likes"].sum(),
        "Purchase": df["purchases"].sum(),
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
                "completion": 1,
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
            "Impression": g["impressions"].sum(),
            "Clicks": g["clicks"].sum(),
            "LinkClicks": g["link_clicks"].sum(),
            "VideoViews": g["video_views"].sum(),
            "Engagement": g["engagements"].sum(),
            "Followers": g["follows"].sum(),
            "Like": g["likes"].sum(),
            "Purchase": g["purchases"].sum(),
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
            plat_pct = plat_budget / media_budget * 100 if media_budget > 0 else 0
            children.append(
                {
                    "name": platform,
                    "budgetPercentage": round(plat_pct, 2),
                    "budgetAmount": round(plat_budget, 2),
                }
            )

        res.append(
            {
                "name": media,
                "budgetPercentage": round(media_pct, 2),
                "budgetAmount": round(media_budget, 2),
                "children": children,
            }
        )
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
    - 每个 media 一条
    - platform: 当前国家该 media 下所有平台
    - marketingFunnels: 当前 media 相关的所有 funnel
    - adTypeWithKPI: 按 (funnel, ad_type, platform) 聚合 KPI
    """
    result = []

    # 先按 media 切分
    for media, g_media in country_df.dropna(subset=["Media_final"]).groupby(
        "Media_final"
    ):
        media_entry: dict = {
            "mediaName": media,
            "platform": sorted(
                {
                    p
                    for p in g_media["Platform_final"].unique().tolist()
                    if isinstance(p, str) and p
                }
            ),
            "marketingFunnels": [],
            "adTypeWithKPI": [],
        }

        # marketingFunnels 列表
        funnels = sorted(
            {
                f
                for f in g_media["Funnel_final"].unique().tolist()
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

        # adTypeWithKPI：按 (funnel, ad_type, platform) 聚合
        key_cols = ["Funnel_final", "ad_type", "Platform_final"]
        g_valid = g_media.dropna(subset=["Funnel_final", "ad_type"])
        if not g_valid.empty:
            grouped = g_valid.groupby(key_cols)
            for (funnel, ad_type, platform), g_combo in grouped:
                spend = float(g_combo["spend"].sum())
                # KPI 聚合
                kpi_vals = {
                    "Impression": g_combo["impressions"].sum(),
                    "Clicks": g_combo["clicks"].sum(),
                    "LinkClicks": g_combo["link_clicks"].sum(),
                    "VideoViews": g_combo["video_views"].sum(),
                    "Engagement": g_combo["engagements"].sum(),
                    "Followers": g_combo["follows"].sum(),
                    "Like": g_combo["likes"].sum(),
                    "Purchase": g_combo["purchases"].sum(),
                }
                kpi_list = []
                for key in KPI_KEYS:
                    kpi_list.append(
                        {
                            "key": key,
                            "val": str(int(kpi_vals.get(key, 0.0))),
                            "priority": KPI_KEYS.index(key) + 1,
                            "completion": 0,
                        }
                    )

                media_entry["adTypeWithKPI"].append(
                    {
                        "funnelName": funnel,
                        "adTypeName": ad_type,
                        "platform": platform,
                        "spend": round(spend, 2),
                        "kpiInfo": kpi_list,
                    }
                )

        result.append(media_entry)

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
    output_path: str = "brief_from_data.json",
    max_regions: int | None = None,
) -> dict:
    """
    主入口：将 data.csv 转成符合 brief_template 结构的 JSON。
    """
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

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result


if __name__ == "__main__":
    # 如需在命令行控制区域数量，可在此传入 max_regions，例如：convert(max_regions=5)
    convert(max_regions=5)
