"""
数据加载模块：提供数据文件加载功能
"""
import traceback
import warnings
import numpy as np
import pandas as pd


def load_mapping(adtype_path: str) -> pd.DataFrame:
    """
    读取 adtype 映射表（CSV），标准化列名，主要按 (Media, Ad Type) 做映射。
    """
    try:
        # 先尝试 utf-8，如果失败再回退到常见的本地编码（如 gbk）
        try:
            df = pd.read_csv(adtype_path, encoding="utf-8")
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(adtype_path, encoding="gbk")
            except UnicodeDecodeError:
                # 最后兜底：使用 latin1 防止再次抛错（可能会出现少量乱码，但不影响英文字段）
                df = pd.read_csv(adtype_path, encoding="latin1")
        # 去掉前后空格
        df.columns = [c.strip() for c in df.columns]
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        print(f"[ERROR] 加载映射文件失败 {adtype_path}: {e}")
        traceback.print_exc()
        raise


def load_data(data_path: str) -> pd.DataFrame:
    """
    读取历史数据 CSV（通用版），并做基本清洗。
    """
    try:
        df = pd.read_csv(data_path)

        # 统一列名
        df.columns = [c.strip() for c in df.columns]

        # 将 \N 等视为缺失
        df = df.replace({"\\N": np.nan})

        # 数值列转浮点
        num_cols = [
            "spend",
            "impressions",
            "clicks",
            "link_clicks",
            "engagements",
            "likes",
            "video_views",
            "video_watched_2s",
            "purchases",
            "leads",
            "follows",
        ]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        return df
    except Exception as e:
        print(f"[ERROR] 加载数据文件失败 {data_path}: {e}")
        traceback.print_exc()
        raise


def load_data_xiaomi(data_path: str) -> pd.DataFrame:
    """
    读取新格式数据 CSV（data_xiaomi.csv），并做基本清洗。
    格式：Country, Media, Media Channel, Stage, Objective, Creative, Ad format, Budget, Estimated Impressions, etc.
    """
    try:
        df = pd.read_csv(data_path)

        # 统一列名（去掉前后空格，处理换行符）
        df.columns = [
            c.strip().replace("\n", " ").replace("\r", "") for c in df.columns
        ]

        # 将 \N 等视为缺失
        # 使用 warnings 模块抑制 FutureWarning
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", category=FutureWarning, message=".*Downcasting behavior.*"
            )
            df = df.replace({"\\N": np.nan, "-": np.nan, "": np.nan})
        # 显式调用 infer_objects 以保留旧行为
        df = df.infer_objects(copy=False)

        # 映射字段名
        df = df.rename(
            columns={
                "Country": "country_code",
                "Ad format": "ad_type",
                "Media Channel": "media_channel",
                "Stage": "stage",  # 保留 stage 字段
                "Objective": "objective",
                "Creative": "creative",
            }
        )

        # 处理 Budget 字段（去掉 $ 和逗号）
        if "Budget" in df.columns:
            df["spend"] = (
                df["Budget"]
                .astype(str)
                .str.replace("$", "")
                .str.replace(",", "")
                .str.strip()
            )
            df["spend"] = pd.to_numeric(df["spend"], errors="coerce").fillna(0.0)
        else:
            df["spend"] = 0.0

        # 处理 KPI 字段（Estimated 开头的字段）
        kpi_mapping = {
            "Estimated Impressions": "impressions",
            "Estimated Views": "video_views",
            "Estimated Engagements": "engagements",
            "Estimated Clicks": "clicks",
        }

        for old_col, new_col in kpi_mapping.items():
            if old_col in df.columns:
                # 去掉逗号并转换为数值
                df[new_col] = df[old_col].astype(str).str.replace(",", "").str.strip()
                df[new_col] = pd.to_numeric(df[new_col], errors="coerce").fillna(0.0)
            else:
                df[new_col] = 0.0

        # 其他 KPI 字段设为 0
        for col in ["link_clicks", "likes", "purchases", "leads", "follows"]:
            if col not in df.columns:
                df[col] = 0.0

        # 如果没有 month_ 字段，使用 stage 作为阶段标识
        if "month_" not in df.columns:
            df["month_"] = df.get("stage", "").astype(str)

        # 确保 Media 字段存在（用于后续映射）
        if "Media" in df.columns:
            df["Media"] = df["Media"].astype(str).str.strip()
        elif "media" in df.columns:
            df["Media"] = df["media"].astype(str).str.strip()

        # 确保所有必需的 KPI 字段存在
        required_kpi_cols = {
            "spend": 0.0,
            "impressions": 0.0,
            "clicks": 0.0,
            "link_clicks": 0.0,
            "engagements": 0.0,
            "likes": 0.0,
            "video_views": 0.0,
            "purchases": 0.0,
            "follows": 0.0,
        }
        for col, default_val in required_kpi_cols.items():
            if col not in df.columns:
                df[col] = default_val
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default_val)

        return df
    except Exception as e:
        print(f"[ERROR] 加载数据文件失败 {data_path}: {e}")
        traceback.print_exc()
        raise


def load_country_dict(country_path: str) -> pd.DataFrame:
    """
    加载国家信息字典。
    """
    try:
        df = pd.read_csv(country_path, encoding="utf-8")
        df.columns = [c.strip() for c in df.columns]
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        print(f"[WARNING] 加载国家字典失败 {country_path}: {e}，将使用默认值")
        return pd.DataFrame()


def load_adformat_dict(adformat_path: str) -> pd.DataFrame:
    """
    加载广告格式字典（包含 creative 映射）。
    """
    try:
        df = pd.read_csv(adformat_path, encoding="utf-8")
        # 去掉列名前后空格，并统一列名
        df.columns = [c.strip() for c in df.columns]
        # 统一列名：将 "Media Channel " 等统一为 "Media Channel"
        # 先去掉所有列名的前后空格
        df.columns = [c.strip() for c in df.columns]
        # 统一可能的变体
        column_mapping = {
            "Ad Format": "Ad format",
            "ad format": "Ad format",
        }
        df.rename(columns=column_mapping, inplace=True)

        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        print(f"[WARNING] 加载广告格式字典失败 {adformat_path}: {e}，将使用推断方式")
        traceback.print_exc()
        return pd.DataFrame()

