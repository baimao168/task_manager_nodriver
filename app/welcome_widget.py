# welcome_widget.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QProgressBar, QTableWidget, QTableWidgetItem,
                             QHeaderView, QFrame, QSplitter, QPushButton,
                             QMessageBox, QTabWidget)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QFont, QColor, QBrush
import pyqtgraph as pg
import datetime
import numpy as np


class WelcomeWidget(QWidget):
    def __init__(self, statistics_manager):
        super().__init__()
        self.statistics_manager = statistics_manager
        self.init_ui()
        self.setup_refresh_timer()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 标题
        title_label = QLabel("📊 任务统计概览")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        main_layout.addWidget(title_label)

        # 创建标签页
        self.tab_widget = QTabWidget()

        # 概览标签页
        overview_tab = self.create_overview_tab()
        self.tab_widget.addTab(overview_tab, "概览")

        # 详细统计标签页
        details_tab = self.create_details_tab()
        self.tab_widget.addTab(details_tab, "详细统计")

        # 历史记录标签页
        history_tab = self.create_history_tab()
        self.tab_widget.addTab(history_tab, "历史记录")

        main_layout.addWidget(self.tab_widget)

        # 控制按钮
        control_layout = QHBoxLayout()
        control_layout.addStretch()

        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self.manual_refresh)
        self.refresh_btn.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; padding: 8px 16px; border-radius: 4px; }")

        self.clear_btn = QPushButton("🗑️ 清空统计")
        self.clear_btn.clicked.connect(self.clear_statistics)
        self.clear_btn.setStyleSheet(
            "QPushButton { background-color: #e74c3c; color: white; padding: 8px 16px; border-radius: 4px; }")

        control_layout.addWidget(self.refresh_btn)
        control_layout.addWidget(self.clear_btn)
        main_layout.addLayout(control_layout)

        self.apply_styles()

    def create_overview_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 关键指标卡片
        metrics_widget = self.create_metrics_widget()
        layout.addWidget(metrics_widget)

        # 图表区域
        charts_splitter = QSplitter(Qt.Horizontal)

        # 成功率趋势图
        success_chart = self.create_success_rate_chart()
        charts_splitter.addWidget(success_chart)

        # 任务分布图
        distribution_chart = self.create_distribution_chart()
        charts_splitter.addWidget(distribution_chart)

        charts_splitter.setSizes([400, 300])
        layout.addWidget(charts_splitter)

        return widget

    def create_metrics_widget(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(10)

        # 总任务数卡片
        self.total_tasks_frame = self.create_metric_frame("总任务数", "0", "#3498db", "📈")
        layout.addWidget(self.total_tasks_frame)

        # 成功率卡片
        self.success_rate_frame = self.create_metric_frame("成功率", "0%", "#2ecc71", "✅")
        layout.addWidget(self.success_rate_frame)

        # 今日任务卡片
        self.today_tasks_frame = self.create_metric_frame("今日任务", "0", "#e74c3c", "📅")
        layout.addWidget(self.today_tasks_frame)

        # 平均时间卡片
        self.avg_time_frame = self.create_metric_frame("平均运行时间", "0s", "#f39c12", "⏱️")
        layout.addWidget(self.avg_time_frame)

        # 运行时长卡片
        self.total_time_frame = self.create_metric_frame("总运行时长", "0s", "#9b59b6", "🕒")
        layout.addWidget(self.total_time_frame)

        return widget

    def create_metric_frame(self, title, value, color, icon):
        frame = QFrame()
        frame.setMinimumHeight(80)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 8px;
                padding: 15px;
                margin: 2px;
            }}
        """)

        layout = QVBoxLayout(frame)

        # 标题行
        title_layout = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 16px;")
        title_label = QLabel(title)
        title_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # 数值
        value_label = QLabel(value)
        value_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)

        return frame

    def create_success_rate_chart(self):
        win = pg.GraphicsLayoutWidget()
        win.setBackground('w')
        plot = win.addPlot(title="24小时成功率趋势")
        plot.setLabel('left', '成功率', '%')
        plot.setLabel('bottom', '时间')
        plot.showGrid(x=True, y=True)
        plot.setYRange(0, 100)

        self.success_curve = plot.plot(pen=pg.mkPen(color='#2ecc71', width=3))
        self.success_scatter = pg.ScatterPlotItem(size=10, pen=pg.mkPen(color='#27ae60'), brush=pg.mkBrush('#27ae60'))
        plot.addItem(self.success_scatter)

        return win

    def create_distribution_chart(self):
        win = pg.GraphicsLayoutWidget()
        win.setBackground('w')
        plot = win.addPlot(title="平台任务分布")
        plot.showGrid(x=True, y=True)

        self.distribution_bars = pg.BarGraphItem(x=[], height=[], width=0.6, brush=pg.mkBrush('#3498db'))
        plot.addItem(self.distribution_bars)

        return win

    def create_details_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 平台统计表格
        platform_label = QLabel("平台统计")
        platform_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px 0;")
        layout.addWidget(platform_label)

        self.platform_table = QTableWidget()
        self.platform_table.setColumnCount(4)
        self.platform_table.setHorizontalHeaderLabels(["平台", "任务数", "成功数", "成功率"])
        self.platform_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.platform_table)

        # 小时统计表格
        hourly_label = QLabel("小时统计")
        hourly_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px 0;")
        layout.addWidget(hourly_label)

        self.hourly_table = QTableWidget()
        self.hourly_table.setColumnCount(4)
        self.hourly_table.setHorizontalHeaderLabels(["时间段", "任务数", "成功数", "成功率"])
        self.hourly_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.hourly_table)

        return widget

    def create_history_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        table_label = QLabel("最近任务记录")
        table_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px 0;")
        layout.addWidget(table_label)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(["任务ID", "时间", "状态", "运行时间", "平台", "URL"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.history_table.setColumnWidth(0, 80)  # 任务ID
        self.history_table.setColumnWidth(1, 120)  # 时间
        self.history_table.setColumnWidth(2, 60)  # 状态
        self.history_table.setColumnWidth(3, 80)  # 运行时间
        self.history_table.setColumnWidth(4, 100)  # 平台
        self.history_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)  # URL

        layout.addWidget(self.history_table)
        return widget

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Microsoft YaHei', Arial;
            }

            QTabWidget::pane {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
            }

            QTabBar::tab {
                background-color: #ecf0f1;
                color: #2c3e50;
                padding: 8px 16px;
                margin: 2px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
            }

            QTabBar::tab:selected {
                background-color: #3498db;
                color: white;
            }

            QTableWidget {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                alternate-background-color: #f8f9fa;
                gridline-color: #ecf0f1;
            }

            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #ecf0f1;
            }

            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }

            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)

    def setup_refresh_timer(self):
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_all_stats)
        self.refresh_timer.start(3000)  # 3秒刷新一次

    def manual_refresh(self):
        """手动刷新"""
        self.update_all_stats()
        QMessageBox.information(self, "刷新", "统计数据已刷新！")

    def clear_statistics(self):
        """清空统计"""
        reply = QMessageBox.question(self, "确认清空", "确定要清空所有统计数据吗？此操作不可恢复！",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.statistics_manager.clear_stats()
            self.update_all_stats()
            QMessageBox.information(self, "清空完成", "统计数据已清空！")

    def update_all_stats(self):
        """更新所有统计显示"""
        try:
            self.update_metrics()
            self.update_charts()
            self.update_tables()
        except Exception as e:
            logging.error(f"更新统计显示失败: {e}")

    def update_metrics(self):
        """更新关键指标"""
        total_tasks = self.statistics_manager.task_stats['total_tasks']
        success_rate = self.statistics_manager.get_success_rate()
        today_stats = self.statistics_manager.get_today_stats()
        avg_runtime = self.statistics_manager.get_avg_runtime()
        total_runtime = self.statistics_manager.task_stats['total_runtime']

        # 格式化运行时间
        if total_runtime > 3600:
            total_time_str = f"{total_runtime / 3600:.1f}h"
        elif total_runtime > 60:
            total_time_str = f"{total_runtime / 60:.1f}m"
        else:
            total_time_str = f"{total_runtime:.0f}s"

        # 更新指标卡片
        self.total_tasks_frame.findChildren(QLabel)[2].setText(str(total_tasks))
        self.success_rate_frame.findChildren(QLabel)[2].setText(f"{success_rate:.1f}%")
        self.today_tasks_frame.findChildren(QLabel)[2].setText(str(today_stats.get('tasks', 0)))
        self.avg_time_frame.findChildren(QLabel)[2].setText(f"{avg_runtime:.1f}s")
        self.total_time_frame.findChildren(QLabel)[2].setText(total_time_str)

    def update_charts(self):
        """更新图表"""
        # 更新成功率趋势图
        hourly_data = self.statistics_manager.get_hourly_success_rates(24)
        if hourly_data:
            hours = list(range(len(hourly_data)))
            success_rates = [data['success_rate'] for data in hourly_data]
            self.success_curve.setData(hours, success_rates)

            # 更新散点图
            self.success_scatter.setData(hours, success_rates)

        # 更新平台分布图
        platform_stats = self.statistics_manager.get_platform_stats()
        if platform_stats:
            platforms = [stats['name'] for stats in platform_stats]
            task_counts = [stats['tasks'] for stats in platform_stats]

            x = range(len(platforms))
            self.distribution_bars.setOpts(x=x, height=task_counts)

    def update_tables(self):
        """更新表格数据"""
        self.update_platform_table()
        self.update_hourly_table()
        self.update_history_table()

    def update_platform_table(self):
        """更新平台统计表格"""
        platform_stats = self.statistics_manager.get_platform_stats()
        self.platform_table.setRowCount(len(platform_stats))

        for row, stats in enumerate(platform_stats):
            self.platform_table.setItem(row, 0, QTableWidgetItem(stats['name']))
            self.platform_table.setItem(row, 1, QTableWidgetItem(str(stats['tasks'])))
            self.platform_table.setItem(row, 2, QTableWidgetItem(str(stats['success'])))
            self.platform_table.setItem(row, 3, QTableWidgetItem(f"{stats['success_rate']:.1f}%"))

    def update_hourly_table(self):
        """更新小时统计表格"""
        hourly_data = self.statistics_manager.get_hourly_success_rates(24)
        self.hourly_table.setRowCount(len(hourly_data))

        for row, data in enumerate(hourly_data):
            self.hourly_table.setItem(row, 0, QTableWidgetItem(data['hour']))
            self.hourly_table.setItem(row, 1, QTableWidgetItem(str(data['tasks'])))
            self.hourly_table.setItem(row, 2, QTableWidgetItem(str(data['success'])))

            success_rate_item = QTableWidgetItem(f"{data['success_rate']:.1f}%")
            # 根据成功率设置颜色
            if data['success_rate'] >= 80:
                success_rate_item.setForeground(QBrush(QColor('#27ae60')))
            elif data['success_rate'] >= 60:
                success_rate_item.setForeground(QBrush(QColor('#f39c12')))
            else:
                success_rate_item.setForeground(QBrush(QColor('#e74c3c')))
            self.hourly_table.setItem(row, 3, success_rate_item)

    def update_history_table(self):
        """更新历史记录表格"""
        recent_tasks = self.statistics_manager.get_recent_tasks(50)
        self.history_table.setRowCount(len(recent_tasks))

        for row, task in enumerate(recent_tasks):
            # 任务ID
            self.history_table.setItem(row, 0, QTableWidgetItem(str(task.get('task_id', ''))))

            # 时间
            timestamp = datetime.datetime.fromisoformat(task['timestamp'])
            time_str = timestamp.strftime("%m-%d %H:%M:%S")
            self.history_table.setItem(row, 1, QTableWidgetItem(time_str))

            # 状态
            status = "成功" if task['success'] else "失败"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QBrush(QColor('#27ae60') if task['success'] else QColor('#e74c3c')))
            self.history_table.setItem(row, 2, status_item)

            # 运行时间
            self.history_table.setItem(row, 3, QTableWidgetItem(f"{task['runtime']:.1f}s"))

            # 平台
            self.history_table.setItem(row, 4, QTableWidgetItem(task.get('platform', 'N/A')))

            # URL (截断显示)
            url = task.get('url', '')
            display_url = (url[:40] + "...") if len(url) > 40 else url
            url_item = QTableWidgetItem(display_url)
            url_item.setToolTip(url)  # 鼠标