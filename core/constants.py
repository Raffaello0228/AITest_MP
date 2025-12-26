"""
常量定义
"""

KPI_KEYS = [
    "Impression",
    "Clicks",
    "LinkClicks",
    "VideoViews",
    "Engagement",
    "Followers",
    "Like",
    "Purchase",
]

# 若希望限制 JSON 中的推广区域（国家）数量，在此设置最大国家数；
# 例如设为 5 表示只保留花费最高的前 5 个国家；设为 None 则不过滤。
MAX_REGION_COUNT: int | None = None

