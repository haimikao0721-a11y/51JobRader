# 模拟人为操作运行py
from playwright.async_api import Page
import random
import asyncio


class Human(object):
    def __init__(self, page: Page):
        self.page = page
        self._x = 500
        self._y = 500

    def bezier_points(self, from_x, from_y, to_x, to_y, steps=30):
        """生成二次贝塞尔曲线路径"""
        ctrl_x = (from_x + to_x) / 2 + random.uniform(-50, 50)
        ctrl_y = (from_y + to_y) / 2 + random.uniform(-30, 30)

        points = []
        for i in range(steps + 1):
            t = i / steps
            x = (1 - t) ** 2 * from_x + 2 * (1 - t) * t * ctrl_x + t ** 2 * to_x
            y = (1 - t) ** 2 * from_y + 2 * (1 - t) * t * ctrl_y + t ** 2 * to_y
            points.append((x, y))
        return points

    async def move_mouse(self, to_x, to_y):
        """沿贝塞尔曲线移动到目标位置"""
        points = self.bezier_points(self._x, self._y, to_x, to_y)
        for px, py in points:
            await self.page.mouse.move(px, py)
            await asyncio.sleep(random.uniform(0.005, 0.015))
        self._x, self._y = to_x, to_y

    async def mouse_move_click(self, selector: str):
        '''
        模拟人从当前位置移动到某个元素并点击
        '''
        el = self.page.locator(selector)
        await el.wait_for()
        box = await el.bounding_box()
        if not box:
            return

        target_x = box["x"] + random.uniform(0, box["width"])
        target_y = box["y"] + random.uniform(0, box["height"])

        await self.move_mouse(target_x, target_y)
        await asyncio.sleep(random.uniform(0.05, 0.15))
        await self.page.mouse.click(target_x, target_y)
        await asyncio.sleep(random.uniform(0.3, 0.8))
    
    async def men_input(self, input_str: str):
        """
        模拟人输入内容（支持中文）
        """
        await self.page.keyboard.type(input_str, delay=random.uniform(50, 200))
        await asyncio.sleep(random.uniform(0.3, 0.8))
            
