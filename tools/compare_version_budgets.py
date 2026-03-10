#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本变化对比：对比两个算法版本下各用例、各维度的预算差异，输出报告并标出差异较大的项。

使用方式：
    python tools/compare_version_budgets.py --version-a latest --version-b 20250226_v2
    python tools/compare_version_budgets.py --variant common --version-a latest --version-b v2 --output report.html
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config.version_config import (
    resolve_results_dir,
)


def parse_budget(val: Any) -> float:
    """解析预算为浮点数"""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        if not val or val == "-":
            return 0.0
        val = val.replace("%", "").replace(",", "").strip()
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def extract_ai_data(result_json: Dict, variant: str) -> List[Dict]:
    """从结果 JSON 提取 AI 维度数据列表（common 与 xiaomi 字段略有不同）"""
    data = result_json.get("data", {})
    result = data.get("result", {})
    dimension_result = result.get("dimensionMultiCountryResult", {})

    ai_data_list = []
    budget_key = "totalBudget" if variant == "xiaomi" else "adTypeBudget"

    for region_key, region_data in dimension_result.items():
        ai_list = region_data.get("corporation", [])
        for ai_item in ai_list:
            if variant == "xiaomi":
                if ai_item.get("media") and "TTL" in str(ai_item.get("media", "")):
                    continue
            ai_item["_region_key"] = region_key
            ai_item["_budget_key"] = budget_key
            ai_data_list.append(ai_item)

    return ai_data_list


def _country_from_item(ai_item: Dict, variant: str) -> str:
    if variant == "xiaomi":
        return str(ai_item.get("country") or "").strip()
    region = str(ai_item.get("region") or "").strip()
    return region.split("_")[0] if "_" in region else region


def aggregate_budgets_by_dimension(
    ai_data_list: List[Dict], variant: str
) -> Dict[str, Any]:
    """
    按维度聚合预算：总预算、区域、阶段、营销漏斗、媒体|平台、Adtype(媒体|平台|adtype)。
    返回结构便于与另一版本逐维度对比。
    """
    total = 0.0
    by_region: Dict[str, float] = {}
    by_stage: Dict[str, float] = {}  # key: country|stage
    by_funnel: Dict[str, float] = {}  # key: country|funnel
    by_media: Dict[str, float] = {}   # key: country|media|platform
    by_adtype: Dict[str, float] = {} # key: country|media|platform|adtype

    budget_key = "_budget_key"
    for ai_item in ai_data_list:
        key_name = ai_item.get(budget_key, "adTypeBudget")
        if key_name == "totalBudget":
            b = parse_budget(ai_item.get("totalBudget", 0))
        else:
            b = parse_budget(ai_item.get("adTypeBudget", "0"))

        country = _country_from_item(ai_item, variant)
        stage = str(ai_item.get("stage") or "").strip()
        funnel = str(ai_item.get("marketingFunnel") or "").strip()
        media = str(ai_item.get("media") or "").strip()
        platform = str(ai_item.get("mediaChannel") or "").strip()
        adtype = str(ai_item.get("adType") or "").strip()

        total += b
        if country:
            by_region[country] = by_region.get(country, 0.0) + b
        if country and stage:
            by_stage[f"{country}|{stage}"] = by_stage.get(f"{country}|{stage}", 0.0) + b
        if country and funnel:
            by_funnel[f"{country}|{funnel}"] = by_funnel.get(f"{country}|{funnel}", 0.0) + b
        if country and media and platform:
            by_media[f"{country}|{media}|{platform}"] = by_media.get(f"{country}|{media}|{platform}", 0.0) + b
        if country and media and platform and adtype:
            by_adtype[f"{country}|{media}|{platform}|{adtype}"] = by_adtype.get(
                f"{country}|{media}|{platform}|{adtype}", 0.0
            ) + b

    return {
        "total": total,
        "by_region": by_region,
        "by_stage": by_stage,
        "by_funnel": by_funnel,
        "by_media": by_media,
        "by_adtype": by_adtype,
    }


def compare_aggregates(
    agg_a: Dict[str, Any],
    agg_b: Dict[str, Any],
    total_a: float,
    total_b: float,
    pct_threshold: float = 10.0,
    amount_pct_of_total_threshold: float = 5.0,
) -> Tuple[Dict[str, List[Dict]], List[Dict]]:
    """
    对比两个聚合结果，返回各维度对比行 + 差异较大的告警列表。
    - pct_threshold: 相对变化百分比超过此值标为差异大（基于较小值算 pct）
    - amount_pct_of_total_threshold: 绝对差异占两版总预算较大者的百分比超过此值也可标为差异大
    """
    ref_total = max(total_a, total_b) or 1.0
    dimension_tables: Dict[str, List[Dict]] = {}
    warnings: List[Dict] = []

    def _add_warning(dimension: str, key: str, budget_a: float, budget_b: float, diff: float, diff_pct: Optional[float], case_name: str = ""):
        w = {
            "dimension": dimension,
            "key": key,
            "budget_a": budget_a,
            "budget_b": budget_b,
            "diff": diff,
            "diff_pct": diff_pct,
            "case_name": case_name,
        }
        warnings.append(w)

    def _compare_dimension(
        dim_name: str,
        dict_a: Dict[str, float],
        dict_b: Dict[str, float],
    ) -> List[Dict]:
        all_keys = sorted(set(dict_a.keys()) | set(dict_b.keys()))
        rows = []
        for k in all_keys:
            va = dict_a.get(k, 0.0)
            vb = dict_b.get(k, 0.0)
            diff = vb - va
            if va != 0:
                diff_pct = (diff / va) * 100.0
            elif vb != 0:
                diff_pct = 100.0
            else:
                diff_pct = 0.0

            is_large = False
            if abs(diff_pct) > pct_threshold:
                is_large = True
            if ref_total > 0 and (abs(diff) / ref_total * 100.0) > amount_pct_of_total_threshold:
                is_large = True

            rows.append({
                "key": k,
                "budget_a": round(va, 2),
                "budget_b": round(vb, 2),
                "diff": round(diff, 2),
                "diff_pct": round(diff_pct, 2) if diff_pct is not None else None,
                "is_large": is_large,
            })
            if is_large:
                _add_warning(dim_name, k, va, vb, diff, round(diff_pct, 2) if va != 0 else None)
        return rows

    # 总预算单独一行
    total_diff = total_b - total_a
    total_diff_pct = (total_diff / total_a * 100.0) if total_a else (100.0 if total_b else 0.0)
    dimension_tables["total"] = [{
        "key": "总预算",
        "budget_a": round(total_a, 2),
        "budget_b": round(total_b, 2),
        "diff": round(total_diff, 2),
        "diff_pct": round(total_diff_pct, 2),
        "is_large": abs(total_diff_pct) > pct_threshold or (abs(total_diff) / ref_total * 100.0) > amount_pct_of_total_threshold,
    }]
    if dimension_tables["total"][0]["is_large"]:
        _add_warning("总预算", "总预算", total_a, total_b, total_diff, round(total_diff_pct, 2))

    dimension_tables["region"] = _compare_dimension("区域", agg_a["by_region"], agg_b["by_region"])
    dimension_tables["stage"] = _compare_dimension("阶段", agg_a["by_stage"], agg_b["by_stage"])
    dimension_tables["funnel"] = _compare_dimension("营销漏斗", agg_a["by_funnel"], agg_b["by_funnel"])
    dimension_tables["media"] = _compare_dimension("媒体|平台", agg_a["by_media"], agg_b["by_media"])
    dimension_tables["adtype"] = _compare_dimension("Adtype", agg_a["by_adtype"], agg_b["by_adtype"])

    return dimension_tables, warnings


def run_comparison(
    results_dir_a: Path,
    results_dir_b: Path,
    variant: str,
    pct_threshold: float = 10.0,
    amount_pct_threshold: float = 5.0,
) -> Dict[str, Any]:
    """对比两个结果目录下同名的 mp_result_*.json，返回结构化对比数据。"""
    prefix = "mp_result_"
    files_a = {f.stem.replace(prefix, ""): f for f in results_dir_a.glob("mp_result_*.json")}
    files_b = {f.stem.replace(prefix, ""): f for f in results_dir_b.glob("mp_result_*.json")}
    common_cases = sorted(set(files_a.keys()) & set(files_b.keys()))

    if not common_cases:
        return {
            "version_a": str(results_dir_a),
            "version_b": str(results_dir_b),
            "common_cases": [],
            "case_comparisons": [],
            "summary": {"total_cases": 0, "cases_with_large_diff": 0},
        }

    case_comparisons = []
    cases_with_large_diff = 0

    for case_name in common_cases:
        path_a = files_a[case_name]
        path_b = files_b[case_name]
        try:
            with path_a.open("r", encoding="utf-8") as f:
                json_a = json.load(f)
            with path_b.open("r", encoding="utf-8") as f:
                json_b = json.load(f)
        except Exception as e:
            case_comparisons.append({
                "case_name": case_name,
                "error": str(e),
                "dimension_tables": {},
                "warnings": [],
            })
            continue

        ai_a = extract_ai_data(json_a, variant)
        ai_b = extract_ai_data(json_b, variant)
        agg_a = aggregate_budgets_by_dimension(ai_a, variant)
        agg_b = aggregate_budgets_by_dimension(ai_b, variant)

        dimension_tables, warnings = compare_aggregates(
            agg_a, agg_b,
            agg_a["total"], agg_b["total"],
            pct_threshold=pct_threshold,
            amount_pct_of_total_threshold=amount_pct_threshold,
        )

        for w in warnings:
            w["case_name"] = case_name

        if warnings:
            cases_with_large_diff += 1

        case_comparisons.append({
            "case_name": case_name,
            "dimension_tables": dimension_tables,
            "warnings": warnings,
            "total_a": round(agg_a["total"], 2),
            "total_b": round(agg_b["total"], 2),
        })

    return {
        "version_a": str(results_dir_a),
        "version_b": str(results_dir_b),
        "common_cases": common_cases,
        "case_comparisons": case_comparisons,
        "summary": {
            "total_cases": len(common_cases),
            "cases_with_large_diff": cases_with_large_diff,
        },
        "pct_threshold": pct_threshold,
        "amount_pct_threshold": amount_pct_threshold,
    }


def render_html_report(comparison: Dict[str, Any], version_a_label: str, version_b_label: str) -> str:
    """生成 HTML 报告：差异较大提示 + 各维度预算对比表。"""
    summary = comparison.get("summary", {})
    case_comparisons = comparison.get("case_comparisons", [])
    pct_threshold = comparison.get("pct_threshold", 10.0)
    amount_threshold = comparison.get("amount_pct_threshold", 5.0)

    all_warnings: List[Dict] = []
    for c in case_comparisons:
        for w in c.get("warnings", []):
            w["case_name"] = c.get("case_name", "")
            all_warnings.append(w)

    html_parts = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'><title>版本预算对比报告</title>",
        "<style>",
        "body { font-family: 'Segoe UI', sans-serif; margin: 20px; background: #f5f5f5; }",
        "h1 { color: #1a1a2e; }",
        "h2 { color: #16213e; margin-top: 24px; }",
        "table { border-collapse: collapse; width: 100%; max-width: 900px; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }",
        "th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }",
        "th { background: #16213e; color: #fff; }",
        "tr:nth-child(even) { background: #f9f9f9; }",
        ".warn { background: #fff3cd !important; }",
        ".warn strong { color: #856404; }",
        ".alert-box { background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 6px; padding: 12px 16px; margin: 16px 0; max-width: 900px; }",
        ".alert-box h3 { color: #721c24; margin-top: 0; }",
        ".summary { background: #e7f3ff; border: 1px solid #b8daff; border-radius: 6px; padding: 12px 16px; margin: 16px 0; max-width: 900px; }",
        "</style></head><body>",
        f"<h1>版本预算对比报告</h1>",
        f"<div class='summary'><strong>版本 A</strong>: {version_a_label} &nbsp;|&nbsp; <strong>版本 B</strong>: {version_b_label} &nbsp;|&nbsp; "
        f"共对比 <strong>{summary.get('total_cases', 0)}</strong> 个用例，"
        f"其中 <strong>{summary.get('cases_with_large_diff', 0)}</strong> 个用例存在差异较大项（相对变化 &gt;{pct_threshold}% 或 绝对差异占总量 &gt;{amount_threshold}%）</div>",
    ]

    if all_warnings:
        html_parts.append("<div class='alert-box'>")
        html_parts.append("<h3>⚠ 差异较大需关注</h3>")
        html_parts.append("<p>以下维度预算在版本间变化超过阈值，请重点核对：</p>")
        html_parts.append("<table><thead><tr><th>用例</th><th>维度</th><th>项</th><th>版本 A</th><th>版本 B</th><th>差异</th><th>变化%</th></tr></thead><tbody>")
        for w in all_warnings[:200]:  # 最多展示 200 条
            diff_pct_str = f"{w.get('diff_pct')}%" if w.get("diff_pct") is not None else "-"
            html_parts.append(
                f"<tr><td>{w.get('case_name', '')}</td><td>{w.get('dimension', '')}</td><td>{w.get('key', '')}</td>"
                f"<td>{w.get('budget_a', 0)}</td><td>{w.get('budget_b', 0)}</td><td>{w.get('diff', 0)}</td><td>{diff_pct_str}</td></tr>"
            )
        html_parts.append("</tbody></table></div>")

    for comp in case_comparisons:
        case_name = comp.get("case_name", "")
        if comp.get("error"):
            html_parts.append(f"<h2>{case_name}</h2><p>加载失败: {comp['error']}</p>")
            continue

        html_parts.append(f"<h2>用例: {case_name}</h2>")
        html_parts.append(f"<p>总预算 版本 A: {comp.get('total_a', 0)} &nbsp; 版本 B: {comp.get('total_b', 0)}</p>")

        dim_names = {
            "total": "总预算",
            "region": "区域",
            "stage": "阶段",
            "funnel": "营销漏斗",
            "media": "媒体|平台",
            "adtype": "Adtype",
        }
        for dim_key, dim_title in dim_names.items():
            tables = comp.get("dimension_tables", {}).get(dim_key, [])
            if not tables:
                continue
            html_parts.append(f"<h3>{dim_title}</h3>")
            html_parts.append("<table><thead><tr><th>项</th><th>版本 A</th><th>版本 B</th><th>差异</th><th>变化%</th><th>备注</th></tr></thead><tbody>")
            for row in tables:
                cls = " class='warn'" if row.get("is_large") else ""
                diff_pct = row.get("diff_pct")
                diff_pct_str = f"{diff_pct}%" if diff_pct is not None else "-"
                remark = "⚠ 差异较大" if row.get("is_large") else ""
                html_parts.append(
                    f"<tr{cls}><td>{row.get('key', '')}</td><td>{row.get('budget_a', 0)}</td><td>{row.get('budget_b', 0)}</td>"
                    f"<td>{row.get('diff', 0)}</td><td>{diff_pct_str}</td><td>{remark}</td></tr>"
                )
            html_parts.append("</tbody></table>")

    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def main():
    parser = argparse.ArgumentParser(
        description="对比两个算法版本下各用例、各维度的预算差异，输出报告并标出差异较大的项"
    )
    parser.add_argument(
        "--variant",
        type=str,
        choices=["common", "xiaomi"],
        default="common",
        help="结果目录对应版本（common 或 xiaomi）",
    )
    parser.add_argument(
        "--version-a",
        type=str,
        required=True,
        help="版本 A 的 algo_version（如 latest、20250226_baseline）",
    )
    parser.add_argument(
        "--version-b",
        type=str,
        required=True,
        help="版本 B 的 algo_version（如 20250226_v2）",
    )
    parser.add_argument(
        "--pct-threshold",
        type=float,
        default=10.0,
        help="相对变化百分比超过此值标为差异大（默认 10）",
    )
    parser.add_argument(
        "--amount-pct-threshold",
        type=float,
        default=5.0,
        help="绝对差异占总量百分比超过此值标为差异大（默认 5）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="报告输出路径（HTML）。不指定则输出到 output/<variant>/achievement_checks/reports/version_compare_<version_a>_vs_<version_b>.html",
    )
    parser.add_argument(
        "--json-output",
        type=str,
        default=None,
        help="可选：将对比数据同时输出为 JSON 文件",
    )
    args = parser.parse_args()

    results_dir_a = resolve_results_dir(project_root, args.variant, args.version_a)
    results_dir_b = resolve_results_dir(project_root, args.variant, args.version_b)

    if not results_dir_a.exists():
        print(f"错误：版本 A 结果目录不存在: {results_dir_a}")
        sys.exit(1)
    if not results_dir_b.exists():
        print(f"错误：版本 B 结果目录不存在: {results_dir_b}")
        sys.exit(1)

    print(f"对比 版本 A: {args.version_a}  版本 B: {args.version_b}  (variant={args.variant})")
    comparison = run_comparison(
        results_dir_a,
        results_dir_b,
        args.variant,
        pct_threshold=args.pct_threshold,
        amount_pct_threshold=args.amount_pct_threshold,
    )

    summary = comparison.get("summary", {})
    print(f"共 {summary.get('total_cases', 0)} 个用例参与对比，{summary.get('cases_with_large_diff', 0)} 个用例存在差异较大项。")

    html = render_html_report(comparison, args.version_a, args.version_b)

    if args.output:
        out_path = Path(args.output)
    else:
        reports_dir = project_root / "output" / args.variant / "achievement_checks" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        out_path = reports_dir / f"version_compare_{args.version_a}_vs_{args.version_b}.html"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        f.write(html)
    print(f"报告已保存: {out_path}")

    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(comparison, f, ensure_ascii=False, indent=2)
        print(f"JSON 数据已保存: {json_path}")


if __name__ == "__main__":
    main()
