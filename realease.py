
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QListWidget, QDialog, QCheckBox, QFrame,QFileDialog,QLineEdit,QMainWindow,QDesktopWidget,QMessageBox
from ios_device.remote.remote_lockdown import RemoteLockdownClient
from ios_device.servers.syslog import SyslogServer
from datetime import datetime
import sys,threading, queue,re
from PyQt5.QtCore import QThread, pyqtSignal,Qt, QTimer
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtGui import QIcon
from ios_device.py_ios_device import PyiOSDevice
from ios_device.servers.Instrument import  InstrumentServer
import subprocess,signal,os, json,sys,time

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

host = 'fd6b:4a2e:6491::1'
port = 60250 
userspace_port = 60106
device_id='00008027-000A61C81107002E'

class client(object):
    def __init__(self,host,port,userspace_port,device_id,metal_hud_pattern):
        super().__init__()

        self.address = [host,port]
        self.userspace_port = userspace_port
        self.device_id = device_id 
        self.re_pattern = metal_hud_pattern
        self.file_name = './log1.txt'
        
        self.Remote_Client = RemoteLockdownClient(self.address, userspace_port=self.userspace_port) 
        self.syslog = SyslogServer(lockdown=self.Remote_Client)
        self.channel =  PyiOSDevice(device_id=self.device_id,rpc_channel=InstrumentServer(self.Remote_Client).init())

        self.reading = False
        self.writing = False
        self.read_thread = None
        self.write_thread = None
        self.log_queue =  queue.Queue()
        self.realtime_callback = None
        self.realtime_usage_callback = None

    def calculate_bucket_fps(self, item):
        num = float(0)
        j = float(0)
        values = item.split(',')
        for i in range(3, len(values),2):
            try:
                value = float(values[i])
            except ValueError:
                continue
            if value < 8.3368071:
                num += 119.95
            else:
                num += float(1000) / value
            j += 1
        if j != 0:
            return float(num / j)
        return None

    def calculate_bucket_usage_gb(self, item):
        values = item.split(',')
        if len(values) <= 2:
            return None
        try:
            usage_mb = float(values[2])
        except ValueError:
            return None
        if usage_mb < 0:
            return None
        return usage_mb / 1024.0

    def get_process_list(self):
        keys = ['name', 'pid']
        pr = self.channel.get_processes()
        return [{key: process[key] for key in keys} for process in pr]


    def get_instant_log_from_ios(self):
        data = self.syslog.c.recv(4096)
        data = data.decode('utf-8')
        return data.strip("\n\x00\x00")
    
    def thread_read_log(self) :
        while self.reading:
            log_data = self.get_instant_log_from_ios()
            self.log_queue.put(log_data)

    def thread_write_log(self,file_name):
        while self.writing :
            try:
                data = self.log_queue.get(timeout=3)
                matches = self.re_pattern.findall(data)
                with open(file_name, 'a') as f:
                    for item in matches :
                        f.write(item + "\n")
                        usage_gb = self.calculate_bucket_usage_gb(item)
                        if usage_gb is not None and callable(self.realtime_usage_callback):
                            self.realtime_usage_callback(usage_gb)
                        fps = self.calculate_bucket_fps(item)
                        if fps is not None and callable(self.realtime_callback):
                            self.realtime_callback(fps)
                        
                
            except queue.Empty:
                self.log_queue.task_done()
                self.write_thread.finished.connect(self.write_thread.deleteLater)
                break
        self.writing  = False

    def  start_thread(self):
        
        #self.read_thread = threading.Thread(target=self.thread_read_log)
        #self.write_thread = threading.Thread(target=self.thread_write_log,args=(self.file_name,))
        self.read_thread = QThread()
        self.write_thread = QThread()
        self.read_thread.run = self.thread_read_log
        self.write_thread.run = lambda: self.thread_write_log(self.file_name)

    def run_thread(self):
        self.start_thread()

        self.reading = True
        self.writing = True

        self.read_thread.start()
        self.write_thread.start()

        #self.read_thread.join()
        #self.write_thread.join()

    def stop_thread(self):
        self.reading = False
        self.read_thread.finished.connect(self.read_thread.deleteLater)

class ProcessMonitorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.metal_hud_pattern = re.compile(r'metal-HUD: ([\d\.,]+)')
        #self.Client = client(host=host_,port=port_,userspace_port=userspace_port_,device_id=device_id_,metal_hud_pattern=self.metal_hud_pattern)
        self.Client=None
        self.file_name = None
        self.save_file_name = None
        self.setWindowTitle("performance Monitor for Apple device with ios  未连接到ios设备")
        self.setGeometry(100, 100, 1200, 700)
        
        #self.title_signal = pyqtSignal(str)
        #self.title_signal.connect(self.update_title_log)

        self.Start_the_tunnel_thread = None
        self.Strat_curl_thread = None
        self.realtime_x = []
        self.realtime_y = []
        self.realtime_usage_gb = None
        self.realtime_lock = threading.Lock()
        self.realtime_timer = None
        self.realtime_canvas = None
        self.realtime_ax = None
        self.realtime_line = None

        self.initUI()
    
        #self.Start_the_connect()
        self.device_info = None
        '''
        while(self.Strat_curl()):
            self.log_display.append(f"{self.current_time()} 与ios设备连接失败 3s后再次尝试连接")
            time.sleep(3)
        self.setWindowTitle("performance Monitor for Apple device with ios  已连接到ios设备")
        # 连接成功了
        self.Client = client(host=self.device_info['address'],port=self.device_info['rsdPort'],userspace_port=self.device_info['userspaceTunPort'],device_id=self.device_info['udid'],metal_hud_pattern=self.metal_hud_pattern)
        '''
    def update_title_log(self, new_title,new_log):
        # 这是槽函数，用于更新窗口标题
        self.setWindowTitle(new_title)
        self.log_display.append(new_log)

    def Strat_curl_thread_fun(self):

        while(self.Strat_curl()):
            #self.title_signal.emit("performance Monitor for Apple device with ios 18 未与ios设备连接成功",f"{self.current_time()} 未与ios设备连接成功 1s后继续尝试连接")
            time.sleep(1)
        #self.test()
        #self.setWindowTitle("performance Monitor for Apple device with ios 18 已连接到ios设备")

        

    

    def Start_the_connect(self):
        self.Start_the_tunnel_thread = QThread()
        self.Strat_curl_thread = QThread()

        self.Start_the_tunnel_thread.run = self.Start_the_tunnel
        self.Strat_curl_thread.run = self.Strat_curl_thread_fun

        self.Start_the_tunnel_thread.start()
        self.Strat_curl_thread.start()
        
        #self.Strat_curl_thread.finished.connect(self.Strat_curl_thread.deleteLater)
        #self.Strat_curl_thread.run = self.Strat_curl
        

    def Start_the_tunnel(self):
        program = r'C:\Users\r9000p\AppData\Roaming\npm\bin\ios.exe'  
        args = ['tunnel', 'start', '--userspace']

        process = subprocess.Popen([program] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


    def Strat_curl(self):
        program = r'curl' 
        args = ['http://127.0.0.1:60105/tunnels'] 

        process = subprocess.Popen([program] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()

        try:
            
            self.device_info = json.loads(stdout.replace('[','').replace(']',''))
            self.Client = client(host=self.device_info['address'],port=self.device_info['rsdPort'],userspace_port=self.device_info['userspaceTunPort'],device_id=self.device_info['udid'],metal_hud_pattern=self.metal_hud_pattern)
            self.Client.realtime_callback = self.on_realtime_fps
            self.Client.realtime_usage_callback = self.on_realtime_usage
            print(self.device_info)
            #self.log_display.append(f"{self.device_info['udid']} {self.device_info['address']} {self.device_info['rsdPort']} {self.device_info['userspaceTunPort']}")
            #self.title_signal.emit("performance Monitor for Apple device with ios 18 与ios设备连接成功",f"{self.current_time()} 与ios设备连接成功")

           # self.log_display.append(f"{self.current_time()} 与ios设备连接成功")
            self.log_display.append(f"{self.current_time()} 与ios设备连接成功,可以开始性能记录")
            self.setWindowTitle(f"performance Monitor for Apple device with ios  已连接到ios设备       udid:{self.device_info['udid']}")
            return 0
        except :
            return 1


    def initUI(self):
        self.setWindowIcon(QIcon(r'D:\code\ios_helper\icon.ico'))  # 设置图标
        self.center()

        layout = QVBoxLayout()
        
        # 信息显示区域
        info_layout = QHBoxLayout()  # 创建一个水平布局

        self.info_display = QLabel("运行日志")
        self.performance_info_display = QLabel("性能分析文件：")

        info_layout.addWidget(self.info_display)
        info_layout.addWidget(self.performance_info_display)

        layout.addLayout(info_layout)  # 将水平布局添加到主布局
        
        # 实时日志输出区域
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)

        # 实时帧率图表区域
        self.realtime_canvas = FigureCanvas(Figure(figsize=(10, 3)))
        self.realtime_ax = self.realtime_canvas.figure.add_subplot(111)
        self.realtime_ax.set_title("实时帧率")
        self.realtime_ax.set_xlabel("时间 (秒)")
        self.realtime_ax.set_ylabel("Frame Rate (fps)")
        self.realtime_ax.grid(True, linestyle='--', alpha=0.7)
        (self.realtime_line,) = self.realtime_ax.plot([], [], color='red', linewidth=1.5)
        self.realtime_canvas.setMinimumHeight(220)
        self.realtime_canvas.setMaximumHeight(260)
        self.current_fps_label = QLabel("当前 FPS: --")
        self.current_usage_label = QLabel("当前进程占用: --")
        metric_layout = QHBoxLayout()
        metric_layout.addWidget(self.current_fps_label)
        metric_layout.addSpacing(18)
        metric_layout.addWidget(self.current_usage_label)
        layout.addLayout(metric_layout)
        layout.addWidget(self.realtime_canvas)
        layout.addSpacing(8)

        self.realtime_timer = QTimer(self)
        self.realtime_timer.timeout.connect(self.refresh_realtime_plot)
        self.realtime_timer.start(500)

        # 复选框区域（横向布局）
        checkbox_layout = QHBoxLayout()
        
        self.fps_checkbox = QCheckBox("帧率")
        self.cpu_checkbox = QCheckBox("CPU")
        self.gpu_checkbox = QCheckBox("GPU")

        self.fps_checkbox.stateChanged.connect(self.checkbox_changed)
        self.cpu_checkbox.stateChanged.connect(self.checkbox_changed)
        self.gpu_checkbox.stateChanged.connect(self.checkbox_changed)

        checkbox_layout.addWidget(self.fps_checkbox)
        checkbox_layout.addWidget(self.cpu_checkbox)
        checkbox_layout.addWidget(self.gpu_checkbox)

        layout.addLayout(checkbox_layout)

        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.process_button = QPushButton("选择进程")
        self.process_button.clicked.connect(self.show_process_list)
        button_layout.addWidget(self.process_button)

        self.start_button = QPushButton("开始监测")
        self.start_button.clicked.connect(self.start_monitoring)
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("停止监测")
        self.stop_button.clicked.connect(self.stop_monitoring)
        button_layout.addWidget(self.stop_button)

        # 新增性能分析按钮
        self.performance_button = QPushButton("性能分析")
        self.performance_button.clicked.connect(self.analyze_performance)  # 假设你有这个方法
        #checkbox_layout.addWidget(self.performance_button)
        
        self.performance_choice_button = QPushButton("文件选择")
        self.performance_choice_button.clicked.connect(self.performance_File_Selection)  # 假设你有这个方法
        button_layout.addWidget(self.performance_choice_button)

        button_layout.addWidget(self.performance_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def performance_File_Selection(self):
        options = QFileDialog.Options()
        self.file_name, _ = QFileDialog.getOpenFileName(self, "选择性能分析文件", "", "performance Files (*.performance)", options=options)
        if self.file_name:
            self.log_display.append(f"{self.current_time()} 选择性能分析文件: {self.file_name}")
            self.performance_info_display.setText(f"性能分析文件: {self.file_name}")

    def analyze_performance(self):
        
        if self.file_name:
            lines=None
            with open(self.file_name, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            performance_str_list = []

            for item in lines :
                str1 = item.replace('\n','').split(',')
                str1 = [elem for elem in str1 if elem != '']  # 
                performance_str_list.append([float(item) for item in str1])

            Frame_number = []
            Frame_number_len = []

            for item in performance_str_list :

                Frame_number.append( int(item[0]))  #首帧编号

                num = len(item)- 3
                if(num % 2) :num = num /2 + 1 
                else : num = num / 2

                Frame_number_len.append( int(num) )

            print(len(performance_str_list))

            loss_frame = 0
            all_frame = 0

            for i in range(len(Frame_number)-1):
                if Frame_number[i] + Frame_number_len[i] != Frame_number[i+1]:
                    loss_frame += Frame_number[i+1] - (Frame_number[i] + Frame_number_len[i])
                all_frame += Frame_number_len[i]

            frame = []
            #print(len(performance_str_list))

            for item in performance_str_list :
                num = float(0);
                j = float(0);
                for i in range(3,len(item),2):
                    if(item[i]< 8.3368071):
                        num += 119.95
                    else:
                        num += float(1000) / item[i]
                    j += 1
                if j!= 0:
                    frame.append(float(num/j))
            
            

            # 过滤无用帧率
            #filtered_data = [num for num in frame if num > 65]
            filtered_data = frame
            total_time = len(filtered_data)  # 总时间（秒）
            time = range(total_time)  # x 轴为时间（单位：秒）
            #time = range(len(frame))
            average_fps = sum(filtered_data) / len(filtered_data)  # 平均帧率
            Frame_rate_loss_percentile = loss_frame / all_frame  #帧率损失比例

            fps_array = np.array(filtered_data)
            sorted_fps = np.sort(fps_array)
            
            index_1_low = int(len(sorted_fps) * 0.01)
            index_5_low = int(len(sorted_fps) * 0.05)

            percentile_1_low = sorted_fps[index_1_low]  # 百分之 1 低帧率
            percentile_5_low = sorted_fps[index_5_low]  # 百分之 5 低帧率

            low_frame_count = float(0)
            for i in range(1,len(filtered_data)):
                if filtered_data[i] < filtered_data[i-1] and filtered_data[i-1]-filtered_data[i] >1.5:
                    low_frame_count += 1
            #low_frame_count = sum(1 for fps in filtered_data if fps < average_fps)
            #print(low_frame_count )
            stutter_rate = (low_frame_count / len(filtered_data)) * 100 

            

            # 创建散点图
            plt.figure(figsize=(12, 6),num='performance analyze  Plot')
            plt.scatter(time, filtered_data, color='blue', s=4)  # s 为点的大小
            plt.title('Frame Rate Scatter Plot Over Time', fontsize=16)

            plt.xticks(np.arange(0, total_time, step=50))  # 每10秒设置一个刻度
            plt.xlabel('Time (seconds)', fontsize=14)
            plt.ylabel('Frame Rate (fps)', fontsize=14)
            plt.ylim(40, 125)

            plt.text(total_time * 0.05, 105, f'Average: {average_fps:.2f}', fontsize=15, color='red', ha='left')
            plt.text(total_time * 0.05, 100, f'Frame_rate_loss_percentile: {Frame_rate_loss_percentile*100:.2f}%  loss frame:{loss_frame} all frame:{all_frame}', fontsize=15, color='black', ha='left')
            plt.text(total_time * 0.05, 95, f'1% Low: {percentile_1_low:.2f}', fontsize=15, color='orange', ha='left')
            plt.text(total_time * 0.05, 90, f'5% Low: {percentile_5_low:.2f}', fontsize=15, color='green', ha='left')
            plt.text(total_time * 0.05, 85, f'Stutter rate: {stutter_rate:.2f}%', fontsize=15, color='purple', ha='left')

            plt.plot(time, filtered_data, color='red', linewidth=2, label='Frame Rate')
            #for i, fps in enumerate(filtered_data):
                #if fps < average_fps:
                    #plt.text(i, fps, f'{fps}', fontsize=3, color='black', ha='center', #va='bottom')



            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()  # 自适应布局
            plt.show()

            self.log_display.append(f"{self.current_time()} 性能分析完成: {self.file_name}")
        else:
            self.log_display.append(f"{self.current_time()} 未选择性能分析文件")
        return 
    def show_process_list(self):
        '''
        if self.Client == None :
            self.Client = client(host=self.device_info['address'],port=self.device_info['rsdPort'],userspace_port=self.device_info['userspaceTunPort'],device_id=self.device_info['udid'],metal_hud_pattern=self.metal_hud_pattern)
        '''
        processes = self.Client.get_process_list()
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
        '''
        dialog = QDialog(self)
        dialog.setWindowTitle("进程列表")
        dialog.setGeometry(200, 200, 500, 800)

        dialog.move(self.x() + (self.width() - dialog.width()) // 2,
                    self.y() + (self.height() - dialog.height()) // 2)
        # 创建搜索框
        search_box = QLineEdit(dialog)
        search_box.setPlaceholderText("搜索进程...")
        search_box.textChanged.connect(lambda: self.filter_processes(search_box.text(), list_widget))

        list_widget = QListWidget(dialog)
        processes = self.Client.get_process_list()     #11111
        list_widget.addItems(processes)
        list_widget.itemDoubleClicked.connect(lambda item: self.on_process_select(item.text(), dialog))

        layout = QVBoxLayout(dialog)
        layout.addWidget(search_box)
        layout.addWidget(list_widget)
        dialog.setLayout(layout)
        dialog.exec_()
        '''
    def filter_processes(self, processes):
        filter_text = self.search_box.text().lower()
        self.process_list.clear()
        for process in processes:
            if filter_text in process['name'].lower() or filter_text in str(process['pid']):
                self.process_list.addItem(f"{process['pid']} - {process['name']}")

    def process_selected(self, process_info, dialog):
        # 处理选择的进程
        
        self.log_display.append(f"{self.current_time()}：选择了进程: {process_info}")
        self.info_display.setText(f"当前选择的进程: {process_info}")
        for i in range(len(process_info)-1,-1,-1):
            if process_info[i] == ' ':
                self.save_file_name = process_info[i+1:]+'-'
                break
        print(self.save_file_name )
        #self.save_file_name = process_info.replace(' ','-')
        dialog.accept()  # 关闭对话框
        
        
        '''
    def filter_processes(self, search_text, list_widget):
        # 根据搜索文本过滤进程列表
        all_processes = ["进程1", "进程2", "进程3", "进程4", "进程5"]
        filtered_processes = [p for p in all_processes if search_text in p]
    
        list_widget.clear()  # 清空列表
        list_widget.addItems(filtered_processes)  # 添加过滤后的进程
        
    def on_process_select(self, process_name, dialog):
        self.log_display.append(f"选择了进程: {process_name}")
        self.info_display.setText(f"当前选择的进程: {process_name}")
        dialog.accept()  # 关闭对话框
        '''
    def start_monitoring(self):
        if self.save_file_name == None :
            self.log_display.append(f"{self.current_time()}: 未选择需要监视的进程。")
            return
            
        selected_options = []
        if self.fps_checkbox.isChecked():
            selected_options.append("帧率")
        if self.cpu_checkbox.isChecked():
            selected_options.append("CPU")
        if self.gpu_checkbox.isChecked():
            selected_options.append("GPU")
        

        if selected_options:
            self.reset_realtime_plot()
            self.log_display.append(f"{self.current_time()}: 开始监测: {', '.join(selected_options)}...")
            self.Client.file_name = './' + self.save_file_name + self.current_time().replace(' ','-').replace(':','-')+'.performance'
            #self.save_file_name = self.Client.file_name
            self.Client.run_thread()
        else:
            self.log_display.append(f"{self.current_time()}: 未选择任何监测项。")

    def stop_monitoring(self):
        if self.Client.reading == True :
            self.Client.stop_thread()
            self.log_display.append(f"{self.current_time()}: 性能记录文件已保存至{self.Client.file_name}")
            self.refresh_realtime_plot()
        else :
            self.log_display.append(f"{self.current_time()}:  未开始监测...请开始监测后保存")

    def reset_realtime_plot(self):
        with self.realtime_lock:
            self.realtime_x.clear()
            self.realtime_y.clear()
            self.realtime_usage_gb = None
        if self.realtime_line is not None:
            self.realtime_line.set_data([], [])
            self.realtime_ax.relim()
            self.realtime_ax.autoscale_view()
            self.realtime_canvas.draw_idle()
        self.current_fps_label.setText("当前 FPS: --")
        self.current_usage_label.setText("当前进程占用: --")

    def on_realtime_fps(self, fps):
        with self.realtime_lock:
            self.realtime_x.append(len(self.realtime_x) + 1)
            self.realtime_y.append(fps)

    def on_realtime_usage(self, usage_gb):
        with self.realtime_lock:
            self.realtime_usage_gb = usage_gb

    def refresh_realtime_plot(self):
        if self.realtime_line is None:
            return
        with self.realtime_lock:
            x = list(self.realtime_x)
            y = list(self.realtime_y)
        if not x:
            return

        self.realtime_line.set_data(x, y)
        self.realtime_ax.set_xlim(1, max(10, x[-1]))

        y_min = min(y)
        y_max = max(y)
        y_span = max(1.0, y_max - y_min)
        padding = max(2.0, y_span * 0.15)
        self.realtime_ax.set_ylim(y_min - padding, y_max + padding)

        self.current_fps_label.setText(f"当前 FPS: {y[-1]:.2f}")
        with self.realtime_lock:
            usage_gb = self.realtime_usage_gb
        if usage_gb is None:
            self.current_usage_label.setText("当前进程占用: --")
        else:
            self.current_usage_label.setText(f"当前进程占用: {usage_gb:.2f} GB")
        self.realtime_canvas.draw_idle()

    def checkbox_changed(self, state):
        sender = self.sender()  # 获取发出信号的复选框
        checkbox_name = sender.text()  # 获取复选框的文本
        if state == Qt.Checked:
            self.log_display.append(f"{self.current_time()}:  启用{checkbox_name}记录选项")
        else : self.log_display.append(f"{self.current_time()}:  关闭{checkbox_name}记录选项")

    def current_time(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def center(self):
        screen = QDesktopWidget().screenGeometry()  # 获取屏幕几何信息
        size = self.geometry()  # 获取窗口的几何信息
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)  # 设置窗口位置
    
    def closeEvent(self, event):
        # 在关闭事件中确认是否要保存
        reply = QMessageBox.question(self, 'Message', '保存日志并退出？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            with open('log.txt', 'a',encoding='utf-8') as f:
                log_content = self.log_display.toPlainText()  # 获取 QTextEdit 中的文本
                f.write(log_content)  # 将内容写入文件
            event.accept()  # 允许关闭
        else:
            event.accept()  # 忽略关闭


'''
sudo ios tunnel start && ios tunnel start --userspace
curl http://127.0.0.1:60105/tunnels
'''
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProcessMonitorApp()
    window.show()
    window.Start_the_connect()
    
    sys.exit(app.exec_())


