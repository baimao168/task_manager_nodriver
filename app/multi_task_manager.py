import logging
import os
import json
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QListWidget, QListWidgetItem, QLabel,
                             QSplitter, QGroupBox, QLineEdit, QMessageBox,
                             QTabWidget, QInputDialog, QToolBar, QAction, QTabBar)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QIcon, QFont

from app.task_window import TaskWindow


class MultiTaskManager(QMainWindow):
    """多任务管理器主窗口"""

    def __init__(self):
        super().__init__()
        self.task_windows = {}  # 存储任务窗口 {title: window}
        self.next_task_number = 1
        self.init_ui()
        self.connect_signals()
        self.load_existing_tasks()  # 启动时加载已存在的任务

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("多任务管理器 - 可管理多个独立任务窗口")
        self.setGeometry(100, 100, 1400, 900)

        # 创建工具栏
        self.create_toolbar()

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧任务列表面板
        left_widget = self.create_task_list_panel()
        splitter.addWidget(left_widget)

        # 右侧内容区域
        right_widget = self.create_content_panel()
        splitter.addWidget(right_widget)

        # 设置分割器比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([300, 1100])

        main_layout.addWidget(splitter)

        # 状态栏
        self.statusBar().showMessage("就绪 - 点击'添加任务'创建新任务窗口")

    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)

        # 添加任务动作
        add_action = QAction("添加任务", self)
        add_action.setStatusTip("添加一个新的任务窗口")
        add_action.triggered.connect(self.add_task)
        toolbar.addAction(add_action)

        # 删除任务动作
        remove_action = QAction("删除任务", self)
        remove_action.setStatusTip("删除选中的任务窗口")
        remove_action.triggered.connect(self.remove_task)
        toolbar.addAction(remove_action)

        toolbar.addSeparator()

        # 刷新任务列表动作
        refresh_action = QAction("刷新列表", self)
        refresh_action.setStatusTip("刷新任务列表")
        refresh_action.triggered.connect(self.refresh_task_list)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        # 全部开始动作
        start_all_action = QAction("全部开始", self)
        start_all_action.setStatusTip("开始所有任务")
        start_all_action.triggered.connect(self.start_all_tasks)
        toolbar.addAction(start_all_action)

        # 全部停止动作
        stop_all_action = QAction("全部停止", self)
        stop_all_action.setStatusTip("停止所有任务")
        stop_all_action.triggered.connect(self.stop_all_tasks)
        toolbar.addAction(stop_all_action)

    def create_task_list_panel(self):
        """创建任务列表面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 任务列表组
        task_group = QGroupBox("任务列表")
        task_layout = QVBoxLayout(task_group)

        # 任务操作按钮
        button_layout = QHBoxLayout()

        self.add_task_btn = QPushButton("添加任务")
        self.add_task_btn.setStyleSheet("""
            QPushButton { 
                background-color: #4CAF50; 
                color: white; 
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(self.add_task_btn)

        self.remove_task_btn = QPushButton("删除任务")
        self.remove_task_btn.setStyleSheet("""
            QPushButton { 
                background-color: #F44336; 
                color: white; 
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.remove_task_btn.setEnabled(False)
        button_layout.addWidget(self.remove_task_btn)

        self.refresh_btn = QPushButton("刷新列表")
        self.refresh_btn.setStyleSheet("""
            QPushButton { 
                background-color: #2196F3; 
                color: white; 
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        button_layout.addWidget(self.refresh_btn)

        task_layout.addLayout(button_layout)

        # 任务列表
        self.task_list = QListWidget()
        self.task_list.setFont(QFont("Arial", 10))
        self.task_list.itemDoubleClicked.connect(self.on_task_double_clicked)
        self.task_list.itemSelectionChanged.connect(self.on_task_selection_changed)
        task_layout.addWidget(self.task_list)

        # 任务统计
        stats_group = QGroupBox("统计信息")
        stats_layout = QVBoxLayout(stats_group)

        total_layout = QHBoxLayout()
        total_layout.addWidget(QLabel("总任务窗口:"))
        self.total_tasks_label = QLabel("0")
        self.total_tasks_label.setStyleSheet("QLabel { color: #2196F3; font-weight: bold; font-size: 14px; }")
        total_layout.addWidget(self.total_tasks_label)
        total_layout.addStretch()
        stats_layout.addLayout(total_layout)

        running_layout = QHBoxLayout()
        running_layout.addWidget(QLabel("运行中:"))
        self.running_tasks_label = QLabel("0")
        self.running_tasks_label.setStyleSheet("QLabel { color: #4CAF50; font-weight: bold; font-size: 14px; }")
        running_layout.addWidget(self.running_tasks_label)
        running_layout.addStretch()
        stats_layout.addLayout(running_layout)

        paused_layout = QHBoxLayout()
        paused_layout.addWidget(QLabel("已暂停:"))
        self.paused_tasks_label = QLabel("0")
        self.paused_tasks_label.setStyleSheet("QLabel { color: #FF9800; font-weight: bold; font-size: 14px; }")
        paused_layout.addWidget(self.paused_tasks_label)
        paused_layout.addStretch()
        stats_layout.addLayout(paused_layout)

        task_layout.addWidget(stats_group)

        layout.addWidget(task_group)

        return widget

    def create_content_panel(self):
        """创建内容面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 使用选项卡显示多个任务窗口
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)

        layout.addWidget(self.tab_widget)

        # 初始提示
        self.create_welcome_tab()

        return widget

    def create_welcome_tab(self):
        """创建欢迎选项卡"""
        welcome_widget = QWidget()
        layout = QVBoxLayout(welcome_widget)

        welcome_label = QLabel("多任务管理器")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet("QLabel { font-size: 28px; color: #333; font-weight: bold; margin: 30px; }")
        layout.addWidget(welcome_label)

        hint_label = QLabel("点击\"添加任务\"按钮来创建新的任务窗口\n每个任务窗口都有独立的配置和运行状态")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("QLabel { font-size: 16px; color: #666; margin: 20px; line-height: 1.5; }")
        layout.addWidget(hint_label)

        features_label = QLabel(
            "功能特点:\n"
            "• 每个任务窗口独立运行\n"
            "• 相同的参数配置界面\n"
            "• 独立的任务管理和状态显示\n"
            "• 支持同时运行多个任务组\n"
            "• 自动保存和加载任务配置\n"
            "• 完善的手动检测功能"
        )
        features_label.setAlignment(Qt.AlignLeft)
        features_label.setStyleSheet(
            "QLabel { font-size: 14px; color: #555; margin: 20px; line-height: 1.8; background-color: #f5f5f5; padding: 15px; border-radius: 5px; }")
        layout.addWidget(features_label)

        layout.addStretch()

        # 修改：给欢迎选项卡一个特殊的标识
        self.tab_widget.addTab(welcome_widget, "欢迎")
        # 修改：使用setMovable而不是setTabEnabled来防止关闭
        self.tab_widget.setMovable(True)  # 允许选项卡重新排序

        # 设置欢迎选项卡为不可关闭（通过重写tabBar的鼠标事件）
        self.tab_widget.tabBar().setTabButton(0, QTabBar.RightSide, None)
        self.tab_widget.tabBar().setTabButton(0, QTabBar.LeftSide, None)

    def connect_signals(self):
        """连接信号和槽"""
        self.add_task_btn.clicked.connect(self.add_task)
        self.remove_task_btn.clicked.connect(self.remove_task)
        self.refresh_btn.clicked.connect(self.refresh_task_list)

    def load_existing_tasks(self):
        """加载已存在的任务配置"""
        try:
            # 查找当前目录下的所有任务配置文件
            config_files = [f for f in os.listdir('.')
                            if f.startswith('config_') and f.endswith('.json')]

            for config_file in config_files:
                try:
                    # 从文件名提取任务标题
                    title = config_file.replace('config_', '').replace('.json', '')

                    # 检查配置是否有效
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)

                    # 如果配置有效，创建任务窗口
                    if self.is_valid_config(config_data):
                        self.create_task_from_config(title, config_file)
                        logging.info(f"加载已存在任务: {title}")

                except Exception as e:
                    logging.error(f"加载任务配置 {config_file} 失败: {e}")
                    continue

            # 更新统计信息
            self.update_stats()

            if self.task_windows:
                self.statusBar().showMessage(f"已加载 {len(self.task_windows)} 个任务")
            else:
                self.statusBar().showMessage("未找到已保存的任务配置")

        except Exception as e:
            logging.error(f"加载已存在任务时出错: {e}")

    def is_valid_config(self, config_data: dict) -> bool:
        """检查配置是否有效"""
        try:
            # 检查必要的配置字段
            required_fields = ['target_url', 'platform', 'ua_type']
            for field in required_fields:
                if field not in config_data:
                    return False

            # 检查URL是否有效
            target_url = config_data.get('target_url', '').strip()
            if not target_url:
                return False

            return True

        except:
            return False

    def create_task_from_config(self, title: str, config_file: str):
        """从配置创建任务窗口"""
        try:
            # 检查任务是否已存在
            if title in self.task_windows:
                logging.warning(f"任务 '{title}' 已存在，跳过加载")
                return

            # 创建任务窗口
            task_window = TaskWindow(title)

            # 存储任务窗口引用
            self.task_windows[title] = task_window

            # 添加到任务列表
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, title)
            self.task_list.addItem(item)

            # 添加到选项卡
            tab_index = self.tab_widget.addTab(task_window, title)

            # 连接任务窗口的状态信号
            task_window.task_status_changed.connect(self.on_task_status_changed)

            # 更新下一个任务编号
            try:
                # 从标题中提取数字，用于设置下一个任务编号
                if title.startswith('任务窗口_'):
                    num_str = title.replace('任务窗口_', '')
                    if num_str.isdigit():
                        task_num = int(num_str)
                        if task_num >= self.next_task_number:
                            self.next_task_number = task_num + 1
            except:
                pass

            logging.info(f"成功加载任务窗口: {title}")

        except Exception as e:
            logging.error(f"从配置创建任务窗口失败 {title}: {e}")

    def add_task(self):
        """添加新任务窗口"""
        # 生成默认任务标题
        default_title = f"任务窗口_{self.next_task_number}"

        title, ok = QInputDialog.getText(
            self,
            "添加任务窗口",
            "请输入任务窗口标题:",
            text=default_title
        )

        if ok and title:
            title = title.strip()
            if not title:
                QMessageBox.warning(self, "输入错误", "任务窗口标题不能为空")
                return

            if title in self.task_windows:
                QMessageBox.warning(self, "错误", f"任务窗口标题 '{title}' 已存在")
                return

            # 创建新任务窗口
            task_window = TaskWindow(title)

            # 存储任务窗口引用
            self.task_windows[title] = task_window
            self.next_task_number += 1

            # 添加到任务列表
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, title)
            self.task_list.addItem(item)

            # 添加到选项卡
            tab_index = self.tab_widget.addTab(task_window, title)
            self.tab_widget.setCurrentIndex(tab_index)  # 自动切换到新添加的任务

            # 连接任务窗口的状态信号
            task_window.task_status_changed.connect(self.on_task_status_changed)

            # 更新统计
            self.update_stats()

            # 更新状态栏
            self.statusBar().showMessage(f"已添加任务窗口: {title}")

            logging.info(f"添加新任务窗口: {title}")

            # 新增：选中列表中的对应项
            self.task_list.setCurrentItem(item)

    def remove_task(self):
        """删除选中的任务窗口"""
        current_item = self.task_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个任务窗口")
            return

        title = current_item.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除任务窗口 '{title}' 吗？\n这将删除任务配置文件和任务数据。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # 停止任务
                task_window = self.task_windows[title]
                if task_window.task_manager.is_running or task_window.task_manager.is_manual_test_active():
                    task_window.task_manager.stop_tasks()

                # 从选项卡中移除
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.tabText(i) == title:
                        self.tab_widget.removeTab(i)
                        break

                # 从列表中移除
                self.task_list.takeItem(self.task_list.row(current_item))

                # 从存储中移除
                del self.task_windows[title]

                # 删除配置文件
                self.delete_task_files(title)

                # 更新统计
                self.update_stats()

                # 更新状态栏
                self.statusBar().showMessage(f"已删除任务窗口: {title}")

                logging.info(f"删除任务窗口: {title}")

                # 新增：如果删除后没有任务，切换到欢迎选项卡
                if self.tab_widget.count() == 1:  # 只剩下欢迎选项卡
                    self.tab_widget.setCurrentIndex(0)
                    self.task_list.clearSelection()

            except Exception as e:
                logging.error(f"删除任务窗口失败 {title}: {e}")
                QMessageBox.warning(self, "删除失败", f"删除任务窗口时出错: {e}")

    def delete_task_files(self, title: str):
        """删除任务相关的所有文件"""
        try:
            # 配置文件
            config_file = f"config_{title}.json"
            if os.path.exists(config_file):
                os.remove(config_file)
                logging.info(f"已删除配置文件: {config_file}")

            # 日志文件（如果有的话）
            log_file = f"task_manager_{title}.log"
            if os.path.exists(log_file):
                os.remove(log_file)
                logging.info(f"已删除日志文件: {log_file}")

            # 其他可能的数据文件
            data_files = [
                f"data_{title}.json",
                f"cache_{title}.db",
                f"session_{title}.pkl"
            ]

            for data_file in data_files:
                if os.path.exists(data_file):
                    os.remove(data_file)
                    logging.info(f"已删除数据文件: {data_file}")

        except Exception as e:
            logging.error(f"删除任务文件失败 {title}: {e}")
            # 不向用户显示这个错误，因为主要功能已经完成

    def refresh_task_list(self):
        """刷新任务列表"""
        try:
            # 保存当前选中的任务
            current_items = self.task_list.selectedItems()
            current_title = current_items[0].data(Qt.UserRole) if current_items else None

            # 清空当前列表
            self.task_list.clear()
            # 注意：不要清空 task_windows 和 tab_widget，否则会丢失正在运行的任务

            # 重新加载所有配置文件
            config_files = [f for f in os.listdir('.')
                            if f.startswith('config_') and f.endswith('.json')]

            loaded_titles = set()

            for config_file in config_files:
                try:
                    title = config_file.replace('config_', '').replace('.json', '')

                    # 如果任务窗口已存在，直接添加到列表
                    if title in self.task_windows:
                        item = QListWidgetItem(title)
                        item.setData(Qt.UserRole, title)
                        self.task_list.addItem(item)
                        loaded_titles.add(title)
                    else:
                        # 加载新发现的配置
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config_data = json.load(f)

                        if self.is_valid_config(config_data):
                            self.create_task_from_config(title, config_file)
                            loaded_titles.add(title)

                except Exception as e:
                    logging.error(f"刷新时加载配置 {config_file} 失败: {e}")
                    continue

            # 恢复选中状态
            if current_title and current_title in loaded_titles:
                for i in range(self.task_list.count()):
                    item = self.task_list.item(i)
                    if item.data(Qt.UserRole) == current_title:
                        item.setSelected(True)
                        self.switch_to_task_tab(current_title)  # 新增：切换到对应的选项卡
                        break

            self.update_stats()
            self.statusBar().showMessage(f"任务列表已刷新，共 {len(loaded_titles)} 个任务")

        except Exception as e:
            logging.error(f"刷新任务列表失败: {e}")
            QMessageBox.warning(self, "刷新失败", f"刷新任务列表时出错: {e}")

    def close_tab(self, index):
        """关闭选项卡"""
        # 修复：欢迎选项卡不能关闭
        if index == 0:
            QMessageBox.information(self, "提示", "欢迎窗口不能关闭")
            return

        title = self.tab_widget.tabText(index)

        # 修复：检查是否是欢迎窗口的特殊处理
        if title == "欢迎":
            return

        reply = QMessageBox.question(
            self,
            "确认关闭",
            f"确定要关闭任务窗口 '{title}' 吗？\n注意：这不会删除任务配置文件。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 从选项卡中移除
            self.tab_widget.removeTab(index)

            # 从列表中移除对应的项
            for i in range(self.task_list.count()):
                item = self.task_list.item(i)
                if item.data(Qt.UserRole) == title:
                    self.task_list.takeItem(i)
                    break

            # 从存储中移除
            if title in self.task_windows:
                task_window = self.task_windows[title]
                if task_window.task_manager.is_running or task_window.task_manager.is_manual_test_active():
                    task_window.task_manager.stop_tasks()
                del self.task_windows[title]

            # 更新统计
            self.update_stats()

            logging.info(f"关闭任务窗口: {title}")

            # 新增：如果关闭后没有任务选项卡，确保选中欢迎选项卡
            if self.tab_widget.count() == 1:  # 只剩下欢迎选项卡
                self.tab_widget.setCurrentIndex(0)
                # 清空任务列表选择
                self.task_list.clearSelection()

    def on_task_double_clicked(self, item):
        """双击任务项切换到对应选项卡"""
        title = item.data(Qt.UserRole)
        self.switch_to_task_tab(title)

    def on_task_selection_changed(self):
        """任务选择改变"""
        has_selection = len(self.task_list.selectedItems()) > 0
        self.remove_task_btn.setEnabled(has_selection)

        # 修复：选中任务时联动右侧选项卡
        if has_selection:
            current_item = self.task_list.currentItem()
            if current_item:
                title = current_item.data(Qt.UserRole)
                # 确保切换到对应的选项卡
                self.switch_to_task_tab(title)

    def switch_to_task_tab(self, title: str):
        """切换到指定任务选项卡"""
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == title:
                self.tab_widget.setCurrentIndex(i)
                return True
        # 如果没有找到对应的选项卡，可能是欢迎窗口
        return False

    @pyqtSlot(str, str)
    def on_task_status_changed(self, title, status):
        """任务状态改变"""
        # 更新列表项的显示
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            if item.data(Qt.UserRole) == title:
                # 根据状态设置不同的颜色
                if status == "running":
                    item.setForeground(Qt.darkGreen)
                elif status == "paused":
                    item.setForeground(Qt.darkYellow)
                elif status == "stopped":
                    item.setForeground(Qt.darkRed)
                elif status == "timeout":
                    item.setForeground(Qt.darkGray)
                else:
                    item.setForeground(Qt.black)
                break

        # 更新统计
        self.update_stats()

    def update_stats(self):
        """更新统计信息"""
        total_count = len(self.task_windows)
        running_count = 0
        paused_count = 0

        for task_window in self.task_windows.values():
            if task_window.task_manager.is_running:
                if task_window.task_manager.is_paused:
                    paused_count += 1
                else:
                    running_count += 1

        self.total_tasks_label.setText(str(total_count))
        self.running_tasks_label.setText(str(running_count))
        self.paused_tasks_label.setText(str(paused_count))

    def start_all_tasks(self):
        """开始所有任务"""
        if not self.task_windows:
            QMessageBox.information(self, "提示", "没有可启动的任务窗口")
            return

        started_count = 0
        for title, task_window in self.task_windows.items():
            if not task_window.task_manager.is_running:
                # 模拟点击开始按钮
                task_window.start_tasks()
                started_count += 1

        self.statusBar().showMessage(f"已启动 {started_count} 个任务窗口")
        logging.info(f"批量启动 {started_count} 个任务窗口")

    def stop_all_tasks(self):
        """停止所有任务"""
        if not self.task_windows:
            return

        stopped_count = 0
        for title, task_window in self.task_windows.items():
            if task_window.task_manager.is_running:
                task_window.task_manager.stop_tasks()
                stopped_count += 1

        self.statusBar().showMessage(f"已停止 {stopped_count} 个任务窗口")
        logging.info(f"批量停止 {stopped_count} 个任务窗口")

    def closeEvent(self, event):
        """关闭事件处理"""
        # 检查是否有运行中的任务
        running_tasks = []
        for title, task_window in self.task_windows.items():
            if task_window.task_manager.is_running or task_window.task_manager.is_manual_test_active():
                running_tasks.append(title)

        if running_tasks:
            reply = QMessageBox.question(
                self,
                "确认退出",
                f"有 {len(running_tasks)} 个任务正在运行，确定要退出吗？\n"
                f"运行中的任务: {', '.join(running_tasks[:5])}{'...' if len(running_tasks) > 5 else ''}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 停止所有任务
                self.stop_all_tasks()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()