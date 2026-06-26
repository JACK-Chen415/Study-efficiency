# TASKS.md

## Priority Labels

- P0：必须完成，否则 MVP 不成立。
- P1：建议完成，能明显提升答辩质量。
- P2：有时间再做，不影响主线。

---

## Week 1 - Scope, Docs & Project Skeleton

### P0

- [x] 创建项目根目录结构。
- [x] 创建 README.md。
- [x] 创建 AGENTS.md。
- [x] 创建 docs/PLAN.md。
- [x] 创建 docs/TASKS.md。
- [x] 创建 docs/API_SPEC.md。
- [x] 创建 docs/DATA_DICTIONARY.md。
- [x] 创建 docs/EXPERIMENT_LOG.md。
- [x] 明确 MVP 必做/延期清单。
- [x] 确定学习记录字段。
- [x] 确定效率等级转换规则。
- [x] 设计 users 表。
- [x] 设计 study_sessions 表。
- [x] 设计 motion_features 表。
- [x] 设计 predictions 表。
- [x] 画系统架构图草稿。
- [x] 画数据流图草稿。
- [x] 画页面草图。
- [x] 准备答辩主线：为什么做、做了什么、AI 如何体现、创新在哪里。

### P1

- [ ] 设计 model_metrics 表。
- [ ] 设计 feature_importance 表。
- [ ] 整理公开数据集作为背景材料。

---

## Week 2 - Backend & Database

### P0

- [x] 初始化 backend/FastAPI 项目。
- [x] 配置 requirements.txt。
- [x] 配置 MySQL 连接。
- [x] 配置 SQLAlchemy。
- [x] 实现 users 模型。
- [x] 实现 study_sessions 模型。
- [x] 实现 motion_features 模型。
- [x] 实现 predictions 模型。
- [x] 实现 POST /api/users/simple-login。
- [x] 实现 POST /api/sessions/start。
- [x] 实现 POST /api/sessions/end。
- [x] 实现 POST /api/sessions/{id}/abandon 软放弃未结束学习。
- [x] 实现 GET /api/sessions/list。
- [x] 实现 GET /api/sessions/{id}。
- [x] 实现 PUT /api/sessions/{id} 覆盖修改历史记录。
- [x] 实现 DELETE /api/sessions/{id} 并归档删除记录。
- [x] 实现 POST /api/motion/upload。
- [x] 实现 GET /api/motion/{session_id}。
- [x] 编写基础接口测试。
- [x] 确认 FastAPI /docs 可访问。
- [ ] 确认数据能写入 MySQL。

### P1

- [ ] 实现 GET /api/analytics/overview 的后端雏形。
- [ ] 实现基础 seed 数据脚本。

---

## Week 3 - Frontend Session Flow & Motion Feature

### P0

- [x] 初始化 frontend/Vue 3 + Vite 项目。
- [x] 安装移动端 UI 组件库。
- [x] 配置 API 请求封装。
- [x] 实现 simple-login 页面或入口。
- [x] 实现首页。
- [x] 实现学习中页面。
- [x] 实现计时器。
- [x] 实现结束学习表单页。
- [x] 实现历史记录页。
- [x] 历史记录支持删除，并将删除记录归档到备份表。
- [x] 历史记录支持修改，并覆盖更新原学习记录。
- [x] 接入后端 start/end/list API。
- [x] 接入 DeviceMotionEvent。
- [x] 实现传感器权限申请。
- [x] 统计 move_count。
- [x] 统计 shake_count。
- [x] 统计 still_ratio。
- [x] 统计 avg_acceleration。
- [x] 统计 max_acceleration。
- [x] 实现传感器不可用时的降级提示。
- [x] 上传运动特征。
- [x] 增加手机端应用内返回键与系统返回键拦截。
- [x] 增加学习中前台采集、Wake Lock 和后台暂停提示。
- [x] 修复重新进入页面时本地 active session 与后端学习会话状态校验。
- [x] 学习中支持“放弃本次学习”，避免服务器残留未结束 session 阻塞重新开始。
- [x] 首页增加真实采集使用指南与昵称数据说明。
- [x] 编写手机端页面流程文档。
- [x] 编写真实数据采集规范。
- [x] 编写演示脚本草案。
- [x] 编写截图清单。
- [x] 完成采集前科研设计审查。
- [x] 根据采集前审查更新采集规范文档。
- [x] npm run build 通过。
- [x] 拉取 Jahon 远端真实采集数据库到本地隔离目录并完成质检。
- [ ] 继续真实数据采集，目标至少 50 条有效 completed 记录。

### P1

- [x] 优化手机端 UI。
- [x] 增加学习中状态提示。
- [x] 增加提交成功反馈。

---

## Week 4 - Model Training & Prediction

### P0

- [x] 编写数据读取逻辑（Milestone 4A：从已完成学习记录导出训练 CSV）。
- [x] 编写训练前特征准备逻辑（Milestone 4A：合并自报告字段与运动特征）。
- [x] 实现效率评分到 low/medium/high 的转换。
- [x] 处理缺失运动特征（导出时运动字段填 0，并增加 `motion_available`）。
- [x] 生成训练数据 CSV 导出脚本。
- [x] 训练数据导出排除 abandoned 会话。
- [x] 增加 demo/mock seed 数据脚本。
- [x] 增加训练前数据质量检查脚本。
- [x] 检查是否满足最低训练样本数 30。
- [x] 更新训练前数据就绪检查与实验记录模板。
- [x] 处理类别特征 One-Hot（Milestone 4B：离线训练脚本）。
- [x] 训练 RandomForestClassifier（Milestone 4B：离线训练脚本）。
- [x] 输出 Accuracy（Milestone 4B：离线训练脚本）。
- [x] 输出 Precision（Milestone 4B：离线训练脚本）。
- [x] 输出 Recall（Milestone 4B：离线训练脚本）。
- [x] 输出 F1-score（Milestone 4B：离线训练脚本）。
- [x] 输出混淆矩阵（Milestone 4B：离线训练脚本）。
- [x] 输出特征重要性（Milestone 4B：离线训练脚本）。
- [x] 保存模型 latest.joblib（Milestone 4B：离线训练脚本；模型 artifact 不提交）。
- [x] 实现 POST /api/model/train。
- [x] 实现 POST /api/model/predict。
- [x] 实现 GET /api/model/metrics。
- [x] 实现 GET /api/model/feature-importance。
- [x] 数据不足时返回明确提示（Milestone 4B：离线训练脚本与模型 API）。
- [x] 将训练结果写入 docs/EXPERIMENT_LOG.md。

### P1

- [ ] 增加 DecisionTreeClassifier 对比实验。
- [ ] 增加 LogisticRegression 对比实验。
- [ ] 增加 RandomForestRegressor 补充实验。

---

## Week 5 - Dashboard & Integration

### P0

- [x] 实现 GET /api/analytics/overview。
- [x] 实现 GET /api/analytics/trend。
- [x] 实现 GET /api/analytics/factor-analysis。
- [x] 前端实现总览统计卡片。
- [x] 前端实现学习时长趋势图。
- [x] 前端实现效率评分趋势图。
- [x] 前端实现时间段效率对比图。
- [x] 前端实现特征重要性图。
- [x] 前端实现运动次数与效率散点图。
- [x] 前端展示预测等级。
- [x] 前端展示预测置信度。
- [x] 前端展示系统建议。
- [x] 实现规则建议：
  - 高疲劳建议
  - 强手机干扰建议
  - 目标清晰度低建议
  - 噪声高建议
  - 深夜学习建议
- [ ] 完成端到端联调：打卡 → 填表 → 保存 → 训练 → 预测 → 看板展示。

### P1

- [x] 增加模型指标展示区。
- [ ] 增加混淆矩阵展示。
- [ ] 增加记录详情页。

---

## Week 6 - Freeze, Polish & Defense

### P0

- [ ] 冻结功能，不再新增大模块。
- [ ] 修复核心流程 bug。
- [x] 补齐演示数据，目标至少 50 条。
- [ ] 整理系统截图。
- [ ] 整理数据库截图。
- [ ] 整理 API 文档截图。
- [ ] 整理模型训练结果截图。
- [ ] 整理看板截图。
- [ ] 准备项目报告。
- [ ] 准备答辩 PPT。
- [ ] 准备系统演示脚本。
- [ ] 准备备用演示录屏。
- [ ] 整理风险说明：
  - 传感器兼容性
  - 数据量不足
  - 模型准确率有限
  - 部署环境不稳定
- [ ] 做一次完整答辩彩排。

### P1

- [ ] 美化前端页面。
- [ ] 优化 README。
- [ ] 增加一键启动说明。
- [ ] 增加 .env.example。
- [ ] 增加 demo 数据导入脚本。

---

## P0 Final Checklist

- [ ] 手机端开始学习可用。
- [ ] 手机端结束学习可用。
- [ ] 自报告表单可提交。
- [ ] 数据能进入 MySQL。
- [ ] 历史记录可查看。
- [ ] 运动特征可采集或可降级。
- [ ] 至少一种模型可训练。
- [ ] 能预测低/中/高效率。
- [ ] 能展示模型指标。
- [ ] 能展示特征重要性。
- [ ] 看板能展示统计和趋势。
- [ ] 有报告。
- [ ] 有 PPT。
- [ ] 有演示流程。
- [ ] 有备用录屏或备用样例数据。

---

## P1 Final Checklist

- [ ] 特征重要性可视化。
- [ ] 混淆矩阵展示。
- [ ] 手机运动散点图。
- [ ] 规则建议较完整。
- [ ] 回归模型补充实验。
- [ ] 一键启动说明。
- [ ] demo 数据脚本。

---

## P2 Final Checklist

- [ ] 完整登录注册。
- [ ] 管理端。
- [ ] 多模型调参。
- [ ] 云端 HTTPS 部署。
- [ ] 公开数据集对比实验。
