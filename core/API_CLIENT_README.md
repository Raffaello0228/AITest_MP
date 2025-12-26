# API客户端模块使用说明

## 概述

`api_client.py` 是一个独立的接口调用模块，提供了完整的API调用功能，可以在其他项目中复用。

## 功能特性

- ✅ 获取UUID接口调用
- ✅ Save任务创建接口调用
- ✅ 任务状态轮询查询
- ✅ 完整工作流（UUID -> Save -> 轮询）
- ✅ 支持自定义请求体
- ✅ 支持从配置文件加载请求体
- ✅ 完整的错误处理和日志记录
- ✅ 异步支持，可并发调用

## 安装依赖

```bash
pip install aiohttp
```

## 快速开始

### 方式1: 直接使用APIClient

```python
import asyncio
from core import APIClient

async def main():
    async with APIClient(
        get_uuid_url="https://api.example.com/get-uuid",
        save_url="https://api.example.com/save",
        query_url_template="https://api.example.com/query/{job_id}",
        common_headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer your-token",
        },
    ) as client:
        # 获取UUID
        uuid = await client.fetch_uuid()
        
        # 调用Save接口
        save_result = await client.save_task(uuid)
        
        # 轮询任务状态
        if save_result["ok"]:
            query_result = await client.query_job_status(
                save_result["job_id"],
                max_attempts=100,
                polling_interval_ms=2000,
            )

asyncio.run(main())
```

### 方式2: 从配置创建客户端

```python
import asyncio
from core import create_client_from_config

# 定义API配置
API_CONFIG = {
    "GET_UUID_URL": "https://api.example.com/get-uuid",
    "SAVE_URL": "https://api.example.com/save",
    "QUERY_URL_TEMPLATE": "https://api.example.com/query/{job_id}",
    "COMMON_HEADERS": {
        "Content-Type": "application/json",
        "Authorization": "Bearer your-token",
    },
}

async def main():
    async with create_client_from_config(api_config=API_CONFIG) as client:
        # 使用完整工作流
        result = await client.complete_workflow(
            uuid=None,  # 自动获取UUID
            max_polling_attempts=100,
            polling_interval_ms=2000,
        )
        print(f"工作流结果: {result}")

asyncio.run(main())
```

## API参考

### APIClient类

#### 初始化参数

- `get_uuid_url` (str): 获取UUID的接口URL
- `save_url` (str): Save接口的URL
- `query_url_template` (str): 查询接口的URL模板，支持 `{job_id}` 占位符
- `common_headers` (Dict[str, str]): 通用请求头
- `request_json_path` (Optional[str]): request.json文件路径（可选）
- `default_request_body` (Optional[Dict]): 默认请求体（可选）
- `logger` (Optional[logging.Logger]): 日志记录器（可选）

#### 方法

##### `fetch_uuid() -> str`

获取一个UUID。

**返回**: UUID字符串

**异常**: 当获取失败时抛出Exception

##### `save_task(uuid: str, request_body: Optional[Dict] = None) -> Dict[str, Any]`

调用Save接口创建任务。

**参数**:
- `uuid`: 任务UUID
- `request_body`: 自定义请求体（可选）

**返回**: 包含以下字段的字典
- `ok` (bool): 是否成功
- `status` (int): HTTP状态码
- `ms` (int): 请求耗时（毫秒）
- `uuid` (str): 任务UUID
- `job_id` (Optional[str]): 任务ID（成功时返回）
- `error` (Optional[str]): 错误信息（失败时返回）

##### `query_job_status(job_id: str, max_attempts: int = 100, polling_interval_ms: int = 2000) -> Dict[str, Any]`

轮询查询任务状态。

**参数**:
- `job_id`: 任务ID
- `max_attempts`: 最大轮询次数（默认100）
- `polling_interval_ms`: 轮询间隔（毫秒，默认2000）

**返回**: 包含以下字段的字典
- `success` (bool): 是否成功
- `job_status` (str): 任务状态（SUCCESS/FAILED/ERROR/TIMEOUT）
- `attempts` (int): 轮询次数
- `total_time` (int): 总耗时（毫秒）
- `job_id` (str): 任务ID
- `is_final` (bool): 是否为最终状态
- `error` (Optional[str]): 错误信息（失败时返回）

##### `complete_workflow(uuid: Optional[str] = None, request_body: Optional[Dict] = None, max_polling_attempts: int = 100, polling_interval_ms: int = 2000) -> Dict[str, Any]`

完整的任务流程：获取UUID -> Save -> 轮询状态。

**参数**:
- `uuid`: 任务UUID（可选，如果不提供则自动获取）
- `request_body`: 自定义请求体（可选）
- `max_polling_attempts`: 最大轮询次数（默认100）
- `polling_interval_ms`: 轮询间隔（毫秒，默认2000）

**返回**: 包含完整流程结果的字典

##### `build_save_body(uuid: str, request_body: Optional[Dict] = None) -> Dict`

构建Save接口的请求体。

**参数**:
- `uuid`: 任务UUID
- `request_body`: 自定义请求体（可选）

**返回**: 构建好的请求体字典

### 便捷函数

#### `create_client_from_config(api_config: Dict[str, Any], ...) -> APIClient`

从配置字典创建API客户端。

**参数**:
- `api_config`: API配置字典，应包含 `GET_UUID_URL`, `SAVE_URL`, `QUERY_URL_TEMPLATE`, `COMMON_HEADERS`
- `request_json_path`: request.json文件路径（可选）
- `default_request_body`: 默认请求体（可选）
- `logger`: 日志记录器（可选）

## 使用场景

### 1. 单个任务处理

```python
async with create_client_from_config(api_config=API_CONFIG) as client:
    result = await client.complete_workflow()
    if result["success"]:
        print(f"任务成功完成: {result['job_id']}")
```

### 2. 批量任务处理

```python
async with create_client_from_config(api_config=API_CONFIG) as client:
    # 并发获取UUID
    uuid_tasks = [client.fetch_uuid() for _ in range(10)]
    uuids = await asyncio.gather(*uuid_tasks)
    
    # 并发执行Save
    save_tasks = [client.save_task(uuid) for uuid in uuids]
    save_results = await asyncio.gather(*save_tasks)
    
    # 并发轮询状态
    query_tasks = [
        client.query_job_status(r["job_id"])
        for r in save_results
        if r["ok"] and r["job_id"]
    ]
    query_results = await asyncio.gather(*query_tasks)
```

### 3. 自定义请求体

```python
custom_body = {
    "basicInfo": {
        "taskId": "",  # 会被自动替换为UUID
        "totalBudget": 100000,
    },
    # ... 其他字段
}

async with create_client_from_config(api_config=API_CONFIG) as client:
    uuid = await client.fetch_uuid()
    result = await client.save_task(uuid, request_body=custom_body)
```

### 4. 从文件加载请求体

```python
async with create_client_from_config(
    api_config=API_CONFIG,
    request_json_path="request.json",  # 指定request.json路径
) as client:
    uuid = await client.fetch_uuid()
    result = await client.save_task(uuid)  # 自动从request.json加载
```

## 错误处理

所有方法都会记录详细的日志信息，包括：
- 请求URL和参数
- 响应状态和内容
- 错误信息
- 耗时统计

建议在生产环境中配置合适的日志级别：

```python
import logging

logger = logging.getLogger("api_client")
logger.setLevel(logging.INFO)  # 或 logging.WARNING

async with APIClient(..., logger=logger) as client:
    # ...
```

## 注意事项

1. **必须使用异步上下文管理器**: 使用 `async with` 语句确保HTTP会话正确关闭
2. **请求体中的UUID**: `build_save_body` 方法会自动将UUID添加到 `basicInfo.taskId` 字段
3. **轮询间隔**: 根据实际业务需求调整 `polling_interval_ms`，避免过于频繁的请求
4. **最大轮询次数**: 根据任务处理时间合理设置 `max_attempts`，避免无限等待
5. **并发控制**: 虽然支持并发调用，但请注意API服务器的并发限制

## 迁移指南

如果你之前使用的是 `performance_test_strategy.py` 中的接口调用代码，可以按以下方式迁移：

### 旧代码
```python
from performance_test_strategy import PerformanceTester

async with PerformanceTester() as tester:
    uuid = await tester.fetch_one_uuid()
    save_result = await tester.save_with_uuid(uuid, index=0)
    query_result = await tester.poll_job_status(save_result["job_id"], index=0)
```

### 新代码
```python
from core import create_client_from_config
from config import API_CONFIG

async with create_client_from_config(api_config=API_CONFIG) as client:
    uuid = await client.fetch_uuid()
    save_result = await client.save_task(uuid)
    query_result = await client.query_job_status(save_result["job_id"])
```

## 示例代码

完整的使用示例请参考 `api_client_example.py` 文件。

