# 51job 职位采集工具
# 用法: collect_jobs("关键词") → list[dict]
import asyncio
import json
import os
import sys
import random

# 确保项目根目录在 path 中（兼容直接运行和作为模块导入）
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from playwright.async_api import async_playwright
from tools.playwright.mouse import Human

COOKIE_FILE = os.path.join(os.path.dirname(__file__), "cookies.json")


async def save_cookies(page):
    cookies = await page.context.cookies()
    with open(COOKIE_FILE, "w") as f:
        json.dump(cookies, f)
    print(f"cookie 已保存 ({len(cookies)} 条)")

async def load_cookies(page):
    if not os.path.exists(COOKIE_FILE):
        return False
    with open(COOKIE_FILE) as f:
        cookies = json.load(f)
    await page.context.add_cookies(cookies)
    print(f"已注入 cookie ({len(cookies)} 条)")
    return True

async def collect_jobs(keyword: str, cit_list=list|None) -> list[dict]:
    """
    搜索 51job 并采集职位完整信息
    参数:
        keyword:   搜索关键词，如 "python开发"
        cit_list:  城市名列表，如 ["深圳"]、["深圳","上海"]（可选）
                   通过 UI 弹窗筛选，不传则不限制
    返回:
        list[dict]: 每个职位包含 title, salary, company, location, tags, jd
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        page = await browser.new_page()

        # 注入 cookie
        await load_cookies(page)

        # 去个人中心，检查登录状态
        await page.goto("https://we.51job.com/pc/my/myjob")
        await page.wait_for_timeout(3000)

        if "login" in page.url.lower() or "passport" in page.url.lower():
            print("请手动登录...")
            await page.wait_for_url("**/myjob**", timeout=0)
            await save_cookies(page)
        else:
            print("已登录")
            if not os.path.exists(COOKIE_FILE):
                await save_cookies(page)

        # 输入搜索关键词
        h = Human(page)
        await h.mouse_move_click(".searchInp input")
        await h.men_input(keyword)

        # 点击搜索 → 打开新标签页
        async with page.context.expect_page() as new_page_info:
            await h.mouse_move_click('[sensor_elementid="sensor_my_searchButton"]')
        search_page = await new_page_info.value
        await search_page.wait_for_load_state()
        print(f"搜索页 URL: {search_page.url}")

        # 等搜索结果渲染
        try:
            await search_page.wait_for_selector(".joblist-item-job", timeout=10000)
        except:
            await search_page.wait_for_timeout(5000)

        # 在页面筛选目标城市
        if cit_list:
            print(f"展开城市筛选: {cit_list}")
            await search_page.wait_for_timeout(2000)

            # 点"其他城市"打开城市选择弹窗
            await search_page.locator(".allcity").click()
            await search_page.wait_for_timeout(1500)

            # 等待城市选择弹窗出现（用弹窗内特有的元素判断）
            await search_page.wait_for_selector(".jbs_cascader_panel", timeout=5000)
            print("城市选择弹窗已打开")

            # 先清空所有已选中的城市标签
            clear_btns = search_page.locator(".selected_list_wrapper_tag .el-tag__close")
            clear_count = await clear_btns.count()
            if clear_count > 0:
                print(f"清空 {clear_count} 个已选城市...")
                for _ in range(clear_count):
                    await clear_btns.first.click()
                    await search_page.wait_for_timeout(300)
                print("已清空")

            # 在弹窗中选择目标城市（从 ABCD 字母分类列表中选）
            for city in cit_list:
                el = search_page.locator(f'.resumeDialog__right-city[title="{city}"]')
                if await el.count() > 0:
                    await el.click()
                    print(f"选择城市: {city}")
                else:
                    print(f"未找到城市: {city}")
                await search_page.wait_for_timeout(300)

            # 点"确定"（限定在"选择城市"弹窗内）
            dialog = search_page.get_by_role("dialog").filter(has_text="选择城市")
            await dialog.locator(".confirm_button").click()
            await search_page.wait_for_timeout(1000)
            print("城市筛选已确认")
            # 等搜索结果刷新
            await search_page.wait_for_timeout(2000)
            

        # 获取列表基本信息
        jobs_list = await search_page.evaluate("""() => {
            const items = document.querySelectorAll('.joblist-item-job');
            return Array.from(items).map(el => ({
                title: el.querySelector('.jname')?.innerText?.trim() || '',
                salary: el.querySelector('.sal')?.innerText?.trim() || '',
                company: el.querySelector('.cname')?.innerText?.trim() || '',
                location: el.querySelector('.location, .area, .city, .workplace')?.innerText?.trim() || '',
                tags: Array.from(el.querySelectorAll('.tag')).map(t => t.innerText.trim()),
            }));
        }""")
        print(f"列表共 {len(jobs_list)} 个职位")

        # 逐个进详情页拿 JD
        results = []
        for i, job in enumerate(jobs_list):
            print(f"  获取第 {i+1}/{len(jobs_list)}: {job['title']}")
            try:
                async with search_page.context.expect_page() as new_page_info:
                    await search_page.locator(".joblist-item-job").nth(i).locator(".jname").click()
                detail_page = await new_page_info.value

                # 等职位内容真正渲染出来
                try:
                    await detail_page.wait_for_selector(".jTitle, .job-detail", timeout=15000)
                except:
                    await detail_page.wait_for_timeout(5000)

                # 调试：看看页面结构
                structure = await detail_page.evaluate("""() =>
                    Array.from(document.querySelectorAll('[class*="detail"],[class*="content"],[class*="main"],[class*="primary"],[class*="job-detail"],[class*="desc"]'))
                        .slice(0,20).map(e => e.tagName+'.'+(e.className||'').split(' ').join('.'))
                """)
                if structure:
                    print(f"  页面容器: {structure}")

                jd_text = await detail_page.evaluate("""() => {
                    const sel = '.job-detail, .job-primary, .job-main, [class*="job-detail"], [class*="job-primary"], .j_jobmsg, .jobmsg, .job_content';
                    for (const s of sel.split(', ')) {
                        const el = document.querySelector(s);
                        if (el && el.innerText.trim().length > 50) return el.innerText.trim();
                    }
                    // 降级：body 去掉页脚导航
                    const body = document.body.cloneNode(true);
                    body.querySelectorAll('script, style, .header, .footer, .nav, [class*="footer"], [class*="copyright"], [class*="friend-link"]').forEach(el => el.remove());
                    return body.innerText.trim();
                }""")

                # 检查是否被反爬拦了
                if "请求时间" in jd_text and "TraceID" in jd_text:
                    print(f"触发反爬，等 5 秒重试...")
                    await asyncio.sleep(5)
                    try:
                        await detail_page.wait_for_selector(".jTitle, .job-detail", timeout=10000)
                    except:
                        pass
                    jd_text = await detail_page.evaluate("""() => {
                        const sel = '.job-detail, .job-primary, .job-main, [class*="job-detail"], [class*="job-primary"], .j_jobmsg, .jobmsg, .job_content';
                        for (const s of sel.split(', ')) {
                            const el = document.querySelector(s);
                            if (el && el.innerText.trim().length > 50) return el.innerText.trim();
                        }
                        const body = document.body.cloneNode(true);
                        body.querySelectorAll('script, style, .header, .footer, .nav, [class*="footer"], [class*="copyright"], [class*="friend-link"]').forEach(el => el.remove());
                        return body.innerText.trim();
                    }""")

                await detail_page.close()

                results.append({
                    "title": job["title"],
                    "salary": job["salary"],
                    "company": job["company"],
                    "location": job.get("location", ""),
                    "tags": job["tags"],
                    "jd": jd_text,
                })
            except Exception as e:
                print(f"失败: {e}")
            # 间隔一段时间，避免被限
            await asyncio.sleep(random.uniform(2, 4))

        await browser.close()
        return results


async def main():
    keyword = sys.argv[1] if len(sys.argv) > 1 else "python开发"
    city_arg = sys.argv[2] if len(sys.argv) > 2 else ""
    cit_list = city_arg.replace("，", ",").split(",") if city_arg else None
    results = await collect_jobs(keyword, cit_list)
    print("\n=== 采集完成 ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n共 {len(results)} 个职位")


if __name__ == "__main__":
    asyncio.run(main())
