#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量检查结果文件并生成测试报告

用法:
    python tools/batch_check_and_report.py [--skip-check] [--skip-report] [--format html]
"""

import argparse
import subprocess
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.generate_test_report import generate_markdown_report, generate_html_report


def load_json(filepath: Path):
    """加载JSON文件"""
    import json

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def batch_check_results(project_root: Path) -> tuple[int, int]:
    """批量检查所有结果文件"""
    # 支持 common 和 xiaomi 两个版本
    # 优先检查 xiaomi，如果不存在则使用 common
    batch_results_dir = project_root / "output" / "xiaomi" / "results"
    achievement_checks_dir = (
        project_root / "output" / "xiaomi" / "achievement_checks" / "json"
    )
    check_script = project_root / "core" / "check_kpi_achievement_xiaomi.py"

    # 如果 xiaomi 目录不存在，尝试使用 common
    if not batch_results_dir.exists():
        batch_results_dir = project_root / "output" / "common" / "results"
        achievement_checks_dir = (
            project_root / "output" / "common" / "achievement_checks" / "json"
        )
        check_script = project_root / "core" / "check_kpi_achievement.py"

    if not batch_results_dir.exists():
        print(f"错误：目录不存在: {batch_results_dir}")
        return 0, 1

    if not check_script.exists():
        print(f"错误：检查脚本不存在: {check_script}")
        return 0, 1

    # 获取所有 batch_query 结果文件
    result_files = sorted(batch_results_dir.glob("mp_result*.json"))

    if not result_files:
        print(f"未找到任何 mp_result 结果文件")
        return 0, 1

    print(f"找到 {len(result_files)} 个结果文件，开始批量检查...\n")
    print("=" * 80)

    success_count = 0
    fail_count = 0

    for result_file in result_files:
        # 从文件名提取用例名称
        case_name = result_file.stem.replace("mp_result_", "")

        print(f"\n[处理] 用例: {case_name}")
        print(f"  结果文件: {result_file.name}")

        # 执行检查脚本
        cmd = [
            sys.executable,
            str(check_script),
            "--result-file",
            str(result_file),
            "--case-name",
            case_name,
            "--output",
            str(achievement_checks_dir),
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode == 0:
                print(f"  [成功] 检查完成")
                success_count += 1
            else:
                print(f"  [失败] 检查失败 (退出码: {result.returncode})")
                if result.stderr:
                    print(f"  错误信息: {result.stderr[:200]}")
                fail_count += 1

        except Exception as e:
            print(f"  [异常] 执行失败: {e}")
            fail_count += 1

    print("\n" + "=" * 80)
    print(f"\n批量检查完成:")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  总计: {len(result_files)}")

    return success_count, fail_count


def batch_generate_reports(
    project_root: Path, format_type: str = "html"
) -> tuple[int, int]:
    """批量生成测试报告"""
    # 自动检测输入目录
    # 优先检查 xiaomi，如果不存在则使用 common
    xiaomi_dir = project_root / "output" / "xiaomi" / "achievement_checks" / "json"
    common_dir = project_root / "output" / "common" / "achievement_checks" / "json"

    if xiaomi_dir.exists():
        input_dir = xiaomi_dir
    elif common_dir.exists():
        input_dir = common_dir
    else:
        print(f"错误：未找到 achievement_checks/json 目录")
        print(f"  请检查: {xiaomi_dir} 或 {common_dir}")
        return 0, 1

    if not input_dir.exists():
        print(f"错误：输入目录不存在: {input_dir}")
        return 0, 1

    # 获取所有 achievement_check.json 文件
    json_files = sorted(input_dir.glob("*_achievement_check.json"))
    if not json_files:
        print(f"错误：在 {input_dir} 中未找到任何 achievement_check.json 文件")
        return 0, 1

    print(f"\n找到 {len(json_files)} 个检查结果文件，开始生成报告...\n")
    print("=" * 80)

    # 确定报告输出目录
    achievement_checks_dir = input_dir.parent
    reports_dir = achievement_checks_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    fail_count = 0

    for json_file in json_files:
        try:
            # 加载检查结果
            results = load_json(json_file)
            case_name = results.get("case_name", json_file.stem)

            print(f"\n[处理] {case_name}")
            print(f"  输入文件: {json_file.name}")

            # 生成报告文件名
            base_name = json_file.stem
            md_path = reports_dir / f"{base_name}.md"
            html_path = reports_dir / f"{base_name}.html"

            # 生成报告
            if format_type in ["markdown", "both"]:
                generate_markdown_report(results, md_path)
                print(f"  [OK] Markdown: {md_path.name}")

            if format_type in ["html", "both"]:
                generate_html_report(results, html_path)
                print(f"  [OK] HTML: {html_path.name}")

            success_count += 1

        except Exception as e:
            print(f"\n[失败] {json_file.name}")
            print(f"  错误: {e}")
            import traceback

            traceback.print_exc()
            fail_count += 1

    print("\n" + "=" * 80)
    print(f"\n批量生成报告完成:")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  总计: {len(json_files)}")
    print(f"\n报告输出目录: {reports_dir}")

    return success_count, fail_count


def main():
    parser = argparse.ArgumentParser(description="批量检查结果文件并生成测试报告")
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="跳过检查步骤，只生成报告",
    )
    parser.add_argument(
        "--skip-report",
        action="store_true",
        help="跳过报告生成步骤，只执行检查",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["markdown", "html", "both"],
        default="html",
        help="报告输出格式：markdown、html 或 both（默认：html）",
    )

    args = parser.parse_args()

    total_success = 0
    total_fail = 0

    # 执行检查
    if not args.skip_check:
        check_success, check_fail = batch_check_results(project_root)
        total_success += check_success
        total_fail += check_fail
    else:
        print("跳过检查步骤...")

    # 生成报告
    if not args.skip_report:
        report_success, report_fail = batch_generate_reports(project_root, args.format)
        total_success += report_success
        total_fail += report_fail
    else:
        print("跳过报告生成步骤...")

    print("\n" + "=" * 80)
    print(f"\n全部完成:")
    print(f"  成功: {total_success}")
    print(f"  失败: {total_fail}")

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
