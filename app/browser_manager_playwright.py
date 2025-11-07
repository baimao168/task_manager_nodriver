# browser_manager_playwright.py
import logging
import random
import asyncio
from typing import Dict, Any
from playwright.async_api import async_playwright

from proxy.config import Config
from proxy.proxy_manager import ProxyManager
from ua.ua_manager import OptimizedUserAgentManager
from utils.nodriver_result_parser import NodriverResultParser

# 初始化管理器
proxy_manager = ProxyManager(Config.PROXY_POOLS)


class PlaywrightBrowserManager:
    """Playwright 浏览器管理器 - 用于自动任务"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.browser = None
        self.context = None
        self.page = None
        self.is_running = False
        self.result_parser = NodriverResultParser()
        self.ua_manager = OptimizedUserAgentManager()
        self.current_ua = None
        self.use_file_reading = None
        self.current_device_type = None
        self.current_network_type = None
        self.stats_manager = None
        self.config_manager = None

        # 设备配置库
        self.device_profiles = {
            'android': {
                'viewport': random.choice([(360, 800), (412, 915), (393, 851)]),
                'device_scale_factor': random.choice([2.0, 2.625, 2.75]),
                'platform': random.choice(['Linux armv8l', 'Linux aarch64']),
                'vendor': random.choice(['Google Inc.', 'Samsung']),
                'touch_points': 5,
                'user_agent': ''
            },
            'ios': {
                'viewport': random.choice([(390, 844), (414, 896), (375, 812)]),
                'device_scale_factor': random.choice([2.0, 3.0]),
                'platform': 'iPhone',
                'vendor': 'Apple Computer, Inc.',
                'touch_points': 5,
                'user_agent': ''
            }
        }

    async def start_browser(self, device='mobile', is_manual_test: bool = False, use_file_reading=None,
                            config_manager=None, stats_manager=None):
        """启动 Playwright 浏览器"""
        self.is_manual_test = is_manual_test
        self.config_manager = config_manager
        self.stats_manager = stats_manager

        # 根据配置比例选择设备类型
        if config_manager:
            self.current_device_type = config_manager.get_device_type_by_ratio()
        else:
            android_ratio = self.config.get('android_ratio', 50)
            self.current_device_type = 'android' if random.randint(1, 100) <= android_ratio else 'ios'

        # 根据配置比例选择网络类型
        if config_manager:
            self.current_network_type = config_manager.get_network_type_by_ratio()
        else:
            mobile_data_ratio = self.config.get('mobile_data_ratio', 50)
            self.current_network_type = 'mobile_data' if random.randint(1, 100) <= mobile_data_ratio else 'wifi'

        print(
            f"🔧 Playwright - 选择的设备类型: {self.current_device_type.upper()}, 网络类型: {self.current_network_type.upper()}")

        # 获取设备配置
        device_config = self.device_profiles.get(self.current_device_type, self.device_profiles['android'])

        # 获取UA
        if use_file_reading is None:
            stats = self.ua_manager.get_ua_stats()
            self.use_file_reading = stats['total_lines'] > 1000

        if self.use_file_reading:
            self.current_ua = self.ua_manager.get_random_ua_from_file(device, self.current_device_type)
        else:
            self.current_ua = self.ua_manager.get_random_ua(device, self.current_device_type)

        # 验证UA
        if not self.current_ua:
            print("❌ 无法获取User-Agent，使用备用UA")
            self.current_ua = self.ua_manager._get_fallback_ua('mobile', self.current_device_type)

        device_config['user_agent'] = self.current_ua
        logging.info(f"Playwright 使用UA: {self.current_ua}")

        try:
            # 启动 Playwright
            self.playwright = await async_playwright().start()

            # 配置浏览器启动参数
            launch_options = {
                'headless': self.config.get('headless_mode', False),
                'args': [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=TranslateUI,VizDisplayCompositor',
                    '--disable-ipc-flooding-protection',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-background-timer-throttling',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-default-apps',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-translate',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-background-networking',
                    '--disable-sync',
                    '--metrics-recording-only',
                    '--safebrowsing-disable-auto-update',
                    '--remote-debugging-port=0',
                    '--disable-remote-fonts',
                    '--disable-logging',
                    '--disable-crash-reporter',
                    '--hide-scrollbars',
                    '--disable-web-security',
                    '--disable-popup-blocking',
                    '--disable-hang-monitor',
                    '--disable-client-side-phishing-detection',
                ]
            }

            # 代理配置
            try:
                proxy_config = proxy_manager.get_valid_proxy(None,
                                                             True if self.current_network_type == 'mobile_data' else False)
                proxy_url = f"{proxy_config['ip']}:{proxy_config['port']}"
                launch_options['proxy'] = {
                    'server': f"http://{proxy_url}",
                    'bypass': '<-loopback>'
                }
                print(f"代理ip: {proxy_config['http']}")
            except Exception as e:
                print("代理获取失败，使用无代理模式")

            # 启动浏览器
            self.browser = await self.playwright.chromium.launch(**launch_options)

            # 创建上下文
            context_options = {
                'user_agent': self.current_ua,
                'viewport': device_config['viewport'],
                'device_scale_factor': device_config['device_scale_factor'],
                'has_touch': True,
                'is_mobile': True
            }

            self.context = await self.browser.new_context(**context_options)

            # 应用隐身配置
            await self.apply_complete_stealth(device_config)

            # 创建页面
            self.page = await self.context.new_page()

            self.is_running = True
            logging.info("Playwright 浏览器启动成功")
            return True

        except Exception as e:
            logging.error(f"Playwright 浏览器启动失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def apply_complete_stealth(self, device_config):
        """应用完整的隐身配置"""
        print("=" * 50)
        print("Playwright - 开始应用完整隐身配置")
        print("=" * 50)

        # 添加初始化脚本到上下文
        await self.context.add_init_script("""
            // 基础CDP变量清理
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Function;

            delete window._Selenium_IDE_Recorder;
            delete window._phantom;
            delete window.callPhantom;
            delete window.__nightmare;
            delete window._Cypress;
        """)

        # 应用各种隐身脚本
        await self.hide_cdp_protocol()
        await self.spoof_mobile_fingerprint(device_config)
        await self.bypass_debug_detection()
        await self.bypass_crc_detection()
        await self.bypass_protocol_detection()

        print("Playwright 隐身配置应用完成!")

    async def hide_cdp_protocol(self):
        """隐藏CDP协议痕迹"""
        script = """
        // 隐藏webdriver属性
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: false
        });

        // 伪造插件信息
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
            configurable: false
        });

        // 伪造语言信息
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en-US', 'en'],
            configurable: false
        });
        """
        await self.context.add_init_script(script)

    async def spoof_mobile_fingerprint(self, device_config):
        """伪造移动端浏览器指纹"""
        script = f"""
        // 屏幕和视口信息
        Object.defineProperty(window, 'innerWidth', {{
            get: () => {device_config['viewport'][0]},
            configurable: false
        }});
        Object.defineProperty(window, 'innerHeight', {{
            get: () => {device_config['viewport'][1]},
            configurable: false
        }});

        // 设备信息
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

        // 硬件信息
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => 4,
            configurable: false
        }});

        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => 6,
            configurable: false
        }});
        """
        await self.context.add_init_script(script)

    async def bypass_debug_detection(self):
        """绕过调试模式检测"""
        script = """
        // 覆盖console.debug
        console.debug = function(){};

        // 防止debugger暂停
        window.debugger = function(){};

        // Function构造函数检测绕过
        const originalFunctionToString = Function.prototype.toString;
        Function.prototype.toString = function() {
            const str = originalFunctionToString.call(this);
            if (str.includes('debugger') || str.includes('[native code]')) {
                return 'function() { [native code] }';
            }
            return str;
        };
        """
        await self.context.add_init_script(script)

    async def bypass_crc_detection(self):
        """绕过Chrome运行时检查(CRC)"""
        script = """
        // 覆盖Chrome运行时属性
        if (window.chrome && window.chrome.runtime) {
            Object.defineProperty(window.chrome.runtime, 'sendMessage', {
                value: function() { return Promise.resolve({}); },
                configurable: false,
                writable: false
            });

            Object.defineProperty(window.chrome.runtime, 'onMessage', {
                value: { addListener: function() {} },
                configurable: false,
                writable: false
            });
        }

        // 覆盖性能时间戳
        if (window.performance && window.performance.timing) {
            const baseTime = Date.now() - Math.floor(Math.random() * 10000);
            const timingProps = ['navigationStart', 'unloadEventStart', 'unloadEventEnd', 'redirectStart', 'redirectEnd'];

            for (const prop of timingProps) {
                Object.defineProperty(window.performance.timing, prop, {
                    get: function() {
                        return baseTime + Math.floor(Math.random() * 1000);
                    },
                    configurable: false
                });
            }
        }
        """
        await self.context.add_init_script(script)

    async def bypass_protocol_detection(self):
        """绕过各种协议检测"""
        script = """
        // WebRTC泄漏防护
        const originalRTCPeerConnection = window.RTCPeerConnection;
        if (originalRTCPeerConnection) {
            window.RTCPeerConnection = function(config) {
                if (config && config.iceServers) {
                    config.iceServers = config.iceServers.filter(server => {
                        return server.urls && 
                               !server.urls.some(url => url.includes('google') || 
                                                      url.includes('mozilla') ||
                                                      url.includes('local'));
                    });
                }
                return new originalRTCPeerConnection(config);
            };
            window.RTCPeerConnection.prototype = originalRTCPeerConnection.prototype;
        }

        // Canvas指纹防护
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
            const context = this.getContext('2d');
            if (context) {
                const imageData = context.getImageData(0, 0, this.width, this.height);
                const data = imageData.data;
                for (let i = 0; i < data.length; i += Math.floor(Math.random() * 100) + 50) {
                    data[i] = data[i] ^ (Math.random() > 0.5 ? 1 : 0);
                }
                context.putImageData(imageData, 0, 0);
            }
            return originalToDataURL.call(this, type, quality);
        };

        // 字体列表随机化
        Object.defineProperty(navigator, 'fonts', {
            value: {
                ready: Promise.resolve(),
                query: function() {
                    return Promise.resolve([
                        { family: 'Arial', status: 'loaded' },
                        { family: 'Helvetica', status: 'loaded' },
                        { family: 'Times New Roman', status: 'loaded' }
                    ].sort(() => Math.random() - 0.5));
                }
            },
            configurable: false,
            writable: false
        });
        """
        await self.context.add_init_script(script)

    async def take_screenshot(self, url, config_manager=None, stats_manager=None):
        """访问URL并返回成功状态"""
        try:
            print(f"🌐 Playwright - 访问: {url}")

            # 导航到URL
            await self.page.goto(url, wait_until='networkidle', timeout=30000)

            # 等待页面加载
            await self.page.wait_for_timeout(3000)

            # 检查页面内容
            title = await self.page.title()
            content = await self.page.content()

            if content and len(content) > 0:
                print(f"✓ Playwright - 访问成功")
                print(f"  标题: {title}")
                print(f"  内容长度: {len(content)}")

                # 更新统计数据
                if stats_manager and self.current_device_type and self.current_network_type:
                    stats_manager.update_stats(True, self.current_device_type, self.current_network_type)

                return True, self.current_device_type, self.current_network_type
            else:
                print(f"✗ Playwright - 访问失败: 页面内容为空")

                if stats_manager and self.current_device_type and self.current_network_type:
                    stats_manager.update_stats(False, self.current_device_type, self.current_network_type)

                return False, self.current_device_type, self.current_network_type

        except Exception as e:
            print(f"✗ Playwright - 访问失败: {e}")

            if stats_manager and self.current_device_type and self.current_network_type:
                stats_manager.update_stats(False, self.current_device_type, self.current_network_type)

            return False, self.current_device_type, self.current_network_type

    async def find_and_click_links(self, max_links: int = 10) -> int:
        """查找并点击链接"""
        if self.is_manual_test:
            logging.info("手动检测模式：跳过自动点击链接")
            return 0

        try:
            # 查找所有链接
            links = await self.page.query_selector_all('a')
            clickable_links = []

            for link in links[:max_links]:
                try:
                    if await link.is_visible():
                        clickable_links.append(link)
                except:
                    continue

            if not clickable_links:
                logging.info("未找到可点击的链接")
                return 0

            # 随机选择链接点击
            click_count = min(random.randint(1, 3), len(clickable_links))
            selected_links = random.sample(clickable_links, click_count)

            clicked_count = 0
            for i, link in enumerate(selected_links):
                try:
                    link_text = await link.text_content() or ""
                    display_text = link_text[:20] + "..." if len(link_text) > 20 else link_text

                    logging.info(f"点击链接 {i + 1}: {display_text}")

                    await link.click()
                    await self.page.wait_for_timeout(random.randint(2000, 4000))

                    clicked_count += 1

                    # 30%概率返回上一页
                    if random.random() < 0.3:
                        await self.page.go_back()
                        await self.page.wait_for_timeout(random.randint(1000, 2000))

                except Exception as e:
                    logging.error(f"点击链接失败: {e}")
                    continue

            return clicked_count

        except Exception as e:
            logging.error(f"查找点击链接失败: {e}")
            return 0

    async def send_message(self, message: str) -> bool:
        """发送消息"""
        if self.is_manual_test:
            logging.info("手动检测模式：跳过自动发送消息")
            return False

        try:
            # 查找输入框
            input_selectors = ['input[type="text"]', 'textarea', 'input[type="search"]']
            input_element = None

            for selector in input_selectors:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        input_element = element
                        break
                if input_element:
                    break

            if not input_element:
                logging.warning("未找到可用的输入框")
                return False

            # 清空输入框
            await input_element.click()
            await self.page.keyboard.press('Control+A')
            await self.page.keyboard.press('Backspace')

            # 模拟人工输入
            await input_element.type(message, delay=random.randint(50, 200))

            # 发送消息（按回车）
            await self.page.keyboard.press('Enter')
            await self.page.wait_for_timeout(random.randint(1000, 3000))

            logging.info(f"消息发送成功: {message[:20]}...")
            return True

        except Exception as e:
            logging.error(f"发送消息失败: {e}")
            return False

    async def random_scroll(self):
        """随机滚动页面"""
        try:
            scroll_amount = random.randint(100, 500)
            scroll_direction = 1 if random.random() > 0.5 else -1

            await self.page.evaluate(f"window.scrollBy(0, {scroll_amount * scroll_direction})")
        except Exception as e:
            logging.error(f"滚动页面失败: {e}")

    async def close_browser(self):
        """关闭浏览器"""
        try:
            if self.is_manual_test:
                logging.info("手动检测模式：浏览器保持打开")
                return

            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()

            self.is_running = False
            logging.info("Playwright 浏览器已关闭")
        except Exception as e:
            logging.error(f"关闭 Playwright 浏览器失败: {e}")

    def get_current_device_type(self):
        """获取当前设备类型"""
        return self.current_device_type

    def get_current_network_type(self):
        """获取当前网络类型"""
        return self.current_network_type