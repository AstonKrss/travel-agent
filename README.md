# 企业差旅智能 Agent 系统

基于 LangGraph 的企业差旅智能 Agent 系统，实现差旅申请-预订-报销全流程自动化闭环。

## 架构 Overview

![架构](https://i.imgur.com/placeholder.png)

### 核心组件

| 组件 | 技术栈 | 说明 |
|------|--------|------|
| 状态机 | LangGraph | 差旅对话状态机，持久化管理多轮对话 |
| Agent 节点 | Python | 决策与执行中心 |
| 工具层 | Pydantic + LangChain | 4 个核心工具（见下文） |
| 后端 | FastAPI | RESTful API 服务 |
| 前端 | 原生 HTML/CSS/JS | 简洁聊天界面 |

## 功能特性

- ✅ **智能交互**：支持自然语言对话，员工可以像聊天一样提交差旅申请
- ✅ **智能推荐**：根据出发地、目的地、日期推荐火车票、航班、酒店
- ✅ **公对公直接扣款**：员工无需垫付，直接从公司预存账户扣款
- ✅ **全流程闭环**：申请 → 消费 → 报销 → 结算自动化
- ✅ **自动财务入账**：月末 TMC 自动开票，同步财务系统
- ✅ **多轮对话持久化**：通过 `thread_id` 保存对话状态

## 目录结构

```
.
├── README.md
├── requirements.txt          # Python 依赖
├── main.py                   # FastAPI 入口
├── backend/
│   ├── state.py              # Pydantic 全局状态定义
│   └── graph.py              # LangGraph 状态机构建
├── tools/
│   ├── information_extraction.py  # 1. 信息抽取 Tool
│   ├── travel_recommendation.py  # 2. 机酒推荐 Tool
│   ├── tmc_api.py                # 3. TMC API（模拟公对公扣款）
│   └── oa_finance.py             # 4. OA/财务系统接口
└── frontend/
    ├── index.html            # 前端页面
    ├── style.css             # 样式
    └── app.js                # 前端逻辑
```

## 状态定义 (Pydantic v2)

`TravelState` 包含以下核心字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `user_id` | `str` | 用户 ID |
| `thread_id` | `str` | 对话线程 ID |
| `messages` | `List[Dict]` | 对话消息列表 |
| `trip` | `TripInfo` | 出行信息（出发地、目的地、日期、人数、偏好） |
| `recommendations` | `List[RecommendationItem]` | 推荐列表 |
| `order` | `OrderInfo` | 订单信息 |
| `current_step` | `str` | 当前流程步骤 |
| `extracted` | `bool` | 是否已抽取信息 |
| `need_recommendation` | `bool` | 是否需要推荐 |

`OrderInfo` 包含：
- `order_id`: 订单 ID
- `status`: 订单状态 (pending/booked/completed/cancelled)
- `ticket_booked`: 车票/机票是否预订
- `hotel_booked`: 酒店是否预订
- `total_amount`: 总金额

## 四个核心工具

### 1. 信息抽取 (InformationExtractionTool)
从用户自然语言中提取：
- 出发地
- 目的地
- 出行日期
- 人数
- 识别是否有完整出行请求

### 2. 商旅 TMC API (TMCApiTool)
Mock 实现：
- 支持公对公下单扣款
- 直接从公司企业预存账户扣款
- 员工无需支付

### 3. 机酒推荐算法 (TravelRecommendationTool)
Mock 实现：
- 根据出发地/目的地/时间推荐
- 返回高铁、航班、酒店三种类型
- 包含价格、时间、舱位/房型信息

### 4. OA/财务系统接口 (OAFinanceTool)
Mock 实现：
- 更新订单状态
- 创建报销单
- 自动入账对账

## API 接口

### POST `/api/chat`
用户发送消息入口

**Request:**
```json
{
  "message": "北京到广州 下周一",
  "user_id": "emp001",
  "thread_id": "optional-existing-thread-id"
}
```

**Response:**
```json
{
  "messages": [
    {"role": "user", "content": "北京到广州 下周一"},
    {"role": "assistant", "content": "I've extracted your trip info... I'll now find recommendations for you."}
  ],
  "recommendations": [...],
  "thread_id": "uuid",
  "current_step": "recommended"
}
```

### POST `/api/order/submit`
用户点击推荐卡片后预订入口

**Request:**
```json
{
  "action": "book",
  "type": "train",
  "train_no": "G27",
  "departure": "北京",
  "destination": "广州",
  "date": "2026-04-01",
  "user_id": "emp001",
  "thread_id": "thread-uuid"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Booking confirmed successfully. Company account has been charged...",
  "order_id": "ORD-ABC12345",
  "amount_charged": 862.0,
  "final_state": {
    "ticket_booked": true,
    "hotel_booked": false,
    "current_step": "completed"
  }
}
```

### GET `/api/state/{thread_id}`
获取指定线程当前状态

## 工作流程

1. **用户输入** → 前端携带 `user_id` 发送消息到 `/api/chat`
2. **LangGraph 状态机** → Agent 第一步调用「信息抽取」Tool
3. **信息抽取完成** → 如果信息完整，调用「机酒推荐」Tool
4. **返回推荐** → 前端将推荐渲染为可点击卡片
5. **用户选择** → 点击预订按钮，前端发送精准 JSON 到 `/api/order/submit`
6. **业务处理** → 后端走传统安全逻辑：权限校验 → TMC 接口下单 → 公司账户扣款
7. **更新状态** → 下单成功后更新 LangGraph State，将 `ticket_booked` 设为 `True`，触发状态机继续
8. **完成闭环** → Agent 调用 OA/财务接口更新，自动生成报销单

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动服务
```bash
python main.py
```

服务启动在 `http://localhost:8000`

### 3. 打开前端
直接用浏览器打开 `frontend/index.html`，或者用静态服务器：

```bash
cd frontend
python -m http.server 8080
```

然后访问 `http://localhost:8080`

## 技术栈版本

- Python 3.10+
- FastAPI >= 0.100
- LangGraph >= 0.1
- Pydantic >= 2.0
- LangChain >= 0.1

## 配置

复制 `.env.example` 为 `.env` 并填写你的配置：

```bash
cp .env.example .env
```

### 配置项说明

| 配置项 | 说明 | 是否必填 |
|--------|------|----------|
| `LLM_PROVIDER` | LLM 提供商: `openai` 或 `volcano` (火山引擎/字节跳动通义千问/Qwen) | 否 (默认 `openai`) |
| `LLM_TEMPERATURE` | LLM 生成温度 | 否 (默认 `0.7`) |
| **OpenAI** | | |
| `OPENAI_API_KEY` | OpenAI API Key | 否 |
| `OPENAI_BASE_URL` | OpenAI API Base URL | 否 |
| `OPENAI_MODEL` | 模型名称 (e.g. `gpt-4o-mini`) | 否 |
| **Volcano Engine (火山引擎)** | | |
| `VOLCANO_API_KEY` | 火山引擎 API Key | 否 |
| `VOLCANO_BASE_URL` | 火山引擎 API Base URL | 否 (默认 `https://ark.cn-beijing.volces.com/api/v3`) |
| `VOLCANO_MODEL` | 模型 ID (e.g. `qwen3-72b-instruct`, `doubao-4`) | 否 |
| **ASR 语音识别** | | |
| `DASHSCOPE_API_KEY` | 阿里云语音识别 ASR API Key | 否 |
| `IFYTEK_APPID` / `IFYTEK_API_KEY` / `IFYTEK_API_SECRET` | 科大讯飞语音识别配置 | 否 |
| **TMC 商旅** | | |
| `TMC_API_BASE_URL` / `TMC_API_KEY` / `TMC_COMPANY_ACCOUNT_ID` | 商旅 TMC 服务商 API 配置 | 否 (Mock 默认运行) |
| **OA/财务** | | |
| `OA_API_BASE_URL` / `OA_API_KEY` | 企业 OA/财务系统 API 配置 | 否 (Mock 默认运行) |
| `USE_MOCK` | 是否使用 Mock 实现，默认 `true` | 否 |

### 支持的 LLM 提供商

✅ **OpenAI** - GPT-3.5, GPT-4o, etc.  
✅ **Volcano Engine (火山引擎)** - 通义千问 (Qwen), Doubao (豆包)  
✅ Any other OpenAI-compatible API endpoints  

只需在 `.env` 中设置 `LLM_PROVIDER=volcano` 并填入你的火山引擎 API 信息即可使用通义千问模型。

设置 `USE_MOCK=false` 并配置 API 信息后，系统会自动调用真实 API。保持默认配置即可零成本本地运行体验流程。

## 语音识别支持

前端已经内置浏览器原生 Web Speech API 语音识别，不需要配置后端 API 即可使用。如果需要更好的中文识别，可以配置阿里云或科大讯飞云端 ASR。

## License

MIT
