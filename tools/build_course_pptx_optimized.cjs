const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "deliverables");
const FIG = path.join(OUT, "figures");
const PPTX_NAME = "202400502094+陈嘉宏+24级物联网1班.pptx";

const TITLE = "基于手机轻量感知与自报告数据的大学生学习效率预测系统设计与实现";
const CLASS_NAME = "24级物联网1班";
const MEMBER_1 = "陈嘉宏（202400502094）";
const MEMBER_2 = "蔡天成（202401100012）";

const C = {
  primary: "264653",
  secondary: "2A9D8F",
  accent: "E9C46A",
  warm: "F4A261",
  danger: "E76F51",
  bg: "F7FBFB",
  surface: "FFFFFF",
  ink: "172033",
  muted: "657287",
  line: "D9E4EA",
  softTeal: "E8F6F1",
  softYellow: "FFF4D6",
  softWarm: "FCEDE9",
  deep: "122A36",
};

const font = "Microsoft YaHei";
const fontEn = "Arial";
const pptx = new pptxgen();
pptx.defineLayout({ name: "COURSE_16_9", width: 10, height: 5.625 });
pptx.layout = "COURSE_16_9";
pptx.author = "陈嘉宏, 蔡天成";
pptx.company = "24级物联网1班";
pptx.subject = "Python 期末课程设计答辩";
pptx.title = TITLE;
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: font,
  bodyFontFace: font,
  lang: "zh-CN",
};

function cleanHex(hex) {
  return String(hex).replace("#", "").toUpperCase();
}

function bg(slide, color = C.bg) {
  slide.background = { color: cleanHex(color) };
}

function text(slide, value, x, y, w, h, opts = {}) {
  slide.addText(value, {
    x, y, w, h,
    fontFace: opts.fontFace || font,
    fontSize: opts.size || 14,
    color: cleanHex(opts.color || C.ink),
    bold: Boolean(opts.bold),
    italic: Boolean(opts.italic),
    align: opts.align || "left",
    valign: opts.valign || "top",
    margin: opts.margin ?? 0.04,
    breakLine: false,
    fit: opts.fit || "shrink",
  });
}

function shape(slide, type, x, y, w, h, opts = {}) {
  slide.addShape(type, {
    x, y, w, h,
    rectRadius: opts.radius ?? 0.08,
    fill: opts.fill ? { color: cleanHex(opts.fill), transparency: opts.transparency || 0 } : { color: cleanHex(C.surface), transparency: 100 },
    line: opts.line ? { color: cleanHex(opts.line), width: opts.lineWidth || 1 } : { color: cleanHex(opts.fill || C.line), transparency: 100 },
    rotate: opts.rotate || 0,
  });
}

function rect(slide, x, y, w, h, fill, opts = {}) {
  shape(slide, pptx.ShapeType.rect, x, y, w, h, {
    fill,
    line: opts.line || fill,
    lineWidth: opts.lineWidth || 0.5,
    transparency: opts.transparency || 0,
    radius: 0,
  });
}

function card(slide, x, y, w, h, opts = {}) {
  shape(slide, pptx.ShapeType.roundRect, x, y, w, h, {
    fill: opts.fill || C.surface,
    line: opts.line || C.line,
    lineWidth: opts.lineWidth || 0.8,
    radius: opts.radius ?? 0.1,
  });
}

function badge(slide, x, y, label, opts = {}) {
  const w = opts.w || 1.1;
  const h = opts.h || 0.34;
  card(slide, x, y, w, h, { fill: opts.fill || C.softTeal, line: opts.fill || C.softTeal, radius: 0.16 });
  text(slide, label, x, y + 0.055, w, h - 0.06, {
    size: opts.size || 9.5,
    color: opts.color || C.primary,
    bold: true,
    align: "center",
    margin: 0,
  });
}

function page(slide, n) {
  shape(slide, pptx.ShapeType.ellipse, 9.3, 5.1, 0.4, 0.4, { fill: C.secondary, line: C.secondary });
  text(slide, String(n).padStart(2, "0"), 9.3, 5.18, 0.4, 0.18, {
    fontFace: fontEn,
    size: 10,
    color: C.surface,
    bold: true,
    align: "center",
    margin: 0,
  });
}

function title(slide, value, n, section = "Python 课程设计") {
  text(slide, value, 0.48, 0.32, 7.7, 0.5, { size: 26, color: C.primary, bold: true });
  badge(slide, 8.18, 0.38, section, { w: 1.18, fill: C.softTeal, size: 8.5 });
  if (n) page(slide, n);
}

function smallCaption(slide, value, x, y, w, h) {
  text(slide, value, x, y, w, h, { size: 8.5, color: C.muted, align: "center", margin: 0.02 });
}

function cardText(slide, x, y, w, h, heading, body, opts = {}) {
  card(slide, x, y, w, h, { fill: opts.fill || C.surface, line: opts.line || C.line, radius: opts.radius ?? 0.1 });
  text(slide, heading, x + 0.18, y + 0.15, w - 0.36, 0.28, {
    size: opts.headingSize || 14,
    color: opts.headingColor || C.primary,
    bold: true,
  });
  text(slide, body, x + 0.18, y + 0.52, w - 0.36, h - 0.62, {
    size: opts.bodySize || 11.5,
    color: opts.bodyColor || C.ink,
    margin: 0.03,
  });
}

function statCard(slide, x, y, w, h, number, label, opts = {}) {
  card(slide, x, y, w, h, { fill: opts.fill || C.surface, line: opts.line || C.line, radius: 0.12 });
  text(slide, number, x + 0.18, y + 0.18, w - 0.36, h * 0.45, {
    fontFace: fontEn,
    size: opts.numberSize || 34,
    color: opts.color || C.primary,
    bold: true,
    align: "center",
    margin: 0,
  });
  text(slide, label, x + 0.18, y + h - 0.42, w - 0.36, 0.25, {
    size: opts.labelSize || 9.5,
    color: opts.labelColor || C.muted,
    align: "center",
    margin: 0,
  });
}

function arrow(slide, x, y, w = 0.28, h = 0.16, color = C.secondary) {
  shape(slide, pptx.ShapeType.rightArrow, x, y, w, h, { fill: color, line: color, radius: 0.02 });
}

function node(slide, x, y, w, h, heading, body, opts = {}) {
  card(slide, x, y, w, h, { fill: opts.fill || C.surface, line: opts.line || C.secondary, radius: 0.09 });
  if (opts.num) {
    shape(slide, pptx.ShapeType.ellipse, x + 0.12, y + 0.14, 0.28, 0.28, { fill: opts.numFill || C.secondary, line: opts.numFill || C.secondary });
    text(slide, opts.num, x + 0.12, y + 0.195, 0.28, 0.12, {
      fontFace: fontEn,
      size: 8,
      color: C.surface,
      bold: true,
      align: "center",
      margin: 0,
    });
    text(slide, heading, x + 0.46, y + 0.13, w - 0.58, 0.24, { size: 11.2, color: opts.headingColor || C.primary, bold: true });
  } else {
    text(slide, heading, x + 0.12, y + 0.13, w - 0.24, 0.24, { size: 11.2, color: opts.headingColor || C.primary, bold: true });
  }
  text(slide, body, x + 0.12, y + 0.43, w - 0.24, h - 0.48, { size: opts.bodySize || 8.8, color: C.ink, margin: 0.02 });
}

function bulletList(slide, items, x, y, w, h, opts = {}) {
  const runs = [];
  items.forEach((item, i) => {
    runs.push({
      text: `${i + 1}. ${item}`,
      options: {
        breakLine: i < items.length - 1,
        fontFace: font,
        fontSize: opts.size || 12.5,
        color: cleanHex(opts.color || C.ink),
        bold: false,
      },
    });
  });
  slide.addText(runs, {
    x, y, w, h,
    fit: "shrink",
    valign: "top",
    margin: 0.04,
    breakLine: false,
    paraSpaceAfterPt: opts.spaceAfter || 8,
  });
}

function readMetrics() {
  const metricsPath = path.join(ROOT, "data/processed/mock/model_metrics_mock_20260618.json");
  const fiPath = path.join(ROOT, "data/processed/mock/feature_importance_mock_20260618.csv");
  let metrics = {};
  if (fs.existsSync(metricsPath)) {
    metrics = JSON.parse(fs.readFileSync(metricsPath, "utf8"));
  }
  let features = [
    ["noise_level", 0.151744],
    ["phone_distraction", 0.147538],
    ["mood_stress", 0.114447],
    ["light_level", 0.113204],
    ["move_count", 0.089503],
  ];
  if (fs.existsSync(fiPath)) {
    const lines = fs.readFileSync(fiPath, "utf8").trim().split(/\r?\n/);
    const headers = lines.shift().split(",");
    const featureIndex = headers.indexOf("feature");
    const importanceIndex = headers.indexOf("importance");
    features = lines.slice(0, 5).map((line) => {
      const cols = line.split(",");
      return [cols[featureIndex], Number(cols[importanceIndex])];
    });
  }
  return { metrics, features };
}

function cover() {
  const slide = pptx.addSlide();
  bg(slide, "F8FAFC");
  rect(slide, 0, 0, 3.0, 5.625, C.deep);
  rect(slide, 0, 4.95, 10, 0.675, C.softTeal);
  badge(slide, 0.45, 0.52, "Python 期末课程设计", { w: 1.55, fill: C.secondary, color: C.surface, size: 9 });
  text(slide, "学习效率\n预测系统", 0.42, 1.22, 2.15, 1.25, { size: 31, color: C.surface, bold: true, margin: 0.02 });
  text(slide, "手机轻量感知 + 自报告数据 + 随机森林三分类", 0.45, 3.26, 2.16, 0.62, { size: 12, color: C.accent, bold: true });
  text(slide, TITLE, 3.42, 0.74, 5.0, 1.25, { size: 28, color: C.primary, bold: true });
  text(slide, "课程目标是交付一个可运行、可演示、可解释的 Python 全栈课程设计系统。", 3.44, 2.18, 4.9, 0.45, { size: 14, color: C.ink });
  card(slide, 3.44, 3.08, 2.3, 1.0, { fill: C.surface, line: C.line });
  text(slide, "真实数据质检", 3.68, 3.24, 1.8, 0.25, { size: 12, color: C.primary, bold: true, align: "center" });
  text(slide, "completed = 17", 3.68, 3.62, 1.8, 0.22, { size: 12, color: C.muted, align: "center" });
  card(slide, 6.02, 3.08, 2.3, 1.0, { fill: C.softWarm, line: C.danger });
  text(slide, "mock 流程演示", 6.24, 3.24, 1.86, 0.25, { size: 12, color: C.primary, bold: true, align: "center" });
  text(slide, "training = 120", 6.24, 3.62, 1.86, 0.22, { size: 12, color: C.muted, align: "center" });

  const home = path.join(FIG, "ui-1-home.png");
  const dash = path.join(FIG, "ui-4-dashboard.png");
  if (fs.existsSync(home)) {
    card(slide, 8.56, 0.62, 0.96, 2.08, { fill: C.surface, line: C.line, radius: 0.12 });
    slide.addImage({ path: home, x: 8.61, y: 0.72, w: 0.86, h: 1.86 });
  }
  if (fs.existsSync(dash)) {
    card(slide, 8.33, 2.75, 1.18, 2.55, { fill: C.surface, line: C.line, radius: 0.12 });
    slide.addImage({ path: dash, x: 8.39, y: 2.87, w: 1.06, h: 2.3 });
  }
  text(slide, `${CLASS_NAME}    ${MEMBER_1}    ${MEMBER_2}`, 3.42, 5.12, 5.8, 0.25, { size: 10.5, color: C.primary, bold: true });
}

function backgroundGoal() {
  const slide = pptx.addSlide();
  bg(slide);
  title(slide, "课程设计背景与目标", 2, "目标与边界");
  cardText(slide, 0.58, 1.08, 2.55, 2.45, "问题背景", "只记录学习时长，很难解释真实效率差异。同样学习 60 分钟，结果可能受任务类型、疲劳、环境噪声和手机干扰影响。", { line: C.secondary, bodySize: 11.2 });
  cardText(slide, 3.47, 1.08, 2.55, 2.45, "系统做法", "用手机浏览器完成学习打卡、自报告量表和可选运动聚合特征采集；后端统一保存并导出训练数据。", { fill: C.softTeal, line: C.secondary, bodySize: 11.2 });
  cardText(slide, 6.36, 1.08, 2.55, 2.45, "交付目标", "优先保证系统能跑通、能演示、能讲清 Python 后端、数据处理、模型预测与看板展示，不追求论文级实验。", { fill: C.softYellow, line: C.accent, bodySize: 11.2 });
  rect(slide, 0.58, 4.1, 8.34, 0.72, C.deep);
  text(slide, "主线", 0.9, 4.31, 0.7, 0.18, { size: 12, color: C.accent, bold: true, margin: 0 });
  text(slide, "手机轻量感知 → Python 后端 → 数据清洗 → RandomForest 预测 → 分析看板", 1.62, 4.28, 6.85, 0.22, { size: 13, color: C.surface, bold: true, margin: 0 });
}

function architecture() {
  const slide = pptx.addSlide();
  bg(slide);
  title(slide, "系统总体架构", 3, "系统设计");
  const items = [
    ["手机浏览器", "打卡、自报告\n可选运动采集"],
    ["Vue 3 前端", "页面流程\n分析看板"],
    ["FastAPI 后端", "业务校验\n模型服务"],
    ["数据库", "users / sessions\nmotion / predictions"],
  ];
  items.forEach(([h, b], i) => {
    node(slide, 0.55 + i * 2.0, 1.1, 1.52, 1.08, h, b, { fill: i % 2 ? C.softTeal : C.surface, num: String(i + 1), bodySize: 8.7 });
    if (i < items.length - 1) arrow(slide, 2.13 + i * 2.0, 1.55, 0.38, 0.18, C.secondary);
  });
  node(slide, 2.25, 3.18, 1.65, 1.02, "Python 脚本", "导出 CSV\n质量检查", { fill: C.softYellow, line: C.accent, num: "A", numFill: C.accent });
  node(slide, 4.35, 3.18, 1.65, 1.02, "RandomForest", "低/中/高三分类\n指标与重要性", { fill: C.softWarm, line: C.danger, num: "B", numFill: C.danger, bodySize: 8.2 });
  arrow(slide, 3.96, 3.61, 0.34, 0.16, C.primary);
  shape(slide, pptx.ShapeType.downArrow, 6.58, 2.12, 0.28, 0.48, { fill: C.primary, line: C.primary });
  shape(slide, pptx.ShapeType.leftArrow, 6.06, 3.58, 0.42, 0.18, { fill: C.primary, line: C.primary });
  cardText(slide, 7.42, 2.72, 1.98, 1.56, "设计边界", "simple-login\n不做复杂认证\n传感器可缺失\n演示环境可降级", { bodySize: 9.6, line: C.line });
  smallCaption(slide, "架构强调课程设计主链路：采集、存储、训练、预测、展示。", 0.78, 4.78, 8.1, 0.18);
}

function collectionFlow() {
  const slide = pptx.addSlide();
  bg(slide);
  title(slide, "手机端采集流程", 4, "采集流程");
  const steps = [
    ["登录", "自选昵称"],
    ["开始", "创建会话"],
    ["学习中", "计时/运动聚合"],
    ["结束表单", "填写量表"],
    ["保存", "生成标签"],
    ["看板", "趋势预测"],
  ];
  steps.forEach(([h, b], i) => {
    node(slide, 0.42 + i * 1.55, 1.16, 1.22, 1.02, h, b, {
      fill: i === 2 ? C.softYellow : (i === 5 ? C.softWarm : C.surface),
      line: i === 2 ? C.accent : (i === 5 ? C.danger : C.secondary),
      num: String(i + 1),
      bodySize: 8,
    });
    if (i < steps.length - 1) arrow(slide, 1.67 + i * 1.55, 1.57, 0.24, 0.14, C.secondary);
  });
  rect(slide, 0.62, 3.02, 8.75, 1.52, C.deep);
  text(slide, "降级策略", 0.92, 3.26, 1.15, 0.28, { size: 15, color: C.accent, bold: true, margin: 0 });
  text(slide, "DeviceMotionEvent 不可用、权限被拒绝、页面进入后台或运动特征上传失败时，系统仍允许提交自报告记录。训练导出阶段使用 motion_available 标记缺失机制。", 2.15, 3.18, 6.55, 0.72, { size: 13, color: C.surface, margin: 0.02 });
  badge(slide, 7.55, 4.03, "不阻断主流程", { w: 1.35, fill: C.accent, color: C.deep });
}

function backendApi() {
  const slide = pptx.addSlide();
  bg(slide);
  title(slide, "后端 API 与数据存储", 5, "后端实现");
  const modules = [
    ["用户", "POST /users/simple-login"],
    ["学习记录", "start / end / list / detail"],
    ["运动特征", "upload / get\n按 session upsert"],
    ["模型", "train / predict\nmetrics / importance"],
    ["分析", "overview / trend\nfactor-analysis"],
  ];
  modules.forEach(([h, b], i) => {
    const x = 0.55 + i * 1.78;
    card(slide, x, 1.18, 1.42, 2.25, { fill: i % 2 ? C.surface : C.softTeal, line: C.secondary, radius: 0.08 });
    text(slide, String(i + 1).padStart(2, "0"), x + 0.16, 1.35, 1.1, 0.32, { fontFace: fontEn, size: 20, color: i % 2 ? C.secondary : C.primary, bold: true, align: "center" });
    text(slide, h, x + 0.16, 1.88, 1.1, 0.28, { size: 13, color: C.primary, bold: true, align: "center" });
    text(slide, b, x + 0.14, 2.42, 1.14, 0.54, { size: 8.6, color: C.ink, align: "center" });
  });
  cardText(slide, 0.7, 4.05, 8.55, 0.8, "P0 数据表", "users、study_sessions、motion_features、predictions；删除历史记录时先写入 deleted_study_sessions 备份表，避免直接丢失用户记录。", { bodySize: 11.2, line: C.line });
}

function modelPipeline() {
  const slide = pptx.addSlide();
  bg(slide);
  title(slide, "特征工程与模型方法", 6, "模型流程");
  const steps = [
    ["completed 会话", "排除 abandoned"],
    ["导出 CSV", "左连接运动特征"],
    ["质量检查", "样本/缺失/越界"],
    ["特征工程", "One-Hot + 填补"],
    ["随机森林", "低/中/高三分类"],
    ["输出", "指标/混淆矩阵/重要性"],
  ];
  steps.forEach(([h, b], i) => {
    const x = 0.42 + i * 1.55;
    node(slide, x, 1.12, 1.2, 1.0, h, b, {
      fill: i < 3 ? C.softYellow : (i === 3 ? C.softTeal : C.softWarm),
      line: i < 3 ? C.accent : (i === 3 ? C.secondary : C.danger),
      num: String(i + 1),
      numFill: i < 3 ? C.accent : (i === 3 ? C.secondary : C.danger),
      bodySize: 7.8,
    });
    if (i < steps.length - 1) arrow(slide, 1.65 + i * 1.55, 1.53, 0.25, 0.14, C.primary);
  });
  cardText(slide, 0.78, 3.08, 3.9, 1.15, "标签转换", "efficiency_score：1-2 → low，3 → medium，4-5 → high", { bodySize: 12, line: C.line });
  cardText(slide, 5.25, 3.08, 3.9, 1.15, "缺失处理", "无运动数据时保留样本，运动字段填 0，并增加 motion_available。", { bodySize: 12, line: C.line });
  smallCaption(slide, "模型用于课程演示链路验证；真实样本不足时不包装成泛化结论。", 1.0, 4.78, 8.0, 0.18);
}

function dataBoundary() {
  const slide = pptx.addSlide();
  bg(slide);
  title(slide, "数据来源与实验口径", 7, "实验口径");
  statCard(slide, 0.78, 1.05, 2.02, 1.35, "17", "真实 completed 记录", { color: C.secondary, line: C.secondary });
  statCard(slide, 3.02, 1.05, 2.02, 1.35, "11", "运动特征缺失记录", { color: C.danger, fill: C.softWarm, line: C.danger });
  statCard(slide, 5.26, 1.05, 2.02, 1.35, "120", "mock 训练/演示记录", { color: C.primary, fill: C.softYellow, line: C.accent });
  statCard(slide, 7.5, 1.05, 1.72, 1.35, "40/40/40", "mock 三类均衡", { color: C.primary, line: C.line, numberSize: 22 });
  cardText(slide, 0.78, 2.78, 3.9, 1.26, "真实数据用途", "说明系统已经支持真实采集与质量检查；由于样本少于 30 条，不作为正式训练结论。", { line: C.secondary, bodySize: 11.2 });
  cardText(slide, 5.25, 2.78, 3.9, 1.26, "mock 数据用途", "用于证明训练、预测、指标展示和看板流程可运行；不代表真实学习规律。", { fill: C.softWarm, line: C.danger, bodySize: 11.2 });
  badge(slide, 2.1, 4.52, "结论边界：演示链路成立，不声称模型已经具有真实场景泛化能力", { w: 5.8, fill: C.deep, color: C.surface, size: 10.2 });
}

function uiScreens() {
  const slide = pptx.addSlide();
  bg(slide, "F8FAFC");
  title(slide, "系统界面与看板结果", 8, "界面展示");
  const collage = path.join(FIG, "fig4-ui-collage.png");
  if (fs.existsSync(collage)) {
    card(slide, 1.12, 0.92, 7.72, 4.56, { fill: C.surface, line: C.line, radius: 0.1 });
    slide.addImage({ path: collage, x: 1.18, y: 1.0, w: 7.6, h: 4.46 });
  } else {
    cardText(slide, 1.2, 1.35, 7.6, 2.5, "截图素材缺失", "请先运行截图自动化脚本生成 fig4-ui-collage.png。", { line: C.danger });
  }
  smallCaption(slide, "截图由浏览器自动采集；看板为 mock/demo 流程展示。", 1.15, 5.25, 7.65, 0.18);
}

function modelResult() {
  const slide = pptx.addSlide();
  bg(slide);
  title(slide, "模型指标与特征重要性", 9, "结果展示");
  const { metrics, features } = readMetrics();
  const rf = metrics.random_forest || {};
  const dummy = metrics.dummy_baseline || {};
  const metricItems = [
    ["Accuracy", rf.accuracy ?? 1.0, dummy.accuracy ?? 0.333333],
    ["Precision", rf.precision_macro ?? 1.0, dummy.precision_macro ?? 0.111111],
    ["Recall", rf.recall_macro ?? 1.0, dummy.recall_macro ?? 0.333333],
    ["F1 Macro", rf.f1_macro ?? 1.0, dummy.f1_macro ?? 0.166667],
  ];
  card(slide, 0.62, 1.05, 4.45, 3.35, { fill: C.surface, line: C.line, radius: 0.1 });
  text(slide, "mock 指标对比", 0.9, 1.25, 2.3, 0.28, { size: 14, color: C.primary, bold: true });
  metricItems.forEach(([name, value, base], i) => {
    const y = 1.76 + i * 0.56;
    text(slide, name, 0.9, y, 1.05, 0.22, { fontFace: fontEn, size: 10.5, color: C.ink, bold: true });
    rect(slide, 2.05, y + 0.04, 2.1, 0.12, C.softTeal);
    rect(slide, 2.05, y + 0.04, 2.1 * Number(value), 0.12, C.secondary);
    text(slide, `${Number(value).toFixed(3)} / ${Number(base).toFixed(3)}`, 4.25, y - 0.015, 0.58, 0.18, { fontFace: fontEn, size: 8.5, color: C.muted, align: "right", margin: 0 });
  });
  smallCaption(slide, "格式：RandomForest / Dummy baseline", 1.05, 4.06, 3.65, 0.16);

  card(slide, 5.42, 1.05, 3.95, 3.35, { fill: C.surface, line: C.line, radius: 0.1 });
  text(slide, "Top 5 特征重要性", 5.7, 1.25, 2.4, 0.28, { size: 14, color: C.primary, bold: true });
  const max = Math.max(...features.map(([, v]) => Number(v)));
  features.forEach(([name, value], i) => {
    const y = 1.78 + i * 0.48;
    text(slide, name, 5.74, y, 1.35, 0.18, { fontFace: fontEn, size: 8.8, color: C.ink, margin: 0 });
    rect(slide, 7.05, y + 0.04, 1.55, 0.11, C.softYellow);
    rect(slide, 7.05, y + 0.04, 1.55 * Number(value) / max, 0.11, i % 2 ? C.accent : C.secondary);
    text(slide, Number(value).toFixed(3), 8.68, y - 0.005, 0.36, 0.16, { fontFace: fontEn, size: 8, color: C.muted, margin: 0 });
  });
  cardText(slide, 0.82, 4.62, 8.35, 0.58, "口径说明", "这些指标来自 120 条 mock 数据，只证明 Python 训练、预测和看板链路可运行，不证明真实场景泛化能力。", { fill: C.softWarm, line: C.danger, bodySize: 10.2, headingSize: 11.2 });
}

function demoRisk() {
  const slide = pptx.addSlide();
  bg(slide);
  title(slide, "演示流程与风险处理", 10, "答辩演示");
  card(slide, 0.72, 1.08, 3.75, 3.55, { fill: C.surface, line: C.secondary, radius: 0.1 });
  text(slide, "5 分钟演示顺序", 1.0, 1.3, 2.1, 0.3, { size: 15, color: C.primary, bold: true });
  bulletList(slide, [
    "输入昵称进入系统",
    "点击开始学习并观察计时状态",
    "结束后填写地点、任务和量表",
    "查看历史记录、分析看板和预测建议",
    "说明真实数据与 mock 数据边界",
  ], 1.0, 1.85, 2.9, 2.35, { size: 11.4, spaceAfter: 7 });

  cardText(slide, 5.05, 1.08, 3.95, 0.82, "传感器兼容性", "运动特征可缺失，不阻断学习记录主流程。", { line: C.secondary, bodySize: 10.6, headingSize: 12.5 });
  cardText(slide, 5.05, 2.18, 3.95, 0.82, "真实样本不足", "真实 completed=17，只做质检，不包装成模型结论。", { fill: C.softYellow, line: C.accent, bodySize: 10.6, headingSize: 12.5 });
  cardText(slide, 5.05, 3.28, 3.95, 0.82, "演示环境波动", "准备截图、mock 数据和代码包，保证答辩能讲清链路。", { fill: C.softWarm, line: C.danger, bodySize: 10.6, headingSize: 12.5 });
}

function summary() {
  const slide = pptx.addSlide();
  bg(slide, "F8FAFC");
  title(slide, "总结与成员分工", 11, "总结");
  cardText(slide, 0.72, 1.05, 4.05, 2.55, "完成内容", "手机端打卡、自报告采集、FastAPI 后端、训练数据导出、随机森林三分类、预测接口和分析看板。", { line: C.secondary, bodySize: 12.2 });
  cardText(slide, 5.15, 1.05, 4.05, 2.55, "成员分工", `${MEMBER_1}：系统需求、后端接口、数据字典、模型训练脚本、论文结果整理。\n${MEMBER_2}：前端页面、手机运动采集、看板展示、PPT 制作、演示材料整理。`, { line: C.danger, bodySize: 9.7 });
  rect(slide, 0.72, 4.18, 8.48, 0.68, C.deep);
  text(slide, "谢谢老师，请批评指正。", 0.72, 4.36, 8.48, 0.28, { size: 25, color: C.surface, bold: true, align: "center", margin: 0 });
}

cover();
backgroundGoal();
architecture();
collectionFlow();
backendApi();
modelPipeline();
dataBoundary();
uiScreens();
modelResult();
demoRisk();
summary();

fs.mkdirSync(OUT, { recursive: true });
const outPath = path.join(OUT, PPTX_NAME);
pptx.writeFile({ fileName: outPath }).then(() => {
  console.log(outPath);
});
