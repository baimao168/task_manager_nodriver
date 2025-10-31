# statistics_manager.py
import json
import datetime
import logging
from collections import defaultdict, deque
from typing import Dict, List, Any


class StatisticsManager:
    def __init__(self):
        self.task_stats = {
            'total_tasks': 0,
            'successful_tasks': 0,
            'failed_tasks': 0,
            'total_runtime': 0,
            'daily_stats': defaultdict(lambda: {'tasks': 0, 'success': 0, 'runtime': 0}),
            'hourly_stats': defaultdict(lambda: {'tasks': 0, 'success': 0}),
            'recent_tasks': deque(maxlen=100),
            'platform_stats': defaultdict(lambda: {'tasks': 0, 'success': 0}),
            'url_stats': defaultdict(lambda: {'tasks': 0, 'success': 0}),
            'start_time': datetime.datetime.now().isoformat()
        }

    def add_task_record(self, task_id, success, runtime, platform="", url=""):
        """添加任务记录"""
        try:
            now = datetime.datetime.now()
            date_key = now.strftime("%Y-%m-%d")
            hour_key = now.strftime("%Y-%m-%d %H:00")

            # 更新基础统计
            self.task_stats['total_tasks'] += 1
            if success:
                self.task_stats['successful_tasks'] += 1
            else:
                self.task_stats['failed_tasks'] += 1
            self.task_stats['total_runtime'] += runtime

            # 更新日期统计
            self.task_stats['daily_stats'][date_key]['tasks'] += 1
            if success:
                self.task_stats['daily_stats'][date_key]['success'] += 1
            self.task_stats['daily_stats'][date_key]['runtime'] += runtime

            # 更新小时统计
            self.task_stats['hourly_stats'][hour_key]['tasks'] += 1
            if success:
                self.task_stats['hourly_stats'][hour_key]['success'] += 1

            # 更新平台统计
            if platform:
                self.task_stats['platform_stats'][platform]['tasks'] += 1
                if success:
                    self.task_stats['platform_stats'][platform]['success'] += 1

            # 更新URL统计
            if url:
                self.task_stats['url_stats'][url]['tasks'] += 1
                if success:
                    self.task_stats['url_stats'][url]['success'] += 1

            # 添加最近任务记录
            self.task_stats['recent_tasks'].append({
                'task_id': task_id,
                'timestamp': now.isoformat(),
                'success': success,
                'runtime': round(runtime, 2),
                'platform': platform,
                'url': url
            })

            # 每10个任务自动保存一次
            if self.task_stats['total_tasks'] % 10 == 0:
                self.save_stats()

        except Exception as e:
            logging.error(f"添加任务记录失败: {e}")

    def get_success_rate(self):
        """获取成功率"""
        if self.task_stats['total_tasks'] == 0:
            return 0
        return (self.task_stats['successful_tasks'] / self.task_stats['total_tasks']) * 100

    def get_avg_runtime(self):
        """获取平均运行时间"""
        if self.task_stats['total_tasks'] == 0:
            return 0
        return self.task_stats['total_runtime'] / self.task_stats['total_tasks']

    def get_today_stats(self):
        """获取今日统计"""
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        return self.task_stats['daily_stats'][today]

    def get_hourly_success_rates(self, hours=24):
        """获取最近小时成功率"""
        hourly_data = []
        now = datetime.datetime.now()

        for i in range(hours - 1, -1, -1):
            hour_time = now - datetime.timedelta(hours=i)
            hour_key = hour_time.strftime("%Y-%m-%d %H:00")
            stats = self.task_stats['hourly_stats'][hour_key]

            success_rate = 0
            if stats['tasks'] > 0:
                success_rate = (stats['success'] / stats['tasks']) * 100

            hourly_data.append({
                'hour': hour_time.strftime("%H:%M"),
                'success_rate': round(success_rate, 2),
                'tasks': stats['tasks'],
                'success': stats['success']
            })

        return hourly_data

    def get_platform_stats(self):
        """获取平台统计"""
        platforms = []
        for platform, stats in self.task_stats['platform_stats'].items():
            if stats['tasks'] > 0:
                success_rate = (stats['success'] / stats['tasks']) * 100
                platforms.append({
                    'name': platform,
                    'tasks': stats['tasks'],
                    'success': stats['success'],
                    'success_rate': round(success_rate, 2)
                })
        return sorted(platforms, key=lambda x: x['tasks'], reverse=True)

    def get_recent_tasks(self, count=20):
        """获取最近任务"""
        return list(self.task_stats['recent_tasks'])[-count:]

    def save_stats(self):
        """保存统计到文件"""
        try:
            # 转换defaultdict为普通dict以便序列化
            stats_to_save = self.task_stats.copy()
            stats_to_save['daily_stats'] = dict(stats_to_save['daily_stats'])
            stats_to_save['hourly_stats'] = dict(stats_to_save['hourly_stats'])
            stats_to_save['platform_stats'] = dict(stats_to_save['platform_stats'])
            stats_to_save['url_stats'] = dict(stats_to_save['url_stats'])
            stats_to_save['recent_tasks'] = list(stats_to_save['recent_tasks'])

            with open('task_statistics.json', 'w', encoding='utf-8') as f:
                json.dump(stats_to_save, f, ensure_ascii=False, indent=2)

            logging.info("统计数据已保存")
        except Exception as e:
            logging.error(f"保存统计失败: {e}")

    def load_stats(self):
        """从文件加载统计"""
        try:
            with open('task_statistics.json', 'r', encoding='utf-8') as f:
                loaded_stats = json.load(f)

                # 转换回defaultdict
                self.task_stats.update(loaded_stats)
                self.task_stats['daily_stats'] = defaultdict(lambda: {'tasks': 0, 'success': 0, 'runtime': 0},
                                                             self.task_stats.get('daily_stats', {}))
                self.task_stats['hourly_stats'] = defaultdict(lambda: {'tasks': 0, 'success': 0},
                                                              self.task_stats.get('hourly_stats', {}))
                self.task_stats['platform_stats'] = defaultdict(lambda: {'tasks': 0, 'success': 0},
                                                                self.task_stats.get('platform_stats', {}))
                self.task_stats['url_stats'] = defaultdict(lambda: {'tasks': 0, 'success': 0},
                                                           self.task_stats.get('url_stats', {}))
                self.task_stats['recent_tasks'] = deque(self.task_stats.get('recent_tasks', []), maxlen=100)

            logging.info("统计数据已加载")
        except FileNotFoundError:
            logging.info("统计文件不存在，创建新的统计")
        except Exception as e:
            logging.error(f"加载统计失败: {e}")

    def clear_stats(self):
        """清空统计数据"""
        self.task_stats = {
            'total_tasks': 0,
            'successful_tasks': 0,
            'failed_tasks': 0,
            'total_runtime': 0,
            'daily_stats': defaultdict(lambda: {'tasks': 0, 'success': 0, 'runtime': 0}),
            'hourly_stats': defaultdict(lambda: {'tasks': 0, 'success': 0}),
            'recent_tasks': deque(maxlen=100),
            'platform_stats': defaultdict(lambda: {'tasks': 0, 'success': 0}),
            'url_stats': defaultdict(lambda: {'tasks': 0, 'success': 0}),
            'start_time': datetime.datetime.now().isoformat()
        }
        self.save_stats()