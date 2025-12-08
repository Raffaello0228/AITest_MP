#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用测试运行脚本
用于提交测试用例并轮询结果

用法:
    python3 run_tests.py --test-dir test_cases_tester --output-dir test_results --port 5000
    python3 run_tests.py --test-dir tests --output-dir test_results_v2 --port 5000
"""

import argparse
import requests
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

def check_service(port: int, max_retries: int = 5) -> bool:
    """检查服务是否可用"""
    status_url = f"http://127.0.0.1:{port}/job_status"
    for i in range(max_retries):
        try:
            response = requests.get(f"{status_url}/test", timeout=5)
            return True
        except:
            if i < max_retries - 1:
                print(f"等待服务启动... ({i+1}/{max_retries})")
                time.sleep(3)
    return False

def submit_tests(test_dir: Path, api_url: str, max_retries: int = 3) -> dict:
    """提交所有测试用例"""
    test_cases = sorted(test_dir.glob("*.json"))
    if not test_cases:
        print(f"在 {test_dir} 中未找到测试用例")
        return {}
    
    print(f"找到 {len(test_cases)} 个测试用例\n")
    print("="*80)
    print("提交测试任务")
    print("="*80)
    
    jobs = {}
    for test_path in test_cases:
        test_name = test_path.stem
        
        try:
            with open(test_path, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            
            submit_retry = 0
            submitted = False
            
            while submit_retry < max_retries and not submitted:
                try:
                    response = requests.post(api_url, json=payload, timeout=30)
                    if response.status_code == 200:
                        result = response.json()
                        job_id = result.get('job_id')
                        jobs[test_name] = job_id
                        print(f"✓ {test_name}: {job_id}")
                        submitted = True
                    else:
                        if submit_retry < max_retries - 1:
                            submit_retry += 1
                            time.sleep(2)
                        else:
                            print(f"✗ {test_name}: 提交失败 ({response.status_code})")
                except requests.exceptions.RequestException as e:
                    if submit_retry < max_retries - 1:
                        submit_retry += 1
                        print(f"  ⏳ {test_name}: 连接失败，重试 {submit_retry}/{max_retries}...")
                        time.sleep(2)
                    else:
                        print(f"✗ {test_name}: 错误 - {e}")
        except Exception as e:
            print(f"✗ {test_name}: 错误 - {e}")
    
    print(f"\n已提交 {len(jobs)} 个任务\n")
    return jobs

def poll_results(jobs: dict, status_url: str, output_dir: Path, max_wait_time: int = 3600) -> dict:
    """轮询任务结果"""
    if not jobs:
        return {}
    
    print("="*80)
    print("轮询任务状态")
    print("="*80)
    
    results = {}
    start_time = time.time()
    last_print_time = {}
    
    while jobs and time.time() - start_time < max_wait_time:
        elapsed = int(time.time() - start_time)
        
        for test_name, job_id in list(jobs.items()):
            try:
                response = requests.get(f"{status_url}/{job_id}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status', 'UNKNOWN')
                    progress = data.get('progress_ratio', 'N/A')
                    
                    should_print = (elapsed - last_print_time.get(test_name, -30) >= 30) or \
                                  (status in ['COMPLETED', 'FAILED', 'ERROR'])
                    
                    if should_print:
                        print(f"[{elapsed}秒] {test_name}: {status} ({progress})")
                        last_print_time[test_name] = elapsed
                    
                    if status == 'COMPLETED':
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        result_file = output_dir / f"{test_name}_result_{timestamp}.json"
                        with open(result_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        results[test_name] = result_file
                        print(f"  ✓ 结果已保存: {result_file.name}")
                        del jobs[test_name]
                    elif status in ['FAILED', 'ERROR']:
                        print(f"  ✗ 任务失败: {data.get('message', 'Unknown error')}")
                        del jobs[test_name]
            except requests.exceptions.RequestException as e:
                print(f"  ✗ 连接错误 ({test_name}): {e}")
            except Exception as e:
                print(f"  ✗ 处理错误 ({test_name}): {e}")
        
        if jobs:
            time.sleep(5)
        else:
            break
    
    return results

def main():
    parser = argparse.ArgumentParser(description='运行测试用例并轮询结果')
    parser.add_argument('--test-dir', type=str, default='test_cases_tester',
                        help='测试用例目录 (默认: test_cases_tester)')
    parser.add_argument('--output-dir', type=str, required=True,
                        help='结果输出目录 (必需)')
    parser.add_argument('--port', type=int, default=5000,
                        help='API端口 (默认: 5000)')
    parser.add_argument('--max-wait', type=int, default=3600,
                        help='最大等待时间(秒) (默认: 3600)')
    
    args = parser.parse_args()
    
    BASE_DIR = Path("/root/zyydebug/mp_zyy/mp_generate")
    TEST_DIR = BASE_DIR / "test_tmp" / args.test_dir
    OUTPUT_DIR = BASE_DIR / "test_tmp" / args.output_dir
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    API_URL = f"http://127.0.0.1:{args.port}/generate_media_plan"
    STATUS_URL = f"http://127.0.0.1:{args.port}/job_status"
    
    # 检查服务
    print("="*80)
    print("检查服务连接")
    print("="*80)
    if not check_service(args.port):
        print(f"✗ 服务连接失败，请检查服务是否在{args.port}端口运行")
        return 1
    
    print(f"✓ 服务连接正常 (端口: {args.port})\n")
    
    # 提交测试
    jobs = submit_tests(TEST_DIR, API_URL)
    
    if not jobs:
        print("没有成功提交任何任务")
        return 1
    
    # 保存job_id映射
    job_mapping_file = OUTPUT_DIR / "job_ids_mapping.json"
    with open(job_mapping_file, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"Job ID映射已保存到: {job_mapping_file}\n")
    
    # 轮询结果
    results = poll_results(jobs, STATUS_URL, OUTPUT_DIR, args.max_wait)
    
    # 最终摘要
    print("\n" + "="*80)
    print("测试完成摘要")
    print("="*80)
    print(f"成功完成: {len(results)} 个")
    print(f"仍在运行: {len(jobs)} 个")
    
    if results:
        print("\n成功的结果文件:")
        for test_name, result_file in sorted(results.items()):
            print(f"  ✓ {test_name}: {result_file.name}")
    
    if jobs:
        print("\n仍在运行的任务:")
        for test_name, job_id in sorted(jobs.items()):
            print(f"  ⏳ {test_name}: {job_id}")
    
    # 保存摘要
    summary_file = OUTPUT_DIR / f"test_summary_{args.output_dir}.json"
    summary = {
        'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'test_dir': str(TEST_DIR),
        'output_dir': str(OUTPUT_DIR),
        'port': args.port,
        'total_submitted': len(jobs) + len(results),
        'completed': len(results),
        'running': len(jobs),
        'results': {name: str(path) for name, path in results.items()},
        'job_ids': jobs
    }
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n摘要已保存到: {summary_file}")
    
    return 0

if __name__ == '__main__':
    exit(main())

