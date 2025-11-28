#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from media_plan_generator_v2 import MediaPlanGenerator


def debug_data_structure():
    """调试数据结构"""
    try:
        # 初始化生成器
        generator = MediaPlanGenerator("adtype_dict.xlsx")

        # 生成一个媒体计划
        media_plan = generator.generate_media_plan()

        print("=== 数据结构调试 ===")

        # 检查adtypeDetailedData的结构
        adtype_data = media_plan["adtypeDetailedData"]
        print(f"AdType详细数据记录数: {len(adtype_data)}")

        if adtype_data:
            print(f"\n第一个AdType记录的字段:")
            first_record = adtype_data[0]
            for key, value in first_record.items():
                print(f"  {key}: {value} (类型: {type(value)})")

            print(f"\n所有记录的Stage字段值:")
            stage_values = set()
            for record in adtype_data:
                if "Stage" in record:
                    stage_values.add(record["Stage"])
                elif "stage" in record:
                    stage_values.add(record["stage"])

            print(f"Stage值: {stage_values}")

            # 检查字段名的大小写
            print(f"\n字段名检查:")
            sample_record = adtype_data[0]
            stage_fields = [
                key for key in sample_record.keys() if "stage" in key.lower()
            ]
            print(f"包含'stage'的字段: {stage_fields}")

        # 检查convert_to_excel的输出
        print(f"\n=== convert_to_excel输出调试 ===")

        # 创建一个简单的测试数据
        test_data = [media_plan]
        df = generator.convert_to_excel(test_data)

        print(f"DataFrame形状: {df.shape}")
        print(f"DataFrame列名: {list(df.columns)}")

        if len(df) > 0:
            print(f"\n第一行数据:")
            first_row = df.iloc[0]
            for col in df.columns:
                value = first_row[col]
                if isinstance(value, str) and len(value) > 200:
                    value = value[:200] + "..."
                print(f"  {col}: {value}")

        return True

    except Exception as e:
        print(f"调试失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = debug_data_structure()
    if success:
        print("\n🎉 数据结构调试完成!")
    else:
        print("\n❌ 数据结构调试失败!")
