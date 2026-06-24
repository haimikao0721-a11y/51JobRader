"""
Bing 网页搜索工具
用法: search_bing("关键词", count=10) → list[dict]
"""
import os
import sys
import asyncio
import base64
import urllib.parse

# 避免 tools/playwright/ 目录和 pip 安装的 playwright 冲突
sys.path = [p for p in sys.path if not p.rstrip("\\").endswith("tools")]

from playwright.async_api import async_playwright

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _bing_url_to_real(href: str) -> str:
    """从 Bing 追踪 URL (bing.com/ck/...) 中提取真实 URL"""
    if "bing.com/ck/" not in href:
        return href
    parsed = urllib.parse.urlparse(href)
    params = urllib.parse.parse_qs(parsed.query)
    u_val = params.get("u", [None])[0]
    if not u_val:
        return href
    # a1 是前缀，后面是 base64 编码的真实 URL
    b64 = u_val[2:] if u_val.startswith("a1") else u_val
    padding = (4 - len(b64) % 4) % 4
    if padding:
        b64 += "=" * padding
    try:
        decoded = base64.b64decode(b64).decode("utf-8")
        return urllib.parse.unquote(decoded)
    except Exception:
        return href


async def _fetch_page_content(page, url: str, timeout: int = 30000) -> str:
    """打开页面提取正文内容（正文前 3000 字）"""
    for attempt in range(2):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            await page.wait_for_timeout(3000)
            break
        except Exception:
            if attempt == 1:
                return "[抓取失败: Timeout]"

    try:
        content = await page.evaluate("""() => {
            // 尝试常见的正文容器（按优先级）
            const selectors = [
                // 通用
                'article',
                'main',
                '.post-content',
                '.article-content',
                '.entry-content',
                '.main-content',
                '#content',
                '.content',
                // 中文站点
                '.lemmaWgt-article-content',  // 百度百科
                '.para',                      // 百度百科
                '.basic-info',                // 百度百科
                '.J-summary',                 // 百度百科
                '.RichText',                  // 知乎
                '.Post-content',              // 知乎
                '#article_content',           // CSDN
                '.article_content',           // CSDN
                '.rich_media_content',        // 微信公众号
                '#js_content',                // 微信公众号
                '.detail-content',
                '.article',
                '#article',
                '.post_body',
            ];
            let mainEl = null;
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el && el.innerText.trim().length > 50) {
                    mainEl = el;
                    break;
                }
            }
            if (mainEl) {
                return mainEl.innerText.trim();
            }
            // fallback: 从 body 提取最大文本块
            const body = document.body;
            if (!body) return '';
            const cloned = body.cloneNode(true);
            cloned.querySelectorAll('script, style, nav, footer, header, iframe, .sidebar, .comments, .aside, [role="navigation"]').forEach(el => el.remove());
            // 尝试找最大的 p / div 文本块
            let best = '';
            for (const tag of ['p', 'div', 'section', 'td']) {
                for (const el of cloned.querySelectorAll(tag)) {
                    const txt = el.innerText.trim();
                    if (txt.length > best.length && txt.length > 80) {
                        // 排除纯导航文本
                        const navWords = ['首页', '登录', '注册', '搜索', '关于', '帮助', 'Copyright', '©'];
                        const navRatio = navWords.filter(w => txt.includes(w)).length / navWords.length;
                        if (navRatio < 0.5) best = txt;
                    }
                }
            }
            return best || cloned.innerText.trim();
        }""")
    except Exception as e:
        content = f"[抓取失败: {type(e).__name__}]"

    # 限制长度
    if content and len(content) > 3000:
        content = content[:3000] + "…[截断]"
    return content or "[无正文内容]"


async def search_bing(query: str, count: int = 5) -> list[dict]:
    """
    在 Bing 搜索关键词，返回搜索结果列表（含各页面正文）
    参数:
        query:  搜索关键词
        count:  返回结果条数（默认 5）
    返回:
        list[dict]: 每个结果包含 title, url, snippet, content
    """
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        # 必须用 new_context 设置 UA + locale，否则 Bing 会拦截
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
        )
        page = await context.new_page()

        await page.goto(
            f"https://www.bing.com/search?q={query}",
            wait_until="load",
        )

        # 等待搜索结果渲染（防 0 结果）
        try:
            await page.wait_for_selector("li.b_algo", timeout=8000)
        except Exception:
            pass  # 超时后用 query_selector_all 再查一次
        await page.wait_for_timeout(1000)

        # 提取搜索结果
        items = await page.query_selector_all("li.b_algo")
        for item in items[:count]:
            title_el = await item.query_selector("h2 a")
            snippet_el = await item.query_selector(".b_caption p, .b_lineclamp2")

            title = (await title_el.inner_text()).strip() if title_el else ""
            raw_link = await title_el.get_attribute("href") if title_el else ""
            snippet = (await snippet_el.inner_text()).strip() if snippet_el else ""

            # 解析真实 URL（Bing 的 href 是追踪链接）
            url = _bing_url_to_real(raw_link.strip()) if raw_link else ""

            if title:
                # 打开结果页面提取正文
                content_page = await context.new_page()
                content = await _fetch_page_content(content_page, url)
                await content_page.close()

                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "content": content,
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
        print(f"   URL: {r['url']}")
        print(f"   摘要: {r['snippet'][:120]}...")
        print(f"   正文: {r['content'][:200]}...\n")
    print(f"共 {len(results)} 条结果")


if __name__ == "__main__":
    asyncio.run(main())
