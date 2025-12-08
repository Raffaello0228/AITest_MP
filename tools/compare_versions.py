#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用版本对比脚本
用于对比两个版本的测试结果

用法:
    python3 compare_versions.py --old-dir test_results_v1 --new-dir test_results_v2 --test-dir test_cases_tester
    python3 compare_versions.py --old-dir test_1113_v7 --new-dir test_1113_v7_1 --test-dir test_cases_tester
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any

# 导入analyze_results中的函数
sys.path.insert(0, str(Path(__file__).parent))
from analyze_results import extract_kpi_config, calculate_kpi_achievement

def load_json(filepath: Path) -> Any:
    """加载JSON文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_constraint_config(request_json: Dict) -> Dict[str, Any]:
    """提取限制条件配置"""
    constraints = {
        'stage': [],
        'media': [],
        'adType': [],
        'marketingFunnel': []
    }
    
    # 提取每个国家的KPI优先级
    country_kpi_priorities = {}
    
    # 提取国家预算配置（InterCountryAllocationConfig）
    country_budget_config = None
    brief_basic_info = request_json.get('briefBasicInfo', {})
    if brief_basic_info:
        # 从 briefBasicInfo 中提取国家预算配置
        # 注意：实际配置可能在 brief_parser 中转换为 inter_country_allocation_config
        # 这里我们尝试从可能的字段中提取
        country_budget_config = {
            'consistentMatch': brief_basic_info.get('consistentMatch', 1),
            'maxDeviation': brief_basic_info.get('maxDeviation', 0.0),
            'rangeMatch': brief_basic_info.get('rangeMatch', 1.0),
            'priority': brief_basic_info.get('countryBudgetPriority', 999)
        }
    
    multi_country_config = request_json.get('multiCountryConfig', [])
    for country_config in multi_country_config:
        country_code = country_config.get('basicInfo', {}).get('country', '')
        
        # 提取KPI优先级
        kpi_budget_config = country_config.get('basicInfo', {}).get('kpiInfoBudgetConfig', {})
        kpi_priority = kpi_budget_config.get('priority', 999)
        country_kpi_priorities[country_code] = kpi_priority
        
        # Stage限制
        stage_config = country_config.get('stageBudgetConfig', {})
        if stage_config:
            constraints['stage'].append({
                'country': country_code,
                'consistentMatch': stage_config.get('consistentMatch', 0),
                'rangeMatch': stage_config.get('rangeMatch', 0),
                'priority': stage_config.get('priority', 999),
                'expected': {s.get('nameKey', ''): float(s.get('budgetPercentage', '0%').replace('%', '')) / 100 
                            for s in country_config.get('stage', [])}
            })
        
        # Media限制
        media_config = country_config.get('mediaBudgetConfig', {})
        if media_config:
            constraints['media'].append({
                'country': country_code,
                'consistentMatch': media_config.get('consistentMatch', 0),
                'rangeMatch': media_config.get('rangeMatch', 0),
                'priority': media_config.get('priority', 999),
                'expected': {m.get('name', ''): float(m.get('budgetPercentage', '0%').replace('%', '')) / 100 
                            for m in country_config.get('media', [])}
            })
        
        # AdType限制
        ad_type_config = country_config.get('adTypeBudgetConfig', {})
        if ad_type_config:
            constraints['adType'].append({
                'country': country_code,
                'consistentMatch': ad_type_config.get('consistentMatch', 0),
                'rangeMatch': ad_type_config.get('rangeMatch', 0),
                'priority': ad_type_config.get('priority', 999),
                'expected': {}
            })
            # AdType配置比较复杂，需要从adType中提取
            for media_group in country_config.get('adType', []):
                media_name = media_group.get('name', '')
                for ad_type_group in media_group.get('adType', []):
                    ad_type_name = ad_type_group.get('adTypeName', '')
                    key = f"{media_name}_{ad_type_name}"
                    # AdType通常没有明确的百分比配置，这里先留空
        
        # MarketingFunnel限制
        funnel_config = country_config.get('marketingFunnelBudgetConfig', {})
        if funnel_config:
            constraints['marketingFunnel'].append({
                'country': country_code,
                'consistentMatch': funnel_config.get('consistentMatch', 0),
                'rangeMatch': funnel_config.get('rangeMatch', 0),
                'priority': funnel_config.get('priority', 999),
                'expected': {f.get('nameKey', ''): float(f.get('budgetPercentage', '0%').replace('%', '')) / 100 
                            for f in country_config.get('marketingFunnel', [])}
            })
    
    return constraints, country_kpi_priorities, country_budget_config

def calculate_actual_allocation(result_data: List[Dict], constraint_type: str) -> Dict[str, Dict[str, float]]:
    """计算实际分配比例（基于实际分配预算）"""
    # constraint_type: 'stage', 'media', 'adType', 'marketingFunnel'
    allocation = defaultdict(lambda: defaultdict(float))  # {country: {name: budget}}
    total_budget = defaultdict(float)  # {country: total} - 实际分配的总预算
    
    for row in result_data:
        region = row.get('Region') or ''
        country_code = region.split('_')[0] if region and '_' in region else (region or 'UNKNOWN')
        
        budget = float(row.get('ai_ad_type_budget', 0) or 0)
        if budget <= 0:
            continue
        
        total_budget[country_code] += budget  # 累计实际分配预算
        
        if constraint_type == 'stage':
            stage = row.get('stage')
            if stage:
                allocation[country_code][stage] += budget
        elif constraint_type == 'media':
            media = row.get('media')
            if media:
                allocation[country_code][media] += budget
        elif constraint_type == 'adType':
            media = row.get('media', '')
            ad_type = row.get('ad_type', '')
            if media and ad_type:
                key = f"{media}_{ad_type}"
                allocation[country_code][key] += budget
        elif constraint_type == 'marketingFunnel':
            funnel = row.get('marketing_funnel')
            if funnel:
                # 统一转换为大写以便匹配
                funnel_upper = funnel.upper()
                allocation[country_code][funnel_upper] += budget
    
    # 转换为百分比（基于实际分配预算）
    percentage_allocation = {}
    for country_code, items in allocation.items():
        total = total_budget[country_code]  # 使用实际分配的总预算
        if total > 0:
            percentage_allocation[country_code] = {
                name: budget / total for name, budget in items.items()
            }
        else:
            percentage_allocation[country_code] = {}
    
    return percentage_allocation

def calculate_country_budgets(result_data: List[Dict], request_json: Dict) -> Dict[str, Dict[str, float]]:
    """
    计算每个国家的实际分配预算和期望预算
    
    返回: {
        'actual': {country_code: actual_budget},
        'expected': {country_code: expected_budget},
        'total_global': global_total_budget
    }
    """
    # 计算实际分配预算
    actual_budgets = defaultdict(float)
    for row in result_data:
        region = row.get('Region') or ''
        country_code = region.split('_')[0] if region and '_' in region else (region or 'UNKNOWN')
        budget = float(row.get('ai_ad_type_budget', 0) or 0)
        if budget > 0:
            actual_budgets[country_code] += budget
    
    # 提取期望预算
    expected_budgets = {}
    global_total_budget = float(request_json.get('briefBasicInfo', {}).get('totalBudget', 0) or 0)
    
    multi_country_config = request_json.get('multiCountryConfig', [])
    for country_config in multi_country_config:
        country_code = country_config.get('basicInfo', {}).get('country', '')
        total_budget_str = country_config.get('basicInfo', {}).get('totalBudget', '0')
        try:
            expected_budgets[country_code] = float(total_budget_str)
        except (ValueError, TypeError):
            expected_budgets[country_code] = 0.0
    
    return {
        'actual': dict(actual_budgets),
        'expected': expected_budgets,
        'total_global': global_total_budget
    }

def check_country_budget_compliance(
    country_budgets: Dict[str, Dict[str, float]],
    country_budget_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    检查国家预算是否合法
    
    返回: {
        'compliant': bool,
        'details': {
            'violations': [...],
            'expected_ratios': {...},
            'actual_ratios': {...}
        }
    }
    """
    if not country_budget_config:
        return {'compliant': True, 'details': {'violations': []}}
    
    consistent_match = country_budget_config.get('consistentMatch', 1)
    max_deviation = country_budget_config.get('maxDeviation', 0.0)
    range_match = country_budget_config.get('rangeMatch', 1.0)
    
    actual_budgets = country_budgets['actual']
    expected_budgets = country_budgets['expected']
    global_total = country_budgets['total_global']
    
    if global_total <= 0:
        return {'compliant': True, 'details': {'violations': [], 'note': 'Global total budget is 0'}}
    
    # 计算期望比例和实际比例
    expected_ratios = {}
    actual_ratios = {}
    
    for country_code in set(list(actual_budgets.keys()) + list(expected_budgets.keys())):
        expected_budget = expected_budgets.get(country_code, 0.0)
        actual_budget = actual_budgets.get(country_code, 0.0)
        
        expected_ratios[country_code] = expected_budget / global_total if global_total > 0 else 0.0
        actual_ratios[country_code] = actual_budget / global_total if global_total > 0 else 0.0
    
    violations = []
    
    if consistent_match == 1:
        # 容差匹配：检查每个国家的实际比例与期望比例的偏差
        # 业务约定：在配置的 max_deviation 基础上，额外允许 0.5 个百分点的误差
        effective_max_deviation = (max_deviation or 0.0) + 0.005
        for country_code in expected_ratios:
            expected_ratio = expected_ratios[country_code]
            actual_ratio = actual_ratios.get(country_code, 0.0)
            abs_error = abs(actual_ratio - expected_ratio)

            if abs_error > effective_max_deviation + 1e-6:  # 允许小的数值误差
                violations.append({
                    'country': country_code,
                    'expected_ratio': expected_ratio,
                    'actual_ratio': actual_ratio,
                    'error': abs_error,
                    'max_deviation': max_deviation,
                    'type': 'tolerance_violation'
                })
    else:
        # 大小匹配：检查大小关系是否一致
        # 按期望比例排序
        expected_sorted = sorted(expected_ratios.items(), key=lambda x: x[1], reverse=True)
        actual_sorted = sorted(actual_ratios.items(), key=lambda x: x[1], reverse=True)
        
        # 检查顺序是否一致
        expected_countries = [c for c, _ in expected_sorted if expected_ratios[c] > 0]
        actual_countries = [c for c, _ in actual_sorted if actual_ratios[c] > 0]
        
        # 检查顺序关系
        for i in range(len(expected_countries) - 1):
            country1 = expected_countries[i]
            country2 = expected_countries[i + 1]
            
            if country1 in actual_ratios and country2 in actual_ratios:
                if actual_ratios[country1] <= actual_ratios[country2] + 1e-6:
                    violations.append({
                        'country1': country1,
                        'country2': country2,
                        'expected_order': f"{country1} > {country2}",
                        'expected_ratio1': expected_ratios[country1],
                        'expected_ratio2': expected_ratios[country2],
                        'actual_ratio1': actual_ratios[country1],
                        'actual_ratio2': actual_ratios[country2],
                        'type': 'order_violation'
                    })
        
        # 检查预算达成率（range_match）
        for country_code in expected_budgets:
            expected_budget = expected_budgets[country_code]
            actual_budget = actual_budgets.get(country_code, 0.0)
            
            if expected_budget > 0:
                achievement_ratio = actual_budget / expected_budget
                if achievement_ratio < range_match - 1e-6:
                    violations.append({
                        'country': country_code,
                        'expected_budget': expected_budget,
                        'actual_budget': actual_budget,
                        'achievement_ratio': achievement_ratio,
                        'required_range_match': range_match,
                        'type': 'achievement_violation'
                    })
    
    return {
        'compliant': len(violations) == 0,
        'details': {
            'violations': violations,
            'expected_ratios': expected_ratios,
            'actual_ratios': actual_ratios
        }
    }

def check_constraint_compliance(expected: Dict[str, float], actual: Dict[str, float],
                                consistent_match: int, range_match: float,
                                actual_total_budget: float = None) -> tuple:
    """
    检查限制条件是否遵守，返回(是否遵守, 详细信息)
    
    Args:
        expected: 期望比例（相对于输入国家预算）
        actual: 实际比例（相对于实际分配预算）
        consistent_match: 匹配模式（1=容差，0=大小）
        range_match: 容差值或达标率
        actual_total_budget: 实际分配的总预算（用于计算偏差占实际预算的比例）
    """
    if not expected or not actual:
        return True, {}  # 如果没有配置，认为遵守
    
    details = {
        'violations': [],
        'expected': expected.copy(),
        'actual': actual.copy()
    }
    
    # 容差限制：consistent_match == 1 时使用 rangeMatch 作为容差
    # 业务约定：在配置的 range_match 基础上，额外允许 0.5 个百分点的误差
    if consistent_match == 1:
        for name, expected_pct in expected.items():
            actual_pct = actual.get(name, 0)
            abs_error = abs(actual_pct - expected_pct)
            # 偏差现在基于实际分配预算的比例（actual_pct 已经是相对于实际分配预算的）
            effective_tolerance = (range_match or 0.0) + 0.005
            if abs_error > effective_tolerance + 1e-6:  # 再允许极小数值误差
                # 计算偏差占实际分配预算的比例
                error_ratio = abs_error
                if actual_total_budget and actual_total_budget > 0:
                    # 如果提供了实际总预算，可以计算绝对偏差
                    absolute_error = abs_error * actual_total_budget
                    error_ratio = absolute_error / actual_total_budget
                
                details['violations'].append({
                    'name': name,
                    'expected': expected_pct,
                    'actual': actual_pct,
                    'error': abs_error,  # 相对误差（比例）
                    'error_ratio': error_ratio,  # 偏差占实际分配预算的比例
                    'rangeMatch': range_match
                })
        return len(details['violations']) == 0, details
    
    # 大小限制：consistent_match != 1 时保持大小关系（添加关系约束）
    if consistent_match != 1:
        # 按期望值排序
        expected_sorted = sorted(expected.items(), key=lambda x: x[1], reverse=True)
        actual_sorted = sorted(actual.items(), key=lambda x: x[1], reverse=True)
        
        # 检查大小关系是否一致
        expected_names = [name for name, _ in expected_sorted]
        actual_names = [name for name, _ in actual_sorted if name in expected_names]
        
        # 只检查在期望中存在的项的大小关系
        if len(actual_names) < len(expected_names):
            details['violations'].append({
                'type': 'missing_items',
                'expected': expected_names,
                'actual': actual_names
            })
            return False, details
        
        # 检查顺序是否一致
        violations = []
        for i in range(len(expected_names) - 1):
            if expected_names[i] not in actual_names or expected_names[i+1] not in actual_names:
                continue
            expected_idx = actual_names.index(expected_names[i])
            next_idx = actual_names.index(expected_names[i+1])
            if expected_idx >= next_idx:
                # 获取期望和实际的比例值
                item1_name = expected_names[i]
                item2_name = expected_names[i+1]
                expected_pct1 = expected.get(item1_name, 0)
                expected_pct2 = expected.get(item2_name, 0)
                actual_pct1 = actual.get(item1_name, 0)
                actual_pct2 = actual.get(item2_name, 0)
                
                violations.append({
                    'type': 'order_violation',
                    'item1': item1_name,
                    'item2': item2_name,
                    'expected_order': f"{item1_name} > {item2_name}",
                    'actual_order': f"{actual_names[expected_idx]} >= {actual_names[next_idx]}",
                    'expected_pct1': expected_pct1,
                    'expected_pct2': expected_pct2,
                    'actual_pct1': actual_pct1,
                    'actual_pct2': actual_pct2
                })
        
        if violations:
            details['violations'] = violations
            return False, details
        
        return True, details
    
    return True, details

def compare_versions(old_dir: Path, new_dir: Path, test_dir: Path, output_dir: Path):
    """对比两个版本的结果"""
    print("开始对比分析...")
    
    # 获取所有测试用例
    test_cases = sorted([f.stem for f in test_dir.glob("*.json")])
    
    all_comparisons = []
    
    for case_name in test_cases:
        # 加载测试用例配置
        test_case_file = test_dir / f"{case_name}.json"
        if not test_case_file.exists():
            continue
        
        request_json = load_json(test_case_file)
        global_kpi_config, country_kpi_config = extract_kpi_config(request_json)
        constraint_config, country_kpi_priorities, country_budget_config = extract_constraint_config(request_json)
        
        # 加载两个版本的结果
        old_result_file = None
        new_result_file = None
        
        for f in old_dir.glob(f"{case_name}_result_*.json"):
            old_result_file = f
            break
        
        for f in new_dir.glob(f"{case_name}_result_*.json"):
            new_result_file = f
            break
        
        if not old_result_file or not new_result_file:
            continue
        
        old_result = load_json(old_result_file)
        new_result = load_json(new_result_file)
        
        old_data = old_result.get('result', {}).get('data', [])
        new_data = new_result.get('result', {}).get('data', [])
        
        old_kpi = calculate_kpi_achievement(old_data, country_kpi_config, global_kpi_config)
        new_kpi = calculate_kpi_achievement(new_data, country_kpi_config, global_kpi_config)
        
        # 计算国家预算合法性
        old_country_budgets = calculate_country_budgets(old_data, request_json)
        new_country_budgets = calculate_country_budgets(new_data, request_json)
        
        old_country_budget_compliance = check_country_budget_compliance(old_country_budgets, country_budget_config)
        new_country_budget_compliance = check_country_budget_compliance(new_country_budgets, country_budget_config)
        
        # 计算限制遵守情况
        old_constraints = {}
        new_constraints = {}
        for constraint_type in ['stage', 'media', 'adType', 'marketingFunnel']:
            old_actual = calculate_actual_allocation(old_data, constraint_type)
            new_actual = calculate_actual_allocation(new_data, constraint_type)
            
            old_compliance = []
            new_compliance = []
            
            for constraint in constraint_config[constraint_type]:
                country = constraint['country']
                expected = constraint['expected']
                old_actual_pct = old_actual.get(country, {})
                new_actual_pct = new_actual.get(country, {})
                
                # 获取该国家的实际分配总预算
                old_country_total = old_country_budgets['actual'].get(country, 0.0)
                new_country_total = new_country_budgets['actual'].get(country, 0.0)
                
                old_ok, old_details = check_constraint_compliance(
                    expected, old_actual_pct, 
                    constraint['consistentMatch'], constraint['rangeMatch'],
                    actual_total_budget=old_country_total
                )
                new_ok, new_details = check_constraint_compliance(
                    expected, new_actual_pct,
                    constraint['consistentMatch'], constraint['rangeMatch'],
                    actual_total_budget=new_country_total
                )
                
                old_compliance.append({
                    'country': country,
                    'type': constraint_type,
                    'compliant': old_ok,
                    'priority': constraint['priority'],
                    'details': old_details
                })
                new_compliance.append({
                    'country': country,
                    'type': constraint_type,
                    'compliant': new_ok,
                    'priority': constraint['priority'],
                    'details': new_details
                })
            
            old_constraints[constraint_type] = old_compliance
            new_constraints[constraint_type] = new_compliance
        
        all_comparisons.append({
            'case_name': case_name,
            'old': {
                'kpi': old_kpi,
                'constraints': old_constraints,
                'country_budget': {
                    'budgets': old_country_budgets,
                    'compliance': old_country_budget_compliance
                }
            },
            'new': {
                'kpi': new_kpi,
                'constraints': new_constraints,
                'country_budget': {
                    'budgets': new_country_budgets,
                    'compliance': new_country_budget_compliance
                }
            },
            'global_kpi_config': global_kpi_config,
            'country_kpi_config': country_kpi_config,
            'country_kpi_priorities': country_kpi_priorities,
            'country_budget_config': country_budget_config
        })
        
        print(f"✓ 已对比: {case_name}")
    
    # 生成对比报告
    generate_comparison_report(all_comparisons, output_dir)
    
    # 保存数据
    data_file = output_dir / "comparison_data.json"
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(all_comparisons, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n对比数据已保存到: {data_file}")

def generate_comparison_report(all_comparisons: List[Dict], output_dir: Path):
    """生成对比报告"""
    report = []
    report.append("="*80)
    report.append("版本对比分析报告")
    report.append("="*80)
    report.append("")
    
    # 全局KPI汇总对比
    global_kpi_summary = defaultdict(lambda: {
        'old_achievements': [],
        'new_achievements': [],
        'old_achieved_count': 0,
        'new_achieved_count': 0,
        'total_count': 0
    })
    
    for comp in all_comparisons:
        old_global = comp['old']['kpi']['global']
        new_global = comp['new']['kpi']['global']
        
        all_kpis = set(list(old_global.keys()) + list(new_global.keys()))
        for kpi_name in all_kpis:
            old_ach = old_global.get(kpi_name, {}).get('achievement', 0)
            new_ach = new_global.get(kpi_name, {}).get('achievement', 0)
            
            global_kpi_summary[kpi_name]['old_achievements'].append(old_ach)
            global_kpi_summary[kpi_name]['new_achievements'].append(new_ach)
            global_kpi_summary[kpi_name]['total_count'] += 1
            
            if old_ach >= 100:
                global_kpi_summary[kpi_name]['old_achieved_count'] += 1
            if new_ach >= 100:
                global_kpi_summary[kpi_name]['new_achieved_count'] += 1
    
    report.append("## 全局KPI达成率对比")
    report.append("-"*80)
    report.append(f"{'KPI名称':<20} {'旧版达成成功率':<20} {'旧版平均达成率':<20} {'新版达成成功率':<20} {'新版平均达成率':<20} {'改善':<15}")
    report.append("-"*80)
    
    for kpi_name in sorted(global_kpi_summary.keys()):
        stats = global_kpi_summary[kpi_name]
        old_success = (stats['old_achieved_count'] / stats['total_count'] * 100) if stats['total_count'] > 0 else 0
        old_avg = sum(stats['old_achievements']) / len(stats['old_achievements']) if stats['old_achievements'] else 0
        new_success = (stats['new_achieved_count'] / stats['total_count'] * 100) if stats['total_count'] > 0 else 0
        new_avg = sum(stats['new_achievements']) / len(stats['new_achievements']) if stats['new_achievements'] else 0
        improvement = new_avg - old_avg
        
        report.append(f"{kpi_name:<20} {old_success:>19.1f}% {old_avg:>19.1f}% {new_success:>19.1f}% {new_avg:>19.1f}% {improvement:>+14.1f}%")
    
    # 按优先级对比全局KPI达成率
    report.append("\n" + "="*80)
    report.append("## 按优先级对比全局KPI达成率")
    report.append("="*80)
    
    priority_global_kpi = defaultdict(lambda: {
        'old_achievements': [],
        'new_achievements': [],
        'old_achieved_count': 0,
        'new_achieved_count': 0,
        'total_count': 0,
        'ratio_list': []  # 新版/旧版达成率比例
    })
    
    for comp in all_comparisons:
        global_kpi_config = comp.get('global_kpi_config', {})
        old_global = comp['old']['kpi']['global']
        new_global = comp['new']['kpi']['global']
        
        for kpi_name, kpi_info in global_kpi_config.items():
            priority = kpi_info.get('priority', 999)
            old_ach = old_global.get(kpi_name, {}).get('achievement', 0)
            new_ach = new_global.get(kpi_name, {}).get('achievement', 0)
            
            priority_global_kpi[priority]['old_achievements'].append(old_ach)
            priority_global_kpi[priority]['new_achievements'].append(new_ach)
            priority_global_kpi[priority]['total_count'] += 1
            
            if old_ach >= 100:
                priority_global_kpi[priority]['old_achieved_count'] += 1
            if new_ach >= 100:
                priority_global_kpi[priority]['new_achieved_count'] += 1
            
            # 计算新版/旧版达成率比例（逐case计算）
            if old_ach > 0:
                ratio = new_ach / old_ach
                priority_global_kpi[priority]['ratio_list'].append(ratio)
    
    report.append("-"*80)
    report.append(f"{'KPI优先级':<15} {'新版/旧版比例':<20} {'旧版达成成功率':<20} {'旧版平均达成率':<20} {'新版达成成功率':<20} {'新版平均达成率':<20} {'改善':<15}")
    report.append("-"*80)
    
    for priority in sorted(priority_global_kpi.keys()):
        stats = priority_global_kpi[priority]
        old_success = (stats['old_achieved_count'] / stats['total_count'] * 100) if stats['total_count'] > 0 else 0
        old_avg = sum(stats['old_achievements']) / len(stats['old_achievements']) if stats['old_achievements'] else 0
        new_success = (stats['new_achieved_count'] / stats['total_count'] * 100) if stats['total_count'] > 0 else 0
        new_avg = sum(stats['new_achievements']) / len(stats['new_achievements']) if stats['new_achievements'] else 0
        improvement = new_avg - old_avg
        avg_ratio = sum(stats['ratio_list']) / len(stats['ratio_list']) * 100 if stats['ratio_list'] else 100.0
        
        report.append(f"{priority:<15} {avg_ratio:>19.1f}% {old_success:>19.1f}% {old_avg:>19.1f}% {new_success:>19.1f}% {new_avg:>19.1f}% {improvement:>+14.1f}%")
    
    # 按优先级对比国家KPI达成率
    report.append("\n" + "="*80)
    report.append("## 按优先级对比国家KPI达成率")
    report.append("="*80)
    
    priority_country_kpi = defaultdict(lambda: {
        'old_achievements': [],
        'new_achievements': [],
        'old_achieved_count': 0,
        'new_achieved_count': 0,
        'total_count': 0,
        'ratio_list': []  # 新版/旧版达成率比例
    })
    
    for comp in all_comparisons:
        country_kpi_config = comp.get('country_kpi_config', {})
        old_country = comp['old']['kpi']['country']
        new_country = comp['new']['kpi']['country']
        
        for country_code, country_kpis in country_kpi_config.items():
            for kpi_name, kpi_info in country_kpis.items():
                priority = kpi_info.get('priority', 999)
                old_ach = old_country.get(country_code, {}).get(kpi_name, {}).get('achievement', 0)
                new_ach = new_country.get(country_code, {}).get(kpi_name, {}).get('achievement', 0)
                
                priority_country_kpi[priority]['old_achievements'].append(old_ach)
                priority_country_kpi[priority]['new_achievements'].append(new_ach)
                priority_country_kpi[priority]['total_count'] += 1
                
                if old_ach >= 100:
                    priority_country_kpi[priority]['old_achieved_count'] += 1
                if new_ach >= 100:
                    priority_country_kpi[priority]['new_achieved_count'] += 1
                
                # 计算新版/旧版达成率比例（逐case计算）
                if old_ach > 0:
                    ratio = new_ach / old_ach
                    priority_country_kpi[priority]['ratio_list'].append(ratio)
    
    report.append("-"*80)
    report.append(f"{'KPI优先级':<15} {'新版/旧版比例':<20} {'旧版达成成功率':<20} {'旧版平均达成率':<20} {'新版达成成功率':<20} {'新版平均达成率':<20} {'改善':<15}")
    report.append("-"*80)
    
    for priority in sorted(priority_country_kpi.keys()):
        stats = priority_country_kpi[priority]
        old_success = (stats['old_achieved_count'] / stats['total_count'] * 100) if stats['total_count'] > 0 else 0
        old_avg = sum(stats['old_achievements']) / len(stats['old_achievements']) if stats['old_achievements'] else 0
        new_success = (stats['new_achieved_count'] / stats['total_count'] * 100) if stats['total_count'] > 0 else 0
        new_avg = sum(stats['new_achievements']) / len(stats['new_achievements']) if stats['new_achievements'] else 0
        improvement = new_avg - old_avg
        avg_ratio = sum(stats['ratio_list']) / len(stats['ratio_list']) * 100 if stats['ratio_list'] else 100.0
        
        report.append(f"{priority:<15} {avg_ratio:>19.1f}% {old_success:>19.1f}% {old_avg:>19.1f}% {new_success:>19.1f}% {new_avg:>19.1f}% {improvement:>+14.1f}%")
    
    # 限制条件遵守率对比
    report.append("\n" + "="*80)
    report.append("## 限制条件遵守率对比")
    report.append("="*80)
    
    constraint_summary = defaultdict(lambda: {
        'old_compliant_count': 0,
        'new_compliant_count': 0,
        'total_count': 0
    })
    
    for comp in all_comparisons:
        old_constraints = comp['old']['constraints']
        new_constraints = comp['new']['constraints']
        
        for constraint_type in ['stage', 'media', 'adType', 'marketingFunnel']:
            old_list = old_constraints.get(constraint_type, [])
            new_list = new_constraints.get(constraint_type, [])
            
            for old_item, new_item in zip(old_list, new_list):
                key = f"{constraint_type}_P{old_item.get('priority', 999)}"
                constraint_summary[key]['total_count'] += 1
                if old_item.get('compliant', False):
                    constraint_summary[key]['old_compliant_count'] += 1
                if new_item.get('compliant', False):
                    constraint_summary[key]['new_compliant_count'] += 1
    
    report.append("-"*80)
    report.append(f"{'限制类型':<20} {'优先级':<10} {'旧版遵守率':<20} {'新版遵守率':<20} {'改善':<15}")
    report.append("-"*80)
    
    for key in sorted(constraint_summary.keys()):
        stats = constraint_summary[key]
        old_rate = (stats['old_compliant_count'] / stats['total_count'] * 100) if stats['total_count'] > 0 else 0
        new_rate = (stats['new_compliant_count'] / stats['total_count'] * 100) if stats['total_count'] > 0 else 0
        improvement = new_rate - old_rate
        
        parts = key.split('_')
        constraint_type = parts[0]
        priority = parts[1] if len(parts) > 1 else 'N/A'
        
        report.append(f"{constraint_type:<20} {priority:<10} {old_rate:>19.1f}% {new_rate:>19.1f}% {improvement:>+14.1f}%")
    
    # 未遵守限制条件的详细列表
    report.append("\n" + "="*80)
    report.append("## 未遵守限制条件详细列表")
    report.append("="*80)
    
    # 旧版未遵守的情况
    report.append("\n### 旧版未遵守限制条件")
    report.append("-"*80)
    old_violations_found = False
    for comp in all_comparisons:
        case_name = comp['case_name']
        old_constraints = comp['old']['constraints']
        
        for constraint_type in ['stage', 'media', 'adType', 'marketingFunnel']:
            for item in old_constraints.get(constraint_type, []):
                if not item.get('compliant', False):
                    old_violations_found = True
                    details = item.get('details', {})
                    violations = details.get('violations', [])
                    
                    report.append(f"\n用例: {case_name}")
                    report.append(f"  限制类型: {constraint_type}")
                    report.append(f"  国家: {item.get('country', 'N/A')}")
                    report.append(f"  优先级: {item.get('priority', 'N/A')}")
                    
                    if violations:
                        for v in violations:
                            if 'name' in v:
                                # 容差限制违规
                                report.append(f"    违规项: {v['name']}")
                                report.append(f"      期望值: {v['expected']:.2%}")
                                report.append(f"      实际值: {v['actual']:.2%}")
                                report.append(f"      偏差: {v['error']:.2%}")
                                report.append(f"      允许偏差: {v['rangeMatch']:.2%}")
                            elif 'type' in v:
                                # 大小限制违规
                                if v['type'] == 'order_violation':
                                    report.append(f"    顺序违规: {v['item1']} 应该大于 {v['item2']}")
                                    report.append(f"      期望顺序: {v['expected_order']}")
                                    if 'expected_pct1' in v and 'expected_pct2' in v:
                                        report.append(f"      期望比例: {v['item1']}={v['expected_pct1']:.2%}, {v['item2']}={v['expected_pct2']:.2%}")
                                    report.append(f"      实际顺序: {v['actual_order']}")
                                    if 'actual_pct1' in v and 'actual_pct2' in v:
                                        report.append(f"      实际比例: {v['item1']}={v['actual_pct1']:.2%}, {v['item2']}={v['actual_pct2']:.2%}")
                                elif v['type'] == 'missing_items':
                                    report.append(f"    缺少项: 期望 {v['expected']}, 实际 {v['actual']}")
    
    if not old_violations_found:
        report.append("  无未遵守的限制条件")
    
    # 新版未遵守的情况
    report.append("\n\n### 新版未遵守限制条件")
    report.append("-"*80)
    new_violations_found = False
    for comp in all_comparisons:
        case_name = comp['case_name']
        new_constraints = comp['new']['constraints']
        
        for constraint_type in ['stage', 'media', 'adType', 'marketingFunnel']:
            for item in new_constraints.get(constraint_type, []):
                if not item.get('compliant', False):
                    new_violations_found = True
                    details = item.get('details', {})
                    violations = details.get('violations', [])
                    
                    report.append(f"\n用例: {case_name}")
                    report.append(f"  限制类型: {constraint_type}")
                    report.append(f"  国家: {item.get('country', 'N/A')}")
                    report.append(f"  优先级: {item.get('priority', 'N/A')}")
                    
                    if violations:
                        for v in violations:
                            if 'name' in v:
                                # 容差限制违规
                                report.append(f"    违规项: {v['name']}")
                                report.append(f"      期望值: {v['expected']:.2%}")
                                report.append(f"      实际值: {v['actual']:.2%}")
                                report.append(f"      偏差: {v['error']:.2%}")
                                report.append(f"      允许偏差: {v['rangeMatch']:.2%}")
                            elif 'type' in v:
                                # 大小限制违规
                                if v['type'] == 'order_violation':
                                    report.append(f"    顺序违规: {v['item1']} 应该大于 {v['item2']}")
                                    report.append(f"      期望顺序: {v['expected_order']}")
                                    if 'expected_pct1' in v and 'expected_pct2' in v:
                                        report.append(f"      期望比例: {v['item1']}={v['expected_pct1']:.2%}, {v['item2']}={v['expected_pct2']:.2%}")
                                    report.append(f"      实际顺序: {v['actual_order']}")
                                    if 'actual_pct1' in v and 'actual_pct2' in v:
                                        report.append(f"      实际比例: {v['item1']}={v['actual_pct1']:.2%}, {v['item2']}={v['actual_pct2']:.2%}")
                                elif v['type'] == 'missing_items':
                                    report.append(f"    缺少项: 期望 {v['expected']}, 实际 {v['actual']}")
    
    if not new_violations_found:
        report.append("  无未遵守的限制条件")
    
    # 高于KPI优先级的限制条件遵守率对比
    report.append("\n" + "="*80)
    report.append("## 高于KPI优先级的限制条件遵守率对比")
    report.append("="*80)
    report.append("说明: 分析优先级高于KPI的限制条件（priority < KPI priority）的遵守情况")
    report.append("")
    
    higher_priority_summary = defaultdict(lambda: {
        'old_compliant_count': 0,
        'new_compliant_count': 0,
        'total_count': 0,
        'old_violations': [],
        'new_violations': []
    })
    
    for comp in all_comparisons:
        case_name = comp['case_name']
        country_kpi_priorities = comp.get('country_kpi_priorities', {})
        old_constraints = comp['old']['constraints']
        new_constraints = comp['new']['constraints']
        
        for constraint_type in ['stage', 'media', 'adType', 'marketingFunnel']:
            old_list = old_constraints.get(constraint_type, [])
            new_list = new_constraints.get(constraint_type, [])
            
            for old_item, new_item in zip(old_list, new_list):
                country = old_item.get('country', '')
                constraint_priority = old_item.get('priority', 999)
                kpi_priority = country_kpi_priorities.get(country, 999)
                
                # 只统计优先级高于KPI的限制条件（priority < kpi_priority）
                if constraint_priority < kpi_priority:
                    key = f"{constraint_type}_P{constraint_priority}"
                    higher_priority_summary[key]['total_count'] += 1
                    
                    if old_item.get('compliant', False):
                        higher_priority_summary[key]['old_compliant_count'] += 1
                    else:
                        higher_priority_summary[key]['old_violations'].append({
                            'case': case_name,
                            'country': country,
                            'type': constraint_type,
                            'priority': constraint_priority,
                            'details': old_item.get('details', {})
                        })
                    
                    if new_item.get('compliant', False):
                        higher_priority_summary[key]['new_compliant_count'] += 1
                    else:
                        higher_priority_summary[key]['new_violations'].append({
                            'case': case_name,
                            'country': country,
                            'type': constraint_type,
                            'priority': constraint_priority,
                            'details': new_item.get('details', {})
                        })
    
    report.append("-"*80)
    report.append(f"{'限制类型':<20} {'优先级':<10} {'旧版遵守率':<20} {'新版遵守率':<20} {'改善':<15}")
    report.append("-"*80)
    
    for key in sorted(higher_priority_summary.keys()):
        stats = higher_priority_summary[key]
        old_rate = (stats['old_compliant_count'] / stats['total_count'] * 100) if stats['total_count'] > 0 else 0
        new_rate = (stats['new_compliant_count'] / stats['total_count'] * 100) if stats['total_count'] > 0 else 0
        improvement = new_rate - old_rate
        
        parts = key.split('_')
        constraint_type = parts[0]
        priority = parts[1] if len(parts) > 1 else 'N/A'
        
        report.append(f"{constraint_type:<20} {priority:<10} {old_rate:>19.1f}% {new_rate:>19.1f}% {improvement:>+14.1f}%")
    
    # 高于KPI优先级的限制条件未遵守详细列表
    report.append("\n" + "="*80)
    report.append("## 高于KPI优先级的限制条件未遵守详细列表")
    report.append("="*80)
    
    report.append("\n### 旧版未遵守限制条件（优先级高于KPI）")
    report.append("-"*80)
    old_higher_violations_found = False
    for key, stats in sorted(higher_priority_summary.items()):
        if stats['old_violations']:
            old_higher_violations_found = True
            parts = key.split('_')
            constraint_type = parts[0]
            priority = parts[1] if len(parts) > 1 else 'N/A'
            report.append(f"\n{constraint_type} (Priority {priority}):")
            for violation in stats['old_violations']:
                report.append(f"  用例: {violation['case']}, 国家: {violation['country']}")
                details = violation.get('details', {})
                violations_list = details.get('violations', [])
                if violations_list:
                    for v in violations_list:
                        if 'name' in v:
                            report.append(f"    违规项: {v['name']}")
                            report.append(f"      期望值: {v['expected']:.2%}")
                            report.append(f"      实际值: {v['actual']:.2%}")
                            report.append(f"      偏差: {v['error']:.2%}")
    
    if not old_higher_violations_found:
        report.append("  无未遵守的限制条件")
    
    report.append("\n\n### 新版未遵守限制条件（优先级高于KPI）")
    report.append("-"*80)
    new_higher_violations_found = False
    for key, stats in sorted(higher_priority_summary.items()):
        if stats['new_violations']:
            new_higher_violations_found = True
            parts = key.split('_')
            constraint_type = parts[0]
            priority = parts[1] if len(parts) > 1 else 'N/A'
            report.append(f"\n{constraint_type} (Priority {priority}):")
            for violation in stats['new_violations']:
                report.append(f"  用例: {violation['case']}, 国家: {violation['country']}")
                details = violation.get('details', {})
                violations_list = details.get('violations', [])
                if violations_list:
                    for v in violations_list:
                        if 'name' in v:
                            report.append(f"    违规项: {v['name']}")
                            report.append(f"      期望值: {v['expected']:.2%}")
                            report.append(f"      实际值: {v['actual']:.2%}")
                            report.append(f"      偏差: {v['error']:.2%}")
    
    if not new_higher_violations_found:
        report.append("  无未遵守的限制条件")
    
    # 国家预算合法性检测
    report.append("\n" + "="*80)
    report.append("## 国家预算合法性检测")
    report.append("="*80)
    report.append("说明: 检测多国家预算分配是否符合配置要求（容差匹配或大小匹配）")
    report.append("")
    
    country_budget_summary = {
        'old_compliant_count': 0,
        'new_compliant_count': 0,
        'total_count': 0,
        'old_violations': [],
        'new_violations': []
    }
    
    for comp in all_comparisons:
        case_name = comp['case_name']
        old_country_budget = comp['old']['country_budget']
        new_country_budget = comp['new']['country_budget']
        
        country_budget_summary['total_count'] += 1
        
        if old_country_budget['compliance']['compliant']:
            country_budget_summary['old_compliant_count'] += 1
        else:
            country_budget_summary['old_violations'].append({
                'case': case_name,
                'details': old_country_budget['compliance']['details']
            })
        
        if new_country_budget['compliance']['compliant']:
            country_budget_summary['new_compliant_count'] += 1
        else:
            country_budget_summary['new_violations'].append({
                'case': case_name,
                'details': new_country_budget['compliance']['details']
            })
    
    report.append("-"*80)
    report.append(f"{'版本':<20} {'合法用例数':<20} {'总用例数':<20} {'合法率':<20}")
    report.append("-"*80)
    
    old_rate = (country_budget_summary['old_compliant_count'] / country_budget_summary['total_count'] * 100) if country_budget_summary['total_count'] > 0 else 0
    new_rate = (country_budget_summary['new_compliant_count'] / country_budget_summary['total_count'] * 100) if country_budget_summary['total_count'] > 0 else 0
    
    report.append(f"{'旧版':<20} {country_budget_summary['old_compliant_count']:<20} {country_budget_summary['total_count']:<20} {old_rate:>19.1f}%")
    report.append(f"{'新版':<20} {country_budget_summary['new_compliant_count']:<20} {country_budget_summary['total_count']:<20} {new_rate:>19.1f}%")
    
    # 详细违规列表
    if country_budget_summary['old_violations']:
        report.append("\n### 旧版国家预算违规详情")
        report.append("-"*80)
        for violation in country_budget_summary['old_violations']:
            report.append(f"\n用例: {violation['case']}")
            details = violation['details']
            violations_list = details.get('violations', [])
            for v in violations_list:
                if v.get('type') == 'tolerance_violation':
                    report.append(f"  国家: {v['country']}")
                    report.append(f"    期望比例: {v['expected_ratio']:.4%}")
                    report.append(f"    实际比例: {v['actual_ratio']:.4%}")
                    report.append(f"    偏差: {v['error']:.4%}")
                    report.append(f"    允许偏差: {v['max_deviation']:.4%}")
                elif v.get('type') == 'order_violation':
                    report.append(f"  顺序违规: {v['country1']} 应该大于 {v['country2']}")
                    report.append(f"    期望: {v['country1']}={v['expected_ratio1']:.4%}, {v['country2']}={v['expected_ratio2']:.4%}")
                    report.append(f"    实际: {v['country1']}={v['actual_ratio1']:.4%}, {v['country2']}={v['actual_ratio2']:.4%}")
                elif v.get('type') == 'achievement_violation':
                    report.append(f"  国家: {v['country']}")
                    report.append(f"    期望预算: {v['expected_budget']:.2f}")
                    report.append(f"    实际预算: {v['actual_budget']:.2f}")
                    report.append(f"    达成率: {v['achievement_ratio']:.4%}")
                    report.append(f"    要求达成率: {v['required_range_match']:.4%}")
    
    if country_budget_summary['new_violations']:
        report.append("\n### 新版国家预算违规详情")
        report.append("-"*80)
        for violation in country_budget_summary['new_violations']:
            report.append(f"\n用例: {violation['case']}")
            details = violation['details']
            violations_list = details.get('violations', [])
            for v in violations_list:
                if v.get('type') == 'tolerance_violation':
                    report.append(f"  国家: {v['country']}")
                    report.append(f"    期望比例: {v['expected_ratio']:.4%}")
                    report.append(f"    实际比例: {v['actual_ratio']:.4%}")
                    report.append(f"    偏差: {v['error']:.4%}")
                    report.append(f"    允许偏差: {v['max_deviation']:.4%}")
                elif v.get('type') == 'order_violation':
                    report.append(f"  顺序违规: {v['country1']} 应该大于 {v['country2']}")
                    report.append(f"    期望: {v['country1']}={v['expected_ratio1']:.4%}, {v['country2']}={v['expected_ratio2']:.4%}")
                    report.append(f"    实际: {v['country1']}={v['actual_ratio1']:.4%}, {v['country2']}={v['actual_ratio2']:.4%}")
                elif v.get('type') == 'achievement_violation':
                    report.append(f"  国家: {v['country']}")
                    report.append(f"    期望预算: {v['expected_budget']:.2f}")
                    report.append(f"    实际预算: {v['actual_budget']:.2f}")
                    report.append(f"    达成率: {v['achievement_ratio']:.4%}")
                    report.append(f"    要求达成率: {v['required_range_match']:.4%}")
    
    if not country_budget_summary['old_violations'] and not country_budget_summary['new_violations']:
        report.append("\n  所有用例的国家预算分配均合法")
    
    # 逐用例对比
    report.append("\n" + "="*80)
    report.append("逐用例KPI达成率对比")
    report.append("="*80)
    
    for comp in all_comparisons:
        case_name = comp['case_name']
        old_global = comp['old']['kpi']['global']
        new_global = comp['new']['kpi']['global']
        
        report.append(f"\n## 用例: {case_name}")
        report.append("-"*80)
        report.append(f"{'KPI名称':<20} {'旧版达成率':<20} {'新版达成率':<20} {'变化':<15}")
        report.append("-"*80)
        
        all_kpis = sorted(set(list(old_global.keys()) + list(new_global.keys())))
        for kpi_name in all_kpis:
            old_ach = old_global.get(kpi_name, {}).get('achievement', 0)
            new_ach = new_global.get(kpi_name, {}).get('achievement', 0)
            diff = new_ach - old_ach
            report.append(f"{kpi_name:<20} {old_ach:>19.2f}% {new_ach:>19.2f}% {diff:>+14.2f}%")
    
    # 保存报告
    report_file = output_dir / "comparison_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print(f"对比报告已保存到: {report_file}")

def main():
    parser = argparse.ArgumentParser(description='对比两个版本的测试结果')
    parser.add_argument('--old-dir', type=str, required=True,
                        help='旧版本结果目录 (必需)')
    parser.add_argument('--new-dir', type=str, required=True,
                        help='新版本结果目录 (必需)')
    parser.add_argument('--test-dir', type=str, default='test_cases_tester',
                        help='测试用例目录 (默认: test_cases_tester)')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='输出目录 (默认: 使用new-dir)')
    
    args = parser.parse_args()
    
    BASE_DIR = Path("/root/zyydebug/mp_zyy/mp_generate")
    OLD_DIR = BASE_DIR / "test_tmp" / args.old_dir
    NEW_DIR = BASE_DIR / "test_tmp" / args.new_dir
    TEST_DIR = BASE_DIR / "test_tmp" / args.test_dir
    
    if args.output_dir:
        OUTPUT_DIR = BASE_DIR / "test_tmp" / args.output_dir
    else:
        OUTPUT_DIR = NEW_DIR / "comparison"
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    if not OLD_DIR.exists():
        print(f"旧版本目录不存在: {OLD_DIR}")
        return 1
    
    if not NEW_DIR.exists():
        print(f"新版本目录不存在: {NEW_DIR}")
        return 1
    
    compare_versions(OLD_DIR, NEW_DIR, TEST_DIR, OUTPUT_DIR)
    
    return 0

if __name__ == '__main__':
    exit(main())

