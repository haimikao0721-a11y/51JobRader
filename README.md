# JobRadar

轻量级 AI Agent 运行时。以 Tool 为中心，将模型（Model）、工具（Tool）和业务策略（Strategy）三层解耦，各层可自由替换、支持私有化部署。

当前工具集以 Playwright 浏览器自动化为主，覆盖职位采集、网页搜索、简历解析等场景。

开源协议：Apache 2.0，可自由商用、修改和分发。

## 架构设计

### Agent Runtime 分层

```
+------------------+     +------------------+
|    模型层 (Model)  |     |  策略层 (Strategy) |
|------------------|     |------------------|
| ai_config.py     |     | ai_prompt.py     |
| 可换 OpenAI/Claude |     | 系统行为定义      |
| /Groq/通义千问...  |     | 不绑定代码        |
+--------+---------+     +--------+---------+
         |                       |
         v                       v
+------------------+     +------------------+
|   运行时 (Runtime) | <-- |   记忆 (Memory)   |
|------------------|     |------------------|
| agent_loop.py    |     | compress.py      |
| 主循环 + 错误恢复:  |     | 上下文压缩        |
| 输入→模型→工具→输出 |     | 策略可替换        |
| 异常 catch→喂回模型 |     |                  |
+--------+---------+     +------------------+
         |
         v
+------------------+
|   工具层 (Tool)    |
|------------------|
| ai_tools.py      | @register_tool 注册表
| tools/            |
|   websearch.py   | Bing 搜索
|   playwright/     | 浏览器自动化
|   resume.py      | 简历解析
+------------------+
```

| 层 | 职责 | 可替换性 |
|----|------|---------|
| **Runtime** | 循环调度：收输入 -> 调模型 -> 执行工具 -> 回传结果 | 与模型和工具完全解耦 |
| **Model** | LLM API 客户端，当前 DeepSeek | 任意 OpenAI 兼容 API，改 `base_url` + `api_key` 即可 |
| **Tool** | 装饰器注册（`@register_tool`），按名调度，工具各自独立 | 新增工具加文件 + 一行装饰器，零侵入 Runtime |
| **Strategy** | System prompt 定义 Agent 行为边界 | 纯文本替换，不涉及代码改动 |
| **Memory** | 上下文压缩，超阈值自动生成摘要续传 | 压缩算法/阈值/保留轮数均可调 |

> 这种分层和当前主流的 AI Coding Agent 架构一致 — 模型、工具、策略彼此独立，可拔插、可私有化。

### 调用流程

```
用户输入
  |
  v
agent_loop.py (Runtime)
  |
  +--> ai_config.py (Model)  --> DeepSeek / OpenAI / Claude API
  |
  +--> ai_prompt.py (Strategy) --> System Prompt
  |
  +--> ai_tools.py (Tool)
  |       |
  |       +--> tools/playwright/browser.py  (浏览器自动化)
  |       +--> tools/websearch.py           (搜索引擎)
  |       +--> resume.py                    (简历解析)
  |
  +--> compress.py (Memory)  --> 超阈值自动压缩
  |
  v
输出结果
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt
playwright install chromium

# 2. 配置环境变量（.env 文件）
DEEPSEEK_API_KEY=your_key_here

# 3. 启动交互式采集助手（默认入口）
python main.py

# 带简历启动（简历内容会自动注入上下文）
python main.py --resume "D:/简历.pdf"

# 4. 直接搜索职位（跳过 AI 对话）
python main.py search "python开发" --city 深圳,上海

# 5. 直接 Bing 搜索（--count 可选，默认 5）
python main.py web "米哈游 公司背景" --count 10

# 6. 解析简历
python main.py resume "xxx.pdf"

# 7. 或单独测试底层模块
python tools/websearch.py "搜索关键词"
python tools/playwright/browser.py "python开发" 深圳,上海
```

## 模块结构

```
main.py                     # CLI 统一入口
resume.py                   # 文档解析（.pdf / .txt / .md），独立工具

agent/                      # Agent Runtime 层
  agent_loop.py             # Runtime 主循环：输入 -> 模型 -> 工具 -> 输出 + 错误恢复
  ai_config.py              # 模型客户端初始化（DeepSeek 默认，可换）
  ai_prompt.py              # System prompt（业务策略，纯文本替换）
  ai_tools.py               # 工具注册表（@register_tool 装饰器 + get_tools + run_tool）

tools/                      # 工具层（各自独立，可拔插）
  websearch.py              # 浏览器搜索引擎（当前 Bing）
  compress.py               # 上下文压缩引擎

  playwright/               # Playwright 自动化工具
    browser.py              # 网页采集通用逻辑：打开 -> 操作 -> 抓取
    mouse.py                # 鼠标/键盘模拟（贝塞尔曲线）
```

> 当前工具集以职位采集为例演示完整链路，任意工具均可替换为其他业务场景的实现。

## 注意事项

- **浏览器环境**：Playwright 首次使用需 `playwright install chromium`
- **反爬检测**：工具已内置 UA 伪装和等待策略，可按需追加代理池或指纹伪装
- **Cookie 登录**：网页采集工具依赖 `cookies.json`，首次使用需手动登录一次生成
- **PDF 解析**：依赖 PyMuPDF，仅支持 `.pdf`，`.docx` 暂不支持
- **模型兼容**：当前默认 DeepSeek，改 `.env` 中的 `base_url` 和 `api_key` 可切到任何 OpenAI 兼容 API

## 扩展性

### 模型层替换

| 当前 | 可换 | 改动 |
|------|-----|------|
| DeepSeek API | OpenAI / Claude / Groq / 通义千问 / 本地模型（Ollama） | 改 `.env` 中的 `base_url` + `api_key`，零代码 |

### 工具层替换

| 当前工具 | 业务场景 | 可替换为 |
|---------|---------|---------|
| `browser.py` | 网页采集 | 任意平台数据抓取（电商、新闻、报表），只需保持函数签名 |
| `websearch.py` | 搜索引擎 | Google / 百度 / Sogou / SearXNG，只需保持入参返回格式 |
| `resume.py` | 文档解析 | 任意文档类型：合同、发票、报告，换解析库即可 |
| `mouse.py` | 浏览器自动化 | Selenium / pyppeteer / DrissionPage |

### 新增工具

只需一步，零侵入：

```python
# 在任意模块（如 tools/my_search.py）中
from agent.ai_tools import register_tool

@register_tool(
    name="my_search",
    description="搜索 XX 信息，返回 ...",
    parameters={
        "type": "object",
        "properties": {"q": {"type": "string", "description": "搜索词"}},
        "required": ["q"],
    },
)
def _handle(q: str):
    return search(q)
```

确保该模块在 agent_loop 启动前被 import，工具即自动注册到 `get_tools()` 列表中。无需改 `ai_tools.py` 或 `agent_loop.py` 一行代码。

### 策略层替换

`ai_prompt.py` 中 `SYSTEM_PROMPT` 为纯字符串，直接替换即可改变 Agent 行为。不影响 Runtime 和工具逻辑。

### 优化方向

- **多工具并行** — `asyncio.gather` 并行调用独立工具，减少轮次等待
- **记忆持久化** — 会话存储到 SQLite / 向量库，跨 session 保留上下文
- **日志系统** — 接入 `loguru` 或 `logging`，替代 `print`
- **结果输出** — 支持 JSON / Markdown / Excel 格式化导出
- **模型适配层** — 抽象 ModelAdapter，支持 Claude / Gemini / Ollama 等非 OpenAI 协议

## 上下文压缩（tools/compress.py）

当对话历史接近 token 上限时，自动将历史记录压缩为结构化 MD 摘要，注入到 system 和 user 之间作为上下文，避免长对话超出模型限制。

### 可调参数

| 参数 | 位置 | 默认值 | 说明 |
|------|------|--------|------|
| `--max-context` | 启动参数 | 256000 | 模型最大上下文 token 数，压缩阈值自动设为 70%（如 256K → 180K 触发） |
| `max_tokens` | `compress_messages()` 参数 | 2000 | 压缩后 MD 摘要的 token 上限 |
| `keep_last` | `compress_messages()` 参数 | 2 | 保留最近 N 轮完整对话不压缩 |

### 压缩范围

| 内容 | 压缩策略 | 是否压缩 |
|------|---------|---------|
| **System Prompt** | 始终保持不变 |  不压缩 |
| **用户输入** | 截取前 200 字 → `> **用户**: ...` |  压缩 |
| **AI 文本回复** | 截取前 300 字 → `> **AI**: ...` |  压缩 |
| **AI 工具调用** | 只保留工具名和参数 → `> **AI 调用了 collect_jobs** — 参数: {...}` |  压缩 |
| **工具返回结果** | 截取前 200 字 → `> **工具返回**: ...` |  压缩 |
| **最近 N 轮对话** | 保持完整，不做任何处理 |  不压缩 |

> 最近 N 轮默认 `keep_last=2`，即保留最近 2 轮用户 + AI 的完整对话。

### 可调策略

在 `tools/compress.py` 的 `_to_md()` 函数中可自定义：

| 策略 | 当前行为 | 可改为 |
|------|---------|--------|
| **摘要截断** | 用户输入保留前 200 字，AI 回复保留前 300 字 | 改为全文保留、或仅提取关键词、或按段落截取 |
| **工具结果处理** | 工具返回数据截取前 200 字 | 改为只保留工具名+关键字段，或丢弃工具返回只保留结论 |
| **保留轮数** | 保留最近 2 轮完整对话（`keep_last=2`） | 改为 3-5 轮，或按 token 数动态保留 |
| **压缩格式** | 结构化 MD（`> **用户**: ...` 格式） | 改为纯文本、JSON、或表格 |
| **触发时机** | 每次工具调用和 AI 回复后检查 | 改为仅工具调用后、或仅用户输入后、或固定间隔 |

### 修改示例

通过启动参数调整：

```bash
# DeepSeek 默认 256K，什么也不用改
python main.py

# 模型支持 1M 上下文（如 Claude），在 700K token 时触发压缩
python main.py --max-context 1000000

# 更激进，400K 就触发压缩
python main.py --max-context 400000
```

通过代码传参（`tools/compress.py`）：

```python
# 更激进：阈值设低、摘要更短、只保留 1 轮
messages, report = check_and_compress(messages, warn_threshold=150_000, max_tokens=1000)

# 更保守：保留 3 轮完整对话
messages, report = check_and_compress(messages, warn_threshold=200_000, keep_last=3)
```

### 参数控制方式一览

| 参数 | 控制方式 | 位置 |
|------|---------|------|
| `--resume` | 指令 | `main.py` / `agent_loop.py` 启动参数 |
| `--max-context` | 指令 | `main.py` → 透传 `agent_loop.py`，自动算 `warn_threshold` |
| `--city` | 指令 | `main.py search` 子命令 |
| `--count` | 指令 | `main.py web` 子命令 |
| `keep_last`（保留轮数） | 硬编码 | `compress.py` → `compress_messages(keep_last=2)` |
| `max_tokens`（摘要上限） | 硬编码 | `compress.py` → `compress_messages(max_tokens=2000)` |
| `_to_md()` 截断策略 | 硬编码 | `compress.py` → 用户前 200 字 / AI 前 300 字 / 工具前 200 字 |
| `check_and_compress` 触发时机 | 硬编码 | `agent_loop.py` → 工具调用后 + AI 回复后各检查一次 |

> `keep_last`、`max_tokens`、截断策略、触发时机如需调整，目前需要直接修改 `compress.py` 或 `agent_loop.py` 源码。

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.13+ | |
| 浏览器自动化 | Playwright 1.60+ | 模拟人工操作，支持 headless / headful |
| 搜索引擎 | Bing (Playwright headless) | 网页内容提取 + 反爬 |
| PDF 解析 | PyMuPDF | |
| Token 计算 | tiktoken (cl100k_base) | 上下文压缩用 |
| 依赖管理 | pip + requirements.txt | 无框架依赖，纯函数调用 |

> 当前接入 DeepSeek API，改配置可切任意 OpenAI 兼容模型。架构不依赖任何 Agent 框架（LangChain / CrewAI 等），所有逻辑为原生 Python 实现。
