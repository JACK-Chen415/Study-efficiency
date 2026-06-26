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

## 2. 训练候选集纳入与排除规则

进入正式训练候选集前，需按以下规则统一清洗：

1. 仅 `completed` 且关键字段合法的学习记录可进入候选训练集。
2. `abandoned` 记录排除，只作为流程质量或异常中断记录，不作为低效率样本。
3. 用户删除过的记录保存在 `deleted_study_sessions`，默认排除。
4. `efficiency_score` 为空或无法派生 `efficiency_label` 的记录排除。
5. `duration_minutes < 5` 的 completed 记录默认标记为 `too_short` 并排除；如需保留，只能用于敏感性分析并在 `EXPERIMENT_LOG.md` 中说明。
6. `motion_features` 缺失时保留样本，设置 `motion_available=0`，并将 `move_count`、`shake_count`、`still_ratio`、`avg_acceleration`、`max_acceleration` 填 `0`。该填补只用于建模矩阵稳定，不代表真实完全无运动。
7. 测试、mock、demo 数据不得计入真实有效样本数，也不得写成真实实验结果。

## 3. 导出字段

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
| `motion_available` | 是否采集到运动特征，`1` 是，`0` 否；这是缺失机制标记，不是学习行为本身 |
| `efficiency_score` | 用户自评效率分数，1-5 |
| `efficiency_label` | 三分类标签 |

CSV 还包含 `session_id` 与 `user_id`，用于检查问题记录，不作为默认训练特征。

## 4. 缺失运动特征处理

手机运动数据是辅助输入。若某条学习记录没有对应的 `motion_features`，导出脚本会保留该样本，并将 `move_count`、`shake_count`、`still_ratio`、`avg_acceleration`、`max_acceleration` 填为 `0`，同时设置 `motion_available=0`。

这样做的目的只是保证训练前数据表结构稳定；后续正式训练时必须在实验日志中继续说明该缺失值处理方式，并评估它对模型结果的影响。建议至少比较两组特征：自报告 only，以及自报告 + 运动特征 + `motion_available`。

## 5. 生成 demo/mock 数据

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

## 6. 使用 demo 数据验证流程

如果本地暂时没有真实采集数据，可以用 demo/mock 数据验证脚本链路：

```bash
python ml/seed_demo_data.py
python ml/export_training_data.py --database-url sqlite:///data/demo/study_efficiency_demo.db
python ml/check_dataset.py
python ml/train_model.py --data-source demo
```

上述流程只证明数据准备链路可运行，不代表模型可靠，也不代表真实学习效率规律。

### 2026-06-18 数据拉取与演示集

已从远端服务器 Jahon 只读复制线上 SQLite 数据库到本地隔离目录：

```text
data/real/study_efficiency_jahon_20260618.db
```

对应导出和质检产物：

```text
data/processed/real/training_dataset_real_jahon_20260618.csv
data/processed/real/data_quality_report_real_jahon_20260618.md
```

当前真实 completed 样本为 17 条，低/中/高标签分布为 `low=4; medium=11; high=2`，未达到 30 条最低正式训练建议，也未达到 50 条课程展示建议。后端 `POST /api/model/train` 使用该真实库时应返回 `422` 样本不足提示。

为答辩演示训练与预测链路，另生成 120 条 mock 数据到单独数据库：

```text
data/mock/study_efficiency_mock_20260618.db
data/processed/mock/training_dataset_mock_20260618.csv
data/processed/mock/data_quality_report_mock_20260618.md
```

mock 数据仅用于接口、训练、预测和看板流程演示，不得写成真实学习效率规律。

## 7. 离线训练脚本

Milestone 4B 新增离线训练脚本，Milestone 4C 已补充后端模型 API：

```bash
python ml/train_model.py --data-source demo
```

也可使用模块方式运行：

```bash
python -m ml.train_model --data-source demo
```

默认输入与输出：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--dataset` | `data/processed/training_dataset.csv` | 由 Milestone 4A 导出的训练 CSV |
| `--output-dir` | `models` | 模型 artifact 目录，默认写入 `models/latest.joblib`；该目录与 joblib 文件不应提交到 git |
| `--metrics-output` | `data/processed/model_metrics.json` | 训练/评估指标 JSON |
| `--feature-importance-output` | `data/processed/feature_importance.csv` | One-Hot 后特征重要性 |
| `--data-source` | `demo` | 必须显式区分 `real` / `demo` / `mock` / `test` |
| `--random-state` | `42` | 训练与划分随机种子 |
| `--test-size` | `0.25` | train/test 评估拆分比例 |

训练脚本以 `efficiency_label` 为目标列，排除 `session_id`、`user_id`、`efficiency_score`，其余字段作为候选特征。`time_period`、`location`、`task_type` 经 `OneHotEncoder` 编码；学习时长、自评字段、运动字段和 `motion_available` 作为数值特征。主模型为 `RandomForestClassifier`，并同时输出多数类 `DummyClassifier` baseline。

`model_metrics.json` 至少包含 Accuracy、macro/weighted Precision、Recall、F1、混淆矩阵、标签分布、样本数、数据来源和 `valid_for_research_conclusion`。当 `data_source != real` 时，JSON 必须包含“仅流程验证，不代表真实学习效率规律”的 warning；当真实样本数少于 30 时，`valid_for_research_conclusion=false`。

demo/mock/test 数据可以用于确认 CSV 读取、One-Hot、训练、指标、特征重要性和模型保存链路跑通，但不能写成真实学习效率规律或研究结论。

## 8. 数据质量检查

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
4. 学习时长异常记录，基础异常规则为 `<1` 或 `>720` 分钟；正式训练前还需将 `<5` 分钟 completed 记录标记为 `too_short`。
5. 五级自报告字段与 `efficiency_score` 是否越界。
6. 枚举字段是否合法。
7. `efficiency_score` 到 `efficiency_label` 的转换是否一致。
8. 是否满足最低训练样本数 `30`。

样本数不足 `30` 时，不建议训练正式模型；即使后续能跑通训练，也只能展示流程和限制说明。最终课程展示建议至少 `50` 条真实有效 completed 记录，理想为 `80-120` 条，并在训练前检查 `low`、`medium`、`high` 标签分布。
