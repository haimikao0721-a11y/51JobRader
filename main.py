"""JobRadar — CLI 统一入口"""

import sys
import argparse


def cmd_chat(args):
    """启动交互式采集助手"""
    from agent.agent_loop import main as chat_main

    if args.resume:
        # 透传给 agent_loop 的 --resume 参数
        sys.argv = [sys.argv[0], "--resume", args.resume]
    chat_main()


def cmd_search(args):
    """直接搜索职位（跳过 AI 对话）"""
    from tools.playwright.browser import collect_jobs
    import asyncio

    result = asyncio.run(collect_jobs(args.keyword, args.city))
    for i, job in enumerate(result, 1):
        print(f"\n{'=' * 50}")
        print(f"{i}. {job['title']}")
        print(f"   公司: {job['company']}  |  薪资: {job['salary']}")
        print(f"   地点: {job['location']}")
        print(f"   标签: {', '.join(job['tags'])}")
        print(f"   JD: {job['jd'][:200]}...")


def cmd_web(args):
    """直接搜索 Bing（跳过 AI 对话）"""
    from tools.websearch import search_bing
    import asyncio

    result = asyncio.run(search_bing(args.query, args.count))
    for i, r in enumerate(result, 1):
        print(f"\n{i}. {r['title']}")
        print(f"   URL: {r['url']}")
        print(f"   摘要: {r['snippet'][:120]}...")


def cmd_resume(args):
    """解析简历文件并输出文本"""
    from resume import load_resume

    text = load_resume(args.file)
    print(text)


def main():
    parser = argparse.ArgumentParser(description="JobRadar — 职位采集分析工具")
    parser.add_argument("--resume", help="简历文件路径，启动时注入上下文")

    sub = parser.add_subparsers(dest="command", help="可用命令")

    # python main.py search <keyword> [--city ...]
    p_search = sub.add_parser("search", help="搜索职位")
    p_search.add_argument("keyword", help="搜索关键词")
    p_search.add_argument("--city", default="", help="城市，多个用逗号分隔")

    # python main.py web <query> [--count 5]
    p_web = sub.add_parser("web", help="Bing 搜索")
    p_web.add_argument("query", help="搜索关键词")
    p_web.add_argument("--count", type=int, default=5, help="返回条数（默认 5）")

    # python main.py resume <file>
    p_resume = sub.add_parser("resume", help="解析简历文件")
    p_resume.add_argument("file", help="简历文件路径")

    args, _ = parser.parse_known_args()

    if args.command == "search":
        cmd_search(args)
    elif args.command == "web":
        cmd_web(args)
    elif args.command == "resume":
        cmd_resume(args)
    else:
        # 默认启动交互式对话
        cmd_chat(args)


if __name__ == "__main__":
    main()
