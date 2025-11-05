import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, Any
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QPushButton, QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


@dataclass
class DeviceStats:
    """设备统计数据"""
    total_tests: int = 0
    successful_tests: int = 0
    failed_tests: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.successful_tests / self.total_tests) * 100


@dataclass
class GlobalStats:
    """全局统计数据"""
    android_stats: DeviceStats = None
    ios_stats: DeviceStats = None
    total_tests: int = 0
    successful_tests: int = 0
    failed_tests: int = 0

    def __post_init__(self):
        if self.android_stats is None:
            self.android_stats = DeviceStats()
        if self.ios_stats is None:
            self.ios_stats = DeviceStats()

    @property
    def overall_success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.successful_tests / self.total_tests) * 100

    @property
    def android_success_rate(self) -> float:
        return self.android_stats.success_rate

    @property
    def ios_success_rate(self) -> float:
        return self.ios_stats.success_rate


class StatsManager:
    """统计管理器"""

    def __init__(self, stats_file="global_stats.json"):
        self.stats_file = stats_file
        self.stats = GlobalStats()
        self.load_stats()

    def load_stats(self):
        """加载统计数据"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.stats = GlobalStats(
                        android_stats=DeviceStats(**data.get('android_stats', {})),
                        ios_stats=DeviceStats(**data.get('ios_stats', {})),
                        total_tests=data.get('total_tests', 0),
                        successful_tests=data.get('successful_tests', 0),
                        failed_tests=data.get('failed_tests', 0)
                    )
        except Exception as e:
            print(f"加载统计数据失败: {e}")
            self.stats = GlobalStats()

    def save_stats(self):
        """保存统计数据"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.stats), f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存统计数据失败: {e}")

    def update_stats(self, success: bool, device_type: str):
        """更新统计数据"""
        self.stats.total_tests += 1

        if success:
            self.stats.successful_tests += 1
            if device_type == 'android':
                self.stats.android_stats.total_tests += 1
                self.stats.android_stats.successful_tests += 1
            else:  # ios
                self.stats.ios_stats.total_tests += 1
                self.stats.ios_stats.successful_tests += 1
        else:
            self.stats.failed_tests += 1
            if device_type == 'android':
                self.stats.android_stats.total_tests += 1
                self.stats.android_stats.failed_tests += 1
            else:  # ios
                self.stats.ios_stats.total_tests += 1
                self.stats.ios_stats.failed_tests += 1

        self.save_stats()

    def clear_stats(self):
        """清空统计数据"""
        self.stats = GlobalStats()
        self.save_stats()

    def get_stats_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        return {
            'total_tests': self.stats.total_tests,
            'successful_tests': self.stats.successful_tests,
            'failed_tests': self.stats.failed_tests,
            'overall_success_rate': self.stats.overall_success_rate,
            'android_total': self.stats.android_stats.total_tests,
            'android_success': self.stats.android_stats.successful_tests,
            'android_success_rate': self.stats.android_success_rate,
            'ios_total': self.stats.ios_stats.total_tests,
            'ios_success': self.stats.ios_stats.successful_tests,
            'ios_success_rate': self.stats.ios_success_rate
        }


class WelcomeStatsWidget(QWidget):
    """欢迎页面统计组件"""

    clear_stats_requested = pyqtSignal()

    def __init__(self, stats_manager: StatsManager):
        super().__init__()
        self.stats_manager = stats_manager
        self.init_ui()
        self.update_display()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel("运行统计")
        title_label.setStyleSheet("QLabel { font-size: 18px; font-weight: bold; color: #333; margin: 10px; }")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 总体统计组
        overall_group = QGroupBox("总体统计")
        overall_layout = QVBoxLayout(overall_group)

        # 总体成功率
        overall_success_layout = QHBoxLayout()
        overall_success_layout.addWidget(QLabel("总体成功率:"))
        self.overall_success_label = QLabel("0%")
        self.overall_success_label.setStyleSheet("QLabel { color: #4CAF50; font-weight: bold; font-size: 16px; }")
        overall_success_layout.addWidget(self.overall_success_label)
        overall_success_layout.addStretch()
        overall_layout.addLayout(overall_success_layout)

        # 总体进度条
        self.overall_progress = QProgressBar()
        self.overall_progress.setMaximum(100)
        overall_layout.addWidget(self.overall_progress)

        # 测试次数
        tests_layout = QHBoxLayout()
        tests_layout.addWidget(QLabel("总测试次数:"))
        self.total_tests_label = QLabel("0")
        tests_layout.addWidget(self.total_tests_label)
        tests_layout.addStretch()

        tests_layout.addWidget(QLabel("成功:"))
        self.success_tests_label = QLabel("0")
        self.success_tests_label.setStyleSheet("QLabel { color: #4CAF50; }")
        tests_layout.addWidget(self.success_tests_label)

        tests_layout.addWidget(QLabel("失败:"))
        self.failed_tests_label = QLabel("0")
        self.failed_tests_label.setStyleSheet("QLabel { color: #F44336; }")
        tests_layout.addWidget(self.failed_tests_label)
        overall_layout.addLayout(tests_layout)

        # 设备统计组
        device_group = QGroupBox("设备统计")
        device_layout = QVBoxLayout(device_group)

        # 安卓统计
        android_group = QGroupBox("安卓设备")
        android_layout = QVBoxLayout(android_group)

        android_success_layout = QHBoxLayout()
        android_success_layout.addWidget(QLabel("成功率:"))
        self.android_success_label = QLabel("0%")
        self.android_success_label.setStyleSheet("QLabel { color: #2196F3; font-weight: bold; }")
        android_success_layout.addWidget(self.android_success_label)
        android_success_layout.addStretch()
        android_layout.addLayout(android_success_layout)

        self.android_progress = QProgressBar()
        self.android_progress.setMaximum(100)
        android_layout.addWidget(self.android_progress)

        android_counts_layout = QHBoxLayout()
        android_counts_layout.addWidget(QLabel("测试:"))
        self.android_total_label = QLabel("0")
        android_counts_layout.addWidget(self.android_total_label)

        android_counts_layout.addWidget(QLabel("成功:"))
        self.android_success_count_label = QLabel("0")
        self.android_success_count_label.setStyleSheet("QLabel { color: #4CAF50; }")
        android_counts_layout.addWidget(self.android_success_count_label)
        android_layout.addLayout(android_counts_layout)

        # iOS统计
        ios_group = QGroupBox("iOS设备")
        ios_layout = QVBoxLayout(ios_group)

        ios_success_layout = QHBoxLayout()
        ios_success_layout.addWidget(QLabel("成功率:"))
        self.ios_success_label = QLabel("0%")
        self.ios_success_label.setStyleSheet("QLabel { color: #FF5722; font-weight: bold; }")
        ios_success_layout.addWidget(self.ios_success_label)
        ios_success_layout.addStretch()
        ios_layout.addLayout(ios_success_layout)

        self.ios_progress = QProgressBar()
        self.ios_progress.setMaximum(100)
        ios_layout.addWidget(self.ios_progress)

        ios_counts_layout = QHBoxLayout()
        ios_counts_layout.addWidget(QLabel("测试:"))
        self.ios_total_label = QLabel("0")
        ios_counts_layout.addWidget(self.ios_total_label)

        ios_counts_layout.addWidget(QLabel("成功:"))
        self.ios_success_count_label = QLabel("0")
        self.ios_success_count_label.setStyleSheet("QLabel { color: #4CAF50; }")
        ios_counts_layout.addWidget(self.ios_success_count_label)
        ios_layout.addLayout(ios_counts_layout)

        # 添加到设备布局
        device_inner_layout = QHBoxLayout()
        device_inner_layout.addWidget(android_group)
        device_inner_layout.addWidget(ios_group)
        device_layout.addLayout(device_inner_layout)

        # 控制按钮
        control_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新统计")
        self.refresh_btn.clicked.connect(self.update_display)
        control_layout.addWidget(self.refresh_btn)

        self.clear_btn = QPushButton("清空统计")
        self.clear_btn.clicked.connect(self.clear_stats)
        control_layout.addWidget(self.clear_btn)
        control_layout.addStretch()

        # 添加到主布局
        layout.addWidget(overall_group)
        layout.addWidget(device_group)
        layout.addLayout(control_layout)
        layout.addStretch()

    def update_display(self):
        """更新显示"""
        stats = self.stats_manager.get_stats_summary()

        # 更新总体统计
        self.overall_success_label.setText(f"{stats['overall_success_rate']:.1f}%")
        self.overall_progress.setValue(int(stats['overall_success_rate']))
        self.total_tests_label.setText(str(stats['total_tests']))
        self.success_tests_label.setText(str(stats['successful_tests']))
        self.failed_tests_label.setText(str(stats['failed_tests']))

        # 更新安卓统计
        self.android_success_label.setText(f"{stats['android_success_rate']:.1f}%")
        self.android_progress.setValue(int(stats['android_success_rate']))
        self.android_total_label.setText(str(stats['android_total']))
        self.android_success_count_label.setText(str(stats['android_success']))

        # 更新iOS统计
        self.ios_success_label.setText(f"{stats['ios_success_rate']:.1f}%")
        self.ios_progress.setValue(int(stats['ios_success_rate']))
        self.ios_total_label.setText(str(stats['ios_total']))
        self.ios_success_count_label.setText(str(stats['ios_success']))

    def clear_stats(self):
        """清空统计"""
        reply = QMessageBox.question(self, "确认清空",
                                     "确定要清空所有统计数据吗？此操作不可恢复！",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.stats_manager.clear_stats()
            self.update_display()
            self.clear_stats_requested.emit()
            QMessageBox.information(self, "清空成功", "统计数据已清空")