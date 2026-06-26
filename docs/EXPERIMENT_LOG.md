# 模型实验日志

本文档用于记录后续学习效率模型训练与评估结果。不得将示例、demo、mock 或测试数据结果填写为真实实验结论。

Milestone 4A 已补充训练前数据准备脚本和质量检查脚本。Milestone 4B 新增离线训练脚本 `ml/train_model.py`，可在安装 scikit-learn/joblib 后用 `python ml/train_model.py --data-source demo` 验证 CSV 读取、One-Hot、RandomForest、Dummy baseline、指标、特征重要性和 `models/latest.joblib` 保存链路。demo/mock/test 数据仅用于开发链路验证，不能写入下方实验索引作为真实实验结论；少于 30 条真实有效 completed 样本时也不得形成正式研究结论。

## 记录规则

1. 每次训练分配唯一的 `model_version`，并注明时间、操作者和代码/数据版本。
2. 清楚区分真实采集数据、模拟开发数据和任何公开辅助数据。
3. 记录缺失运动特征处理、特征编码、数据划分和随机种子，确保可复现。
4. 样本数不足时如实写明限制，不夸大准确率或适用范围。
5. 主任务使用三分类指标；辅助回归实验另行记录指标。

## 训练前数据就绪检查模板

正式训练前先填写本节。若未达到训练条件，只记录检查结果和限制说明，不填写模型指标。

| 检查项 | 记录内容 |
| --- | --- |
| 检查日期与操作者 | `<YYYY-MM-DD / name>` |
| 数据来源说明 | `<真实 completed / 测试 / mock / demo；不可混称>` |
| 真实 completed 样本数 | `<n>` |
| `abandoned` 数量 | `<n>` |
| `in_progress` 数量 | `<n>` |
| 标签分布 | `low=<n>; medium=<n>; high=<n>` |
| motion 缺失率 | `<missing_motion_rows / completed_rows; percent>` |
| `too_short` 排除数量 | `<duration_minutes < 5 的 completed 记录数>` |
| 测试/mock/demo 数据数量 | `test=<n>; mock=<n>; demo=<n>` |
| 其他排除数量与原因 | `<duplicate_candidate / careless / invalid_field / deleted 等>` |
| baseline 方案 | `<例如多数类 DummyClassifier；用于判断模型是否超过简单基线>` |
| 特征组对比方案 | `<自报告 only vs 自报告 + 运动特征 + motion_available>` |
| 当前是否达到正式训练条件 | `<未达到 / 仅可流程演示 / 可做课程项目限制性训练；说明理由>` |

训练条件建议：少于 30 条真实有效 completed 记录时不建议训练正式模型；最终课程展示建议至少 50 条真实有效 completed；理想为 80-120 条，并检查三类标签分布是否过度不平衡。

### 2026-06-18 Jahon 真实数据就绪检查

| 检查项 | 记录内容 |
| --- | --- |
| 检查日期与操作者 | `2026-06-18 / Codex` |
| 数据来源说明 | Jahon 远端部署收集到的真实 completed 数据；本地只读副本为 `data/real/study_efficiency_jahon_20260618.db` |
| 真实 completed 样本数 | `17` |
| `abandoned` 数量 | `11` |
| `in_progress` 数量 | `1` |
| 标签分布 | `low=4; medium=11; high=2` |
| motion 缺失率 | `11 / 17; 64.71%` |
| `too_short` 排除数量 | `0` |
| 测试/mock/demo 数据数量 | `test=0; mock=120; demo=0` |
| 其他排除数量与原因 | `abandoned=11; in_progress=1` |
| baseline 方案 | 多数类 `DummyClassifier` baseline |
| 特征组对比方案 | 当前先使用自报告 + 运动特征 + `motion_available`，后续真实样本增加后再做特征组消融 |
| 当前是否达到正式训练条件 | 未达到；真实 completed 样本少于 30，且标签分布偏向 medium |

本次真实数据可用于说明已完成真实采集和数据质检，但不形成正式模型有效性结论。接口验证中，`POST /api/model/train` 指向该真实库时返回 `422`：`Need at least 30 completed labeled sessions; found 17.`

## 实验索引

| 序号 | 日期 | `model_version` | 任务/模型 | 数据类型 | 样本数 | 关键结果 | 结论 |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| 1 | 2026-06-18 | `rf_20260618_021746` | RandomForest 三分类 / API 演示 | mock | 120 | Accuracy=1.000; F1-macro=1.000; baseline Accuracy=0.333 | 仅证明训练、指标、特征重要性、预测 API 链路可运行；不代表真实规律 |
| - | 2026-06-18 | `rf_20260618_021640` | RandomForest 三分类 / 真实数据检查 | real | 17 | Accuracy=0.600; F1-macro=0.250; baseline 相同 | 样本不足且未超过 baseline，不作为正式实验结论 |

---

## 实验记录模板

### 实验 `rf_20260618_021746`

| 项目 | 记录内容 |
| --- | --- |
| 日期与操作者 | `2026-06-18 / Codex` |
| 目标 | 验证模型训练、指标读取、特征重要性和预测 API 端到端链路 |
| 任务类型 | 三分类 |
| 模型与主要参数 | `RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=20260618)` |
| 代码版本 | Milestone 4C：模型 API 接入 |
| 数据来源 | `mock`；120 条模拟数据，不能作为真实实验结论 |
| 样本数与标签分布 | `total=120; low=40 / medium=40 / high=40` |
| 纳入特征 | `duration_minutes`、`time_period`、`location`、`task_type`、六个自报告字段、五个运动字段、`motion_available` |
| 缺失值处理 | 缺失运动特征导出为 0，并用 `motion_available=0` 标识 |
| 类别编码 | `OneHotEncoder(handle_unknown="ignore")` |
| 数据划分与随机种子 | stratified train/test split；`test_size=0.25`; `random_state=20260618` |
| 模型文件位置 | `models/latest.joblib` |

#### 分类指标

| Accuracy | Precision | Recall | F1-score | 评价口径 |
| ---: | ---: | ---: | ---: | --- |
| `1.000` | `1.000` | `1.000` | `1.000` | macro；仅 mock 流程验证 |

Dummy baseline：Accuracy=`0.333333`，F1-macro=`0.166667`。

#### 混淆矩阵

| Actual \ Predicted | `low` | `medium` | `high` |
| --- | ---: | ---: | ---: |
| `low` | `10` | `0` | `0` |
| `medium` | `0` | `10` | `0` |
| `high` | `0` | `0` | `10` |

#### 特征重要性

| 排名 | 特征 | 重要性 | 解释备注 |
| ---: | --- | ---: | --- |
| 1 | `noise_level` | `0.151744` | mock 构造规律中的主要区分特征之一 |
| 2 | `phone_distraction` | `0.147538` | mock 构造规律中的主要区分特征之一 |
| 3 | `mood_stress` | `0.114447` | mock 构造规律中的主要区分特征之一 |
| 4 | `light_level` | `0.113204` | mock 构造规律中的主要区分特征之一 |
| 5 | `move_count` | `0.089503` | mock 构造规律中的运动辅助特征 |

#### 结论与限制

- 实验结论：模型 API 链路已跑通，能够训练、保存模型、读取指标和特征重要性，并对新 completed 会话写入预测。
- 样本/偏差限制：本实验全部使用 mock 数据，`valid_for_research_conclusion=false`，不能写成真实学习效率规律。
- 下一次实验调整：继续采集真实 completed 记录，达到至少 50 条后再做正式课程展示模型，并补充自报告 only 与自报告 + 运动特征的对比。

### 实验 `<model_version>`

| 项目 | 记录内容 |
| --- | --- |
| 日期与操作者 | `<YYYY-MM-DD / name>` |
| 目标 | `<本次训练要验证的问题>` |
| 任务类型 | `<三分类 / 回归对比>` |
| 模型与主要参数 | `<RandomForestClassifier / parameters>` |
| 代码版本 | `<commit 或里程碑说明>` |
| 数据来源 | `<真实采集 / 模拟开发 / 公开辅助；不可混称>` |
| 样本数与标签分布 | `<total; low / medium / high>` |
| 纳入特征 | `<features>` |
| 缺失值处理 | `<尤其说明 motion_features>` |
| 类别编码 | `<例如 OneHotEncoder>` |
| 数据划分与随机种子 | `<train/test 或交叉验证；random_state>` |
| 模型文件位置 | `<artifact path>` |

#### 分类指标

| Accuracy | Precision | Recall | F1-score | 评价口径 |
| ---: | ---: | ---: | ---: | --- |
| `<value>` | `<value>` | `<value>` | `<value>` | `<macro/weighted 等>` |

#### 混淆矩阵

| Actual \ Predicted | `low` | `medium` | `high` |
| --- | ---: | ---: | ---: |
| `low` | `<n>` | `<n>` | `<n>` |
| `medium` | `<n>` | `<n>` | `<n>` |
| `high` | `<n>` | `<n>` | `<n>` |

#### 特征重要性

| 排名 | 特征 | 重要性 | 解释备注 |
| ---: | --- | ---: | --- |
| 1 | `<feature>` | `<value>` | `<note>` |

#### 结论与限制

- 实验结论：`<填写观察结果，不超过数据能支持的范围>`
- 样本/偏差限制：`<填写>`
- 下一次实验调整：`<填写>`
