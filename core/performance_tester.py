#!/usr/bin/env python3
"""
性能测试模块
提供分批次性能测试功能，用于测试 brief-save 和 brief-submit-query 接口的性能表现
"""

import asyncio
import json
import statistics
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from core.api_client import APIClient, create_client_from_config
from core.api_config import (
    get_api_config,
    get_strategy_config,
    LOGGING_CONFIG,
    CONCURRENCY_CONFIG,
)


@dataclass
class TaskResult:
    """任务结果"""

    index: int
    job_id: Optional[str]
    save_time: int
    poll_time: int
    poll_attempts: int
    total_time: int
    final_job_status: str
    is_final: bool
    success: bool
    task_status: str = "RUNNING"


@dataclass
class BatchResult:
    """批次结果"""

    concurrency: int
    timestamp: str
    batch_time: int
    total_tests: int
    successful_tests: int
    failed_tests: int
    success_rate: float
    failure_rate: float
    performance_metrics: Optional[Dict]
    task_time_details: List[TaskResult]
    config_name: str
    concurrency_stats: Optional[Dict] = None


class APILogger:
    """API接口日志记录器"""

    def __init__(self):
        self.request_id = 0
        self.active_tasks = 0  # 当前活跃任务数（EXECUTING状态）
        self.max_active_tasks = 0  # 历史最高活跃任务数
        self.task_start_times = {}  # 记录任务开始时间
        self.task_statuses = {}  # 记录任务状态
        self.max_concurrency_threshold = CONCURRENCY_CONFIG.get(
            "max_concurrency_threshold", 16
        )

    def get_next_request_id(self) -> int:
        """获取下一个请求ID"""
        self.request_id += 1
        return self.request_id

    def task_started(self, task_index: int):
        """任务开始执行"""
        self.task_start_times[task_index] = time.time()
        self.task_statuses[task_index] = "STARTED"

    def update_task_status(self, task_index: int, job_status: str):
        """更新任务状态"""
        previous_status = self.task_statuses.get(task_index, "UNKNOWN")
        self.task_statuses[task_index] = job_status

        # 如果状态变为EXECUTING，增加活跃任务数
        if job_status == "EXECUTING" and previous_status != "EXECUTING":
            self.active_tasks += 1
            if self.active_tasks > self.max_active_tasks:
                self.max_active_tasks = self.active_tasks

            if self.active_tasks > self.max_concurrency_threshold:
                print(
                    f"[CONCURRENCY-ALERT] 当前活跃任务数 {self.active_tasks} 超过阈值 {self.max_concurrency_threshold}！"
                )

        # 如果状态从EXECUTING变为其他状态，减少活跃任务数
        elif previous_status == "EXECUTING" and job_status != "EXECUTING":
            self.active_tasks = max(0, self.active_tasks - 1)

    def task_completed(self, task_index: int):
        """任务完成执行"""
        if task_index in self.task_start_times:
            del self.task_start_times[task_index]

        if self.task_statuses.get(task_index) == "EXECUTING":
            self.active_tasks = max(0, self.active_tasks - 1)

        if task_index in self.task_statuses:
            del self.task_statuses[task_index]

    def get_concurrency_stats(self) -> Dict:
        """获取并发统计信息"""
        return {
            "current_active_tasks": self.active_tasks,
            "max_active_tasks": self.max_active_tasks,
            "active_task_count": len(self.task_start_times),
        }

    def reset_concurrency_stats(self):
        """重置并发统计"""
        self.active_tasks = 0
        self.max_active_tasks = 0
        self.task_start_times.clear()
        self.task_statuses.clear()


class PerformanceTester:
    """性能测试器"""

    def __init__(
        self,
        api_config: Dict[str, Any],
        strategy_config=None,
        request_json_path: Optional[str] = None,
        default_request_body: Optional[Dict] = None,
    ):
        """
        初始化性能测试器

        Args:
            api_config: API配置字典
            strategy_config: 策略配置（可选，如果不提供则从配置文件读取）
            request_json_path: request.json文件路径（可选）
            default_request_body: 默认请求体（可选）
        """
        self.api_config = api_config
        self.strategy = strategy_config or get_strategy_config()
        self.request_json_path = request_json_path
        self.default_request_body = default_request_body
        self.client: Optional[APIClient] = None
        self.api_logger = APILogger()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.client = create_client_from_config(
            api_config=self.api_config,
            request_json_path=self.request_json_path,
            default_request_body=self.default_request_body,
        )
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def fetch_one_uuid(self) -> str:
        """获取一个UUID"""
        if not self.client:
            raise RuntimeError("Client not initialized")
        return await self.client.fetch_uuid()

    async def run_complete_test(
        self, uuid: str, index: int, request_body: Optional[Dict] = None
    ) -> TaskResult:
        """完整的测试流程：save + 轮询"""
        self.api_logger.task_started(index)

        try:
            # 1. 调用brief-save接口
            save_start = time.time()
            save_result = await self.client.save_task(uuid, request_body)
            save_time = int((time.time() - save_start) * 1000)

            if not save_result["ok"]:
                self.api_logger.task_completed(index)
                return TaskResult(
                    index=index,
                    job_id=None,
                    save_time=save_time,
                    poll_time=0,
                    poll_attempts=0,
                    total_time=save_time,
                    final_job_status="SAVE_FAILED",
                    is_final=True,
                    success=False,
                    task_status="FAILED",
                )

            job_id = save_result.get("job_id")

            # 2. 轮询brief-submit-query接口
            poll_start = time.time()
            poll_result = await self._poll_job_status_with_monitoring(
                uuid, index, job_id
            )
            poll_time = int((time.time() - poll_start) * 1000)

            self.api_logger.task_completed(index)

            return TaskResult(
                index=index,
                job_id=job_id,
                save_time=save_time,
                poll_time=poll_time,
                poll_attempts=poll_result.get("attempts", 0),
                total_time=save_time + poll_time,
                final_job_status=poll_result.get("job_status", "UNKNOWN"),
                is_final=poll_result.get("is_final", True),
                success=poll_result.get("success", False),
                task_status="COMPLETED",
            )
        except Exception as e:
            self.api_logger.task_completed(index)
            raise

    async def _poll_job_status_with_monitoring(
        self, uuid: str, index: int, job_id: Optional[str]
    ) -> Dict[str, Any]:
        """轮询任务状态（带并发监控）"""
        if not uuid:
            return {
                "success": False,
                "error": "No UUID provided",
                "index": index,
                "is_final": True,
                "attempts": 0,
            }

        # 使用 api_client 的 query_job_status 方法，但需要监控状态
        # 由于需要监控并发状态，我们需要自定义轮询逻辑
        query_url = self.api_config["QUERY_URL_TEMPLATE"].format(job_id=uuid)
        start_time = time.time()

        for attempt in range(1, self.strategy.max_polling_attempts + 1):
            try:
                if not self.client.session:
                    raise RuntimeError("Client session not initialized")
                # 注意：根据 api_client.py，这里应该使用 POST 请求
                async with self.client.session.post(
                    query_url, headers=self.api_config["COMMON_HEADERS"]
                ) as response:
                    if response.status >= 400:
                        raise Exception(f"HTTP {response.status}: {response.reason}")

                    response_text = await response.text()
                    data = json.loads(response_text) if response_text else {}
                    job_status = data.get("result", {}).get("jobStatus") or data.get(
                        "jobStatus"
                    )
                    actual_job_id = data.get("result", {}).get("jobId") or job_id

                    # 更新任务状态（用于并发监控）
                    if job_status:
                        self.api_logger.update_task_status(index, job_status)

                    # 检查任务状态 - 只有SUCCESS、FAILED、ERROR才视为最终状态
                    if job_status in ["SUCCESS", "FAILED", "ERROR"]:
                        total_time = int((time.time() - start_time) * 1000)
                        return {
                            "success": job_status == "SUCCESS",
                            "job_status": job_status,
                            "attempts": attempt,
                            "total_time": total_time,
                            "index": index,
                            "job_id": actual_job_id,
                            "is_final": True,
                            "error": (
                                f"Job failed with status: {job_status}"
                                if job_status != "SUCCESS"
                                else None
                            ),
                        }

                    # 如果还在处理中，等待后继续轮询
                    if attempt < self.strategy.max_polling_attempts:
                        await asyncio.sleep(self.strategy.polling_interval / 1000)

            except Exception as error:
                if attempt < self.strategy.max_polling_attempts:
                    await asyncio.sleep(self.strategy.polling_interval / 1000)

        # 超过最大轮询次数 - 视为最终状态
        total_time = int((time.time() - start_time) * 1000)
        return {
            "success": False,
            "attempts": self.strategy.max_polling_attempts,
            "total_time": total_time,
            "index": index,
            "job_id": job_id,
            "error": f"Timeout after {self.strategy.max_polling_attempts} attempts",
            "is_final": True,
        }

    async def run_concurrency_level(
        self, concurrency: int, request_bodies: Optional[List[Dict]] = None
    ) -> Optional[BatchResult]:
        """运行单个并发级别的测试"""
        # 重置并发统计
        self.api_logger.reset_concurrency_stats()

        print(f"\n=== 开始测试并发级别: {concurrency} ===")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)

        batch_start = time.time()

        try:
            # 1. 并发获取UUID
            print("\n1. 获取UUID...")
            t1 = time.time()

            uuid_tasks = [self.fetch_one_uuid() for _ in range(concurrency)]
            uuid_results = await asyncio.gather(*uuid_tasks, return_exceptions=True)

            ok_uuids = []
            uuid_failed = []

            for i, result in enumerate(uuid_results):
                if isinstance(result, Exception):
                    uuid_failed.append({"index": i, "error": str(result)})
                else:
                    ok_uuids.append(result)

            print(
                f"UUID获取结果 -> 成功: {len(ok_uuids)}, 失败: {len(uuid_failed)}, 耗时: {int((time.time() - t1) * 1000)}ms"
            )

            if not ok_uuids:
                print("没有获取到UUID，测试终止。")
                return None

            # 2. 并发执行完整的测试流程
            print("\n2. 执行完整测试流程...")
            t2 = time.time()

            # 准备请求体列表
            if request_bodies is None:
                request_bodies = [None] * len(ok_uuids)
            elif len(request_bodies) < len(ok_uuids):
                # 如果请求体数量不足，用None填充
                request_bodies.extend([None] * (len(ok_uuids) - len(request_bodies)))

            test_tasks = [
                self.run_complete_test(uuid, i, request_bodies[i])
                for i, uuid in enumerate(ok_uuids)
            ]
            test_results = await asyncio.gather(*test_tasks, return_exceptions=True)

            t3 = time.time()

            # 3. 分析结果
            print("\n3. 分析测试结果...")
            successes = []
            failures = []

            for result in test_results:
                if isinstance(result, Exception):
                    failures.append({"error": str(result)})
                elif result.success:
                    successes.append(result)
                else:
                    failures.append(result)

            # 4. 计算性能指标
            batch_time = int((t3 - batch_start) * 1000)
            success_rate = len(successes) / len(ok_uuids) if ok_uuids else 0
            failure_rate = len(failures) / len(ok_uuids) if ok_uuids else 0

            performance_metrics = None
            task_time_details = []

            if successes:
                save_times = [s.save_time for s in successes]
                poll_times = [s.poll_time for s in successes]
                total_times = [s.total_time for s in successes]
                poll_attempts = [s.poll_attempts for s in successes]

                performance_metrics = {
                    "save": {
                        "avg": int(statistics.mean(save_times)),
                        "min": min(save_times),
                        "max": max(save_times),
                    },
                    "poll": {
                        "avg_attempts": int(statistics.mean(poll_attempts)),
                        "avg_time": int(statistics.mean(poll_times)),
                        "min_time": min(poll_times),
                        "max_time": max(poll_times),
                    },
                    "total": {
                        "avg": int(statistics.mean(total_times)),
                        "min": min(total_times),
                        "max": max(total_times),
                    },
                }

                task_time_details = sorted(successes, key=lambda x: x.total_time)

            # 5. 输出统计信息
            concurrency_stats = self.api_logger.get_concurrency_stats()

            print(f"\n=== 并发级别 {concurrency} 测试结果 ===")
            print(f"批次总时间: {batch_time}ms")
            print(f"测试数量: {len(ok_uuids)}")
            print(f"完整成功: {len(successes)}")
            print(f"部分失败: {len(failures)}")
            print(f"成功率: {success_rate * 100:.2f}%")
            print(f"失败率: {failure_rate * 100:.2f}%")
            print(f"最高并发任务数: {concurrency_stats['max_active_tasks']}")
            print(f"当前活跃任务数: {concurrency_stats['current_active_tasks']}")

            if performance_metrics:
                print(f"\n--- Save接口性能 ---")
                print(f"平均耗时: {performance_metrics['save']['avg']}ms")
                print(f"最小耗时: {performance_metrics['save']['min']}ms")
                print(f"最大耗时: {performance_metrics['save']['max']}ms")

                print(f"\n--- 轮询性能 ---")
                print(f"平均轮询次数: {performance_metrics['poll']['avg_attempts']}")
                print(f"平均轮询总时间: {performance_metrics['poll']['avg_time']}ms")
                print(
                    f"轮询时间范围: {performance_metrics['poll']['min_time']}ms - {performance_metrics['poll']['max_time']}ms"
                )

                print(f"\n--- 总体性能 ---")
                print(f"平均总耗时: {performance_metrics['total']['avg']}ms")
                print(
                    f"总耗时范围: {performance_metrics['total']['min']}ms - {performance_metrics['total']['max']}ms"
                )

            # 6. 返回批次结果
            return BatchResult(
                concurrency=concurrency,
                timestamp=datetime.now().isoformat(),
                batch_time=batch_time,
                total_tests=len(ok_uuids),
                successful_tests=len(successes),
                failed_tests=len(failures),
                success_rate=success_rate,
                failure_rate=failure_rate,
                performance_metrics=performance_metrics,
                task_time_details=task_time_details,
                config_name=self.strategy.name,
                concurrency_stats=concurrency_stats,
            )

        except Exception as error:
            print(f"并发级别 {concurrency} 测试失败: {str(error)}")
            concurrency_stats = self.api_logger.get_concurrency_stats()
            return BatchResult(
                concurrency=concurrency,
                timestamp=datetime.now().isoformat(),
                batch_time=int((time.time() - batch_start) * 1000),
                total_tests=0,
                successful_tests=0,
                failed_tests=0,
                success_rate=0.0,
                failure_rate=1.0,
                performance_metrics=None,
                task_time_details=[],
                config_name=self.strategy.name,
                concurrency_stats=concurrency_stats,
            )

    async def run_strategy_test(
        self, request_bodies: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """执行分批次性能测试策略"""
        print("=== 分批次性能测试策略开始 ===")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试策略: {self.strategy.name}")
        print(
            f"测试策略: 以{self.strategy.step_size}为步长，从{self.strategy.start_concurrency}到{self.strategy.max_concurrency}并发"
        )
        print(f"批次间延迟: {self.strategy.batch_delay}ms")
        print(f"成功率阈值: {self.strategy.success_rate_threshold * 100:.1f}%")
        print(f"失败率阈值: {self.strategy.max_failure_rate * 100:.1f}%")
        print("=" * 50)

        overall_start = time.time()
        all_results = []
        should_continue = True

        # 按步长逐步增加并发数
        for concurrency in range(
            self.strategy.start_concurrency,
            self.strategy.max_concurrency + 1,
            self.strategy.step_size,
        ):
            if not should_continue:
                break

            print(f"\n🚀 准备测试并发级别: {concurrency}")

            # 执行当前并发级别的测试
            batch_result = await self.run_concurrency_level(concurrency, request_bodies)

            if batch_result:
                all_results.append(batch_result)

                # 检查是否应该继续测试
                if batch_result.success_rate < self.strategy.success_rate_threshold:
                    print(
                        f"\n⚠️  成功率 {batch_result.success_rate * 100:.1f}% 低于阈值 {self.strategy.success_rate_threshold * 100:.1f}%，停止测试"
                    )
                    should_continue = False
                elif batch_result.failure_rate > self.strategy.max_failure_rate:
                    print(
                        f"\n⚠️  失败率 {batch_result.failure_rate * 100:.1f}% 高于阈值 {self.strategy.max_failure_rate * 100:.1f}%，停止测试"
                    )
                    should_continue = False

            # 如果不是最后一个批次，等待后继续
            if (
                should_continue
                and concurrency + self.strategy.step_size
                <= self.strategy.max_concurrency
            ):
                print(f"\n⏳ 等待 {self.strategy.batch_delay}ms 后开始下一个批次...")
                await asyncio.sleep(self.strategy.batch_delay / 1000)

        # 保存所有结果
        complete_results = {
            "timestamp": datetime.now().isoformat(),
            "strategy": self.strategy.name,
            "config": {
                "strategy": asdict(self.strategy),
            },
            "overall_time": int((time.time() - overall_start) * 1000),
            "batches": [asdict(r) for r in all_results],
            "summary": {
                "total_batches": len(all_results),
                "total_tests": sum(r.total_tests for r in all_results),
                "total_successful_tests": sum(r.successful_tests for r in all_results),
                "total_failed_tests": sum(r.failed_tests for r in all_results),
                "max_concurrency_tested": (
                    max(r.concurrency for r in all_results) if all_results else 0
                ),
                "average_success_rate": (
                    sum(r.success_rate for r in all_results) / len(all_results)
                    if all_results
                    else 0
                ),
                "average_failure_rate": (
                    sum(r.failure_rate for r in all_results) / len(all_results)
                    if all_results
                    else 0
                ),
            },
        }

        print(f"\n=== 总体测试统计 ===")
        print(f"总测试时间: {complete_results['overall_time']}ms")
        print(f"测试批次数: {complete_results['summary']['total_batches']}")
        print(f"总测试数: {complete_results['summary']['total_tests']}")
        print(f"总成功数: {complete_results['summary']['total_successful_tests']}")
        print(f"总失败数: {complete_results['summary']['total_failed_tests']}")
        print(
            f"最大测试并发数: {complete_results['summary']['max_concurrency_tested']}"
        )
        print(
            f"平均成功率: {complete_results['summary']['average_success_rate'] * 100:.2f}%"
        )
        print(
            f"平均失败率: {complete_results['summary']['average_failure_rate'] * 100:.2f}%"
        )

        print(f"\n=== 分批次性能测试策略完成 ===")

        return complete_results
