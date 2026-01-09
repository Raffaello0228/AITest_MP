#!/usr/bin/env python3
"""
性能测试工具脚本
用于执行分批次性能测试，测试 brief-save 和 brief-submit-query 接口的性能表现

使用方式：
    python tools/performance_test.py --version common --environment PRE
    python tools/performance_test.py --version xiaomi --environment TEST --start-concurrency 2 --max-concurrency 10
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.performance_tester import PerformanceTester
from core.api_config import get_api_config, get_strategy_config, StrategyConfig


def load_request_bodies_from_dir(directory: Path) -> Optional[List[Dict[str, Any]]]:
    """从目录加载所有请求JSON文件"""
    if not directory.exists():
        return None

    json_files = sorted(directory.glob("*.json"))
    if not json_files:
        return None

    request_bodies = []
    for json_file in json_files:
        try:
            with json_file.open("r", encoding="utf-8") as f:
                request_bodies.append(json.load(f))
        except Exception as e:
            print(f"警告：无法加载 {json_file}: {e}")

    return request_bodies if request_bodies else None


async def main(args):
    """主函数"""
    # 获取API配置
    version = args.version or "common"
    environment = args.environment or "PRE"
    api_config = get_api_config(version, environment)

    print(f"使用 {version} 版本 API 配置，环境: {environment}")

    # 获取或创建策略配置
    if args.start_concurrency or args.max_concurrency or args.step_size:
        # 从命令行参数创建策略配置
        base_strategy = get_strategy_config()
        strategy_config = StrategyConfig(
            name="自定义性能测试策略",
            start_concurrency=args.start_concurrency or base_strategy.start_concurrency,
            max_concurrency=args.max_concurrency or base_strategy.max_concurrency,
            step_size=args.step_size or base_strategy.step_size,
            batch_delay=args.batch_delay or base_strategy.batch_delay,
            success_rate_threshold=args.success_rate_threshold
            or base_strategy.success_rate_threshold,
            max_failure_rate=args.max_failure_rate or base_strategy.max_failure_rate,
            max_polling_attempts=args.max_polling_attempts
            or base_strategy.max_polling_attempts,
            polling_interval=args.polling_interval or base_strategy.polling_interval,
        )
    else:
        # 使用默认策略配置
        strategy_config = None

    # 加载请求体（如果指定了目录）
    request_bodies = None
    if args.request_dir:
        request_dir = Path(args.request_dir)
        request_bodies = load_request_bodies_from_dir(request_dir)
        if request_bodies:
            print(f"从 {request_dir} 加载了 {len(request_bodies)} 个请求文件")
        else:
            print(f"警告：从 {request_dir} 未找到请求文件，将使用默认请求体")

    # 创建性能测试器
    async with PerformanceTester(
        api_config=api_config,
        strategy_config=strategy_config,
        request_json_path=args.request_json,
        default_request_body=args.request_body,
    ) as tester:
        # 执行性能测试
        results = await tester.run_strategy_test(request_bodies)

        # 保存结果
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n测试结果已保存到: {output_path}")
        else:
            # 默认保存到 output/performance_test_results.json
            output_path = project_root / "output" / "performance_test_results.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n测试结果已保存到: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="性能测试工具 - 测试 brief-save 和 brief-submit-query 接口的性能表现"
    )

    # 基本配置
    parser.add_argument(
        "--version",
        type=str,
        choices=["common", "xiaomi"],
        default=None,
        help="指定版本（common 或 xiaomi），如果不指定则使用 common",
    )
    parser.add_argument(
        "--environment",
        type=str,
        choices=["TEST", "PRE", "PROD"],
        default="PRE",
        help="指定环境（TEST、PRE 或 PROD），默认使用 PRE",
    )

    # 策略配置
    parser.add_argument(
        "--start-concurrency",
        type=int,
        default=None,
        help="起始并发数（默认从配置文件读取）",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=None,
        help="最大并发数（默认从配置文件读取）",
    )
    parser.add_argument(
        "--step-size",
        type=int,
        default=None,
        help="并发数步长（默认从配置文件读取）",
    )
    parser.add_argument(
        "--batch-delay",
        type=int,
        default=None,
        help="批次间延迟（毫秒，默认从配置文件读取）",
    )
    parser.add_argument(
        "--success-rate-threshold",
        type=float,
        default=None,
        help="成功率阈值（0.0-1.0，默认从配置文件读取）",
    )
    parser.add_argument(
        "--max-failure-rate",
        type=float,
        default=None,
        help="最大失败率（0.0-1.0，默认从配置文件读取）",
    )
    parser.add_argument(
        "--max-polling-attempts",
        type=int,
        default=None,
        help="最大轮询次数（默认从配置文件读取）",
    )
    parser.add_argument(
        "--polling-interval",
        type=int,
        default=None,
        help="轮询间隔（毫秒，默认从配置文件读取）",
    )

    # 请求配置
    parser.add_argument(
        "--request-dir",
        type=str,
        default=None,
        help="请求JSON文件所在目录（例如：output/xiaomi/requests），如果指定，将使用该目录下的所有JSON文件作为请求体",
    )
    parser.add_argument(
        "--request-json",
        type=str,
        default=None,
        help="request.json文件路径（可选）",
    )
    parser.add_argument(
        "--request-body",
        type=str,
        default=None,
        help="请求体JSON字符串（可选，优先级低于 --request-dir）",
    )

    # 输出配置
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="结果输出文件路径（默认：output/performance_test_results.json）",
    )

    args = parser.parse_args()

    # 解析请求体JSON字符串（如果提供）
    if args.request_body:
        try:
            args.request_body = json.loads(args.request_body)
        except json.JSONDecodeError as e:
            print(f"错误：无法解析 --request-body 参数: {e}")
            sys.exit(1)

    asyncio.run(main(args))
