#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate boundary-case brief from final mp_result.
Only keeps the reverse-derive workflow:
1) read base brief + mp_result
2) optional backfill stage/funnel/media ratios from result
3) reverse-derive KPI targets to boundary or must-achieve
4) write new brief
"""

from __future__ import annotations

import argparse
import copy
import json
from collections import defaultdict
from pathlib import Path

KPI_KEYS = ["Impression", "Clicks", "VideoViews"]


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def _num(value) -> float:
    if isinstance(value, dict):
        value = value.get("value", 0)
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if text in {"", "-", "null", "None"}:
            return 0.0
        try:
            return float(text)
        except ValueError:
            return 0.0
    return 0.0


def _extract_dimension_rows(
    result_json: dict, check_dimension: str, country_code: str | None
) -> list[dict]:
    rows: list[dict] = []
    dimension = (
        result_json.get("data", {})
        .get("result", {})
        .get("dimensionMultiCountryResult", {})
    )
    for _, payload in dimension.items():
        for row in payload.get(check_dimension, []):
            media = str(row.get("media", "") or "")
            if "TTL" in media.upper():
                continue
            if country_code and str(row.get("country", "")).upper() != country_code.upper():
                continue
            rows.append(row)
    return rows


def _boundary_target_for_rate(actual: int, target_rate: int) -> tuple[int, int]:
    if actual <= 0:
        return 0, 0
    if target_rate <= 0 or target_rate > 100:
        return actual, 100
    # Use near-closed-form upper bound, then only search a small neighborhood.
    approx = max(1, int(actual * 100.0 / target_rate))
    window = 2000
    lower = max(1, approx - window)
    upper = approx + window

    exact: list[tuple[int, int]] = []
    passes: list[tuple[int, int]] = []
    for target in range(lower, upper + 1):
        achieved_rate = int(round(actual / target * 100))
        if achieved_rate == target_rate:
            exact.append((target, achieved_rate))
        if achieved_rate >= target_rate:
            passes.append((target, achieved_rate))

    if exact:
        return max(exact, key=lambda x: x[0])
    if passes:
        return max(passes, key=lambda x: x[0])

    target = max(1, approx)
    return target, int(round(actual / target * 100))


def _aggregate_rows(rows: list[dict]) -> dict:
    stage_amounts: dict[str, float] = defaultdict(float)
    funnel_amounts: dict[str, float] = defaultdict(float)
    media_amounts: dict[str, float] = defaultdict(float)
    child_amounts: dict[tuple[str, str], float] = defaultdict(float)
    global_kpi = {k: 0 for k in KPI_KEYS}
    adformat_kpi: dict[str, dict[str, int]] = defaultdict(lambda: {k: 0 for k in KPI_KEYS})

    for row in rows:
        budget = _num(row.get("totalBudget"))
        stage = str(row.get("stage", ""))
        funnel = str(row.get("marketingFunnel", ""))
        media = str(row.get("media", ""))
        channel = str(row.get("mediaChannel", ""))
        stage_amounts[stage] += budget
        funnel_amounts[funnel] += budget
        media_amounts[media] += budget
        child_amounts[(media, channel)] += budget

        imp = int(round(_num(row.get("estImpression"))))
        clk = int(round(_num(row.get("estClicks"))))
        vv = int(round(_num(row.get("estViews"))))
        global_kpi["Impression"] += imp
        global_kpi["Clicks"] += clk
        global_kpi["VideoViews"] += vv

        key = "|".join(
            [str(row.get("country", "")), media, channel, funnel, str(row.get("adFormat", ""))]
        )
        adformat_kpi[key]["Impression"] += imp
        adformat_kpi[key]["Clicks"] += clk
        adformat_kpi[key]["VideoViews"] += vv

    return {
        "stage_amounts": stage_amounts,
        "funnel_amounts": funnel_amounts,
        "media_amounts": media_amounts,
        "child_amounts": child_amounts,
        "global_kpi": global_kpi,
        "adformat_kpi": adformat_kpi,
    }


def _backfill_ratios(brief: dict, agg: dict) -> dict:
    total_budget = float(brief.get("basicInfo", {}).get("totalBudget", 0.0))
    if total_budget <= 0:
        return {"applied": False, "reason": "basicInfo.totalBudget invalid"}

    country_cfg = brief.get("briefMultiConfig", [{}])[0]
    updated = {"stage": 0, "funnel": 0, "media": 0, "media_child": 0}

    for item in country_cfg.get("stage", []):
        name = str(item.get("name", ""))
        amount = float(agg["stage_amounts"].get(name, 0))
        if amount > 0:
            item["budgetAmount"] = int(round(amount))
            item["budgetPercentage"] = round(amount / total_budget * 100, 2)
            updated["stage"] += 1

    for item in country_cfg.get("marketingFunnel", []):
        name = str(item.get("name", ""))
        amount = float(agg["funnel_amounts"].get(name, 0))
        if amount > 0:
            item["budgetAmount"] = int(round(amount))
            item["budgetPercentage"] = round(amount / total_budget * 100, 2)
            updated["funnel"] += 1

    for media in country_cfg.get("media", []):
        media_name = str(media.get("name", ""))
        amount = float(agg["media_amounts"].get(media_name, 0))
        if amount > 0:
            media["budgetAmount"] = int(round(amount))
            media["budgetPercentage"] = round(amount / total_budget * 100, 2)
            updated["media"] += 1

        for child in media.get("children", []):
            child_name = str(child.get("name", ""))
            key = (media_name, child_name)
            child_amount = float(agg["child_amounts"].get(key, 0))
            if child_amount > 0:
                child["budgetAmount"] = int(round(child_amount))
                child["budgetPercentage"] = round(child_amount / total_budget * 100, 2)
                updated["media_child"] += 1

    return {"applied": True, "updated": updated}


def _apply_kpi_boundary_targets(brief: dict, agg: dict, target_rate: int, must_achieve: bool) -> dict:
    basic_info = brief.get("basicInfo", {})
    global_actual = agg["global_kpi"]
    global_meta = {}

    basic_info["kpiInfo"] = []
    for idx, key in enumerate(KPI_KEYS, 1):
        actual = int(global_actual.get(key, 0))
        if must_achieve:
            target, achieved_rate = actual, (100 if actual > 0 else 0)
            completion = 1 if actual > 0 else 0
        else:
            target, achieved_rate = _boundary_target_for_rate(actual, target_rate)
            completion = 0
        basic_info["kpiInfo"].append(
            {"key": key, "val": str(target), "priority": idx, "completion": completion}
        )
        global_meta[key] = {"actual": actual, "target": target, "achieved_rate": achieved_rate}

    basic_info["kpiInfoBudgetConfig"] = {"rangeMatch": target_rate}

    country_cfg = brief.get("briefMultiConfig", [{}])[0]
    country_code = (
        country_cfg.get("countryInfo", {}).get("countryCode")
        or country_cfg.get("country", {}).get("code")
        or ""
    )
    adformat_actual = agg["adformat_kpi"]
    adformat_count = 0

    for mmff in country_cfg.get("mediaMarketingFunnelFormat", []):
        media_name = str(mmff.get("mediaName", ""))
        platform = str((mmff.get("platform") or [""])[0])
        for adf in mmff.get("adFormatWithKPI", []):
            funnel = str(adf.get("funnelName", ""))
            adformat = str(adf.get("adFormatName", ""))
            key = "|".join([country_code, media_name, platform, funnel, adformat])
            actual_map = adformat_actual.get(key, {k: 0 for k in KPI_KEYS})
            for kpi in adf.get("kpiInfo", []):
                key_name = kpi.get("key")
                if key_name not in KPI_KEYS:
                    continue
                actual = int(actual_map.get(key_name, 0))
                if must_achieve:
                    target, _ = actual, (100 if actual > 0 else 0)
                    completion = 1 if actual > 0 else 0
                else:
                    target, _ = _boundary_target_for_rate(actual, target_rate)
                    completion = 0
                kpi["val"] = str(target)
                kpi["completion"] = completion
            adf["completion"] = 1 if must_achieve else 0
            adformat_count += 1

    mmff_cfg = country_cfg.setdefault("mediaMarketingFunnelFormatBudgetConfig", {})
    mmff_cfg["kpiFlexibility"] = target_rate
    mmff_cfg["totalBudgetFlexibility"] = target_rate

    return {
        "target_rate": target_rate,
        "must_achieve": must_achieve,
        "global_preview": global_meta,
        "adformat_count": adformat_count,
    }


def build_boundary_case(
    input_brief: Path,
    result_file: Path,
    output_brief: Path,
    target_rate: int,
    must_achieve: bool,
    country_code: str | None,
    backfill_ratios: bool,
    check_dimension: str,
) -> dict:
    brief = copy.deepcopy(_load_json(input_brief))
    result_json = _load_json(result_file)
    rows = _extract_dimension_rows(
        result_json, check_dimension=check_dimension, country_code=country_code
    )
    if not rows:
        raise ValueError(f"No usable {check_dimension} rows found in result")

    agg = _aggregate_rows(rows)
    ratio_info = {"applied": False, "reason": "disabled"}
    if backfill_ratios:
        ratio_info = _backfill_ratios(brief, agg)
    kpi_info = _apply_kpi_boundary_targets(brief, agg, target_rate, must_achieve)

    _save_json(output_brief, brief)
    return {
        "input_brief": str(input_brief),
        "result_file": str(result_file),
        "output_brief": str(output_brief),
        "check_dimension": check_dimension,
        "country_code": country_code,
        "row_count": len(rows),
        "ratio_info": ratio_info,
        "kpi_info": kpi_info,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simplified: reverse-derive boundary brief from final result"
    )
    parser.add_argument(
        "--input-brief",
        type=Path,
        default=Path("brief_stage_media_stablility.json"),
        help="Base brief path",
    )
    parser.add_argument(
        "--result-file",
        type=Path,
        required=True,
        help="Final mp_result json path",
    )
    parser.add_argument(
        "--output-brief",
        type=Path,
        default=Path("output/xiaomi/requests_stage_media_stability_from_brief/brief_case_boundary_from_result.json"),
        help="Output brief path",
    )
    parser.add_argument(
        "--kpi-target-rate",
        type=int,
        default=95,
        help="Target rate for boundary reverse derivation",
    )
    parser.add_argument(
        "--kpi-must-achieve",
        action="store_true",
        default=False,
        help="Use must-achieve mode (target=actual)",
    )
    parser.add_argument(
        "--check-dimension",
        type=str,
        choices=["corporation", "category", "ai"],
        default="corporation",
        help="Use which dimension under dimensionMultiCountryResult",
    )
    parser.add_argument(
        "--country-code",
        type=str,
        default=None,
        help="Country filter, e.g. SG",
    )
    parser.add_argument(
        "--no-backfill-ratios",
        dest="backfill_ratios",
        action="store_false",
        help="Do not backfill stage/funnel/media ratios",
    )
    parser.set_defaults(backfill_ratios=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_boundary_case(
        input_brief=args.input_brief,
        result_file=args.result_file,
        output_brief=args.output_brief,
        target_rate=args.kpi_target_rate,
        must_achieve=args.kpi_must_achieve,
        country_code=args.country_code,
        backfill_ratios=args.backfill_ratios,
        check_dimension=args.check_dimension,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
