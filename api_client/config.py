#!/usr/bin/env python3
"""
性能测试配置文件
包含所有测试相关的配置信息
"""

from dataclasses import dataclass
from typing import Dict, List, Any


# 策略配置类
@dataclass
class StrategyConfig:
    """策略配置"""

    name: str
    start_concurrency: int
    max_concurrency: int
    step_size: int
    batch_delay: int
    success_rate_threshold: float
    max_failure_rate: float


# 环境配置类
@dataclass
class EnvironmentConfig:
    """环境配置"""

    name: str
    batch_delay: int
    max_polling_attempts: int
    polling_interval: int


# 日志配置
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "log_dir": "logs",
    "log_filename_template": "api_performance_test_{timestamp}.log",
    "console_output": True,
    "file_encoding": "utf-8",
}

# 并发监控配置
CONCURRENCY_CONFIG = {
    "max_concurrency_threshold": 16,
    "enable_concurrency_monitoring": True,
}

# 预设策略配置
PRESET_STRATEGIES = {
    "CONSERVATIVE": StrategyConfig(
        name="保守策略",
        start_concurrency=2,
        max_concurrency=20,
        step_size=2,
        batch_delay=10000,
        success_rate_threshold=0.9,
        max_failure_rate=0.1,
    ),
    "STANDARD": StrategyConfig(
        name="标准策略",
        start_concurrency=2,
        max_concurrency=50,
        step_size=2,
        batch_delay=5000,
        success_rate_threshold=0.8,
        max_failure_rate=0.2,
    ),
    "AGGRESSIVE": StrategyConfig(
        name="激进策略",
        start_concurrency=2,
        max_concurrency=100,
        step_size=5,
        batch_delay=3000,
        success_rate_threshold=0.7,
        max_failure_rate=0.3,
    ),
    "CUSTOM": StrategyConfig(
        name="自定义策略",
        start_concurrency=11,
        max_concurrency=50,
        step_size=2,
        batch_delay=5000,
        success_rate_threshold=0.01,
        max_failure_rate=0.99,
    ),
}

# 环境配置
ENVIRONMENT_CONFIGS = {
    "DEVELOPMENT": EnvironmentConfig(
        name="开发环境",
        batch_delay=3000,
        max_polling_attempts=20000,
        polling_interval=1500,
    ),
    "TESTING": EnvironmentConfig(
        name="测试环境",
        batch_delay=5000,
        max_polling_attempts=30000,
        polling_interval=2000,
    ),
    "STAGING": EnvironmentConfig(
        name="预生产环境",
        batch_delay=8000,
        max_polling_attempts=40000,
        polling_interval=2500,
    ),
    "PRODUCTION": EnvironmentConfig(
        name="生产环境",
        batch_delay=15000,
        max_polling_attempts=50000,
        polling_interval=3000,
    ),
}

API_CONFIG = {
    "GET_UUID_URL": "https://pre-pu-gateway.meetsocial.com/sino-adtech-mediaplan/mediaPlan/brief/get-signed-uuid",
    "SAVE_URL": "https://pre-pu-gateway.meetsocial.com/sino-adtech-mediaplan/mediaPlan/brief/multi-country/brief-save",
    "QUERY_URL_TEMPLATE": "https://pre-pu-gateway.meetsocial.com/sino-adtech-mediaplan/mediaPlan/job/{job_id}/brief-submit-query",
    "BRIEF_DETAIL_URL_TEMPLATE": "https://pre-pu-gateway.meetsocial.com/sino-adtech-mediaplan/mediaPlan/brief/multi-country/{task_id}/brief-detail",
    "COMMON_HEADERS": {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "content-type": "application/json;charset=UTF-8",
        "origin": "https://pre-op.meetsocial.cn",
        "referer": "https://pre-op.meetsocial.cn/",
        "x-sino-global-userid": "2641",
        # !!! 替换为有效 token
        "x-sino-jwt-token": "eyJYLVNJTk8tVE9LRU4iOiJTLWU0ZmM2Mjg2OTkwOTQ2NjRhNGIzNzYxMTgwNjg5YzUzIiwiWC1TSU5PLUFQUC1JRCI6InNpbm8tb3AiLCJ0eXAiOiJKV1QiLCJYLVNJTk8tVE9LRU4tVFlQRSI6IlNTTyIsImFsZyI6IkhTMjU2In0.eyJ1c2VyTmFtZSI6InNpbW9uLnN1biIsImV4cCI6MTc2NTM0ODIxNiwidXNlcklkIjoyNjQxfQ.xUxMro9Runc1LsOpdJsth3F5vYQ0kWuE8P1ApVMipR0",
        "x-channel-access-token": "undefined",
        "x-channel-userid": "undefined",
        "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
    },
}
# BR_API_CONFIG = {
#     "GET_UUID_URL": "https://pre-pu-gateway.meetsocial.com/sino-adtech-mediaplan/mediaPlan/brief/get-signed-uuid",
#     "SAVE_URL": "https://pre-pu-gateway.meetsocial.com/sino-adtech-mediaplan/estimation/br/tasks/create",
#     "QUERY_URL_TEMPLATE": "https://pre-pu-gateway.meetsocial.com/sino-adtech-mediaplan/estimation/br/tasks/{job_id}/query",
# }
