# JobRadar

基于 AI Agent 的职位采集分析工具。AI 自主决策，一轮循环内完成搜索、采集、分析全流程。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt
playwright install chromium

# 2. 配置环境变量（.env）
# DEEPSEEK_API_KEY=your_key_here

# 3. 启动交互式采集助手
python agent/agent_loop.py

# 4. 或直接测试各模块
python tools/playwright/browser.py "python开发" 深圳,上海
python tools/websearch.py "关键词"
```

## 系统架构

```
┌───────────────────────────────────────────────────────────┐
│                   agent/agent_loop.py                     │
│               AI 对话循环 + 工具调度引擎                     │
│     接收用户输入 → 调用 AI → 执行工具 → 返回结果 → 输出      │
└──────┬──────────────────────────────────┬─────────────────┘
       │                                  │
       ▼                                  ▼
┌──────────────┐                  ┌──────────────────┐
│ ai_config.py │                  │   ai_tools.py    │
│  DeepSeek    │                  │  工具定义 + 调度   │
│  客户端配置   │                  │  run_tool()       │
└──────────────┘                  └────────┬─────────┘
       │                                   │
       ▼                                   ▼
┌───────────────────────────────────────────────────────────┐
│                     tools/ 工具层                          │
│                                                           │
│  ┌─────────────────────┐    ┌─────────────────────────┐   │
│  │ playwright/browser  │    │    websearch.py         │   │
│  │  .py                │    │    Bing 搜索             │   │
│  │  51job 采集         │    │    (公司背景/口碑查询)    │   │
│  │  (登录/搜索/城市筛选 │    │                         │   │
│  │   /JD抓取)          │    │                         │   │
│  └─────────┬───────────┘    └─────────────────────────┘   │
│            │                                               │
│  ┌─────────▼───────────┐                                   │
│  │ playwright/mouse.py │                                   │
│  │ 人性化鼠标/键盘模拟  │                                   │
│  └─────────────────────┘                                   │
└───────────────────────────────────────────────────────────┘
```

## 系统流程

```
用户输入需求（如"找深圳的 Python 工作"）
       │
       ▼
agent_loop.py 启动 AI 对话循环
       │
       ▼
AI 理解用户意图，决定调用 collect_jobs
       │
       ▼
browser.py 执行：
  1. 打开 51job，注入 cookie 登录
  2. 输入关键词搜索
  3. 点击"其他城市"展开城市弹窗
  4. 清空默认已选 → 选择目标城市 → 确定
  5. 获取职位列表（title/salary/company/location/tags）
  6. 逐个进入详情页抓取 JD
       │
       ▼
返回结果给 AI → AI 分析整理 → 输出给用户
       │
       ▼
（可选）AI 再调 websearch.py 查询公司背景
       │
       ▼
最终输出完整分析报告
```

## 模块完成情况

| 模块 | 状态 | 职责 |
|------|------|------|
| `agent/ai_config.py` | ✅ 完成 | DeepSeek 客户端初始化、环境变量加载 |
| `agent/ai_prompt.py` | ✅ 完成 | 系统提示词定义 |
| `agent/ai_tools.py` | ✅ 完成 | 工具 schema 定义 + run_tool 调度函数 |
| `agent/agent_loop.py` | ✅ 完成 | Agent 对话循环、流式输出、工具调用编排 |
| `tools/playwright/browser.py` | ✅ 完成 | 51job 职位采集：登录、搜索、城市弹窗筛选、JD 抓取、反爬重试 |
| `tools/playwright/mouse.py` | ✅ 完成 | 贝塞尔曲线鼠标模拟、中文输入 |
| `tools/websearch.py` | ✅ 完成 | Bing 搜索，Playwright headless 采集 |
| `resume.py` | ⬜️ 未开始 | 简历文件加载解析（占位） |
| `main.py` | ⬜️ 未开始 | CLI 入口编排（占位） |

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.13+ |
| AI | DeepSeek API (deepseek-v4-pro) |
| 浏览器自动化 | Playwright 1.60+ |
| 搜索 | Bing (Playwright headless) |
| 依赖管理 | pip + requirements.txt |

## .gitignore 已忽略内容

`.env` / `cookies.json` / `CLAUDE.md` / `.claude/` / `.venv/`
