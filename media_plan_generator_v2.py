import os
import pandas as pd
import random
from datetime import datetime, timedelta
import numpy as np
import json
import re
import argparse
from collections import defaultdict
import uuid
import time

# 设置随机种子以确保每次运行都不同
current_time = int(time.time())  # 使用秒级时间戳
random.seed(current_time)
np.random.seed(current_time % (2**32))  # 确保在numpy允许的范围内


class MediaPlanGenerator:
    def __init__(self, adtype_dict_path):
        """
        初始化媒体计划生成器

        Args:
            adtype_dict_path: adtype_dict.xlsx的文件路径
        """
        self.brands = ["Brand A", "Brand B", "Brand C", "Brand D", "Brand E"]
        self.products = [
            "Product A",
            "Product B",
            "Product C",
            "Product D",
            "Product E",
        ]
        self.countries = [
            "US",
            "CA",
            "FR",
            "DE",
            "UK",
            "NL",
            "BE",
            "AT",
            "CH",
            "IE",
            "IT",
            "ES",
            "PT",
            "GR",
            "SI",
            "HR",
            "RS",
            "MK",
            "BA",
            "SE",
            "DK",
            "FI",
            "NO",
            "IS",
            "PL",
            "CZ",
            "HU",
            "RO",
            "SK",
            "BG",
            "RU",
            "UA",
            "BY",
            "KZ",
            "UZ",
            "AZ",
            "AM",
            "GE",
            "MD",
            "TJ",
            "KG",
            "TM",
            "SA",
            "AE",
            "TR",
            "IQ",
            "IR",
            "IL",
            "JO",
            "KW",
            "LB",
            "OM",
            "QA",
            "SY",
            "YE",
            "EG",
            "DZ",
            "MA",
            "TN",
            "LY",
            "IN",
            "PK",
            "BD",
            "NP",
            "LK",
            "AF",
            "MV",
            "BT",
            "TH",
            "MY",
            "PH",
            "VN",
            "SG",
            "ID",
            "MM",
            "KH",
            "LA",
            "BN",
            "TL",
            "MX",
            "BR",
            "AR",
            "CL",
            "CO",
            "PE",
            "VE",
            "EC",
            "UY",
            "PY",
            "BO",
            "GT",
            "CR",
            "PA",
            "SV",
            "NG",
            "ZA",
            "KE",
            "GH",
            "ET",
            "UG",
            "TZ",
            "SN",
            "CI",
            "CM",
            "ZM",
            "ZW",
            "SD",
        ]
        # KPI指标
        self.kpi_metrics = [
            "Impression",
            "Clicks",
            "Link Clicks",
            "Video Views",
            "video Watch 2s",
            "Engagement",
            "Followers",
            "Like",
            "Purchase",
            "Leads",
            # "Install"
        ]
        self.cpx_metrics = [
            "CPM",
            "CPC",
            "CPC(Link Clicks)",
            "CPV",
            "CPV2S",
            "CPE",
            "CPF",
            "CPEL",
            "CPP",
            "CPL",
        ]
        # CPX指标对应的KPI指标映射
        self.cpx_to_kpi_mapping = {
            "CPM": "Impression",
            "CPC": "Clicks",
            "CPC(Link Clicks)": "Link Clicks",
            "CPV": "Video Views",
            "CPV2S": "video Watch 2s",
            "CPE": "Engagement",
            "CPF": "Followers",
            "CPEL": "Like",
            "CPP": "Purchase",
            "CPL": "Leads",
        }
        # CPX指标的合理范围（美元）
        self.cpx_ranges = {
            "CPM": (1.0, 50.0),  # 每千次展示成本
            "CPC": (0.5, 10.0),  # 每次点击成本
            "CPC(Link Clicks)": (0.8, 15.0),  # 每次链接点击成本
            "CPV": (0.02, 0.5),  # 每次视频观看成本
            "CPV2S": (0.01, 0.3),  # 每次2秒观看成本
            "CPE": (0.1, 5.0),  # 每次互动成本
            "CPF": (0.5, 20.0),  # 每个粉丝成本
            "CPEL": (0.05, 2.0),  # 每个点赞成本
            "CPP": (5.0, 200.0),  # 每次购买成本
            "CPL": (10.0, 500.0),  # 每个线索成本
        }
        # 读取并处理adtype_dict
        self.adtype_df = pd.read_excel(adtype_dict_path)
        self._process_adtype_data()

    def _process_adtype_data(self):
        """处理adtype_dict数据，建立必要的映射关系"""
        # 获取唯一值列表
        self.media_channels = self.adtype_df["Media Channel"].unique().tolist()
        self.marketing_funnels = self.adtype_df["Marketing Funnel"].unique().tolist()

        # 建立media_channel到media的映射
        self.channel_to_media = dict(
            zip(self.adtype_df["Media Channel"], self.adtype_df["Media"])
        )

        # 建立media_channel到adtype的映射
        self.channel_adtypes = defaultdict(list)
        for _, row in self.adtype_df.iterrows():
            self.channel_adtypes[row["Media Channel"]].append(row["Ad Type"])

        # 建立adtype到marketing_funnel的映射
        self.adtype_funnels = defaultdict(set)
        for _, row in self.adtype_df.iterrows():
            key = (row["Media Channel"], row["Ad Type"])
            self.adtype_funnels[key].add(row["Marketing Funnel"])

        # 建立adtype到Media Buy Type的映射
        self.adtype_buy_types = {}
        for _, row in self.adtype_df.iterrows():
            key = (row["Media Channel"], row["Ad Type"])
            self.adtype_buy_types[key] = row["Media Buy Type"]

    def generate_basic_info(self, total_budget, country):
        """生成基本信息"""
        brand = random.choice(self.brands)
        product = random.choice(self.products)

        # 生成KPI信息
        kpi_info = []
        for metric in random.sample(self.kpi_metrics, random.randint(5, 8)):
            if metric in ["Impression", "Engagement", "Followers", "Reach"]:
                val = str(random.randint(100000, 10000000))
            elif metric in [
                "Clicks",
                "Link Clicks",
                "Video Views",
                "Like",
                "Conversions",
            ]:
                val = str(random.randint(100, 10000))
            elif metric in ["Purchase", "Leads"]:
                val = str(random.randint(1000, 100000))
            else:
                val = str(random.randint(100, 5000))

            kpi_info.append({"key": metric, "val": val})

        return {
            "uuid": str(uuid.uuid4())[:32],
            "kpiInfo": kpi_info,
            "mediaPlanName": f"{brand} {product} Campaign",
            "corporationId": str(random.randint(100000, 999999)),
            "brandName": brand,
            "productName": product,
            "currency": "USD",
            "totalBudget": str(total_budget),
            "country": country,
            "corporationName": str(random.randint(100000, 999999)),
            "fileName": f"media_plan_{datetime.now().strftime('%Y%m%d')}.xlsx",
            "documentStatus": random.randint(1, 3),
            "dimension": random.sample(
                ["corporation", "competitor", "category", "ai"],
                random.randint(2, 4),
            ),
            "isHistoryMp": random.randint(0, 1),
            "accountId": str(random.randint(1000000000000000000, 9999999999999999999)),
            "campaignId": str(random.randint(1000000000000000000, 9999999999999999999)),
            "competitorCorporationId": str(random.randint(100000, 999999)),
            "categoryLevel1Id": str(random.randint(1, 10)),
            "categoryLevel2Id": str(random.randint(1000, 9999)),
            "categoryLevel3Id": str(random.randint(1000000, 9999999)),
        }

    def generate_stage_budget(self, total_budgets):
        """生成推广阶段时间线和预算分配"""

        # 随机生成2-5个自定义stage
        num_stages = random.randint(2, 5)
        custom_stages = [f"stage{i+1}" for i in range(num_stages)]

        # 分配预算百分比
        stage_percentages = np.random.dirichlet(np.ones(num_stages)) * 100
        stage_budget = [int(p) * total_budgets / 100 for p in stage_percentages]

        # 调整以确保总和为total_budgets
        adjustment = total_budgets - sum(stage_budget)
        stage_budget[-1] += adjustment

        # 返回每个stage的预算信息
        stage_budget_info = []
        for i, stage in enumerate(custom_stages):
            stage_budget_info.append(
                {
                    "stage": stage,
                    "budget": stage_budget[i],
                    "percentage": round(stage_budget[i] / total_budgets * 100, 2),
                }
            )

        return stage_budget_info

    def generate_adtype_budgets(self, stage_budget, country, cpx_cache=None):
        """为每个stage生成adtype预算分配"""
        # 首先决定Meta的渠道选择策略
        stage_budget_amount = stage_budget["budget"]
        stage = stage_budget["stage"]
        meta_strategy = random.choice(["combined", "separate"])
        adtype_budgets = []

        # 过滤可用的渠道
        available_channels = []
        for channel in self.media_channels:
            # 处理Meta相关渠道
            if channel in ["FB&IG", "FB", "IG"]:
                if meta_strategy == "combined" and channel == "FB&IG":
                    available_channels.append(channel)
                elif meta_strategy == "separate" and channel in ["FB", "IG"]:
                    available_channels.append(channel)
            else:
                available_channels.append(channel)

        # 随机选择2-4个渠道
        num_channels = random.randint(2, min(4, len(available_channels)))
        selected_channels = random.sample(available_channels, num_channels)

        # 为选中的渠道分配stage预算
        channel_budgets = (
            np.random.dirichlet(np.ones(num_channels)) * stage_budget_amount
        )
        channel_budgets = [int(p) for p in channel_budgets]
        # 调整以确保总和等于stage_budget_amount
        adjustment = stage_budget_amount - sum(channel_budgets)
        channel_budgets[-1] += adjustment

        for i, channel in enumerate(selected_channels):
            channel_budget = channel_budgets[i]

            # 首先区分reserve和non-reserve类型
            available_adtypes = self.channel_adtypes[channel]
            reserve_types = []
            non_reserve_types = []
            for adtype in available_adtypes:
                key = (channel, adtype)
                if self.adtype_buy_types.get(key) == "reserved":
                    reserve_types.append(adtype)
                else:
                    non_reserve_types.append(adtype)

            num_non_reserve = random.randint(1, min(3, len(non_reserve_types)))
            selected_non_reserve = random.sample(non_reserve_types, num_non_reserve)
            # 可能额外选择0-1个reserve类型
            num_reserve = random.randint(0, min(1, len(reserve_types)))
            selected_reserve = (
                random.sample(reserve_types, num_reserve) if reserve_types else []
            )

            # 为non-reserve类型分配channel预算
            non_reserve_budgets = (
                np.random.dirichlet(np.ones(len(selected_non_reserve))) * channel_budget
            )
            non_reserve_budgets = [int(p) for p in non_reserve_budgets]
            # 调整以确保总和等于channel_budget
            adjustment = channel_budget - sum(non_reserve_budgets)
            non_reserve_budgets[-1] += adjustment

            # 记录non-reserve adtype预算
            for j, adtype in enumerate(selected_non_reserve):
                adtype_budget = non_reserve_budgets[j]
                # 生成CPX和KPI指标
                metrics = self.generate_cpx_and_kpi_metrics(
                    adtype_budget, adtype, cpx_cache
                )

                adtype_budgets.append(
                    {
                        "Stage": stage,
                        "Media": self.channel_to_media[channel],
                        "Platform": channel,
                        "Marketing Funnel": list(
                            self.adtype_funnels[(channel, adtype)]
                        )[0],
                        "Ad Type": adtype,
                        "Budget": adtype_budget,
                        "Region": country,
                        **metrics,
                    }
                )
            # 记录reserve adtype（预算为0）
            for adtype in selected_reserve:
                # 对于reserve类型，CPX和KPI指标都为0
                metrics = self.generate_cpx_and_kpi_metrics(0, adtype, cpx_cache)

                adtype_budgets.append(
                    {
                        "Stage": stage,
                        "Media": self.channel_to_media[channel],
                        "Platform": channel,
                        "Marketing Funnel": list(
                            self.adtype_funnels[(channel, adtype)]
                        )[0],
                        "Ad Type": adtype,
                        "Budget": 0,
                        "Region": country,
                        **metrics,
                    }
                )

        return adtype_budgets

    def generate_cpx_and_kpi_metrics(self, budget, adtype, cpx_cache=None):
        """为给定的预算和adtype生成CPX指标和对应的KPI指标"""
        metrics = {}

        # 为每个adtype生成所有CPX指标
        selected_cpx_metrics = self.cpx_metrics

        # 为每个CPX指标生成随机值
        for cpx_metric in selected_cpx_metrics:
            # 如果提供了缓存且该adtype的CPX指标已存在，则使用缓存的值
            if cpx_cache and adtype in cpx_cache and cpx_metric in cpx_cache[adtype]:
                cpx_value = cpx_cache[adtype][cpx_metric]
            else:
                min_val, max_val = self.cpx_ranges[cpx_metric]
                cpx_value = round(random.uniform(min_val, max_val), 2)
                # 将新生成的CPX值添加到缓存中
                if cpx_cache is not None:
                    if adtype not in cpx_cache:
                        cpx_cache[adtype] = {}
                    cpx_cache[adtype][cpx_metric] = cpx_value

            metrics[cpx_metric] = cpx_value

            # 计算对应的KPI指标
            kpi_metric = self.cpx_to_kpi_mapping[cpx_metric]
            if cpx_metric == "CPM":
                # CPM = 成本 / (展示次数 / 1000)
                # 所以 展示次数 = (成本 / CPM) * 1000
                impressions = int((budget / cpx_value) * 1000)
                metrics[kpi_metric] = impressions
            else:
                # 其他指标：KPI = 成本 / CPX
                kpi_count = int(budget / cpx_value)
                metrics[kpi_metric] = kpi_count

        return metrics

    def generate_adtype_detailed_data(self, total_budget, country):
        """生成adtype粒度的详细数据"""
        adtype_detailed_data = []
        cpx_cache = {}

        # 生成stage预算分配
        stage_budget_items = self.generate_stage_budget(total_budget)

        for stage_budget in stage_budget_items:
            # 生成该stage的adtype预算
            stage_adtype_budgets = self.generate_adtype_budgets(
                stage_budget, country, cpx_cache
            )
            adtype_detailed_data += stage_adtype_budgets

        # 验证预算分配是否正确
        total_adtype_budget = sum(item["Budget"] for item in adtype_detailed_data)
        if total_adtype_budget != total_budget:
            print(
                f"警告：adtype预算总和({total_adtype_budget})与总预算({total_budget})不匹配"
            )
            print(f"差异：{total_budget - total_adtype_budget}")
        else:
            print(
                f"预算分配正确：adtype预算总和({total_adtype_budget})等于总预算({total_budget})"
            )

        return adtype_detailed_data

    def aggregate_to_stage(self, adtype_detailed_data):
        """聚合到stage维度"""
        stage_budgets = defaultdict(float)

        # 按stage汇总预算
        for item in adtype_detailed_data:
            stage = item["Stage"]
            budget = item["Budget"]
            stage_budgets[stage] += budget

        # 转换为输出格式
        stage_data = []
        total_budget = sum(stage_budgets.values())

        for stage_name, budget in stage_budgets.items():
            percentage = (budget / total_budget) * 100 if total_budget > 0 else 0

            stage_data.append(
                {
                    "name": stage_name,
                    "budgetPercentage": f"{round(percentage, 2)}%",
                    "budgetAmount": str(int(budget)),
                }
            )

        return stage_data

    def aggregate_to_marketing_funnel(self, adtype_detailed_data):
        """聚合到marketing funnel维度"""
        funnel_budgets = defaultdict(float)

        # 按funnel汇总预算
        for item in adtype_detailed_data:
            funnels = item["Marketing Funnel"]
            budget = item["Budget"]

            # 平均分配预算给每个funnel
            if funnels:
                funnel_budgets[funnels] += budget

        # 转换为输出格式
        funnel_data = []
        total_budget = sum(funnel_budgets.values())
        for funnel, budget in funnel_budgets.items():
            percentage = (budget / total_budget) * 100 if total_budget > 0 else 0
            funnel_data.append(
                {
                    "name": funnel,
                    "nameKey": funnel.replace(" ", "_").upper(),
                    "budgetPercentage": f"{round(percentage, 2)}%",
                    "budgetAmount": str(int(budget)),
                }
            )

        return funnel_data

    def aggregate_to_media_platform(self, adtype_detailed_data):
        """聚合到media-platform维度"""
        media_platform_budgets = defaultdict(
            lambda: {"media": "", "budget": 0, "children": defaultdict(float)}
        )

        # 按media和platform汇总预算
        for item in adtype_detailed_data:
            media = item["Media"]
            platform = item["Platform"]
            budget = item["Budget"]

            media_platform_budgets[media]["media"] = media
            media_platform_budgets[media]["budget"] += budget
            media_platform_budgets[media]["children"][platform] += budget

        # 转换为输出格式
        media_data = []
        total_budget = sum(data["budget"] for data in media_platform_budgets.values())

        for media, data in media_platform_budgets.items():
            media_percentage = (
                (data["budget"] / total_budget) * 100 if total_budget > 0 else 0
            )

            media_item = {
                "name": media,
                "nameKey": media.upper(),
                "budgetPercentage": f"{round(media_percentage, 2)}%",
                "budgetAmount": str(int(data["budget"])),
                "children": [],
            }

            # 添加platform子项
            for platform, platform_budget in data["children"].items():
                platform_percentage = (
                    (platform_budget / data["budget"]) * 100
                    if data["budget"] > 0
                    else 0
                )
                media_item["children"].append(
                    {
                        "name": platform,
                        "nameKey": platform.upper(),
                        "budgetPercentage": f"{round(platform_percentage, 2)}%",
                        "budgetAmount": str(int(platform_budget)),
                    }
                )

            media_data.append(media_item)

        return media_data

    def save_to_excel(self, media_plan, output_dir="output"):
        """将媒体计划数据保存为Excel格式"""
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 创建Excel文件
        excel_filename = f"media_plan_{timestamp}.xlsx"
        excel_path = os.path.join(output_dir, excel_filename)

        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            # 2. 保存adtype粒度详细数据
            adtype_data = media_plan
            if adtype_data:
                adtype_df = pd.DataFrame(adtype_data)
                # 重新排列列的顺序
                columns_order = [
                    "Stage",
                    "Media",
                    "Platform",
                    "Ad Type",
                    "Budget",
                    "Region",
                    "Marketing Funnel",
                    "CPM",
                    "CPC",
                    "CPC(Link Clicks)",
                    "CPV",
                    "CPV2S",
                    "CPE",
                    "CPF",
                    "CPEL",
                    "CPP",
                    "CPL",
                    "Impression",
                    "Clicks",
                    "Link Clicks",
                    "Video Views",
                    "video Watch 2s",
                    "Engagement",
                    "Followers",
                    "Like",
                    "Purchase",
                    "Leads",
                ]
                # 只保留存在的列
                existing_columns = [
                    col for col in columns_order if col in adtype_df.columns
                ]
                adtype_df = adtype_df[existing_columns]
                adtype_df.to_excel(writer, sheet_name="Media Plan", index=False)

        print(f"Excel文件已保存: {excel_path}")
        return excel_path

    def generate_platform_goals(self, adtype_detailed_data):
        """生成平台目标（adtype汇总）"""
        media_adtypes = defaultdict(set)

        for item in adtype_detailed_data:
            media = item["Media"]
            adtype = item["Ad Type"]
            media_adtypes[media].add(adtype)

        platform_goals = []
        for media, adtypes in media_adtypes.items():
            platform_goals.append(
                {"name": media, "nameKey": media.upper(), "adType": list(adtypes)}
            )

        return platform_goals

    def generate_media_plan(self):
        """生成完整的媒体计划"""
        # 生成基本信息
        total_budget = round(np.random.normal(500000, 166667))
        total_budget = max(1000, min(1000000, total_budget))
        country = random.choice(self.countries)

        # 第一步：生成adtype粒度的详细数据
        adtype_detailed_data = self.generate_adtype_detailed_data(total_budget, country)
        # 保存为Excel文件
        self.save_to_excel(adtype_detailed_data)

        # 第二步：聚合到不同维度
        stage_aggregated = self.aggregate_to_stage(adtype_detailed_data)
        funnel_aggregated = self.aggregate_to_marketing_funnel(adtype_detailed_data)
        media_platform_aggregated = self.aggregate_to_media_platform(
            adtype_detailed_data
        )

        # 构建最终的JSON对象
        media_plan = {
            "basicInfo": self.generate_basic_info(total_budget, country),
            "stage": stage_aggregated,
            "marketingFunnel": funnel_aggregated,
            "media": media_platform_aggregated,
            "adType": self.generate_platform_goals(
                adtype_detailed_data
            ),  # 保留adtype粒度的详细数据
        }

        return media_plan


def convert_to_excel(data):
    """将JSON格式数据转换为与图片格式一致的Excel格式"""
    excel_data = []

    for item in data:
        # 生成KPI指标字符串
        kpi_metrics = []
        for kpi_info in item["basicInfo"]["kpiInfo"]:
            kpi_metrics.append(f"{kpi_info['key']}: {kpi_info['val']}")
        kpi_string = "\n".join(kpi_metrics)

        # 生成推广周期字符串
        stage_periods = []
        for stage in item["stage"]:
            stage_periods.append(f"{stage['name']}: {stage['budgetPercentage']}")
        stage_string = "\n".join(stage_periods)

        # 生成推广目标字符串
        funnel_goals = []
        for funnel in item["marketingFunnel"]:
            funnel_goals.append(f"{funnel['name']}: {funnel['budgetPercentage']}")
        goal_string = "\n".join(funnel_goals)

        # 生成推广媒体字符串
        media_distribution = []
        for media in item["media"]:
            media_distribution.append(f"{media['name']}: {media['budgetPercentage']}")
        media_string = "\n".join(media_distribution)

        # 生成广告产品字符串
        ad_products = []
        for platform in item["adType"]:
            ad_products.append(f"{platform['name']}: {', '.join(platform['adType'])}")
        ad_product_string = "\n".join(ad_products)

        record = {
            "推广品牌": item["basicInfo"]["brandName"],
            "推广产品": item["basicInfo"]["productName"],
            "推广预算": f"USD {item['basicInfo']['totalBudget']}",
            "KPI指标": kpi_string,
            "国家": item["basicInfo"]["country"],
            "推广周期": stage_string,
            "推广目标": goal_string,
            "推广媒体": media_string,
            "广告产品": ad_product_string,
        }
        excel_data.append(record)

    return pd.DataFrame(excel_data)


def main():
    """主函数"""
    try:
        # 初始化生成器
        generator = MediaPlanGenerator("adtype_dict.xlsx")

        # 生成数据
        mp_data = generator.generate_media_plan()

        # 转换为Excel格式
        df = convert_to_excel([mp_data])

        # 保存为Excel文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"media_plan_summary_{timestamp}.xlsx"
        excel_path = os.path.join("output", excel_filename)

        # 确保输出目录存在
        if not os.path.exists("output"):
            os.makedirs("output")

        # 保存Excel文件
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="媒体计划汇总", index=False)

            # 设置列宽
            worksheet = writer.sheets["媒体计划汇总"]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        print(f"Excel文件已保存: {excel_path}")

        # # 同时保存详细的adtype数据
        # generator.save_to_excel(mp_data["adType"])

    except Exception as e:
        print(f"生成数据时发生错误: {str(e)}")


if __name__ == "__main__":
    main()
