import sys
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget, QLabel, QHBoxLayout, QFrame,QSpacerItem,QSizePolicy

class PerformanceMonitorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("性能监控工具箱")
        self.setGeometry(100, 100, 800, 600)

        self.layout = QVBoxLayout(self)
        
        # 创建一个水平布局来容纳标题和FPS信息
        self.title_layout = QHBoxLayout()
        
        # 显示软件名称
        self.title_label = QLabel("性能监控工具箱", self)
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px;")
        
        # FPS 信息标签
        self.fps_info = QLabel(self)
        self.fps_info.setStyleSheet("font-size: 24px; padding: 10px;")
        self.title_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)  # 不扩展
        # 将标题和信息标签添加到水平布局中
        self.title_layout.addWidget(self.title_label)
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.title_layout.addItem(spacer)  # 添加间隔项
        self.title_layout.addWidget(self.fps_info)

        # 将水平布局添加到主布局中
        self.layout.addLayout(self.title_layout)

        # FPS 图
        self.fps_canvas = FigureCanvas(plt.Figure())
        self.ax = self.fps_canvas.figure.add_subplot(111)
        self.layout.addWidget(self.fps_canvas)

        # CPU 和 GPU 图
        self.cpu_gpu_layout = QHBoxLayout()

        # CPU 图
        self.cpu_canvas = FigureCanvas(plt.Figure())
        self.cpu_ax = self.cpu_canvas.figure.add_subplot(111)
        self.cpu_gpu_layout.addWidget(self.cpu_canvas)

        # GPU 图
        self.gpu_canvas = FigureCanvas(plt.Figure())
        self.gpu_ax = self.gpu_canvas.figure.add_subplot(111)
        self.cpu_gpu_layout.addWidget(self.gpu_canvas)

        self.layout.addLayout(self.cpu_gpu_layout)

        # 生成测试数据并实时更新图表
        self.fps_data = []
        self.cpu_data = []
        self.gpu_data = []
        self.current_frame = 0

        # 启动定时器
        self.timer = self.startTimer(1000)  # 每秒更新一次
        self.show()

    def timerEvent(self, event):
        self.update_fps_plot(self.current_frame)
        self.update_cpu_plot(self.current_frame)
        self.update_gpu_plot(self.current_frame)

    def update_fps_plot(self, frame):
        self.current_frame += 1
        self.fps_data.append(random.uniform(20, 60))  # 随机模拟帧率

        self.ax.clear()
        self.ax.plot(self.fps_data, color='blue', linewidth=2)
        self.ax.set_ylim(0, 100)
        self.ax.set_title("FPS 实时监控", fontsize=16, pad=20)  # 调整标题位置
        self.ax.set_xlabel("时间", fontsize=12)
        self.ax.set_ylabel("FPS", fontsize=12)

        avg_fps = sum(self.fps_data) / len(self.fps_data)
        min_fps = min(self.fps_data)
        self.fps_info.setText(f"平均帧率: {avg_fps:.2f} 最低帧率: {min_fps:.2f}")

        self.fps_canvas.draw()  # 更新图形

    def update_cpu_plot(self, frame):
        cpu_value = random.uniform(0, 100)  # 随机模拟CPU使用率
        self.cpu_data.append(cpu_value)
        self.cpu_ax.clear()
        self.cpu_ax.plot(self.cpu_data, color='green', linewidth=2)
        self.cpu_ax.set_title("CPU 使用率", fontsize=16, pad=20)  # 调整标题位置
        self.cpu_ax.set_xlabel("时间", fontsize=12)
        self.cpu_ax.set_ylabel("使用率 (%)", fontsize=12)
        self.cpu_ax.set_ylim(0, 100)

        self.cpu_canvas.draw()  # 更新图形

    def update_gpu_plot(self, frame):
        gpu_value = random.uniform(0, 100)  # 随机模拟GPU使用率
        self.gpu_data.append(gpu_value)
        self.gpu_ax.clear()
        self.gpu_ax.plot(self.gpu_data, color='orange', linewidth=2)
        self.gpu_ax.set_title("GPU 使用率", fontsize=16, pad=20)  # 调整标题位置
        self.gpu_ax.set_xlabel("时间", fontsize=12)
        self.gpu_ax.set_ylabel("使用率 (%)", fontsize=12)
        self.gpu_ax.set_ylim(0, 100)

        self.gpu_canvas.draw()  # 更新图形

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PerformanceMonitorApp()
    window.show()
    sys.exit(app.exec_())
