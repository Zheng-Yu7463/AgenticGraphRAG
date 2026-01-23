# Agentic GraphRAG

FastAPI + LangGraph 的图谱增强检索生成（GraphRAG）实验项目。后端已实现 LangGraph 检索-生成-校验循环和混合检索，前端目前仍是 Vue 3 + Vite 的脚手架，需要后续对接。

## 功能亮点
- LangGraph 工作流：retrieve → generate → validate，支持检索/生成重试闭环。
- 混合检索：LLM 抽取实体 → Qdrant 相似实体匹配 → Neo4j 查询关系，拼接上下文返回。
- 对话能力：同步接口和 SSE 流式接口，持久化会话存储于 `backend/app/logs/chat_history.json`。
- 数据同步：启动时检测 Qdrant 是否为空，自动触发 Neo4j → Qdrant 全量同步；也可通过接口手动同步。
- 监控与模型信息：健康检查、模型配置查看、手动同步接口等辅助能力。

## 目录结构
- `backend/`：FastAPI + LangGraph + Neo4j + Qdrant 的核心实现。
- `frontend/`：Vue 3 + Vite + TypeScript 脚手架（尚未接入后端 API）。

## 环境要求
- Python 3.10+
- Node.js 20.19+ 或 22.12+
- Neo4j（本地/云均可）
- Qdrant（本地文件模式默认使用 `./qdrant_data`，可替换为服务端/云端）

## 全栈快速上手（根目录）
1) 准备依赖与配置：
- 按下方“后端快速上手”完成 Python 依赖与 `.env` 配置，并启动 Neo4j/Qdrant。
- 前端可选创建 `.env.local` 指定后端地址（默认 `http://localhost:8000`）。
```ini
VITE_API_BASE=http://localhost:8000
```

2) 启动后端：
```bash
cd backend
python -m app.main
```

3) 启动前端（新终端）：
```bash
cd frontend
npm install
npm run dev
```

4) 访问：
- 前端：`http://localhost:5173`
- 后端文档：`http://localhost:8000/docs`

## 后端快速上手（`backend/`）
1) 创建虚拟环境并安装依赖（示例）：
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows 使用 venv\Scripts\activate

pip install "fastapi[all]" uvicorn langchain langgraph \
  langchain-openai langchain-qdrant qdrant-client neo4j \
  pydantic-settings python-dotenv loguru
```

2) 配置环境变量（`cp .env.example .env` 后修改）：
```ini
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Qdrant（本地文件模式无需 API Key）
QDRANT_URL=./qdrant_data
QDRANT_API_KEY=
COLLECTION_NAME=test-collection  # 建议显式设置，避免使用默认拼写

# LLM（可用 OpenAI/SiliconFlow 兼容接口）
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_API_KEY=sk-xxx
MODEL_FAST=Qwen/Qwen3-30B-A3B-Thinking-2507
MODEL_SMART=Qwen/Qwen3-Coder-480B-A35B-Instruct
MODEL_STRICT=Qwen/Qwen3-Coder-480B-A35B-Instruct

# Embedding
EMBD_BASE_URL=https://api.siliconflow.cn/v1/embeddings
EMBD_API_KEY=sk-xxx
EMBD_MODEL_NAME=Qwen/Qwen3-Embedding-8B
EMBD_DIMENSIONS=4096
```

3) 启动依赖：
- 启动 Neo4j 并确认可连接 `http://localhost:7474`。
- Qdrant 使用本地 `./qdrant_data` 时无需额外进程；若改为服务端/云端，请在 `.env` 中填好地址/API Key。

4) 运行服务：
```bash
python -m app.main
```
首次启动若 Qdrant 集合为空，将自动从 Neo4j 抽取实体并向量化写入 Qdrant。

## API 快速参考
- 同步对话：`POST /api/v1/chat`
  - body: `{"query": "...", "thread_id": "可选"}`，返回 `answer/entities/graph_data/validation_status`
- 流式对话 (SSE)：`POST /api/v1/chat/stream`
  - EventSource 监听，首帧返回 `thread_id`，节点状态/校验结果实时推送，结尾 `[DONE]`
- 会话管理：
  - `POST /api/v1/chat/history` 获取指定线程历史
  - `GET /api/v1/chat/threads` 列出线程概要
  - `DELETE /api/v1/chat/history` 删除指定线程
- 监控/同步：
  - `GET /api/v1/monitor/health` 全局健康检查（Neo4j/Qdrant）
  - `GET /api/v1/monitor/models` 当前模型与参数（脱敏）
  - `POST /api/v1/monitor/sync` 手动触发 Neo4j → Qdrant 同步
- 文档：`http://localhost:8000/docs`

## 数据与日志
- Qdrant 本地数据：`backend/qdrant_data/`
- 会话持久化：`backend/app/logs/chat_history.json`
- 运行日志：`backend/app/logs/app.log`（Loguru，自动滚动）

## 前端快速上手（`frontend/`）
1) 安装依赖：
```bash
cd frontend
npm install
```

2) 可选：配置后端地址（默认 `http://localhost:8000`）：
```ini
VITE_API_BASE=http://localhost:8000
```

3) 启动开发服务器：
```bash
npm run dev
```

4) 常用脚本：
- `npm run build` 生产构建
- `npm run lint`（ESLint + Oxlint）
- `npm run test:unit`（Vitest）
- `npm run test:e2e`（Playwright，需要先 `npx playwright install`）

## Star History
[![Star History Chart](https://api.star-history.com/svg?repos=Zheng-Yu7463/AgenticGraphRAG&type=date&legend=bottom-right)](https://www.star-history.com/#Zheng-Yu7463/AgenticGraphRAG&type=date&legend=bottom-right)

## Contributors
<a href="https://github.com/Zheng-Yu7463/AgenticGraphRAG/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Zheng-Yu7463/AgenticGraphRAG" />
</a>

![Alt](https://repobeats.axiom.co/api/embed/166d0a05e6aab6aeb61a7970e588dec6d9ffa653.svg "Repobeats analytics image")
