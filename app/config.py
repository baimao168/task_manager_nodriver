import json
import os
from dataclasses import dataclass, asdict, field
from typing import List, Optional
from enum import Enum


class Platform(Enum):
    PLATFORM1 = "平台1"
    PLATFORM2 = "平台2"
    PLATFORM3 = "平台3"


class UAType(Enum):
    mobile = "浏览器"
    wechat = "微信"


@dataclass
class TaskConfig:
    """任务配置数据类"""
    target_url: str = ""
    platform: Platform = Platform.PLATFORM1
    thread_count: int = 1
    random_stay_time: bool = False
    min_stay_time: int = 5
    max_stay_time: int = 30
    bypass_verification: bool = False
    auto_click_links: bool = False
    auto_send_messages: bool = False
    message_list: List[str] = field(default_factory=list)
    ua_type: UAType = UAType.mobile

    # 精简后的新参数
    auto_click_ratio: int = 50  # 自动点击链接比例（%）
    auto_message_ratio: int = 50  # 自动发送消息比例（%）
    total_processes: int = 30  # 总进程数（纯数字）
    total_minutes: int = 30  # 总时间（分钟）

    # 浏览器设置
    headless_mode: bool = False  # 无头模式
    browser_timeout: int = 30  # 浏览器超时时间（秒）

    # 代理设置
    proxy_enabled: bool = True
    proxy_type: str = "http"  # http, https, socks5
    proxy_host: str = ""
    proxy_port: int = 0
    proxy_username: str = ""
    proxy_password: str = ""

    # UA设置
    custom_user_agent: str = ""  # 自定义User-Agent

    def to_dict(self):
        data = asdict(self)
        # 转换枚举值为字符串
        data['platform'] = self.platform.value
        data['ua_type'] = self.ua_type.value
        return data

    @classmethod
    def from_dict(cls, data):
        # 转换字符串为枚举值
        if 'platform' in data:
            data['platform'] = Platform(data['platform'])
        if 'ua_type' in data:
            data['ua_type'] = UAType(data['ua_type'])
        return cls(**data)


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.default_config = TaskConfig()
        self.current_config = TaskConfig()

    def load_config(self) -> TaskConfig:
        """从文件加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_config = TaskConfig.from_dict(data)
            else:
                self.current_config = TaskConfig()
                self.save_config()
        except Exception as e:
            print(f"加载配置失败: {e}")
            self.current_config = TaskConfig()

        return self.current_config

    def save_config(self, config: TaskConfig = None):
        """保存配置到文件"""
        try:
            if config:
                self.current_config = config

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_config.to_dict(), f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")