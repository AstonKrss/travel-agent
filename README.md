# Enterprise Travel AI Agent

基于 **LangGraph** 的企业差旅智能 Agent 系统，实现 **意图识别 → 信息提取 → 政策检查(RAG) → 行程规划 → 智能推荐 → 人机协同审批 → 预订执行** 全流程自动化。

## 技术亮点

| 特性 | 实现 |
|------|------|
| **LangGraph 多节点编排** | 8个专业节点 + 条件路由 + 子图 |
| **多 LLM 智能路由** | 小模型(intent) + 大模型(reasoning) 按需分配 |
| **RAG 政策检查** | 企业差旅政策知识库检索 + 违规检测 |
| **人机协同** | 超预算自动触发审批中断 (`update_state`) |
| **状态持久化** | MemorySaver checkpointer 支持断点恢复 |
| **SSE 流式输出** | 实时节点状态 + 推荐卡片流式推送 |
| **可观测性** | 节点耗时追踪 + 错误记录 |

## 架构

```
用户消息
  │
  ▼
┌─────────────┐     小模型快速分类
│  Intent     │ ──── greeting/chat/query/book
└──────┬──────┘
       │
  ┌────┴────┐
  ▼         ▼
Chat    Extractor ──── 结构化信息提取 (LLM + Regex)
  │         │
  │         ▼
  │    Planner ────── 行程规划
  │         │
  │         ▼
  │    Policy ─────── RAG 政策检查
  │         │
  │    ┌────┴────┐
  │    ▼         ▼
  │ Approval  Recommender ── LLM 智能排序
  │    │         │
  │    └────┬────┘
  │         ▼
  │    Booker ─────── 执行预订
  │         │
  ▼         ▼
 END ←──── END
```

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env   # 填入 API Key
python main.py
```

浏览器打开 `frontend/index.html`。

## 项目结构

```
├── main.py                      # FastAPI 入口 + SSE 流式
├── backend/
│   ├── config.py               # 配置管理
│   ├── agents/
│   │   ├── graph.py            # LangGraph 主图 + 条件路由
│   │   ├── nodes/              # 8个专业节点
│   │   │   ├── intent_node.py      # 意图识别 (小模型)
│   │   │   ├── extractor_node.py   # 信息提取
│   │   │   ├── planner_node.py     # 行程规划
│   │   │   ├── policy_node.py      # 政策检查 (RAG)
│   │   │   ├── recommender_node.py # 智能推荐 + LLM排序
│   │   │   ├── approval_node.py    # 人机协同审批
│   │   │   ├── booker_node.py      # 预订执行
│   │   │   └── chat_node.py        # 通用对话
│   │   └── subgraphs/
│   │       └── booking_graph.py    # 预订子图
│   ├── llm/
│   │   └── __init__.py         # 多模型路由 (intent/reasoning/chat)
│   ├── rag/
│   │   └── __init__.py         # RAG 政策检索器
│   ├── observability/
│   │   └── __init__.py         # 节点追踪 + 性能指标
│   └── schemas/
│       ├── state.py            # 状态模型 + Reducer
│       └── events.py           # SSE 事件
├── tools/                      # 外部工具 (TMC/财务)
└── frontend/                   # 暗色主题精致UI
```

## API

| 端点 | 说明 |
|------|------|
| `POST /api/chat/stream` | SSE 流式对话 |
| `POST /api/chat` | 普通对话 |
| `POST /api/approve` | 审批处理 |
| `POST /api/book` | 预订执行 |
| `GET /api/state/{thread_id}` | 获取状态 |
| `GET /api/graph` | 图结构信息 |
