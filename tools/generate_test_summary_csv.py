#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成测试结果CSV报告脚本
用于生成单个测试结果的CSV格式摘要报告

用法:
    python3 generate_test_summary_csv.py --output-dir test_results --test-dir test_cases_tester
    python3 generate_test_summary_csv.py --output-dir test_exp/test_1201_low_priority_v7_2_1 --test-dir test_cases/test_cases_tester_low_kpi
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Tuple

# 导入analyze_results中的函数
import sys
sys.path.insert(0, str(Path(__file__).parent))
from analyze_results import extract_kpi_config, calculate_kpi_achievement
from compare_versions import extract_constraint_config, calculate_actual_allocation, check_constraint_compliance

def load_json(filepath: Path) -> Any:
    """加载JSON文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def calculate_case_summary(case_name: str, test_dir: Path, result_dir: Path) -> Dict[str, Any]:
    """计算单个测试用例的摘要信息"""
    # 加载测试用例配置
    test_case_file = test_dir / f"{case_name}.json"
    if not test_case_file.exists():
        return None
    
    request_json = load_json(test_case_file)
    global_kpi_config, country_kpi_config = extract_kpi_config(request_json)
    constraint_config, country_kpi_priorities, country_budget_config = extract_constraint_config(request_json)
    
    # 提取KPI名称（按优先级）
    kpi_names_by_priority = defaultdict(set)  # {priority: {kpi_names}}
    
    # 从全局KPI提取
    for kpi_name, kpi_info in global_kpi_config.items():
        priority = kpi_info.get('priority', 999)
        if priority <= 6:
            kpi_names_by_priority[priority].add(kpi_name)
    
    # 从国家KPI提取
    for country_code, country_kpis in country_kpi_config.items():
        for kpi_name, kpi_info in country_kpis.items():
            priority = kpi_info.get('priority', 999)
            if priority <= 6:
                kpi_names_by_priority[priority].add(kpi_name)
    
    # 检查每个优先级的KPI名称是否所有国家都一样
    kpi_names = {}
    for priority in range(1, 7):
        if priority in kpi_names_by_priority:
            kpi_name_set = kpi_names_by_priority[priority]
            if len(kpi_name_set) == 1:
                # 所有国家都一样，取第一个
                kpi_names[f'P{priority}_KPI'] = list(kpi_name_set)[0]
            else:
                # 不一样，设为NULL
                kpi_names[f'P{priority}_KPI'] = 'NULL'
        else:
            kpi_names[f'P{priority}_KPI'] = 'NULL'
    
    # 提取限制名称（按优先级）
    constraint_names_by_priority = defaultdict(set)  # {priority: {constraint_types}}
    
    for constraint_type in ['stage', 'media', 'adType', 'marketingFunnel']:
        for constraint in constraint_config[constraint_type]:
            priority = constraint['priority']
            if priority <= 6:
                constraint_names_by_priority[priority].add(constraint_type)
    
    # 检查每个优先级的限制名称是否所有国家都一样
    constraint_names = {}
    for priority in range(1, 7):
        if priority in constraint_names_by_priority:
            constraint_type_set = constraint_names_by_priority[priority]
            if len(constraint_type_set) == 1:
                # 所有国家都一样，取第一个
                constraint_names[f'限制P{priority}_name'] = list(constraint_type_set)[0]
            else:
                # 不一样，设为NULL
                constraint_names[f'限制P{priority}_name'] = 'NULL'
        else:
            constraint_names[f'限制P{priority}_name'] = 'NULL'
    
    # 加载结果文件
    result_file = None
    for f in result_dir.glob(f"{case_name}_result_*.json"):
        result_file = f
        break
    
    if not result_file:
        return None
    
    result = load_json(result_file)
    result_data = result.get('result', {}).get('data', [])
    
    # 1. 计算国家数和总预算
    countries = set()
    total_budget = 0.0
    for row in result_data:
        region = row.get('Region') or ''
        country_code = region.split('_')[0] if region and '_' in region else (region or 'UNKNOWN')
        if country_code and country_code != 'UNKNOWN':
            countries.add(country_code)
        
        budget = float(row.get('ai_ad_type_budget', 0) or 0)
        if budget > 0:
            total_budget += budget
    
    num_countries = len(countries)
    
    # 2. 计算KPI达成率（按优先级分组）
    kpi_achievement = calculate_kpi_achievement(result_data, country_kpi_config, global_kpi_config)
    
    # 按优先级分组KPI达成率
    kpi_by_priority = defaultdict(lambda: {'achieved': 0, 'total': 0, 'total_achievement': 0.0})
    
    # 处理全局KPI
    for kpi_name, kpi_stats in kpi_achievement.get('global', {}).items():
        priority = kpi_stats.get('priority', 999)
        if priority <= 6:  # 只考虑P1-P6
            achievement = kpi_stats.get('achievement', 0.0)
            target = kpi_stats.get('target', 0.0)
            estimated = kpi_stats.get('estimated', 0.0)
            
            kpi_by_priority[priority]['total'] += 1
            kpi_by_priority[priority]['total_achievement'] += achievement
            # 如果达成率 >= 100%，算作达成
            if achievement >= 100.0:
                kpi_by_priority[priority]['achieved'] += 1
    
    # 计算每个优先级的平均达成率
    kpi_achievement_rates = {}
    for priority in range(1, 7):  # P1-P6
        if priority in kpi_by_priority:
            total = kpi_by_priority[priority]['total']
            if total > 0:
                avg_achievement = kpi_by_priority[priority]['total_achievement'] / total
                kpi_achievement_rates[f'KPI_P{priority}'] = avg_achievement / 100.0  # 转换为倍数（KPI完成量/KPI目标量）
            else:
                kpi_achievement_rates[f'KPI_P{priority}'] = 0.0
        else:
            kpi_achievement_rates[f'KPI_P{priority}'] = 0.0

    # 基于 kpiInfoBudgetConfig 的 KPI 优先级（不单独导出列，用于标记到限制P{X}_name 中）
    kpi_budget_priority = None
    if country_kpi_priorities:
        valid_priorities = [p for p in country_kpi_priorities.values() if p is not None and p != 999]
        if valid_priorities:
            unique_priorities = set(valid_priorities)
            if len(unique_priorities) == 1:
                kpi_budget_priority = list(unique_priorities)[0]
    
    # 3. 计算限制遵守率（按优先级分组），并记录匹配类型（大小匹配/容差/KPI达标）
    constraint_by_priority = defaultdict(lambda: {'compliant': 0, 'total': 0})
    # 记录每个优先级下约束的匹配方式及容差数值
    constraint_match_types_by_priority = defaultdict(set)  # {priority: {'大小匹配', '容差'}}
    constraint_range_values_by_priority = defaultdict(set)  # {priority: {rangeMatch_value}}
    
    # 计算国家预算信息（用于获取实际分配预算）
    from compare_versions import calculate_country_budgets
    country_budgets = calculate_country_budgets(result_data, request_json)
    
    for constraint_type in ['stage', 'media', 'adType', 'marketingFunnel']:
        actual_allocation = calculate_actual_allocation(result_data, constraint_type)
        
        for constraint in constraint_config[constraint_type]:
            country = constraint['country']
            expected = constraint['expected']
            actual_pct = actual_allocation.get(country, {})
            priority = constraint['priority']
            
            if priority <= 6:  # 只考虑P1-P6
                constraint_by_priority[priority]['total'] += 1
                # 记录该优先级下的匹配方式
                if constraint['consistentMatch'] == 1:
                    constraint_match_types_by_priority[priority].add('容差')
                    # 记录容差数值
                    range_match_val = constraint.get('rangeMatch')
                    if isinstance(range_match_val, (int, float)):
                        constraint_range_values_by_priority[priority].add(float(range_match_val))
                else:
                    constraint_match_types_by_priority[priority].add('大小匹配')
                
                # 获取该国家的实际分配总预算
                country_total = country_budgets['actual'].get(country, 0.0)
                
                is_compliant, _ = check_constraint_compliance(
                    expected, actual_pct,
                    constraint['consistentMatch'], constraint['rangeMatch'],
                    actual_total_budget=country_total
                )
                
                if is_compliant:
                    constraint_by_priority[priority]['compliant'] += 1
    
    # 计算每个优先级的遵守率
    constraint_compliance_rates = {}
    # 记录所有出现过的优先级
    all_priorities = set()
    for constraint_type in ['stage', 'media', 'adType', 'marketingFunnel']:
        for constraint in constraint_config[constraint_type]:
            priority = constraint['priority']
            if priority <= 6:
                all_priorities.add(priority)
    
    # 按优先级排序
    for priority in sorted(all_priorities):
        if priority in constraint_by_priority:
            total = constraint_by_priority[priority]['total']
            if total > 0:
                compliance_rate = constraint_by_priority[priority]['compliant'] / total
                constraint_compliance_rates[f'限制P{priority}'] = compliance_rate
            else:
                constraint_compliance_rates[f'限制P{priority}'] = 0.0
        else:
            constraint_compliance_rates[f'限制P{priority}'] = 0.0

    # 如果存在统一的 kpiInfoBudgetConfig.priority，则把这一优先级标记到对应的 限制PX_name 中
    if kpi_budget_priority is not None and 1 <= kpi_budget_priority <= 6:
        key = f'限制P{kpi_budget_priority}_name'
        existing = constraint_names.get(key, 'NULL')
        if existing == 'NULL' or not existing:
            constraint_names[key] = 'KPI'
        else:
            constraint_names[key] = f"{existing}+KPI"
    
    # 进一步解析 KPI 预算限制的目标达标率（rangeMatch）
    kpi_budget_threshold = None
    multi_country_config = request_json.get('multiCountryConfig', [])
    if multi_country_config:
        range_vals = []
        for country_config in multi_country_config:
            basic_info = country_config.get('basicInfo', {})
            kpi_budget_cfg = basic_info.get('kpiInfoBudgetConfig', {})
            val = kpi_budget_cfg.get('rangeMatch', None)
            if isinstance(val, (int, float)):
                range_vals.append(float(val))
        if range_vals:
            unique_vals = set(range_vals)
            if len(unique_vals) == 1:
                kpi_budget_threshold = list(unique_vals)[0]
    
    # 为每个优先级生成「限制PX_达成率/误差」说明
    constraint_match_meta = {}
    for priority in range(1, 7):
        key = f'限制P{priority}_达成率/误差'
        desc = 'NULL'
        # KPI 优先级：输出目标达标率数值（rangeMatch），如果无法确定则退化为文本
        if kpi_budget_priority is not None and priority == kpi_budget_priority:
            if kpi_budget_threshold is not None:
                desc = f"{kpi_budget_threshold:.4f}"
            else:
                desc = '目标达标率'
        else:
            match_types = constraint_match_types_by_priority.get(priority, set())
            if match_types:
                # 纯大小匹配
                if match_types == {'大小匹配'}:
                    desc = '大小匹配'
                # 只存在容差匹配：输出统一的容差数值
                elif match_types == {'容差'}:
                    range_vals = constraint_range_values_by_priority.get(priority, set())
                    if range_vals and len(range_vals) == 1:
                        desc = f"{list(range_vals)[0]:.4f}"
                    elif range_vals:
                        # 多个不同容差值
                        joined = ','.join(f"{v:.4f}" for v in sorted(range_vals))
                        desc = joined
                    else:
                        desc = '容差'
                else:
                    # 同时存在大小匹配和容差匹配的混合情况
                    desc = '+'.join(sorted(match_types))
        constraint_match_meta[key] = desc
    
    return {
        'case_name': case_name,
        'num_countries': num_countries,
        'total_budget': total_budget,
        'kpi_names': kpi_names,
        'constraint_names': constraint_names,
        'kpi_achievement_rates': kpi_achievement_rates,
        'constraint_compliance_rates': constraint_compliance_rates,
        'constraint_match_meta': constraint_match_meta,
    }

def generate_csv_report(result_dir: Path, test_dir: Path, output_file: Path):
    """生成CSV报告"""
    print(f"开始生成CSV报告...")
    print(f"结果目录: {result_dir}")
    print(f"测试用例目录: {test_dir}")
    
    # 获取所有测试用例
    test_cases = sorted([f.stem for f in test_dir.glob("*.json")])
    
    all_summaries = []
    for case_name in test_cases:
        summary = calculate_case_summary(case_name, test_dir, result_dir)
        if summary:
            all_summaries.append(summary)
            print(f"✓ 已处理: {case_name}")
        else:
            print(f"✗ 跳过: {case_name} (未找到结果文件)")
    
    if not all_summaries:
        print("错误: 没有找到任何可用的测试结果")
        return
    
    # 确定所有可能的列
    all_kpi_priorities = set()
    all_constraint_priorities = set()
    
    for summary in all_summaries:
        all_kpi_priorities.update(summary['kpi_achievement_rates'].keys())
        all_constraint_priorities.update(summary['constraint_compliance_rates'].keys())
    
    # 构建CSV列
    csv_columns = ['用例名称', '国家数', '总预算']
    
    # 添加KPI名称列（P1-P6）
    for priority in range(1, 7):
        col_name = f'P{priority}_KPI'
        csv_columns.append(col_name)
    
    # 添加限制名称列（P1-P6）及其「达成率/误差」说明列（即使没有也显示）
    for priority in range(1, 7):
        col_name_name = f'限制P{priority}_name'
        col_name_meta = f'限制P{priority}_达成率/误差'
        csv_columns.append(col_name_name)
        csv_columns.append(col_name_meta)
    
    # 添加KPI达成率列（P1-P6）
    for priority in range(1, 7):
        col_name = f'KPI_P{priority}达成率'
        csv_columns.append(col_name)
    
    # 添加限制遵守率列（P1-P6，即使没有也显示）
    for priority in range(1, 7):
        col_name = f'限制P{priority}符合率'
        csv_columns.append(col_name)
    
    # 写入CSV文件
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        
        for summary in all_summaries:
            row = {
                '用例名称': summary['case_name'],
                '国家数': summary['num_countries'],
                '总预算': f"{summary['total_budget']:.2f}",
            }
            
            # 添加KPI名称
            for priority in range(1, 7):
                col_name = f'P{priority}_KPI'
                kpi_name = summary['kpi_names'].get(col_name, 'NULL')
                row[col_name] = kpi_name
            
            # 添加限制名称（P1-P6）及其「达成率/误差」说明
            for priority in range(1, 7):
                col_name_name = f'限制P{priority}_name'
                col_name_meta = f'限制P{priority}_达成率/误差'
                constraint_name = summary['constraint_names'].get(col_name_name, 'NULL')
                desc = summary.get('constraint_match_meta', {}).get(col_name_meta, 'NULL')
                row[col_name_name] = constraint_name
                row[col_name_meta] = desc
            
            # 添加KPI达成率
            for priority in range(1, 7):
                col_name_rate_key = f'KPI_P{priority}'
                col_name = f'KPI_P{priority}达成率'
                rate = summary['kpi_achievement_rates'].get(col_name_rate_key, 0.0)
                row[col_name] = f"{rate:.4f}"  # 保留4位小数
            
            # 添加限制遵守率（P1-P6）
            for priority in range(1, 7):
                col_name_rate_key = f'限制P{priority}'
                col_name = f'限制P{priority}符合率'
                rate = summary['constraint_compliance_rates'].get(col_name_rate_key, 0.0)
                row[col_name] = f"{rate:.4f}"  # 保留4位小数
            
            writer.writerow(row)
    
    print(f"\nCSV报告已保存到: {output_file}")
    print(f"共处理 {len(all_summaries)} 个测试用例")

def main():
    parser = argparse.ArgumentParser(description='生成测试结果CSV报告')
    parser.add_argument('--output-dir', type=str, required=True,
                        help='测试结果目录 (必需)')
    parser.add_argument('--test-dir', type=str, required=True,
                        help='测试用例目录 (必需)')
    parser.add_argument('--output-file', type=str, default=None,
                        help='输出CSV文件名 (默认: {output-dir}/test_summary.csv)')
    
    args = parser.parse_args()
    
    BASE_DIR = Path("/root/zyydebug/mp_zyy/mp_generate")
    RESULT_DIR = BASE_DIR / "test_tmp" / args.output_dir
    TEST_DIR = BASE_DIR / "test_tmp" / args.test_dir
    
    if not RESULT_DIR.exists():
        print(f"错误: 结果目录不存在: {RESULT_DIR}")
        return
    
    if not TEST_DIR.exists():
        print(f"错误: 测试用例目录不存在: {TEST_DIR}")
        return
    
    if args.output_file:
        OUTPUT_FILE = Path(args.output_file)
    else:
        OUTPUT_FILE = RESULT_DIR / "test_summary.csv"
    
    generate_csv_report(RESULT_DIR, TEST_DIR, OUTPUT_FILE)

if __name__ == '__main__':
    main()

