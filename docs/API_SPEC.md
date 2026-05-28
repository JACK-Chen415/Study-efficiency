# P0 API 草案

## 1. 目标与范围

本文档定义 MVP 主链路所需的 P0 REST API 草案：简单登录、学习会话记录、可选手机运动特征、模型训练/预测和分析看板。完整认证、多角色管理和跨用户对比不属于 P0。

当前已实现的后端接口包括：`/api/users/simple-login`、`/api/sessions/start`、`/api/sessions/end`、`POST /api/sessions/{id}/abandon`、`/api/sessions/list`、`/api/sessions/{id}`、`PUT /api/sessions/{id}`、`DELETE /api/sessions/{id}`、`/api/motion/upload`、`/api/motion/{session_id}`。模型训练/预测与分析看板接口保留为后续 milestone 草案，本阶段不注册这些路由。

接口实现前可细化校验与分页方式；若修改路径、字段或枚举，必须同时更新 `DATA_DICTIONARY.md`。

## 2. 通用约定

| 项目 | 约定 |
| --- | --- |
| Base URL | `/api` |
| 数据格式 | 请求与响应均为 `application/json` |
| 时间格式 | ISO 8601 含时区，例如 `2026-05-25T14:00:00+08:00` |
| 标识符 | 正整数 ID，由服务端生成 |
| P0 身份识别 | simple-login 使用用户自选昵称进入系统，返回 `user_id`；请求显式携带该 ID，不实现 JWT |
| 可空运动特征 | 设备不支持、未授权或采集失败时允许为空 |
| 标签枚举 | `low`、`medium`、`high` |
| 错误格式 | Milestone 2 使用 FastAPI 默认错误响应 `{"detail": "可读说明"}`；统一 `code/message/details` 可在后续 API 规范化时引入 |

常用状态码：

| 状态码 | 含义 |
| --- | --- |
| `200` | 查询或更新成功 |
| `201` | 记录创建成功 |
| `400` | 请求字段或业务状态不合法 |
| `404` | 用户、会话或结果不存在 |
| `409` | 资源状态冲突，例如尚无可用于预测的模型 |
| `422` | 字段校验失败或训练样本不足 |
| `500` | 服务端未预期错误 |

## 3. 业务枚举与计算规则

| 字段 | P0 取值/规则 |
| --- | --- |
| `efficiency_score` | 整数 `1` 到 `5` |
| `efficiency_label` | `1-2 -> low`，`3 -> medium`，`4-5 -> high`，由服务端计算 |
| `time_period` | `05:00-11:59 -> morning`，`12:00-17:59 -> afternoon`，`18:00-22:59 -> evening`，`23:00-04:59 -> late_night`，由开始时间计算 |
| `location` | `dormitory`、`library`、`classroom`、`study_room`、`other` |
| `task_type` | `coursework`、`exam_review`、`coding`、`paper_reading`、`postgraduate_prep`、`other` |
| 五级自评字段 | `goal_clarity`、`light_level`、`noise_level`、`fatigue_level`、`mood_stress`、`phone_distraction` 均为整数 `1` 到 `5` |

## 4. 用户 API

### `POST /api/users/simple-login`

按用户自选昵称创建或进入 P0 用户，不包含密码认证。

请求：

```json
{
  "nickname": "student_a",
  "grade": "2024",
  "major": "物联网工程"
}
```

响应 `200` 或 `201`：

```json
{
  "id": 1,
  "nickname": "student_a",
  "grade": "2024",
  "major": "物联网工程",
  "created_at": "2026-05-25T14:00:00+08:00"
}
```

校验说明：`nickname` 必填并去除首尾空格；P0 以昵称作为唯一进入用户的键。再次使用同一昵称登录会进入同一个用户，即使本次年级或专业留空、或与首次填写不同，也不会创建新用户；年级和专业只在首次创建该昵称用户时保存。

## 5. 学习记录 API

### `POST /api/sessions/start`

为用户开始一次尚未完成的学习会话。

请求：

```json
{
  "user_id": 1,
  "start_time": "2026-05-25T14:00:00+08:00"
}
```

响应 `201`：

```json
{
  "id": 101,
  "user_id": 1,
  "start_time": "2026-05-25T14:00:00+08:00",
  "status": "in_progress"
}
```

业务说明：`start_time` 可由客户端提交并由服务端校验；缺省时使用服务端当前时间。同一用户重复开启未结束且未放弃的会话时返回 `409`。已放弃的会话不会阻塞重新开始。响应中的 `status` 由 `end_time` 与 `abandoned_at` 推导，不写入独立 `status` 字段。

### `POST /api/sessions/end`

结束会话并提交本次自报告。`duration_minutes`、`time_period` 与 `efficiency_label` 由服务端产生。`end_time` 可选，缺省时使用服务端当前时间；必须满足 `end_time >= start_time`；不足 1 分钟按 1 分钟记录；已结束会话再次提交返回 `409`；已放弃会话不能再结束，返回 `409`。

请求：

```json
{
  "session_id": 101,
  "end_time": "2026-05-25T15:20:00+08:00",
  "location": "library",
  "task_type": "coding",
  "goal_clarity": 4,
  "light_level": 4,
  "noise_level": 2,
  "fatigue_level": 3,
  "mood_stress": 2,
  "phone_distraction": 2,
  "efficiency_score": 4
}
```

响应 `200`：

```json
{
  "id": 101,
  "user_id": 1,
  "start_time": "2026-05-25T14:00:00+08:00",
  "end_time": "2026-05-25T15:20:00+08:00",
  "duration_minutes": 80,
  "time_period": "afternoon",
  "location": "library",
  "task_type": "coding",
  "efficiency_score": 4,
  "efficiency_label": "high",
  "status": "completed"
}
```

### `GET /api/sessions/list`

查询指定用户的学习记录，默认包含进行中和已完成会话，不返回已放弃会话；`status` 由 `end_time` 与 `abandoned_at` 推导。

查询参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `user_id` | 是 | 用户 ID |
| `limit` | 否 | 默认 `20`，最大 `100` |
| `offset` | 否 | 默认 `0` |

响应 `200`：

```json
{
  "items": [
    {
      "id": 101,
      "start_time": "2026-05-25T14:00:00+08:00",
      "duration_minutes": 80,
      "task_type": "coding",
      "efficiency_score": 4,
      "efficiency_label": "high"
    }
  ],
  "total": 1
}
```

### `GET /api/sessions/{id}`

返回一次会话的自报告、运动特征、放弃状态和已有的最近预测结果。`status` 可能为 `in_progress`、`completed` 或 `abandoned`。若运动数据未采集，则 `motion_features` 为 `null`；若尚无预测，则 `latest_prediction` 为 `null`。

### `POST /api/sessions/{id}/abandon`

主动放弃一次未结束学习会话，用于用户开始后决定不把本次学习作为有效记录的情况。放弃后的会话会保留在数据库中，但不会阻塞同一用户重新开始学习，也不会进入默认历史列表或训练数据导出。

请求体可省略；如传入原因，`reason` 会保存到 `abandon_reason`：

```json
{
  "reason": "user_requested"
}
```

响应 `200`：返回放弃后的 `SessionResponse`，其中 `status` 为 `abandoned`，`abandoned_at` 为服务端放弃时间。若会话不存在返回 `404`；若会话已完成返回 `409`；若会话已放弃，重复调用幂等返回成功。

### `PUT /api/sessions/{id}`

修改一条已完成学习记录的自报告字段和效率评分，直接覆盖原 `study_sessions` 行，不新增学习记录。`duration_minutes`、`start_time`、`end_time` 与 `time_period` 不在本接口修改范围内；`efficiency_label` 会根据新的 `efficiency_score` 重新计算。若该记录已有预测结果，更新时会清理旧预测，避免展示与新字段不一致的预测。

请求：

```json
{
  "location": "study_room",
  "task_type": "exam_review",
  "goal_clarity": 5,
  "light_level": 4,
  "noise_level": 2,
  "fatigue_level": 2,
  "mood_stress": 2,
  "phone_distraction": 1,
  "efficiency_score": 4
}
```

响应 `200`：返回更新后的 `SessionResponse`。若会话不存在返回 `404`；若会话仍在进行中返回 `409`。

### `DELETE /api/sessions/{id}`

从当前学习记录中删除一条会话，并先将会话字段和可选运动特征快照写入 `deleted_study_sessions` 备份表。删除后的记录不再出现在历史记录和训练数据导出中；备份表只用于追溯用户删除过的记录，不作为默认训练数据来源。

响应 `200`：

```json
{
  "deleted_session_id": 101,
  "archived_id": 1,
  "deleted_at": "2026-05-27T01:50:00+08:00",
  "message": "session archived and deleted"
}
```

若会话不存在返回 `404`。

## 6. 手机运动数据 API

### `POST /api/motion/upload`

为一次学习会话写入或更新一组聚合运动特征。原始加速度事件不在 P0 存储范围内。`session_id` 不存在时返回 `404`；每个 `session_id` 最多一条记录，重复上传执行 upsert。

请求：

```json
{
  "session_id": 101,
  "move_count": 12,
  "shake_count": 1,
  "still_ratio": 0.86,
  "avg_acceleration": 0.14,
  "max_acceleration": 1.92
}
```

响应 `201` 或 `200`：

```json
{
  "id": 501,
  "session_id": 101,
  "move_count": 12,
  "shake_count": 1,
  "still_ratio": 0.86,
  "avg_acceleration": 0.14,
  "max_acceleration": 1.92,
  "created_at": "2026-05-25T15:20:00+08:00"
}
```

校验说明：`move_count`、`shake_count` 不小于 `0`；`still_ratio` 位于 `0` 到 `1`；该接口失败不得使 `sessions/end` 失败。

### `GET /api/motion/{session_id}`

返回会话聚合运动特征；未采集时返回 `404`，前端应以“未采集/不可用”状态展示而非报错中断。

## 7. 模型 API 草案（后续 milestone）

Milestone 4A 仅新增离线数据准备脚本，不注册本节任何模型路由。训练数据由 `ml/export_training_data.py` 从已完成、未放弃且带 `efficiency_score` 的学习记录导出，并 left join `motion_features`；缺失运动特征导出为 `0`，同时使用 `motion_available=0` 标识。正式训练、预测、指标和特征重要性接口仍属于后续 milestone。

### `POST /api/model/train`

使用已完成且带标签的会话训练 RandomForest 三分类模型。

请求：

```json
{
  "model_type": "random_forest_classifier",
  "test_size": 0.2,
  "random_state": 42
}
```

响应 `201`：

```json
{
  "model_version": "rf_20260525_001",
  "sample_count": 58,
  "status": "trained",
  "metrics": {
    "accuracy": 0.75,
    "precision_macro": 0.74,
    "recall_macro": 0.72,
    "f1_macro": 0.73,
    "confusion_matrix": [[3, 1, 0], [1, 3, 1], [0, 0, 3]]
  }
}
```

限制说明：响应示例仅展示结构，不代表实验结果。真实训练完成后必须记录到 `EXPERIMENT_LOG.md`。样本少于 `30` 时返回 `422` 与明确限制说明，不将演示结果表述为可靠结论。

### `POST /api/model/predict`

对已有会话调用最新可用模型生成预测。

请求：

```json
{
  "session_id": 101
}
```

响应 `201`：

```json
{
  "id": 901,
  "session_id": 101,
  "predicted_label": "high",
  "confidence": 0.78,
  "model_version": "rf_20260525_001",
  "suggestion": "保持明确学习目标，并继续减少手机干扰。",
  "created_at": "2026-05-25T15:21:00+08:00"
}
```

### `GET /api/model/metrics`

查询参数：可选 `model_version`；未传时返回当前模型的样本数、分类指标和混淆矩阵。

### `GET /api/model/feature-importance`

查询参数：可选 `model_version`；未传时返回当前模型按重要性降序排列的特征列表。

```json
{
  "model_version": "rf_20260525_001",
  "items": [
    {"feature_name": "phone_distraction", "importance_score": 0.21},
    {"feature_name": "fatigue_level", "importance_score": 0.18}
  ]
}
```

## 8. 分析 API

| 方法与路径 | 查询参数 | 返回内容 |
| --- | --- | --- |
| `GET /api/analytics/overview` | `user_id` | 总学习次数、总分钟数、平均评分、高效率占比 |
| `GET /api/analytics/trend` | `user_id`、可选日期范围 | 按日学习时长与效率评分趋势 |
| `GET /api/analytics/factor-analysis` | `user_id` | 按时间段对比、运动次数与效率关系等聚合分析 |

统计接口只使用已完成的会话；运动特征缺失记录仍纳入不依赖运动数据的统计。

## 9. P0 之外

以下接口延期：完整注册登录/JWT、`/api/users/me`、管理端接口、多用户横向比较、公开数据集导入和复杂推荐服务。
