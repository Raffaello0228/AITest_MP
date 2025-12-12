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

from api_client import create_client_from_config
from config import API_CONFIG, ENVIRONMENT_CONFIGS


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

    env_cfg = ENVIRONMENT_CONFIGS.get("TESTING")
    max_attempts = args.max_attempts or env_cfg.max_polling_attempts
    interval_ms = args.interval or env_cfg.polling_interval

    # 批量查询接口配置：优先使用命令行参数，其次使用 API_CONFIG 中的配置
    brief_detail_tmpl = args.brief_detail or API_CONFIG.get("BRIEF_DETAIL_URL_TEMPLATE")

    # 创建批量查询结果输出目录（在 output 目录下，而不是在 requests 目录下）
    output_base = output_dir.parent if output_dir.name == "requests" else output_dir
    detail_output_dir = output_base / "results"
    detail_output_dir.mkdir(parents=True, exist_ok=True)

    async with create_client_from_config(api_config=API_CONFIG) as client:
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
    parser.add_argument("--dir", default="output/requests", help="请求 JSON 所在目录")
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
        help="批量查询接口 URL 模板，需包含 {job_id} 占位符（可选，默认使用 config.py 中的配置）",
    )

    args = parser.parse_args()

    asyncio.run(main(args))
