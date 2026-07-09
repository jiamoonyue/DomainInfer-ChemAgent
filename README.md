<div align="center">

# AgentForge

**企业级 AI Agent 开发平台**

*多智能体编排 · Agentic RAG · MCP 工具协议 · 生产级可观测性*

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136+-00a393?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-purple?style=flat-square)](/)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-1.50+-orange?style=flat-square)](/)
[![React](https://img.shields.io/badge/React-19+-61dafb?style=flat-square&logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=flat-square&logo=postgresql)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-dc382d?style=flat-square&logo=redis)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ed?style=flat-square&logo=docker)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-31_passing-brightgreen?style=flat-square)](/)

[English](./README_EN.md)

</div>

---

## 概述

**AgentForge** 是一个生产就绪的企业级 AI Agent 开发平台。它提供从 ReAct 推理循环、多智能体路由，到混合检索增强生成（RAG）的完整技术栈，采用**模块化单体**架构设计，一条命令即可部署。

最初作为化学工程领域项目（ChemAgent）开发，现已泛化为**领域无关**的通用平台，适用于**智能客服、研究助手、流程自动化、知识库问答**等场景。

### 架构图

```
React 前端 (Vite + TypeScript + Tailwind)
        │ SSE 流式传输
        ▼
┌──────────────────────────────────────┐
│    FastAPI 后端 (模块化单体)            │
│                                      │
│  ┌──────┐ ┌─────────┐ ┌──────────┐  │
│  │ 认证  │ │  Agent  │ │   RAG    │  │
│  │ 模块  │ │  引擎   │ │   模块   │  │
│  └──┬───┘ └────┬────┘ └────┬─────┘  │
│     │          │            │        │
│     └──────────┼────────────┘        │
│                ▼                     │
│    ┌────────────────────────┐        │
│    │   Provider 适配层       │        │
│    │ (LiteLLM + 熔断降级)    │        │
│    └────────────────────────┘        │
└─────────────────┬───────────────────┘
                  │
       ┌──────────┴──────────┐
       │                      │
       ▼                      ▼
┌──────────────┐      ┌──────────────┐
│  PostgreSQL   │      │    Redis     │
│  (持久化存储)  │      │  (缓存/限流)  │
└──────────────┘      └──────────────┘
```

### 请求数据流

```
用户 → React UI → Nginx → FastAPI → JWT 认证 → Redis 限流
  → Agent 引擎 → 分类节点 → 路由到最佳 Agent → RAG 上下文注入
  → 思考节点 (LiteLLM) → 调用工具? → 是 → 执行工具 → 回到思考
  → 最终回答 → SSE 流式返回 → React UI
  ↓
  OpenTelemetry 追踪每一步 → Jaeger
  Prometheus 记录指标
```

---

## 核心特性

### 🤖 多智能体编排 (LangGraph)
- **ReAct 循环**：推理 → 行动循环，Agent 思考、调用工具、观察结果、最终回答
- **StateGraph 流水线**：`classify → think → [execute_tool → think → ...] → respond`
- **智能路由**：按领域自动选择 Agent（计算、安全、知识库、流程）
- **流式输出**：基于 SSE 的逐 token 实时流式传输

### 🔌 Provider 层 + 熔断降级
- **统一 API**：通过 LiteLLM 接入 100+ 大模型（`提供商/模型名` 格式）
- **熔断降级**：主模型 → 备选1 → 备选2 自动切换，故障冷却恢复
- **多 Provider**：DeepSeek、OpenAI、Anthropic、Ollama 即插即用
- **Token 记账**：按对话统计成本

### 📚 Agentic RAG（混合搜索）
- **查询重写**：LLM 改写用户查询以提升检索质量
- **混合搜索**：BGE-M3 稠密向量 + BM25 稀疏关键词 + RRF 融合排序
- **纠错检索**：相关性评分触发自动重检索
- **块生命周期**：SHA-256 内容哈希、`stable_id` 版本追踪、增量更新
- **命名空间隔离**：每个领域独立知识库（化工、法律、医疗等）

### 🔧 MCP 工具协议
- **JSON-RPC 标准**：工具发现（`tools/list`）和执行（`tools/call`）
- **10 个内置工具**：6 个领域工具（分子量计算、单位换算等）+ 4 个外部 API（PubChem、NIST、arXiv）
- **可扩展**：在 `TOOL_DEFINITIONS` 中注册新工具，零样板代码

### 🔐 企业级安全
- **JWT 双令牌**：15 分钟访问令牌 + 7 天刷新令牌
- **API Key 支持**：程序化访问的 API 密钥管理
- **RBAC 权限**：三个角色 — `admin`（管理员）、`user`（用户）、`viewer`（查看者）
- **全局认证中间件**：所有 `/api/*` 端点默认受保护
- **Redis 限流**：可配置的每用户配额（默认 20 次/分钟）

### 📊 生产级可观测性
- **OpenTelemetry + Jaeger**：Agent 每一步的分布式追踪
- **Prometheus 指标**：请求计数、延迟直方图、Token 用量
- **Jaeger UI**：端口 16686 可视化查看追踪链路

### 💻 现代化前端
- **React 19 + TypeScript + Vite + Tailwind CSS**
- **实时 SSE 流式传输**：逐 token 实时显示 Agent 回复
- **对话管理**：侧边栏历史记录，自动生成标题
- **工具调用可视化**：可展开的卡片展示工具调用详情

---

## 技术栈

| 类别 | 技术 |
|------|------|
| **后端框架** | FastAPI（异步、自动 OpenAPI、SSE 流式） |
| **Agent 框架** | LangGraph StateGraph（ReAct 循环） |
| **LLM 网关** | LiteLLM（100+ 模型统一接口） |
| **数据库** | PostgreSQL 15 + SQLAlchemy 2.0（异步） |
| **缓存/队列** | Redis 7（限流、缓存、分布式锁） |
| **向量搜索** | BGE-M3 向量 + BM25 关键词（混合搜索） |
| **认证** | JWT（访问 + 刷新令牌）、bcrypt、RBAC |
| **可观测性** | OpenTelemetry、Jaeger、Prometheus |
| **前端** | React 19、TypeScript、Vite、Tailwind CSS |
| **部署** | Docker Compose（5 个服务） |
| **测试** | pytest、pytest-asyncio、httpx |
| **数据库迁移** | Alembic |

---

## 快速开始

### 前提条件

- [Docker](https://docs.docker.com/get-docker/) 和 [Docker Compose](https://docs.docker.com/compose/install/)
- Python 3.10+（本地开发用）

### 方式一：Docker Compose（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/jiamoonyue/DomainInfer-ChemAgent.git
cd DomainInfer-ChemAgent

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env：填入 DEEPSEEK_API_KEY、SECRET_KEY 等

# 3. 一键启动所有服务
docker compose up -d

# 4. 验证部署
curl http://localhost/api/status
# {"status":"running","version":"0.1.0","database":"configured","redis":"configured",...}

# 5. 打开应用
# 前端页面：http://localhost
# API 文档：http://localhost/docs
# Jaeger UI：http://localhost:16686
```

### 方式二：本地开发

```bash
# 1. 启动基础服务（PostgreSQL + Redis + Jaeger）
docker compose up -d postgres redis jaeger

# 2. 配置 Python 环境
cd backend
pip install -e ../[dev]

# 3. 执行数据库迁移
alembic upgrade head

# 4. 启动后端
uvicorn app.main:app --reload --port 8000

# 5. 另一个终端启动前端
cd frontend
npm install
npm run dev
```

---

## 配置说明

将 `.env.example` 复制为 `.env` 并配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SERVER_HOST` | `0.0.0.0` | 服务器绑定地址 |
| `SERVER_PORT` | `8000` | 服务器端口 |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL 连接地址 |
| `REDIS_URL` | `redis://redis:6379/0` | Redis 连接地址 |
| `DEEPSEEK_API_KEY` | — | DeepSeek API 密钥 |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 模型名称 |
| `USE_API` | `true` | 启用 API 模式 |
| `SECRET_KEY` | — | JWT 签名密钥（至少 32 字符） |
| `ADMIN_EMAIL` | `admin@agentforge.local` | 自动创建的管理员邮箱 |
| `ADMIN_PASSWORD` | `admin123` | 管理员密码 |
| `RATE_LIMIT_PER_MINUTE` | `20` | 每用户每分钟请求上限 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://jaeger:4317` | OpenTelemetry 端点 |

---

## 项目结构

```
├── backend/                    # Python FastAPI 后端
│   ├── app/
│   │   ├── core/              # 配置、数据库、Redis、安全、中间件
│   │   ├── modules/
│   │   │   ├── auth/          # 用户管理、JWT、RBAC、API 密钥
│   │   │   ├── agents/        # LangGraph 引擎、ReAct 循环、多 Agent 路由
│   │   │   ├── rag/           # 混合搜索、Agentic RAG、块生命周期
│   │   │   ├── tools/         # MCP 工具注册、10 个工具、审计日志
│   │   │   ├── knowledge/     # 文档上传、命名空间管理
│   │   │   ├── conversations/ # 聊天历史、消息 CRUD
│   │   │   └── observability/ # Token 成本、用量分析
│   │   ├── providers/         # LLM 适配器（LiteLLM、OpenAI、Anthropic、Ollama、DeepSeek、熔断器）
│   │   └── mcp/               # MCP JSON-RPC 服务器
│   ├── tests/                 # 31 个测试（单元 + 集成）
│   ├── migrations/            # Alembic 数据库迁移
│   └── alembic.ini
├── frontend/                   # React + TypeScript + Vite + Tailwind
│   └── src/
│       ├── App.tsx            # 主聊天界面（SSE 流式）
│       ├── main.tsx           # 入口文件
│       └── index.css          # Tailwind 样式
├── agents/                     # Agent YAML 配置文件
├── knowledge/                  # 知识库源文件
├── prompts/                    # Jinja2 提示词模板
├── nginx/                      # Nginx 配置（SSE 代理）
├── docs/                       # 架构文档
├── docker-compose.yml          # 5 服务 Docker 编排
├── Dockerfile                  # 后端容器镜像
└── pyproject.toml              # Python 依赖和元数据
```

---

## API 概览

| 接口 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/health` | GET | 否 | 健康检查 |
| `/api/status` | GET | 否 | 服务器状态 |
| `/api/auth/register` | POST | 否 | 用户注册 |
| `/api/auth/login` | POST | 否 | 登录（返回 JWT） |
| `/api/auth/refresh` | POST | 否 | 刷新访问令牌 |
| `/api/auth/me` | GET | JWT | 当前用户信息 |
| `/api/chat` | POST | JWT | 与 Agent 对话（SSE 流） |
| `/api/agents` | GET | 否 | 列出已配置的 Agent |
| `/api/tools` | GET | 否 | 列出可用工具（MCP） |
| `/api/tools/call` | POST | 否 | 执行工具（MCP） |
| `/api/search` | POST | JWT | 混合搜索 |
| `/api/agentic-search` | POST | JWT | Agentic RAG 搜索 |
| `/api/ingest/{namespace}` | POST | JWT | 导入文档 |
| `/api/knowledge/namespaces` | GET | 否 | 列出知识库命名空间 |
| `/api/conversations` | GET | JWT | 列出对话 |
| `/api/observability/overview` | GET | JWT | 用量概览 |
| `/metrics` | GET | 否 | Prometheus 指标 |

完整交互式 API 文档请访问 `http://localhost/docs`（Swagger UI）。

---

## 测试

```bash
cd backend

# 运行全部测试
pytest tests/ -v

# 运行指定测试模块
pytest tests/test_tools.py -v    # 14 个工具测试
pytest tests/test_security.py -v # 5 个安全测试
pytest tests/test_integration.py -v # 12 个集成测试

# 带覆盖率
pip install pytest-cov
pytest tests/ --cov=app -v
```

**共 31 个测试**：19 个单元测试 + 12 个集成测试。

---

## Agent 配置

Agent 以 YAML 文件形式定义在 `agents/` 目录下：

```yaml
name: chem-calculator
display_name: 化学计算器
description: 精通化工计算的 AI 助手
type: calculation
model: deepseek/deepseek-chat
temperature: 0.3
system_prompt: |
  你是化工计算专家。
  使用工具进行精确计算，并展示计算过程。
```

内置 Agent：

| Agent | 类型 | 功能 |
|-------|------|------|
| **化学计算器** | `calculation` | 化学计量、气体定律、单位换算 |
| **安全分析师** | `safety` | 化学品安全、MSDS 解读 |
| **领域知识** | `knowledge` | RAG 增强的知识库问答 |
| **工艺工程师** | `process` | 工艺设计、设备选型 |

---

## Docker 服务

| 服务 | 端口 | 说明 |
|------|------|------|
| `nginx` | `80` | 反向代理（支持 SSE） |
| `backend` | `8000` | FastAPI 应用 |
| `postgres` | `5432` | PostgreSQL 15 数据库 |
| `redis` | `6379` | Redis 7 缓存和限流 |
| `jaeger` | `16686` | Jaeger 链路追踪 UI |

---

## 扩展指南

### 添加新工具

```python
from app.modules.tools.engine import TOOL_DEFINITIONS

def my_custom_tool(param1: str, param2: int) -> str:
    """做一些有用的事。"""
    return f"结果: {param1 * param2}"

TOOL_DEFINITIONS["my_custom_tool"] = {
    "name": "my_custom_tool",
    "description": "描述这个工具的功能",
    "input_schema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "第一个参数"},
            "param2": {"type": "integer", "description": "第二个参数"},
        },
        "required": ["param1", "param2"],
    },
    "fn": my_custom_tool,
}
```

### 添加新 Provider

继承 `BaseLLMProvider`，实现 `chat()` 和 `chat_stream()` 方法。

### 添加新 Agent

在 `agents/` 目录下创建一个 YAML 文件，路由系统会自动识别。

## 许可证

MIT

---

## 致谢

感谢 [FastAPI](https://fastapi.tiangolo.com/)、[LangGraph](https://langchain-ai.github.io/langgraph/)、[LiteLLM](https://litellm.vercel.app/) 和开源社区。

---

*AgentForge — 从原型到生产，一步一个 Agent。*
