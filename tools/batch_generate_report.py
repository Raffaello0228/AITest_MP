#!/usr/bin/env python3
"""
批量生成测试报告 - 为 output/achievement_checks/ 目录下的所有 achievement_check.json 文件生成报告
"""
import subprocess
import sys
from pathlib import Path


def main():
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    achievement_checks_dir = project_root / "output" / "achievement_checks" / "json"
    report_script = project_root / "tools" / "generate_test_report.py"

    if not achievement_checks_dir.exists():
        print(f"错误：目录不存在: {achievement_checks_dir}")
        return 1

    if not report_script.exists():
        print(f"错误：报告生成脚本不存在: {report_script}")
        return 1

    # 获取所有 achievement_check.json 文件（优先从 json/ 目录，如果没有则从根目录）
    # 支持两种格式：*_achievement_check.json 和 *_{job_id}_achievement_check.json
    json_dir = achievement_checks_dir / "json"
    if json_dir.exists():
        result_files = sorted(json_dir.glob("*_achievement_check.json"))
    else:
        result_files = sorted(achievement_checks_dir.glob("*_achievement_check.json"))

    if not result_files:
        print(f"未找到任何 achievement_check.json 文件")
        return 1

    print(f"找到 {len(result_files)} 个结果文件，开始批量生成报告...\n")
    print("=" * 80)

    success_count = 0
    fail_count = 0

    for result_file in result_files:
        print(f"\n[处理] {result_file.name}")

        # 执行报告生成脚本
        cmd = [
            sys.executable,
            str(report_script),
            "--result-file",
            str(result_file),
            "--format",
            "both",
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
                print(f"  [成功] 报告已生成")
                # 显示生成的文件（报告在 reports/ 目录）
                reports_dir = (
                    result_file.parent.parent / "reports"
                    if result_file.parent.name == "json"
                    else result_file.parent
                )
                md_file = reports_dir / f"{result_file.stem}.md"
                html_file = reports_dir / f"{result_file.stem}.html"
                if md_file.exists():
                    print(f"    - Markdown: {md_file.name}")
                if html_file.exists():
                    print(f"    - HTML: {html_file.name}")
                success_count += 1
            else:
                print(f"  [失败] 生成失败 (退出码: {result.returncode})")
                if result.stderr:
                    print(f"  错误信息: {result.stderr[:200]}")
                fail_count += 1

        except Exception as e:
            print(f"  [异常] 执行失败: {e}")
            fail_count += 1

    print("\n" + "=" * 80)
    print(f"\n批量生成完成:")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  总计: {len(result_files)}")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
