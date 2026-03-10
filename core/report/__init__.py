"""
报告层：测试报告生成与 KPI 达成校验
"""

from core.report.generator import (
    generate_markdown_report,
    generate_html_report,
    load_json,
)

__all__ = [
    "generate_markdown_report",
    "generate_html_report",
    "load_json",
]
