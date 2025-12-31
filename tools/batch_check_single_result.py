#!/usr/bin/env python3
"""
批量执行 check_kpi_achievement.py 对所有 batch_query_results 下的文件
"""
import re
import subprocess
import sys
from pathlib import Path


def main():
    # 获取项目根目录
    project_root = Path(__file__).parent.parent

    # 支持 common 和 xiaomi 两个版本
    # 优先检查 xiaomi，如果不存在则使用 common
    batch_results_dir = project_root / "output" / "xiaomi" / "results"
    requests_dir = project_root / "output" / "xiaomi" / "requests"
    achievement_checks_dir = (
        project_root / "output" / "xiaomi" / "achievement_checks" / "json"
    )
    testcase_file = project_root / "testcase_templatex_xiaomi.py"
    check_script = project_root / "core" / "check_kpi_achievement_xiaomi.py"

    # 如果 xiaomi 目录不存在，尝试使用 common
    if not batch_results_dir.exists():
        batch_results_dir = project_root / "output" / "common" / "results"
        requests_dir = project_root / "output" / "common" / "requests"
        achievement_checks_dir = (
            project_root / "output" / "common" / "achievement_checks" / "json"
        )
        testcase_file = project_root / "testcase_template.py"
        check_script = project_root / "core" / "check_kpi_achievement.py"

    if not batch_results_dir.exists():
        print(f"错误：目录不存在: {batch_results_dir}")
        return 1

    if not testcase_file.exists():
        print(f"错误：测试用例文件不存在: {testcase_file}")
        return 1

    if not check_script.exists():
        print(f"错误：检查脚本不存在: {check_script}")
        return 1

    # 获取所有 batch_query 结果文件
    result_files = sorted(batch_results_dir.glob("mp_result*.json"))

    if not result_files:
        print(f"未找到任何 mp_result 结果文件")
        return 1

    print(f"找到 {len(result_files)} 个结果文件，开始批量检查...\n")
    print("=" * 80)

    success_count = 0
    fail_count = 0

    for result_file in result_files:
        # 从文件名提取用例名称
        case_name = result_file.stem.replace("mp_result_", "")

        # 构建请求文件路径
        request_file = requests_dir / f"brief_case_{case_name}.json"

        if not request_file.exists():
            print(f"\n[跳过] 用例: {case_name}")
            print(f"  原因: 请求文件不存在: {request_file}")
            fail_count += 1
            continue

        print(f"\n[处理] 用例: {case_name}")
        print(f"  请求文件: {request_file.name}")
        print(f"  结果文件: {result_file.name}")

        # 输出文件路径由 check_kpi_achievement.py 自动生成（包含 job_id）
        # 不指定 --output，让脚本自动处理文件名

        # 执行检查脚本
        cmd = [
            sys.executable,
            str(check_script),
            "--testcase-file",
            str(testcase_file),
            "--request-file",
            str(request_file),
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
                errors="replace",  # 处理编码错误
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

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
