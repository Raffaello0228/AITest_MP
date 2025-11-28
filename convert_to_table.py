import json
import pandas as pd
from collections import defaultdict


def convert_json_to_table(json_file_path, output_file_path):
    """
    将JSON列表转换为表格格式，将metric的枚举值作为列名

    Args:
        json_file_path: JSON文件路径
        output_file_path: 输出Excel文件路径
    """
    # 读取JSON文件
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 获取所有唯一的metric值
    metrics = sorted(list(set(item["metric"] for item in data)))

    # 创建用于存储表格数据的字典
    table_data = defaultdict(dict)

    # 遍历数据，按维度、广告类型、媒体、平台分组
    for item in data:
        # 创建唯一键
        key = (item["dimension"], item["adType"], item["media"], item["platform"])

        # 如果这个组合还没有记录，初始化
        if key not in table_data:
            table_data[key] = {
                "dimension": item["dimension"],
                "adType": item["adType"],
                "media": item["media"],
                "platform": item["platform"],
            }

        # 添加metric值
        table_data[key][item["metric"]] = item["value"]

    # 转换为DataFrame
    df = pd.DataFrame(list(table_data.values()))

    # 重新排列列的顺序
    base_columns = ["dimension", "adType", "media", "platform"]
    metric_columns = [col for col in df.columns if col not in base_columns]
    df = df[base_columns + sorted(metric_columns)]

    # 保存到Excel文件
    df.to_excel(output_file_path, index=False, sheet_name="数据表")

    print(f"转换完成！")
    print(f"数据行数: {len(df)}")
    print(f"数据列数: {len(df.columns)}")
    print(f"基础列: {base_columns}")
    print(f"指标列: {sorted(metric_columns)}")
    print(f"输出文件: {output_file_path}")

    return df


if __name__ == "__main__":
    # 转换数据
    df = convert_json_to_table("example.json", "output/example_table.xlsx")

    # 显示前几行数据
    print("\n前5行数据:")
    print(df.head())
