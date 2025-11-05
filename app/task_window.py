import logging
import math
import json
import os
from dataclasses import dataclass, asdict
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QFormLayout, QLineEdit, QComboBox, QSpinBox,
                             QCheckBox, QPushButton, QTextEdit, QProgressBar,
                             QLabel, QMessageBox, QTabWidget, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot
from PyQt5.QtGui import QFont

from app.task_manager import TaskManager
from app.config import ConfigManager, TaskConfig, Platform, UAType
from utils.validators import Validators


@dataclass
class TaskDeviceStats:
    """任务设备统计数据"""
    total_tests: int = 0
    successful_tests: int = 0
    failed_tests: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.successful_tests / self.total_tests) * 100


@dataclass
class TaskNetworkStats:
    """任务网络统计数据"""
    total_tests: int = 0
    successful_tests: int = 0
    failed_tests: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.successful_tests / self.total_tests) * 100


@dataclass
class TaskStats:
    """任务统计数据"""
    android_stats: TaskDeviceStats = None
    ios_stats: TaskDeviceStats = None
    mobile_data_stats: TaskNetworkStats = None
    wifi_stats: TaskNetworkStats = None
    total_tests: int = 0
    successful_tests: int = 0
    failed_tests: int = 0

    def __post_init__(self):
        if self.android_stats is None:
            self.android_stats = TaskDeviceStats()
        if self.ios_stats is None:
            self.ios_stats = TaskDeviceStats()
        if self.mobile_data_stats is None:
            self.mobile_data_stats = TaskNetworkStats()
        if self.wifi_stats is None:
            self.wifi_stats = TaskNetworkStats()

    @property
    def overall_success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.successful_tests / self.total_tests) * 100


class TaskStatsManager:
    """任务统计管理器"""

    def __init__(self, task_title: str):
        self.task_title = task_title
        self.stats_file = f"task_stats_{task_title}.json"
        self.stats = TaskStats()
        self.load_stats()

    def load_stats(self):
        """加载统计数据"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.stats = TaskStats(
                        android_stats=TaskDeviceStats(**data.get('android_stats', {})),
                        ios_stats=TaskDeviceStats(**data.get('ios_stats', {})),
                        mobile_data_stats=TaskNetworkStats(**data.get('mobile_data_stats', {})),
                        wifi_stats=TaskNetworkStats(**data.get('wifi_stats', {})),
                        total_tests=data.get('total_tests', 0),
                        successful_tests=data.get('successful_tests', 0),
                        failed_tests=data.get('failed_tests', 0)
                    )
        except Exception as e:
            print(f"加载任务统计数据失败: {e}")
            self.stats = TaskStats()

    def save_stats(self):
        """保存统计数据"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.stats), f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存任务统计数据失败: {e}")

    def update_stats(self, success: bool, device_type: str, network_type: str):
        """更新统计数据"""
        self.stats.total_tests += 1

        if success:
            self.stats.successful_tests += 1
            # 更新设备统计
            if device_type == 'android':
                self.stats.android_stats.total_tests += 1
                self.stats.android_stats.successful_tests += 1
            else:  # ios
                self.stats.ios_stats.total_tests += 1
                self.stats.ios_stats.successful_tests += 1

            # 更新网络统计
            if network_type == 'mobile_data':
                self.stats.mobile_data_stats.total_tests += 1
                self.stats.mobile_data_stats.successful_tests += 1
            else:  # wifi
                self.stats.wifi_stats.total_tests += 1
                self.stats.wifi_stats.successful_tests += 1
        else:
            self.stats.failed_tests += 1
            # 更新设备统计
            if device_type == 'android':
                self.stats.android_stats.total_tests += 1
                self.stats.android_stats.failed_tests += 1
            else:  # ios
                self.stats.ios_stats.total_tests += 1
                self.stats.ios_stats.failed_tests += 1

            # 更新网络统计
            if network_type == 'mobile_data':
                self.stats.mobile_data_stats.total_tests += 1
                self.stats.mobile_data_stats.failed_tests += 1
            else:  # wifi
                self.stats.wifi_stats.total_tests += 1
                self.stats.wifi_stats.failed_tests += 1

        self.save_stats()

    def clear_stats(self):
        """清空统计数据"""
        self.stats = TaskStats()
        self.save_stats()

    def get_stats_summary(self) -> dict:
        """获取统计摘要"""
        return {
            'total_tests': self.stats.total_tests,
            'successful_tests': self.stats.successful_tests,
            'failed_tests': self.stats.failed_tests,
            'overall_success_rate': self.stats.overall_success_rate,
            'android_total': self.stats.android_stats.total_tests,
            'android_success': self.stats.android_stats.successful_tests,
            'android_success_rate': self.stats.android_stats.success_rate,
            'ios_total': self.stats.ios_stats.total_tests,
            'ios_success': self.stats.ios_stats.successful_tests,
            'ios_success_rate': self.stats.ios_stats.success_rate,
            'mobile_data_total': self.stats.mobile_data_stats.total_tests,
            'mobile_data_success': self.stats.mobile_data_stats.successful_tests,
            'mobile_data_success_rate': self.stats.mobile_data_stats.success_rate,
            'wifi_total': self.stats.wifi_stats.total_tests,
            'wifi_success': self.stats.wifi_stats.successful_tests,
            'wifi_success_rate': self.stats.wifi_stats.success_rate
        }


class TaskWindow(QWidget):
    """单个任务窗口 - 使用选项卡分组设置项"""

    # 信号定义
    task_status_changed = pyqtSignal(str, str)  # 任务状态改变: 标题, 状态

    def __init__(self, title, stats_manager=None):
        super().__init__()
        self.title = title
        self.task_manager = TaskManager()
        self.config_manager = ConfigManager(f"config_{title}.json")
        self.current_config = TaskConfig()
        self.global_stats_manager = stats_manager  # 全局统计管理器（可选）
        self.task_stats_manager = TaskStatsManager(title)  # 任务独立统计管理器

        self.init_ui()
        self.load_config()
        self.connect_signals()

        # 状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)

        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel(f"任务窗口: {self.title}")
        title_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; color: #333; padding: 10px; }")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # 创建选项卡控件
        self.tab_widget = QTabWidget()

        # 添加各个设置选项卡
        self.tab_widget.addTab(self.create_basic_tab(), "基本设置")
        self.tab_widget.addTab(self.create_task_tab(), "任务设置")
        self.tab_widget.addTab(self.create_ratio_tab(), "比例设置")
        self.tab_widget.addTab(self.create_function_tab(), "功能设置")
        self.tab_widget.addTab(self.create_control_tab(), "任务控制")
        self.tab_widget.addTab(self.create_stats_tab(), "任务统计")
        self.tab_widget.addTab(self.create_log_tab(), "任务日志")

        layout.addWidget(self.tab_widget)

    def create_basic_tab(self):
        """创建基本设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 基本设置组
        basic_group = QGroupBox("基本设置")
        basic_layout = QFormLayout(basic_group)

        self.target_url_edit = QLineEdit()
        self.target_url_edit.setPlaceholderText("请输入目标URL")
        basic_layout.addRow("目标地址:", self.target_url_edit)

        self.platform_combo = QComboBox()
        self.platform_combo.addItems([platform.value for platform in Platform])
        basic_layout.addRow("所属平台:", self.platform_combo)

        self.ua_combo = QComboBox()
        self.ua_combo.addItems([ua.value for ua in UAType])
        basic_layout.addRow("UA类型:", self.ua_combo)

        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 100)
        self.thread_spin.setValue(1)
        basic_layout.addRow("线程数:", self.thread_spin)

        layout.addWidget(basic_group)
        layout.addStretch()
        return widget

    def create_task_tab(self):
        """创建任务设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 任务设置组
        task_group = QGroupBox("任务设置")
        task_layout = QFormLayout(task_group)

        self.total_processes_spin = QSpinBox()
        self.total_processes_spin.setRange(1, 10000)
        self.total_processes_spin.setValue(30)
        task_layout.addRow("总进程数:", self.total_processes_spin)

        self.total_minutes_spin = QSpinBox()
        self.total_minutes_spin.setRange(1, 1440)  # 1分钟到24小时
        self.total_minutes_spin.setValue(30)
        self.total_minutes_spin.setSuffix(" 分钟")
        task_layout.addRow("总时间:", self.total_minutes_spin)

        # 计算信息显示
        info_layout = QVBoxLayout()
        self.calc_label = QLabel("")
        self.calc_label.setStyleSheet(
            "QLabel { color: #666; font-size: 12px; background-color: #f5f5f5; padding: 8px; border-radius: 4px; }")
        self.calc_label.setWordWrap(True)
        info_layout.addWidget(self.calc_label)
        task_layout.addRow("计算信息:", info_layout)

        layout.addWidget(task_group)

        # 高级设置组
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QFormLayout(advanced_group)

        self.random_stay_check = QCheckBox("启用随机停留时间")
        self.random_stay_check.toggled.connect(self.on_random_stay_changed)
        advanced_layout.addRow(self.random_stay_check)

        stay_time_layout = QHBoxLayout()
        self.min_stay_spin = QSpinBox()
        self.min_stay_spin.setRange(0, 3600)
        self.min_stay_spin.setValue(5)
        self.min_stay_spin.setSuffix(" 秒")
        self.min_stay_spin.setEnabled(False)

        self.max_stay_spin = QSpinBox()
        self.max_stay_spin.setRange(0, 3600)
        self.max_stay_spin.setValue(30)
        self.max_stay_spin.setSuffix(" 秒")
        self.max_stay_spin.setEnabled(False)

        stay_time_layout.addWidget(QLabel("最小:"))
        stay_time_layout.addWidget(self.min_stay_spin)
        stay_time_layout.addWidget(QLabel("最大:"))
        stay_time_layout.addWidget(self.max_stay_spin)
        stay_time_layout.addStretch()

        advanced_layout.addRow("停留时间:", stay_time_layout)

        self.bypass_verification_check = QCheckBox("开启过验证")
        advanced_layout.addRow(self.bypass_verification_check)

        layout.addWidget(advanced_group)
        layout.addStretch()

        # 连接计算信号
        self.total_processes_spin.valueChanged.connect(self.update_calculation)
        self.total_minutes_spin.valueChanged.connect(self.update_calculation)
        self.thread_spin.valueChanged.connect(self.update_calculation)

        return widget

    def create_ratio_tab(self):
        """创建比例设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 设备比例设置组
        device_ratio_group = QGroupBox("设备比例设置")
        device_layout = QFormLayout(device_ratio_group)

        # 安卓比例
        android_layout = QHBoxLayout()
        self.android_ratio_slider = QSpinBox()
        self.android_ratio_slider.setRange(0, 100)
        self.android_ratio_slider.setValue(50)
        self.android_ratio_slider.setSuffix("%")
        android_layout.addWidget(self.android_ratio_slider)
        android_layout.addWidget(QLabel("安卓"))
        android_layout.addStretch()
        device_layout.addRow("安卓比例:", android_layout)

        # iOS比例
        ios_layout = QHBoxLayout()
        self.ios_ratio_slider = QSpinBox()
        self.ios_ratio_slider.setRange(0, 100)
        self.ios_ratio_slider.setValue(50)
        self.ios_ratio_slider.setSuffix("%")
        ios_layout.addWidget(self.ios_ratio_slider)
        ios_layout.addWidget(QLabel("iOS"))
        ios_layout.addStretch()
        device_layout.addRow("iOS比例:", ios_layout)

        # 比例同步
        self.android_ratio_slider.valueChanged.connect(self.sync_device_ratios)
        self.ios_ratio_slider.valueChanged.connect(self.sync_device_ratios)

        layout.addWidget(device_ratio_group)

        # 网络类型比例设置组
        network_ratio_group = QGroupBox("网络类型比例设置")
        network_layout = QFormLayout(network_ratio_group)

        # 移动数据比例
        mobile_data_layout = QHBoxLayout()
        self.mobile_data_ratio_slider = QSpinBox()
        self.mobile_data_ratio_slider.setRange(0, 100)
        self.mobile_data_ratio_slider.setValue(50)
        self.mobile_data_ratio_slider.setSuffix("%")
        mobile_data_layout.addWidget(self.mobile_data_ratio_slider)
        mobile_data_layout.addWidget(QLabel("移动数据"))
        mobile_data_layout.addStretch()
        network_layout.addRow("移动数据比例:", mobile_data_layout)

        # WIFI比例
        wifi_layout = QHBoxLayout()
        self.wifi_ratio_slider = QSpinBox()
        self.wifi_ratio_slider.setRange(0, 100)
        self.wifi_ratio_slider.setValue(50)
        self.wifi_ratio_slider.setSuffix("%")
        wifi_layout.addWidget(self.wifi_ratio_slider)
        wifi_layout.addWidget(QLabel("WIFI"))
        wifi_layout.addStretch()
        network_layout.addRow("WIFI比例:", wifi_layout)

        # 比例同步
        self.mobile_data_ratio_slider.valueChanged.connect(self.sync_network_ratios)
        self.wifi_ratio_slider.valueChanged.connect(self.sync_network_ratios)

        layout.addWidget(network_ratio_group)
        layout.addStretch()
        return widget

    def create_function_tab(self):
        """创建功能设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 功能设置组
        function_group = QGroupBox("功能设置")
        function_layout = QVBoxLayout(function_group)

        # 自动点击链接
        auto_click_layout = QHBoxLayout()
        self.auto_click_check = QCheckBox("开启自动点击链接")
        auto_click_layout.addWidget(self.auto_click_check)

        self.auto_click_ratio_spin = QSpinBox()
        self.auto_click_ratio_spin.setRange(1, 100)
        self.auto_click_ratio_spin.setValue(50)
        self.auto_click_ratio_spin.setSuffix("%")
        auto_click_layout.addWidget(QLabel("点击比例:"))
        auto_click_layout.addWidget(self.auto_click_ratio_spin)
        auto_click_layout.addStretch()

        function_layout.addLayout(auto_click_layout)

        # 自动发送消息
        auto_message_layout = QHBoxLayout()
        self.auto_message_check = QCheckBox("开启自动发送消息")
        self.auto_message_check.toggled.connect(self.on_auto_message_changed)
        auto_message_layout.addWidget(self.auto_message_check)

        self.auto_message_ratio_spin = QSpinBox()
        self.auto_message_ratio_spin.setRange(1, 100)
        self.auto_message_ratio_spin.setValue(50)
        self.auto_message_ratio_spin.setSuffix("%")
        auto_message_layout.addWidget(QLabel("发送比例:"))
        auto_message_layout.addWidget(self.auto_message_ratio_spin)
        auto_message_layout.addStretch()

        function_layout.addLayout(auto_message_layout)

        self.message_text = QTextEdit()
        self.message_text.setMaximumHeight(120)
        self.message_text.setPlaceholderText("请输入要发送的消息，每行一条")
        self.message_text.setEnabled(False)
        function_layout.addWidget(self.message_text)

        layout.addWidget(function_group)
        layout.addStretch()
        return widget

    def create_control_tab(self):
        """创建任务控制选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 任务控制组
        control_group = QGroupBox("任务控制")
        control_layout = QVBoxLayout(control_group)

        # 按钮布局
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("开始任务")
        self.start_btn.setStyleSheet("""
            QPushButton { 
                background-color: #4CAF50; 
                color: white; 
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(self.start_btn)

        self.manual_test_btn = QPushButton("手动检测")
        self.manual_test_btn.setStyleSheet("""
            QPushButton { 
                background-color: #2196F3; 
                color: white; 
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        button_layout.addWidget(self.manual_test_btn)

        self.pause_btn = QPushButton("暂停任务")
        self.pause_btn.setStyleSheet("""
            QPushButton { 
                background-color: #FF9800; 
                color: white; 
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        button_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("停止任务")
        self.stop_btn.setStyleSheet("""
            QPushButton { 
                background-color: #F44336; 
                color: white; 
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        button_layout.addWidget(self.stop_btn)

        control_layout.addLayout(button_layout)

        # 状态显示区域
        status_group = QGroupBox("运行状态")
        status_layout = QVBoxLayout(status_group)

        # 状态行
        status_row1 = QHBoxLayout()
        status_row1.addWidget(QLabel("运行状态:"))
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("QLabel { color: #666; font-weight: bold; }")
        status_row1.addWidget(self.status_label)
        status_row1.addStretch()

        status_row1.addWidget(QLabel("手动检测:"))
        self.manual_status_label = QLabel("就绪")
        self.manual_status_label.setStyleSheet("QLabel { color: #666; font-weight: bold; }")
        status_row1.addWidget(self.manual_status_label)
        status_row1.addStretch()
        status_layout.addLayout(status_row1)

        # 时间显示
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("剩余时间:"))
        self.time_remaining_label = QLabel("--:--")
        self.time_remaining_label.setStyleSheet("QLabel { color: #2196F3; font-weight: bold; font-size: 14px; }")
        time_layout.addWidget(self.time_remaining_label)
        time_layout.addStretch()
        status_layout.addLayout(time_layout)

        # 进度显示
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("完成进度:"))
        self.progress_label = QLabel("0/0 (0%)")
        self.progress_label.setStyleSheet("QLabel { color: #4CAF50; font-weight: bold; font-size: 14px; }")
        progress_layout.addWidget(self.progress_label)
        progress_layout.addStretch()
        status_layout.addLayout(progress_layout)

        # 线程状态显示
        thread_layout = QHBoxLayout()
        thread_layout.addWidget(QLabel("运行线程:"))
        self.thread_count_label = QLabel("0")
        self.thread_count_label.setStyleSheet("QLabel { color: #FF9800; font-weight: bold; }")
        thread_layout.addWidget(self.thread_count_label)
        thread_layout.addStretch()

        thread_layout.addWidget(QLabel("理论循环:"))
        self.cycle_label = QLabel("0")
        self.cycle_label.setStyleSheet("QLabel { color: #9C27B0; font-weight: bold; }")
        thread_layout.addWidget(self.cycle_label)
        thread_layout.addStretch()
        status_layout.addLayout(thread_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)

        control_layout.addWidget(status_group)
        layout.addWidget(control_group)
        layout.addStretch()
        return widget

    def create_stats_tab(self):
        """创建任务统计选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 任务统计组
        stats_group = QGroupBox("任务统计")
        stats_layout = QVBoxLayout(stats_group)

        # 总体统计
        overall_layout = QHBoxLayout()
        overall_layout.addWidget(QLabel("总测试:"))
        self.total_tests_label = QLabel("0")
        overall_layout.addWidget(self.total_tests_label)

        overall_layout.addWidget(QLabel("成功率:"))
        self.success_rate_label = QLabel("0%")
        self.success_rate_label.setStyleSheet("QLabel { color: #4CAF50; font-weight: bold; }")
        overall_layout.addWidget(self.success_rate_label)
        overall_layout.addStretch()
        stats_layout.addLayout(overall_layout)

        # 设备统计
        device_stats_layout = QHBoxLayout()

        # 安卓统计
        android_stats_layout = QVBoxLayout()
        android_stats_layout.addWidget(QLabel("安卓设备:"))
        android_inner_layout = QHBoxLayout()
        android_inner_layout.addWidget(QLabel("测试:"))
        self.android_total_label = QLabel("0")
        android_inner_layout.addWidget(self.android_total_label)
        android_inner_layout.addWidget(QLabel("成功:"))
        self.android_success_label = QLabel("0")
        self.android_success_label.setStyleSheet("QLabel { color: #4CAF50; }")
        android_inner_layout.addWidget(self.android_success_label)
        android_inner_layout.addWidget(QLabel("成功率:"))
        self.android_rate_label = QLabel("0%")
        self.android_rate_label.setStyleSheet("QLabel { color: #2196F3; font-weight: bold; }")
        android_inner_layout.addWidget(self.android_rate_label)
        android_stats_layout.addLayout(android_inner_layout)
        device_stats_layout.addLayout(android_stats_layout)

        # iOS统计
        ios_stats_layout = QVBoxLayout()
        ios_stats_layout.addWidget(QLabel("iOS设备:"))
        ios_inner_layout = QHBoxLayout()
        ios_inner_layout.addWidget(QLabel("测试:"))
        self.ios_total_label = QLabel("0")
        ios_inner_layout.addWidget(self.ios_total_label)
        ios_inner_layout.addWidget(QLabel("成功:"))
        self.ios_success_label = QLabel("0")
        self.ios_success_label.setStyleSheet("QLabel { color: #4CAF50; }")
        ios_inner_layout.addWidget(self.ios_success_label)
        ios_inner_layout.addWidget(QLabel("成功率:"))
        self.ios_rate_label = QLabel("0%")
        self.ios_rate_label.setStyleSheet("QLabel { color: #FF5722; font-weight: bold; }")
        ios_inner_layout.addWidget(self.ios_rate_label)
        ios_stats_layout.addLayout(ios_inner_layout)
        device_stats_layout.addLayout(ios_stats_layout)

        stats_layout.addLayout(device_stats_layout)

        # 网络统计
        network_stats_layout = QHBoxLayout()

        # 移动数据统计
        mobile_data_stats_layout = QVBoxLayout()
        mobile_data_stats_layout.addWidget(QLabel("移动数据:"))
        mobile_data_inner_layout = QHBoxLayout()
        mobile_data_inner_layout.addWidget(QLabel("测试:"))
        self.mobile_data_total_label = QLabel("0")
        mobile_data_inner_layout.addWidget(self.mobile_data_total_label)
        mobile_data_inner_layout.addWidget(QLabel("成功:"))
        self.mobile_data_success_label = QLabel("0")
        self.mobile_data_success_label.setStyleSheet("QLabel { color: #4CAF50; }")
        mobile_data_inner_layout.addWidget(self.mobile_data_success_label)
        mobile_data_inner_layout.addWidget(QLabel("成功率:"))
        self.mobile_data_rate_label = QLabel("0%")
        self.mobile_data_rate_label.setStyleSheet("QLabel { color: #9C27B0; font-weight: bold; }")
        mobile_data_inner_layout.addWidget(self.mobile_data_rate_label)
        mobile_data_stats_layout.addLayout(mobile_data_inner_layout)
        network_stats_layout.addLayout(mobile_data_stats_layout)

        # WIFI统计
        wifi_stats_layout = QVBoxLayout()
        wifi_stats_layout.addWidget(QLabel("WIFI:"))
        wifi_inner_layout = QHBoxLayout()
        wifi_inner_layout.addWidget(QLabel("测试:"))
        self.wifi_total_label = QLabel("0")
        wifi_inner_layout.addWidget(self.wifi_total_label)
        wifi_inner_layout.addWidget(QLabel("成功:"))
        self.wifi_success_label = QLabel("0")
        self.wifi_success_label.setStyleSheet("QLabel { color: #4CAF50; }")
        wifi_inner_layout.addWidget(self.wifi_success_label)
        wifi_inner_layout.addWidget(QLabel("成功率:"))
        self.wifi_rate_label = QLabel("0%")
        self.wifi_rate_label.setStyleSheet("QLabel { color: #009688; font-weight: bold; }")
        wifi_inner_layout.addWidget(self.wifi_rate_label)
        wifi_stats_layout.addLayout(wifi_inner_layout)
        network_stats_layout.addLayout(wifi_stats_layout)

        stats_layout.addLayout(network_stats_layout)

        # 统计控制按钮
        stats_control_layout = QHBoxLayout()
        self.refresh_stats_btn = QPushButton("刷新统计")
        self.refresh_stats_btn.clicked.connect(self.update_task_stats_display)
        stats_control_layout.addWidget(self.refresh_stats_btn)

        self.clear_stats_btn = QPushButton("清空统计")
        self.clear_stats_btn.clicked.connect(self.clear_task_stats)
        stats_control_layout.addWidget(self.clear_stats_btn)
        stats_control_layout.addStretch()

        stats_layout.addLayout(stats_control_layout)
        layout.addWidget(stats_group)
        layout.addStretch()
        return widget

    def create_log_tab(self):
        """创建日志选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 日志输出
        log_group = QGroupBox("任务日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))

        log_layout.addWidget(self.log_text)

        # 清空日志按钮
        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self.log_text.clear)
        log_layout.addWidget(clear_btn)

        layout.addWidget(log_group)
        return widget

    # 保留所有原有的功能方法，包括：
    # connect_signals, load_config, apply_config_to_ui, get_config_from_ui,
    # sync_device_ratios, sync_network_ratios, validate_config, update_calculation,
    # update_task_stats_display, clear_task_stats, start_manual_test,
    # on_manual_test_completed, start_tasks, pause_tasks, stop_tasks,
    # 各种槽函数，控件状态更新函数，日志函数等

    # 这里省略了其他功能方法的重复，因为它们与原始代码完全相同
    # 只需要确保所有原有的功能都被保留

    def connect_signals(self):
        """连接信号和槽"""
        # 任务管理器信号
        self.task_manager.task_started.connect(self.on_task_started)
        self.task_manager.task_progress.connect(self.on_task_progress)
        self.task_manager.task_finished.connect(self.on_task_finished)
        self.task_manager.task_error.connect(self.on_task_error)
        self.task_manager.status_updated.connect(self.on_status_updated)
        self.task_manager.all_tasks_completed.connect(self.on_all_tasks_completed)
        self.task_manager.time_limit_reached.connect(self.on_time_limit_reached)
        self.task_manager.manual_test_completed.connect(self.on_manual_test_completed)

        # 按钮信号
        self.start_btn.clicked.connect(self.start_tasks)
        self.manual_test_btn.clicked.connect(self.start_manual_test)
        self.pause_btn.clicked.connect(self.pause_tasks)
        self.stop_btn.clicked.connect(self.stop_tasks)

    def load_config(self):
        """加载配置"""
        self.current_config = self.config_manager.load_config()
        self.apply_config_to_ui()

    def apply_config_to_ui(self):
        """将配置应用到UI"""
        config = self.current_config

        self.target_url_edit.setText(config.target_url)
        self.platform_combo.setCurrentText(config.platform.value)
        self.ua_combo.setCurrentText(config.ua_type.value)
        self.thread_spin.setValue(config.thread_count)

        # 任务设置
        self.total_processes_spin.setValue(config.total_processes)
        self.total_minutes_spin.setValue(config.total_minutes)

        # 功能设置
        self.auto_click_check.setChecked(config.auto_click_links)
        self.auto_click_ratio_spin.setValue(config.auto_click_ratio)
        self.auto_message_check.setChecked(config.auto_send_messages)
        self.auto_message_ratio_spin.setValue(config.auto_message_ratio)

        # 消息列表
        if config.message_list:
            self.message_text.setPlainText('\n'.join(config.message_list))
        else:
            self.message_text.clear()

        # 设备比例设置
        self.android_ratio_slider.setValue(config.android_ratio)
        self.ios_ratio_slider.setValue(config.ios_ratio)

        # 网络类型比例设置
        self.mobile_data_ratio_slider.setValue(config.mobile_data_ratio)
        self.wifi_ratio_slider.setValue(config.wifi_ratio)

        # 高级设置
        self.random_stay_check.setChecked(config.random_stay_time)
        self.min_stay_spin.setValue(config.min_stay_time)
        self.max_stay_spin.setValue(config.max_stay_time)
        self.bypass_verification_check.setChecked(config.bypass_verification)

        # 更新控件状态
        self.on_random_stay_changed(config.random_stay_time)
        self.on_auto_message_changed(config.auto_send_messages)
        self.update_calculation()

    def get_config_from_ui(self) -> TaskConfig:
        """从UI获取配置"""
        config = TaskConfig()

        # 基本设置
        config.target_url = self.target_url_edit.text().strip()
        config.platform = Platform(self.platform_combo.currentText())
        config.ua_type = UAType(self.ua_combo.currentText())
        config.thread_count = self.thread_spin.value()

        # 任务设置
        config.total_processes = self.total_processes_spin.value()
        config.total_minutes = self.total_minutes_spin.value()

        # 功能设置
        config.auto_click_links = self.auto_click_check.isChecked()
        config.auto_click_ratio = self.auto_click_ratio_spin.value()
        config.auto_send_messages = self.auto_message_check.isChecked()
        config.auto_message_ratio = self.auto_message_ratio_spin.value()

        # 消息列表
        message_text = self.message_text.toPlainText().strip()
        if message_text:
            config.message_list = [msg.strip() for msg in message_text.split('\n') if msg.strip()]
        else:
            config.message_list = []

        # 设备比例设置
        config.android_ratio = self.android_ratio_slider.value()
        config.ios_ratio = self.ios_ratio_slider.value()

        # 网络类型比例设置
        config.mobile_data_ratio = self.mobile_data_ratio_slider.value()
        config.wifi_ratio = self.wifi_ratio_slider.value()

        # 高级设置
        config.random_stay_time = self.random_stay_check.isChecked()
        config.min_stay_time = self.min_stay_spin.value()
        config.max_stay_time = self.max_stay_spin.value()
        config.bypass_verification = self.bypass_verification_check.isChecked()

        return config

    def sync_device_ratios(self):
        """同步设备比例设置"""
        android_ratio = self.android_ratio_slider.value()
        ios_ratio = self.ios_ratio_slider.value()

        total = android_ratio + ios_ratio
        if total != 100:
            # 自动调整比例，保持总和为100%
            if android_ratio > ios_ratio:
                self.android_ratio_slider.setValue(100 - ios_ratio)
            else:
                self.ios_ratio_slider.setValue(100 - android_ratio)

    def sync_network_ratios(self):
        """同步网络类型比例设置"""
        mobile_data_ratio = self.mobile_data_ratio_slider.value()
        wifi_ratio = self.wifi_ratio_slider.value()

        total = mobile_data_ratio + wifi_ratio
        if total != 100:
            # 自动调整比例，保持总和为100%
            if mobile_data_ratio > wifi_ratio:
                self.mobile_data_ratio_slider.setValue(100 - wifi_ratio)
            else:
                self.wifi_ratio_slider.setValue(100 - mobile_data_ratio)

    def validate_config(self, config: TaskConfig, is_manual_test: bool = False) -> bool:
        """验证配置"""
        if not Validators.validate_url(config.target_url):
            QMessageBox.warning(self, "输入错误", "请输入有效的目标URL")
            return False

        if not is_manual_test:  # 批量任务才需要验证这些
            if not Validators.validate_thread_count(config.thread_count):
                QMessageBox.warning(self, "输入错误", "线程数必须在1-100之间")
                return False

            if config.total_processes <= 0:
                QMessageBox.warning(self, "输入错误", "总进程数必须大于0")
                return False

            if config.total_minutes <= 0:
                QMessageBox.warning(self, "输入错误", "总时间必须大于0")
                return False

        if config.random_stay_time:
            if not Validators.validate_stay_time_range(config.min_stay_time, config.max_stay_time):
                QMessageBox.warning(self, "输入错误", "停留时间范围无效")
                return False

        # 验证自动发送消息配置
        if config.auto_send_messages:
            if not config.message_list:
                QMessageBox.warning(self, "输入错误", "启用了自动发送消息，但消息列表不能为空")
                return False
            for i, msg in enumerate(config.message_list):
                if not msg.strip():
                    QMessageBox.warning(self, "输入错误", f"第 {i + 1} 条消息不能为空")
                    return False

        return True

    def update_calculation(self):
        """更新计算信息"""
        total_processes = self.total_processes_spin.value()
        total_minutes = self.total_minutes_spin.value()
        thread_count = self.thread_spin.value()

        total_seconds = total_minutes * 60

        if thread_count > 0:
            # 计算理论循环次数
            cycles = math.ceil(total_processes / thread_count)
            # 计算平均每轮时间
            avg_cycle_time = total_seconds / cycles if cycles > 0 else 0
            # 计算平均每个进程时间
            avg_process_time = total_seconds / total_processes if total_processes > 0 else 0

            info_text = (
                f"理论循环: {cycles}轮 | "
                f"每轮: {avg_cycle_time:.1f}秒 | "
                f"每个进程: {avg_process_time:.1f}秒"
            )

            self.calc_label.setText(info_text)
            self.cycle_label.setText(f"{cycles}轮")

    def update_task_stats_display(self):
        """更新任务统计显示"""
        stats = self.task_stats_manager.get_stats_summary()

        # 更新总体统计
        self.total_tests_label.setText(str(stats['total_tests']))
        self.success_rate_label.setText(f"{stats['overall_success_rate']:.1f}%")

        # 更新设备统计
        self.android_total_label.setText(str(stats['android_total']))
        self.android_success_label.setText(str(stats['android_success']))
        self.android_rate_label.setText(f"{stats['android_success_rate']:.1f}%")

        self.ios_total_label.setText(str(stats['ios_total']))
        self.ios_success_label.setText(str(stats['ios_success']))
        self.ios_rate_label.setText(f"{stats['ios_success_rate']:.1f}%")

        # 更新网络统计
        self.mobile_data_total_label.setText(str(stats['mobile_data_total']))
        self.mobile_data_success_label.setText(str(stats['mobile_data_success']))
        self.mobile_data_rate_label.setText(f"{stats['mobile_data_success_rate']:.1f}%")

        self.wifi_total_label.setText(str(stats['wifi_total']))
        self.wifi_success_label.setText(str(stats['wifi_success']))
        self.wifi_rate_label.setText(f"{stats['wifi_success_rate']:.1f}%")

    def clear_task_stats(self):
        """清空任务统计"""
        reply = QMessageBox.question(self, "确认清空",
                                     "确定要清空当前任务的统计数据吗？此操作不可恢复！",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.task_stats_manager.clear_stats()
            self.update_task_stats_display()
            self.log_message("任务统计数据已清空")

    def start_manual_test(self):
        """开始手动检测"""
        config = self.get_config_from_ui()

        if not self.validate_config(config, is_manual_test=True):
            return

        # 更新UI状态
        self.manual_test_btn.setEnabled(False)
        self.manual_status_label.setText("检测中...")
        self.manual_status_label.setStyleSheet("QLabel { color: #2196F3; font-weight: bold; }")

        # 记录日志
        self.log_message("开始手动检测...")
        self.log_message(f"检测目标: {config.target_url}")
        self.log_message(f"平台类型: {config.platform.value}")
        self.log_message(f"设备比例: 安卓{config.android_ratio}% / iOS{config.ios_ratio}%")
        self.log_message(f"网络比例: 移动数据{config.mobile_data_ratio}% / WIFI{config.wifi_ratio}%")

        # 启动手动检测，传递任务统计管理器
        self.task_manager.start_manual_test(config, self.config_manager, self.task_stats_manager)

    def on_manual_test_completed(self, success: bool, message: str):
        """手动检测完成"""
        # 更新UI状态
        self.manual_test_btn.setEnabled(True)

        if success:
            self.manual_status_label.setText("检测成功")
            self.manual_status_label.setStyleSheet("QLabel { color: #4CAF50; font-weight: bold; }")
            self.log_message(f"手动检测成功: {message}")
        else:
            self.manual_status_label.setText("检测失败")
            self.manual_status_label.setStyleSheet("QLabel { color: #F44336; font-weight: bold; }")
            self.log_message(f"手动检测失败: {message}")

        # 更新统计显示
        self.update_task_stats_display()

    def start_tasks(self):
        """开始批量任务"""
        if self.task_manager.is_manual_test_active():
            QMessageBox.warning(self, "操作冲突", "手动检测正在运行，请等待手动检测完成")
            return

        config = self.get_config_from_ui()

        if not self.validate_config(config, is_manual_test=False):
            return

        # 保存配置
        self.config_manager.save_config(config)
        self.current_config = config

        # 更新UI状态
        self.set_controls_enabled(False)
        self.status_label.setText("运行中")
        self.status_label.setStyleSheet("QLabel { color: #4CAF50; font-weight: bold; }")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # 记录日志
        self.log_message(f"开始批量任务 - {self.title}")
        self.log_message(f"目标: {config.total_processes}个进程在{config.total_minutes}分钟内完成")
        self.log_message(f"线程数: {config.thread_count}")
        self.log_message(f"目标地址: {config.target_url}")
        self.log_message(f"设备比例: 安卓{config.android_ratio}% / iOS{config.ios_ratio}%")
        self.log_message(f"网络比例: 移动数据{config.mobile_data_ratio}% / WIFI{config.wifi_ratio}%")

        if config.auto_click_links:
            self.log_message(f"自动点击链接比例: {config.auto_click_ratio}%")

        if config.auto_send_messages:
            self.log_message(f"自动发送消息比例: {config.auto_message_ratio}%")

        # 显示计算信息
        cycles = math.ceil(config.total_processes / config.thread_count)
        avg_cycle_time = (config.total_minutes * 60) / cycles
        self.log_message(f"理论循环: {cycles}轮，平均每轮: {avg_cycle_time:.1f}秒")

        # 启动任务，传递任务统计管理器
        self.task_manager.start_tasks(config, self.config_manager, self.task_stats_manager)

        # 发射状态改变信号
        self.task_status_changed.emit(self.title, "running")

    def pause_tasks(self):
        """暂停任务"""
        if self.task_manager.is_paused:
            self.task_manager.resume_tasks()
            self.pause_btn.setText("暂停任务")
            self.status_label.setText("运行中")
            self.task_status_changed.emit(self.title, "running")
        else:
            self.task_manager.pause_tasks()
            self.pause_btn.setText("恢复任务")
            self.status_label.setText("已暂停")
            self.task_status_changed.emit(self.title, "paused")

    def stop_tasks(self):
        """停止任务"""
        if self.task_manager.is_manual_test_active():
            self.task_manager.stop_manual_test()
            self.manual_test_btn.setEnabled(True)
            self.manual_status_label.setText("已停止")
            self.manual_status_label.setStyleSheet("QLabel { color: #FF9800; font-weight: bold; }")
            self.log_message("手动检测已停止")
        else:
            self.task_manager.stop_tasks()

    # 槽函数
    @pyqtSlot(int)
    def on_task_started(self, task_id):
        self.log_message(f"任务 {task_id} 已开始")

    @pyqtSlot(int, str)
    def on_task_progress(self, task_id, message):
        self.log_message(f"任务 {task_id}: {message}")

    @pyqtSlot(int, bool)
    def on_task_finished(self, task_id, success):
        status = "成功" if success else "失败"
        self.log_message(f"任务 {task_id} 已完成 - {status}")

    @pyqtSlot(int, str)
    def on_task_error(self, task_id, error_msg):
        self.log_message(f"任务 {task_id} 错误: {error_msg}", "ERROR")

    @pyqtSlot(int, int, int)
    def on_status_updated(self, running_count, completed_count, scheduled_count):
        """状态更新槽函数"""
        self.thread_count_label.setText(str(running_count))

        # 更新进度显示
        target = self.task_manager.get_target_processes()
        if target > 0:
            progress_percent = (completed_count / target) * 100
            self.progress_label.setText(f"{completed_count}/{target} ({progress_percent:.1f}%)")
            self.progress_bar.setValue(int(progress_percent))

    @pyqtSlot()
    def on_all_tasks_completed(self):
        """所有任务完成槽函数"""
        self.set_controls_enabled(True)
        completed = self.task_manager.get_completed_processes()
        target = self.task_manager.get_target_processes()
        completion_rate = (completed / target * 100) if target > 0 else 0

        self.status_label.setText(f"已完成 ({completion_rate:.1f}%)")
        self.status_label.setStyleSheet("QLabel { color: #2196F3; font-weight: bold; }")
        self.progress_bar.setVisible(False)
        self.pause_btn.setText("暂停任务")

        total_time = self.task_manager.get_time_elapsed()
        self.log_message(f"批量任务完成: {completed}/{target} 个进程 ({completion_rate:.1f}%)")
        self.log_message(f"实际用时: {total_time:.1f}秒")

        # 更新统计显示
        self.update_task_stats_display()

        self.task_status_changed.emit(self.title, "stopped")

    @pyqtSlot()
    def on_time_limit_reached(self):
        """时间到达"""
        completed = self.task_manager.get_completed_processes()
        target = self.task_manager.get_target_processes()
        completion_rate = (completed / target * 100) if target > 0 else 0

        self.log_message(f"时间到达，完成 {completed}/{target} 个进程 ({completion_rate:.1f}%)")
        self.set_controls_enabled(True)
        self.status_label.setText("时间到达")
        self.status_label.setStyleSheet("QLabel { color: #FF9800; font-weight: bold; }")
        self.progress_bar.setVisible(False)

        # 更新统计显示
        self.update_task_stats_display()

        self.task_status_changed.emit(self.title, "timeout")

    # 控件状态更新函数
    def on_random_stay_changed(self, enabled):
        self.min_stay_spin.setEnabled(enabled)
        self.max_stay_spin.setEnabled(enabled)

    def on_auto_message_changed(self, enabled):
        self.message_text.setEnabled(enabled)
        if enabled:
            self.message_text.setStyleSheet("QTextEdit { background-color: white; }")
        else:
            self.message_text.setStyleSheet("QTextEdit { background-color: #f0f0f0; }")

    def set_controls_enabled(self, enabled):
        """设置控件启用状态"""
        controls = [
            self.target_url_edit, self.platform_combo, self.ua_combo,
            self.thread_spin, self.total_processes_spin, self.total_minutes_spin,
            self.auto_click_check, self.auto_click_ratio_spin,
            self.auto_message_check, self.auto_message_ratio_spin,
            self.random_stay_check, self.bypass_verification_check,
            self.android_ratio_slider, self.ios_ratio_slider,
            self.mobile_data_ratio_slider, self.wifi_ratio_slider,
            self.start_btn, self.manual_test_btn
        ]

        for control in controls:
            control.setEnabled(enabled)

        # 特殊控件状态
        self.on_random_stay_changed(enabled and self.random_stay_check.isChecked())
        self.on_auto_message_changed(enabled and self.auto_message_check.isChecked())

        # 暂停/停止按钮的状态
        self.pause_btn.setEnabled(not enabled)
        self.stop_btn.setEnabled(not enabled)

        # 手动检测按钮特殊处理
        if enabled:
            self.manual_test_btn.setEnabled(True)
        else:
            self.manual_test_btn.setEnabled(False)

    def log_message(self, message, level="INFO"):
        """记录日志消息"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if level == "ERROR":
            color = "color: red;"
        elif level == "WARNING":
            color = "color: orange;"
        else:
            color = "color: blue;"

        log_entry = f'<span style="{color}">[{timestamp}] {level}: {message}</span>'
        self.log_text.append(log_entry)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def update_status(self):
        """更新状态显示"""
        if self.task_manager.is_running:
            # 更新剩余时间
            remaining_time = self.task_manager.get_time_remaining()
            minutes = int(remaining_time // 60)
            seconds = int(remaining_time % 60)
            self.time_remaining_label.setText(f"{minutes:02d}:{seconds:02d}")

            # 更新完成率
            completion_rate = self.task_manager.get_completion_rate()

            if self.task_manager.is_paused:
                status_text = f"已暂停 ({completion_rate:.1f}%)"
                self.status_label.setStyleSheet("QLabel { color: #FF9800; font-weight: bold; }")
            else:
                status_text = f"运行中 ({completion_rate:.1f}%)"
                self.status_label.setStyleSheet("QLabel { color: #4CAF50; font-weight: bold; }")

            self.status_label.setText(status_text)