# -*- coding: utf-8 -*-
"""
算法版本配置：用于按版本保留 results / achievement_checks，便于算法更新后快速评测。

版本来源（优先级从高到低）：
  1. 命令行参数 --algo-version
  2. 环境变量 MEDIAPLAN_ALGO_VERSION
  3. 配置文件 config/version_config.ini [version] algo_version
  4. 默认 "latest"

目录约定：
  - output/<common|xiaomi>/results/<algo_version>/    存放 mp_result_*.json
  - output/<common|xiaomi>/achievement_checks/json/<algo_version>/  存放 *_achievement_check.json
  - output/<common|xiaomi>/achievement_checks/reports/<algo_version>/  存放报告
  - 不指定版本时使用 "latest"，便于与旧脚本兼容（可把当前结果写到 latest）
"""

import os
from pathlib import Path
from typing import Optional

# 项目根目录（core/config 的上级的上级）
_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
_VERSION_INI = _CONFIG_DIR / "version_config.ini"


def get_algo_version(override: Optional[str] = None) -> str:
    """
    获取当前算法版本号。
    :param override: 命令行等传入的版本，优先级最高
    :return: 版本字符串，如 "latest"、"20250226_v1"
    """
    if override is not None and override.strip():
        return override.strip()
    env_val = os.environ.get("MEDIAPLAN_ALGO_VERSION", "").strip()
    if env_val:
        return env_val
    try:
        import configparser
        cfg = configparser.ConfigParser()
        if _VERSION_INI.exists():
            cfg.read(_VERSION_INI, encoding="utf-8")
            if cfg.has_section("version") and cfg.has_option("version", "algo_version"):
                return cfg.get("version", "algo_version").strip() or "latest"
    except Exception:
        pass
    return "latest"


def resolve_results_dir(
    project_root: Path,
    variant: str = "common",
    algo_version: Optional[str] = None,
) -> Path:
    """结果目录：output/<variant>/results/<algo_version>/"""
    version = algo_version if algo_version is not None else get_algo_version()
    return project_root / "output" / variant / "results" / version


def resolve_achievement_json_dir(
    project_root: Path,
    variant: str = "common",
    algo_version: Optional[str] = None,
) -> Path:
    """KPI 检查 JSON 目录：output/<variant>/achievement_checks/json/<algo_version>/"""
    version = algo_version if algo_version is not None else get_algo_version()
    return project_root / "output" / variant / "achievement_checks" / "json" / version


def resolve_achievement_reports_dir(
    project_root: Path,
    variant: str = "common",
    algo_version: Optional[str] = None,
) -> Path:
    """报告目录：output/<variant>/achievement_checks/reports/<algo_version>/"""
    version = algo_version if algo_version is not None else get_algo_version()
    return project_root / "output" / variant / "achievement_checks" / "reports" / version


def infer_algo_version_from_result_path(result_file: Path) -> Optional[str]:
    """
    从结果文件路径推断算法版本。
    约定：result_file 位于 .../output/<variant>/results/<algo_version>/mp_result_xxx.json
    若为 .../results/mp_result_xxx.json（无版本子目录）则返回 None。
    :return: 若路径中包含 results/<某版本>/ 则返回该版本，否则返回 None
    """
    try:
        result_file = result_file.resolve()
        parts = result_file.parts
        if "results" in parts:
            i = parts.index("results")
            if i + 1 < len(parts):
                next_part = parts[i + 1]
                # 下一层是文件名（如 mp_result_xxx.json）则无版本子目录
                if next_part.endswith(".json") or next_part.startswith("mp_result"):
                    return None
                return next_part
    except Exception:
        pass
    return None


def infer_variant_from_result_path(result_file: Path) -> str:
    """从结果文件路径推断 variant：common 或 xiaomi。"""
    try:
        result_file = result_file.resolve()
        parts = result_file.parts
        if "output" in parts:
            i = parts.index("output")
            if i + 1 < len(parts) and parts[i + 1] in ("common", "xiaomi"):
                return parts[i + 1]
    except Exception:
        pass
    return "common"
