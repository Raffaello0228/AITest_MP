#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成测试报告 - 以更可读的方式输出测试结论
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


def generate_markdown_report(results: Dict[str, Any], output_path: Path):
    """生成 Markdown 格式的测试报告"""
    case_name = results.get("case_name", "未知用例")
    testcase_config = results.get("testcase_config", {})

    report_lines = []
    report_lines.append("# 测试报告\n")
    report_lines.append(f"**测试用例**: {case_name}\n")

    # 显示 uuid 和 job_id（如果存在）
    uuid = results.get("uuid")
    job_id = results.get("job_id")
    if uuid:
        report_lines.append(f"**UUID**: {uuid}\n")
    if job_id:
        report_lines.append(f"**Job ID**: {job_id}\n")

    report_lines.append(
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    report_lines.append("\n---\n")

    # 测试配置
    report_lines.append("## 测试配置\n")
    report_lines.append("| 配置项 | 值 |\n")
    report_lines.append("|--------|-----|\n")
    report_lines.append(
        f"| KPI目标达成率 | {testcase_config.get('kpi_target_rate', 80)}% |\n"
    )
    report_lines.append(
        f"| 区域预算目标达成率 | {testcase_config.get('region_budget_target_rate', 90)}% |\n"
    )
    report_lines.append(
        f"| 区域KPI目标达成率 | {testcase_config.get('region_kpi_target_rate', 80)}% |\n"
    )
    report_lines.append(
        f"| 广告类型KPI目标达成率 | {testcase_config.get('mediaMarketingFunnelAdtype_target_rate', 80)}% |\n"
    )
    report_lines.append(
        f"| 阶段预算误差范围 | {testcase_config.get('stage_range_match', 20)}% |\n"
    )
    report_lines.append(
        f"| 营销漏斗预算误差范围 | {testcase_config.get('marketingfunnel_range_match', 15)}% |\n"
    )
    report_lines.append(
        f"| 媒体预算误差范围 | {testcase_config.get('media_range_match', 5)}% |\n"
    )
    report_lines.append("\n---\n")

    # KPI优先级
    kpi_priority_list = testcase_config.get("kpi_priority_list", [])
    if kpi_priority_list:
        report_lines.append("### KPI优先级\n")
        report_lines.append("| 优先级 | KPI |\n")
        report_lines.append("|--------|-----|\n")
        for idx, kpi_name in enumerate(kpi_priority_list, 1):
            report_lines.append(f"| {idx} | {kpi_name} |\n")
        report_lines.append("\n---\n")

    # 模块优先级
    module_priority_list = testcase_config.get("module_priority_list", [])
    if module_priority_list:
        report_lines.append("### 模块优先级\n")
        report_lines.append("| 优先级 | 模块 |\n")
        report_lines.append("|--------|-----|\n")
        for idx, module_name in enumerate(module_priority_list, 1):
            report_lines.append(f"| {idx} | {module_name} |\n")
        report_lines.append("\n---\n")

    # 全局 KPI
    if "global_kpi" in results:
        report_lines.append("## 全局 KPI 达成情况\n")
        global_kpi = results["global_kpi"]
        achieved_count = sum(1 for v in global_kpi.values() if v.get("achieved", False))
        total_count = len(global_kpi)

        report_lines.append(
            f"**达成率**: {achieved_count}/{total_count} ({achieved_count/total_count*100:.2f}%)\n"
        )
        report_lines.append(
            '\n**判断逻辑**: 当"必须达成"为"是"时，要求实际值 ≥ 目标值；当"必须达成"为"否"时，满足达成率条件即可。\n'
        )
        report_lines.append(
            "\n| KPI | 优先级 | 必须达成 | 实际值 | 目标值 | 达成率 | 状态 |\n"
        )
        report_lines.append(
            "|-----|--------|----------|--------|--------|--------|------|\n"
        )

        for kpi_name in sorted(
            global_kpi.keys(), key=lambda x: global_kpi[x].get("priority", 999)
        ):
            kpi_data = global_kpi[kpi_name]
            status = "✓ 达成" if kpi_data["achieved"] else "✗ 未达成"
            achievement_rate = kpi_data.get("achievement_rate", 0)
            if isinstance(achievement_rate, (int, float)):
                rate_str = f"{achievement_rate:.2f}%"
            else:
                rate_str = str(achievement_rate)
            completion = kpi_data.get("completion", 0)
            must_achieve = "是" if completion == 1 else "否"

            report_lines.append(
                f"| {kpi_name} | {kpi_data.get('priority', 999)} | {must_achieve} | "
                f"{kpi_data['actual']:,.0f} | {kpi_data['target']:,.0f} | "
                f"{rate_str} | {status} |\n"
            )
        report_lines.append("\n---\n")

    # 区域预算
    if "region_budget" in results:
        report_lines.append("## 区域预算达成情况\n")
        region_budget = results["region_budget"]
        achieved_count = sum(
            1 for v in region_budget.values() if v.get("achieved", False)
        )
        total_count = len(region_budget)

        match_type = None
        if region_budget:
            first_region = next(iter(region_budget.values()))
            match_type = first_region.get("match_type", "完全匹配")

        report_lines.append(f"**匹配类型**: {match_type}\n")
        report_lines.append(
            f"**达成率**: {achieved_count}/{total_count} ({achieved_count/total_count*100:.2f}%)\n"
        )

        if match_type == "完全匹配":
            report_lines.append(
                "\n| 区域 | 实际占比 | 目标占比 | 误差 | 允许误差 | 状态 |\n"
            )
            report_lines.append(
                "|------|----------|----------|------|----------|------|\n"
            )

            for country_code in sorted(region_budget.keys()):
                budget_data = region_budget[country_code]
                status = "✓ 达成" if budget_data["achieved"] else "✗ 未达成"
                error = budget_data.get("error_percentage", 0)
                if isinstance(error, (int, float)):
                    error_str = f"{error:.2f}%"
                else:
                    error_str = str(error)

                report_lines.append(
                    f"| {country_code} | {budget_data.get('actual_percentage', 0):.2f}% | "
                    f"{budget_data.get('target_percentage', 0):.2f}% | {error_str} | "
                    f"{budget_data.get('range_match', 0)}% | {status} |\n"
                )

        elif match_type == "大小关系匹配":
            order_consistent = None
            if region_budget:
                first_region = next(iter(region_budget.values()))
                order_consistent = first_region.get("order_consistent", False)

            order_status = "✓ 一致" if order_consistent else "✗ 不一致"
            report_lines.append(f"**顺序一致性**: {order_status}\n")

            report_lines.append(
                "\n| 区域 | 目标排名 | 实际排名 | 实际预算 | 目标预算 | 必须达成 | 状态 |\n"
            )
            report_lines.append(
                "|------|----------|----------|----------|----------|----------|------|\n"
            )

            sorted_regions = sorted(
                region_budget.items(), key=lambda x: x[1].get("target_rank", 999)
            )

            for country_code, budget_data in sorted_regions:
                status = "✓ 达成" if budget_data["achieved"] else "✗ 未达成"
                completion = budget_data.get("completion", 0)
                must_achieve = "是" if completion == 1 else "否"

                report_lines.append(
                    f"| {country_code} | {budget_data.get('target_rank', -1) + 1} | "
                    f"{budget_data.get('actual_rank', -1) + 1} | "
                    f"{budget_data['actual']:,.2f} | {budget_data['target']:,.2f} | "
                    f"{must_achieve} | {status} |\n"
                )

        report_lines.append("\n---\n")

    # 区域 KPI
    if "region_kpi" in results:
        report_lines.append("## 区域 KPI 达成情况\n")
        region_kpi = results["region_kpi"]

        report_lines.append(
            '\n**判断逻辑**: 当"必须达成"为"是"时，要求实际值 ≥ 目标值；当"必须达成"为"否"时，满足达成率条件即可。\n'
        )
        # 汇总表格
        report_lines.append("### 汇总\n")
        report_lines.append("| 区域 | 达成数/总数 | 达成率 |\n")
        report_lines.append("|------|-------------|--------|\n")

        for country_code in sorted(region_kpi.keys()):
            country_kpis = region_kpi[country_code]
            achieved_count = sum(
                1 for v in country_kpis.values() if v.get("achieved", False)
            )
            total_count = len(country_kpis)
            rate = (achieved_count / total_count * 100) if total_count > 0 else 0

            report_lines.append(
                f"| {country_code} | {achieved_count}/{total_count} | {rate:.2f}% |\n"
            )

        # 详细表格
        report_lines.append("\n### 详细信息\n")
        for country_code in sorted(region_kpi.keys()):
            country_kpis = region_kpi[country_code]
            report_lines.append(f"#### {country_code}\n")
            report_lines.append(
                "| KPI | 优先级 | 必须达成 | 实际值 | 目标值 | 达成率 | 状态 |\n"
            )
            report_lines.append(
                "|-----|--------|----------|--------|--------|--------|------|\n"
            )

            for kpi_name in sorted(
                country_kpis.keys(), key=lambda x: country_kpis[x].get("priority", 999)
            ):
                kpi_data = country_kpis[kpi_name]
                status = "✓ 达成" if kpi_data["achieved"] else "✗ 未达成"
                achievement_rate = kpi_data.get("achievement_rate", 0)
                if isinstance(achievement_rate, (int, float)):
                    rate_str = f"{achievement_rate:.2f}%"
                else:
                    rate_str = str(achievement_rate)
                completion = kpi_data.get("completion", 0)
                must_achieve = "是" if completion == 1 else "否"

                report_lines.append(
                    f"| {kpi_name} | {kpi_data.get('priority', 999)} | {must_achieve} | "
                    f"{kpi_data['actual']:,.0f} | {kpi_data['target']:,.0f} | "
                    f"{rate_str} | {status} |\n"
                )
        report_lines.append("\n---\n")

    # 阶段预算
    if "stage_budget" in results:
        report_lines.append("## 阶段预算满足情况\n")
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

        report_lines.append(
            f"**总体满足率**: {total_satisfied}/{total_count} ({total_satisfied/total_count*100:.1f}%)\n"
        )

        report_lines.append("\n| 区域 | 满足数/总数 | 满足率 |\n")
        report_lines.append("|------|-------------|--------|\n")

        for country_code in sorted(stage_budget.keys()):
            country_stages = stage_budget[country_code]
            country_satisfied = sum(
                1 for v in country_stages.values() if v.get("satisfied", False)
            )
            country_total = len(country_stages)
            rate = (country_satisfied / country_total * 100) if country_total > 0 else 0

            report_lines.append(
                f"| {country_code} | {country_satisfied}/{country_total} | {rate:.1f}% |\n"
            )
        report_lines.append("\n---\n")

    # 营销漏斗预算
    if "marketingfunnel_budget" in results:
        report_lines.append("## 营销漏斗预算满足情况\n")
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

        report_lines.append(
            f"**总体满足率**: {total_satisfied}/{total_count} ({total_satisfied/total_count*100:.1f}%)\n"
        )

        report_lines.append("\n| 区域 | 满足数/总数 | 满足率 |\n")
        report_lines.append("|------|-------------|--------|\n")

        for country_code in sorted(funnel_budget.keys()):
            country_funnels = funnel_budget[country_code]
            country_satisfied = sum(
                1 for v in country_funnels.values() if v.get("satisfied", False)
            )
            country_total = len(country_funnels)
            rate = (country_satisfied / country_total * 100) if country_total > 0 else 0

            report_lines.append(
                f"| {country_code} | {country_satisfied}/{country_total} | {rate:.1f}% |\n"
            )
        report_lines.append("\n---\n")

    # 媒体预算
    if "media_budget" in results:
        report_lines.append("## 媒体预算满足情况\n")
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

        report_lines.append(
            f"**总体满足率**: {total_satisfied}/{total_count} ({total_satisfied/total_count*100:.1f}%)\n"
        )

        report_lines.append("\n| 区域 | 满足数/总数 | 满足率 |\n")
        report_lines.append("|------|-------------|--------|\n")

        for country_code in sorted(media_budget.keys()):
            country_media = media_budget[country_code]
            country_satisfied = sum(
                1 for v in country_media.values() if v.get("satisfied", False)
            )
            country_total = len(country_media)
            rate = (country_satisfied / country_total * 100) if country_total > 0 else 0

            report_lines.append(
                f"| {country_code} | {country_satisfied}/{country_total} | {rate:.1f}% |\n"
            )
        report_lines.append("\n---\n")

    # 广告类型 KPI 汇总
    if "adtype_kpi" in results:
        report_lines.append("## 广告类型 KPI 达成情况\n")
        adtype_kpi = results["adtype_kpi"]
        total_achieved = 0
        total_count = 0

        for key, adtype_data in adtype_kpi.items():
            kpis = adtype_data.get("kpis", {})
            for kpi_name, kpi_data in kpis.items():
                total_count += 1
                if kpi_data.get("achieved", False):
                    total_achieved += 1

        report_lines.append(
            f"**总体达成率**: {total_achieved}/{total_count} ({total_achieved/total_count*100:.1f}%)\n"
        )
        report_lines.append("\n(详细数据请查看 JSON 文件)\n")
        report_lines.append("\n---\n")

    # Adtype 预算分配检查
    if "adtype_budget_allocation" in results:
        report_lines.append("## Adtype 预算分配检查\n")
        report_lines.append(
            "\n**说明**: 当 `allow_zero_budget=False` 时，检查每个推广区域下每个 Adtype 是否都分配了预算。"
            "按 (媒体, 平台, 广告类型) 聚合求和预算（跨所有 stage），只要预算 > 0 即视为已分配。\n"
        )
        adtype_allocation = results["adtype_budget_allocation"]
        total_satisfied = 0
        total_count = 0

        for country_code in sorted(adtype_allocation.keys()):
            country_adtypes = adtype_allocation[country_code]
            country_satisfied = sum(
                1 for v in country_adtypes.values() if v.get("satisfied", False)
            )
            country_total = len(country_adtypes)
            total_satisfied += country_satisfied
            total_count += country_total

        report_lines.append(
            f"**总体满足率**: {total_satisfied}/{total_count} ({total_satisfied/total_count*100:.1f}%)\n"
        )

        report_lines.append("\n| 区域 | 满足数/总数 | 满足率 |\n")
        report_lines.append("|------|-------------|--------|\n")

        for country_code in sorted(adtype_allocation.keys()):
            country_adtypes = adtype_allocation[country_code]
            country_satisfied = sum(
                1 for v in country_adtypes.values() if v.get("satisfied", False)
            )
            country_total = len(country_adtypes)
            rate = (country_satisfied / country_total * 100) if country_total > 0 else 0

            report_lines.append(
                f"| {country_code} | {country_satisfied}/{country_total} | {rate:.1f}% |\n"
            )

        # 显示未满足的 Adtype
        unsatisfied_count = 0
        for country_code in sorted(adtype_allocation.keys()):
            country_adtypes = adtype_allocation[country_code]
            unsatisfied = [
                (k, v)
                for k, v in country_adtypes.items()
                if not v.get("satisfied", False)
            ]
            if unsatisfied:
                unsatisfied_count += len(unsatisfied)
                report_lines.append(f"\n### {country_code} - 未满足的 Adtype\n")
                report_lines.append("| 媒体 | 平台 | 广告类型 | 预算 |\n")
                report_lines.append("|------|------|----------|------|\n")
                for key, adtype_data in sorted(unsatisfied, key=lambda x: x[0]):
                    report_lines.append(
                        f"| {adtype_data['media']} | {adtype_data['platform']} | "
                        f"{adtype_data['adtype']} | {adtype_data['budget']:,.2f} |\n"
                    )

        if unsatisfied_count == 0:
            report_lines.append("\n✓ 所有 Adtype 都已分配预算\n")

        report_lines.append("\n---\n")

    # 总体结论
    report_lines.append("## 总体结论\n")
    report_lines.append("\n### 各维度达成情况汇总\n")
    report_lines.append("\n| 维度 | 达成情况 | 达成率 |\n")
    report_lines.append("|------|----------|--------|\n")

    dimensions = [
        ("全局 KPI", "global_kpi"),
        ("区域预算", "region_budget"),
        ("区域 KPI", "region_kpi"),
        ("阶段预算", "stage_budget"),
        ("营销漏斗预算", "marketingfunnel_budget"),
        ("媒体预算", "media_budget"),
        ("广告类型 KPI", "adtype_kpi"),
        ("Adtype 预算分配", "adtype_budget_allocation"),
    ]

    for dim_name, dim_key in dimensions:
        if dim_key in results:
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
                achieved_count = sum(
                    1
                    for v in dim_data.values()
                    if v.get("achieved", False) or v.get("satisfied", False)
                )
                total_count = len(dim_data)
                achieved_str = f"{achieved_count}/{total_count}"
                rate = (achieved_count / total_count * 100) if total_count > 0 else 0

            report_lines.append(f"| {dim_name} | {achieved_str} | {rate:.1f}% |\n")

    # 保存报告
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(report_lines)

    print(f"Markdown 报告已保存到: {output_path}")


def generate_html_report(results: Dict[str, Any], output_path: Path):
    """生成 HTML 格式的测试报告"""
    case_name = results.get("case_name", "未知用例")
    testcase_config = results.get("testcase_config", {})

    html_lines = []
    html_lines.append("<!DOCTYPE html>\n")
    html_lines.append("<html lang='zh-CN'>\n")
    html_lines.append("<head>\n")
    html_lines.append("  <meta charset='UTF-8'>\n")
    html_lines.append(
        "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
    )
    html_lines.append("  <title>测试报告 - " + case_name + "</title>\n")
    html_lines.append("  <style>\n")
    html_lines.append(
        "    body { font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background: #f5f5f5; }\n"
    )
    html_lines.append(
        "    .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }\n"
    )
    html_lines.append(
        "    h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }\n"
    )
    html_lines.append(
        "    h2 { color: #555; margin-top: 30px; border-left: 4px solid #4CAF50; padding-left: 10px; }\n"
    )
    html_lines.append(
        "    table { width: 100%; border-collapse: collapse; margin: 20px 0; }\n"
    )
    html_lines.append(
        "    th, td { padding: 12px; text-align: left; border: 1px solid #ddd; }\n"
    )
    html_lines.append(
        "    th { background-color: #4CAF50; color: white; font-weight: bold; }\n"
    )
    html_lines.append("    tr:nth-child(even) { background-color: #f9f9f9; }\n")
    html_lines.append("    .status-ok { color: #4CAF50; font-weight: bold; }\n")
    html_lines.append("    .status-fail { color: #f44336; font-weight: bold; }\n")
    html_lines.append(
        "    .summary { background: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0; }\n"
    )
    html_lines.append("    .config-table { background: #fff3e0; }\n")
    html_lines.append("  </style>\n")
    html_lines.append("</head>\n")
    html_lines.append("<body>\n")
    html_lines.append("  <div class='container'>\n")
    html_lines.append(f"    <h1>测试报告</h1>\n")
    html_lines.append(f"    <p><strong>测试用例</strong>: {case_name}</p>\n")

    # 显示 uuid 和 job_id（如果存在）
    uuid = results.get("uuid")
    job_id = results.get("job_id")
    if uuid:
        html_lines.append(f"    <p><strong>UUID</strong>: {uuid}</p>\n")
    if job_id:
        html_lines.append(f"    <p><strong>Job ID</strong>: {job_id}</p>\n")

    html_lines.append(
        f"    <p><strong>生成时间</strong>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n"
    )

    # 测试配置
    html_lines.append("    <h2>测试配置</h2>\n")
    html_lines.append("    <table class='config-table'>\n")
    html_lines.append("      <tr><th>配置项</th><th>值</th></tr>\n")
    html_lines.append(
        f"      <tr><td>KPI目标达成率</td><td>{testcase_config.get('kpi_target_rate', 80)}%</td></tr>\n"
    )
    html_lines.append(
        f"      <tr><td>区域预算目标达成率</td><td>{testcase_config.get('region_budget_target_rate', 90)}%</td></tr>\n"
    )
    html_lines.append(
        f"      <tr><td>区域KPI目标达成率</td><td>{testcase_config.get('region_kpi_target_rate', 80)}%</td></tr>\n"
    )
    html_lines.append(
        f"      <tr><td>广告类型KPI目标达成率</td><td>{testcase_config.get('mediaMarketingFunnelAdtype_target_rate', 80)}%</td></tr>\n"
    )
    html_lines.append(
        f"      <tr><td>阶段预算误差范围</td><td>{testcase_config.get('stage_range_match', 20)}%</td></tr>\n"
    )
    html_lines.append(
        f"      <tr><td>营销漏斗预算误差范围</td><td>{testcase_config.get('marketingfunnel_range_match', 15)}%</td></tr>\n"
    )
    html_lines.append(
        f"      <tr><td>媒体预算误差范围</td><td>{testcase_config.get('media_range_match', 5)}%</td></tr>\n"
    )
    html_lines.append("    </table>\n")

    # KPI优先级
    kpi_priority_list = testcase_config.get("kpi_priority_list", [])
    if kpi_priority_list:
        html_lines.append("    <h3>KPI优先级</h3>\n")
        html_lines.append("    <table class='config-table'>\n")
        html_lines.append("      <tr><th>优先级</th><th>KPI</th></tr>\n")
        for idx, kpi_name in enumerate(kpi_priority_list, 1):
            html_lines.append(f"      <tr><td>{idx}</td><td>{kpi_name}</td></tr>\n")
        html_lines.append("    </table>\n")

    # 模块优先级
    module_priority_list = testcase_config.get("module_priority_list", [])
    if module_priority_list:
        html_lines.append("    <h3>模块优先级</h3>\n")
        html_lines.append("    <table class='config-table'>\n")
        html_lines.append("      <tr><th>优先级</th><th>模块</th></tr>\n")
        for idx, module_name in enumerate(module_priority_list, 1):
            html_lines.append(f"      <tr><td>{idx}</td><td>{module_name}</td></tr>\n")
        html_lines.append("    </table>\n")

    # 全局 KPI
    if "global_kpi" in results:
        html_lines.append("    <h2>全局 KPI 达成情况</h2>\n")
        global_kpi = results["global_kpi"]
        achieved_count = sum(1 for v in global_kpi.values() if v.get("achieved", False))
        total_count = len(global_kpi)

        html_lines.append(
            f"    <div class='summary'><strong>达成率</strong>: {achieved_count}/{total_count} ({achieved_count/total_count*100:.1f}%)</div>\n"
        )
        html_lines.append(
            '    <div class=\'summary\'><strong>判断逻辑</strong>: 当"必须达成"为"是"时，要求实际值 ≥ 目标值；当"必须达成"为"否"时，满足达成率条件即可。</div>\n'
        )
        html_lines.append("    <table>\n")
        html_lines.append(
            "      <tr><th>KPI</th><th>优先级</th><th>必须达成</th><th>实际值</th><th>目标值</th><th>达成率</th><th>状态</th></tr>\n"
        )

        for kpi_name in sorted(
            global_kpi.keys(), key=lambda x: global_kpi[x].get("priority", 999)
        ):
            kpi_data = global_kpi[kpi_name]
            status_class = "status-ok" if kpi_data["achieved"] else "status-fail"
            status_text = "✓ 达成" if kpi_data["achieved"] else "✗ 未达成"
            achievement_rate = kpi_data.get("achievement_rate", 0)
            if isinstance(achievement_rate, (int, float)):
                rate_str = f"{achievement_rate:.2f}%"
            else:
                rate_str = str(achievement_rate)
            completion = kpi_data.get("completion", 0)
            must_achieve = "是" if completion == 1 else "否"

            html_lines.append(
                f"      <tr><td>{kpi_name}</td><td>{kpi_data.get('priority', 999)}</td>"
                f"<td>{must_achieve}</td><td>{kpi_data['actual']:,.0f}</td><td>{kpi_data['target']:,.0f}</td>"
                f"<td>{rate_str}</td><td class='{status_class}'>{status_text}</td></tr>\n"
            )
        html_lines.append("    </table>\n")

    # 区域预算
    if "region_budget" in results:
        html_lines.append("    <h2>区域预算达成情况</h2>\n")
        region_budget = results["region_budget"]
        achieved_count = sum(
            1 for v in region_budget.values() if v.get("achieved", False)
        )
        total_count = len(region_budget)

        match_type = None
        if region_budget:
            first_region = next(iter(region_budget.values()))
            match_type = first_region.get("match_type", "完全匹配")

        html_lines.append(
            f"    <div class='summary'><strong>匹配类型</strong>: {match_type} | "
            f"<strong>达成率</strong>: {achieved_count}/{total_count} ({achieved_count/total_count*100:.1f}%)</div>\n"
        )

        if match_type == "完全匹配":
            html_lines.append("    <table>\n")
            html_lines.append(
                "      <tr><th>区域</th><th>实际占比</th><th>目标占比</th><th>误差</th><th>允许误差</th><th>状态</th></tr>\n"
            )

            for country_code in sorted(region_budget.keys()):
                budget_data = region_budget[country_code]
                status_class = "status-ok" if budget_data["achieved"] else "status-fail"
                status_text = "✓ 达成" if budget_data["achieved"] else "✗ 未达成"
                error = budget_data.get("error_percentage", 0)
                if isinstance(error, (int, float)):
                    error_str = f"{error:.2f}%"
                else:
                    error_str = str(error)

                html_lines.append(
                    f"      <tr><td>{country_code}</td>"
                    f"<td>{budget_data.get('actual_percentage', 0):.2f}%</td>"
                    f"<td>{budget_data.get('target_percentage', 0):.2f}%</td>"
                    f"<td>{error_str}</td><td>{budget_data.get('range_match', 0)}%</td>"
                    f"<td class='{status_class}'>{status_text}</td></tr>\n"
                )
            html_lines.append("    </table>\n")

        elif match_type == "大小关系匹配":
            order_consistent = None
            if region_budget:
                first_region = next(iter(region_budget.values()))
                order_consistent = first_region.get("order_consistent", False)

            order_status = "✓ 一致" if order_consistent else "✗ 不一致"
            order_class = "status-ok" if order_consistent else "status-fail"
            html_lines.append(
                f"    <div class='summary'><strong>顺序一致性</strong>: <span class='{order_class}'>{order_status}</span></div>\n"
            )

            html_lines.append("    <table>\n")
            html_lines.append(
                "      <tr><th>区域</th><th>目标排名</th><th>实际排名</th><th>实际预算</th><th>目标预算</th><th>必须达成</th><th>状态</th></tr>\n"
            )

            sorted_regions = sorted(
                region_budget.items(), key=lambda x: x[1].get("target_rank", 999)
            )

            for country_code, budget_data in sorted_regions:
                status_class = "status-ok" if budget_data["achieved"] else "status-fail"
                status_text = "✓ 达成" if budget_data["achieved"] else "✗ 未达成"
                completion = budget_data.get("completion", 0)
                must_achieve = "是" if completion == 1 else "否"

                html_lines.append(
                    f"      <tr><td>{country_code}</td>"
                    f"<td>{budget_data.get('target_rank', -1) + 1}</td>"
                    f"<td>{budget_data.get('actual_rank', -1) + 1}</td>"
                    f"<td>{budget_data['actual']:,.2f}</td>"
                    f"<td>{budget_data['target']:,.2f}</td>"
                    f"<td>{must_achieve}</td>"
                    f"<td class='{status_class}'>{status_text}</td></tr>\n"
                )
            html_lines.append("    </table>\n")

    # 其他维度汇总表格
    dimensions_summary = [
        ("区域 KPI", "region_kpi"),
        ("阶段预算", "stage_budget"),
        ("营销漏斗预算", "marketingfunnel_budget"),
        ("媒体预算", "media_budget"),
    ]

    # Adtype 预算分配检查
    if "adtype_budget_allocation" in results:
        html_lines.append("    <h2>Adtype 预算分配检查</h2>\n")
        html_lines.append(
            "    <div class='summary'><strong>说明</strong>: 当 <code>allow_zero_budget=False</code> 时，"
            "检查每个推广区域下每个 Adtype 是否都分配了预算。按 (媒体, 平台, 广告类型) 聚合求和预算（跨所有 stage），"
            "只要预算 > 0 即视为已分配。</div>\n"
        )
        adtype_allocation = results["adtype_budget_allocation"]
        total_satisfied = 0
        total_count = 0

        for country_code in sorted(adtype_allocation.keys()):
            country_adtypes = adtype_allocation[country_code]
            country_satisfied = sum(
                1 for v in country_adtypes.values() if v.get("satisfied", False)
            )
            country_total = len(country_adtypes)
            total_satisfied += country_satisfied
            total_count += country_total

        html_lines.append(
            f"    <div class='summary'><strong>总体满足率</strong>: {total_satisfied}/{total_count} ({total_satisfied/total_count*100:.1f}%)</div>\n"
        )
        html_lines.append("    <table>\n")
        html_lines.append(
            "      <tr><th>区域</th><th>满足数/总数</th><th>满足率</th></tr>\n"
        )

        for country_code in sorted(adtype_allocation.keys()):
            country_adtypes = adtype_allocation[country_code]
            country_satisfied = sum(
                1 for v in country_adtypes.values() if v.get("satisfied", False)
            )
            country_total = len(country_adtypes)
            rate = (country_satisfied / country_total * 100) if country_total > 0 else 0

            html_lines.append(
                f"      <tr><td>{country_code}</td><td>{country_satisfied}/{country_total}</td><td>{rate:.1f}%</td></tr>\n"
            )
        html_lines.append("    </table>\n")

        # 显示未满足的 Adtype
        unsatisfied_count = 0
        for country_code in sorted(adtype_allocation.keys()):
            country_adtypes = adtype_allocation[country_code]
            unsatisfied = [
                (k, v)
                for k, v in country_adtypes.items()
                if not v.get("satisfied", False)
            ]
            if unsatisfied:
                unsatisfied_count += len(unsatisfied)
                html_lines.append(f"    <h3>{country_code} - 未满足的 Adtype</h3>\n")
                html_lines.append("    <table>\n")
                html_lines.append(
                    "      <tr><th>媒体</th><th>平台</th><th>广告类型</th><th>预算</th></tr>\n"
                )
                for key, adtype_data in sorted(unsatisfied, key=lambda x: x[0]):
                    html_lines.append(
                        f"      <tr><td>{adtype_data['media']}</td><td>{adtype_data['platform']}</td>"
                        f"<td>{adtype_data['adtype']}</td><td>{adtype_data['budget']:,.2f}</td></tr>\n"
                    )
                html_lines.append("    </table>\n")

        if unsatisfied_count == 0:
            html_lines.append(
                "    <div class='summary'><strong>✓ 所有 Adtype 都已分配预算</strong></div>\n"
            )

    for dim_name, dim_key in dimensions_summary:
        if dim_key in results:
            html_lines.append(f"    <h2>{dim_name}满足情况</h2>\n")
            dim_data = results[dim_key]

            if dim_key == "region_kpi":
                # 区域 KPI 特殊处理
                html_lines.append(
                    '    <div class=\'summary\'><strong>判断逻辑</strong>: 当"必须达成"为"是"时，要求实际值 ≥ 目标值；当"必须达成"为"否"时，满足达成率条件即可。</div>\n'
                )
                # 汇总表格
                html_lines.append("    <h3>汇总</h3>\n")
                html_lines.append("    <table>\n")
                html_lines.append(
                    "      <tr><th>区域</th><th>达成数/总数</th><th>达成率</th></tr>\n"
                )

                for country_code in sorted(dim_data.keys()):
                    country_kpis = dim_data[country_code]
                    achieved_count = sum(
                        1 for v in country_kpis.values() if v.get("achieved", False)
                    )
                    total_count = len(country_kpis)
                    rate = (
                        (achieved_count / total_count * 100) if total_count > 0 else 0
                    )

                    html_lines.append(
                        f"      <tr><td>{country_code}</td><td>{achieved_count}/{total_count}</td><td>{rate:.1f}%</td></tr>\n"
                    )
                html_lines.append("    </table>\n")

                # 详细表格
                html_lines.append("    <h3>详细信息</h3>\n")
                for country_code in sorted(dim_data.keys()):
                    country_kpis = dim_data[country_code]
                    html_lines.append(f"    <h4>{country_code}</h4>\n")
                    html_lines.append("    <table>\n")
                    html_lines.append(
                        "      <tr><th>KPI</th><th>优先级</th><th>必须达成</th><th>实际值</th><th>目标值</th><th>达成率</th><th>状态</th></tr>\n"
                    )

                    for kpi_name in sorted(
                        country_kpis.keys(),
                        key=lambda x: country_kpis[x].get("priority", 999),
                    ):
                        kpi_data = country_kpis[kpi_name]
                        status_class = (
                            "status-ok" if kpi_data["achieved"] else "status-fail"
                        )
                        status_text = "✓ 达成" if kpi_data["achieved"] else "✗ 未达成"
                        achievement_rate = kpi_data.get("achievement_rate", 0)
                        if isinstance(achievement_rate, (int, float)):
                            rate_str = f"{achievement_rate:.2f}%"
                        else:
                            rate_str = str(achievement_rate)
                        completion = kpi_data.get("completion", 0)
                        must_achieve = "是" if completion == 1 else "否"

                        html_lines.append(
                            f"      <tr><td>{kpi_name}</td><td>{kpi_data.get('priority', 999)}</td>"
                            f"<td>{must_achieve}</td><td>{kpi_data['actual']:,.0f}</td>"
                            f"<td>{kpi_data['target']:,.0f}</td><td>{rate_str}</td>"
                            f"<td class='{status_class}'>{status_text}</td></tr>\n"
                        )
                    html_lines.append("    </table>\n")
            else:
                # 其他维度
                total_satisfied = 0
                total_count = 0

                for country_code in sorted(dim_data.keys()):
                    country_items = dim_data[country_code]
                    country_satisfied = sum(
                        1 for v in country_items.values() if v.get("satisfied", False)
                    )
                    country_total = len(country_items)
                    total_satisfied += country_satisfied
                    total_count += country_total

                html_lines.append(
                    f"    <div class='summary'><strong>总体满足率</strong>: {total_satisfied}/{total_count} ({total_satisfied/total_count*100:.1f}%)</div>\n"
                )
                html_lines.append("    <table>\n")
                html_lines.append(
                    "      <tr><th>区域</th><th>满足数/总数</th><th>满足率</th></tr>\n"
                )

                for country_code in sorted(dim_data.keys()):
                    country_items = dim_data[country_code]
                    country_satisfied = sum(
                        1 for v in country_items.values() if v.get("satisfied", False)
                    )
                    country_total = len(country_items)
                    rate = (
                        (country_satisfied / country_total * 100)
                        if country_total > 0
                        else 0
                    )

                    html_lines.append(
                        f"      <tr><td>{country_code}</td><td>{country_satisfied}/{country_total}</td><td>{rate:.1f}%</td></tr>\n"
                    )
                html_lines.append("    </table>\n")

    # 总体结论
    html_lines.append("    <h2>总体结论</h2>\n")
    html_lines.append("    <h3>各维度达成情况汇总</h3>\n")
    html_lines.append("    <table>\n")
    html_lines.append("      <tr><th>维度</th><th>达成情况</th><th>达成率</th></tr>\n")

    dimensions = [
        ("全局 KPI", "global_kpi"),
        ("区域预算", "region_budget"),
        ("区域 KPI", "region_kpi"),
        ("阶段预算", "stage_budget"),
        ("营销漏斗预算", "marketingfunnel_budget"),
        ("媒体预算", "media_budget"),
        ("广告类型 KPI", "adtype_kpi"),
        ("Adtype 预算分配", "adtype_budget_allocation"),
    ]

    for dim_name, dim_key in dimensions:
        if dim_key in results:
            dim_data = results[dim_key]
            if dim_key == "region_kpi":
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
                achieved_count = sum(
                    1
                    for v in dim_data.values()
                    if v.get("achieved", False) or v.get("satisfied", False)
                )
                total_count = len(dim_data)
                achieved_str = f"{achieved_count}/{total_count}"
                rate = (achieved_count / total_count * 100) if total_count > 0 else 0

            rate_class = "status-ok" if rate >= 80 else "status-fail"
            html_lines.append(
                f"      <tr><td>{dim_name}</td><td>{achieved_str}</td><td class='{rate_class}'>{rate:.1f}%</td></tr>\n"
            )

    html_lines.append("    </table>\n")
    html_lines.append("  </div>\n")
    html_lines.append("</body>\n")
    html_lines.append("</html>\n")

    # 保存报告
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(html_lines)

    print(f"HTML 报告已保存到: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="生成测试报告")
    parser.add_argument(
        "--result-file",
        type=Path,
        required=True,
        help="achievement_check JSON 文件路径（通常在 output/achievement_checks/ 目录下）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出报告文件路径（可选，默认：与 result-file 同目录，同名 .md 和 .html）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["markdown", "html", "both"],
        default="both",
        help="输出格式：markdown、html 或 both（默认：both）",
    )

    args = parser.parse_args()

    # 加载结果
    results = load_json(args.result_file)

    # 确定输出路径
    if args.output:
        output_base = args.output
    else:
        # 如果输入文件在 json/ 目录，输出到 reports/ 目录；否则与输入文件同目录
        if args.result_file.parent.name == "json":
            reports_dir = args.result_file.parent.parent / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            output_base = reports_dir / args.result_file.stem
        else:
            # 默认与输入文件同目录，同名但扩展名不同
            output_base = args.result_file.with_suffix("")

    # 生成报告
    if args.format in ["markdown", "both"]:
        md_path = output_base.with_suffix(".md")
        generate_markdown_report(results, md_path)

    if args.format in ["html", "both"]:
        html_path = output_base.with_suffix(".html")
        generate_html_report(results, html_path)


if __name__ == "__main__":
    main()
