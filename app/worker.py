import time
import random
import logging
import asyncio
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from typing import Dict, Any, List

from app.browser_manager import BrowserManager  # nodriver - 手动检测
from app.browser_manager_playwright import PlaywrightBrowserManager  # Playwright - 自动任务


class Worker(QObject):
    """工作线程类 - 使用BrowserManager进行浏览器操作"""

    # 信号定义
    started = pyqtSignal(int)  # 任务开始，参数：任务ID
    progress = pyqtSignal(int, str)  # 任务进度，参数：任务ID, 状态消息
    finished = pyqtSignal(int, bool)  # 任务完成，参数：任务ID, 是否成功
    error = pyqtSignal(int, str)  # 任务错误，参数：任务ID, 错误消息
    paused = pyqtSignal(int)  # 任务暂停，参数：任务ID
    resumed = pyqtSignal(int)  # 任务恢复，参数：任务ID
    manual_test_result = pyqtSignal(bool, str, str)  # 手动检测结果: 是否成功, 消息, 设备类型

    def __init__(self, task_id: int, config: Dict[str, Any], config_manager=None, stats_manager=None):
        super().__init__()
        self.task_id = task_id
        self.config = config
        self.is_running = False
        self.is_paused = False
        self.current_step = 0
        self.should_stop = False
        self.browser_manager = None
        # 默认的配置，我们需要用到任务设置配置
        self.config_manager = config_manager
        self.stats_manager = stats_manager

    def run(self):
        """执行任务"""
        self.is_running = True
        self.started.emit(self.task_id)

        try:
            # 在单独的线程中运行异步任务
            asyncio.run(self._async_run())

        except Exception as e:
            logging.error(f"任务 {self.task_id} 执行错误: {e}")
            self.error.emit(self.task_id, str(e))
            self.finished.emit(self.task_id, False)
        finally:
            self.is_running = False

    async def _async_run(self):
        """异步执行任务"""
        try:
            self.progress.emit(self.task_id, "任务开始执行")

            # 检查是否为手动检测模式
            is_manual_test = self.config.get('is_manual_test', False)

            # 根据模式选择浏览器引擎
            if is_manual_test:
                # 手动检测模式使用 nodriver
                self.browser_manager = BrowserManager(self.config)
                self.progress.emit(self.task_id, "使用 nodriver 引擎 (手动检测模式)")

                # 步骤1: 启动浏览器
                await self._start_browser(is_manual_test)
                if self.should_stop:
                    return

                await self._manual_test_only()
            else:
                # 自动任务模式使用 Playwright
                self.browser_manager = PlaywrightBrowserManager(self.config)
                self.progress.emit(self.task_id, "使用 Playwright 引擎 (自动任务模式)")

                # 步骤1: 启动浏览器
                await self._start_browser(is_manual_test)
                if self.should_stop:
                    return

                # 步骤2: 访问目标网址
                await self._visit_target()
                if self.should_stop:
                    return

                # 步骤3: 执行自动点击链接
                # if self.config.get('auto_click_links', False):
                #     await self._auto_click_links()
                #     if self.should_stop:
                #         return


            # 步骤4: 执行自动发送消息
            # if self.config.get('auto_send_messages', False):
            #     await self._auto_send_messages()
            #     if self.should_stop:
            #         return

            # 步骤5: 执行随机停留时间
            # if self.config.get('random_stay_time', False):
            #     await self._random_stay()
            #     if self.should_stop:
            #         return

            # 步骤6: 执行验证过程
            # await self._handle_verification()
            # if self.should_stop:
            #     return

            # 步骤7: 执行平台特定操作
            # await self._platform_specific_operations()
            # if self.should_stop:
            #     return

            self.progress.emit(self.task_id, "任务执行完成")
            self.finished.emit(self.task_id, True)

        except Exception as e:
            logging.error(f"任务 {self.task_id} 异步执行错误: {e}")
            self.error.emit(self.task_id, str(e))
            self.finished.emit(self.task_id, False)
        finally:
            # 关闭浏览器
            if self.browser_manager:
                await self.browser_manager.close_browser()

    async def _start_browser(self, is_manual_test: bool = False):
        """启动浏览器"""
        self.current_step = 1

        ua_type = self.config.get('ua_type', 'mobile')
        if ua_type == "浏览器":
            ua_type = 'mobile'
        else:
            ua_type = 'wechat'
        success = await self.browser_manager.start_browser(
            ua_type,
            is_manual_test,
            config_manager=self.config_manager,
            stats_manager=self.stats_manager
        )
        if success:
            device_type = self.browser_manager.get_current_device_type()
            network_type = self.browser_manager.get_current_network_type()
            self.progress.emit(self.task_id, f"浏览器启动成功 - 设备类型: {device_type.upper()}, 网络类型: {network_type.upper()}")
            await asyncio.sleep(random.uniform(1, 3))
        else:
            raise Exception("浏览器启动失败")

    async def _manual_test_only(self):
        """手动检测模式 - 只验证页面访问"""
        self.current_step = 2

        target_url = self.config['target_url']
        self.progress.emit(self.task_id, f"手动检测：正在访问目标网站 {target_url}")

        # 使用专门的页面访问检查方法
        success, device_type, network_type = await self.browser_manager.take_screenshot(
            target_url,
            self.config_manager,
            self.stats_manager
        )

        if success:
            message = f"手动检测成功：页面访问正常 - 设备类型: {device_type.upper()}, 网络类型: {network_type.upper()}"
            self.progress.emit(self.task_id, message)
            self.progress.emit(self.task_id, "浏览器保持打开，请手动检查页面内容")
            self.progress.emit(self.task_id, "检查完成后请手动关闭浏览器窗口")
            self.manual_test_result.emit(True, message, device_type)
            self.finished.emit(self.task_id, True)
        else:
            message = f"手动检测失败 - 设备类型: {device_type.upper()}, 网络类型: {network_type.upper()}"
            self.progress.emit(self.task_id, message)
            self.manual_test_result.emit(False, message, device_type)
            self.finished.emit(self.task_id, False)

    async def _visit_target(self):
        """访问目标网址"""
        self.current_step = 2

        target_url = self.config['target_url']
        self.progress.emit(self.task_id, f"访问目标: {target_url}")

        # 启动应用隐身，并导航到页面
        success, device_type, network_type = await self.browser_manager.take_screenshot(
            target_url,
            self.config_manager,
            self.stats_manager
        )

        if success:
            self.progress.emit(self.task_id, f"页面访问成功 - 设备类型: {device_type.upper()}, 网络类型: {network_type.upper()}")
        else:
            raise Exception("页面访问失败")

    async def _auto_click_links(self):
        """自动点击链接"""
        self.current_step = 3

        click_ratio = self.config.get('auto_click_ratio', 50)
        if random.randint(1, 100) <= click_ratio:
            self.progress.emit(self.task_id, f"执行自动点击链接 (比例: {click_ratio}%)")

            clicked_count = await self.browser_manager.find_and_click_links()

            if clicked_count > 0:
                self.progress.emit(self.task_id, f"成功点击 {clicked_count} 个链接")
            else:
                self.progress.emit(self.task_id, "未找到可点击的链接")
        else:
            self.progress.emit(self.task_id, f"跳过自动点击链接 (比例: {click_ratio}%)")

    async def _auto_send_messages(self):
        """自动发送消息"""
        self.current_step = 4

        message_ratio = self.config.get('auto_message_ratio', 50)
        if random.randint(1, 100) <= message_ratio:
            messages = self.config.get('message_list', [])
            if messages:
                self.progress.emit(self.task_id, f"开始发送消息 (比例: {message_ratio}%)")

                sent_count = 0
                for i, message in enumerate(messages):
                    if self.should_stop:
                        return

                    display_msg = message[:20] + "..." if len(message) > 20 else message
                    self.progress.emit(self.task_id, f"发送消息 {i + 1}: {display_msg}")

                    success = await self.browser_manager.send_message(message)
                    if success:
                        sent_count += 1
                    else:
                        self.progress.emit(self.task_id, f"消息 {i + 1} 发送失败")

                self.progress.emit(self.task_id, f"成功发送 {sent_count}/{len(messages)} 条消息")
            else:
                self.progress.emit(self.task_id, "警告: 启用了自动发送消息但消息列表为空")
        else:
            self.progress.emit(self.task_id, f"跳过自动发送消息 (比例: {message_ratio}%)")

    async def _random_stay(self):
        """随机停留时间"""
        self.current_step = 5

        stay_time = random.randint(
            self.config.get('min_stay_time', 5),
            self.config.get('max_stay_time', 30)
        )

        self.progress.emit(self.task_id, f"随机停留 {stay_time} 秒")

        stay_start = time.time()
        while time.time() - stay_start < stay_time:
            if self.should_stop:
                return

            # 检查暂停状态
            while self.is_paused:
                await asyncio.sleep(0.1)
                if self.should_stop:
                    return

            # 随机滚动页面
            if random.random() < 0.3:
                await self.browser_manager.random_scroll()

            await asyncio.sleep(1)

            # 每5秒报告一次进度
            elapsed = int(time.time() - stay_start)
            if elapsed % 5 == 0 and elapsed > 0:
                self.progress.emit(self.task_id, f"停留中... ({elapsed}/{stay_time})")

    async def _handle_verification(self):
        """处理验证过程"""
        self.current_step = 6

        if self.config.get('bypass_verification', False):
            self.progress.emit(self.task_id, "尝试绕过验证检查")
            await asyncio.sleep(2)
        else:
            self.progress.emit(self.task_id, "执行正常验证流程")
            await asyncio.sleep(2)

    async def _platform_specific_operations(self):
        """平台特定操作"""
        self.current_step = 7

        platform = self.config.get('platform', 'PLATFORM1')
        platform_actions = {
            'PLATFORM1': "执行平台1特定操作",
            'PLATFORM2': "执行平台2特定操作",
            'PLATFORM3': "执行平台3特定操作"
        }

        action_text = platform_actions.get(platform, "执行平台特定操作")
        self.progress.emit(self.task_id, action_text)

        await asyncio.sleep(2)

    def pause(self):
        """暂停任务"""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            self.paused.emit(self.task_id)
            self.progress.emit(self.task_id, f"任务已暂停 (步骤{self.current_step})")

    def resume(self):
        """恢复任务"""
        if self.is_running and self.is_paused:
            self.is_paused = False
            self.resumed.emit(self.task_id)
            self.progress.emit(self.task_id, f"任务已恢复 (步骤{self.current_step})")

    def stop(self):
        """停止任务"""
        self.should_stop = True
        self.is_running = False
        self.is_paused = False
        self.progress.emit(self.task_id, "任务已停止")