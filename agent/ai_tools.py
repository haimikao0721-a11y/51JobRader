"""工具注册表 — 第三方通过 @register_tool 装饰器注册，无需改调度逻辑"""
import asyncio

_registry: dict[str, dict] = {}


def register_tool(name: str, description: str, parameters: dict):
    """装饰器：将函数注册为 AI 可调用的工具。注册后自动出现在 get_tools() 列表中。

    用法:
        @register_tool("my_search", "搜索互联网", {
            "type": "object",
            "properties": {"q": {"type": "string"}},
            "required": ["q"],
        })
        def _handle(q: str):
            ...
    """
    def decorator(func):
        _registry[name] = {
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                },
            },
            "handler": func,
        }
        return func
    return decorator


def get_tools() -> list[dict]:
    """返回所有已注册工具的 OpenAI tool schema 列表"""
    return [v["schema"] for v in _registry.values()]


def run_tool(name: str, args: dict):
    """按名调度工具。找不到抛 ValueError，工具内部异常向上抛（由 Runtime 层处理）"""
    entry = _registry.get(name)
    if not entry:
        raise ValueError(f"未知工具: {name}")
    return entry["handler"](**args)


# ── 内置工具注册 ──────────────────────────────────
# 第三方新增工具：仿照下方格式，在任意模块加 @register_tool 并确保被导入即可


@register_tool(
    name="collect_jobs",
    description="在招聘网站搜索职位，返回 title / salary / company / location / tags / jd",
    parameters={
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "搜索关键词，如 python开发、产品经理"},
            "city": {"type": "string", "description": "城市名，多个用逗号分隔（可选），如 深圳、深圳,上海"},
        },
        "required": ["keyword"],
    },
)
def _tool_collect_jobs(keyword: str, city: str = ""):
    from tools.playwright.browser import collect_jobs

    cit_list = (
        [c.strip() for c in city.replace("，", ",").split(",") if c.strip()]
        if city else []
    )
    return asyncio.run(collect_jobs(keyword, cit_list))


@register_tool(
    name="search_bing",
    description="搜索公司/事物信息，返回 title / url / snippet / content（含页面正文）",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词，如 米哈游 公司背景"},
        },
        "required": ["query"],
    },
)
def _tool_search_bing(query: str):
    from tools.websearch import search_bing

    return asyncio.run(search_bing(query))
