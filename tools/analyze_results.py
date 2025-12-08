#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用结果分析脚本
用于分析单个版本的测试结果

用法:
    python3 analyze_results.py --output-dir test_results --test-dir test_cases_tester
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Tuple

def load_json(filepath: Path) -> Any:
    """加载JSON文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_kpi_config(request_json: Dict) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """提取KPI配置信息"""
    kpi_config = {}
    
    brief_info = request_json.get('briefBasicInfo', {})
    global_kpis = brief_info.get('kpiInfo', [])
    for kpi in global_kpis:
        kpi_key = kpi.get('key', '').replace(' ', '')
        kpi_config[kpi_key] = {
            'priority': kpi.get('priority', 999),
            'target': float(kpi.get('val', '0') or 0),
            'completion': kpi.get('completion', 1)
        }
    
    country_kpi_config = {}
    multi_country_config = request_json.get('multiCountryConfig', [])
    for country_config in multi_country_config:
        basic_info = country_config.get('basicInfo', {})
        country_code = basic_info.get('country', '')
        country_kpis = basic_info.get('kpiInfo', [])
        
        country_kpi_config[country_code] = {}
        for kpi in country_kpis:
            kpi_key = kpi.get('key', '').replace(' ', '')
            country_kpi_config[country_code][kpi_key] = {
                'priority': kpi.get('priority', 999),
                'target': float(kpi.get('val', '0') or 0),
                'completion': kpi.get('completion', 1)
            }
    
    return kpi_config, country_kpi_config

def calculate_kpi_achievement(result_data: List[Dict], country_kpi_config: Dict, global_kpi_config: Dict) -> Dict[str, Any]:
    """计算KPI达成率"""
    kpi_mapping = {
        'Impression': 'ai_cpm',
        'VideoViews': 'ai_cpv',
        'Video Views': 'ai_cpv',
        'Engagement': 'ai_cpe',
        'Followers': 'ai_cpf',
        'LinkClicks': 'ai_cpc_link',
        'Link Clicks': 'ai_cpc_link',
        'Purchase': 'ai_cpp',
        'Clicks': 'ai_cpc',
        'Leads': 'ai_cpl',
        'Like': 'ai_cpe',
    }
    
    global_kpi_stats = defaultdict(lambda: {
        'target': 0.0,
        'estimated': 0.0,
        'achievement': 0.0,
        'priority': 999,
        'achieved_count': 0,
        'total_count': 0
    })
    
    country_kpi_stats = defaultdict(lambda: defaultdict(lambda: {
        'target': 0.0,
        'estimated': 0.0,
        'achievement': 0.0,
        'priority': 999
    }))
    
    for kpi_name, kpi_info in global_kpi_config.items():
        global_kpi_stats[kpi_name]['target'] = kpi_info['target']
        global_kpi_stats[kpi_name]['priority'] = kpi_info['priority']
    
    for row in result_data:
        region = row.get('Region') or ''
        country_code = region.split('_')[0] if region and '_' in region else (region or 'UNKNOWN')
        
        budget = float(row.get('ai_ad_type_budget', 0) or 0)
        if budget <= 0:
            continue
        
        for kpi_name, cpx_field in kpi_mapping.items():
            kpi_normalized = kpi_name.replace(' ', '')
            
            ai_cpx = row.get(cpx_field, '')
            if not ai_cpx:
                continue
            
            try:
                ai_cpx_float = float(ai_cpx)
            except:
                continue
            
            if ai_cpx_float <= 0:
                continue
            
            if kpi_normalized == 'Impression' and cpx_field == 'ai_cpm':
                estimated_quantity = (budget / ai_cpx_float) * 1000
            else:
                estimated_quantity = budget / ai_cpx_float
            
            if kpi_normalized in global_kpi_stats:
                global_kpi_stats[kpi_normalized]['estimated'] += estimated_quantity
                global_kpi_stats[kpi_normalized]['total_count'] += 1
                if estimated_quantity >= global_kpi_stats[kpi_normalized]['target']:
                    global_kpi_stats[kpi_normalized]['achieved_count'] += 1
            
            if country_code in country_kpi_config and kpi_normalized in country_kpi_config[country_code]:
                country_kpi_stats[country_code][kpi_normalized]['estimated'] += estimated_quantity
                country_kpi_stats[country_code][kpi_normalized]['target'] = country_kpi_config[country_code][kpi_normalized]['target']
                country_kpi_stats[country_code][kpi_normalized]['priority'] = country_kpi_config[country_code][kpi_normalized]['priority']
    
    for kpi_name in global_kpi_stats:
        target = global_kpi_stats[kpi_name]['target']
        estimated = global_kpi_stats[kpi_name]['estimated']
        if target > 0:
            global_kpi_stats[kpi_name]['achievement'] = (estimated / target) * 100
    
    for country_code in country_kpi_stats:
        for kpi_name in country_kpi_stats[country_code]:
            target = country_kpi_stats[country_code][kpi_name]['target']
            estimated = country_kpi_stats[country_code][kpi_name]['estimated']
            if target > 0:
                country_kpi_stats[country_code][kpi_name]['achievement'] = (estimated / target) * 100
    
    return {
        'global': dict(global_kpi_stats),
        'country': {k: dict(v) for k, v in country_kpi_stats.items()}
    }

def analyze_single_case(case_name: str, test_dir: Path, result_dir: Path) -> Dict[str, Any]:
    """分析单个测试用例"""
    test_case_file = test_dir / f"{case_name}.json"
    if not test_case_file.exists():
        return None
    
    request_json = load_json(test_case_file)
    global_kpi_config, country_kpi_config = extract_kpi_config(request_json)
    
    result_file = None
    for f in result_dir.glob(f"{case_name}_result_*.json"):
        result_file = f
        break
    
    if not result_file:
        return None
    
    result = load_json(result_file)
    result_data = result.get('result', {}).get('data', [])
    
    kpi = calculate_kpi_achievement(result_data, country_kpi_config, global_kpi_config)
    
    return {
        'case_name': case_name,
        'kpi': kpi
    }

def generate_report(all_results: List[Dict], output_dir: Path):
    """生成分析报告"""
    report = []
    report.append("="*80)
    report.append("测试结果分析报告")
    report.append("="*80)
    report.append("")
    
    # 全局KPI汇总
    global_kpi_summary = defaultdict(lambda: {
        'achievements': [],
        'achieved_count': 0,
        'total_count': 0
    })
    
    for result in all_results:
        global_kpis = result['kpi']['global']
        for kpi_name, stats in global_kpis.items():
            achievement = stats.get('achievement', 0)
            global_kpi_summary[kpi_name]['achievements'].append(achievement)
            global_kpi_summary[kpi_name]['total_count'] += 1
            if achievement >= 100:
                global_kpi_summary[kpi_name]['achieved_count'] += 1
    
    report.append("## 全局KPI达成率汇总")
    report.append("-"*80)
    report.append(f"{'KPI名称':<20} {'达成用例数':<15} {'总用例数':<15} {'达成成功率':<15} {'平均达成率':<15}")
    report.append("-"*80)
    
    for kpi_name in sorted(global_kpi_summary.keys()):
        stats = global_kpi_summary[kpi_name]
        success_rate = (stats['achieved_count'] / stats['total_count'] * 100) if stats['total_count'] > 0 else 0
        avg_achievement = sum(stats['achievements']) / len(stats['achievements']) if stats['achievements'] else 0
        report.append(f"{kpi_name:<20} {stats['achieved_count']:>14}/{stats['total_count']:<14} {success_rate:>14.1f}% {avg_achievement:>14.1f}%")
    
    # 逐用例报告
    report.append("\n" + "="*80)
    report.append("逐用例KPI达成率")
    report.append("="*80)
    
    for result in all_results:
        case_name = result['case_name']
        global_kpis = result['kpi']['global']
        
        report.append(f"\n## 用例: {case_name}")
        report.append("-"*80)
        report.append(f"{'KPI名称':<20} {'目标值':<15} {'预估达成':<15} {'达成率':<15}")
        report.append("-"*80)
        
        for kpi_name in sorted(global_kpis.keys()):
            stats = global_kpis[kpi_name]
            report.append(f"{kpi_name:<20} {stats['target']:>15,.0f} {stats['estimated']:>15,.0f} {stats['achievement']:>14.2f}%")
    
    # 保存报告
    report_file = output_dir / "analysis_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print(f"报告已保存到: {report_file}")

def main():
    parser = argparse.ArgumentParser(description='分析测试结果')
    parser.add_argument('--output-dir', type=str, required=True,
                        help='结果输出目录 (必需)')
    parser.add_argument('--test-dir', type=str, default='test_cases_tester',
                        help='测试用例目录 (默认: test_cases_tester)')
    
    args = parser.parse_args()
    
    BASE_DIR = Path("/root/zyydebug/mp_zyy/mp_generate")
    OUTPUT_DIR = BASE_DIR / "test_tmp" / args.output_dir
    TEST_DIR = BASE_DIR / "test_tmp" / args.test_dir
    
    if not OUTPUT_DIR.exists():
        print(f"输出目录不存在: {OUTPUT_DIR}")
        return 1
    
    # 获取所有结果文件
    result_files = list(OUTPUT_DIR.glob("*_result_*.json"))
    if not result_files:
        print(f"在 {OUTPUT_DIR} 中未找到结果文件")
        return 1
    
    test_names = set()
    for f in result_files:
        name_parts = f.name.split('_result_')
        if len(name_parts) > 0:
            test_names.add(name_parts[0])
    
    print(f"找到 {len(test_names)} 个测试用例的结果")
    
    all_results = []
    for case_name in sorted(test_names):
        result = analyze_single_case(case_name, TEST_DIR, OUTPUT_DIR)
        if result:
            all_results.append(result)
            print(f"✓ 已分析: {case_name}")
        else:
            print(f"✗ 跳过: {case_name} (缺少配置或结果文件)")
    
    if not all_results:
        print("没有可分析的结果")
        return 1
    
    # 生成报告
    analysis_dir = OUTPUT_DIR / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    
    generate_report(all_results, analysis_dir)
    
    # 保存数据
    data_file = analysis_dir / "analysis_data.json"
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"数据已保存到: {data_file}")
    
    return 0

if __name__ == '__main__':
    exit(main())

