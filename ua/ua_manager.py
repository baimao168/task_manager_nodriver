import linecache
import os
import random


class OptimizedUserAgentManager:
    """优化的 User-Agent 管理器（移动端和微信完全分离）"""

    def __init__(self, ua_file_path='user_agents.txt', cache_size=1000):
        self.ua_file_path = ua_file_path
        self.cache_size = cache_size
        self.mobile_cache = []  # 纯移动端 UA（不含微信）
        self.desktop_cache = []  # 桌面端 UA
        self.wechat_cache = []  # 微信浏览器 UA
        self.all_cache = []  # 所有 UA（用于 any 类型）
        self.total_lines = 0
        self.mobile_count = 0
        self.desktop_count = 0
        self.wechat_count = 0
        self.cache_loaded = False

        # 初始化
        self.initialize_ua_system()

    def initialize_ua_system(self):
        """初始化 UA 系统"""
        try:
            if not os.path.exists(self.ua_file_path):
                print(f"⚠️  User-Agent 文件不存在，创建默认文件")
                self.create_default_ua_file()

            # 快速统计行数
            self.total_lines = self._count_file_lines()
            print(f"📊 User-Agent 文件行数: {self.total_lines}")

            if self.total_lines <= self.cache_size:
                # 文件较小，直接全量加载
                self._load_all_agents()
            else:
                # 大文件，使用缓存策略
                print(f"🔧 检测到大文件 ({self.total_lines} 行)，启用缓存模式")
                self._load_sample_to_cache()

        except Exception as e:
            print(f"❌ 初始化 User-Agent 系统失败: {e}")
            self.create_default_agents()

    def _count_file_lines(self):
        """快速统计文件行数"""
        try:
            count = 0
            with open(self.ua_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for _ in f:
                    count += 1
            return count
        except:
            return 0

    def _load_all_agents(self):
        """全量加载所有 User-Agent（确保移动端不含微信）"""
        try:
            with open(self.ua_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.all_cache.append(line)
                        if self._is_wechat_ua(line):
                            # 微信浏览器
                            self.wechat_cache.append(line)
                            self.wechat_count += 1
                        elif self._is_mobile_ua(line) and not self._is_wechat_ua(line):
                            # 纯移动端（不含微信）
                            self.mobile_cache.append(line)
                            self.mobile_count += 1
                        elif not self._is_mobile_ua(line) and not self._is_wechat_ua(line):
                            # 桌面端
                            self.desktop_cache.append(line)
                            self.desktop_count += 1

            self.cache_loaded = True
            print(f"✅ 全量加载 {len(self.all_cache)} 个 User-Agent")
            print(f"   📱 纯移动端: {len(self.mobile_cache)} 个")
            print(f"   💻 桌面端: {len(self.desktop_cache)} 个")
            print(f"   💬 微信浏览器: {len(self.wechat_cache)} 个")

        except Exception as e:
            print(f"❌ 加载 User-Agent 失败: {e}")
            self.create_default_agents()

    def _load_sample_to_cache(self):
        """加载样本到缓存（用于大文件）"""
        try:
            # 随机选择一些行加载到缓存
            sample_indices = random.sample(range(1, self.total_lines + 1),
                                           min(self.cache_size, self.total_lines))

            mobile_count = 0
            desktop_count = 0
            wechat_count = 0

            for line_num in sample_indices:
                line = linecache.getline(self.ua_file_path, line_num).strip()
                if line and not line.startswith('#'):
                    self.all_cache.append(line)
                    if self._is_wechat_ua(line):
                        self.wechat_cache.append(line)
                        wechat_count += 1
                    elif self._is_mobile_ua(line) and not self._is_wechat_ua(line):
                        self.mobile_cache.append(line)
                        mobile_count += 1
                    elif not self._is_mobile_ua(line) and not self._is_wechat_ua(line):
                        self.desktop_cache.append(line)
                        desktop_count += 1

            self.mobile_count = mobile_count
            self.desktop_count = desktop_count
            self.wechat_count = wechat_count
            self.cache_loaded = True

            print(f"✅ 缓存加载完成: {len(self.all_cache)} 个样本")
            print(f"   📱 纯移动端样本: {len(self.mobile_cache)} 个")
            print(f"   💻 桌面端样本: {len(self.desktop_cache)} 个")
            print(f"   💬 微信浏览器样本: {len(self.wechat_cache)} 个")

        except Exception as e:
            print(f"❌ 缓存加载失败: {e}")
            self.create_default_agents()

    def _is_mobile_ua(self, ua):
        """判断是否为移动端 User-Agent（不含微信）"""
        mobile_keywords = ['iphone', 'ipad', 'android', 'mobile', 'tablet']
        return any(keyword in ua.lower() for keyword in mobile_keywords)

    def _is_wechat_ua(self, ua):
        """判断是否为微信浏览器 User-Agent"""
        wechat_keywords = ['micromessenger']
        return any(keyword in ua.lower() for keyword in wechat_keywords)

    def get_random_ua(self, device_type='mobile'):
        """获取随机 User-Agent（优化版）"""
        if not self.cache_loaded:
            # 如果缓存未加载，使用默认
            return self._get_fallback_ua(device_type)

        if device_type == 'wechat' and self.wechat_cache:
            return random.choice(self.wechat_cache)
        elif device_type == 'mobile' and self.mobile_cache:
            return random.choice(self.mobile_cache)
        elif device_type == 'desktop' and self.desktop_cache:
            return random.choice(self.desktop_cache)
        elif device_type == 'any' and self.all_cache:
            return random.choice(self.all_cache)
        else:
            return self._get_fallback_ua(device_type)

    def get_random_ua_from_file(self, device_type='mobile'):
        """直接从文件随机读取 User-Agent（不加载到内存）"""
        try:
            max_attempts = 100  # 最大尝试次数
            for _ in range(max_attempts):
                # 随机选择一行
                line_num = random.randint(1, self.total_lines)
                line = linecache.getline(self.ua_file_path, line_num).strip()

                if line and not line.startswith('#'):
                    if device_type == 'wechat' and self._is_wechat_ua(line):
                        return line
                    elif device_type == 'mobile' and self._is_mobile_ua(line) and not self._is_wechat_ua(line):
                        return line
                    elif device_type == 'desktop' and not self._is_mobile_ua(line) and not self._is_wechat_ua(line):
                        return line
                    elif device_type == 'any':
                        return line

            # 如果没找到合适的，回退到缓存
            return self.get_random_ua(device_type)

        except Exception as e:
            print(f"❌ 从文件读取 User-Agent 失败: {e}")
            return self.get_random_ua(device_type)

    def _get_fallback_ua(self, device_type):
        """获取备用 User-Agent"""
        fallback_agents = {
            'mobile': [
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
            ],
            'desktop': [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
            ],
            'wechat': [
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.42(0x18002a29) NetType/WIFI Language/zh_CN',
                'Mozilla/5.0 (Linux; Android 13; SM-G991B Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/119.0.6045.193 Mobile Safari/537.36 MicroMessenger/8.0.42(0x18002a29) WeChat/arm64 Weixin Android Tablet NetType/WIFI Language/zh_CN'
            ]
        }

        if device_type in fallback_agents:
            return random.choice(fallback_agents[device_type])
        else:
            return fallback_agents['mobile'][0]

    def create_default_ua_file(self):
        """创建默认 User-Agent 文件（移动端和微信完全分离）"""
        default_agents = self._get_default_agents()
        try:
            with open(self.ua_file_path, 'w', encoding='utf-8') as f:
                f.write("# User-Agent 数据库\n")
                f.write("# 移动端和微信浏览器完全分离存储\n")
                f.write("# 每行一个 User-Agent\n\n")

                # 写入纯移动端（不含微信）
                f.write("# 纯移动端 User-Agents (不含微信)\n")
                for ua in default_agents['mobile']:
                    f.write(f"{ua}\n")

                # 写入微信浏览器
                f.write("\n# 微信浏览器 User-Agents (MicroMessenger)\n")
                for ua in default_agents['wechat']:
                    f.write(f"{ua}\n")

                # 写入桌面端
                f.write("\n# 桌面端 User-Agents\n")
                for ua in default_agents['desktop']:
                    f.write(f"{ua}\n")

            print(f"✅ 已创建默认 User-Agent 文件: {self.ua_file_path}")
            total_lines = len(default_agents['mobile']) + len(default_agents['wechat']) + len(
                default_agents['desktop']) + 6
            self.total_lines = total_lines

        except Exception as e:
            print(f"❌ 创建 User-Agent 文件失败: {e}")

    def _get_default_agents(self):
        """获取默认的 User-Agent 列表（移动端和微信完全分离）"""
        return {
            'mobile': [
                # iPhone Safari
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 15_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.7 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1',

                # Android Chrome
                'Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; SM-S926B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; SM-G996B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36',

                # Google Pixel
                'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',

                # 小米
                'Mozilla/5.0 (Linux; Android 14; 2211133G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; 2211133C) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; 2201123G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; 2201123C) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',

                # 华为
                'Mozilla/5.0 (Linux; Android 13; LNA-AL00) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; MNA-AL00) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',

                # iPad
                'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPad; CPU OS 15_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.7 Mobile/15E148 Safari/604.1',

                # OPPO
                'Mozilla/5.0 (Linux; Android 13; PGFM10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; PHU110) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',

                # Vivo
                'Mozilla/5.0 (Linux; Android 14; V2309) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; V2166A) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36'
            ],
            'wechat': [
                # iPhone 微信
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.42(0x18002a29) NetType/WIFI Language/zh_CN',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.40(0x18002831) NetType/WIFI Language/zh_CN',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 15_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.38(0x18002621) NetType/WIFI Language/zh_CN',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.37(0x18002529) NetType/WIFI Language/zh_CN',

                # Android 微信
                'Mozilla/5.0 (Linux; Android 13; SM-G991B Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/119.0.6045.193 Mobile Safari/537.36 MicroMessenger/8.0.42(0x18002a29) WeChat/arm64 Weixin Android Tablet NetType/WIFI Language/zh_CN',
                'Mozilla/5.0 (Linux; Android 14; SM-S911B Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.210 Mobile Safari/537.36 MicroMessenger/8.0.43(0x18002b31) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN',
                'Mozilla/5.0 (Linux; Android 13; 2201123C Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/119.0.6045.193 Mobile Safari/537.36 MicroMessenger/8.0.41(0x18002921) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN',
                'Mozilla/5.0 (Linux; Android 14; 2211133G Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.210 Mobile Safari/537.36 MicroMessenger/8.0.43(0x18002b31) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN',

                # iPad 微信
                'Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.41(0x18002921) NetType/WIFI Language/zh_CN',
                'Mozilla/5.0 (iPad; CPU OS 15_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.39(0x18002729) NetType/WIFI Language/zh_CN',
                'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.43(0x18002b31) NetType/WIFI Language/zh_CN',

                # 其他 Android 设备微信
                'Mozilla/5.0 (Linux; Android 13; Pixel 7 Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/119.0.6045.193 Mobile Safari/537.36 MicroMessenger/8.0.42(0x18002a29) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN',
                'Mozilla/5.0 (Linux; Android 12; M2101K7AG Build/RKQ1.200826.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/118.0.0.0 Mobile Safari/537.36 MicroMessenger/8.0.40(0x18002831) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN',
                'Mozilla/5.0 (Linux; Android 13; LNA-AL00 Build/HONORLNA-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/119.0.6045.193 Mobile Safari/537.36 MicroMessenger/8.0.42(0x18002a29) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN'
            ],
            'desktop': [
                # Windows Chrome
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',

                # Mac Chrome
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',

                # Windows Firefox
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0',

                # Mac Safari
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6.1 Safari/605.1.15',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',

                # Linux
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0'
            ]
        }

    def create_default_agents(self):
        """创建默认的 User-Agent 缓存"""
        default_agents = self._get_default_agents()
        self.mobile_cache = default_agents['mobile']
        self.wechat_cache = default_agents['wechat']
        self.desktop_cache = default_agents['desktop']
        self.all_cache = self.mobile_cache + self.wechat_cache + self.desktop_cache
        self.mobile_count = len(self.mobile_cache)
        self.wechat_count = len(self.wechat_cache)
        self.desktop_count = len(self.desktop_cache)
        self.cache_loaded = True
        print("✅ 使用默认 User-Agent 缓存")

    def get_ua_stats(self):
        """获取 User-Agent 统计信息"""
        return {
            'total_lines': self.total_lines,
            'cache_size': len(self.all_cache),
            'mobile_count': self.mobile_count,
            'desktop_count': self.desktop_count,
            'wechat_count': self.wechat_count,
            'cache_loaded': self.cache_loaded
        }

    def add_user_agent(self, user_agent, device_type='auto'):
        """添加 User-Agent 到文件"""
        try:
            # 追加到文件
            with open(self.ua_file_path, 'a', encoding='utf-8') as f:
                f.write(f"{user_agent}\n")

            # 更新统计
            self.total_lines += 1

            # 如果缓存已加载，也添加到缓存
            if self.cache_loaded and len(self.all_cache) < self.cache_size:
                self.all_cache.append(user_agent)
                if device_type == 'wechat' or (device_type == 'auto' and self._is_wechat_ua(user_agent)):
                    self.wechat_cache.append(user_agent)
                    self.wechat_count += 1
                elif device_type == 'mobile' or (
                        device_type == 'auto' and self._is_mobile_ua(user_agent) and not self._is_wechat_ua(
                        user_agent)):
                    self.mobile_cache.append(user_agent)
                    self.mobile_count += 1
                else:
                    self.desktop_cache.append(user_agent)
                    self.desktop_count += 1

            print(f"✅ 已添加 User-Agent，文件总行数: {self.total_lines}")
            return True

        except Exception as e:
            print(f"❌ 添加 User-Agent 失败: {e}")
            return False
