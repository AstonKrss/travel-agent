# 企业差旅智能 Agent API 接口测试文档 (Apifox)

本文档用于 Apifox 接口测试，包含所有接口的请求路径、请求格式、示例。

---

## 基础信息

- **Base URL**: `http://localhost:8000`
- **Content-Type**: `application/json`

---

## 1. 健康检查

**接口路径**: `GET /`

**描述**: 服务健康检查

**请求示例**:
```
GET http://localhost:8000/
```

**响应示例**:
```json
{
  "message": "Enterprise Travel Agent System API"
}
```

---

## 2. 发送对话消息

**接口路径**: `POST /api/chat`

**描述**: 用户发送自然语言消息，LangGraph 状态机处理，返回响应和推荐列表。

### 请求体

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `message` | string | 是 | 用户输入的自然语言消息 |
| `user_id` | string | 是 | 用户 ID，例如 `emp001` |
| `thread_id` | string | 否 | 对话线程 ID，首次不传由后端生成 |

### 请求示例 1 - 首次对话

```json
{
  "message": "北京到广州 下周一",
  "user_id": "emp001"
}
```

### 请求示例 2 - 已有对话继续

```json
{
  "message": "帮我预订 G27 这趟车",
  "user_id": "emp001",
  "thread_id": "a1b2c3d4-5678-90ef-ghij-klmnopqrstuv"
}
```

### 响应示例

```json
{
  "messages": [
    {
      "role": "user",
      "content": "北京到广州 下周一"
    },
    {
      "role": "assistant",
      "content": "I've extracted your trip info: 北京 to 广州 on 2026-04-01. I'll now find recommendations for you."
    }
  ],
  "recommendations": [
    {
      "id": "G27",
      "type": "train",
      "name": "G27",
      "departure": "北京",
      "destination": "广州",
      "date": "2026-04-01",
      "departure_time": "09:00",
      "arrival_time": "15:45",
      "price": 862.0,
      "duration": "6h 45m",
      "available": true
    },
    {
      "id": "CA1321",
      "type": "flight",
      "name": "CA1321",
      "departure": "北京",
      "destination": "广州",
      "date": "2026-04-01",
      "departure_time": "07:30",
      "arrival_time": "10:50",
      "price": 1200.0,
      "duration": "3h 20m",
      "available": true
    }
  ],
  "thread_id": "a1b2c3d4-5678-90ef-ghij-klmnopqrstuv",
  "current_step": "recommended"
}
```

---

## 3. 提交预订订单

**接口路径**: `POST /api/order/submit`

**描述**: 用户点击推荐卡片后，调用此接口完成预订。后端调用 TMC API 公对公扣款，然后更新 LangGraph 状态。

### 请求体

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `action` | string | 是 | 固定值 `"book"` |
| `type` | string | 是 | 预订类型: `train` / `flight` / `hotel` |
| `user_id` | string | 是 | 用户 ID |
| `thread_id` | string | 是 | 对话线程 ID (从 /api/chat 返回获取) |
| `departure` | string | 否 | 出发地 (train/flight 需要) |
| `destination` | string | 否 | 目的地 (train/flight 需要) |
| `date` | string | 否 | 日期 YYYY-MM-DD (train/flight 需要) |

**根据不同类型，需要额外传对应 ID:**
- `type=train`: 需要传 `train_no`
- `type=flight`: 需要传 `flight_no`
- `type=hotel`: 需要传 `hotel_id`

### 请求示例 1 - 预订火车票

```json
{
  "action": "book",
  "type": "train",
  "train_no": "G27",
  "departure": "北京",
  "destination": "广州",
  "date": "2026-04-01",
  "user_id": "emp001",
  "thread_id": "a1b2c3d4-5678-90ef-ghij-klmnopqrstuv"
}
```

### 请求示例 2 - 预订航班

```json
{
  "action": "book",
  "type": "flight",
  "flight_no": "CA1321",
  "departure": "北京",
  "destination": "广州",
  "date": "2026-04-01",
  "user_id": "emp001",
  "thread_id": "a1b2c3d4-5678-90ef-ghij-klmnopqrstuv"
}
```

### 请求示例 3 - 预订酒店

```json
{
  "action": "book",
  "type": "hotel",
  "hotel_id": "HOTEL001",
  "user_id": "emp001",
  "thread_id": "a1b2c3d4-5678-90ef-ghij-klmnopqrstuv"
}
```

### 响应示例 (成功)

```json
{
  "success": true,
  "message": "Booking confirmed successfully. Company account has been charged ¥862.00. No employee payment needed.",
  "order_id": "ORD-AB12CD34",
  "amount_charged": 862.0,
  "final_state": {
    "ticket_booked": true,
    "hotel_booked": false,
    "current_step": "completed"
  }
}
```

### 响应示例 (失败)

```json
{
  "detail": "Missing ID for type train"
}
```

---

## 4. 获取对话状态

**接口路径**: `GET /api/state/{thread_id}`

**描述**: 获取指定对话线程的当前完整状态

**请求示例**:
```
GET http://localhost:8000/api/state/a1b2c3d4-5678-90ef-ghij-klmnopqrstuv
```

**响应示例**:
```json
{
  "user_id": "emp001",
  "thread_id": "a1b2c3d4-5678-90ef-ghij-klmnopqrstuv",
  "messages": [
    {
      "role": "user",
      "content": "北京到广州 下周一"
    },
    {
      "role": "assistant",
      "content": "I've extracted your trip info: 北京 to 广州 on 2026-04-01. I'll now find recommendations for you."
    }
  ],
  "trip": {
    "departure": "北京",
    "destination": "广州",
    "date": "2026-04-01",
    "passengers": 1,
    "trip_type": "one_way"
  },
  "recommendations": [...],
  "order": {
    "order_id": "ORD-AB12CD34",
    "status": "booked",
    "ticket_booked": true,
    "hotel_booked": false,
    "total_amount": 862.0
  },
  "current_step": "completed",
  "extracted": true,
  "need_recommendation": true
}
```

---

## Apifox 导入方式

1. 在 Apifox 中新建项目
2. 新建「自动生成」API 文档
3. 依次添加上述三个接口，复制对应的请求示例
4. 或者直接导入 OpenAPI 文档:
   - 启动服务后访问: `http://localhost:8000/openapi.json`
   - 在 Apifox 中导入 OpenAPI/Swagger 即可自动生成所有接口

---

## 测试流程 (完整走通)

**步骤 1**: 调用 `/api/chat` 发送用户请求
```json
{
  "message": "北京到上海下周一",
  "user_id": "emp001"
}
```
→ 得到 `thread_id` 和 `recommendations` 列表

**步骤 2**: 从推荐列表中选一个，记住 `id` 和 `type`

**步骤 3**: 调用 `/api/order/submit` 发送预订请求
```json
{
  "action": "book",
  "type": "train",
  "train_no": "G1",
  "departure": "北京",
  "destination": "上海",
  "date": "2026-04-01",
  "user_id": "emp001",
  "thread_id": "<从步骤1返回得到的thread_id>"
}
```

**步骤 4**: 调用 `/api/state/{thread_id}` 查看最终状态，验证 `ticket_booked` 是否为 `true`，`current_step` 是否为 `completed`

---

## Mock 模式预期结果

- 无论请求是什么，预订都会成功
- 自动生成订单号
- 金额根据类型不同: train 862, flight 1200, hotel 480
- 最终 `ticket_booked` 或 `hotel_booked` 会变为 `true`
- `current_step` 变为 `completed`

---

## 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 (缺少必填字段) |
| 500 | 后端 / TMC API 错误 |
