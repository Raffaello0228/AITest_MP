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

from core.report import generate_markdown_report, generate_html_report
from core.config.version_config import (
    get_algo_version,
    resolve_results_dir,
    resolve_achievement_json_dir,
    resolve_achievement_reports_dir,
)


def load_json(filepath: Path):
    """加载JSON文件"""
    import json

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


VARIANT_CONFIG = [
    ("xiaomi", "check_kpi_achievement_xiaomi.py"),
    ("common", "check_kpi_achievement.py"),
]


def batch_check_results(
    project_root: Path, algo_version: str, check_dimension: str = "corporation"
) -> tuple[int, int]:
    """批量检查指定算法版本的结果文件，同时检测 xiaomi 和 common 两条路径。"""
    total_success = 0
    total_fail = 0
    any_checked = False

    for variant, script_name in VARIANT_CONFIG:
        batch_results_dir = resolve_results_dir(project_root, variant, algo_version)
        check_script = project_root / "core" / script_name

        if not batch_results_dir.exists():
            print(f"\n[{variant}] 跳过：结果目录不存在 {batch_results_dir}")
            continue
        if not check_script.exists():
            print(f"\n[{variant}] 跳过：检查脚本不存在 {check_script}")
            continue

        result_files = sorted(batch_results_dir.glob("mp_result*.json"))
        if not result_files:
            print(f"\n[{variant}] 跳过：未找到 mp_result 结果文件")
            continue

        any_checked = True
        print(f"\n{'=' * 80}")
        print(f"[{variant}] 找到 {len(result_files)} 个结果文件，开始批量检查...")
        print("=" * 80)

        success_this = 0
        fail_this = 0
        for result_file in result_files:
            case_name = result_file.stem.replace("mp_result_", "")
            print(f"\n[处理] [{variant}] 用例: {case_name}")
            print(f"  结果文件: {result_file.name}")

            cmd = [
                sys.executable,
                str(check_script),
                "--result-file",
                str(result_file),
                "--case-name",
                case_name,
            ]
            # Xiaomi 检查支持选择 dimensionMultiCountryResult 下的维度
            if variant == "xiaomi":
                cmd.extend(["--check-dimension", check_dimension])
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
                    success_this += 1
                    total_success += 1
                else:
                    print(f"  [失败] 检查失败 (退出码: {result.returncode})")
                    if result.stderr:
                        print(f"  错误信息: {result.stderr[:200]}")
                    fail_this += 1
                    total_fail += 1
            except Exception as e:
                print(f"  [异常] 执行失败: {e}")
                fail_this += 1
                total_fail += 1

        print(f"\n[{variant}] 本路径检查完成: 成功 {success_this}，失败 {fail_this}")

    if not any_checked:
        print("\n错误：xiaomi 与 common 下均未找到可检查的结果目录")
        return 0, 1

    print("\n" + "=" * 80)
    print(f"\n批量检查完成（xiaomi + common）:")
    print(f"  成功: {total_success}")
    print(f"  失败: {total_fail}")
    print(f"  总计: {total_success + total_fail}")
    return total_success, total_fail


def batch_generate_reports(
    project_root: Path, algo_version: str, format_type: str = "html"
) -> tuple[int, int]:
    """批量生成指定算法版本的测试报告，同时处理 xiaomi 和 common 两条路径。"""
    total_success = 0
    total_fail = 0
    any_generated = False

    for variant in ["xiaomi", "common"]:
        input_dir = resolve_achievement_json_dir(project_root, variant, algo_version)
        if not input_dir.exists():
            print(
                f"\n[{variant}] 跳过：未找到 achievement_checks/json/{algo_version} 目录"
            )
            print(f"  请检查: {input_dir}")
            continue

        json_files = sorted(input_dir.glob("*_achievement_check.json"))
        if not json_files:
            print(f"\n[{variant}] 跳过：未找到 *_achievement_check.json 文件")
            continue

        any_generated = True
        print(f"\n{'=' * 80}")
        print(
            f"[{variant}] 找到 {len(json_files)} 个检查结果文件（版本: {algo_version}），开始生成报告..."
        )
        print("=" * 80)

        reports_dir = resolve_achievement_reports_dir(
            project_root, variant, algo_version
        )
        reports_dir.mkdir(parents=True, exist_ok=True)

        success_this = 0
        fail_this = 0
        for json_file in json_files:
            try:
                results = load_json(json_file)
                case_name = results.get("case_name", json_file.stem)

                print(f"\n[处理] [{variant}] {case_name}")
                print(f"  输入文件: {json_file.name}")

                base_name = json_file.stem
                md_path = reports_dir / f"{base_name}.md"
                html_path = reports_dir / f"{base_name}.html"

                if format_type in ["markdown", "both"]:
                    generate_markdown_report(results, md_path)
                    print(f"  [OK] Markdown: {md_path.name}")

                if format_type in ["html", "both"]:
                    generate_html_report(results, html_path)
                    print(f"  [OK] HTML: {html_path.name}")

                success_this += 1
                total_success += 1

            except Exception as e:
                print(f"\n[失败] {json_file.name}")
                print(f"  错误: {e}")
                import traceback

                traceback.print_exc()
                fail_this += 1
                total_fail += 1

        print(
            f"\n[{variant}] 本路径报告生成完成: 成功 {success_this}，失败 {fail_this}"
        )
        print(f"  报告输出目录: {reports_dir}")

    if not any_generated:
        print(
            "\n错误：xiaomi 与 common 下均未找到可生成报告的 achievement_checks/json 目录"
        )
        return 0, 1

    print("\n" + "=" * 80)
    print(f"\n批量生成报告完成（xiaomi + common）:")
    print(f"  成功: {total_success}")
    print(f"  失败: {total_fail}")
    print(f"  总计: {total_success + total_fail}")

    return total_success, total_fail


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
    parser.add_argument(
        "--algo-version",
        type=str,
        default="20260326_v1",
        help="算法版本（如 latest、20250226_v1）。不指定时使用配置或环境变量 MEDIAPLAN_ALGO_VERSION，默认 latest",
    )
    parser.add_argument(
        "--check-dimension",
        type=str,
        choices=["corporation", "category", "ai"],
        default="ai",
        help="Xiaomi 检查使用的维度（默认: corporation）",
    )

    args = parser.parse_args()

    algo_version = get_algo_version(args.algo_version)
    print(f"使用算法版本: {algo_version}\n")

    total_success = 0
    total_fail = 0

    if not args.skip_check:
        check_success, check_fail = batch_check_results(
            project_root, algo_version, args.check_dimension
        )
        total_success += check_success
        total_fail += check_fail
    else:
        print("跳过检查步骤...")

    if not args.skip_report:
        report_success, report_fail = batch_generate_reports(
            project_root, algo_version, args.format
        )
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
