import json
import csv
from datetime import datetime


def create_csv_sample(json_file_path, sample_size=100):
    """
    从JSON文件创建CSV样本文件
    """

    print("正在读取JSON文件...")

    # 读取JSON文件
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"读取完成，共 {len(data)} 条记录")

    # 取前sample_size条记录作为样本
    sample_data = data[:sample_size]

    # 生成输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file_path = f"example_data_sample_{timestamp}.csv"

    print(f"正在创建CSV样本文件，包含 {len(sample_data)} 条记录...")

    # 写入CSV文件
    with open(output_file_path, "w", newline="", encoding="utf-8-sig") as csvfile:
        fieldnames = ["dimension", "media", "platform", "adType", "metric", "value"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in sample_data:
            writer.writerow(row)

    print(f"CSV样本文件已创建: {output_file_path}")

    # 显示数据统计
    dimensions = set(row["dimension"] for row in sample_data)
    medias = set(row["media"] for row in sample_data)
    platforms = set(row["platform"] for row in sample_data)
    ad_types = set(row["adType"] for row in sample_data)
    metrics = set(row["metric"] for row in sample_data)

    print(f"\n数据统计:")
    print(f"维度: {list(dimensions)}")
    print(f"媒体: {list(medias)}")
    print(f"平台: {list(platforms)}")
    print(f"广告类型: {list(ad_types)}")
    print(f"指标: {list(metrics)}")

    return output_file_path


if __name__ == "__main__":
    json_file = "example.json"
    create_csv_sample(json_file, 100)
