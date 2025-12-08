#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成两个版本测试结果对比的 CSV 报告

按用例逐行对比：
- KPI 名称/优先级：如果同一优先级对应多个 KPI，则报错；否则填入名称或 NULL
- 限制名称/优先级：如果同一优先级对应多个限制类型，则报错；否则填入名称或 NULL
- KPI_Px 列：改为 新版/旧版 的达成比例（倍数），数值 = new_avg / old_avg
- 限制Px 列：
    - 如果新版与旧版遵守率相同（差值 < 1e-6），输出 'X'
    - 否则输出 '{new_rate:.4f}/{old_rate:.4f}' 字符串

用法示例：
    cd test_tmp
    python3 generate_test_comparison_csv.py \\
        --old-dir test_exp/test_1126_low_priority_v7_1 \\
        --new-dir test_exp/test_1201_low_priority_v7_2_1 \\
        --test-dir test_cases/v7/test_cases_tester_low_kpi
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any

import sys
sys.path.insert(0, str(Path(__file__).parent))

from analyze_results import extract_kpi_config, calculate_kpi_achievement
from compare_versions import extract_constraint_config, calculate_actual_allocation, check_constraint_compliance


def load_json(filepath: Path) -> Any:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def compute_kpi_priority_mapping(global_kpi_config: Dict[str, Any]) -> Dict[int, str]:
    """
    计算 KPI 优先级到名称的映射：
    - 如果某个优先级下有多个 KPI，则报错（需求：不一样报错）
    - 如果没有 KPI，则映射为 NULL（调用方处理）
    """
    mapping: Dict[int, List[str]] = defaultdict(list)
    for kpi_name, info in global_kpi_config.items():
        priority = int(info.get('priority', 999))
        if 1 <= priority <= 6:
            mapping[priority].append(kpi_name)

    result: Dict[int, str] = {}
    for p in range(1, 7):
        names = mapping.get(p, [])
        if not names:
            # 交由调用方填 NULL
            continue
        if len(names) > 1:
            raise ValueError(f"KPI 优先级 P{p} 对应多个 KPI: {names}")
        result[p] = names[0]
    return result


def compute_constraint_priority_mapping(constraint_config: Dict[str, List[Dict[str, Any]]]) -> Dict[int, str]:
    """
    计算限制优先级到限制类型名称的映射：
    - 如果同一优先级下出现多个不同 constraint_type，则报错（需求：不一样报错）
    - 如果没有限制使用该优先级，则映射由调用方填 NULL
    """
    mapping: Dict[int, List[str]] = defaultdict(list)

    for constraint_type in ['stage', 'media', 'adType', 'marketingFunnel']:
        for cfg in constraint_config.get(constraint_type, []):
            priority = int(cfg.get('priority', 999))
            if 1 <= priority <= 6:
                if constraint_type not in mapping[priority]:
                    mapping[priority].append(constraint_type)

    result: Dict[int, str] = {}
    for p in range(1, 7):
        types = mapping.get(p, [])
        if not types:
            continue
        if len(types) > 1:
            raise ValueError(f"限制优先级 P{p} 对应多个限制类型: {types}")
        result[p] = types[0]
    return result


def compute_kpi_priority_achievement(kpi_stats: Dict[str, Any]) -> Dict[int, float]:
    """
    根据 calculate_kpi_achievement 的结果（global 部分），按优先级计算平均达成比例（倍数）。
    返回：{priority: avg_achievement_multiple}
    """
    by_priority: Dict[int, Dict[str, float]] = defaultdict(lambda: {'total_achievement': 0.0, 'count': 0})

    for kpi_name, stats in kpi_stats.get('global', {}).items():
        priority = int(stats.get('priority', 999))
        if 1 <= priority <= 6:
            achievement_percent = float(stats.get('achievement', 0.0))
            by_priority[priority]['total_achievement'] += achievement_percent
            by_priority[priority]['count'] += 1

    result: Dict[int, float] = {}
    for p in range(1, 7):
        info = by_priority.get(p)
        if not info or info['count'] == 0:
            continue
        avg_percent = info['total_achievement'] / info['count']
        # 转换为倍数（完成量/目标量）
        result[p] = avg_percent / 100.0
    return result


def compute_constraint_priority_compliance(
    result_data: List[Dict[str, Any]],
    constraint_config: Dict[str, List[Dict[str, Any]]],
    request_json: Dict[str, Any] = None
) -> Dict[int, float]:
    """
    计算限制遵守率，按优先级聚合：遵守个数/总个数
    返回：{priority: compliance_rate}
    """
    by_priority: Dict[int, Dict[str, int]] = defaultdict(lambda: {'compliant': 0, 'total': 0})

    # 计算国家预算信息（用于获取实际分配预算）
    from compare_versions import calculate_country_budgets
    if request_json:
        country_budgets = calculate_country_budgets(result_data, request_json)
    else:
        country_budgets = {'actual': {}}
    
    for constraint_type in ['stage', 'media', 'adType', 'marketingFunnel']:
        actual_allocation = calculate_actual_allocation(result_data, constraint_type)

        for constraint in constraint_config.get(constraint_type, []):
            priority = int(constraint.get('priority', 999))
            if not (1 <= priority <= 6):
                continue

            country = constraint['country']
            expected = constraint['expected']
            actual_pct = actual_allocation.get(country, {})
            
            # 获取该国家的实际分配总预算
            country_total = country_budgets['actual'].get(country, 0.0)

            is_compliant, _ = check_constraint_compliance(
                expected,
                actual_pct,
                constraint['consistentMatch'],
                constraint['rangeMatch'],
                actual_total_budget=country_total
            )

            by_priority[priority]['total'] += 1
            if is_compliant:
                by_priority[priority]['compliant'] += 1

    result: Dict[int, float] = {}
    for p in range(1, 7):
        info = by_priority.get(p)
        if not info or info['total'] == 0:
            continue
        result[p] = info['compliant'] / info['total']
    return result


def compute_constraint_priority_meta(
    request_json: Dict[str, Any],
    constraint_config: Dict[str, List[Dict[str, Any]]],
) -> Dict[int, str]:
    """
    计算每个优先级对应的「达成率/误差」元信息：
    - KPI 预算限制优先级：输出 kpiInfoBudgetConfig.rangeMatch，如果统一；否则输出 '目标达标率'
    - 仅大小匹配：输出 '大小匹配'
    - 仅容差匹配：如果 rangeMatch 统一，则输出该数值；否则输出所有数值的逗号拼接
    - 同时存在大小匹配和容差匹配：输出 '大小匹配+容差'
    """
    # 统计匹配方式与 rangeMatch 数值
    match_types_by_priority: Dict[int, set] = defaultdict(set)
    range_vals_by_priority: Dict[int, set] = defaultdict(set)

    for constraint_type in ['stage', 'media', 'adType', 'marketingFunnel']:
        for cfg in constraint_config.get(constraint_type, []):
            priority = int(cfg.get('priority', 999))
            if not (1 <= priority <= 6):
                continue
            consistent = cfg.get('consistentMatch')
            if consistent == 1:
                match_types_by_priority[priority].add('容差')
                rv = cfg.get('rangeMatch')
                if isinstance(rv, (int, float)):
                    range_vals_by_priority[priority].add(float(rv))
            else:
                match_types_by_priority[priority].add('大小匹配')

    # 解析 KPI 预算优先级与 rangeMatch
    kpi_budget_priority = None
    kpi_budget_threshold = None
    multi_country_config = request_json.get('multiCountryConfig', [])
    if multi_country_config:
        pri_vals = []
        range_vals = []
        for country_cfg in multi_country_config:
            basic_info = country_cfg.get('basicInfo', {})
            kpi_cfg = basic_info.get('kpiInfoBudgetConfig', {})
            p = kpi_cfg.get('priority', None)
            if isinstance(p, int):
                pri_vals.append(p)
            rv = kpi_cfg.get('rangeMatch', None)
            if isinstance(rv, (int, float)):
                range_vals.append(float(rv))
        if pri_vals:
            uniq_p = set(pri_vals)
            if len(uniq_p) == 1 and 1 <= list(uniq_p)[0] <= 6:
                kpi_budget_priority = list(uniq_p)[0]
        if range_vals:
            uniq_r = set(range_vals)
            if len(uniq_r) == 1:
                kpi_budget_threshold = list(uniq_r)[0]

    meta: Dict[int, str] = {}
    for p in range(1, 7):
        desc = 'NULL'
        if kpi_budget_priority is not None and p == kpi_budget_priority:
            if kpi_budget_threshold is not None:
                desc = f"{kpi_budget_threshold:.4f}"
            else:
                desc = '目标达标率'
        else:
            types = match_types_by_priority.get(p, set())
            if types:
                if types == {'大小匹配'}:
                    desc = '大小匹配'
                elif types == {'容差'}:
                    vals = range_vals_by_priority.get(p, set())
                    if vals:
                        if len(vals) == 1:
                            desc = f"{list(vals)[0]:.4f}"
                        else:
                            desc = ','.join(f"{v:.4f}" for v in sorted(vals))
                    else:
                        desc = '容差'
                else:
                    desc = '+'.join(sorted(types))
        meta[p] = desc
    return meta


def generate_comparison_csv(
    old_dir: Path,
    new_dir: Path,
    test_dir: Path,
    output_file: Path,
) -> None:
    print("开始生成对比 CSV 报告...")
    print(f"旧版本目录: {old_dir}")
    print(f"新版本目录: {new_dir}")
    print(f"测试用例目录: {test_dir}")

    test_cases = sorted([f.stem for f in test_dir.glob("*.json")])
    rows: List[Dict[str, Any]] = []

    for case_name in test_cases:
        test_case_file = test_dir / f"{case_name}.json"
        if not test_case_file.exists():
            continue

        request_json = load_json(test_case_file)
        global_kpi_config, country_kpi_config = extract_kpi_config(request_json)
        constraint_config, _, country_budget_config = extract_constraint_config(request_json)

        # KPI/限制优先级映射校验（如果同一优先级对应多个元素则抛错）
        kpi_priority_map = compute_kpi_priority_mapping(global_kpi_config)
        constraint_priority_map = compute_constraint_priority_mapping(constraint_config)

        # 加载旧/新结果
        old_result_file = None
        new_result_file = None

        for f in old_dir.glob(f"{case_name}_result_*.json"):
            old_result_file = f
            break
        for f in new_dir.glob(f"{case_name}_result_*.json"):
            new_result_file = f
            break

        if not old_result_file or not new_result_file:
            print(f"✗ 跳过 {case_name}: 结果文件不存在 (old: {bool(old_result_file)}, new: {bool(new_result_file)})")
            continue

        old_result = load_json(old_result_file)
        new_result = load_json(new_result_file)

        old_data = old_result.get('result', {}).get('data', [])
        new_data = new_result.get('result', {}).get('data', [])

        # KPI 达成情况
        old_kpi = calculate_kpi_achievement(old_data, country_kpi_config, global_kpi_config)
        new_kpi = calculate_kpi_achievement(new_data, country_kpi_config, global_kpi_config)

        old_kpi_by_priority = compute_kpi_priority_achievement(old_kpi)
        new_kpi_by_priority = compute_kpi_priority_achievement(new_kpi)

        # 限制遵守率
        old_constraint_by_priority = compute_constraint_priority_compliance(old_data, constraint_config, request_json)
        new_constraint_by_priority = compute_constraint_priority_compliance(new_data, constraint_config, request_json)
        # 限制元信息（达成率/误差）
        constraint_meta_by_priority = compute_constraint_priority_meta(request_json, constraint_config)

        # 组装一行
        row: Dict[str, Any] = {
            '用例名称': case_name,
        }

        # KPI 名称列（P1-P6）
        for p in range(1, 7):
            col_name = f'P{p}_KPI'
            row[col_name] = kpi_priority_map.get(p, 'NULL')

        # 限制名称列（P1-P6）及对应的达成率/误差说明（新/旧共用）
        for p in range(1, 7):
            col_name = f'限制P{p}_name'
            meta_col_new_old = f'限制P{p}_达成率/误差_新/旧'
            row[col_name] = constraint_priority_map.get(p, 'NULL')
            row[meta_col_new_old] = constraint_meta_by_priority.get(p, 'NULL')

        # KPI 对比列：新版/旧版
        for p in range(1, 7):
            col_name = f'KPI_P{p}新/旧'
            old_val = old_kpi_by_priority.get(p)
            new_val = new_kpi_by_priority.get(p)
            if old_val is None or old_val == 0 or new_val is None:
                row[col_name] = 'NULL'
            else:
                ratio = new_val / old_val
                row[col_name] = f"{ratio:.4f}"

        # 限制对比列：相同 => 'SAME'，不同 => 'new/old'
        for p in range(1, 7):
            col_name = f'限制P{p}新/旧'
            old_rate = old_constraint_by_priority.get(p)
            new_rate = new_constraint_by_priority.get(p)

            if old_rate is None and new_rate is None:
                row[col_name] = 'NULL'
            else:
                old_v = float(old_rate or 0.0)
                new_v = float(new_rate or 0.0)
                if abs(old_v - new_v) < 1e-6:
                    row[col_name] = 'SAME'
                else:
                    row[col_name] = f"{new_v:.4f}/{old_v:.4f}"

        rows.append(row)
        print(f"✓ 已对比: {case_name}")

    if not rows:
        print("错误: 未生成任何对比数据")
        return

    # 确定列顺序
    columns: List[str] = ['用例名称']
    for p in range(1, 7):
        columns.append(f'P{p}_KPI')
    for p in range(1, 7):
        columns.append(f'限制P{p}_name')
        columns.append(f'限制P{p}_达成率/误差_新/旧')
    # KPI 列名改为「KPI_PX新/旧」
    for p in range(1, 7):
        columns.append(f'KPI_P{p}新/旧')
    # 限制列名改为「限制PX新/旧」
    for p in range(1, 7):
        columns.append(f'限制P{p}新/旧')

    # 写入 CSV
    import csv
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"\n对比 CSV 已保存到: {output_file}")
    print(f"共生成 {len(rows)} 行")


def main() -> None:
    parser = argparse.ArgumentParser(description='生成两个版本逐用例对比的 CSV 报告')
    parser.add_argument('--old-dir', type=str, required=True, help='旧版本结果目录 (必需)')
    parser.add_argument('--new-dir', type=str, required=True, help='新版本结果目录 (必需)')
    parser.add_argument('--test-dir', type=str, required=True, help='测试用例目录 (必需)')
    parser.add_argument('--output-file', type=str, default=None, help='输出 CSV 文件路径 (默认: new-dir 同级目录下 comparison_summary.csv)')

    args = parser.parse_args()

    base_dir = Path("/root/zyydebug/mp_zyy/mp_generate/test_tmp")
    old_dir = base_dir / args.old_dir
    new_dir = base_dir / args.new_dir
    test_dir = base_dir / args.test_dir

    if not old_dir.exists():
        print(f"错误: 旧版本结果目录不存在: {old_dir}")
        return
    if not new_dir.exists():
        print(f"错误: 新版本结果目录不存在: {new_dir}")
        return
    if not test_dir.exists():
        print(f"错误: 测试用例目录不存在: {test_dir}")
        return

    if args.output_file:
        output_file = Path(args.output_file)
    else:
        output_file = new_dir / "comparison_summary.csv"

    generate_comparison_csv(old_dir, new_dir, test_dir, output_file)


if __name__ == '__main__':
    main()


