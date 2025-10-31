import logging
import random
import asyncio
import nodriver as uc
from typing import List, Optional, Dict, Any
import time

from proxy.config import Config
from proxy.proxy_manager import ProxyManager
from ua.ua_manager import OptimizedUserAgentManager
from utils.nodriver_result_parser import NodriverResultParser

# 初始化管理器
proxy_manager = ProxyManager(Config.PROXY_POOLS)

class BrowserManager:
    """浏览器管理器 - 适配最新版nodriver"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.browser = None
        self.current_tab = None
        self.is_running = False
        self.page = None
        self.result_parser = NodriverResultParser()
        self.ua_manager = OptimizedUserAgentManager()
        self.current_ua = None
        self.use_file_reading = None
        self.is_manual_test = False  # 标记是否为手动检测模式
        # 设备配置库
        self.device_profiles = {
            'random_mobile': {
                'viewport': random.choice([(390, 844), (360, 800), (393, 851), (412, 915)]),
                'device_scale_factor': random.choice([2.0, 2.625, 2.75, 3.0]),
                'platform': random.choice(['iPhone', 'Linux armv8l', 'Linux aarch64']),
                'vendor': random.choice(['Apple Computer, Inc.', 'Google Inc.']),
                'touch_points': 5
            }
        }

    async def start_browser(self,device = 'mobile',is_manual_test: bool = False,use_file_reading = None):
        """启动浏览器"""

        # 获取移动端基本参数
        config = self.device_profiles.get('random_mobile', self.device_profiles['random_mobile'])

        # 获取UA参数
        if use_file_reading is None:
            # 自动选择：大文件使用直接读取，小文件使用缓存
            stats = self.ua_manager.get_ua_stats()
            self.use_file_reading = stats['total_lines'] > 1000

        if self.use_file_reading:
            self.current_ua = self.ua_manager.get_random_ua_from_file(device)
            print("🔧 使用文件直接读取模式")
        else:
            self.current_ua = self.ua_manager.get_random_ua(device)
            print("🔧 使用缓存模式")

        logging.info(self.current_ua)

        # 基础参数
        browser_args = [
            # 基础安全参数
            '--no-sandbox',
            '--disable-dev-shm-usage',

            # 关键：禁用所有调试和开发者工具
            '--disable-blink-features=AutomationControlled',
            '--disable-features=TranslateUI,VizDisplayCompositor',
            '--disable-ipc-flooding-protection',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--disable-background-timer-throttling',

            # 隐藏Chrome特征
            '--disable-component-extensions-with-background-pages',
            '--disable-default-apps',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-translate',
            '--no-first-run',
            '--no-default-browser-check',

            # 网络相关
            '--disable-background-networking',
            '--disable-sync',
            '--metrics-recording-only',
            '--safebrowsing-disable-auto-update',

            # 关键：禁用远程调试
            '--remote-debugging-port=0',
            '--disable-remote-fonts',
            '--disable-logging',
            '--disable-crash-reporter',

            # 移动端参数
            f'--user-agent={self.current_ua}',
            f'--window-size={config["viewport"][0]},{config["viewport"][1]}',
            f'--device-scale-factor={config["device_scale_factor"]}',
            '--hide-scrollbars',

            # 额外的隐身参数
            '--disable-web-security',
            '--disable-popup-blocking',
            '--disable-hang-monitor',
            '--disable-client-side-phishing-detection',
        ]

        # 获取代理配置
        try:
            proxy_config = proxy_manager.get_valid_proxy()
            proxy_url = f"{proxy_config['ip']}:{proxy_config['port']}"
            print(f"{proxy_config.get("http")}")
            browser_args.extend([
                f'--proxy-server=http://{proxy_url}',
                '--proxy-bypass-list=<-loopback>',  # 绕过本地地址
            ])
            print(f"代理ip: {proxy_config['http']}")
        except Exception as e:
            print("代理获取失败")


        try:
            self.is_manual_test = is_manual_test
            logging.info("正在启动浏览器...")

            # 启动浏览器
            self.browser = await uc.start(
                headless=self.config.get('headless_mode', False) and not is_manual_test,
                browser_args=browser_args,
                user_data_dir='./mobile_stealth_data'
            )
            # 获取主页面 - 修复这里
            if hasattr(self.browser, 'main_tab'):
                self.page = self.browser.main_tab
            else:
                # 如果沒有 main_tab 属性，尝试其他方式获取页面
                self.page = self.browser
            self.is_running = True
            logging.info("浏览器启动成功")
            return True

        except Exception as e:
            logging.error(f"浏览器启动失败: {e}")
            return False

    async def close_browser(self):
        """关闭浏览器 - 手动检测模式下不自动关闭"""
        try:
            # 如果是手动检测模式，不自动关闭浏览器，让用户自己关闭
            if self.is_manual_test:
                logging.info("手动检测模式：浏览器保持打开，请用户手动关闭")
                return

            if self.browser and self.is_running:
                # 正常模式下关闭浏览器
                await self.browser.stop()
                self.is_running = False
                logging.info("浏览器已关闭")
        except Exception as e:
            logging.error(f"关闭浏览器失败: {e}")

    async def take_screenshot(self,url):

        try:

            # 应用完整隐身配置（使用随机设备）
            await self.apply_complete_stealth()

            # 测试隐身效果
            # await self.test_stealth_effectiveness()

            result = await self.stealth_navigate(url, delay_before=2, delay_after=3,max_retries=2)

            if result['success']:
                print(f"✓ 访问成功")
                print(f"  标题: {result['title']}")
                print(f"  内容长度: {result['content_length']}")
                return True
            else:
                print(f"✗ 访问失败: {result.get('error', '未知错误')}")
                return False

        except Exception as e:
            print(f"访问失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close_browser()

    async def stealth_navigate(self, url, delay_before=1, delay_after=3,max_retries = 1):
        """隐身导航到指定URL（支持重试）- 修复版本"""
        for attempt in range(max_retries):
            try:
                print(f"\n🌐 尝试 {attempt + 1}/{max_retries}: 访问 {url}")

                if delay_before > 0:
                    print(f"⏳ 导航前等待 {delay_before} 秒...")
                    await asyncio.sleep(delay_before)

                # 使用修复的导航方法
                navigation_success = await self.navigate_to_url(url)

                if not navigation_success:
                    print("❌ 导航失败")
                    continue

                # 应用隐身脚本
                await self.apply_stealth_scripts()

                # 安全获取页面状态
                page_info = await self.get_page_info()

                # 确保 page_info 是字典且可以安全访问
                if isinstance(page_info, dict) and page_info.get('success') and page_info.get('bodyContent', 0) > 0:
                    print(f"✅ 访问成功")
                    print(f"   标题: {page_info.get('title', '未知')}")
                    print(f"   内容长度: {page_info.get('bodyContent', 0)}")
                    #print(f"   使用代理: {self.current_proxy or '无'}")

                    if delay_after > 0:
                        print(f"⏳ 导航后等待 {delay_after} 秒...")
                        await asyncio.sleep(delay_after)

                    return {
                        'success': True,
                        'title': page_info.get('title', '未知'),
                        'content_length': page_info.get('bodyContent', 0),
                        'url': page_info.get('url', '未知'),
                        #'proxy': self.current_proxy,
                        'attempt': attempt + 1
                    }
                else:
                    error_msg = page_info.get('error', '页面内容为空') if isinstance(page_info, dict) else '页面信息获取失败'
                    print(f"❌ 页面加载问题: {error_msg}")

            except Exception as e:
                print(f"❌ 导航失败 (尝试 {attempt + 1}): {e}")

                if attempt == max_retries - 1:
                    return {
                        'success': False,
                        'error': str(e),
                        #'proxy': self.current_proxy,
                        'attempt': attempt + 1
                    }

                # 更换代理重试
                # if self.proxy_manager.proxies and len(self.proxy_manager.proxies) > 1:
                #     print("🔄 更换代理并重试...")
                #     await self.restart_with_new_proxy()
                #     await asyncio.sleep(2)

            await asyncio.sleep(2)

        return {'success': False, 'error': '所有重试都失败'}


    async def get_page_info(self):
        """安全获取页面信息"""
        script = """
        (function() {
            try {
                return {
                    success: true,
                    readyState: document.readyState,
                    bodyContent: document.body ? document.body.innerHTML.length : 0,
                    title: document.title || '无标题',
                    url: window.location.href,
                    hasBody: !!document.body
                };
            } catch(e) {
                return {
                    success: false,
                    error: e.toString()
                };
            }
        })()
        """

        result = await self.execute_script_safely(script, "获取页面信息")
        if result and result.get('success'):
            return result
        else:
            return {
                'success': False,
                'error': result.get('error') if result else '未知错误',
                'readyState': 'unknown',
                'bodyContent': 0,
                'title': '未知',
                'url': '未知',
                'hasBody': False
            }

    async def apply_stealth_scripts(self):
        """应用隐身脚本 - 使用安全执行"""
        print("🔧 应用隐身脚本...")

        stealth_scripts = [
            {
                "name": "删除CDP变量",
                "script": """
                    // 删除CDP相关变量
                    const cdpVars = [
                        'cdc_adoQpoasnfa76pfcZLmcfl_Array',
                        'cdc_adoQpoasnfa76pfcZLmcfl_Promise', 
                        'cdc_adoQpoasnfa76pfcZLmcfl_Symbol',
                        '_Selenium_IDE_Recorder',
                        '_phantom',
                        'callPhantom'
                    ];

                    for (const varName of cdpVars) {
                        try {
                            delete window[varName];
                        } catch(e) {}
                    }
                    return 'CDP变量清理完成';
                """
            },
            {
                "name": "隐藏webdriver",
                "script": """
                    // 隐藏webdriver属性
                    try {
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined,
                            configurable: true
                        });
                        return 'webdriver隐藏成功';
                    } catch(e) {
                        return 'webdriver隐藏失败: ' + e.toString();
                    }
                """
            }
        ]

        for script_info in stealth_scripts:
            try:
                print(f"  执行: {script_info['name']}")
                result = await self.execute_script_safely(script_info['script'], script_info['name'])
                if result:
                    print(f"    ✅ {script_info['name']}: {result}")
                else:
                    print(f"    ❌ {script_info['name']}: 执行失败")
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"    ❌ {script_info['name']}: 异常 - {e}")

    async def execute_script_safely(self, script, description="脚本"):
        """安全的脚本执行方法 - 修复版"""
        try:
            if not self.page:
                print(f"❌ {description}: 页面未初始化")
                return None

            # 直接执行脚本
            raw_result = await self.page.evaluate(script)

            # 解析结果
            parsed_result = self.result_parser.parse_result(raw_result)

            print(f"🔍 {description} - 原始结果: {raw_result}")
            print(f"🔍 {description} - 解析结果: {parsed_result}")

            return parsed_result

        except Exception as e:
            print(f"❌ {description}: 执行失败 - {e}")
            return {'success': False, 'error': str(e)}

    async def apply_complete_stealth(self, device='mobile'):
        """应用完整的隐身配置"""
        print("=" * 50)
        print("开始应用完整隐身配置")
        print("=" * 50)

        # 等待页面就绪
        print("等待页面准备就绪...")
        if not await self.wait_for_page_ready():
            print("警告: 页面准备超时，但继续执行")

        # 先访问一个简单页面来确保浏览器正常工作
        try:
            await self.page.get('about:blank')
            await asyncio.sleep(1)
        except:
            pass

        print("应用CDP协议隐藏...")
        await self.hide_cdp_protocol()

        print("伪造浏览器指纹...")
        config = self.device_profiles.get(device, self.device_profiles['random_mobile'])
        await self.spoof_mobile_fingerprint(config)

        print("绕过调试检测...")
        await self.bypass_debug_detection()

        print("隐身配置应用完成!")

    async def navigate_to_url(self, url: str) -> bool:
        """安全导航到URL - 修复 page.get() 返回列表的问题"""
        try:
            print(f"🔄 正在导航到: {url}")

            # 使用 browser.get() 而不是 page.get()
            if hasattr(self.browser, 'get'):
                result = await self.browser.get(url)
            else:
                result = await self.page.get(url)

            # 处理可能的列表返回
            if isinstance(result, list):
                if len(result) > 0:
                    # 取第一个元素作为主要页面
                    self.page = result[0]
                    print(f"✅ 导航成功，获取到 {len(result)} 个页面")
                else:
                    print("❌ 导航返回空列表")
                    return False
            else:
                # 如果是单个页面对象，直接使用
                self.page = result
                print("✅ 导航成功")

            # 等待页面加载
            await asyncio.sleep(3)
            return True

        except Exception as e:
            print(f"❌ 导航失败: {e}")
            return False

    async def _wait_for_page_load(self, timeout: int = 30):
        """等待页面加载完成"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # 简单的等待策略
                await asyncio.sleep(2)
                break

            except Exception as e:
                logging.warning(f"等待页面加载时出错: {e}")
                await asyncio.sleep(1)

    async def check_page_access(self, url: str) -> tuple[bool, str]:
        """检查页面访问是否成功 - 专门用于手动检测"""
        try:
            if not self.browser:
                return False, "浏览器未启动"

            logging.info(f"手动检测：正在访问 {url}")

            # 访问URL
            await self.browser.get(url)

            # 等待页面加载
            await self._wait_for_page_load()

            # 获取页面信息 - 使用新的API
            try:
                # 尝试获取页面标题
                page_title = await self.browser.get_title()
            except:
                page_title = "无法获取标题"

            try:
                # 尝试获取当前URL
                current_url = await self.browser.get_url()
            except:
                current_url = url  # 使用原始URL作为回退

            logging.info(f"手动检测成功：页面标题='{page_title}', URL='{current_url}'")

            # 手动检测模式下，只要页面能正常加载就认为成功
            success_message = f"页面访问成功！\n标题: {page_title}\nURL: {current_url}\n\n浏览器保持打开，请手动检查页面内容后关闭浏览器。"

            return True, success_message

        except Exception as e:
            error_message = f"页面访问失败: {str(e)}"
            logging.error(f"手动检测失败: {error_message}")
            return False, error_message

    async def find_and_click_links(self, max_links: int = 10) -> int:
        """查找并点击链接，返回点击的链接数量"""
        # 手动检测模式下不执行自动操作
        if self.is_manual_test:
            logging.info("手动检测模式：跳过自动点击链接")
            return 0

        try:
            if not self.browser:
                return 0

            # 使用新的元素查找方法
            elements = await self._find_elements_simple('a')
            clickable_links = []

            for element in elements[:max_links]:
                try:
                    if await self._is_element_visible_simple(element):
                        clickable_links.append(element)
                except:
                    continue

            if not clickable_links:
                logging.info("未找到可点击的链接")
                return 0

            # 随机选择链接点击
            click_count = min(random.randint(1, 3), len(clickable_links))
            selected_links = random.sample(clickable_links, click_count)

            clicked_count = 0
            for i, element in enumerate(selected_links):
                try:
                    # 获取链接文本
                    link_text = await self._get_element_text_simple(element)
                    display_text = link_text[:20] + "..." if len(link_text) > 20 else link_text

                    logging.info(f"点击链接 {i + 1}: {display_text}")

                    # 点击链接
                    await element.click()
                    await asyncio.sleep(random.uniform(2, 4))

                    clicked_count += 1

                    # 30%概率返回上一页
                    if random.random() < 0.3:
                        await self.browser.back()
                        await asyncio.sleep(random.uniform(1, 2))

                except Exception as e:
                    logging.error(f"点击链接失败: {e}")
                    continue

            return clicked_count

        except Exception as e:
            logging.error(f"查找点击链接失败: {e}")
            return 0

    async def _find_elements_simple(self, selector: str):
        """简化版元素查找"""
        try:
            # 使用新的元素查找API
            if hasattr(self.browser, 'find_elements'):
                return await self.browser.find_elements(selector)
            else:
                # 如果不存在，返回空列表
                logging.warning(f"元素查找方法不可用: {selector}")
                return []
        except Exception as e:
            logging.error(f"查找元素失败 {selector}: {e}")
            return []

    async def _is_element_visible_simple(self, element) -> bool:
        """简化版元素可见性检查"""
        try:
            # 简单的可见性检查
            if hasattr(element, 'is_displayed'):
                return await element.is_displayed()
            return True  # 默认认为可见
        except:
            return False

    async def _get_element_text_simple(self, element) -> str:
        """简化版获取元素文本"""
        try:
            if hasattr(element, 'text'):
                return await element.text()
            return ""  # 返回空字符串作为回退
        except:
            return ""

    async def send_message(self, message: str) -> bool:
        """发送消息"""
        # 手动检测模式下不执行自动操作
        if self.is_manual_test:
            logging.info("手动检测模式：跳过自动发送消息")
            return False

        try:
            if not self.browser:
                return False

            # 查找输入框
            input_element = await self._find_input_element_simple()
            if not input_element:
                logging.warning("未找到可用的输入框")
                return False

            # 清空输入框
            await self._clear_element_simple(input_element)

            # 模拟人工输入
            for char in message:
                await self._send_keys_simple(input_element, char)
                await asyncio.sleep(random.uniform(0.05, 0.2))

            # 发送消息
            send_success = await self._send_input_simple(input_element)

            if send_success:
                logging.info(f"消息发送成功: {message[:20]}...")
            else:
                logging.warning("消息发送失败")

            return send_success

        except Exception as e:
            logging.error(f"发送消息失败: {e}")
            return False

    async def _find_input_element_simple(self):
        """简化版查找输入框元素"""
        input_selectors = [
            'input[type="text"]',
            'textarea',
            'input[type="search"]',
        ]

        for selector in input_selectors:
            try:
                elements = await self._find_elements_simple(selector)
                for element in elements:
                    if await self._is_element_visible_simple(element):
                        return element
            except:
                continue

        return None

    async def _clear_element_simple(self, element):
        """简化版清空元素内容"""
        try:
            if hasattr(element, 'clear'):
                await element.clear()
            elif hasattr(element, 'send_keys'):
                # 使用Ctrl+A全选然后删除
                await element.send_keys('\x01')  # Ctrl+A
                await element.send_keys('\x08')  # Backspace
        except Exception as e:
            logging.error(f"清空元素失败: {e}")

    async def _send_keys_simple(self, element, text: str):
        """简化版向元素发送按键"""
        try:
            if hasattr(element, 'send_keys'):
                await element.send_keys(text)
        except Exception as e:
            logging.error(f"发送按键失败: {e}")

    async def _send_input_simple(self, input_element) -> bool:
        """简化版发送输入内容"""
        try:
            # 尝试按回车发送
            await self._send_keys_simple(input_element, '\n')
            await asyncio.sleep(random.uniform(1, 3))
            return True

        except Exception as e:
            logging.error(f"发送输入失败: {e}")
            return False

    async def random_scroll(self):
        """随机滚动页面"""
        try:
            if self.browser:
                # 使用JavaScript滚动
                scroll_amount = random.randint(100, 500)
                scroll_direction = 1 if random.random() > 0.5 else -1

                # 尝试使用JavaScript执行滚动
                try:
                    await self.browser.execute_script(f"window.scrollBy(0, {scroll_amount * scroll_direction})")
                except:
                    # 如果JavaScript执行失败，忽略错误
                    pass
        except Exception as e:
            logging.error(f"滚动页面失败: {e}")

    async def hide_cdp_protocol(self):
        """隐藏CDP协议痕迹"""
        cdp_scripts = [
            # 删除CDP相关变量
            """
            try {
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Function;

                // 删除其他自动化变量
                delete window._Selenium_IDE_Recorder;
                delete window._phantom;
                delete window.callPhantom;
                delete window.__nightmare;
                delete window._Cypress;
                delete window._nodriver;

                console.log('CDP变量删除成功');
            } catch(e) {
                console.log('CDP变量删除部分成功:', e.message);
            }
            """,

            # 隐藏自动化特征
            """
            try {
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: false
                });

                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                    configurable: false
                });

                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en-US', 'en'],
                    configurable: false
                });

                console.log('自动化特征隐藏成功');
            } catch(e) {
                console.log('自动化特征隐藏部分成功:', e.message);
            }
            """
        ]

        for i, script in enumerate(cdp_scripts):
            try:
                print(f"执行CDP隐藏脚本 {i + 1}/{len(cdp_scripts)}...")
                result = await self.safe_evaluate(script)
                if result is not None:
                    print(f"CDP隐藏脚本 {i + 1} 执行成功")
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"CDP隐藏脚本 {i + 1} 执行失败: {e}")

    async def spoof_mobile_fingerprint(self, device_config):
        """伪造移动端浏览器指纹"""
        fingerprint_scripts = [
            # 屏幕和视口信息
            f"""
            try {{
                Object.defineProperty(window, 'innerWidth', {{
                    get: () => {device_config['viewport'][0]},
                    configurable: false
                }});
                Object.defineProperty(window, 'innerHeight', {{
                    get: () => {device_config['viewport'][1]},
                    configurable: false
                }});
                console.log('视口信息设置成功');
            }} catch(e) {{
                console.log('视口信息设置失败:', e.message);
            }}
            """,

            # 设备信息
            f"""
            try {{
                Object.defineProperty(navigator, 'platform', {{
                    get: () => '{device_config['platform']}',
                    configurable: false
                }});

                Object.defineProperty(navigator, 'vendor', {{
                    get: () => '{device_config['vendor']}',
                    configurable: false
                }});

                Object.defineProperty(navigator, 'maxTouchPoints', {{
                    get: () => {device_config['touch_points']},
                    configurable: false
                }});

                console.log('设备信息设置成功');
            }} catch(e) {{
                console.log('设备信息设置失败:', e.message);
            }}
            """,

            # 硬件信息
            """
            try {
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 4,
                    configurable: false
                });

                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 6,
                    configurable: false
                });

                console.log('硬件信息设置成功');
            } catch(e) {
                console.log('硬件信息设置失败:', e.message);
            }
            """
        ]

        for i, script in enumerate(fingerprint_scripts):
            try:
                print(f"执行指纹脚本 {i + 1}/{len(fingerprint_scripts)}...")
                result = await self.safe_evaluate(script)
                if result is not None:
                    print(f"指纹脚本 {i + 1} 执行成功")
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"指纹脚本 {i + 1} 执行失败: {e}")

    async def bypass_debug_detection(self):
        """绕过调试模式检测"""
        debug_scripts = [
            # 基础调试绕过
            """
            try {
                // 覆盖console.debug
                console.debug = function(){};

                // 防止debugger暂停
                window.debugger = function(){};

                console.log('调试绕过基础设置成功');
            } catch(e) {
                console.log('调试绕过基础设置失败:', e.message);
            }
            """,

            # Function构造函数检测绕过
            """
            try {
                const originalFunctionToString = Function.prototype.toString;
                Function.prototype.toString = function() {
                    const str = originalFunctionToString.call(this);
                    if (str.includes('debugger') || str.includes('[native code]')) {
                        return 'function() { [native code] }';
                    }
                    return str;
                };
                console.log('Function检测绕过成功');
            } catch(e) {
                console.log('Function检测绕过失败:', e.message);
            }
            """
        ]

        for i, script in enumerate(debug_scripts):
            try:
                print(f"执行调试绕过脚本 {i + 1}/{len(debug_scripts)}...")
                result = await self.safe_evaluate(script)
                if result is not None:
                    print(f"调试绕过脚本 {i + 1} 执行成功")
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"调试绕过脚本 {i + 1} 执行失败: {e}")

    async def safe_evaluate(self, script, retries=3):
        """安全执行 JavaScript 脚本"""
        for attempt in range(retries):
            try:
                if self.page:
                    result = await self.page.evaluate(script)
                    return result
                else:
                    print("页面未初始化")
                    return None
            except Exception as e:
                print(f"执行脚本失败 (尝试 {attempt + 1}/{retries}): {e}")
                await asyncio.sleep(1)
        return None

    async def wait_for_page_ready(self, timeout=10):
        """等待页面准备就绪"""
        try:
            # 等待页面加载
            for i in range(timeout):
                try:
                    # 尝试执行简单脚本来检查页面是否就绪
                    result = await self.page.evaluate("1+1")
                    if result == 2:
                        print("页面准备就绪")
                        return True
                except:
                    pass
                await asyncio.sleep(1)
            return False
        except Exception as e:
            print(f"等待页面就绪时出错: {e}")
            return False