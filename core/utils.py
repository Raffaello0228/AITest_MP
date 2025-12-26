"""
工具函数
"""

from typing import Dict, List


def normalize_percentage_sum(
    items: list[dict], percent_key: str = "budgetPercentage"
) -> None:
    """
    调整百分比分配，使总和精确为 100（保留两位小数），误差补到最后一项。
    """
    if not items:
        return
    total = round(sum(float(x.get(percent_key, 0) or 0) for x in items), 2)
    diff = round(100 - total, 2)
    items[-1][percent_key] = round(float(items[-1].get(percent_key, 0) or 0) + diff, 2)


def reorder_priorities(result: dict) -> dict:
    """
    按 priority 对各层列表重新排序（升序），确保生成结果顺序一致。
    """

    def sort_list(lst: list[dict]):
        lst.sort(key=lambda x: x.get("priority", 1e9))

    basic = result.get("basicInfo", {})
    # basicInfo.kpiInfo / moduleConfig
    if "kpiInfo" in basic:
        sort_list(basic["kpiInfo"])
    if "moduleConfig" in basic:
        sort_list(basic["moduleConfig"])

    # regionBudget kpiInfo（通用版）
    for region in basic.get("regionBudget", []):
        if "kpiInfo" in region:
            sort_list(region["kpiInfo"])

    # briefMultiConfig 层级
    for country in result.get("briefMultiConfig", []):
        if "moduleConfig" in country:
            sort_list(country["moduleConfig"])
        # mediaMarketingFunnelAdtype -> adTypeWithKPI.kpiInfo（通用版）
        for mmfa in country.get("mediaMarketingFunnelAdtype", []):
            for adtype in mmfa.get("adTypeWithKPI", []):
                if "kpiInfo" in adtype:
                    sort_list(adtype["kpiInfo"])
        # mediaMarketingFunnelFormat -> adFormatWithKPI.kpiInfo（xiaomi版）
        for mmff in country.get("mediaMarketingFunnelFormat", []):
            for adformat in mmff.get("adFormatWithKPI", []):
                if "kpiInfo" in adformat:
                    sort_list(adformat["kpiInfo"])

    return result


def safe_sum(df, col_name: str) -> float:
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
