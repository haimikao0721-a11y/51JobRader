# JobRadar

基于 AI Agent 的职位采集分析工具。AI 自主决策，一轮循环内完成搜索、采集、分析全流程。

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

# 5. 直接 Bing 搜索
python main.py web "米哈游 公司背景"

# 6. 解析简历
python main.py resume "xxx.pdf"

# 7. 或单独测试底层模块
python tools/websearch.py "搜索关键词"
python tools/playwright/browser.py "python开发" 深圳,上海
```

## 模块结构

```
main.py                     # CLI 统一入口，调度各模块

agent/                      # AI 驱动层
  agent_loop.py             # 主循环：接收用户输入 → 调 AI → 执行工具 → 输出结果
  ai_config.py              # DeepSeek 客户端初始化，被 agent_loop.py 引用
  ai_prompt.py              # System prompt 定义，被 agent_loop.py 引用
  ai_tools.py               # 工具注册 + run_tool 调度，被 agent_loop.py 引用

tools/                      # 工具层，被 ai_tools.py 按需调用
  websearch.py              # Bing 搜索：搜公司背景/口碑，返回标题 + 摘要 + 正文
  resume.py                 # 简历解析：读取 .pdf / .txt / .md，返回纯文本

  playwright/
    browser.py              # 51job 采集：登录 → 搜索 → 城市筛选 → 获取职位列表 → 抓取 JD
    mouse.py                # 鼠标/键盘模拟（贝塞尔曲线），被 browser.py 引用
```

### 调用关系

```
用户输入 → agent_loop.py
              ├── ai_config.py  → DeepSeek API 客户端
              ├── ai_prompt.py  → system prompt
              └── ai_tools.py   ──→ tools/websearch.py    (Bing 搜索)
                                  ──→ tools/playwright/browser.py (51job 采集)
                                  ──→ tools/resume.py      (简历加载)
```

**流程说明：**
1. `agent_loop.py` 启动后等待用户输入
2. AI 理解意图，决定调哪个工具（`collect_jobs` / `search_bing` / `load_resume`）
3. `ai_tools.py` 的 `run_tool()` 调度对应的工具函数
4. 工具返回数据，AI 整理后输出给用户

## 注意事项

- **浏览器环境**：Playwright 首次使用需运行 `playwright install chromium`
- **反爬检测**：51job 和 Bing 都有反爬机制，相关工具已内置 UA 伪装和等待策略
- **Cookie 登录**：51job 采集前需要手动登录一次生成 `cookies.json`，放在项目根目录
- **PDF 简历**：依赖 PyMuPDF，仅支持 `.pdf`，`.docx` 暂不支持
- **搜索限制**：`collect_jobs` 仅支持 `51job`，`search_bing` 默认返回 5 条结果

## 可扩展性 & 优化方向

### 可替换的模块

当前系统采用简单模块化设计，各层之间通过函数调用解耦，以下模块均可替换为其他实现：

| 模块 | 当前实现 | 可替换为 | 替换难度 |
|------|---------|---------|---------|
| `ai_config.py` | DeepSeek API | 任何 OpenAI 兼容 API（OpenAI、Claude、Groq、通义千问等），只需改 `api_key` 和 `base_url` |  低 |
| `tools/playwright/browser.py` | 51job 采集 | 其他招聘平台（BOSS直聘、猎聘、拉勾等），只需保持 `collect_jobs(keyword, city)` 签名不变 |  中 |
| `tools/websearch.py` | Bing 搜索 | Google / 百度 / Sogou，只需保持 `search_bing(query)` 签名不变 |  中低 |
| `tools/playwright/mouse.py` | Playwright 模拟 | Selenium / pyppeteer / DrissionPage |  中 |
| `tools/resume.py` | PyMuPDF 解析 | pdfplumber / pdfminer / OCR（如 PaddleOCR） |  中低 |

### 可升级的模块

| 模块 | 升级方向 | 收益 |
|------|---------|------|
| `agent/agent_loop.py` | 支持多轮工具调用、记忆持久化 | AI 可连续调用多个工具，上下文更连贯 |
| `agent/ai_tools.py` | 动态工具注册、工具热加载 | 新增工具无需改代码 |
| `tools/playwright/browser.py` | 多站点并行采集（asyncio.gather） | 同时搜多个招聘平台，效率翻倍 |
| `tools/websearch.py` | 多搜索引擎聚合 + 结果去重 | 搜索覆盖面更广，结果更准确 |
| `tools/resume.py` | 支持 .docx / 图片 OCR / 多格式自动识别 | 兼容更多简历文件 |

### 优化建议

1. **数据库缓存** — 搜索过的公司信息存入本地（SQLite 或文件），相同关键词重复搜索时直接命中缓存，减少请求
2. **异步编排** — 当前采集是串行的，`collect_jobs` 和 `search_bing` 可以用 `asyncio.gather` 并行执行
3. **日志系统** — 接入 `loguru` 或标准 `logging`，替代 `print()`，方便排查问题
4. **CLI 入口** — `main.py` 可做成统一命令行入口，支持 `--resume`、`--output`、`--format` 等参数
5. **反爬策略** — 当前仅做了 UA 伪装，后续可加入随机 IP（代理池）、随机延迟、浏览器指纹伪装
6. **工具函数签名统一** — 当前 `run_tool` 对 `collect_jobs` 做了参数转换（`city` → `cit_list`），后续可统一入参规范
7. **结果输出格式化** — 支持输出为 JSON / Markdown / Excel，方便留存或分享

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.13+ |
| AI | DeepSeek API |
| 浏览器自动化 | Playwright 1.60+ |
| 搜索 | Bing (Playwright headless) |
| PDF 解析 | PyMuPDF |
| 依赖管理 | pip + requirements.txt |
