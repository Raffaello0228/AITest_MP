#!/usr/bin/env python3
"""
API客户端模块
提供独立的接口调用功能，可在其他项目中复用
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import Dict, Optional, Any
import os


class APIClient:
    """API客户端类，封装所有接口调用功能"""

    def __init__(
        self,
        get_uuid_url: str,
        save_url: str,
        query_url_template: str,
        common_headers: Dict[str, str],
        request_json_path: Optional[str] = None,
        default_request_body: Optional[Dict] = None,
        brief_detail_url_template: Optional[str] = None,
        brief_detail_headers: Optional[Dict[str, str]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        初始化API客户端

        Args:
            get_uuid_url: 获取UUID的接口URL
            save_url: Save接口的URL
            query_url_template: 查询接口的URL模板，支持 {job_id} 占位符
            common_headers: 通用请求头
            request_json_path: request.json文件路径（可选）
            default_request_body: 默认请求体（可选）
            brief_detail_url_template: brief-detail 接口URL模板，支持 {task_id} 占位符（可选）
            brief_detail_headers: brief-detail 接口的请求头（可选，默认复用 common_headers）
            logger: 日志记录器（可选）
        """
        self.get_uuid_url = get_uuid_url
        self.save_url = save_url
        self.query_url_template = query_url_template
        self.common_headers = common_headers
        self.request_json_path = request_json_path
        self.default_request_body = default_request_body or {}
        self.brief_detail_url_template = brief_detail_url_template
        self.brief_detail_headers = brief_detail_headers
        self.logger = logger or self._setup_default_logger()
        self.session: Optional[aiohttp.ClientSession] = None

    @staticmethod
    def _setup_default_logger() -> logging.Logger:
        """设置默认日志记录器"""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    def build_save_body(self, uuid: str, request_body: Optional[Dict] = None) -> Dict:
        """
        构建Save接口的请求体

        Args:
            uuid: 任务UUID
            request_body: 自定义请求体（可选，如果提供则优先使用）

        Returns:
            构建好的请求体字典
        """
        # 优先使用传入的请求体
        if request_body:
            body = request_body.copy()
        # 其次尝试从request.json文件加载
        elif self.request_json_path and os.path.exists(self.request_json_path):
            try:
                with open(self.request_json_path, "r", encoding="utf-8") as f:
                    body = json.load(f)
                self.logger.info(f"成功从 {self.request_json_path} 加载接口参数")
            except Exception as e:
                self.logger.warning(
                    f"无法加载 request.json ({self.request_json_path})，使用默认配置: {e}"
                )
                body = self.default_request_body.copy()
        # 最后使用默认请求体
        else:
            body = self.default_request_body.copy()

        # 确保 basicInfo 存在并添加UUID
        if "basicInfo" not in body:
            body["basicInfo"] = {}
        body["basicInfo"]["taskId"] = uuid

        return body

    async def fetch_uuid(self) -> str:
        """
        获取一个UUID

        Returns:
            返回UUID字符串

        Raises:
            Exception: 当获取UUID失败时抛出异常
        """
        if not self.session:
            raise RuntimeError("API客户端未初始化，请使用 async with 语句")

        start_time = time.time()
        self.logger.info(f"开始获取UUID: {self.get_uuid_url}")

        try:
            async with self.session.post(
                self.get_uuid_url, headers=self.common_headers
            ) as response:
                response_time = int((time.time() - start_time) * 1000)
                response_text = await response.text()

                if response.status >= 400:
                    error_msg = f"get-uuid failed: {response.status} {response.reason} {response_text[:200]}"
                    self.logger.error(f"[UUID] {error_msg}")
                    raise Exception(error_msg)

                data = json.loads(response_text) if response_text else {}
                uuid = data.get("result")

                if not uuid:
                    error_msg = f"get-uuid parse error: {json.dumps(data)[:200]}"
                    self.logger.error(f"[UUID] {error_msg}")
                    raise Exception(error_msg)

                self.logger.info(f"[UUID] 获取成功: {uuid}, 耗时: {response_time}ms")
                return uuid

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            error_msg = f"UUID获取失败: {str(e)}"
            self.logger.error(f"[UUID] {error_msg}, 耗时: {response_time}ms")
            raise Exception(error_msg)

    async def save_task(
        self, uuid: str, request_body: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        调用Save接口创建任务

        Args:
            uuid: 任务UUID
            request_body: 自定义请求体（可选）

        Returns:
            包含以下字段的字典:
            - ok: bool, 是否成功
            - status: int, HTTP状态码
            - ms: int, 请求耗时（毫秒）
            - uuid: str, 任务UUID
            - job_id: Optional[str], 任务ID（成功时返回）
            - error: Optional[str], 错误信息（失败时返回）
        """
        if not self.session:
            raise RuntimeError("API客户端未初始化，请使用 async with 语句")

        start_time = time.time()
        body = self.build_save_body(uuid, request_body)

        self.logger.info(f"开始调用Save接口: {self.save_url}, UUID: {uuid}")

        try:
            async with self.session.post(
                self.save_url, headers=self.common_headers, json=body
            ) as response:
                save_time = int((time.time() - start_time) * 1000)
                response_text = await response.text()

                if response.status >= 400:
                    error_msg = (
                        f"Save failed: {response.status} - {response_text[:200]}"
                    )
                    self.logger.error(f"[SAVE] {error_msg}, 耗时: {save_time}ms")
                    return {
                        "ok": False,
                        "status": response.status,
                        "ms": save_time,
                        "uuid": uuid,
                        "job_id": None,
                        "error": error_msg,
                    }

                data = json.loads(response_text) if response_text else {}
                job_id = data.get("result", None)

                if job_id:
                    self.logger.info(
                        f"[SAVE] 成功创建任务, JobID: {job_id}, 耗时: {save_time}ms"
                    )
                else:
                    self.logger.warning(
                        f"[SAVE] 响应成功但未获取到JobID, 耗时: {save_time}ms"
                    )

                return {
                    "ok": True,
                    "status": response.status,
                    "ms": save_time,
                    "uuid": uuid,
                    "job_id": job_id,
                    "body_snippet": response_text[:500] if response_text else "",
                }

        except Exception as e:
            save_time = int((time.time() - start_time) * 1000)
            error_msg = f"Save exception: {str(e)}"
            self.logger.error(f"[SAVE] {error_msg}, 耗时: {save_time}ms")
            return {
                "ok": False,
                "status": 0,
                "ms": save_time,
                "uuid": uuid,
                "job_id": None,
                "error": error_msg,
            }

    async def query_job_status(
        self,
        job_id: str,
        max_attempts: int = 100,
        polling_interval_ms: int = 2000,
    ) -> Dict[str, Any]:
        """
        轮询查询任务状态

        Args:
            job_id: 任务ID
            max_attempts: 最大轮询次数
            polling_interval_ms: 轮询间隔（毫秒）

        Returns:
            包含以下字段的字典:
            - success: bool, 是否成功
            - job_status: str, 任务状态
            - attempts: int, 轮询次数
            - total_time: int, 总耗时（毫秒）
            - job_id: str, 任务ID
            - is_final: bool, 是否为最终状态
            - error: Optional[str], 错误信息（失败时返回）
        """
        if not self.session:
            raise RuntimeError("API客户端未初始化，请使用 async with 语句")

        if not job_id:
            return {
                "success": False,
                "error": "No jobId provided",
                "is_final": True,
                "job_status": "ERROR",
                "attempts": 0,
                "total_time": 0,
                "job_id": None,
            }

        query_url = self.query_url_template.format(job_id=job_id)
        start_time = time.time()

        self.logger.info(f"开始轮询任务状态: {job_id}")

        for attempt in range(1, max_attempts + 1):
            attempt_start_time = time.time()

            try:
                async with self.session.get(
                    query_url, headers=self.common_headers
                ) as response:
                    attempt_time = int((time.time() - attempt_start_time) * 1000)
                    response_text = await response.text()

                    if response.status >= 400:
                        error_msg = f"HTTP {response.status}: {response.reason}"
                        self.logger.error(
                            f"[QUERY] 轮询尝试 {attempt} 失败: {error_msg}, 耗时: {attempt_time}ms"
                        )
                        raise Exception(error_msg)

                    data = json.loads(response_text) if response_text else {}
                    job_status = data.get("result", {}).get("jobStatus") or data.get(
                        "jobStatus"
                    )

                    # 记录轮询信息
                    if attempt % 10 == 0 or job_status in [
                        "SUCCESS",
                        "FAILED",
                        "ERROR",
                    ]:
                        self.logger.info(
                            f"[QUERY] 轮询尝试 {attempt}: JobID={job_id}, 状态={job_status}, 耗时={attempt_time}ms"
                        )

                    # 检查任务状态 - 只有SUCCESS、FAILED、ERROR才视为最终状态
                    if job_status in ["SUCCESS", "FAILED", "ERROR"]:
                        total_time = int((time.time() - start_time) * 1000)
                        self.logger.info(
                            f"[QUERY] 任务完成: JobID={job_id}, 状态={job_status}, 总耗时={total_time}ms, 轮询次数={attempt}"
                        )
                        return {
                            "success": job_status == "SUCCESS",
                            "job_status": job_status,
                            "attempts": attempt,
                            "total_time": total_time,
                            "job_id": job_id,
                            "is_final": True,
                            "error": (
                                f"Job failed with status: {job_status}"
                                if job_status != "SUCCESS"
                                else None
                            ),
                        }

                    # 如果还在处理中，等待后继续轮询
                    if attempt < max_attempts:
                        await asyncio.sleep(polling_interval_ms / 1000)

            except Exception as error:
                attempt_time = int((time.time() - attempt_start_time) * 1000)
                self.logger.error(
                    f"[QUERY] 轮询尝试 {attempt} 异常: {str(error)}, 耗时: {attempt_time}ms"
                )
                if attempt < max_attempts:
                    await asyncio.sleep(polling_interval_ms / 1000)

        # 超过最大轮询次数 - 视为最终状态
        total_time = int((time.time() - start_time) * 1000)
        self.logger.warning(
            f"[QUERY] 轮询超时: JobID={job_id}, 总耗时={total_time}ms, 最大轮询次数={max_attempts}"
        )
        return {
            "success": False,
            "attempts": max_attempts,
            "total_time": total_time,
            "job_id": job_id,
            "error": f"Timeout after {max_attempts} attempts",
            "is_final": True,
            "job_status": "TIMEOUT",
        }

    async def fetch_brief_detail(self, task_id: str) -> Dict[str, Any]:
        """
        调用 brief-detail 接口获取详情。

        Args:
            task_id: brief 的 taskId（即创建时的 uuid）

        Returns:
            包含 success / status / body_snippet 或 error 的字典
        """
        if not self.session:
            raise RuntimeError("API客户端未初始化，请使用 async with 语句")
        if not self.brief_detail_url_template:
            raise RuntimeError(
                "未配置 brief_detail_url_template，无法调用 brief-detail 接口"
            )

        url = self.brief_detail_url_template.format(task_id=task_id)
        headers = self.brief_detail_headers or self.common_headers

        start_time = time.time()
        self.logger.info(f"开始调用 brief-detail: {url}")
        try:
            async with self.session.post(url, headers=headers) as response:
                cost = int((time.time() - start_time) * 1000)
                text = await response.text()

                if response.status >= 400:
                    error_msg = f"brief-detail failed: {response.status} {response.reason} {text[:200]}"
                    self.logger.error(f"[BRIEF-DETAIL] {error_msg}, 耗时: {cost}ms")
                    return {
                        "success": False,
                        "status": response.status,
                        "ms": cost,
                        "error": error_msg,
                        "body_snippet": text[:500] if text else "",
                    }

                self.logger.info(f"[BRIEF-DETAIL] 成功，耗时: {cost}ms")
                try:
                    data = json.loads(text) if text else {}
                except json.JSONDecodeError:
                    data = {"raw": text}

                return {
                    "success": True,
                    "status": response.status,
                    "ms": cost,
                    "data": data,
                    "body_snippet": text[:500] if text else "",
                }
        except Exception as e:
            cost = int((time.time() - start_time) * 1000)
            error_msg = f"brief-detail exception: {str(e)}"
            self.logger.error(f"[BRIEF-DETAIL] {error_msg}, 耗时: {cost}ms")
            return {
                "success": False,
                "status": 0,
                "ms": cost,
                "error": error_msg,
            }

    async def complete_workflow(
        self,
        uuid: Optional[str] = None,
        request_body: Optional[Dict] = None,
        max_polling_attempts: int = 100,
        polling_interval_ms: int = 2000,
    ) -> Dict[str, Any]:
        """
        完整的任务流程：获取UUID -> Save -> 轮询状态

        Args:
            uuid: 任务UUID（可选，如果不提供则自动获取）
            request_body: 自定义请求体（可选）
            max_polling_attempts: 最大轮询次数
            polling_interval_ms: 轮询间隔（毫秒）

        Returns:
            包含完整流程结果的字典
        """
        workflow_start = time.time()

        try:
            # 1. 获取UUID（如果未提供）
            if not uuid:
                uuid = await self.fetch_uuid()

            # 2. 调用Save接口
            save_result = await self.save_task(uuid, request_body)
            if not save_result["ok"]:
                return {
                    "success": False,
                    "uuid": uuid,
                    "job_id": None,
                    "save_result": save_result,
                    "query_result": None,
                    "total_time": int((time.time() - workflow_start) * 1000),
                    "error": save_result.get("error", "Save failed"),
                }

            job_id = save_result["job_id"]
            if not job_id:
                return {
                    "success": False,
                    "uuid": uuid,
                    "job_id": None,
                    "save_result": save_result,
                    "query_result": None,
                    "total_time": int((time.time() - workflow_start) * 1000),
                    "error": "Save succeeded but no job_id returned",
                }

            # 3. 轮询任务状态
            query_result = await self.query_job_status(
                job_id, max_polling_attempts, polling_interval_ms
            )

            total_time = int((time.time() - workflow_start) * 1000)

            detail_result: Optional[Dict[str, Any]] = None
            if query_result["success"] and self.brief_detail_url_template:
                detail_result = await self.fetch_brief_detail(uuid)

            success_all = query_result["success"] and (
                detail_result is None or detail_result.get("success", False)
            )

            return {
                "success": success_all,
                "uuid": uuid,
                "job_id": job_id,
                "save_result": save_result,
                "query_result": query_result,
                "detail_result": detail_result,
                "total_time": total_time,
                "error": (
                    detail_result.get("error")
                    if detail_result and not detail_result.get("success")
                    else query_result.get("error")
                ),
            }

        except Exception as e:
            total_time = int((time.time() - workflow_start) * 1000)
            error_msg = f"Workflow exception: {str(e)}"
            self.logger.error(f"[WORKFLOW] {error_msg}, 耗时: {total_time}ms")
            return {
                "success": False,
                "uuid": uuid,
                "job_id": None,
                "save_result": None,
                "query_result": None,
                "total_time": total_time,
                "error": error_msg,
            }


# 便捷函数：从配置创建客户端
def create_client_from_config(
    api_config: Dict[str, Any],
    request_json_path: Optional[str] = None,
    default_request_body: Optional[Dict] = None,
    brief_detail_url_template: Optional[str] = None,
    brief_detail_headers: Optional[Dict[str, str]] = None,
    logger: Optional[logging.Logger] = None,
) -> APIClient:
    """
    从配置字典创建API客户端

    Args:
        api_config: API配置字典，应包含:
            - GET_UUID_URL: 获取UUID的URL
            - SAVE_URL: Save接口的URL
            - QUERY_URL_TEMPLATE: 查询接口URL模板
            - COMMON_HEADERS: 通用请求头
        request_json_path: request.json文件路径（可选）
        default_request_body: 默认请求体（可选）
        brief_detail_url_template: brief-detail 接口URL模板（可选）
        brief_detail_headers: brief-detail 接口的请求头（可选）
        logger: 日志记录器（可选）

    Returns:
        APIClient实例
    """
    return APIClient(
        get_uuid_url=api_config["GET_UUID_URL"],
        save_url=api_config["SAVE_URL"],
        query_url_template=api_config["QUERY_URL_TEMPLATE"],
        common_headers=api_config["COMMON_HEADERS"],
        request_json_path=request_json_path,
        default_request_body=default_request_body,
        brief_detail_url_template=brief_detail_url_template,
        brief_detail_headers=brief_detail_headers,
        logger=logger,
    )
