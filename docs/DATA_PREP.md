# Milestone 4A 数据准备说明

本文档只覆盖模型训练前的数据准备：从数据库导出训练 CSV、生成开发用 demo/mock 数据、运行数据质量检查。此阶段不训练 RandomForest，不实现模型预测接口，不输出模型指标。

## 1. 导出训练数据

默认导出命令：

```bash
python ml/export_training_data.py
```

脚本读取 `DATABASE_URL`；若未设置，则默认读取 `backend/study_efficiency.db`。导出文件为：

```text
data/processed/training_dataset.csv
```

也可以显式指定数据库和输出路径：

```bash
python ml/export_training_data.py \
  --database-url sqlite:////absolute/path/to/study_efficiency.db \
  --output data/processed/training_dataset.csv
```

导出数据来源为 `study_sessions` 中 `end_time` 不为空且 `efficiency_score` 不为空的记录，并 left join `motion_features`。`efficiency_label` 在导出时由 `efficiency_score` 重新转换：`1-2 -> low`、`3 -> medium`、`4-5 -> high`。

用户从历史记录中删除过的数据会进入 `deleted_study_sessions` 备份表，不会被默认导出脚本纳入训练 CSV。

## 2. 导出字段

训练 CSV 至少包含以下模型准备字段：

| 字段 | 说明 |
| --- | --- |
| `duration_minutes` | 学习时长 |
| `time_period` | 开始时间所属时段 |
| `location` | 学习地点 |
| `task_type` | 任务类型 |
| `goal_clarity` | 目标清晰度，1-5 |
| `light_level` | 光照感受，1-5 |
| `noise_level` | 噪声程度，1-5 |
| `fatigue_level` | 疲劳程度，1-5 |
| `mood_stress` | 心情/压力，1-5 |
| `phone_distraction` | 手机干扰，1-5 |
| `move_count` | 移动次数 |
| `shake_count` | 晃动次数 |
| `still_ratio` | 静止比例 |
| `avg_acceleration` | 平均加速度 |
| `max_acceleration` | 最大加速度 |
| `motion_available` | 是否采集到运动特征，`1` 是，`0` 否 |
| `efficiency_score` | 用户自评效率分数，1-5 |
| `efficiency_label` | 三分类标签 |

CSV 还包含 `session_id` 与 `user_id`，用于检查问题记录，不作为默认训练特征。

## 3. 缺失运动特征处理

手机运动数据是辅助输入。若某条学习记录没有对应的 `motion_features`，导出脚本会保留该样本，并将 `move_count`、`shake_count`、`still_ratio`、`avg_acceleration`、`max_acceleration` 填为 `0`，同时设置 `motion_available=0`。

这样做的目的只是保证训练前数据表结构稳定；后续正式训练时必须在实验日志中继续说明该缺失值处理方式，并评估它对模型结果的影响。

## 4. 生成 demo/mock 数据

默认命令会写入单独的 SQLite demo 数据库，不写入真实 MySQL：

```bash
python ml/seed_demo_data.py
```

默认输出数据库：

```text
data/demo/study_efficiency_demo.db
```

该脚本生成用于开发测试的模拟学习记录，覆盖 `low`、`medium`、`high` 三类标签，并故意保留部分缺失运动特征，用于验证导出和质量检查流程。demo/mock 数据不能作为真实学习行为结论，也不能写入正式实验结果。

如确需写入当前后端配置的开发数据库，可显式传入数据库 URL：

```bash
python ml/seed_demo_data.py --database-url "$DATABASE_URL"
```

## 5. 使用 demo 数据验证流程

如果本地暂时没有真实采集数据，可以用 demo/mock 数据验证脚本链路：

```bash
python ml/seed_demo_data.py
python ml/export_training_data.py --database-url sqlite:///data/demo/study_efficiency_demo.db
python ml/check_dataset.py
```

上述流程只证明数据准备链路可运行，不代表模型可靠，也不代表真实学习效率规律。

## 6. 数据质量检查

默认检查命令：

```bash
python ml/check_dataset.py
```

默认读取：

```text
data/processed/training_dataset.csv
```

默认输出 Markdown 报告：

```text
data/processed/data_quality_report.md
```

检查内容包括：

1. 样本总数。
2. `low`、`medium`、`high` 标签分布。
3. 缺失运动特征数量。
4. 学习时长异常记录，当前规则为 `<1` 或 `>720` 分钟。
5. 五级自报告字段与 `efficiency_score` 是否越界。
6. 枚举字段是否合法。
7. `efficiency_score` 到 `efficiency_label` 的转换是否一致。
8. 是否满足最低训练样本数 `30`。

样本数不足 `30` 时，不应声称模型可靠；即使后续能跑通训练，也只能展示流程和限制说明。
