import linecache
import os
import random
import time
import hashlib


class OptimizedUserAgentManager:
    """优化的 User-Agent 管理器（修复设备类型匹配问题）"""

    def __init__(self, ua_file_path='user_agents.txt', cache_size=1000):
        self.ua_file_path = ua_file_path
        self.cache_size = cache_size

        # 分类缓存
        self.mobile_android_cache = []
        self.mobile_ios_cache = []
        self.wechat_android_cache = []
        self.wechat_ios_cache = []
        self.desktop_cache = []
        self.all_cache = []

        # 统计信息
        self.total_lines = 0
        self.mobile_android_count = 0
        self.mobile_ios_count = 0
        self.wechat_android_count = 0
        self.wechat_ios_count = 0
        self.desktop_count = 0

        self.cache_loaded = False
        self.last_refresh_time = 0
        self.cache_ttl = 300

        # 设备类型比例配置
        self.device_ratios = {
            'android': 50,  # 安卓比例
            'ios': 50  # iOS比例
        }

        # 选择历史记录，避免重复
        self.selection_history = []
        self.max_history_size = 50

        # 初始化
        self.initialize_ua_system()

    def set_device_ratios(self, android_ratio: int, ios_ratio: int):
        """设置设备类型比例"""
        if android_ratio + ios_ratio == 100:
            self.device_ratios = {
                'android': android_ratio,
                'ios': ios_ratio
            }
            print(f"✅ 设备比例设置: Android {android_ratio}%, iOS {ios_ratio}%")
        else:
            print("❌ 设备比例总和必须为100%")

    def _should_refresh_cache(self):
        """检查是否需要刷新缓存"""
        current_time = time.time()
        if not self.cache_loaded:
            return True
        if current_time - self.last_refresh_time > self.cache_ttl:
            return True
        return False

    def refresh_cache_if_needed(self):
        """如果需要则刷新缓存"""
        if self._should_refresh_cache():
            print("🔄 刷新UA缓存...")
            old_cache_size = len(self.all_cache)
            self.initialize_ua_system()
            self.last_refresh_time = time.time()
            new_cache_size = len(self.all_cache)
            print(f"🔄 缓存刷新完成: {old_cache_size} -> {new_cache_size} 个UA")

    def initialize_ua_system(self):
        """初始化 UA 系统"""
        try:
            if not os.path.exists(self.ua_file_path):
                print(f"⚠️ User-Agent 文件不存在，创建默认文件")
                self.create_default_ua_file()

            # 清空现有缓存
            self.mobile_android_cache = []
            self.mobile_ios_cache = []
            self.wechat_android_cache = []
            self.wechat_ios_cache = []
            self.desktop_cache = []
            self.all_cache = []
            self.selection_history = []

            # 快速统计行数
            self.total_lines = self._count_file_lines()
            print(f"📊 User-Agent 文件行数: {self.total_lines}")

            if self.total_lines <= self.cache_size:
                self._load_all_agents()
            else:
                print(f"🔧 检测到大文件 ({self.total_lines} 行)，启用缓存模式")
                self._load_sample_to_cache()

            # 彻底打乱所有缓存
            self._shuffle_all_caches()

            self.cache_loaded = True
            print(f"✅ UA系统初始化完成，总缓存数: {len(self.all_cache)}")

        except Exception as e:
            print(f"❌ 初始化 User-Agent 系统失败: {e}")
            self.create_default_agents()

    def _shuffle_all_caches(self):
        """彻底打乱所有缓存"""
        random.shuffle(self.mobile_android_cache)
        random.shuffle(self.mobile_ios_cache)
        random.shuffle(self.wechat_android_cache)
        random.shuffle(self.wechat_ios_cache)
        random.shuffle(self.desktop_cache)
        random.shuffle(self.all_cache)
        print("🔀 所有缓存彻底随机化完成")

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
        """全量加载所有 User-Agent（精确分类）"""
        try:
            loaded_count = 0
            with open(self.ua_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        loaded_count += 1
                        self.all_cache.append(line)

                        # 精确分类 - 修复逻辑
                        if self._is_wechat_ua(line):
                            if self._is_android_ua(line):
                                self.wechat_android_cache.append(line)
                                self.wechat_android_count += 1
                            elif self._is_ios_ua(line):
                                self.wechat_ios_cache.append(line)
                                self.wechat_ios_count += 1
                            # 微信UA不进入移动端缓存
                        elif self._is_mobile_ua(line):
                            if self._is_android_ua(line):
                                self.mobile_android_cache.append(line)
                                self.mobile_android_count += 1
                            elif self._is_ios_ua(line):
                                self.mobile_ios_cache.append(line)
                                self.mobile_ios_count += 1
                        else:
                            # 既不是移动端也不是微信，就是桌面端
                            self.desktop_cache.append(line)
                            self.desktop_count += 1

            print(f"✅ 全量加载 {loaded_count} 个 User-Agent")
            print(f"   📱 安卓移动端: {len(self.mobile_android_cache)} 个")
            print(f"   📱 iOS移动端: {len(self.mobile_ios_cache)} 个")
            print(f"   💬 安卓微信: {len(self.wechat_android_cache)} 个")
            print(f"   💬 iOS微信: {len(self.wechat_ios_cache)} 个")
            print(f"   💻 桌面端: {len(self.desktop_cache)} 个")

        except Exception as e:
            print(f"❌ 加载 User-Agent 失败: {e}")
            self.create_default_agents()

    def _load_sample_to_cache(self):
        """加载样本到缓存（用于大文件）"""
        try:
            sample_indices = random.sample(range(1, self.total_lines + 1),
                                           min(self.cache_size, self.total_lines))

            for line_num in sample_indices:
                line = linecache.getline(self.ua_file_path, line_num).strip()
                if line and not line.startswith('#'):
                    self.all_cache.append(line)

                    # 使用相同的分类逻辑
                    if self._is_wechat_ua(line):
                        if self._is_android_ua(line):
                            self.wechat_android_cache.append(line)
                        elif self._is_ios_ua(line):
                            self.wechat_ios_cache.append(line)
                    elif self._is_mobile_ua(line):
                        if self._is_android_ua(line):
                            self.mobile_android_cache.append(line)
                        elif self._is_ios_ua(line):
                            self.mobile_ios_cache.append(line)
                    else:
                        self.desktop_cache.append(line)

            # 更新统计
            self.mobile_android_count = len(self.mobile_android_cache)
            self.mobile_ios_count = len(self.mobile_ios_cache)
            self.wechat_android_count = len(self.wechat_android_cache)
            self.wechat_ios_count = len(self.wechat_ios_cache)
            self.desktop_count = len(self.desktop_cache)

            print(f"✅ 缓存加载完成: {len(self.all_cache)} 个样本")
            print(f"   📱 安卓移动端样本: {len(self.mobile_android_cache)} 个")
            print(f"   📱 iOS移动端样本: {len(self.mobile_ios_cache)} 个")
            print(f"   💬 安卓微信样本: {len(self.wechat_android_cache)} 个")
            print(f"   💬 iOS微信样本: {len(self.wechat_ios_cache)} 个")
            print(f"   💻 桌面端样本: {len(self.desktop_cache)} 个")

        except Exception as e:
            print(f"❌ 缓存加载失败: {e}")
            self.create_default_agents()

    def _is_mobile_ua(self, ua):
        """判断是否为移动端 User-Agent（不含微信）"""
        ua_lower = ua.lower()
        mobile_keywords = ['iphone', 'ipad', 'android', 'mobile', 'tablet']
        wechat_keywords = ['micromessenger']

        # 是移动设备且不是微信
        is_mobile = any(keyword in ua_lower for keyword in mobile_keywords)
        is_wechat = any(keyword in ua_lower for keyword in wechat_keywords)

        return is_mobile and not is_wechat

    def _is_wechat_ua(self, ua):
        """判断是否为微信浏览器 User-Agent"""
        wechat_keywords = ['micromessenger']
        return any(keyword in ua.lower() for keyword in wechat_keywords)

    def _is_android_ua(self, ua):
        """判断是否为安卓设备"""
        ua_lower = ua.lower()
        return ('android' in ua_lower and
                'iphone' not in ua_lower and
                'ipad' not in ua_lower)

    def _is_ios_ua(self, ua):
        """判断是否为iOS设备"""
        ua_lower = ua.lower()
        return (('iphone' in ua_lower or 'ipad' in ua_lower) and
                'android' not in ua_lower)

    def _is_desktop_ua(self, ua):
        """判断是否为桌面端 User-Agent"""
        ua_lower = ua.lower()
        desktop_keywords = ['windows', 'macintosh', 'x11', 'linux']
        mobile_keywords = ['iphone', 'ipad', 'android', 'mobile', 'tablet']

        # 包含桌面关键词且不包含移动关键词
        has_desktop = any(keyword in ua_lower for keyword in desktop_keywords)
        has_mobile = any(keyword in ua_lower for keyword in mobile_keywords)

        return has_desktop and not has_mobile

    def _select_cache_pool(self, device_type, os_type):
        """根据设备类型和操作系统选择缓存池 - 修复版本"""
        cache_pools = {
            'mobile': {
                'android': self.mobile_android_cache,
                'ios': self.mobile_ios_cache,
                'any': self.mobile_android_cache + self.mobile_ios_cache
            },
            'wechat': {
                'android': self.wechat_android_cache,
                'ios': self.wechat_ios_cache,
                'any': self.wechat_android_cache + self.wechat_ios_cache
            },
            'desktop': {
                'any': self.desktop_cache
            },
            'any': {
                'android': self.mobile_android_cache + self.wechat_android_cache,
                'ios': self.mobile_ios_cache + self.wechat_ios_cache,
                'any': self.all_cache
            }
        }

        # 严格按参数选择，不自动回退到其他类型
        if device_type in cache_pools:
            device_pool = cache_pools[device_type]
            if os_type in device_pool:
                pool = device_pool[os_type]
                if pool and len(pool) > 0:
                    print(f"🎯 选择缓存池: {device_type}.{os_type}, 数量: {len(pool)}")
                    return pool

        print(f"⚠️ 未找到匹配的缓存池: {device_type}.{os_type}")
        return None

    def _avoid_recent_selection(self, pool, max_attempts=10):
        """避免最近选择过的UA"""
        if not pool or len(pool) <= 1:
            return random.choice(pool) if pool else None

        for attempt in range(max_attempts):
            selected_ua = random.choice(pool)
            ua_hash = hashlib.md5(selected_ua.encode()).hexdigest()

            if ua_hash not in self.selection_history:
                # 添加到历史记录
                self.selection_history.append(ua_hash)
                # 保持历史记录大小
                if len(self.selection_history) > self.max_history_size:
                    self.selection_history.pop(0)
                return selected_ua

        # 如果所有尝试都失败，返回随机一个并清空历史
        self.selection_history.clear()
        return random.choice(pool)

    def get_random_ua(self, device_type='mobile', os_type='any'):
        """获取随机 User-Agent - 严格按参数匹配"""
        self.refresh_cache_if_needed()

        if not self.cache_loaded:
            print("⚠️ 缓存未加载，使用备用UA")
            return self._get_fallback_ua(device_type, os_type)

        print(f"🔍 请求UA - 设备: {device_type}, 系统: {os_type}")

        # 严格按参数选择缓存池
        cache_pool = self._select_cache_pool(device_type, os_type)

        if not cache_pool:
            print(f"❌ {device_type}.{os_type} 类型缓存为空，使用备用UA")
            return self._get_fallback_ua(device_type, os_type)

        # 避免重复选择
        selected_ua = self._avoid_recent_selection(cache_pool)

        if selected_ua:
            # 验证选择的UA是否符合要求
            is_valid = self._validate_ua_match(selected_ua, device_type, os_type)
            if not is_valid:
                print(f"⚠️ 选择的UA不匹配要求，重新选择")
                # 从缓存池中移除这个无效的UA
                if selected_ua in cache_pool:
                    cache_pool.remove(selected_ua)
                # 重新选择
                selected_ua = self._avoid_recent_selection(cache_pool)

            if selected_ua:
                # 最终验证
                detected_device = self._detect_device_type(selected_ua)
                detected_os = self._detect_os_type(selected_ua)

                print(f"✅ 最终选择:")
                print(f"   要求: {device_type}.{os_type}")
                print(f"   实际: {detected_device}.{detected_os}")
                print(f"   UA: {selected_ua[:80]}...")

                return selected_ua

        print("❌ 无法选择有效的UA，使用备用")
        return self._get_fallback_ua(device_type, os_type)

    def _validate_ua_match(self, ua, device_type, os_type):
        """验证UA是否匹配要求的设备类型和操作系统"""
        ua_lower = ua.lower()

        # 验证设备类型
        if device_type == 'mobile':
            if not self._is_mobile_ua(ua):
                return False
        elif device_type == 'wechat':
            if not self._is_wechat_ua(ua):
                return False
        elif device_type == 'desktop':
            if not self._is_desktop_ua(ua):
                return False

        # 验证操作系统
        if os_type == 'android':
            if not self._is_android_ua(ua):
                return False
        elif os_type == 'ios':
            if not self._is_ios_ua(ua):
                return False

        return True

    def _detect_device_type(self, ua):
        """检测UA的设备类型"""
        if self._is_wechat_ua(ua):
            return 'wechat'
        elif self._is_mobile_ua(ua):
            return 'mobile'
        elif self._is_desktop_ua(ua):
            return 'desktop'
        else:
            return 'unknown'

    def _detect_os_type(self, ua):
        """检测UA的操作系统类型"""
        if self._is_android_ua(ua):
            return 'android'
        elif self._is_ios_ua(ua):
            return 'ios'
        else:
            return 'other'

    def get_random_ua_from_file(self, device_type='mobile', os_type='any'):
        """直接从文件随机读取 User-Agent - 严格匹配"""
        try:
            new_line_count = self._count_file_lines()
            if new_line_count != self.total_lines:
                print(f"🔄 检测到UA文件变化，重新统计行数: {self.total_lines} -> {new_line_count}")
                self.total_lines = new_line_count

            max_attempts = 100
            found_agents = []

            print(f"🔍 从文件查找UA - 设备: {device_type}, 系统: {os_type}")

            for attempt in range(max_attempts):
                line_num = random.randint(1, self.total_lines)
                line = linecache.getline(self.ua_file_path, line_num).strip()

                if line and not line.startswith('#'):
                    # 严格匹配设备类型和操作系统
                    if self._validate_ua_match(line, device_type, os_type):
                        found_agents.append(line)

                    # 如果找到足够多的UA，提前返回
                    if len(found_agents) >= 5:
                        break

            if found_agents:
                selected_ua = self._avoid_recent_selection(found_agents)
                if selected_ua:
                    detected_device = self._detect_device_type(selected_ua)
                    detected_os = self._detect_os_type(selected_ua)
                    print(f"📁 从文件选择的UA (找到 {len(found_agents)} 个): {detected_device}.{detected_os}")
                    return selected_ua

            print(f"❌ 文件读取未找到匹配 {device_type}.{os_type} 的UA，回退到缓存")
            return self.get_random_ua(device_type, os_type)

        except Exception as e:
            print(f"❌ 从文件读取 User-Agent 失败: {e}")
            return self.get_random_ua(device_type, os_type)

    def _get_fallback_ua(self, device_type='mobile', os_type='any'):
        """获取备用 User-Agent"""
        fallback_agents = self._get_default_agents()

        print(f"🆘 使用备用UA - 设备: {device_type}, 系统: {os_type}")

        if device_type in fallback_agents:
            if os_type in fallback_agents[device_type]:
                pool = fallback_agents[device_type][os_type]
            elif 'any' in fallback_agents[device_type]:
                pool = fallback_agents[device_type]['any']
            else:
                pool = None

            if pool:
                selected_ua = random.choice(pool)
                detected_device = self._detect_device_type(selected_ua)
                detected_os = self._detect_os_type(selected_ua)
                print(f"🆘 备用UA: {detected_device}.{detected_os} - {selected_ua[:80]}...")
                return selected_ua

        # 最终回退
        if device_type == 'mobile' and os_type == 'android':
            default_ua = "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        elif device_type == 'mobile' and os_type == 'ios':
            default_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        elif device_type == 'desktop':
            default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        else:
            default_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"

        print(f"🆘 使用默认UA: {default_ua[:80]}...")
        return default_ua

    def get_ua_stats(self):
        """获取 User-Agent 统计信息 - 修复版本"""
        return {
            'total_lines': self.total_lines,  # 修复：添加这个字段
            'mobile_android_count': len(self.mobile_android_cache),
            'mobile_ios_count': len(self.mobile_ios_cache),
            'wechat_android_count': len(self.wechat_android_cache),
            'wechat_ios_count': len(self.wechat_ios_cache),
            'desktop_count': len(self.desktop_cache),
            'total_cache': len(self.all_cache),
            'cache_loaded': self.cache_loaded
        }

    def create_default_ua_file(self):
        """创建默认 User-Agent 文件"""
        default_agents = self._get_default_agents()
        try:
            with open(self.ua_file_path, 'w', encoding='utf-8') as f:
                f.write("# User-Agent 数据库 - 精确分类\n")
                f.write("# 移动端、微信浏览器、桌面端完全分离存储\n\n")

                # 写入安卓移动端
                f.write("# 安卓移动端 User-Agents\n")
                for ua in default_agents['mobile']['android']:
                    f.write(f"{ua}\n")

                # 写入iOS移动端
                f.write("\n# iOS移动端 User-Agents\n")
                for ua in default_agents['mobile']['ios']:
                    f.write(f"{ua}\n")

                # 写入安卓微信
                f.write("\n# 安卓微信浏览器 User-Agents\n")
                for ua in default_agents['wechat']['android']:
                    f.write(f"{ua}\n")

                # 写入iOS微信
                f.write("\n# iOS微信浏览器 User-Agents\n")
                for ua in default_agents['wechat']['ios']:
                    f.write(f"{ua}\n")

                # 写入桌面端
                f.write("\n# 桌面端 User-Agents\n")
                for ua in default_agents['desktop']['any']:
                    f.write(f"{ua}\n")

            print(f"✅ 已创建精确分类的 User-Agent 文件: {self.ua_file_path}")
            total_lines = (len(default_agents['mobile']['android']) +
                           len(default_agents['mobile']['ios']) +
                           len(default_agents['wechat']['android']) +
                           len(default_agents['wechat']['ios']) +
                           len(default_agents['desktop']['any']) + 8)
            self.total_lines = total_lines

        except Exception as e:
            print(f"❌ 创建 User-Agent 文件失败: {e}")

    def _get_default_agents(self):
        """获取默认的 User-Agent 列表"""
        return {
            'mobile': {
                'android': [
                    'Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                    'Mozilla/5.0 (Linux; Android 14; SM-S926B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                    'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
                ],
                'ios': [
                    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
                ]
            },
            'wechat': {
                'android': [
                    'Mozilla/5.0 (Linux; Android 13; SM-G991B Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/119.0.6045.193 Mobile Safari/537.36 MicroMessenger/8.0.42(0x18002a29) WeChat/arm64 Weixin Android Tablet NetType/WIFI Language/zh_CN',
                ],
                'ios': [
                    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.42(0x18002a29) NetType/WIFI Language/zh_CN',
                ]
            },
            'desktop': {
                'any': [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                ]
            }
        }

    def create_default_agents(self):
        """创建默认的 User-Agent 缓存"""
        default_agents = self._get_default_agents()
        self.mobile_android_cache = default_agents['mobile']['android']
        self.mobile_ios_cache = default_agents['mobile']['ios']
        self.wechat_android_cache = default_agents['wechat']['android']
        self.wechat_ios_cache = default_agents['wechat']['ios']
        self.desktop_cache = default_agents['desktop']['any']

        self.all_cache = (self.mobile_android_cache + self.mobile_ios_cache +
                          self.wechat_android_cache + self.wechat_ios_cache +
                          self.desktop_cache)

        self.cache_loaded = True
        print("✅ 使用默认 User-Agent 缓存")

    def add_user_agent(self, user_agent, device_type='auto'):
        """添加 User-Agent 到文件"""
        try:
            with open(self.ua_file_path, 'a', encoding='utf-8') as f:
                f.write(f"{user_agent}\n")

            self.total_lines += 1

            if self.cache_loaded and len(self.all_cache) < self.cache_size:
                self.all_cache.append(user_agent)

                # 自动分类
                if self._is_wechat_ua(user_agent):
                    if self._is_android_ua(user_agent):
                        self.wechat_android_cache.append(user_agent)
                    elif self._is_ios_ua(user_agent):
                        self.wechat_ios_cache.append(user_agent)
                elif self._is_mobile_ua(user_agent):
                    if self._is_android_ua(user_agent):
                        self.mobile_android_cache.append(user_agent)
                    elif self._is_ios_ua(user_agent):
                        self.mobile_ios_cache.append(user_agent)
                else:
                    self.desktop_cache.append(user_agent)

            print(f"✅ 已添加 User-Agent，文件总行数: {self.total_lines}")
            return True

        except Exception as e:
            print(f"❌ 添加 User-Agent 失败: {e}")
            return False