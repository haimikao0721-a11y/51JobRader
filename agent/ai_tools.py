import json
import asyncio


tools = [
    {
        "type": "function",
        "function": {
            "name": "collect_jobs",
            "description": "在 51job 搜索职位，返回 title / salary / company / location / tags / jd",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词，如 python开发、java 后端、产品经理",
                    },
                    "city": {
                        "type": "string",
                        "description": "城市名，多个用逗号分隔（可选），如 深圳、深圳,上海,广州（最多5个）",
                    },
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_bing",
            "description": "在Bing搜索公司信息，返回 title / url / snippet / content（含页面正文）",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，如 长沙节点薪火信息有限公司、上海米哈游公司",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


def run_tool(name: str, args: dict):
    if name == "collect_jobs":
        from tools.playwright.browser import collect_jobs

        city_str = args.pop("city", "")
        if city_str:
            args["cit_list"] = [
                c.strip()
                for c in city_str.replace("，", ",").split(",")
                if c.strip()
            ]
        return asyncio.run(collect_jobs(**args))

    if name == "search_bing":
        from tools.websearch import search_bing

        return asyncio.run(search_bing(**args))

    raise ValueError(f"未知工具: {name}")
