#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汇总所有测试结果 - 将所有 achievement_check.json 文件的结果汇总到一张表中
"""

import json
import argparse
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


def load_json(filepath: Path) -> Any:
    """加载JSON文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_dimension_summary(results: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """计算各维度达成情况汇总（与 generate_test_report.py 中的逻辑一致）"""
    dimensions = {
        "global_kpi": "全局 KPI",
        "region_budget": "区域预算",
        "region_kpi": "区域 KPI",
        "stage_budget": "阶段预算",
        "marketingfunnel_budget": "营销漏斗预算",
        "media_budget": "媒体预算",
        "adtype_kpi": "广告类型 KPI",
        "adtype_budget_allocation": "Adtype 预算分配",
    }

    summary = {}

    for dim_key, dim_name in dimensions.items():
        if dim_key not in results:
            continue

        dim_data = results[dim_key]

        if dim_key == "region_kpi":
            # 区域 KPI 需要特殊处理
            total_achieved = 0
            total_count = 0
            for country_kpis in dim_data.values():
                for kpi_data in country_kpis.values():
                    total_count += 1
                    if kpi_data.get("achieved", False):
                        total_achieved += 1
            achieved_str = f"{total_achieved}/{total_count}"
            rate = (total_achieved / total_count * 100) if total_count > 0 else 0
        elif dim_key == "adtype_kpi":
            total_achieved = 0
            total_count = 0
            for adtype_data in dim_data.values():
                kpis = adtype_data.get("kpis", {})
                for kpi_data in kpis.values():
                    total_count += 1
                    if kpi_data.get("achieved", False):
                        total_achieved += 1
            achieved_str = f"{total_achieved}/{total_count}"
            rate = (total_achieved / total_count * 100) if total_count > 0 else 0
        elif dim_key in [
            "stage_budget",
            "marketingfunnel_budget",
            "media_budget",
            "adtype_budget_allocation",
        ]:
            # 这些维度需要统计所有区域下的所有项目
            total_satisfied = 0
            total_count = 0
            for country_items in dim_data.values():
                for item_data in country_items.values():
                    total_count += 1
                    if item_data.get("satisfied", False):
                        total_satisfied += 1
            achieved_str = f"{total_satisfied}/{total_count}"
            rate = (total_satisfied / total_count * 100) if total_count > 0 else 0
        else:
            # 其他维度（global_kpi, region_budget）
            achieved_count = sum(
                1
                for v in dim_data.values()
                if v.get("achieved", False) or v.get("satisfied", False)
            )
            total_count = len(dim_data)
            achieved_str = f"{achieved_count}/{total_count}"
            rate = (achieved_count / total_count * 100) if total_count > 0 else 0

        summary[dim_key] = {
            "name": dim_name,
            "achieved": achieved_str,
            "rate": rate,
        }

    return summary


def calculate_total_kpi_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    """计算总 KPI 达成情况（所有维度的汇总）"""
    all_achieved = 0
    all_total = 0

    # 全局 KPI
    if "global_kpi" in results:
        for kpi_data in results["global_kpi"].values():
            all_total += 1
            if kpi_data.get("achieved", False):
                all_achieved += 1

    # 区域 KPI
    if "region_kpi" in results:
        for country_kpis in results["region_kpi"].values():
            for kpi_data in country_kpis.values():
                all_total += 1
                if kpi_data.get("achieved", False):
                    all_achieved += 1

    # 广告类型 KPI
    if "adtype_kpi" in results:
        for adtype_data in results["adtype_kpi"].values():
            kpis = adtype_data.get("kpis", {})
            for kpi_data in kpis.values():
                all_total += 1
                if kpi_data.get("achieved", False):
                    all_achieved += 1

    rate = (all_achieved / all_total * 100) if all_total > 0 else 0
    return {
        "achieved": f"{all_achieved}/{all_total}",
        "rate": rate,
    }


def generate_summary_table(all_results: List[Dict[str, Any]]) -> str:
    """生成汇总表格"""
    # 定义维度顺序
    dimension_keys = [
        "global_kpi",
        "region_budget",
        "region_kpi",
        "stage_budget",
        "marketingfunnel_budget",
        "media_budget",
        "adtype_kpi",
        "adtype_budget_allocation",
    ]

    # 构建表头
    header = ["测试用例"]
    for dim_key in dimension_keys:
        # 从第一个结果中获取维度名称
        if all_results and dim_key in all_results[0]["summary"]:
            header.append(all_results[0]["summary"][dim_key]["name"])
    header.append("总 KPI 达成率")

    # 构建表格行
    lines = []
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    for result in all_results:
        case_name = result["case_name"]
        summary = result["summary"]
        total_kpi = result["total_kpi"]

        row = [case_name]
        for dim_key in dimension_keys:
            if dim_key in summary:
                dim_info = summary[dim_key]
                row.append(f"{dim_info['achieved']} ({dim_info['rate']:.1f}%)")
            else:
                row.append("-")

        # 添加总 KPI 达成率
        row.append(f"{total_kpi['achieved']} ({total_kpi['rate']:.1f}%)")

        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def generate_markdown_report(all_results: List[Dict[str, Any]], output_path: Path):
    """生成 Markdown 格式的汇总报告"""
    report_lines = []
    report_lines.append("# 测试结果汇总报告\n")
    report_lines.append(
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    report_lines.append(f"**测试用例数量**: {len(all_results)}\n")
    report_lines.append("\n---\n")

    # 汇总表格
    report_lines.append("## 各维度达成情况汇总\n")
    report_lines.append(generate_summary_table(all_results))
    report_lines.append("\n---\n")

    # 说明
    report_lines.append("## 说明\n")
    report_lines.append(
        "- **全局 KPI**: 全局 KPI 指标的达成情况\n"
    )
    report_lines.append(
        "- **区域预算**: 各推广区域预算分配的达成情况\n"
    )
    report_lines.append(
        "- **区域 KPI**: 各推广区域 KPI 指标的达成情况\n"
    )
    report_lines.append(
        "- **阶段预算**: 各阶段预算分配的满足情况\n"
    )
    report_lines.append(
        "- **营销漏斗预算**: 各营销漏斗预算分配的满足情况\n"
    )
    report_lines.append(
        "- **媒体预算**: 各媒体预算分配的满足情况\n"
    )
    report_lines.append(
        "- **广告类型 KPI**: 各广告类型 KPI 指标的达成情况\n"
    )
    report_lines.append(
        "- **Adtype 预算分配**: Adtype 预算分配检查（仅当 allow_zero_budget=False 时）\n"
    )
    report_lines.append(
        "- **总 KPI 达成率**: 所有 KPI（全局、区域、广告类型）的总体达成情况\n"
    )

    # 保存报告
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(report_lines)

    print(f"汇总报告已保存到: {output_path}")


def generate_html_report(all_results: List[Dict[str, Any]], output_path: Path):
    """生成 HTML 格式的汇总报告"""
    html_lines = []
    html_lines.append("<!DOCTYPE html>\n")
    html_lines.append("<html lang='zh-CN'>\n")
    html_lines.append("<head>\n")
    html_lines.append("  <meta charset='UTF-8'>\n")
    html_lines.append(
        "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
    )
    html_lines.append("  <title>测试结果汇总报告</title>\n")
    html_lines.append("  <style>\n")
    html_lines.append(
        "    body { font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background: #f5f5f5; }\n"
    )
    html_lines.append(
        "    .container { max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }\n"
    )
    html_lines.append(
        "    h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }\n"
    )
    html_lines.append(
        "    h2 { color: #555; margin-top: 30px; border-left: 4px solid #4CAF50; padding-left: 10px; }\n"
    )
    html_lines.append(
        "    table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 12px; }\n"
    )
    html_lines.append(
        "    th, td { padding: 8px; text-align: left; border: 1px solid #ddd; }\n"
    )
    html_lines.append(
        "    th { background-color: #4CAF50; color: white; font-weight: bold; position: sticky; top: 0; }\n"
    )
    html_lines.append("    tr:nth-child(even) { background-color: #f9f9f9; }\n")
    html_lines.append("    .rate-ok { color: #4CAF50; font-weight: bold; }\n")
    html_lines.append("    .rate-warning { color: #ff9800; font-weight: bold; }\n")
    html_lines.append("    .rate-fail { color: #f44336; font-weight: bold; }\n")
    html_lines.append(
        "    .summary { background: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0; }\n"
    )
    html_lines.append("  </style>\n")
    html_lines.append("</head>\n")
    html_lines.append("<body>\n")
    html_lines.append("  <div class='container'>\n")
    html_lines.append(f"    <h1>测试结果汇总报告</h1>\n")
    html_lines.append(
        f"    <p><strong>生成时间</strong>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n"
    )
    html_lines.append(f"    <p><strong>测试用例数量</strong>: {len(all_results)}</p>\n")

    # 汇总表格
    html_lines.append("    <h2>各维度达成情况汇总</h2>\n")
    html_lines.append("    <div style='overflow-x: auto;'>\n")
    html_lines.append("    <table>\n")

    # 表头
    dimension_keys = [
        "global_kpi",
        "region_budget",
        "region_kpi",
        "stage_budget",
        "marketingfunnel_budget",
        "media_budget",
        "adtype_kpi",
        "adtype_budget_allocation",
    ]

    header = ["测试用例"]
    for dim_key in dimension_keys:
        if all_results and dim_key in all_results[0]["summary"]:
            header.append(all_results[0]["summary"][dim_key]["name"])
    header.append("总 KPI 达成率")

    html_lines.append("      <tr>")
    for h in header:
        html_lines.append(f"        <th>{h}</th>")
    html_lines.append("      </tr>\n")

    # 表格行
    for result in all_results:
        case_name = result["case_name"]
        summary = result["summary"]
        total_kpi = result["total_kpi"]

        html_lines.append("      <tr>")
        html_lines.append(f"        <td><strong>{case_name}</strong></td>")

        for dim_key in dimension_keys:
            if dim_key in summary:
                dim_info = summary[dim_key]
                rate = dim_info["rate"]
                # 根据达成率设置颜色
                if rate >= 80:
                    rate_class = "rate-ok"
                elif rate >= 60:
                    rate_class = "rate-warning"
                else:
                    rate_class = "rate-fail"
                html_lines.append(
                    f"        <td class='{rate_class}'>{dim_info['achieved']} ({rate:.1f}%)</td>"
                )
            else:
                html_lines.append("        <td>-</td>")

        # 总 KPI 达成率
        total_rate = total_kpi["rate"]
        if total_rate >= 80:
            rate_class = "rate-ok"
        elif total_rate >= 60:
            rate_class = "rate-warning"
        else:
            rate_class = "rate-fail"
        html_lines.append(
            f"        <td class='{rate_class}'><strong>{total_kpi['achieved']} ({total_rate:.1f}%)</strong></td>"
        )
        html_lines.append("      </tr>\n")

    html_lines.append("    </table>\n")
    html_lines.append("    </div>\n")

    # 说明
    html_lines.append("    <h2>说明</h2>\n")
    html_lines.append("    <div class='summary'>\n")
    html_lines.append(
        "<ul><li><strong>全局 KPI</strong>: 全局 KPI 指标的达成情况</li>\n"
    )
    html_lines.append(
        "<li><strong>区域预算</strong>: 各推广区域预算分配的达成情况</li>\n"
    )
    html_lines.append(
        "<li><strong>区域 KPI</strong>: 各推广区域 KPI 指标的达成情况</li>\n"
    )
    html_lines.append(
        "<li><strong>阶段预算</strong>: 各阶段预算分配的满足情况</li>\n"
    )
    html_lines.append(
        "<li><strong>营销漏斗预算</strong>: 各营销漏斗预算分配的满足情况</li>\n"
    )
    html_lines.append(
        "<li><strong>媒体预算</strong>: 各媒体预算分配的满足情况</li>\n"
    )
    html_lines.append(
        "<li><strong>广告类型 KPI</strong>: 各广告类型 KPI 指标的达成情况</li>\n"
    )
    html_lines.append(
        "<li><strong>Adtype 预算分配</strong>: Adtype 预算分配检查（仅当 allow_zero_budget=False 时）</li>\n"
    )
    html_lines.append(
        "<li><strong>总 KPI 达成率</strong>: 所有 KPI（全局、区域、广告类型）的总体达成情况</li></ul>\n"
    )
    html_lines.append("    </div>\n")

    html_lines.append("  </div>\n")
    html_lines.append("</body>\n")
    html_lines.append("</html>\n")

    # 保存报告
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(html_lines)

    print(f"HTML 汇总报告已保存到: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="汇总所有测试结果")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default="output/achievement_checks/json",
        help="输入目录（包含所有 achievement_check.json 文件）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出文件路径（可选，默认：与输入目录同级的 reports 目录）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["markdown", "html", "both"],
        default="both",
        help="输出格式：markdown、html 或 both（默认：both）",
    )

    args = parser.parse_args()

    # 获取所有 achievement_check.json 文件
    input_dir = args.input_dir
    if not input_dir.exists():
        print(f"错误：输入目录不存在: {input_dir}")
        return 1

    json_files = sorted(input_dir.glob("*_achievement_check.json"))
    if not json_files:
        print(f"错误：在 {input_dir} 中未找到任何 achievement_check.json 文件")
        return 1

    print(f"找到 {len(json_files)} 个结果文件，开始汇总...\n")

    # 加载所有结果并计算汇总
    all_results = []
    for json_file in json_files:
        try:
            results = load_json(json_file)
            case_name = results.get("case_name", json_file.stem)

            # 计算各维度汇总
            summary = calculate_dimension_summary(results)

            # 计算总 KPI 汇总
            total_kpi = calculate_total_kpi_summary(results)

            all_results.append({
                "case_name": case_name,
                "summary": summary,
                "total_kpi": total_kpi,
            })
            print(f"  ✓ 已处理: {case_name}")
        except Exception as e:
            print(f"  ✗ 处理失败 {json_file.name}: {e}")

    if not all_results:
        print("错误：没有成功加载任何结果文件")
        return 1

    # 确定输出路径
    if args.output:
        output_base = args.output
    else:
        # 默认输出到与输入目录同级的 reports 目录
        if input_dir.name == "json":
            reports_dir = input_dir.parent / "reports"
        else:
            reports_dir = input_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        output_base = reports_dir / "summary_all_results"

    # 生成报告
    if args.format in ["markdown", "both"]:
        md_path = output_base.with_suffix(".md")
        generate_markdown_report(all_results, md_path)

    if args.format in ["html", "both"]:
        html_path = output_base.with_suffix(".html")
        generate_html_report(all_results, html_path)

    print(f"\n汇总完成，共处理 {len(all_results)} 个测试用例")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())

