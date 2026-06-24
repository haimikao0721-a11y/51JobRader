# JobMatch Analyzer

基于 AI Agent 的岗位匹配分析工具。AI 自主决策，工具平级调用，一轮循环内完成搜索→分析→报告全流程。

## 快速开始

```bash
# 分析指定职位
python main.py --resume my_resume.pdf --job-url https://xxx.com/job/123

# 搜索+分析
python main.py --resume my_resume.pdf --search "Python 后端开发 上海"

# 导出报告
python main.py --resume my_resume.pdf --search "数据工程师" --output report.md
```

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         main.py (入口编排)                           │
│              参数解析 / 初始化 / 启动 Agent / 输出报告               │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     agent_loop.py (Agent 循环引擎)                   │
│              ReAct 循环: Thought → Action → Observation → ...       │
│              管理消息历史 / 工具调度 / token 计数 / 终止判断        │
│              达 max_talk 或 400K tokens → 触发 compress.py         │
└────┬──────────┬──────────┬──────────────────┬───────────────────────┘
     │          │          │                  │
     ▼          ▼          ▼                  ▼
┌─────────┐ ┌─────────┐ ┌──────────────┐ ┌──────────────────┐
│ resume  │ │compress │ │ websearch    │ │ playwright /     │
│ .py     │ │.py      │ │ .py          │ │  └─ mouse.py     │
│         │ │         │ │              │ │                  │
│简历加载  │ │对话 →   │ │联网搜索      │ │浏览器自动化       │
│→ 解析    │ │MD 摘要  │ │(公司背景/    │ │(登录 + 采集 +    │
│→ 文本化  │ │(格式待  │ │ 员工评价)    │ │ 鼠标模拟)        │
│→ 一次    │ │ 使用中  │ │              │ │                  │
│  注入    │ │ 确定)   │ │              │ │                  │
└─────────┘ └─────────┘ └──────────────┘ └──────────────────┘
     │          │
     │          └── 下次启动 → 注入上一轮 MD 继续对话
     │
     └── 简历参考文档 → system prompt ⚡ 一次性注入，持续生效
```

---

## 模块职责

### `main.py` — 入口编排

```
职责:
  - 解析命令行参数 (--resume, --search, --job-url, --output)
  - 调用 resume.py 加载简历
  - 初始化 agent_loop 并启动 ReAct 循环
  - 接收最终报告并输出到文件/终端

边界:
  - 不参与任何分析逻辑
  - 不持有对话状态
```

### `agent_loop.py` — Agent 循环引擎

```
职责:
  - 构建 system prompt（拼接简历参考文档 + 工具定义 + 行为约束）
  - 驱动 ReAct 循环: AI 思考 → 调用工具 → 返回结果 → 继续思考
  - 维护完整的消息历史列表
  - 工具调度: 根据 AI 返回的 tool_use 调用对应的 tools/ 模块
  - Token 监控: 当前轮次计数 / 累计 token 估算
  - 终止条件判断:
      · AI 主动输出最终报告 → 结束
      · 达 max_talk 轮 → 触发 compress → 注入 MD 继续
      · 达 400K tokens → 触发 compress → 注入 MD 继续

边界:
  - 不直接操作浏览器、文件、网络
  - 不执行任何分析计算（分析完全由 AI 完成）
```

### `resume.py` — 简历加载器

```
职责:
  - 读取简历文件（.txt / .md / .pdf）
  - 解析为结构化的纯文本（技能 / 经验 / 教育 / 项目）
  - 返回一份"简历参考文档"字符串

工作方式（类似 CLAUDE.md）:
  - main.py 启动时调用一次
  - 产出注入到 system prompt 底部，整轮对话持续生效
  - compress 压缩时保留简历部分，仅压缩对话内容

边界:
  - 不参与任何匹配分析
  - 不维护状态（纯函数，输入文件→输出文本）
```

### `compress.py` — 上下文压缩策略

```
职责:
  - 将当前对话历史压缩为一份精简 MD 摘要
  - 保留: 分析结论 / 已找到的职位 / 匹配判断 / 待办事项
  - 省略: 冗余的来回对话 / 原始工具返回细节
  - 输出格式: 先用基础 MD 结构，待真实使用后迭代优化

触发条件:
  · 累计达 400K tokens（估算）
  · 或 agent_loop 轮数达 max_talk 上限
  · 或 AI 本轮处理完毕准备归档时

压缩后行为:
  - 本轮对话历史 → 压缩为 MD 文档
  - 下次启动 agent_loop 时: 注入上一轮 MD + 用户新输入
  - 简历参考文档始终保留，不被压缩掉

边界:
  - 不做匹配分析（那是 AI 的事）
  - 不写文件（返回字符串，由 agent_loop 或 main 决定存/传）
```

### 工具集 `tools/`

| 模块 | 文件 | 职责 |
|------|------|------|
| 浏览器自动化 | `playwright/` | 采集职位 JD、要求、薪资等详情数据 |
| 联网搜索 | `websearch.py` | 查询公司背景、员工评价、行业口碑 |
| 鼠标模拟 | `playwright/mouse.py` | 浏览器内部的人性化操作（随机轨迹 / 延时 / 防检测） |

**工具设计原则:**
- 所有工具**平级**，AI 自主决定调用顺序
- 不存在预设的降级链路或分支流程
- 每个工具对外暴露 1-2 个纯函数
- `tools/__init__.py` 统一注册，agent_loop 按名称调度
- 新工具只需加文件 → 注册 → agent_loop 自动发现（无需改循环逻辑）

### `tools/__init__.py` — 工具注册中心

```
职责:
  - 统一导入所有工具函数
  - 维护 TOOL_REGISTRY 字典（name → function）
  - 提供 list_tools() 返回工具元信息，供 AI 生成 tool_use
```

---

## 数据流

```
用户输入 (CLI 参数)
      │
      ▼
main.py
  ├── resume.py ───────→ "简历参考文档"
  └── agent_loop.py ───→ 构建 system prompt
                              │
                    ┌─────────┴──────────────┐
                    │  ReAct 循环开始          │
                    │                        │
                    │  AI 自主决策:           │
                    │  ① playwright → 采集   │
                    │     JD / 要求 / 薪资    │
                    │  ② websearch → 查询    │
                    │     公司背景 / 评价     │
                    │  ③ 结合 简历+用户想法   │
                    │     +①② 做匹配分析     │
                    │  ④ 输出分析报告         │
                    │                        │
                    │  监控条件:              │
                    │  达 400K tokens ─┐      │
                    │  达 max_talk    ─┤      │
                    │  AI 主动结束    ─┤      │
                    │                  │      │
                    └──────────────────│──────┘
                                       ▼
                               compress.py
                          对话 → MD 摘要文档
                                       │
                         下次启动 → 注入 MD 继续
```

> 所有步骤在**一轮 Agent 循环**内完成。AI 根据当前对话状态自主决定下一步调什么工具、何时结束。不存在预设的降级链路。

---

## 关键设计原则

### 🔌 插件化工具
- `tools/` 每个文件是一个独立工具，agent_loop 无感调度
- 新增工具只需加文件 → `__init__.py` 注册，不改循环逻辑

### 🧠 简历即上下文基准
- 简历只加载一次，转为"简历参考文档"注入 system prompt
- 后续所有分析基于这个固定基准
- compress 压缩时保留简历部分，不压缩

### 🎯 单轮闭环
- 所有操作在同一轮 Agent 循环内完成
- 不存在预设降级链路
- AI 根据上下文实时决策下一步

### 📦 Checkpoint 压缩
- 达 400K tokens 或 max_talk 上限 → 压缩为 MD 摘要
- 下次启动注入 MD 继续对话
- 压缩格式先用基础版，边用边迭代优化

### 🧩 关注点分离

```
main.py        → "调"  入口编排
agent_loop.py  → "控"  循环控制 + 工具调度
resume.py      → "读"  简历 → 文本
compress.py    → "缩"  Token 优化 + 对话存档
tools/         → "采"  搜索 / 采集 / 辅助
AI 模型         → "算"  匹配分析 + 报告生成
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.11+ |
| AI SDK | Anthropic SDK / OpenAI SDK |
| 浏览器自动化 | Playwright + mouse.py (人性化操作) |
| 搜索 | DuckDuckGo / Bing API |
| PDF 解析 | PyMuPDF / pdfplumber |
| CLI | argparse + rich |

---

## 目录结构

```
job-match-analyzer/
├── tools/
│   ├── __init__.py         # 工具注册中心
│   ├── websearch.py        # 联网搜索
│   └── playwright/         # 浏览器自动化（后续可能演化为包）
│       ├── __init__.py
│       ├── browser.py      # 浏览器控制
│       └── mouse.py        # 人性化鼠标/键盘模拟
├── resume.py               # 简历加载 + 解析（一次性注入）
├── compress.py             # 上下文压缩 → MD 摘要
├── agent_loop.py           # ReAct 循环引擎
├── main.py                 # 入口 + 编排
└── README.md               # 本文件（项目说明 + 架构文档）
```
