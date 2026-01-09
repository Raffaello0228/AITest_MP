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
from typing import Dict, Any, Optional


# ============================================================================
# 数据类定义
# ============================================================================


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


@dataclass
class EnvironmentConfig:
    """环境配置"""

    name: str
    host_name: str


# ============================================================================
# 配置加载器
# ============================================================================


class ConfigLoader:
    """配置加载器，统一管理所有配置文件的加载"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化配置加载器

        Args:
            config_dir: 配置文件目录，默认为项目根目录下的 config 目录
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "config"
        self.config_dir = config_dir
        self._performance_config: Optional[configparser.ConfigParser] = None

        # 加载所有配置文件
        self._load_all_configs()

    def _load_all_configs(self):
        """加载所有配置文件"""
        # 加载性能配置文件
        self._performance_config = self._load_ini_file(
            self.config_dir / "performance_config.ini"
        )

    def _load_json_file(self, file_path: Path, default: Any = None) -> Any:
        """加载 JSON 配置文件"""
        if not file_path.exists():
            return default
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"警告：加载配置文件 {file_path} 失败: {e}，使用默认值")
            return default

    def _load_ini_file(self, file_path: Path) -> Optional[configparser.ConfigParser]:
        """加载 INI 配置文件"""
        if not file_path.exists():
            return None
        try:
            config = configparser.ConfigParser()
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # 如果内容不包含 section header，添加 DEFAULT section
                if not content.strip().startswith("["):
                    content = "[DEFAULT]\n" + content
                config.read_string(content)
            return config
        except Exception as e:
            print(f"警告：加载配置文件 {file_path} 失败: {e}")
            return None

    def _load_text_file(self, file_path: Path, default: str = "") -> str:
        """加载文本配置文件"""
        if not file_path.exists():
            return default
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            print(f"警告：加载配置文件 {file_path} 失败: {e}，使用默认值")
            return default

    def get_performance_value(self, key: str, default: Any = None) -> Any:
        """
        从 performance_config.ini 获取配置值

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            配置值，如果不存在则返回默认值
        """
        if self._performance_config is None:
            return default

        try:
            if self._performance_config.has_option("DEFAULT", key):
                value = self._performance_config.get("DEFAULT", key)
                return self._convert_value(value)
        except Exception:
            pass
        return default

    def _convert_value(self, value: str) -> Any:
        """
        转换配置值为合适的类型

        Args:
            value: 字符串值

        Returns:
            转换后的值（int、float、bool 或 str）
        """
        # 尝试转换为数字
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            # 尝试转换为布尔值
            value_lower = value.lower()
            if value_lower in ("true", "1", "yes", "on"):
                return True
            elif value_lower in ("false", "0", "no", "off"):
                return False
            return value


# ============================================================================
# 全局配置加载器实例
# ============================================================================

_config_loader = ConfigLoader()
_CONFIG_DIR = _config_loader.config_dir

# ============================================================================
# 配置文件加载
# ============================================================================

# 加载 API 常量配置
_CONSTANT_COMMON = _config_loader._load_json_file(
    _CONFIG_DIR / "constant_comon.json", {}
)
_CONSTANT_XIAOMI = _config_loader._load_json_file(
    _CONFIG_DIR / "constant_xiaomi.json", {}
)
_CONSTANT_BR = _config_loader._load_json_file(_CONFIG_DIR / "constant_br.json", {})

# 加载 Token 配置
_TOKEN_TEST = _config_loader._load_text_file(_CONFIG_DIR / "token_test.txt")
_TOKEN_PRE = _config_loader._load_text_file(_CONFIG_DIR / "token_pre.txt")
_TOKEN_PROD = _config_loader._load_text_file(_CONFIG_DIR / "token_prod.txt")

# Token 映射
_TOKEN_MAP = {
    "TEST": _TOKEN_TEST,
    "PRE": _TOKEN_PRE,
    "PROD": _TOKEN_PROD,
}

# ============================================================================
# 性能测试配置
# ============================================================================

# 并发监控配置（从配置文件读取）
CONCURRENCY_CONFIG = {
    "max_concurrency_threshold": _config_loader.get_performance_value(
        "max_concurrency_threshold", 16
    ),
    "enable_concurrency_monitoring": _config_loader.get_performance_value(
        "enable_concurrency_monitoring", True
    ),
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


def get_strategy_config() -> StrategyConfig:
    """
    从配置文件获取策略配置

    Returns:
        StrategyConfig 实例
    """
    return StrategyConfig(
        name="性能测试策略",
        start_concurrency=_config_loader.get_performance_value("start_concurrency", 2),
        max_concurrency=_config_loader.get_performance_value("max_concurrency", 50),
        step_size=_config_loader.get_performance_value("step_size", 2),
        batch_delay=_config_loader.get_performance_value("batch_delay", 5000),
        success_rate_threshold=_config_loader.get_performance_value(
            "success_rate_threshold", 0.8
        ),
        max_failure_rate=_config_loader.get_performance_value("max_failure_rate", 0.2),
        max_polling_attempts=_config_loader.get_performance_value(
            "max_polling_attempts", 30000
        ),
        polling_interval=_config_loader.get_performance_value("polling_interval", 2000),
    )


# ============================================================================
# 环境配置
# ============================================================================

ENVIRONMENT_CONFIGS = {
    "TEST": EnvironmentConfig(
        name="测试环境",
        host_name="o-test-pu-gateway.meetsocial.com",
    ),
    "PRE": EnvironmentConfig(
        name="预生产环境",
        host_name="pre-pu-gateway.meetsocial.com",
    ),
    "PROD": EnvironmentConfig(
        name="生产环境",
        host_name="pu-gateway.meetsocial.com",
    ),
}

# ============================================================================
# HTTP 请求配置
# ============================================================================

# 基础请求头模板（不包含 token）
_BASE_HEADERS = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "content-type": "application/json;charset=UTF-8",
    "x-sino-global-userid": "2641",
}


def _normalize_environment(environment: str) -> str:
    """
    规范化环境名称

    Args:
        environment: 环境名称

    Returns:
        规范化后的环境名称（TEST、PRE 或 PROD）
    """
    env_upper = environment.upper()
    env_mapping = {
        "TESTING": "TEST",
        "STAGING": "PRE",
        "PRODUCTION": "PROD",
    }
    return env_mapping.get(env_upper, env_upper)


def _get_common_headers(environment: str = "TEST") -> Dict[str, str]:
    """
    根据环境获取请求头（包含对应环境的 token）

    Args:
        environment: 环境名称，"TEST"、"PRE" 或 "PROD"

    Returns:
        包含 token 的请求头字典
    """
    env_normalized = _normalize_environment(environment)
    token = _TOKEN_MAP.get(env_normalized, _TOKEN_TEST)
    return {
        **_BASE_HEADERS,
        "x-sino-jwt-token": token,
    }


# ============================================================================
# API 配置
# ============================================================================
def get_api_config(
    version: str = "common", environment: str = "TEST"
) -> Dict[str, Any]:
    """
    根据版本和环境获取对应的 API 配置

    Args:
        version: 版本名称，"common" 或 "xiaomi"
        environment: 环境名称，"TEST"、"PRE" 或 "PROD"
                    （也支持 "TESTING"、"STAGING"、"PRODUCTION"）

    Returns:
        API 配置字典（包含对应环境的 token 和 URL）
    """
    # 获取对应版本的 API URL 配置
    api_urls = _CONSTANT_XIAOMI if version.lower() == "xiaomi" else _CONSTANT_COMMON

    # 获取环境配置
    env_normalized = _normalize_environment(environment)
    env_config = ENVIRONMENT_CONFIGS.get(env_normalized, ENVIRONMENT_CONFIGS["TEST"])
    target_host = env_config.host_name

    # 根据环境替换 URL 中的 host
    updated_urls = {}
    for key, url in api_urls.items():
        if isinstance(url, str) and "://" in url:
            # 提取协议和路径
            parts = url.split("://", 1)
            if len(parts) == 2:
                protocol = parts[0]
                rest = parts[1]
                # 提取路径（host 之后的部分）
                path_parts = rest.split("/", 1)
                if len(path_parts) == 2:
                    path = "/" + path_parts[1]
                    # 替换 host
                    updated_urls[key] = f"{protocol}://{target_host}{path}"
                else:
                    updated_urls[key] = url
            else:
                updated_urls[key] = url
        else:
            updated_urls[key] = url

    # 获取对应环境的请求头（包含 token）
    headers = _get_common_headers(environment)

    return {
        **updated_urls,
        "COMMON_HEADERS": headers,
    }
