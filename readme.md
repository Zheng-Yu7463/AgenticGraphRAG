# 🚀 Backend Quick Start

本指南用于快速启动 Agentic GraphRAG 的后端服务。

## 📋 前置要求

* **Python 3.10+**
* **Neo4j** (社区版/企业版 或 Neo4j Aura 云服务)
* **Qdrant**

---

## 🛠️ 安装与配置

### 1. 进入后端目录
```bash
cd backend
````

### 2\. 安装依赖

建议使用虚拟环境：

```bash
# 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 安装依赖包
pip install -r requirements.txt
```

### 3\. 配置环境变量

复制示例配置文件：

```bash
cp .env.example .env
```

打开 `.env` 文件，根据你的实际情况填入配置（参考下方说明）：

```ini
# --- Neo4j 数据库配置 ---
# 本地启动通常是 bolt://localhost:7687，云服务请填提供的 URI
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=你的密码

# --- Qdrant 数据库配置 ---
# 本地模式 (数据存在 ./qdrant_data)，无需额外安装 Server
QDRANT_URL=./qdrant_data
QDRANT_API_KEY=

# --- 大模型配置 (示例: SiliconFlow) ---
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_API_KEY=sk-你的Key
MODEL_FAST=Qwen/Qwen3-30B-A3B-Thinking-2507
MODEL_SMART=Qwen/Qwen3-Coder-480B-A35B-Instruct
MODEL_STRICT=Qwen/Qwen3-Coder-480B-A35B-Instruct

# --- 嵌入模型配置 ---
EMBD_BASE_URL=https://api.siliconflow.cn/v1/embeddings
EMBD_API_KEY=sk-你的Key
EMBD_MODEL_NAME=Qwen/Qwen3-Embedding-8B
```

-----

## 🗄️ 启动数据库

### 1\. Neo4j 图数据库

  * **本地安装版**:
    下载并解压 Neo4j 后，在终端运行：

    ```bash
    <NEO4J_HOME>/bin/neo4j start
    ```

    启动后请确保浏览器访问 `http://localhost:7474` 能正常登录，且密码与 `.env` 中一致。

  * **云服务**: 确保实例正在运行即可,在配置文件中修改对应的api和key。

### 2\. Qdrant 向量数据库

  * **本地模式 (推荐)**: 只要 `.env` 中配置为 `QDRANT_URL=./qdrant_data`，Python 客户端会自动管理本地文件，**无需手动启动服务**。
  * **服务端模式**: 如果使用 Docker 或云服务，请确保服务已启动并修改 `.env` 中的 URL。

-----

## ▶️ 启动服务

运行以下命令启动 FastAPI 后端：

```bash
python -m app.main
```

启动成功后，控制台将显示：

```text
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 🧪 接口测试

服务启动后，可访问自动生成的 API 文档：

  * **Swagger UI**: [http://localhost:8000/docs](https://www.google.com/search?q=http://localhost:8000/docs)
  * **监控检查**: [http://localhost:8000/api/v1/monitor/health](https://www.google.com/search?q=http://localhost:8000/api/v1/monitor/health)



## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Zheng-Yu7463/AgenticGraphRAG&type=date&legend=bottom-right)](https://www.star-history.com/#Zheng-Yu7463/AgenticGraphRAG&type=date&legend=bottom-right)

## Contributors

<a href="https://github.com/Zheng-Yu7463/AgenticGraphRAG/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Zheng-Yu7463/AgenticGraphRAG" />
</a>


![Alt](https://repobeats.axiom.co/api/embed/166d0a05e6aab6aeb61a7970e588dec6d9ffa653.svg "Repobeats analytics image")