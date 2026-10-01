# 农智 AI 顾问系统

> 基于多模态小样本的农作物病虫害 + 缺肥智能诊断与农事 AI 顾问系统 · 国赛参赛项目

## 一句话简介

针对传统农业 AI 识别准确率低、无法区分病害/虫害/缺素/药害、农村弱网无法使用的痛点，本项目基于小样本视觉模型 + 农业 RAG 知识库，实现手机拍照离线识别病虫害、自动溯源减产原因、智能生成绿色农事方案，打造轻量化普惠式 AI 农技助手。

## 核心创新点

1. **多模态区分四类田间问题** —— 真菌病害 / 虫害 / 土壤缺肥 / 农药药害，解决肉眼易混淆痛点
2. **双模型级联 + 域检查门** —— 病害模型（55 类）与虫害模型（21 类）按序推理，
   并在**模型之前**加一道轻量域检查，杜绝无关图片（截图、食物、监控画面）被高置信度误判
3. **离线轻量化部署** —— ONNX Runtime 纯 CPU 推理，无需 GPU、无需联网即可识别，适配农村偏远场景
4. **AI 农事大模型顾问** —— 农业垂直 RAG 知识库，输出精准用药、施肥、绿色减药方案

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + Pinia + Element Plus |
| 后端 | Python FastAPI + SQLAlchemy + SQLite + JWT 认证 |
| 推理 | ONNX Runtime（CPU）· YOLOv8n 病害模型 + YOLOv8m 虫害模型 |
| 知识库 | FAISS 向量检索 + 关键词回退（离线可用） |
| 自训管线 | `algorithm/`（可选：数据集构建 → 训练 → 量化 → 导出 ONNX，用于替换开源权重） |

> **关于模型来源（口径说明）**：当前线上推理使用的是两个开源预训练权重
> （来源见下方「获取模型权重」），本项目的工作集中在**本地双模型编排、域检查门、
> 细分类映射与农业知识方案生成**；`algorithm/` 提供自训链路，可用于用自己的田间数据
> 微调后替换权重，不是当前推理路径的前置条件。

## 项目结构

```
AgriculturalScience/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── main.py          # 入口（中间件 + 异常处理）
│   │   ├── config.py        # 配置中心
│   │   ├── schemas.py       # Pydantic 请求/响应模型
│   │   ├── api/             # 路由（识别/RAG/历史/农事/系统）
│   │   ├── core/
│   │   │   ├── model_inference.py   # YOLOv8 推理（启发式回退）
│   │   │   ├── rag_engine.py        # RAG 引擎（FAISS + 关键词回退）
│   │   │   ├── scheme_generator.py  # 治理方案生成
│   │   │   ├── middleware.py        # 请求日志 + 滑动窗口限流
│   │   │   └── exceptions.py        # 统一异常处理
│   │   └── db/              # ORM 模型 + 数据库
│   ├── knowledge/           # 农业知识库 JSON + 向量库构建
│   └── requirements.txt
├── frontend/                # Vue 3 前端（企业仪表盘架构）
│   ├── src/
│   │   ├── views/           # 首页/识别/顾问/历史/日历
│   │   ├── components/      # StatCard/Chart/DetectionCanvas 等 8 个通用组件
│   │   ├── layouts/         # DefaultLayout 仪表盘布局
│   │   ├── stores/          # Pinia 状态
│   │   ├── api/             # 接口封装
│   │   └── styles/          # 设计令牌 + 8px网格 + 全局样式
│   ├── vite.config.js       # chunk 拆分 + 代理
│   └── package.json
├── algorithm/               # 算法模块
│   ├── yolov8_lite/         # 轻量化模型 + 训练 + 量化
│   ├── sam_fewshot/         # SAM 小样本分割
│   ├── data_builder/        # 数据集自动构建 + 增强
│   └── train.py             # 一键全流程
└── docs/                    # 项目说明书/创新点/部署教程
```

## 快速开始

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python knowledge/build_vector_db.py   # 构建 RAG 知识库
# 固定 8001 端口；不加 --reload（改完代码手动重启更可靠）
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev -- --port 5188 --strictPort   # 启动 http://localhost:5188
```

> 前端固定 5188：`vite.config` 默认端口是 5173，而 5173 已被本机另一个项目占用，
> 直接 `npm run dev` 会被自动顺延或占用他人端口。生产预览同理：
> `npm run build && npm run preview -- --port 5188 --strictPort`。
> 也可用根目录的 `start.bat` 一键启动（已统一为 8001 + 5188）。

### 3.（可选）训练模型

```bash
cd algorithm
pip install -r requirements.txt
python train.py                       # 一键：构建数据集→训练→量化→部署
```

> 未训练模型时，系统使用启发式识别回退，保证开箱即可演示。

### 4. 获取模型权重（仓库不含）

模型权重文件体积较大（合计约 226MB），**已通过 `.gitignore` 排除，不在本仓库内**。
克隆后请按下表下载并放置到 `backend/data/models/` 目录：

| 文件 | 用途 | 规模 | 来源 |
|---|---|---|---|
| `plant_disease_yolov8n.onnx` | 作物叶部病害检测（YOLOv8n，55 类） | 约 6MB | GitHub `GithubSpy/Plant_Disease_Detection_YOLOv8n` |
| `insect_best.onnx` | 田间害虫检测（YOLOv8m，21 类） | 约 93MB | HuggingFace `Mustafa5645344/insect-detection-yolov8`（国内可用 `hf-mirror.com` 镜像） |

若只有 `.pt` 权重，可用 ultralytics 导出为 ONNX：

```bash
python -c "from ultralytics import YOLO; YOLO('insect_best.pt').export(format='onnx', imgsz=640, opset=12)"
```

> 无模型文件时系统自动降级为「本地视觉分析」（启发式），功能不受影响。

## 文档

- [项目说明书](docs/项目说明书.md)
- [创新点介绍](docs/创新点介绍.md)
- [部署教程](docs/部署教程.md)

## 架构亮点

- **企业级设计系统**：完整设计令牌（8px 网格、双色融合渐变、5 级阴影、双字体、动效曲线、深色模式）
- **通用组件库**：StatCard / Chart(ECharts 封装) / DetectionCanvas / CategoryBadge 等 8 个可复用组件
- **仪表盘布局**：可折叠侧边栏 + 顶栏（搜索/通知/主题/用户）+ 面包屑 + 页面过渡动效
- **性能优化**：ECharts 按需引入 + chunk 拆分（首屏 60kB，Home 6.78kB）+ 路由懒加载
- **后端工程化**：请求日志中间件 + 滑动窗口限流 + 统一异常处理 + 优雅降级（无模型时启发式回退）

## 优势

- ✅ 0 硬件成本，纯软件实现
- ✅ 创新点碾压 90% 同赛道农业项目
- ✅ 避开烂大街的温湿度监测、单一病害识别
- ✅ AI 大模型 + 视觉双创新，国赛评审最爱
- ✅ 离线可用，农村弱网场景友好