#!/usr/bin/env python3
"""
批量读取 output 目录下的 JSON 请求，调用 API 完整流程，并在任务成功后拉取批量查询结果。

使用方式：
    python tools/batch_execute_requests.py --dir output/common/requests
    python tools/batch_execute_requests.py --dir output/common/requests --resume
    python tools/batch_execute_requests.py --dir output/common/requests --resume --retry 3

执行策略：
    --resume  断点续跑：只执行未完成的 request（已存在对应 mp_result_*.json 的请求跳过）
    --retry N 单个请求失败时重试 N 次，重试间隔递增（2s、4s…）
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict

import sys
from pathlib import Path

# 添加项目根目录到路径，以便导入 core 模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core import (
    create_client_from_config,
    ENVIRONMENT_CONFIGS,
    get_api_config,
    get_strategy_config,
)
from core.config.version_config import get_algo_version, resolve_results_dir


def load_request_body(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_result_path_for_request(file_path: Path, detail_output_dir: Path) -> Path:
    """根据请求文件名得到对应的结果文件路径（brief_case_xxx -> mp_result_xxx.json）。"""
    base = file_path.stem.replace("brief_case_", "mp_result_")
    return detail_output_dir / f"{base}.json"


async def run_for_file(
    client,
    file_path: Path,
    max_attempts: int,
    interval_ms: int,
) -> Dict[str, Any]:
    body = load_request_body(file_path)
    result = await client.complete_workflow(
        request_body=body,
        max_polling_attempts=max_attempts,
        polling_interval_ms=interval_ms,
    )
    return result


async def main(args):
    output_dir = Path(args.dir)
    if not output_dir.exists():
        print(f"输出目录不存在: {output_dir}")
        return

    files = sorted(output_dir.glob("*.json"))
    if not files:
        print(f"目录 {output_dir} 中未找到 json 文件")
        return

    # 获取环境配置（使用命令行参数，默认值为 PROD）
    environment = args.environment

    # 从策略配置获取轮询参数
    strategy_config = get_strategy_config()
    max_attempts = args.max_attempts or strategy_config.max_polling_attempts
    interval_ms = args.interval or strategy_config.polling_interval

    # 根据命令行参数或目录路径自动判断 API 版本（common/xiaomi）
    if args.version:
        variant = args.version
    else:
        variant = "xiaomi" if "xiaomi" in str(output_dir).lower() else "common"
    api_config = get_api_config(variant, environment)
    print(f"使用 {variant} 版本 API 配置，环境: {environment}")

    # 算法版本：用于按版本保留结果，便于后续对比评测
    algo_version = get_algo_version(getattr(args, "algo_version", None))
    print(f"算法版本: {algo_version}（结果将保存到 results/{algo_version}/）")

    # 创建批量查询结果输出目录（带算法版本子目录）
    # output/common/requests -> output/common/results/<algo_version>/
    detail_output_dir = resolve_results_dir(
        project_root, variant=variant, algo_version=algo_version
    )
    detail_output_dir.mkdir(parents=True, exist_ok=True)

    # --resume：只执行未完成的 request（对应结果文件不存在的跳过已完成的）
    if getattr(args, "resume", False):
        todo = []
        for f in files:
            result_path = get_result_path_for_request(f, detail_output_dir)
            if not result_path.exists():
                todo.append(f)
            else:
                print(f"[resume] 跳过已完成: {f.name} -> {result_path.name}")
        files = todo
        if not files:
            print("所有请求均已有结果，无需执行。")
            return
        print(f"[resume] 待执行 {len(files)} 个未完成请求")

    retry_times = getattr(args, "retry", 0)

    async with create_client_from_config(api_config=api_config) as client:
        for file_path in files:
            print(f"\n=== 开始处理: {file_path.name} ===")
            last_result = None
            for attempt in range(1 + retry_times):
                if attempt > 0:
                    delay_sec = 2 * attempt  # 重试间隔 2s, 4s, ...
                    print(f"  第 {attempt + 1} 次尝试（{delay_sec}s 后重试）...")
                    await asyncio.sleep(delay_sec)
                result = await run_for_file(
                    client, file_path, max_attempts, interval_ms
                )
                last_result = result
                success = result.get("success", False)
                detail_ok = (
                    result.get("detail_result", {}).get("success")
                    if result.get("detail_result") is not None
                    else None
                )
                if success and (detail_ok is None or detail_ok):
                    break
                if attempt < retry_times:
                    print(
                        f"  本轮未成功 (success={success}, detail_ok={detail_ok})，将重试"
                    )
            result = last_result

            query_ok = result.get("query_result", {}).get("success")
            detail_ok = (
                result.get("detail_result", {}).get("success")
                if result.get("detail_result") is not None
                else None
            )

            print(
                f"结果: success={result.get('success')} | "
                f"job_status={result.get('query_result', {}).get('job_status')} | "
                f"detail_success={detail_ok}"
            )
            if result.get("error"):
                print(f"error: {result['error']}")
            if result.get("detail_result") and not detail_ok:
                print(f"detail_error: {result['detail_result'].get('error')}")

            # 保存 detail 结果到本地文件
            if result.get("detail_result"):
                detail_result = result.get("detail_result")

                # 将 uuid 和 job_id 添加到结果中
                if result.get("uuid"):
                    detail_result["uuid"] = result["uuid"]
                if result.get("job_id"):
                    detail_result["job_id"] = result["job_id"]

                # 生成输出文件名：将原文件名中的 brief_case_ 替换为 batch_query_
                # 如果存在 job_id，则包含在文件名中
                base_filename = file_path.stem.replace("brief_case_", "mp_result_")
                detail_filename = f"{base_filename}.json"
                detail_output_path = detail_output_dir / detail_filename

                try:
                    # 保存完整的 detail_result 数据（包含 uuid 和 job_id）
                    with detail_output_path.open("w", encoding="utf-8") as f:
                        json.dump(detail_result, f, ensure_ascii=False, indent=2)
                    print(f"✓ 批量查询结果已保存: {detail_output_path}")
                except Exception as e:
                    print(f"✗ 保存批量查询结果失败: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量调用 output 目录中的请求 JSON")
    parser.add_argument(
        "--dir",
        default="output/xiaomi/requests_stage_media_stability_from_brief",
        help="请求 JSON 所在目录（例如：output/common/requests 或 output/xiaomi/requests）",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=None,
        help="轮询最大次数，默认使用配置中的 TESTING 环境",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="轮询间隔(ms)，默认使用配置中的 TESTING 环境",
    )
    parser.add_argument(
        "--brief-detail",
        type=str,
        default=None,
        help="批量查询接口 URL 模板，需包含 {job_id} 占位符（可选，默认根据目录路径自动选择配置）",
    )
    parser.add_argument(
        "--version",
        type=str,
        choices=["common", "xiaomi"],
        default="xiaomi",
        help="指定 API 版本（common 或 xiaomi），如果不指定则根据目录路径自动判断",
    )
    parser.add_argument(
        "--algo-version",
        type=str,
        default="20260326_v1",
        help="算法版本标识（如 20250226_v1、v2.0）。不指定时使用配置或环境变量 MEDIAPLAN_ALGO_VERSION，默认 latest。结果将保存到 output/<common|xiaomi>/results/<algo_version>/",
    )
    parser.add_argument(
        "--environment",
        type=str,
        choices=["TEST", "PRE", "PROD"],
        default="TEST",
        help="指定环境（TEST、PRE 或 PROD，也支持 TESTING、STAGING、PRODUCTION），默认使用 PROD",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="断点续跑：只执行未完成的 request（已存在对应 mp_result_*.json 的请求将跳过）",
    )
    parser.add_argument(
        "--retry",
        type=int,
        default=0,
        metavar="N",
        help="单个请求失败时的重试次数（默认 0 不重试）。每次重试间隔递增（2s、4s…）",
    )

    args = parser.parse_args()

    asyncio.run(main(args))
