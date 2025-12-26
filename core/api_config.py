#!/usr/bin/env python3
"""
性能测试配置文件
包含所有测试相关的配置信息
从外部配置文件加载配置
"""

import json
import configparser
from dataclasses import dataclass
from pathlib import Path
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
    max_polling_attempts: int
    polling_interval: int


# 环境配置类
@dataclass
class EnvironmentConfig:
    """环境配置"""

    name: str
    host_name: str


def _load_config_file(config_path: Path, default: Any = None) -> Any:
    """加载配置文件，如果文件不存在则返回默认值"""
    if config_path.exists():
        try:
            if config_path.suffix == ".json":
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            elif config_path.suffix == ".ini":
                # 对于没有 section 的 INI 文件，使用 DEFAULT section
                config = configparser.ConfigParser()
                # 读取文件内容，如果没有 section，添加 DEFAULT section
                with open(config_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 如果内容不包含 section header，添加 DEFAULT section
                    if not content.strip().startswith("["):
                        content = "[DEFAULT]\n" + content
                    config.read_string(content)
                return config
            elif config_path.suffix == ".txt":
                with open(config_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except Exception as e:
            print(f"警告：加载配置文件 {config_path} 失败: {e}，使用默认值")
    return default


# 获取配置文件路径（相对于项目根目录）
_CONFIG_DIR = Path(__file__).parent.parent / "config"

# 加载配置文件
_CONSTANT_COMMON = _load_config_file(_CONFIG_DIR / "constant_comon.json", {})
_CONSTANT_XIAOMI = _load_config_file(_CONFIG_DIR / "constant_xiaomi.json", {})
_CONSTANT_BR = _load_config_file(_CONFIG_DIR / "constant_br.json", {})
_PERFORMANCE_CONFIG = _load_config_file(_CONFIG_DIR / "performance_config.ini", None)

# 加载不同环境的 token
_TOKEN_TEST = _load_config_file(_CONFIG_DIR / "token_test.txt", "")
_TOKEN_PRE = _load_config_file(_CONFIG_DIR / "token_pre.txt", "")
_TOKEN_PROD = _load_config_file(_CONFIG_DIR / "token_prod.txt", "")

# Token 映射
_TOKEN_MAP = {
    "TEST": _TOKEN_TEST,
    "PRE": _TOKEN_PRE,
    "PROD": _TOKEN_PROD,
}

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


# 从配置文件加载性能参数
def _get_performance_value(key: str, default: Any = None) -> Any:
    """从 performance_config.ini 获取配置值"""
    if _PERFORMANCE_CONFIG is None:
        return default
    try:
        # INI 文件可能没有 section，尝试从 DEFAULT section 读取
        if _PERFORMANCE_CONFIG.has_option("DEFAULT", key):
            value = _PERFORMANCE_CONFIG.get("DEFAULT", key)
            # 尝试转换为数字
            try:
                if "." in value:
                    return float(value)
                return int(value)
            except ValueError:
                return value
    except Exception:
        pass
    return default


# 策略配置（直接从配置文件读取参数）
def get_strategy_config() -> StrategyConfig:
    """
    从配置文件获取策略配置

    Returns:
        StrategyConfig 实例
    """
    return StrategyConfig(
        name="性能测试策略",
        start_concurrency=_get_performance_value("start_concurrency", 2),
        max_concurrency=_get_performance_value("max_concurrency", 50),
        step_size=_get_performance_value("step_size", 2),
        batch_delay=_get_performance_value("batch_delay", 5000),
        success_rate_threshold=_get_performance_value("success_rate_threshold", 0.8),
        max_failure_rate=_get_performance_value("max_failure_rate", 0.2),
        max_polling_attempts=_get_performance_value("max_polling_attempts", 30000),
        polling_interval=_get_performance_value("polling_interval", 2000),
        max_concurrency_threshold=_get_performance_value(
            "max_concurrency_threshold", 16
        ),
        enable_concurrency_monitoring=_get_performance_value(
            "enable_concurrency_monitoring", True
        ),
    )


ENVIRONMENT_CONFIGS = {
    "TEST": EnvironmentConfig(
        name="测试环境",
        host_name="o-test-pu-gateway.meetsocial.cn",
    ),
    "PRE": EnvironmentConfig(
        name="预生产环境",
        host_name="pre-pu-gateway.meetsocial.cn",
    ),
    "PROD": EnvironmentConfig(
        name="生产环境",
        host_name="pu-gateway.meetsocial.cn",
    ),
}

# 基础请求头模板（不包含 token）
_BASE_HEADERS = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "content-type": "application/json;charset=UTF-8",
    "x-sino-global-userid": "2641",
}


def _get_common_headers(environment: str = "TESTING") -> Dict[str, str]:
    """
    根据环境获取请求头（包含对应环境的 token）

    Args:
        environment: 环境名称，"TESTING"、"STAGING" 或 "PRODUCTION"

    Returns:
        包含 token 的请求头字典
    """
    env_upper = environment.upper()
    token = _TOKEN_MAP.get(env_upper, _TOKEN_TEST)  # 默认使用 TESTING 的 token
    return {
        **_BASE_HEADERS,
        "x-sino-jwt-token": token,
    }


# 便捷函数：根据版本和环境获取配置
def get_api_config(
    version: str = "common", environment: str = "TESTING"
) -> Dict[str, Any]:
    """
    根据版本和环境获取对应的 API 配置

    Args:
        version: 版本名称，"common" 或 "xiaomi"
        environment: 环境名称，"TESTING"、"STAGING" 或 "PRODUCTION"

    Returns:
        API 配置字典（包含对应环境的 token）
    """
    # 获取对应版本的 API URL 配置
    api_urls = _CONSTANT_XIAOMI if version.lower() == "xiaomi" else _CONSTANT_COMMON

    # 获取对应环境的请求头（包含 token）
    headers = _get_common_headers(environment)

    return {
        **api_urls,
        "COMMON_HEADERS": headers,
    }
