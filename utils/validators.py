import re
from urllib.parse import urlparse


class Validators:
    """输入验证器"""

    @staticmethod
    def validate_url(url: str) -> bool:
        """验证URL格式"""
        if not url:
            return False

        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def validate_thread_count(count: int) -> bool:
        """验证线程数"""
        return 1 <= count <= 100

    @staticmethod
    def validate_stay_time_range(min_time: int, max_time: int) -> bool:
        """验证停留时间范围"""
        return 0 <= min_time <= max_time <= 3600  # 最大1小时