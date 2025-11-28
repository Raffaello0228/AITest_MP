import json


def debug_json_structure(json_file_path):
    """
    调试JSON文件结构
    """

    print("正在读取JSON文件...")

    # 读取JSON文件
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"读取完成，数据类型: {type(data)}")

    if isinstance(data, dict):
        print(f"字典键: {list(data.keys())}")
        for key, value in data.items():
            print(f"键 '{key}' 的值类型: {type(value)}")
            if isinstance(value, list):
                print(f"键 '{key}' 的值长度: {len(value)}")
                if len(value) > 0:
                    print(f"键 '{key}' 的第一个元素: {value[0]}")
            elif isinstance(value, dict):
                print(f"键 '{key}' 的值: {value}")
    elif isinstance(data, list):
        print(f"列表长度: {len(data)}")
        if len(data) > 0:
            print(f"第一个元素: {data[0]}")
            print(f"第一个元素的键: {list(data[0].keys())}")

    return data


if __name__ == "__main__":
    json_file = "example.json"
    debug_json_structure(json_file)
