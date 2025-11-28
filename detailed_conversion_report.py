import json
import pandas as pd
from collections import defaultdict, Counter

def analyze_and_convert_json(json_file_path, output_file_path):
    """
    分析JSON数据并转换为表格格式，生成详细报告
    
    Args:
        json_file_path: JSON文件路径
        output_file_path: 输出Excel文件路径
    """
    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=== 数据转换报告 ===")
    print(f"原始JSON数据条数: {len(data)}")
    
    # 分析数据结构
    dimensions = set(item['dimension'] for item in data)
    ad_types = set(item['adType'] for item in data)
    media_platforms = set(item['media'] for item in data)
    platforms = set(item['platform'] for item in data)
    metrics = set(item['metric'] for item in data)
    
    print(f"\n=== 数据维度分析 ===")
    print(f"维度类型: {sorted(dimensions)}")
    print(f"广告类型数量: {len(ad_types)}")
    print(f"媒体平台: {sorted(media_platforms)}")
    print(f"具体平台: {sorted(platforms)}")
    print(f"指标类型: {sorted(metrics)}")
    
    # 统计各维度的数据分布
    print(f"\n=== 数据分布统计 ===")
    dimension_counts = Counter(item['dimension'] for item in data)
    print("各维度数据条数:")
    for dim, count in dimension_counts.most_common():
        print(f"  {dim}: {count}条")
    
    media_counts = Counter(item['media'] for item in data)
    print("\n各媒体平台数据条数:")
    for media, count in media_counts.most_common():
        print(f"  {media}: {count}条")
    
    metric_counts = Counter(item['metric'] for item in data)
    print("\n各指标类型数据条数:")
    for metric, count in metric_counts.most_common():
        print(f"  {metric}: {count}条")
    
    # 转换数据
    print(f"\n=== 开始转换数据 ===")
    
    # 创建用于存储表格数据的字典
    table_data = defaultdict(dict)
    
    # 遍历数据，按维度、广告类型、媒体、平台分组
    for item in data:
        # 创建唯一键
        key = (item['dimension'], item['adType'], item['media'], item['platform'])
        
        # 如果这个组合还没有记录，初始化
        if key not in table_data:
            table_data[key] = {
                'dimension': item['dimension'],
                'adType': item['adType'],
                'media': item['media'],
                'platform': item['platform']
            }
        
        # 添加metric值
        table_data[key][item['metric']] = item['value']
    
    # 转换为DataFrame
    df = pd.DataFrame(list(table_data.values()))
    
    # 重新排列列的顺序
    base_columns = ['dimension', 'adType', 'media', 'platform']
    metric_columns = [col for col in df.columns if col not in base_columns]
    df = df[base_columns + sorted(metric_columns)]
    
    print(f"转换后的表格行数: {len(df)}")
    print(f"转换后的表格列数: {len(df.columns)}")
    print(f"数据压缩比: {len(data) / len(df):.2f}:1")
    
    # 保存到Excel文件
    df.to_excel(output_file_path, index=False, sheet_name='数据表')
    
    print(f"\n=== 转换完成 ===")
    print(f"输出文件: {output_file_path}")
    
    # 显示示例数据
    print(f"\n=== 示例数据 ===")
    print("前3行数据:")
    print(df.head(3).to_string(index=False))
    
    # 显示各维度的行数统计
    print(f"\n=== 转换后各维度行数 ===")
    dimension_row_counts = df['dimension'].value_counts()
    for dim, count in dimension_row_counts.items():
        print(f"  {dim}: {count}行")
    
    return df

if __name__ == "__main__":
    # 转换数据并生成报告
    df = analyze_and_convert_json('example.json', 'output/example_table_detailed.xlsx') 