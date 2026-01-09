## 项目说明（README）

### 一、项目目的

本项目是一个**媒体计划测试和验证系统**，主要用于：

1. **数据转换**：将历史投放数据（CSV）转换为媒体计划接口所需的 JSON 格式
2. **批量测试**：批量生成测试用例、执行接口请求、验证结果
3. **KPI 验证**：检查 KPI 达成情况、预算分配准确性等
4. **性能测试**：测试接口性能表现
5. **报告生成**：生成详细的测试报告和性能报告

支持 **Common** 和 **Xiaomi** 两个版本的媒体计划接口。

---

### 二、项目结构

```
mediaplan/
├── core/                          # 核心功能模块
│   ├── api_client.py              # API 客户端（UUID、Save、Query 接口）
│   ├── api_config.py              # API 配置管理
│   ├── check_kpi_achievement.py   # Common 版本 KPI 达成检查
│   ├── check_kpi_achievement_xiaomi.py  # Xiaomi 版本 KPI 达成检查
│   ├── generate_test_report.py   # 测试报告生成（Markdown/HTML）
│   ├── performance_tester.py      # 性能测试器
│   ├── data_loader.py             # 数据加载工具
│   ├── constants.py               # 常量定义
│   └── utils.py                   # 工具函数
│
├── tools/                         # 工具脚本
│   ├── batch_generate_requests_common.py   # 批量生成 Common 版本请求
│   ├── batch_generate_requests_xiaomi.py   # 批量生成 Xiaomi 版本请求
│   ├── batch_execute_requests.py  # 批量执行请求
│   ├── batch_check_and_report.py  # 批量检查结果并生成报告
│   ├── performance_test.py        # 性能测试工具
│   ├── generate_performance_report.py  # 性能报告生成
│   └── summarize_all_results.py  # 结果汇总
│
├── config/                        # 配置文件
│   ├── constant_common.json       # Common 版本常量配置
│   ├── constant_xiaomi.json       # Xiaomi 版本常量配置
│   ├── constant_br.json           # BR 版本常量配置
│   ├── performance_config.ini     # 性能测试配置
│   └── token_*.txt                # API 令牌文件
│
├── doc/                           # 文档和数据字典
│   ├── common/
│   │   └── adtype_dict.csv        # 广告类型映射表
│   └── xiaomi/
│       ├── adformat.csv           # 广告格式字典
│       ├── country.csv            # 国家字典
│       └── enum.csv               # 枚举值字典
│
├── output/                        # 输出目录
│   ├── common/                    # Common 版本输出
│   │   ├── requests/              # 生成的请求文件
│   │   └── achievement_checks/    # KPI 检查结果
│   │       ├── json/              # JSON 格式结果
│   │       └── reports/           # 报告文件（HTML/Markdown）
│   └── xiaomi/                    # Xiaomi 版本输出
│       ├── requests/              # 生成的请求文件
│       └── results/               # 接口返回结果
│
├── testcase_template.py           # Common 版本测试用例模板
├── testcase_templatex_xiaomi.py   # Xiaomi 版本测试用例模板
├── testcase_allocation_strategy.py # 分配策略测试用例
├── data.csv                       # 历史投放数据（Common）
├── data_xiaomi.csv                # 历史投放数据（Xiaomi）
├── brief_template.json            # JSON 模板
└── README.md                      # 项目说明文档
```

---

### 三、核心功能模块

#### 1. API 客户端（`core/api_client.py`）

提供完整的 API 调用功能，支持：

- ✅ 获取 UUID 接口调用
- ✅ Save 任务创建接口调用
- ✅ 任务状态轮询查询
- ✅ 完整工作流（UUID → Save → 轮询）
- ✅ 支持自定义请求体
- ✅ 支持从配置文件加载请求体
- ✅ 异步支持，可并发调用

**使用示例**：

```python
from core import create_client_from_config
from core.api_config import get_api_config

async with create_client_from_config(api_config=get_api_config("common", "PRE")) as client:
    result = await client.complete_workflow(
        uuid=None,  # 自动获取 UUID
        max_polling_attempts=100,
        polling_interval_ms=2000,
    )
```

详细文档请参考：`core/API_CLIENT_README.md`

#### 2. 数据转换（`tools/batch_generate_requests_*.py`）

将历史投放数据转换为媒体计划接口所需的 JSON 格式。

**输入文件**：
- `data.csv` / `data_xiaomi.csv`：历史投放明细数据
  - 关键字段：`country_code`、`channel_id`、`media_channel`、`ad_type`、`month_`、`spend`、KPI 字段等
- `doc/common/adtype_dict.csv`：广告类型映射表
  - 关键字段：`Media`、`Platform`、`Marketing Funnel`、`Objective`、`Ad Type` 等

**输出文件**：
- `output/{version}/requests/brief_case_*.json`：生成的请求 JSON 文件

**主要功能**：
- 数据读取与清洗
- 媒体/平台/漏斗推断
- `basicInfo` 构建（总预算、全局 KPI、区域预算）
- 按国家构建 `briefMultiConfig`（阶段、营销漏斗、媒体、广告类型等）

**使用方法**：

```bash
# Common 版本
python tools/batch_generate_requests_common.py

# Xiaomi 版本
python tools/batch_generate_requests_xiaomi.py
```

#### 3. KPI 达成检查（`core/check_kpi_achievement*.py`）

检查媒体计划结果是否满足测试用例要求。

**检查维度**：
- 全局 KPI 达成情况
- 区域预算分配
- 阶段预算分配
- 营销漏斗预算分配
- 媒体预算分配
- 广告类型 KPI 达成情况
- 广告类型预算分配

**使用方法**：

```bash
# Common 版本
python core/check_kpi_achievement.py \
    --testcase-file testcase_template.py \
    --request-file output/common/requests/brief_case_*.json \
    --result-file output/common/results/result_*.json \
    --case-name "完全匹配-5%-KPI第一"

# Xiaomi 版本
python core/check_kpi_achievement_xiaomi.py \
    --testcase-file testcase_templatex_xiaomi.py \
    --request-file output/xiaomi/requests/brief_case_*.json \
    --result-file output/xiaomi/results/mp_result_*.json \
    --case-name "基准用例-完全匹配默认配置"
```

详细文档请参考：`core/CHECK_KPI_ACHIEVEMENT_XIAOMI_README.md`

#### 4. 测试报告生成（`core/generate_test_report.py`）

生成详细的测试报告，支持 Markdown 和 HTML 格式。

**报告内容**：
- 测试配置信息
- KPI 优先级和模块优先级
- 各维度达成情况汇总
- 详细的达成/未达成项列表
- 统计图表（HTML 格式）

**使用方法**：

```bash
python core/generate_test_report.py \
    --input output/common/achievement_checks/json/*.json \
    --output output/common/achievement_checks/reports/ \
    --format html
```

#### 5. 批量处理工具

**批量执行请求**（`tools/batch_execute_requests.py`）：

```bash
python tools/batch_execute_requests.py \
    --version common \
    --environment PRE \
    --input-dir output/common/requests/
```

**批量检查并生成报告**（`tools/batch_check_and_report.py`）：

```bash
python tools/batch_check_and_report.py \
    --format html \
    --skip-check  # 跳过检查，只生成报告
    --skip-report # 跳过报告生成，只执行检查
```

#### 6. 性能测试（`tools/performance_test.py`）

测试接口性能表现，支持分批次并发测试。

**功能特性**：
- 支持不同版本（common/xiaomi）
- 支持不同环境（PRE/TEST/PROD）
- 可配置并发数和批次大小
- 自动生成性能报告

**使用方法**：

```bash
python tools/performance_test.py \
    --version common \
    --environment PRE \
    --start-concurrency 2 \
    --max-concurrency 10 \
    --step 2
```

---

### 四、环境依赖

#### 1. Python 版本

- Python 3.9+（建议使用 Python 3.10+）

#### 2. 依赖库

```bash
pip install pandas numpy aiohttp
```

**主要依赖说明**：
- `pandas`：数据处理和分析
- `numpy`：数值计算
- `aiohttp`：异步 HTTP 客户端

---

### 五、配置说明

#### 1. API 配置

API 配置在 `core/api_config.py` 中管理，支持：

- **版本**：`common`、`xiaomi`
- **环境**：`PRE`、`TEST`、`PROD`
- **接口地址**：自动从配置中获取
- **认证令牌**：从 `config/token_*.txt` 读取

#### 2. 测试用例配置

测试用例在 `testcase_template.py` 或 `testcase_templatex_xiaomi.py` 中定义，主要配置项：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `kpi_target_rate` | KPI 目标达成率 | 80% |
| `kpi_must_achieve` | KPI 是否必须达成 | False |
| `stage_range_match` | 阶段预算误差范围 | 20% |
| `marketingfunnel_range_match` | 营销漏斗预算误差范围 | 15% |
| `media_range_match` | 媒体预算误差范围 | 5% |
| `allow_zero_budget` | 是否允许 0 预算 | False |
| `kpi_priority_list` | KPI 优先级列表 | [] |
| `module_priority_list` | 模块优先级列表 | [] |

#### 3. 性能测试配置

性能测试配置在 `config/performance_config.ini` 中：

```ini
[performance]
polling_interval_ms = 2000
max_polling_attempts = 100
batch_size = 10
```

---

### 六、使用流程

#### 典型工作流程

1. **准备数据**
   - 准备历史投放数据（`data.csv` 或 `data_xiaomi.csv`）
   - 准备广告类型映射表（`doc/common/adtype_dict.csv`）

2. **生成测试用例**
   ```bash
   # Common 版本
   python tools/batch_generate_requests_common.py
   
   # Xiaomi 版本
   python tools/batch_generate_requests_xiaomi.py
   ```

3. **执行接口请求**
   ```bash
   python tools/batch_execute_requests.py \
       --version common \
       --environment PRE \
       --input-dir output/common/requests/
   ```

4. **检查结果并生成报告**
   ```bash
   python tools/batch_check_and_report.py --format html
   ```

5. **查看报告**
   - JSON 结果：`output/{version}/achievement_checks/json/`
   - HTML 报告：`output/{version}/achievement_checks/reports/*.html`
   - Markdown 报告：`output/{version}/achievement_checks/reports/*.md`

#### 性能测试流程

1. **配置性能测试参数**
   - 编辑 `config/performance_config.ini`
   - 或使用命令行参数

2. **执行性能测试**
   ```bash
   python tools/performance_test.py \
       --version common \
       --environment PRE \
       --start-concurrency 2 \
       --max-concurrency 10
   ```

3. **查看性能报告**
   - 报告自动生成在 `output/performance/` 目录

---

### 七、注意事项

1. **数据格式要求**：
   - `data.csv` 中 `ad_type` 必须能在 `adtype_dict.csv` 中找到对应行
   - `month_` 字段必须存在且为 `YYYYMM` 格式，才能按月生成阶段
   - 缺失时会退化为单一 "All" 阶段

2. **API 令牌**：
   - 确保 `config/token_*.txt` 文件存在且包含有效的 API 令牌
   - 不同环境使用不同的令牌文件

3. **版本差异**：
   - Common 版本和 Xiaomi 版本的数据结构不同
   - 使用对应的脚本和测试用例模板
   - 结果文件路径也不同

4. **并发控制**：
   - 性能测试时注意 API 服务器的并发限制
   - 建议从较小的并发数开始测试

5. **编码问题**：
   - 数据文件可能使用不同编码（UTF-8/GBK/Latin1）
   - 脚本会自动尝试多种编码读取

---

### 八、常见问题

#### Q1: 如何限制生成的区域数量？

在 `tools/batch_generate_requests_*.py` 中，可以设置 `MAX_REGION_COUNT` 全局变量：

```python
MAX_REGION_COUNT = 5  # 只保留前 5 个国家
```

#### Q2: 如何自定义测试用例配置？

编辑 `testcase_template.py` 或 `testcase_templatex_xiaomi.py`，在 `TEST_CASES` 字典中添加或修改测试用例配置。

#### Q3: 如何查看详细的 API 调用日志？

API 客户端使用 Python 标准 `logging` 模块，可以配置日志级别：

```python
import logging
logger = logging.getLogger("api_client")
logger.setLevel(logging.DEBUG)  # 显示详细日志
```

#### Q4: 性能测试结果在哪里？

性能测试结果保存在 `output/performance/` 目录，包括：
- JSON 格式的详细数据
- HTML 格式的性能报告

---

### 九、相关文档

- `core/API_CLIENT_README.md`：API 客户端使用说明
- `core/CHECK_KPI_ACHIEVEMENT_XIAOMI_README.md`：Xiaomi 版本 KPI 检查说明
- `brief_template_structure.md`：JSON 模板结构说明

---

### 十、更新日志

- **2024-XX-XX**：初始版本，支持 Common 和 Xiaomi 两个版本
- 支持批量生成请求、执行请求、检查结果、生成报告
- 支持性能测试和报告生成