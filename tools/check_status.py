#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用任务状态检查脚本
用于检查指定输出目录中的任务状态

用法:
    python3 check_status.py --output-dir test_results --port 5000
    python3 check_status.py --output-dir test_results --port 5000 --save-results
"""

import argparse
import requests
import json
from pathlib import Path
from datetime import datetime
from typing import Dict

def check_jobs_status(output_dir: Path, status_url: str, save_results: bool = False) -> Dict:
    """检查任务状态"""
    job_mapping_file = output_dir / "job_ids_mapping.json"
    
    if not job_mapping_file.exists():
        print(f"未找到job_id映射文件: {job_mapping_file}")
        return {}
    
    with open(job_mapping_file, 'r', encoding='utf-8') as f:
        jobs = json.load(f)
    
    print("="*80)
    print(f"检查 {len(jobs)} 个任务状态")
    print("="*80)
    
    completed = []
    processing = []
    failed = []
    results = {}
    
    for test_name, job_id in sorted(jobs.items()):
        try:
            response = requests.get(f"{status_url}/{job_id}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'UNKNOWN')
                progress = data.get('progress_ratio', 'N/A')
                
                if status == 'COMPLETED':
                    completed.append((test_name, job_id))
                    print(f"✓ {test_name}: {status} ({progress})")
                    
                    if save_results:
                        # 检查是否已保存
                        existing_files = list(output_dir.glob(f"{test_name}_result_*.json"))
                        if not existing_files:
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            result_file = output_dir / f"{test_name}_result_{timestamp}.json"
                            with open(result_file, 'w', encoding='utf-8') as f:
                                json.dump(data, f, indent=2, ensure_ascii=False)
                            results[test_name] = result_file
                            print(f"  → 结果已保存: {result_file.name}")
                elif status == 'PROCESSING':
                    processing.append((test_name, job_id, progress))
                    print(f"⏳ {test_name}: {status} ({progress})")
                elif status in ['FAILED', 'ERROR']:
                    failed.append((test_name, job_id, data.get('message', 'Unknown')))
                    print(f"✗ {test_name}: {status} - {data.get('message', 'Unknown error')}")
                else:
                    print(f"? {test_name}: {status} ({progress})")
            else:
                print(f"✗ {test_name}: 查询失败 ({response.status_code})")
        except Exception as e:
            print(f"✗ {test_name}: 错误 - {e}")
    
    print("="*80)
    print(f"完成: {len(completed)}/{len(jobs)} ({len(completed)/len(jobs)*100:.1f}%)")
    print(f"处理中: {len(processing)}/{len(jobs)}")
    print(f"失败: {len(failed)}/{len(jobs)}")
    
    if save_results and results:
        print(f"\n新保存了 {len(results)} 个结果文件")
    
    return {
        'completed': len(completed),
        'processing': len(processing),
        'failed': len(failed),
        'total': len(jobs)
    }

def main():
    parser = argparse.ArgumentParser(description='检查任务状态')
    parser.add_argument('--output-dir', type=str, required=True,
                        help='结果输出目录 (必需)')
    parser.add_argument('--host', type=str, default='10.1.12.39',
                        help='API主机地址 (默认: 10.1.12.39)')
    parser.add_argument('--port', type=int, default=5000,
                        help='API端口 (默认: 5000)')
    parser.add_argument('--save-results', action='store_true',
                        help='自动保存已完成的结果')
    
    args = parser.parse_args()
    
    BASE_DIR = Path("/root/zyydebug/mp_zyy/mp_generate")
    OUTPUT_DIR = BASE_DIR / "test_tmp" / args.output_dir
    STATUS_URL = f"http://{args.host}:{args.port}/job_status"
    
    if not OUTPUT_DIR.exists():
        print(f"输出目录不存在: {OUTPUT_DIR}")
        return 1
    
    stats = check_jobs_status(OUTPUT_DIR, STATUS_URL, args.save_results)
    
    return 0

if __name__ == '__main__':
    exit(main())

