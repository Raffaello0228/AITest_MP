#!/usr/bin/env python3
"""
批量读取 output 目录下的 JSON 请求，调用 API 完整流程，并在任务成功后拉取批量查询结果。

使用方式：
    python api_client/run_output_requests.py --dir output --max-attempts 200 --interval 2000 \
        --brief-detail https://pre-pu-gateway.meetsocial.com/sino-adtech-mediaplan/mediaPlan/result/multi-country/{job_id}/mp-query-batch
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
    API_CONFIG,
    API_CONFIG_XIAOMI,
    ENVIRONMENT_CONFIGS,
    get_api_config,
    get_strategy_config,
)


def load_request_body(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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

    # 获取环境配置（默认使用 TEST）
    environment = args.environment or "PRE"

    # 从策略配置获取轮询参数
    strategy_config = get_strategy_config()
    max_attempts = args.max_attempts or strategy_config.max_polling_attempts
    interval_ms = args.interval or strategy_config.polling_interval

    # 根据命令行参数或目录路径自动判断版本
    if args.version:
        version = args.version
    else:
        # 如果路径包含 "xiaomi" 则使用小米版配置
        version = "xiaomi" if "xiaomi" in str(output_dir).lower() else "common"
    api_config = get_api_config(version, environment)
    print(f"使用 {version} 版本 API 配置，环境: {environment}")

    # 创建批量查询结果输出目录
    # 如果输入目录是 requests，则结果输出到同级的 results 目录
    # 新结构：output/common/requests -> output/common/results
    #         output/xiaomi/requests -> output/xiaomi/results
    if output_dir.name == "requests":
        detail_output_dir = output_dir.parent / "results"
    else:
        # 如果直接指定了 output/common 或 output/xiaomi，则在其中创建 results
        detail_output_dir = output_dir / "results"
    detail_output_dir.mkdir(parents=True, exist_ok=True)

    async with create_client_from_config(api_config=api_config) as client:
        for file_path in files:
            print(f"\n=== 开始处理: {file_path.name} ===")
            result = await run_for_file(client, file_path, max_attempts, interval_ms)

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
        default="output/xiaomi/requests",
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
        default=None,
        help="指定版本（common 或 xiaomi），如果不指定则根据目录路径自动判断",
    )
    parser.add_argument(
        "--environment",
        type=str,
        choices=["TEST", "PRE", "PROD", "TESTING", "STAGING", "PRODUCTION"],
        default=None,
        help="指定环境（TEST、PRE 或 PROD，也支持 TESTING、STAGING、PRODUCTION），默认使用 TEST",
    )

    args = parser.parse_args()

    asyncio.run(main(args))
