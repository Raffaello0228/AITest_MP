#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate an infeasible Xiaomi brief by media-capacity upper bound.

Idea:
1) Force media split (e.g. Meta 50%, Google 50%)
2) Assume Google-GG can achieve minimum CPM (e.g. 0.6), compute max GG impression
3) Assume Meta impression capacity by chosen CPM model (history/best/fixed)
4) Set global Impression KPI to (max_total_impression * (1 + uplift))
   so the target is intentionally beyond the theoretical upper bound.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd


def _clean_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.replace("$", "", regex=False).str.strip(),
        errors="coerce",
    ).fillna(0.0)


def _load_csv_metrics(csv_path: Path) -> dict:
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().replace("\n", " ").replace("\r", "") for c in df.columns]
    if "Country" in df.columns:
        df["Country"] = df["Country"].ffill()

    for col in ["Budget", "Estimated Impressions", "Estimated CPM"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = _clean_number(df[col])

    total_budget = float(df["Budget"].sum())
    total_impression = float(df["Estimated Impressions"].sum())

    meta_df = df[df["Media"].astype(str).str.strip() == "Meta"].copy()
    meta_budget = float(meta_df["Budget"].sum())
    meta_imp = float(meta_df["Estimated Impressions"].sum())
    meta_hist_cpm = (meta_budget / meta_imp * 1000.0) if meta_imp > 0 else None

    meta_cpm_candidates = meta_df["Estimated CPM"]
    meta_cpm_candidates = meta_cpm_candidates[meta_cpm_candidates > 0]
    meta_best_cpm = float(meta_cpm_candidates.min()) if not meta_cpm_candidates.empty else None

    return {
        "total_budget": total_budget,
        "total_impression": total_impression,
        "meta_hist_cpm": meta_hist_cpm,
        "meta_best_cpm": meta_best_cpm,
    }


def _pick_meta_cpm(metrics: dict, mode: str, fixed_cpm: float) -> float:
    if mode == "fixed":
        if fixed_cpm <= 0:
            raise ValueError("--meta-fixed-cpm 必须大于 0")
        return fixed_cpm
    if mode == "best":
        if metrics["meta_best_cpm"] is not None:
            return metrics["meta_best_cpm"]
        if metrics["meta_hist_cpm"] is not None:
            return metrics["meta_hist_cpm"]
        raise ValueError("无法从 CSV 推导 Meta CPM，请改用 --meta-cpm-mode fixed")
    if metrics["meta_hist_cpm"] is not None:
        return metrics["meta_hist_cpm"]
    if metrics["meta_best_cpm"] is not None:
        return metrics["meta_best_cpm"]
    raise ValueError("无法从 CSV 推导 Meta CPM，请改用 --meta-cpm-mode fixed")


def _set_media_split(brief: dict, total_budget: float, meta_ratio: float, ytb_floor_ratio: float) -> None:
    google_ratio = 100.0 - meta_ratio
    gg_ratio = max(0.0, google_ratio - ytb_floor_ratio)

    country_cfg = brief.get("briefMultiConfig", [{}])[0]
    for media in country_cfg.get("media", []):
        media_name = str(media.get("name", "")).strip()
        if media_name == "Meta":
            media["budgetPercentage"] = round(meta_ratio, 2)
            media["budgetAmount"] = int(round(total_budget * meta_ratio / 100.0))
            for child in media.get("children", []):
                child["budgetPercentage"] = round(meta_ratio, 2)
                child["budgetAmount"] = int(round(total_budget * meta_ratio / 100.0))
        elif media_name == "Google":
            media["budgetPercentage"] = round(google_ratio, 2)
            media["budgetAmount"] = int(round(total_budget * google_ratio / 100.0))
            for child in media.get("children", []):
                child_name = str(child.get("name", "")).strip()
                if child_name == "GG":
                    child["budgetPercentage"] = round(gg_ratio, 2)
                    child["budgetAmount"] = int(round(total_budget * gg_ratio / 100.0))
                elif child_name == "YTB":
                    child["budgetPercentage"] = round(ytb_floor_ratio, 2)
                    child["budgetAmount"] = int(round(total_budget * ytb_floor_ratio / 100.0))


def _set_impression_kpi_infeasible(brief: dict, impossible_target: int, keep_other_kpis: bool) -> None:
    basic_info = brief.setdefault("basicInfo", {})
    kpis = basic_info.get("kpiInfo", [])

    impression_found = False
    for kpi in kpis:
        if str(kpi.get("key", "")) == "Impression":
            kpi["val"] = str(impossible_target)
            kpi["completion"] = 1
            impression_found = True
        elif not keep_other_kpis:
            kpi["val"] = "0"
            kpi["completion"] = 0

    if not impression_found:
        kpis.insert(
            0,
            {
                "key": "Impression",
                "val": str(impossible_target),
                "priority": 1,
                "completion": 1,
            },
        )
    basic_info["kpiInfo"] = kpis


def _set_history_mp_flags(brief: dict, is_history_mp: int, history_mp_id: str) -> None:
    basic_info = brief.setdefault("basicInfo", {})
    basic_info["isHistoryMp"] = int(is_history_mp)
    if history_mp_id:
        basic_info["historyMpId"] = history_mp_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate media-infeasible Xiaomi boundary brief")
    parser.add_argument("--csv-path", type=Path, default=Path("xiaomi_v2.csv"))
    parser.add_argument(
        "--input-brief",
        type=Path,
        default=Path("output/xiaomi/requests_stage_media_stability_from_brief/brief_case_xiaomi_v2_baseline.json"),
    )
    parser.add_argument(
        "--output-brief",
        type=Path,
        default=Path("output/xiaomi/requests_xiaomi_v2_boundary/brief_case_xiaomi_v2_media_infeasible.json"),
    )
    parser.add_argument("--meta-ratio", type=float, default=50.0, help="Meta media ratio (%)")
    parser.add_argument("--gg-min-cpm", type=float, default=0.6, help="Best-case GG CPM")
    parser.add_argument("--kpi-uplift", type=float, default=0.10, help="Raise upper bound by this ratio")
    parser.add_argument(
        "--meta-cpm-mode",
        choices=["history", "best", "fixed"],
        default="history",
        help="How to estimate Meta CPM for max-impression bound",
    )
    parser.add_argument("--meta-fixed-cpm", type=float, default=1.2)
    parser.add_argument("--ytb-floor-ratio", type=float, default=0.0, help="Reserve YTB ratio under Google")
    parser.add_argument(
        "--keep-other-kpis",
        action="store_true",
        default=True,
        help="Keep non-Impression KPI targets as-is",
    )
    parser.add_argument(
        "--is-history-mp",
        type=int,
        choices=[0, 1],
        default=1,
        help="Set basicInfo.isHistoryMp (default 1)",
    )
    parser.add_argument(
        "--history-mp-id",
        type=str,
        default="0f25ac3c-d0e6-4340-995b-c795e766",
        help="Set basicInfo.historyMpId to reuse uploaded CPM context",
    )
    args = parser.parse_args()

    if args.meta_ratio <= 0 or args.meta_ratio >= 100:
        raise ValueError("--meta-ratio 必须在 (0,100) 区间")
    if args.gg_min_cpm <= 0:
        raise ValueError("--gg-min-cpm 必须大于 0")
    if args.kpi_uplift <= 0:
        raise ValueError("--kpi-uplift 必须大于 0")

    metrics = _load_csv_metrics(args.csv_path)
    total_budget = metrics["total_budget"]
    meta_budget = total_budget * args.meta_ratio / 100.0
    gg_budget = total_budget - meta_budget

    meta_cpm = _pick_meta_cpm(metrics, args.meta_cpm_mode, args.meta_fixed_cpm)
    imp_meta_max = (meta_budget / meta_cpm) * 1000.0
    imp_gg_max = (gg_budget / args.gg_min_cpm) * 1000.0
    imp_total_max = imp_meta_max + imp_gg_max
    impossible_target = int(math.ceil(imp_total_max * (1.0 + args.kpi_uplift)))

    brief = json.loads(args.input_brief.read_text(encoding="utf-8"))
    _set_media_split(brief, total_budget, args.meta_ratio, args.ytb_floor_ratio)
    _set_impression_kpi_infeasible(brief, impossible_target, args.keep_other_kpis)
    _set_history_mp_flags(brief, args.is_history_mp, args.history_mp_id)
    args.output_brief.parent.mkdir(parents=True, exist_ok=True)
    args.output_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "csv_path": str(args.csv_path),
        "input_brief": str(args.input_brief),
        "output_brief": str(args.output_brief),
        "total_budget": round(total_budget, 2),
        "meta_ratio": args.meta_ratio,
        "gg_ratio": round(100.0 - args.meta_ratio, 2),
        "meta_cpm_assumed": round(meta_cpm, 4),
        "gg_min_cpm": args.gg_min_cpm,
        "impression_upper_bound": int(round(imp_total_max)),
        "kpi_uplift": args.kpi_uplift,
        "impression_target_set": impossible_target,
        "baseline_total_impression_csv": int(round(metrics["total_impression"])),
        "isHistoryMp": args.is_history_mp,
        "historyMpId": args.history_mp_id,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

