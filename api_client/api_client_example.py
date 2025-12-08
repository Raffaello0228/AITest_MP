#!/usr/bin/env python3
"""
API客户端使用示例
演示如何在其他项目中使用api_client模块
"""

import asyncio
from api_client import APIClient, create_client_from_config
from config import API_CONFIG, TEST_DATA_CONFIG


async def example_basic_usage():
    """基本使用示例"""
    print("=== 示例1: 基本使用 ===")

    # 方式1: 直接创建客户端
    async with APIClient(
        get_uuid_url=API_CONFIG["GET_UUID_URL"],
        save_url=API_CONFIG["SAVE_URL"],
        query_url_template=API_CONFIG["QUERY_URL_TEMPLATE"],
        common_headers=API_CONFIG["COMMON_HEADERS"],
        request_json_path="request.json",  # 可选
        default_request_body=TEST_DATA_CONFIG,  # 可选
    ) as client:
        # 获取UUID
        uuid = await client.fetch_uuid()
        print(f"获取到UUID: {uuid}")

        # 调用Save接口
        save_result = await client.save_task(uuid)
        print(f"Save结果: {save_result}")

        if save_result["ok"] and save_result["job_id"]:
            # 轮询任务状态
            query_result = await client.query_job_status(
                save_result["job_id"],
                max_attempts=10,  # 最多轮询10次
                polling_interval_ms=2000,  # 每2秒轮询一次
            )
            print(f"查询结果: {query_result}")


async def example_from_config():
    """从配置创建客户端示例"""
    print("\n=== 示例2: 从配置创建客户端 ===")

    # 方式2: 从配置字典创建客户端
    async with create_client_from_config(
        api_config=API_CONFIG,
        request_json_path="request.json",
        default_request_body=TEST_DATA_CONFIG,
    ) as client:
        # 使用完整工作流
        result = await client.complete_workflow(
            uuid=None,  # 自动获取UUID
            max_polling_attempts=10,
            polling_interval_ms=2000,
        )
        print(f"完整工作流结果: {result}")


async def example_custom_request_body():
    """自定义请求体示例"""
    print("\n=== 示例3: 自定义请求体 ===")

    # 自定义请求体
    custom_body = {
        "basicInfo": {
            "taskId": "",  # 会被自动替换为UUID
            "totalBudget": 100000,
            "country": {"code": "US"},
        },
        # ... 其他字段
    }

    async with create_client_from_config(api_config=API_CONFIG) as client:
        uuid = await client.fetch_uuid()
        save_result = await client.save_task(uuid, request_body=custom_body)
        print(f"使用自定义请求体的Save结果: {save_result}")


async def example_batch_operations():
    """批量操作示例"""
    print("\n=== 示例4: 批量操作 ===")

    async with create_client_from_config(api_config=API_CONFIG) as client:
        # 并发获取多个UUID
        uuid_tasks = [client.fetch_uuid() for _ in range(5)]
        uuids = await asyncio.gather(*uuid_tasks)
        print(f"获取到 {len(uuids)} 个UUID: {uuids}")

        # 并发执行Save操作
        save_tasks = [client.save_task(uuid) for uuid in uuids]
        save_results = await asyncio.gather(*save_tasks)
        print(f"Save结果: {len([r for r in save_results if r['ok']])} 个成功")


async def main():
    """主函数"""
    try:
        await example_basic_usage()
        # await example_from_config()
        # await example_custom_request_body()
        # await example_batch_operations()
    except Exception as e:
        print(f"示例执行失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
