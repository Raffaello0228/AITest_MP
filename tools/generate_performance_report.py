#!/usr/bin/env python3
"""
性能测试可视化报告生成工具
从性能测试结果JSON文件生成包含图表的HTML报告
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("警告：未安装 matplotlib，将生成不包含图表的报告")


def load_results(json_path: Path) -> Dict[str, Any]:
    """加载性能测试结果JSON文件"""
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def generate_charts(results: Dict[str, Any], output_dir: Path) -> Dict[str, str]:
    """生成图表并返回图片路径"""
    if not HAS_MATPLOTLIB:
        return {}
    
    charts = {}
    batches = results.get("batches", [])
    if not batches:
        return charts
    
    # 准备数据
    concurrency_levels = [b["concurrency"] for b in batches]
    success_rates = [b["success_rate"] * 100 for b in batches]
    failure_rates = [b["failure_rate"] * 100 for b in batches]
    avg_total_times = [
        b["performance_metrics"]["total"]["avg"] if b.get("performance_metrics") else 0
        for b in batches
    ]
    avg_save_times = [
        b["performance_metrics"]["save"]["avg"] if b.get("performance_metrics") else 0
        for b in batches
    ]
    avg_poll_times = [
        b["performance_metrics"]["poll"]["avg_time"] if b.get("performance_metrics") else 0
        for b in batches
    ]
    max_active_tasks = [
        b["concurrency_stats"]["max_active_tasks"] if b.get("concurrency_stats") else 0
        for b in batches
    ]
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 1. 成功率/失败率图表
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(concurrency_levels))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, success_rates, width, label='成功率 (%)', color='#4CAF50', alpha=0.8)
    bars2 = ax.bar(x + width/2, failure_rates, width, label='失败率 (%)', color='#F44336', alpha=0.8)
    
    ax.set_xlabel('并发数', fontsize=12)
    ax.set_ylabel('百分比 (%)', fontsize=12)
    ax.set_title('并发数 vs 成功率/失败率', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(concurrency_levels)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, 105)
    
    # 添加数值标签
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%',
                       ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    chart1_path = output_dir / "chart_success_rate.png"
    plt.savefig(chart1_path, dpi=150, bbox_inches='tight')
    plt.close()
    charts["success_rate"] = chart1_path.name
    
    # 2. 平均耗时图表
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(concurrency_levels, avg_total_times, marker='o', linewidth=2, markersize=8, 
            label='总耗时', color='#2196F3')
    ax.plot(concurrency_levels, avg_save_times, marker='s', linewidth=2, markersize=8, 
            label='Save耗时', color='#FF9800')
    ax.plot(concurrency_levels, avg_poll_times, marker='^', linewidth=2, markersize=8, 
            label='轮询耗时', color='#9C27B0')
    
    ax.set_xlabel('并发数', fontsize=12)
    ax.set_ylabel('耗时 (毫秒)', fontsize=12)
    ax.set_title('并发数 vs 平均耗时', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    chart2_path = output_dir / "chart_avg_time.png"
    plt.savefig(chart2_path, dpi=150, bbox_inches='tight')
    plt.close()
    charts["avg_time"] = chart2_path.name
    
    # 3. 最高并发任务数图表
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(concurrency_levels, max_active_tasks, color='#00BCD4', alpha=0.8, width=0.6)
    
    ax.set_xlabel('并发数', fontsize=12)
    ax.set_ylabel('最高并发任务数', fontsize=12)
    ax.set_title('并发数 vs 最高并发任务数', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    # 添加数值标签
    for i, (x, y) in enumerate(zip(concurrency_levels, max_active_tasks)):
        ax.text(x, y, str(y), ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    chart3_path = output_dir / "chart_max_concurrent.png"
    plt.savefig(chart3_path, dpi=150, bbox_inches='tight')
    plt.close()
    charts["max_concurrent"] = chart3_path.name
    
    # 4. 性能分布箱线图（如果有详细任务数据）
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    save_times_all = []
    poll_times_all = []
    total_times_all = []
    concurrency_labels = []
    
    for batch in batches:
        if batch.get("task_time_details"):
            concurrency = batch["concurrency"]
            save_times = [t["save_time"] for t in batch["task_time_details"]]
            poll_times = [t["poll_time"] for t in batch["task_time_details"]]
            total_times = [t["total_time"] for t in batch["task_time_details"]]
            
            save_times_all.append(save_times)
            poll_times_all.append(poll_times)
            total_times_all.append(total_times)
            concurrency_labels.append(f"{concurrency}")
    
    if save_times_all:
        axes[0].boxplot(save_times_all, tick_labels=concurrency_labels)
        axes[0].set_title('Save耗时分布', fontsize=12, fontweight='bold')
        axes[0].set_xlabel('并发数', fontsize=10)
        axes[0].set_ylabel('耗时 (毫秒)', fontsize=10)
        axes[0].grid(True, alpha=0.3, axis='y')
        
        axes[1].boxplot(poll_times_all, tick_labels=concurrency_labels)
        axes[1].set_title('轮询耗时分布', fontsize=12, fontweight='bold')
        axes[1].set_xlabel('并发数', fontsize=10)
        axes[1].set_ylabel('耗时 (毫秒)', fontsize=10)
        axes[1].grid(True, alpha=0.3, axis='y')
        
        axes[2].boxplot(total_times_all, tick_labels=concurrency_labels)
        axes[2].set_title('总耗时分布', fontsize=12, fontweight='bold')
        axes[2].set_xlabel('并发数', fontsize=10)
        axes[2].set_ylabel('耗时 (毫秒)', fontsize=10)
        axes[2].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    chart4_path = output_dir / "chart_distribution.png"
    plt.savefig(chart4_path, dpi=150, bbox_inches='tight')
    plt.close()
    charts["distribution"] = chart4_path.name
    
    return charts


def generate_html_report(results: Dict[str, Any], charts: Dict[str, str], output_path: Path):
    """生成HTML报告"""
    batches = results.get("batches", [])
    summary = results.get("summary", {})
    config = results.get("config", {}).get("strategy", {})
    
    # 生成批次表格HTML
    batch_rows = []
    for batch in batches:
        perf = batch.get("performance_metrics", {})
        stats = batch.get("concurrency_stats", {})
        
        batch_rows.append(f"""
        <tr>
            <td>{batch['concurrency']}</td>
            <td>{batch['total_tests']}</td>
            <td>{batch['successful_tests']}</td>
            <td>{batch['failed_tests']}</td>
            <td><span class="badge {'badge-success' if batch['success_rate'] >= 0.8 else 'badge-warning' if batch['success_rate'] >= 0.5 else 'badge-danger'}">{batch['success_rate']*100:.1f}%</span></td>
            <td>{batch['failure_rate']*100:.1f}%</td>
            <td>{batch['batch_time']:,} ms</td>
            <td>{stats.get('max_active_tasks', 0)}</td>
            <td>{perf.get('save', {}).get('avg', 0):,} ms</td>
            <td>{perf.get('poll', {}).get('avg_time', 0):,} ms</td>
            <td>{perf.get('total', {}).get('avg', 0):,} ms</td>
        </tr>
        """)
    
    # 生成图表HTML
    chart_html = ""
    if charts:
        chart_html = f"""
        <div class="charts-section">
            <h2>📊 性能图表</h2>
            <div class="chart-grid">
                <div class="chart-item">
                    <h3>并发数 vs 成功率/失败率</h3>
                    <img src="{charts.get('success_rate', '')}" alt="成功率图表" class="chart-image">
                </div>
                <div class="chart-item">
                    <h3>并发数 vs 平均耗时</h3>
                    <img src="{charts.get('avg_time', '')}" alt="平均耗时图表" class="chart-image">
                </div>
                <div class="chart-item">
                    <h3>并发数 vs 最高并发任务数</h3>
                    <img src="{charts.get('max_concurrent', '')}" alt="最高并发任务数图表" class="chart-image">
                </div>
                <div class="chart-item">
                    <h3>性能分布箱线图</h3>
                    <img src="{charts.get('distribution', '')}" alt="性能分布图表" class="chart-image">
                </div>
            </div>
        </div>
        """
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>性能测试报告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2196F3;
            margin-bottom: 10px;
            border-bottom: 3px solid #2196F3;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #424242;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .summary-card h3 {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 10px;
        }}
        .summary-card .value {{
            font-size: 32px;
            font-weight: bold;
        }}
        .summary-card.success {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}
        .summary-card.warning {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        .summary-card.info {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th {{
            background: #2196F3;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge-success {{
            background: #4CAF50;
            color: white;
        }}
        .badge-warning {{
            background: #FF9800;
            color: white;
        }}
        .badge-danger {{
            background: #F44336;
            color: white;
        }}
        .charts-section {{
            margin: 30px 0;
        }}
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .chart-item {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .chart-item h3 {{
            margin-bottom: 10px;
            color: #424242;
            font-size: 16px;
        }}
        .chart-image {{
            width: 100%;
            height: auto;
            border-radius: 4px;
        }}
        .config-info {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #2196F3;
        }}
        .config-info h3 {{
            margin-bottom: 10px;
            color: #2196F3;
        }}
        .config-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }}
        .config-item {{
            padding: 8px;
            background: white;
            border-radius: 4px;
        }}
        .config-item strong {{
            color: #666;
        }}
        .timestamp {{
            color: #999;
            font-size: 14px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 性能测试报告</h1>
        <div class="timestamp">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        <div class="timestamp">测试时间: {results.get('timestamp', 'N/A')}</div>
        
        <div class="summary-grid">
            <div class="summary-card info">
                <h3>总测试数</h3>
                <div class="value">{summary.get('total_tests', 0)}</div>
            </div>
            <div class="summary-card success">
                <h3>成功数</h3>
                <div class="value">{summary.get('total_successful_tests', 0)}</div>
            </div>
            <div class="summary-card warning">
                <h3>失败数</h3>
                <div class="value">{summary.get('total_failed_tests', 0)}</div>
            </div>
            <div class="summary-card info">
                <h3>平均成功率</h3>
                <div class="value">{summary.get('average_success_rate', 0)*100:.1f}%</div>
            </div>
            <div class="summary-card info">
                <h3>最大并发数</h3>
                <div class="value">{summary.get('max_concurrency_tested', 0)}</div>
            </div>
            <div class="summary-card info">
                <h3>测试批次数</h3>
                <div class="value">{summary.get('total_batches', 0)}</div>
            </div>
        </div>
        
        <div class="config-info">
            <h3>⚙️ 测试配置</h3>
            <div class="config-grid">
                <div class="config-item"><strong>起始并发数:</strong> {config.get('start_concurrency', 'N/A')}</div>
                <div class="config-item"><strong>最大并发数:</strong> {config.get('max_concurrency', 'N/A')}</div>
                <div class="config-item"><strong>步长:</strong> {config.get('step_size', 'N/A')}</div>
                <div class="config-item"><strong>批次延迟:</strong> {config.get('batch_delay', 'N/A')} ms</div>
                <div class="config-item"><strong>成功率阈值:</strong> {config.get('success_rate_threshold', 0)*100:.1f}%</div>
                <div class="config-item"><strong>最大失败率:</strong> {config.get('max_failure_rate', 0)*100:.1f}%</div>
                <div class="config-item"><strong>最大轮询次数:</strong> {config.get('max_polling_attempts', 'N/A')}</div>
                <div class="config-item"><strong>轮询间隔:</strong> {config.get('polling_interval', 'N/A')} ms</div>
            </div>
        </div>
        
        {chart_html}
        
        <h2>📋 批次详细数据</h2>
        <table>
            <thead>
                <tr>
                    <th>并发数</th>
                    <th>总测试数</th>
                    <th>成功数</th>
                    <th>失败数</th>
                    <th>成功率</th>
                    <th>失败率</th>
                    <th>批次耗时</th>
                    <th>最高并发任务数</th>
                    <th>平均Save耗时</th>
                    <th>平均轮询耗时</th>
                    <th>平均总耗时</th>
                </tr>
            </thead>
            <tbody>
                {''.join(batch_rows)}
            </tbody>
        </table>
        
        <h2>📝 批次详细信息</h2>
        {generate_batch_details(batches)}
    </div>
</body>
</html>
"""
    
    with output_path.open("w", encoding="utf-8") as f:
        f.write(html_content)


def generate_batch_details(batches: List[Dict[str, Any]]) -> str:
    """生成批次详细信息HTML"""
    details_html = []
    
    for batch in batches:
        concurrency = batch["concurrency"]
        perf = batch.get("performance_metrics", {})
        tasks = batch.get("task_time_details", [])
        
        task_rows = []
        for task in tasks:
            status_class = "badge-success" if task["success"] else "badge-danger"
            task_rows.append(f"""
            <tr>
                <td>{task['index']}</td>
                <td>{task['job_id'][:20] + '...' if task.get('job_id') and len(task['job_id']) > 20 else task.get('job_id', 'N/A')}</td>
                <td>{task['save_time']:,} ms</td>
                <td>{task['poll_time']:,} ms</td>
                <td>{task['poll_attempts']}</td>
                <td>{task['total_time']:,} ms</td>
                <td><span class="badge {status_class}">{task['final_job_status']}</span></td>
            </tr>
            """)
        
        details_html.append(f"""
        <div style="margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 8px; border-left: 4px solid #2196F3;">
            <h3 style="color: #2196F3; margin-bottom: 15px;">并发数: {concurrency}</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 15px;">
                <div style="padding: 10px; background: white; border-radius: 4px;">
                    <strong>成功率:</strong> {batch['success_rate']*100:.1f}%
                </div>
                <div style="padding: 10px; background: white; border-radius: 4px;">
                    <strong>批次耗时:</strong> {batch['batch_time']:,} ms
                </div>
                <div style="padding: 10px; background: white; border-radius: 4px;">
                    <strong>最高并发任务数:</strong> {batch.get('concurrency_stats', {}).get('max_active_tasks', 0)}
                </div>
            </div>
            <table style="width: 100%; margin-top: 10px;">
                <thead>
                    <tr>
                        <th>任务索引</th>
                        <th>Job ID</th>
                        <th>Save耗时</th>
                        <th>轮询耗时</th>
                        <th>轮询次数</th>
                        <th>总耗时</th>
                        <th>最终状态</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(task_rows) if task_rows else '<tr><td colspan="7" style="text-align: center; color: #999;">无任务数据</td></tr>'}
                </tbody>
            </table>
        </div>
        """)
    
    return ''.join(details_html)


def main():
    parser = argparse.ArgumentParser(description="生成性能测试可视化报告")
    parser.add_argument(
        "--input",
        type=str,
        default="output/performance_test_results.json",
        help="性能测试结果JSON文件路径",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="HTML报告输出路径（默认：与输入文件同目录）",
    )
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="不生成图表（如果未安装matplotlib）",
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误：输入文件不存在: {input_path}")
        sys.exit(1)
    
    # 确定输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_report.html"
    
    # 创建输出目录（用于存放图表）
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"正在加载结果文件: {input_path}")
    results = load_results(input_path)
    
    # 生成图表
    charts = {}
    if not args.no_charts and HAS_MATPLOTLIB:
        print("正在生成图表...")
        charts = generate_charts(results, output_dir)
        print(f"已生成 {len(charts)} 个图表")
    elif not HAS_MATPLOTLIB:
        print("警告：未安装 matplotlib，跳过图表生成")
    
    # 生成HTML报告
    print(f"正在生成HTML报告: {output_path}")
    generate_html_report(results, charts, output_path)
    
    print(f"[OK] 报告生成完成: {output_path}")
    if charts:
        print(f"图表文件保存在: {output_dir}")


if __name__ == "__main__":
    main()
