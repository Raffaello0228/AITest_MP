# generate_media_infeasible_case.py 使用说明

## 1. 脚本目的

`generate_media_infeasible_case.py` 用于构造一个“媒体能力上限无法满足 KPI”的边界测试用例（不一定报错，但会在验收中失败）。

核心思路：

1. 固定媒体占比（例如 `Meta=50%`，`Google=50%`）；
2. 假设 `GG` 取最佳 CPM（例如 `0.6`），计算理论最大曝光；
3. 假设 `Meta` 取某种 CPM（历史/最佳/固定），计算理论最大曝光；
4. 将全局 `Impression` 目标设置为“理论上限 + uplift（例如 +10%）”，构造不可满足场景。

---

## 2. 计算逻辑

设：

- 总预算：`B`
- Meta 占比：`r_meta`
- GG 最低 CPM：`cpm_gg_min`
- Meta 假设 CPM：`cpm_meta`
- KPI 上调比例：`u`

则：

- `B_meta = B * r_meta`
- `B_gg = B * (1 - r_meta)`
- `Imp_meta_max = B_meta / cpm_meta * 1000`
- `Imp_gg_max = B_gg / cpm_gg_min * 1000`
- `Imp_total_max = Imp_meta_max + Imp_gg_max`
- `Impression_target = ceil(Imp_total_max * (1 + u))`

脚本会把 `Impression` 目标写入 brief，并默认设为 `completion=1`（必须达成）。

---

## 3. 输入与输出

### 输入

- `--csv-path`：用于估算预算和 CPM 的数据源（默认 `xiaomi_v2.csv`）
- `--input-brief`：输入基准 brief（默认 `brief_case_xiaomi_v2_baseline.json`）

### 输出

- `--output-brief`：输出不可满足 case（默认 `brief_case_xiaomi_v2_media_infeasible.json`）

---

## 4. 参数说明

| 参数 | 含义 | 默认值 |
|---|---|---|
| `--meta-ratio` | Meta 预算占比（%） | `50.0` |
| `--gg-min-cpm` | GG 最优 CPM（能力上界） | `0.6` |
| `--kpi-uplift` | KPI 相对上界上浮比例 | `0.10` |
| `--meta-cpm-mode` | Meta CPM 估算模式：`history` / `best` / `fixed` | `history` |
| `--meta-fixed-cpm` | `fixed` 模式下 Meta CPM | `1.2` |
| `--ytb-floor-ratio` | Google 下给 YTB 保底占比（%） | `0.0` |
| `--keep-other-kpis` | 是否保留非 Impression 的 KPI 目标 | 开启 |
| `--is-history-mp` | 是否开启历史 MP | `1` |
| `--history-mp-id` | 历史 MP ID（用于沿用上传的 CPM 语境） | `0f25ac3c-d0e6-4340-995b-c795e766` |

---

## 5. 典型用法

## 场景 A：标准不可满足（Meta 50% + GG CPM 0.6 + KPI +10%）

```bash
python tools/generate_media_infeasible_case.py \
  --csv-path xiaomi_v2.csv \
  --input-brief output/xiaomi/requests_stage_media_stability_from_brief/brief_case_xiaomi_v2_baseline.json \
  --output-brief output/xiaomi/requests_xiaomi_v2_boundary/brief_case_xiaomi_v2_media_infeasible.json \
  --meta-ratio 50 \
  --gg-min-cpm 0.6 \
  --kpi-uplift 0.10
```

## 场景 B：更激进（Meta 60% + KPI +20%）

```bash
python tools/generate_media_infeasible_case.py \
  --meta-ratio 60 \
  --kpi-uplift 0.20
```

## 场景 C：固定 Meta CPM（避免历史波动）

```bash
python tools/generate_media_infeasible_case.py \
  --meta-cpm-mode fixed \
  --meta-fixed-cpm 1.5
```

---

## 6. 结果如何验证

1. 执行新生成的 brief；
2. 跑 `check_kpi_achievement_xiaomi.py`；
3. 关注以下指标：
   - 全局 `Impression` 是否低于目标；
   - `media_budget` 是否出现明显偏离（如 Meta 目标无法满足）；
   - stage / funnel 是否仍可满足（用于确认冲突主要来自 media + KPI）。

---

## 7. 注意事项

- 该脚本构造的是“理论不可满足”输入，不是直接判断器；
- 最终以求解结果 + achievement check 报告为准；
- 若 CSV 缺少曝光/CPM列，Meta CPM 会回退到可用策略（`best` 或需指定 `fixed`）；
- 若要更稳地产生对照实验，建议一次生成三档：
  - `kpi_uplift=0.00`（边界可行）
  - `kpi_uplift=0.05`（临界）
  - `kpi_uplift=0.10`（不可行）

