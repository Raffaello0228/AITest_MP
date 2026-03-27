#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成「Stage-Media 严格容差失败、松弛后可行」的造数 brief。

默认策略：
1. 将 stage 预算比例改为 20/50/30（PREHEAT/OPEN SALE/SUSTAIN）
2. 将 PREHEAT 强绑定 Awareness，以抬高 YTB 实际占比
3. 将 media 目标占比改为 Meta=40, GG=52, YTB=8（Google 合计 60）
4. 校验 gap = |preheat_pct - ytb_target_pct|：
   - gap > strict_range  => 严格容差可触发失败
   - gap <= relax_cap    => 松弛后存在可行空间
"""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path


def _round_amount(total: float, pct: float) -> int:
    return int(round(total * pct / 100.0))


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def _set_stage_distribution(
    country_cfg: dict, total_budget: float, bind_stage_marketing_funnel: bool
) -> None:
    if bind_stage_marketing_funnel:
        stage_specs = [
            ("PREHEAT FOR LOCAL LAUNCH", 20.0, ["Awareness"]),
            ("OPEN SALE", 50.0, ["Traffic"]),
            ("SUSTAIN", 30.0, ["Traffic"]),
        ]
    else:
        # 控制变量：不在 stage 绑定 marketingFunnel，避免 stage-media 冲突掺入 mf 约束
        stage_specs = [
            ("PREHEAT FOR LOCAL LAUNCH", 20.0, None),
            ("OPEN SALE", 50.0, None),
            ("SUSTAIN", 30.0, None),
        ]
    stages = country_cfg.get("stage", [])
    if len(stages) < 3:
        raise ValueError("briefMultiConfig[0].stage 数量不足 3，无法按默认策略造数")

    for idx, (_, pct, funnels) in enumerate(stage_specs):
        stages[idx]["budgetPercentage"] = pct
        stages[idx]["budgetAmount"] = _round_amount(total_budget, pct)
        stages[idx]["marketingFunnel"] = funnels


def _set_media_distribution(country_cfg: dict, total_budget: float) -> None:
    media_list = country_cfg.get("media", [])
    if not media_list:
        raise ValueError("briefMultiConfig[0].media 为空，无法造数")

    # 目标：Meta=40, Google=60；Google 子项 GG=52, YTB=8
    target = {
        "Meta": 40.0,
        "Google": 60.0,
        "GG": 52.0,
        "YTB": 8.0,
    }

    for media in media_list:
        media_name = media.get("name")
        if media_name == "Meta":
            media["budgetPercentage"] = target["Meta"]
            media["budgetAmount"] = _round_amount(total_budget, target["Meta"])
            for child in media.get("children", []):
                child["budgetPercentage"] = target["Meta"]
                child["budgetAmount"] = _round_amount(total_budget, target["Meta"])
        elif media_name == "Google":
            media["budgetPercentage"] = target["Google"]
            media["budgetAmount"] = _round_amount(total_budget, target["Google"])
            for child in media.get("children", []):
                child_name = child.get("name")
                if child_name == "GG":
                    child["budgetPercentage"] = target["GG"]
                    child["budgetAmount"] = _round_amount(total_budget, target["GG"])
                elif child_name == "YTB":
                    child["budgetPercentage"] = target["YTB"]
                    child["budgetAmount"] = _round_amount(total_budget, target["YTB"])


def _set_constraint_config(country_cfg: dict, strict_range: int) -> None:
    stage_cfg = country_cfg.setdefault("stageBudgetConfig", {})
    media_cfg = country_cfg.setdefault("mediaBudgetConfig", {})

    stage_cfg["consistentMatch"] = 1
    if "rangeMatch" not in stage_cfg:
        stage_cfg["rangeMatch"] = 20

    media_cfg["consistentMatch"] = 1
    media_cfg["rangeMatch"] = strict_range


def _deprioritize_marketing_funnel_modules(data: dict, country_cfg: dict) -> None:
    """降权 marketingFunnel 相关模块，尽量聚焦 stage/media 冲突。"""

    def _deprioritize(module_config: list[dict]) -> None:
        for module in module_config:
            name = module.get("moduleName")
            if name in {"marketingFunnel"}:
                module["priority"] = 999
            elif name in {"stage", "media"}:
                module["priority"] = min(module.get("priority", 999), 10)

    basic_module_config = data.get("basicInfo", {}).get("moduleConfig", [])
    country_module_config = country_cfg.get("moduleConfig", [])
    _deprioritize(basic_module_config)
    _deprioritize(country_module_config)

    mf_cfg = country_cfg.setdefault("marketingFunnelBudgetConfig", {})
    mf_cfg["consistentMatch"] = 0
    mf_cfg.pop("rangeMatch", None)


def _derive_kpi_targets_from_check(
    check_json_path: Path,
    global_kpi_multiplier: float,
    adformat_kpi_multiplier: float,
) -> dict:
    """从 achievement_check.json 反推 KPI 目标（按倍率放大）。"""
    check_data = _load_json(check_json_path)

    derived = {"global_kpi_targets": {}, "adformat_kpi_targets": {}}

    global_kpi = check_data.get("global_kpi", {})
    for key in ["Impression", "Clicks", "VideoViews"]:
        actual = float(global_kpi.get(key, {}).get("actual", 0) or 0)
        if actual > 0:
            derived["global_kpi_targets"][key] = int(
                math.ceil(actual * global_kpi_multiplier)
            )
        else:
            # 避免把无法达成的 0 指标强行设为 must-achieve
            derived["global_kpi_targets"][key] = 0

    adformat_kpi = check_data.get("mediaMarketingFunnelFormat_kpi", {})
    for composite_key, item in adformat_kpi.items():
        kpis = item.get("kpis", {})
        target_map = {}
        for key in ["Impression", "Clicks", "VideoViews"]:
            actual = float(kpis.get(key, {}).get("actual", 0) or 0)
            if actual > 0:
                target_map[key] = int(math.ceil(actual * adformat_kpi_multiplier))
            else:
                target_map[key] = 0
        derived["adformat_kpi_targets"][composite_key] = target_map

    return derived


def _inject_kpi_pressure(
    data: dict,
    country_cfg: dict,
    kpi_target_rate: int,
    force_adformat_budget: bool,
    derived_kpi_targets: dict | None = None,
) -> None:
    """注入 KPI 压力：提高 must-achieve 比例与目标值，制造预算与 KPI 的冲突。"""
    basic_info = data.get("basicInfo", {})

    # 1) 全局 KPI：全部设为必须达成，目标值显著提高
    derived_global = (derived_kpi_targets or {}).get("global_kpi_targets", {})
    global_kpis = [
        ("Impression", str(derived_global.get("Impression", 120000000)), 1),
        ("Clicks", str(derived_global.get("Clicks", 1200000)), 2),
        ("VideoViews", str(derived_global.get("VideoViews", 12000000)), 3),
    ]
    basic_info["kpiInfo"] = [
        {
            "key": key,
            "val": val,
            "priority": priority,
            "completion": 1 if float(val) > 0 else 0,
        }
        for key, val, priority in global_kpis
    ]
    basic_info["kpiInfoBudgetConfig"] = {"rangeMatch": kpi_target_rate}

    # 2) 国家级 adformat KPI：全部 completion=1，并对关键漏斗增强 KPI 目标
    mmff_list = country_cfg.get("mediaMarketingFunnelFormat", [])
    country_code = (
        country_cfg.get("countryInfo", {}).get("countryCode")
        or country_cfg.get("country", {}).get("code")
        or "SG"
    )
    derived_adformat = (derived_kpi_targets or {}).get("adformat_kpi_targets", {})
    for mmff in mmff_list:
        media_name = mmff.get("mediaName")
        platform_list = mmff.get("platform", [])
        platform_name = platform_list[0] if platform_list else ""
        for adformat in mmff.get("adFormatWithKPI", []):
            ad_name = adformat.get("adFormatName", "")
            funnel_name = adformat.get("funnelName", "")
            composite_key = (
                f"{country_code}|{media_name}|{platform_name}|{funnel_name}|{ad_name}"
            )
            derived_targets = derived_adformat.get(composite_key, {})

            # 可选：加 adformat 预算约束，进一步增加冲突概率
            if force_adformat_budget:
                if "Search" in ad_name:
                    adformat["adFormatTotalBudget"] = 2400000
                elif "Demand Gen" in ad_name:
                    adformat["adFormatTotalBudget"] = 720000
                elif "VRC" in ad_name:
                    adformat["adFormatTotalBudget"] = 1080000
                elif "Image&Video Link Ads" in ad_name:
                    adformat["adFormatTotalBudget"] = 1800000
            adformat["completion"] = 1

            kpi_list = adformat.get("kpiInfo", [])
            for kpi in kpi_list:
                key = kpi.get("key")
                if key in derived_targets:
                    target_val = int(derived_targets[key] or 0)
                elif key == "Impression":
                    target_val = 80000000 if media_name == "Meta" else 40000000
                elif key == "Clicks":
                    if media_name == "Google" and "GG" in platform_list:
                        target_val = 900000
                    else:
                        target_val = 300000
                elif key == "VideoViews":
                    if media_name == "Google" and "YTB" in platform_list:
                        target_val = 9000000
                    else:
                        target_val = 1500000
                else:
                    target_val = 0
                kpi["val"] = str(target_val)
                kpi["completion"] = 1 if target_val > 0 else 0

    # 3) 收紧 adformat KPI/预算灵活度
    mmff_cfg = country_cfg.setdefault("mediaMarketingFunnelFormatBudgetConfig", {})
    mmff_cfg["precision"] = 2
    mmff_cfg["kpiFlexibility"] = kpi_target_rate
    mmff_cfg["totalBudgetFlexibility"] = kpi_target_rate


def generate_case(
    input_brief: Path,
    output_brief: Path,
    strict_range: int,
    relax_cap: int,
    bind_stage_marketing_funnel: bool,
    isolate_stage_media_only: bool,
    inject_kpi_pressure: bool,
    kpi_target_rate: int,
    force_adformat_budget: bool,
    derive_kpi_from_check: Path | None,
    global_kpi_multiplier: float,
    adformat_kpi_multiplier: float,
) -> dict:
    src = _load_json(input_brief)
    data = copy.deepcopy(src)

    total_budget = float(data["basicInfo"]["totalBudget"])
    country_cfg = data["briefMultiConfig"][0]
    derived_kpi_targets = None
    if inject_kpi_pressure and derive_kpi_from_check is not None:
        derived_kpi_targets = _derive_kpi_targets_from_check(
            check_json_path=derive_kpi_from_check,
            global_kpi_multiplier=global_kpi_multiplier,
            adformat_kpi_multiplier=adformat_kpi_multiplier,
        )

    _set_stage_distribution(
        country_cfg=country_cfg,
        total_budget=total_budget,
        bind_stage_marketing_funnel=bind_stage_marketing_funnel,
    )
    _set_media_distribution(country_cfg, total_budget)
    _set_constraint_config(country_cfg, strict_range)
    if isolate_stage_media_only:
        _deprioritize_marketing_funnel_modules(data, country_cfg)
    if inject_kpi_pressure:
        _inject_kpi_pressure(
            data=data,
            country_cfg=country_cfg,
            kpi_target_rate=kpi_target_rate,
            force_adformat_budget=force_adformat_budget,
            derived_kpi_targets=derived_kpi_targets,
        )

    _save_json(output_brief, data)

    preheat_pct = float(country_cfg["stage"][0]["budgetPercentage"])
    ytb_pct = 0.0
    for media in country_cfg.get("media", []):
        if media.get("name") != "Google":
            continue
        for child in media.get("children", []):
            if child.get("name") == "YTB":
                ytb_pct = float(child.get("budgetPercentage", 0.0))
                break
    gap = abs(preheat_pct - ytb_pct)

    return {
        "input_brief": str(input_brief),
        "output_brief": str(output_brief),
        "preheat_pct": preheat_pct,
        "ytb_target_pct": ytb_pct,
        "gap": gap,
        "strict_range": strict_range,
        "relax_cap": relax_cap,
        "bind_stage_marketing_funnel": bind_stage_marketing_funnel,
        "isolate_stage_media_only": isolate_stage_media_only,
        "inject_kpi_pressure": inject_kpi_pressure,
        "kpi_target_rate": kpi_target_rate,
        "force_adformat_budget": force_adformat_budget,
        "derive_kpi_from_check": str(derive_kpi_from_check)
        if derive_kpi_from_check
        else None,
        "global_kpi_multiplier": global_kpi_multiplier,
        "adformat_kpi_multiplier": adformat_kpi_multiplier,
        "strict_should_fail": gap > strict_range,
        "relax_should_pass": gap <= relax_cap,
        "suggested_testcase": {
            "name": "新增约束-不可行时容差松弛到max25-自动造数",
            "stage_match_type": "完全匹配",
            "stage_range_match": 20,
            "kpi_must_achieve": bool(inject_kpi_pressure),
            "kpi_target_rate": kpi_target_rate if inject_kpi_pressure else 80,
            "media_match_type": "完全匹配",
            "media_range_match": strict_range,
            "allow_zero_budget": False,
            "mediaMarketingFunnelFormat_target_rate": (
                kpi_target_rate if inject_kpi_pressure else 80
            ),
            "mediaMarketingFunnelFormat_must_achieve": bool(inject_kpi_pressure),
            "mediaMarketingFunnelFormatBudgetConfig_target_rate": (
                kpi_target_rate if inject_kpi_pressure else 80
            ),
            "mediaMarketingFunnelFormatBudgetConfig_must_achieve": bool(
                inject_kpi_pressure and force_adformat_budget
            ),
            "module_priority_list": [
                "stage",
                "media",
                "kpiInfo",
                "marketingFunnel",
                "mediaMarketingFunnelFormat",
                "mediaMarketingFunnelFormatBudgetConfig",
            ],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="生成 Stage-Media 容差松弛触发样例 brief"
    )
    parser.add_argument(
        "--input-brief",
        type=Path,
        default=Path("brief_stage_media_stablility.json"),
        help="输入基准 brief 路径",
    )
    parser.add_argument(
        "--output-brief",
        type=Path,
        default=Path("output/xiaomi/requests_stage_media_stability_from_brief/brief_case_relaxation_trigger.json"),
        help="输出 brief 路径",
    )
    parser.add_argument(
        "--strict-range",
        type=int,
        default=5,
        help="严格容差（media_range_match）",
    )
    parser.add_argument(
        "--relax-cap",
        type=int,
        default=25,
        help="松弛上限（默认 25）",
    )
    parser.add_argument(
        "--bind-stage-marketing-funnel",
        action="store_true",
        default=False,
        help="给 stage 绑定 marketingFunnel（默认关闭，用于控制变量）",
    )
    parser.add_argument(
        "--isolate-stage-media-only",
        action="store_true",
        default=True,
        help="尽量隔离 marketingFunnel 约束，仅聚焦 stage/media（默认开启）",
    )
    parser.add_argument(
        "--no-isolate-stage-media-only",
        dest="isolate_stage_media_only",
        action="store_false",
        help="关闭 stage/media 隔离模式",
    )
    parser.add_argument(
        "--inject-kpi-pressure",
        action="store_true",
        default=True,
        help="注入 KPI 强约束（默认开启）",
    )
    parser.add_argument(
        "--no-inject-kpi-pressure",
        dest="inject_kpi_pressure",
        action="store_false",
        help="关闭 KPI 强约束注入",
    )
    parser.add_argument(
        "--kpi-target-rate",
        type=int,
        default=95,
        help="KPI 达成要求（默认 95）",
    )
    parser.add_argument(
        "--force-adformat-budget",
        action="store_true",
        default=True,
        help="注入 adformat 预算 must-achieve 约束（默认开启）",
    )
    parser.add_argument(
        "--no-force-adformat-budget",
        dest="force_adformat_budget",
        action="store_false",
        help="关闭 adformat 预算 must-achieve 约束注入",
    )
    parser.add_argument(
        "--derive-kpi-from-check",
        type=Path,
        default=None,
        help="从 achievement_check.json 反推 KPI 目标（基于实际值按倍率放大）",
    )
    parser.add_argument(
        "--global-kpi-multiplier",
        type=float,
        default=1.2,
        help="全局 KPI 放大倍率（默认 1.2）",
    )
    parser.add_argument(
        "--adformat-kpi-multiplier",
        type=float,
        default=1.15,
        help="adformat KPI 放大倍率（默认 1.15）",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = generate_case(
        input_brief=args.input_brief,
        output_brief=args.output_brief,
        strict_range=args.strict_range,
        relax_cap=args.relax_cap,
        bind_stage_marketing_funnel=args.bind_stage_marketing_funnel,
        isolate_stage_media_only=args.isolate_stage_media_only,
        inject_kpi_pressure=args.inject_kpi_pressure,
        kpi_target_rate=args.kpi_target_rate,
        force_adformat_budget=args.force_adformat_budget,
        derive_kpi_from_check=args.derive_kpi_from_check,
        global_kpi_multiplier=args.global_kpi_multiplier,
        adformat_kpi_multiplier=args.adformat_kpi_multiplier,
    )

    print("\n=== 造数完成 ===")
    print(f"输入: {result['input_brief']}")
    print(f"输出: {result['output_brief']}")
    print(
        f"关键差值 gap=|preheat({result['preheat_pct']}%)-ytb_target({result['ytb_target_pct']}%)|={result['gap']}%"
    )
    print(
        f"严格容差 {result['strict_range']}% -> {'预期失败' if result['strict_should_fail'] else '可能通过'}"
    )
    print(
        f"松弛上限 {result['relax_cap']}% -> {'预期可行' if result['relax_should_pass'] else '可能仍不可行'}"
    )
    print(
        f"Stage 绑定 MF: {result['bind_stage_marketing_funnel']} | 仅 stage/media 隔离模式: {result['isolate_stage_media_only']}"
    )
    print(
        f"KPI 压力注入: {result['inject_kpi_pressure']} | KPI达成要求: {result['kpi_target_rate']}% | adformat预算约束: {result['force_adformat_budget']}"
    )
    print(
        f"KPI 反推来源: {result['derive_kpi_from_check']} | 全局倍率: {result['global_kpi_multiplier']} | adformat倍率: {result['adformat_kpi_multiplier']}"
    )
    print("\n建议 testcase 片段：")
    print(json.dumps(result["suggested_testcase"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
