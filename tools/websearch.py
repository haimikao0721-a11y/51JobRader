"""
Bing 网页搜索工具
用法: search_bing("关键词", count=10) → list[dict]
"""
import os
import sys
import asyncio

# 避免 tools/playwright/ 目录和 pip 安装的 playwright 冲突
sys.path = [p for p in sys.path if not p.rstrip("\\").endswith("tools")]

from playwright.async_api import async_playwright

# 确保项目根目录在 path 中
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


async def search_bing(query: str, count: int = 10) -> list[dict]:
    """
    在 Bing 搜索关键词，返回搜索结果列表
    参数:
        query:  搜索关键词
        count:  返回结果条数（默认 10）
    返回:
        list[dict]: 每个结果包含 title, url, snippet
    """
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
        )
        page = await context.new_page()

        url = f"https://www.bing.com/search?q={query}&setlang=zh-cn"
        await page.goto(url)

        # 关掉 cookie 弹窗（如果有的话）
        try:
            consent = page.locator("#bnp_btn_accept, #sb_accept, button#accept")
            if await consent.count() > 0:
                await consent.click()
                await page.wait_for_timeout(1000)
        except:
            pass

        await page.wait_for_timeout(2000)

        # 提取所有 b_algo（普通搜索结果）+ b_ans（置顶答案/摘要）
        items = await page.query_selector_all("#b_results > li")
        for item in items[:count * 2]:
            # 跳过非结果类型的 li
            class_name = await item.get_attribute("class") or ""
            if "b_ad" in class_name or "b_pag" in class_name:
                continue

            title_el = await item.query_selector("h2 a")
            if not title_el:
                continue

            title = (await title_el.inner_text()).strip()
            link = await title_el.get_attribute("href") or ""

            snippet_el = await item.query_selector(".b_caption p, .b_lineclamp2, .b_lineclamp3")
            snippet = (await snippet_el.inner_text()).strip() if snippet_el else ""

            if title and len(results) < count:
                results.append({
                    "title": title,
                    "url": link.strip(),
                    "snippet": snippet,
                })

        # 降级：如果上面没拿到，直接捞 li.b_algo
        if not results:
            items = await page.query_selector_all("li.b_algo")
            for item in items[:count]:
                title_el = await item.query_selector("h2 a")
                snippet_el = await item.query_selector(".b_caption p, .b_lineclamp2")
                title = (await title_el.inner_text()).strip() if title_el else ""
                link = await title_el.get_attribute("href") if title_el else ""
                snippet = (await snippet_el.inner_text()).strip() if snippet_el else ""
                if title:
                    results.append({
                        "title": title,
                        "url": link.strip(),
                        "snippet": snippet,
                    })

        await browser.close()

    return results

async def main():
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "Python 招聘"
    results = await search_bing(query)
    print(f"\n=== Bing 搜索结果: {query} ===\n")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['title']}")
        print(f"   {r['url']}")
        print(f"   {r['snippet'][:120]}...\n")
    print(f"共 {len(results)} 条结果")


if __name__ == "__main__":
    asyncio.run(main())
