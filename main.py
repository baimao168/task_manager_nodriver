import sys
import os
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# 添加app目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.multi_task_manager import MultiTaskManager


def setup_logging():
    """设置日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("task_manager.log"),
            logging.StreamHandler()
        ]
    )


if __name__ == "__main__":
    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("多任务管理器")
    app.setApplicationVersion("1.0.0")

    # 创建多任务管理器主窗口
    main_window = MultiTaskManager()
    main_window.show()

    sys.exit(app.exec_())