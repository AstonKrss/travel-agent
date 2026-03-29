# 🌟 Enterprise Travel AI Agent

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10+--blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.1+-FF5C8D.svg)](https://langchain.dev/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**中文** | [English](README_EN.md)

基于 LangGraph 的企业差旅智能 Agent 系统，实现差旅申请-预订-报销全流程自动化闭环。

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [架构设计](#-架构设计) • [API 文档](#-api-文档) • [配置说明](#-配置说明)

</div>

---

## ✨ 功能特性

- 🤖 **智能对话**: 基于 LLM 的自然语言交互，智能理解用户差旅需求
- 🎯 **精准推荐**: 根据出发地、目的地、日期智能推荐火车票、航班、酒店
- 💳 **公对公支付**: 企业账户直接扣款，员工无需垫付
- 🔄 **全流程闭环**: 申请 → 预订 → 消费 → 报销 → 结算全自动
- 💰 **自动财务**: 月末 TMC 自动开票，同步企业财务系统
- 💾 **持久化对话**: 支持多轮对话，thread_id 保持会话上下文
- 🔊 **语音输入**: 支持浏览器原生语音识别（中文）
- 📡 **流式输出**: 实时流式响应，用户体验更佳
- 🧠 **意图识别**: 自动识别用户意图（查询/预订/闲聊/问候）
- 📱 **智能卡片**: 推荐卡片可关闭、可滚动。

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- pip

### 1. 克隆项目

```bash
git clone https://github.com/your-repo/enterprise-travel-agent.git
cd enterprise-travel-agent
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境（可选）

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

### 4. 启动服务

```bash
python main.py
```

服务启动在 `http://localhost:8000`

### 5. 打开前端

```bash
# 方式1: 直接用浏览器打开
open frontend/index.html

# 方式2: 使用静态服务器
cd frontend && python -m http.server 8080
# 访问 http://localhost:8080
```

---

## 📖 使用示例

```
用户: 你好
助手: 你好呀！我是企业差旅智能助手，请问您需要安排出差行程吗？请告诉我出发城市、目的地、出行日期和出行人数哦～

用户: 从广州到北京，下周二，1人
助手: 为您找到了从广州到北京的出行方案。请选择以下选项：
[显示推荐卡片：高铁/航班/酒店]
```

---

## 🏗️ 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (HTML/JS)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   聊天界面   │  │  推荐卡片   │  │    语音识别 (Web API)   │  │
│  │  + 关闭按钮  │  │  (可滚动)   │  │                         │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼───────────────┼─────────────────────┼────────────────┘
          │               │                     │
          ▼               ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      /api/chat (SSE)                        ││
│  │  ┌───────────────────────────────────────────────────────┐ ││
│  │  │                   LangGraph Agent                     │ ││
│  │  │  ┌──────────┐    ┌──────────┐    ┌──────────────────┐│││
│  │  │  │  Intent  │───▶│  Agent   │───▶│ Recommendation   ││││
│  │  │  │ Classifier│    │  Node    │    │ (流式输出)        ││││
│  │  │  └──────────┘    └──────────┘    └──────────────────┘│││
│  │  └───────────────────────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Tool Layer                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ Information    │  │     TMC        │  │      OA          │  │
│  │ Extraction     │  │     API        │  │    Finance       │  │
│  │ (正则+LLM)     │  │  (公对公支付)   │  │   (报销入账)     │  │
│  └────────────────┘  └────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 技术栈 | 说明 |
|------|--------|------|
| **意图识别** | LLM | 自动判断用户意图（查询/预订/闲聊/问候） |
| **状态机** | LangGraph | 差旅对话状态机，持久化管理多轮对话 |
| **Agent** | Python | 决策中心，调用 LLM 和工具 |
| **工具层** | Pydantic + LangChain | 4 个核心工具（意图、信息抽取、推荐、TMC） |
| **后端** | FastAPI | RESTful API + SSE 流式输出 |
| **前端** | 原生 HTML/CSS/JS | 聊天界面 + 可滚动推荐卡片 |

### 工作流程

```
1. 用户发送消息 → /api/chat/stream (SSE)
2. Intent Classifier 判断意图 → greeting/chat/book/recommend
3. Agent 根据意图处理 → 调用信息抽取 Tool
4. 信息完整 → 流式调用推荐 Tool → 分段返回卡片
5. 前端渲染 → 推荐卡片可滚动、可关闭
6. 用户选择 → 点击预订 → /api/order/submit
7. 业务处理 → TMC 公对公扣款 → OA 财务入账
8. 完成闭环 → 返回确认消息
```

---

## 📂 项目结构

```
enterprise-travel-agent/
├── main.py                      # FastAPI 入口
├── requirements.txt             # Python 依赖
├── .env                        # 环境变量
│
├── backend/                    # 后端核心
│   ├── __init__.py
│   ├── config.py              # 配置管理
│   ├── llm.py                 # LLM 接口封装
│   │
│   ├── schemas/               # 数据模型
│   │   ├── __init__.py
│   │   ├── request.py         # 请求模型
│   │   ├── response.py        # 响应模型
│   │   ├── state.py           # 状态模型
│   │   └── recommendation.py  # 推荐模型
│   │
│   ├── agents/                # Agent 核心
│   │   ├── __init__.py
│   │   └── graph.py          # LangGraph 图定义
│   │
│   ├── nodes/                 # LangGraph 节点
│   │   ├── __init__.py
│   │   ├── intent_node.py    # 意图识别节点
│   │   ├── extract_node.py   # 信息提取节点
│   │   ├── recommend_node.py # 推荐节点
│   │   └── chat_node.py      # 聊天响应节点
│   │
│   └── tools/                 # 工具层
│       ├── base.py            # 工具基类
│       ├── intent_classifier.py
│       ├── information_extraction.py
│       ├── travel_recommendation.py
│       ├── tmc_api.py
│       └── oa_finance.py
│
└── frontend/                   # 前端页面
    ├── index.html              # 主页面
    ├── style.css               # 样式
    └── app.js                 # 前端逻辑
```

---

## 📡 API 文档

### 1. 流式聊天 `POST /api/chat/stream`

SSE 流式响应，支持推荐卡片分段输出

```javascript
// Request
const res = await fetch('/api/chat/stream', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    message: '北京到上海下周一',
    user_id: 'emp001',
    thread_id: 'optional-thread-id'
  })
});

// Response (SSE) - 文本消息
data: {"type": "start", "thread_id": "..."}
data: {"type": "message", "content": "正在处理..."}
data: {"type": "message", "content": "为您找到了..."}
data: {"type": "clear"}

// Response (SSE) - 流式推荐卡片
data: {"type": "recommendation_category", "category": "train", "title": "🚄 高铁/动车"}
data: {"type": "recommendation", "data": {...}}
data: {"type": "recommendation", "data": {...}}
data: {"type": "recommendation_category", "category": "flight", "title": "✈️ 航班"}
data: {"type": "recommendation", "data": {...}}
data: {"type": "recommendations_done"}
data: {"type": "done", "step": "recommended"}
```

**SSE 事件类型：**
| 类型 | 说明 |
|------|------|
| `start` | 会话开始，返回 thread_id |
| `status` | 处理状态（如"正在理解您的需求..."） |
| `message` | 助手回复文本 |
| `clear` | 清除占位消息 |
| `recommendation_category` | 推荐分类标题 |
| `recommendation` | 单个推荐卡片 |
| `recommendations_done` | 推荐展示完成 |
| `done` | 会话结束 |
| `error` | 错误信息 |

### 2. 普通聊天 `POST /api/chat`

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "北京到广州下周一", "user_id": "emp001"}'
```

### 3. 提交订单 `POST /api/order/submit`

```bash
curl -X POST http://localhost:8000/api/order/submit \
  -H "Content-Type: application/json" \
  -d '{
    "action": "book",
    "type": "train",
    "train_no": "G27",
    "departure": "北京",
    "destination": "广州",
    "date": "2026-04-01",
    "user_id": "emp001",
    "thread_id": "thread-uuid"
  }'
```

### 4. 获取状态 `GET /api/state/{thread_id}`

---

## ⚙️ 配置说明

在 `.env` 中配置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `LLM_PROVIDER` | LLM 提供商 (`openai`/`volcano`) | `openai` |
| `LLM_TEMPERATURE` | LLM 生成温度 | `0.7` |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `VOLCANO_API_KEY` | 火山引擎 API Key | - |
| `USE_MOCK` | 是否使用 Mock 模式 | `true` |

### 支持的 LLM

- ✅ **OpenAI** - GPT-4o, GPT-4o-mini, GPT-3.5
- ✅ **火山引擎** - Doubao (豆包), Qwen (通义千问)
- ✅ **其他 OpenAI 兼容 API**

---

## 🔧 开发指南

### 运行测试

```bash
# 测试 API
python -c "from main import app; from fastapi.testclient import TestClient; c=TestClient(app); print(c.post('/api/chat', json={'message':'你好','user_id':'test'}).json())"
```

### 添加新功能

1. 在 `tools/` 目录下创建新的 Tool
2. 在 `backend/graph.py` 的 `agent_node` 中添加处理逻辑
3. 前端会自动处理新的 SSE 事件类型

### 意图识别

意图分类器 `backend/intent_classifier.py` 支持以下意图：
- `greeting`: 用户问候
- `chat`: 闲聊/一般问题
- `trip_query`: 差旅查询
- `book`: 预订
- `cancel`: 取消
- `expense`: 报销

---

## 📄 License

MIT License - 见 [LICENSE](LICENSE) 文件

---

## 🤝 致谢

- [LangGraph](https://langchain.dev/langgraph/) - 状态机框架
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
- [LangChain](https://langchain.dev/) - LLM 工具链
- [火山引擎](https://www.volcengine.com/) - 大模型服务

---

<div align="center">

⭐ Star this repo if it helps!

</div>