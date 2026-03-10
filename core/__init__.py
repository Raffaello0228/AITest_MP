"""
Core 模块：提供底层数据处理、JSON 构建和 API 客户端功能
"""

from core.config import (
    KPI_KEYS,
    MAX_REGION_COUNT,
    ENVIRONMENT_CONFIGS,
    get_api_config,
    get_strategy_config,
)
from core.data import (
    load_data,
    load_data_xiaomi,
    load_mapping,
    load_country_dict,
    load_adformat_dict,
)
from core.utils import normalize_percentage_sum, reorder_priorities, safe_sum
from core.api import APIClient, create_client_from_config
from core.report import generate_markdown_report, generate_html_report
from core.performance import PerformanceTester, TaskResult, BatchResult, APILogger

__all__ = [
    "KPI_KEYS",
    "MAX_REGION_COUNT",
    "load_data",
    "load_data_xiaomi",
    "load_mapping",
    "load_country_dict",
    "load_adformat_dict",
    "normalize_percentage_sum",
    "reorder_priorities",
    "safe_sum",
    "APIClient",
    "create_client_from_config",
    "ENVIRONMENT_CONFIGS",
    "get_api_config",
    "get_strategy_config",
    "generate_markdown_report",
    "generate_html_report",
    "PerformanceTester",
    "TaskResult",
    "BatchResult",
    "APILogger",
]

# 注意：其他函数（如 attach_mapping, build_* 等）由于版本差异较大，
# 暂时保留在各自的工具文件中，后续可以进一步重构
