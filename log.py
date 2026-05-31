import sys
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QApplication, QVBoxLayout, QWidget, QLabel, 
                             QHBoxLayout, QSpacerItem, QSizePolicy, 
                             QPushButton, QTextEdit, QDialog, QListWidget, QLineEdit)

import logging
import os
import re 
import sys
from optparse import OptionParser
from sys import exit
from ios_device import py_ios_device

from ios_device.remote.remote_lockdown import RemoteLockdownClient
from ios_device.servers.Instrument import  InstrumentServer
from demo.instrument_demo.sysmontap import  sysmontap
from ios_device.remote.remote_lockdown import RemoteLockdownClient

sys.path.append(os.getcwd())
from ios_device.util.lockdown import LockdownClient
from ios_device import py_ios_device
from PyQt5.QtCore import QTimer
from ios_device.remote.remote_lockdown import RemoteLockdownClient
from ios_device.servers.Instrument import  InstrumentServer
from demo.instrument_demo.sysmontap import  sysmontap

from ios_device import py_ios_device
from ios_device.servers.syslog import SyslogServer

class PerformanceMonitorApp(QWidget):
    def __init__(self, lockdown: RemoteLockdownClient, rep):
        super().__init__()

        
        self.filter = re.compile(r'metal-HUD: ([\d\.,]+)')

        self.lockdown = lockdown
        self.channel = rep

        logging.basicConfig(level=logging.INFO)
        self.syslog = SyslogServer(lockdown=self.lockdown)

        self.setWindowTitle("性能监控工具箱")
        self.setGeometry(100, 100, 1800, 1500)

        self.layout = QHBoxLayout(self)  # 改为水平布局

        # 创建左侧布局（2/3区域）
        self.left_layout = QVBoxLayout()
        
        # 创建一个水平布局来容纳标题和FPS信息
        self.title_layout = QHBoxLayout()
        
        # 显示软件名称
        self.title_label = QLabel("性能监控工具箱", self)
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px;")
        
        self.appname = QLabel(self)
        self.appname.setStyleSheet("font-size: 24px; padding: 10px;")
        #self.title_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)  # 不扩展

        # FPS 信息标签
        self.fps_info = QLabel(self)
        self.fps_info.setStyleSheet("font-size: 24px; padding: 10px;")
        self.title_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)  # 不扩展

        # 将标题和信息标签添加到水平布局中
        self.title_layout.addWidget(self.title_label)
        self.title_layout.addWidget(self.appname)
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.title_layout.addItem(spacer)  # 添加间隔项
        self.title_layout.addWidget(self.fps_info)

        # 将水平布局添加到左侧布局中
        self.left_layout.addLayout(self.title_layout)

        # FPS 图
        self.fps_canvas = FigureCanvas(plt.Figure())
        self.ax = self.fps_canvas.figure.add_subplot(111)
        self.left_layout.addWidget(self.fps_canvas)

        # 创建 CPU 和 GPU 图的布局（下部）
        self.cpu_gpu_layout = QVBoxLayout()

        # CPU 图
        self.cpu_canvas = FigureCanvas(plt.Figure())
        self.cpu_ax = self.cpu_canvas.figure.add_subplot(111)

        # GPU 图
        self.gpu_canvas = FigureCanvas(plt.Figure())
        self.gpu_ax = self.gpu_canvas.figure.add_subplot(111)

        # 将 CPU 和 GPU 图添加到 CPU/GPU 布局中
        self.cpu_gpu_layout.addWidget(self.cpu_canvas)
        self.cpu_gpu_layout.addWidget(self.gpu_canvas)

        # 将 CPU/GPU 布局添加到左侧布局中
        self.left_layout.addLayout(self.cpu_gpu_layout)

        # 将左侧布局添加到主布局中
        self.layout.addLayout(self.left_layout, stretch=2)  # 左侧布局占 2/3

        # 实时日志输出区域（右侧 1/3）
        self.log_output = QTextEdit(self)
        self.log_output.setReadOnly(True)  # 只读
        self.log_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 允许扩展

        self.layout.addWidget(self.log_output, stretch=1)  # 日志区域占 1/3

        # 选择进程按钮
        self.select_button = QPushButton("选择进程", self)
        self.select_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)  # 固定大小
        self.select_button.clicked.connect(self.show_process_list)

        # 将选择进程按钮添加到左侧布局的底部
        self.left_layout.addWidget(self.select_button)

        # 生成测试数据并实时更新图表
        self.fps_str = []
        self.fps_data = []
        self.cpu_data = []
        gpu_data = []
        self.fps_window = []
        self.current_frame = 0

        # 启动定时器
        #self.timer = self.startTimer(1000)  # 每秒更新一次
        #self.log_timer = self.startTimer(50)  # 每500毫秒更新一次日志
        self.log_timer = None
        self.Instant_timer = None
        self.show()

    def timerEvent(self, event):
        #self.update_fps_plot(self.current_frame)
        #self.update_cpu_plot(self.current_frame)
        #self.update_gpu_plot(self.current_frame)
        if event.timerId() == self.log_timer :
            self.logEvent(event)
            self.update_fps_plot()
        if  event.timerId() ==self.Instant_timer :
            self.instant_fps()

    def logEvent(self, event):
        self.update_log_output()  # 更新日志输出

    def instant_fps(self):
        if len(self.fps_data) >= 120 :
            avg_fps = sum(self.fps_data[-120:]) / 120
            min_fps = min(self.fps_data[-120:])
            self.fps_info.setText(f"平均帧率: {avg_fps:.2f} 最低帧率: {min_fps:.2f}")
         
    def update_fps_plot(self):
        #self.current_frame += 1
        for i in range(len(self.fps_str)) :
            str_list = self.fps_str[i].split(',')
            #str_list = [element for element in str_list if element]
            float_numbers = [float(num) for num in str_list if num]
            for num in float_numbers:
                if(num <= 17 and num >= 8) :
                    self.fps_data.append(num)
        #self.fps_data.append(random.uniform(20, 60))  # 随机模拟帧率
        if 0 not in self.fps_data:
            self.fps_data = [1000 / num  for num in self.fps_data]
        if len(self.fps_data) > 120 :
            self.fps_window = self.fps_data[-120:]
        else:
            self.fps_window = self.fps_data
       # 更新图形数据
        if not hasattr(self, 'line'):  # 如果是第一次绘图
            self.line, = self.ax.plot(range(len(self.fps_window)), self.fps_window, color='blue', linewidth=2)
        else:  # 更新已有的线
            self.line.set_xdata(range(len(self.fps_window)))  # 更新x数据
            self.line.set_ydata(self.fps_window)  # 更新y数据

        self.ax.set_ylim(40, 140)
        self.ax.set_xlim(0, 119)
        self.ax.set_title("FPS 实时监控", fontsize=16, pad=20)
        self.ax.set_xlabel("时间", fontsize=12)
        self.ax.set_ylabel("FPS", fontsize=12)

        self.fps_canvas.draw()  # 更新图形
        '''
        self.ax.clear()
        self.ax.plot(self.fps_window, color='blue', linewidth=2)
        self.ax.set_ylim(40, 140)
        self.ax.set_xlim(0, 119)
        self.ax.set_title("FPS 实时监控", fontsize=16, pad=20)  # 调整标题位置
        self.ax.set_xlabel("时间", fontsize=12)
        self.ax.set_ylabel("FPS", fontsize=12)

       

        self.fps_canvas.draw()  # 更新图形
        '''
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

    def update_log_output(self):
        self.get_log_data()
        log_data = self.get_log_data()  # 获取日志数据
        self.log_output.append(log_data)  # 追加到日志区域

    def get_log_data(self):
        # 这里是你的 API 调用，用于获取实时日志
        # 返回示例: "这是新的日志内容"
        # 你需要替换以下代码为实际的 API 调用
        d = self.syslog.c.recv(8192)
        d = d.decode('utf-8')
        matches = self.filter.findall(d)
        for i in matches:
            self.fps_str.append(i)
        #self.filter.search(d)
        #s = d.strip("\n\x00\x00")
        return ''.join(matches)

    def show_process_list(self):
        # 获取进程列表并显示
        processes = self.get_process_list()
        self.show_process_dialog(processes)

    def get_process_list(self):
        keys = ['name', 'pid']
        pr = self.channel.get_processes()
        return [{key: process[key] for key in keys} for process in pr]

    def show_process_dialog(self, processes):
        dialog = QDialog(self)
        dialog.setWindowTitle("选择进程")
        dialog.setGeometry(100, 100, 400, 300)
        
        layout = QVBoxLayout(dialog)

        self.search_box = QLineEdit(dialog)
        self.search_box.setPlaceholderText("搜索进程...")
        self.search_box.textChanged.connect(lambda: self.filter_processes(processes))
        layout.addWidget(self.search_box)

        self.process_list = QListWidget(dialog)
        layout.addWidget(self.process_list)

        for process in processes:
            self.process_list.addItem(f"{process['pid']} - {process['name']}")

        self.process_list.itemDoubleClicked.connect(lambda item: self.process_selected(item.text(), dialog))

        dialog.exec_()

    def filter_processes(self, processes):
        filter_text = self.search_box.text().lower()
        self.process_list.clear()
        for process in processes:
            if filter_text in process['name'].lower() or filter_text in str(process['pid']):
                self.process_list.addItem(f"{process['pid']} - {process['name']}")

    def process_selected(self, process_info, dialog):
        # 处理选择的进程
        self.appname.setText(f"选择的进程: {process_info}")
        self.log_timer = self.startTimer(1)
        
        self.Instant_timer = self.startTimer(1)
        #self.log_output.append(f"选择的进程: {process_info}")
        dialog.accept()  # 关闭对话框



from ios_device.remote.remote_lockdown import RemoteLockdownClient
from ios_device.servers.Instrument import  InstrumentServer
from demo.instrument_demo.sysmontap import  sysmontap

import time

import pytest
from queue import Queue
from ios_device import py_ios_device
from ios_device.py_ios_device import PyiOSDevice

if __name__ == '__main__':

    host = 'fdef:8596:1ddc::1'
    port = 58291  
    address = [host,port]
    rsd = RemoteLockdownClient(address, userspace_port=0)
    rep = PyiOSDevice(device_id='00008027-000A61C81107002E',rpc_channel=InstrumentServer(rsd).init())
    app = QApplication(sys.argv)
    window = PerformanceMonitorApp(lockdown=rsd,rep=rep)
    window.show()
    sys.exit(app.exec_())

