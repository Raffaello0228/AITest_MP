#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量为所有 achievement_check.json 文件生成测试报告

用法:
    python tools/batch_generate_reports.py [--input-dir output/xiaomi/achievement_checks/json]
"""

import argparse
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


def main():
    parser = argparse.ArgumentParser(description="批量生成测试报告")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="输入目录（包含所有 achievement_check.json 文件），默认自动检测 xiaomi 或 common",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["markdown", "html", "both"],
        default="html",
        help="输出格式：markdown、html 或 both（默认：both）",
    )

    args = parser.parse_args()

    # 自动检测输入目录
    if args.input_dir is None:
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
            return 1
    else:
        input_dir = args.input_dir

    if not input_dir.exists():
        print(f"错误：输入目录不存在: {input_dir}")
        return 1

    # 获取所有 achievement_check.json 文件
    json_files = sorted(input_dir.glob("*_achievement_check.json"))
    if not json_files:
        print(f"错误：在 {input_dir} 中未找到任何 achievement_check.json 文件")
        return 1

    print(f"找到 {len(json_files)} 个检查结果文件，开始生成报告...\n")
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
            if args.format in ["markdown", "both"]:
                generate_markdown_report(results, md_path)
                print(f"  [OK] Markdown: {md_path.name}")

            if args.format in ["html", "both"]:
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

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
