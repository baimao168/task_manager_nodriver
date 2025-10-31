import logging
import time
import random
import math
import asyncio
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
from typing import Dict, List, Optional, Any

from app.worker import Worker
from app.config import TaskConfig


class TaskManager(QObject):
    """任务管理器 - 支持在指定时间内完成指定进程数和手动检测"""

    # 信号定义
    task_started = pyqtSignal(int)  # 任务开始，参数：任务ID
    task_progress = pyqtSignal(int, str)  # 任务进度，参数：任务ID, 状态消息
    task_finished = pyqtSignal(int, bool)  # 任务完成，参数：任务ID, 是否成功
    task_error = pyqtSignal(int, str)  # 任务错误，参数：任务ID, 错误消息
    status_updated = pyqtSignal(int, int, int)  # 状态更新: 运行中, 已完成, 总任务数
    all_tasks_completed = pyqtSignal()  # 所有任务完成（停止时发射）
    time_limit_reached = pyqtSignal()  # 时间到达
    manual_test_completed = pyqtSignal(bool, str)  # 手动检测完成: 是否成功, 消息

    def __init__(self):
        super().__init__()
        self.tasks: Dict[int, Dict] = {}  # 存储任务信息
        self.workers: Dict[int, Worker] = {}  # 存储工作线程
        self.threads: Dict[int, QThread] = {}  # 存储线程对象
        self.next_task_id = 1
        self.is_running = False
        self.is_paused = False
        self.current_config: Optional[TaskConfig] = None

        # 任务相关
        self.start_time = 0  # 任务开始时间
        self.total_processes = 0  # 总进程数
        self.total_seconds = 0  # 总时间（秒）
        self.completed_processes = 0  # 已完成进程数
        self.scheduled_processes = 0  # 已调度进程数
        self.time_limit_timer = QTimer()  # 时间限制定时器
        self.scheduler_timer = QTimer()  # 任务调度定时器

        # 手动检测相关
        self.manual_test_worker = None
        self.manual_test_thread = None
        self.is_manual_test_running = False

        # 连接定时器
        self.time_limit_timer.timeout.connect(self.on_time_reached)
        self.scheduler_timer.timeout.connect(self.schedule_tasks)

    def start_manual_test(self, config: TaskConfig):
        """开始手动检测 - 执行单个任务"""
        if self.is_manual_test_running:
            self.manual_test_completed.emit(False, "手动检测正在运行中")
            return

        if self.is_running:
            self.manual_test_completed.emit(False, "批量任务正在运行中，无法执行手动检测")
            return

        self.is_manual_test_running = True
        self.current_config = config

        logging.info("开始手动检测 - 执行单个任务")

        # 创建单个任务配置
        task_config = self._create_task_config(config)

        # 创建手动检测工作线程
        self.manual_test_worker = Worker(0, task_config)  # 使用0作为手动检测的任务ID
        self.manual_test_thread = QThread()

        # 移动worker到线程
        self.manual_test_worker.moveToThread(self.manual_test_thread)

        # 连接信号
        self.manual_test_thread.started.connect(self.manual_test_worker.run)
        self.manual_test_worker.started.connect(self.on_manual_test_started)
        self.manual_test_worker.progress.connect(self.on_manual_test_progress)
        self.manual_test_worker.finished.connect(self.on_manual_test_finished)
        self.manual_test_worker.error.connect(self.on_manual_test_error)

        # 启动线程
        self.manual_test_thread.start()

    def _create_task_config(self, config: TaskConfig) -> Dict[str, Any]:
        """创建任务配置"""
        return {
            'target_url': config.target_url,
            'platform': config.platform.value,
            'ua_type': config.ua_type.value,
            'thread_count': 1,  # 手动检测固定为1个线程
            'random_stay_time': config.random_stay_time,
            'min_stay_time': config.min_stay_time,
            'max_stay_time': config.max_stay_time,
            'bypass_verification': config.bypass_verification,
            'auto_click_links': config.auto_click_links,
            'auto_send_messages': config.auto_send_messages,
            'message_list': config.message_list,
            'auto_click_ratio': config.auto_click_ratio,
            'auto_message_ratio': config.auto_message_ratio,
            'headless_mode': config.headless_mode,
            'browser_timeout': config.browser_timeout,
            'is_manual_test': True  # 标记为手动检测
        }

    def on_manual_test_started(self, task_id: int):
        """手动检测开始"""
        logging.info("手动检测任务开始执行")
        self.task_started.emit(task_id)

    def on_manual_test_progress(self, task_id: int, message: str):
        """手动检测进度"""
        logging.info(f"手动检测进度: {message}")
        self.task_progress.emit(task_id, f"[手动检测] {message}")

    def on_manual_test_finished(self, task_id: int, success: bool):
        """手动检测完成"""
        logging.info(f"手动检测完成，结果: {'成功' if success else '失败'}")

        # 清理资源
        self._cleanup_manual_test()

        # 发射完成信号
        status_msg = "手动检测完成 - 成功" if success else "手动检测完成 - 失败"
        self.manual_test_completed.emit(success, status_msg)
        self.task_finished.emit(task_id, success)

    def on_manual_test_error(self, task_id: int, error_msg: str):
        """手动检测错误"""
        logging.error(f"手动检测错误: {error_msg}")

        # 清理资源
        self._cleanup_manual_test()

        # 发射错误信号
        self.manual_test_completed.emit(False, f"手动检测错误: {error_msg}")
        self.task_error.emit(task_id, error_msg)

    def _cleanup_manual_test(self):
        """清理手动检测资源"""
        self.is_manual_test_running = False

        if self.manual_test_worker and self.manual_test_thread:
            try:
                # 断开连接
                self.manual_test_worker.started.disconnect()
                self.manual_test_worker.progress.disconnect()
                self.manual_test_worker.finished.disconnect()
                self.manual_test_worker.error.disconnect()

                # 停止线程
                if self.manual_test_thread.isRunning():
                    self.manual_test_thread.quit()
                    self.manual_test_thread.wait(1000)

                self.manual_test_worker = None
                self.manual_test_thread = None

            except Exception as e:
                logging.error(f"清理手动检测资源失败: {e}")

    def stop_manual_test(self):
        """停止手动检测"""
        if self.is_manual_test_running and self.manual_test_worker:
            self.manual_test_worker.stop()
            self._cleanup_manual_test()
            logging.info("手动检测已停止")

    # 原有的批量任务方法保持不变
    def start_tasks(self, config: TaskConfig):
        """启动批量任务"""
        if self.is_running:
            logging.warning("任务管理器正在运行，无法启动新任务")
            return

        if self.is_manual_test_running:
            logging.warning("手动检测正在运行，无法启动批量任务")
            return

        self.is_running = True
        self.is_paused = False
        self.current_config = config
        self.start_time = time.time()
        self.total_processes = config.total_processes
        self.total_seconds = config.total_minutes * 60  # 转换为秒
        self.completed_processes = 0
        self.scheduled_processes = 0
        self.next_task_id = 1

        logging.info(f"开始批量任务: {self.total_processes}个进程在{config.total_minutes}分钟内完成")

        # 设置时间限制定时器
        self.time_limit_timer.start(self.total_seconds * 1000)

        # 启动任务调度器
        self.scheduler_timer.start(500)

        # 立即开始第一轮任务
        self.schedule_first_round()

    def schedule_first_round(self):
        """调度第一轮任务"""
        if not self.is_running:
            return

        # 启动第一轮任务（不超过线程数）
        tasks_to_start = min(self.current_config.thread_count, self.total_processes)

        for i in range(tasks_to_start):
            if self.scheduled_processes >= self.total_processes:
                break
            self._start_single_task()

        logging.info(f"第一轮启动 {tasks_to_start} 个任务")

    def schedule_tasks(self):
        """调度后续任务 - 基于时间随机分布"""
        if not self.is_running or self.is_paused:
            return

        # 检查是否已完成所有进程
        if self.completed_processes >= self.total_processes:
            logging.info(f"已完成所有进程: {self.completed_processes}/{self.total_processes}")
            self.stop_tasks()
            return

        # 计算当前运行中的任务数
        running_count = len([w for w in self.workers.values() if w.is_running and not w.is_paused])

        # 如果有空闲线程且还有进程需要调度
        if running_count < self.current_config.thread_count and self.scheduled_processes < self.total_processes:
            # 计算已用时间和剩余时间
            elapsed_time = time.time() - self.start_time
            remaining_time = self.total_seconds - elapsed_time

            if remaining_time <= 0:
                return

            # 计算剩余需要完成的进程数
            remaining_processes = self.total_processes - self.completed_processes

            # 计算平均每个剩余进程可用的时间
            if remaining_processes > 0:
                avg_time_per_process = remaining_time / remaining_processes

                # 基于剩余时间随机决定是否启动新任务
                base_probability = min(0.8, (elapsed_time / self.total_seconds) * 1.5)

                if random.random() < base_probability:
                    tasks_to_start = min(
                        self.current_config.thread_count - running_count,
                        remaining_processes
                    )

                    if tasks_to_start > 0:
                        logging.debug(f"随机调度 {tasks_to_start} 个新任务")
                        for i in range(tasks_to_start):
                            if self.scheduled_processes >= self.total_processes:
                                break
                            self._start_single_task()

        # 发射状态更新信号
        self.status_updated.emit(running_count, self.completed_processes, self.scheduled_processes)

    def _start_single_task(self):
        """启动单个任务"""
        task_id = self.next_task_id
        self.next_task_id += 1
        self.scheduled_processes += 1

        # 创建任务配置
        task_config = {
            'target_url': self.current_config.target_url,
            'platform': self.current_config.platform.value,
            'ua_type': self.current_config.ua_type.value,
            'thread_count': self.current_config.thread_count,
            'random_stay_time': self.current_config.random_stay_time,
            'min_stay_time': self.current_config.min_stay_time,
            'max_stay_time': self.current_config.max_stay_time,
            'bypass_verification': self.current_config.bypass_verification,
            'auto_click_links': self.current_config.auto_click_links,
            'auto_send_messages': self.current_config.auto_send_messages,
            'message_list': self.current_config.message_list,
            'auto_click_ratio': self.current_config.auto_click_ratio,
            'auto_message_ratio': self.current_config.auto_message_ratio,
            'headless_mode': self.current_config.headless_mode,
            'browser_timeout': self.current_config.browser_timeout,
            'total_seconds': self.total_seconds,
            'total_processes': self.total_processes,
            'is_manual_test': False  # 标记为批量任务
        }

        # 创建并启动工作线程
        worker = Worker(task_id, task_config)
        thread = QThread()

        # 移动worker到线程
        worker.moveToThread(thread)

        # 连接信号
        thread.started.connect(worker.run)
        worker.started.connect(self.task_started)
        worker.progress.connect(self.task_progress)
        worker.finished.connect(self.on_task_finished)
        worker.error.connect(self.task_error)

        # 立即启动线程
        thread.start()

        # 存储引用
        self.tasks[task_id] = {'config': task_config, 'status': 'running', 'start_time': time.time()}
        self.workers[task_id] = worker
        self.threads[task_id] = thread

        logging.info(f"启动任务 {task_id}, 已调度: {self.scheduled_processes}/{self.total_processes}")

    def on_task_finished(self, task_id: int, success: bool):
        """处理任务完成"""
        self.completed_processes += 1

        # 记录任务执行时间
        if task_id in self.tasks:
            execution_time = time.time() - self.tasks[task_id]['start_time']
            logging.info(f"任务 {task_id} 完成, 执行时间: {execution_time:.2f}秒, 成功: {success}")

        # 清理完成的任务资源
        self._cleanup_task(task_id)

        # 发射完成信号
        self.task_finished.emit(task_id, success)

        # 检查是否已完成所有进程
        if self.completed_processes >= self.total_processes:
            logging.info(f"已完成所有目标进程: {self.completed_processes}/{self.total_processes}")
            self.stop_tasks()

    def on_time_reached(self):
        """时间到达"""
        self.time_limit_timer.stop()
        logging.info(f"时间到达，已完成 {self.completed_processes}/{self.total_processes} 个进程")
        self.stop_tasks()
        self.time_limit_reached.emit()

    def _cleanup_task(self, task_id: int):
        """清理任务资源"""
        if task_id in self.workers:
            worker = self.workers[task_id]
            thread = self.threads[task_id]

            # 断开连接
            try:
                worker.finished.disconnect(self.on_task_finished)
            except:
                pass

            # 清理资源
            if thread.isRunning():
                thread.quit()
                thread.wait(1000)

            del self.workers[task_id]
            del self.threads[task_id]

        if task_id in self.tasks:
            del self.tasks[task_id]

    def pause_tasks(self):
        """暂停所有任务"""
        if not self.is_running or self.is_paused:
            return

        self.is_paused = True
        self.scheduler_timer.stop()

        # 暂停所有运行中的任务
        paused_count = 0
        for task_id, worker in self.workers.items():
            if worker.is_running and not worker.is_paused:
                worker.pause()
                paused_count += 1

        logging.info(f"已暂停 {paused_count} 个运行中的任务")

    def resume_tasks(self):
        """恢复所有任务"""
        if not self.is_running or not self.is_paused:
            return

        self.is_paused = False
        self.scheduler_timer.start(500)

        # 恢复所有暂停的任务
        resumed_count = 0
        for task_id, worker in self.workers.items():
            if worker.is_running and worker.is_paused:
                worker.resume()
                resumed_count += 1

        logging.info(f"已恢复 {resumed_count} 个暂停的任务")

    def stop_tasks(self):
        """停止所有任务"""
        if not self.is_running:
            return

        self.is_running = False
        self.is_paused = False
        self.scheduler_timer.stop()
        self.time_limit_timer.stop()

        # 停止所有工作线程
        for task_id, worker in self.workers.items():
            worker.stop()

        # 等待所有线程结束并清理
        tasks_to_cleanup = list(self.workers.keys())
        for task_id in tasks_to_cleanup:
            self._cleanup_task(task_id)

        # 计算完成率和实际用时
        completion_rate = (self.completed_processes / self.total_processes * 100) if self.total_processes > 0 else 0
        total_time = time.time() - self.start_time

        logging.info(
            f"任务停止。目标: {self.total_processes}, 完成: {self.completed_processes}, 完成率: {completion_rate:.1f}%, 实际用时: {total_time:.1f}秒")

        # 发射所有任务完成信号
        self.all_tasks_completed.emit()

    def get_running_task_count(self) -> int:
        """获取运行中的任务数量"""
        return len([worker for worker in self.workers.values() if worker.is_running and not worker.is_paused])

    def get_paused_task_count(self) -> int:
        """获取暂停中的任务数量"""
        return len([worker for worker in self.workers.values() if worker.is_running and worker.is_paused])

    def get_target_processes(self) -> int:
        """获取目标进程数"""
        return self.total_processes

    def get_completed_processes(self) -> int:
        """获取已完成进程数"""
        return self.completed_processes

    def get_scheduled_processes(self) -> int:
        """获取已调度进程数"""
        return self.scheduled_processes

    def get_time_elapsed(self) -> float:
        """获取已运行时间（秒）"""
        if self.start_time > 0:
            return time.time() - self.start_time
        return 0

    def get_time_remaining(self) -> float:
        """获取剩余时间（秒）"""
        if self.start_time > 0:
            return max(0, self.total_seconds - (time.time() - self.start_time))
        return 0

    def get_completion_rate(self) -> float:
        """获取完成率"""
        if self.total_processes > 0:
            return (self.completed_processes / self.total_processes) * 100
        return 0

    def get_expected_cycle_count(self) -> int:
        """获取预期的循环次数"""
        if self.current_config and self.current_config.thread_count > 0:
            return math.ceil(self.total_processes / self.current_config.thread_count)
        return 0

    def is_manual_test_active(self) -> bool:
        """检查手动检测是否在运行"""
        return self.is_manual_test_running