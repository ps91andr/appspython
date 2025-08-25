import sys
import os
import subprocess
import threading
import platform
import time
import re
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QMessageBox, QFileDialog, QMenu, QScrollArea,
    QListWidget, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QIcon, QAction, QWheelEvent

# Worker for running ADB commands in a separate thread
class AdbWorker(QObject):
    finished = pyqtSignal(object)
    log_message = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, command, *args):
        super().__init__()
        self.command = command
        self.args = args

    def run(self):
        try:
            result = self.command(*self.args)
            self.finished.emit(result)
        except Exception as e:
            self.log_message.emit(f"Error in worker thread: {e}")
            self.finished.emit(None)

class FireTVController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fire TV Controller Pro - التحكم المتقدم في Fire TV")
        self.setGeometry(100, 100, 800, 950)

        # Set app icon
        script_dir = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(script_dir, "firetv_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Member variables
        self.connection_status_text = "غير متصل"
        self.current_app_text = "غير معروف"
        self.log_messages = []
        self.current_apps_list = []
        self.detected_devices = []
        self.auto_update_enabled = True

        self._drag_pos = None

        self.setup_ui()
        self.setup_styles()

        # Check for ADB installation
        if not self.check_adb_installation():
            QMessageBox.critical(self, "خطأ", "ADB غير مثبت أو غير مضاف إلى PATH")

        # Start auto-updates
        self.auto_update_info()
        self.populate_device_list()
        self.auto_update_devices()

    def setup_ui(self):
        # --- Main Scrollable Area ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.setCentralWidget(scroll_area)

        main_widget = QWidget()
        scroll_area.setWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)

        # --- Header ---
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h1>Fire TV Controller Pro</h1>"))
        header_layout.addStretch()
        header_layout.addWidget(QLabel("حالة الاتصال:"))
        self.connection_status_label = QLabel(f"<i>{self.connection_status_text}</i>")
        header_layout.addWidget(self.connection_status_label)
        self.main_layout.addLayout(header_layout)

        # --- Connection Frame ---
        self.create_connection_frame()

        # --- Device Info Frame ---
        self.create_device_info_frame()

        # --- Controls Section ---
        self.create_controls_section()

        # --- Apps Section ---
        self.create_apps_section()

        # --- Log Section ---
        self.create_log_section()

    def create_connection_frame(self):
        group = QGroupBox("إعدادات الاتصال المتقدم")
        layout = QVBoxLayout(group)

        notebook = QTabWidget()
        layout.addWidget(notebook)

        # --- Tab 1: Connection Setup ---
        setup_tab = QWidget()
        setup_layout = QGridLayout(setup_tab)

        self.device_combobox = QComboBox()
        self.device_combobox.setEditable(False)
        self.device_combobox.currentTextChanged.connect(self.on_device_selected)
        setup_layout.addWidget(QLabel("الجهاز المحدد:"), 0, 0)
        setup_layout.addWidget(self.device_combobox, 0, 1)

        connect_selected_btn = QPushButton("اتصال بالجهاز المحدد")
        connect_selected_btn.setObjectName("ConnectButton")
        connect_selected_btn.clicked.connect(lambda: self.connect_device(self.device_combobox.currentText()))
        setup_layout.addWidget(connect_selected_btn, 0, 2)
        
        refresh_devices_btn = QPushButton("تحديث الأجهزة")
        refresh_devices_btn.clicked.connect(self.populate_device_list)
        setup_layout.addWidget(refresh_devices_btn, 0, 3)

        self.device_ip_edit = QLineEdit("192.168.1.100:5555")
        setup_layout.addWidget(QLabel("IP الجهاز (يدوي):"), 1, 0)
        setup_layout.addWidget(self.device_ip_edit, 1, 1)

        connect_manual_btn = QPushButton("اتصال بعنوان IP يدوي")
        connect_manual_btn.setObjectName("ConnectButton")
        connect_manual_btn.clicked.connect(lambda: self.connect_device(self.device_ip_edit.text()))
        setup_layout.addWidget(connect_manual_btn, 1, 2)

        disconnect_btn = QPushButton("قطع الاتصال")
        disconnect_btn.setObjectName("RedButton")
        disconnect_btn.clicked.connect(self.disconnect_device)
        setup_layout.addWidget(disconnect_btn, 1, 3)
        
        reset_btn = QPushButton("إصلاح الاتصال")
        reset_btn.setObjectName("BlueButton")
        reset_btn.clicked.connect(self.reset_adb_connection)
        setup_layout.addWidget(reset_btn, 2, 2)

        ping_btn = QPushButton("اختبار Ping")
        ping_btn.clicked.connect(self.test_ping)
        setup_layout.addWidget(ping_btn, 2, 1)
        
        enable_wireless_btn = QPushButton("تفعيل ADB لاسلكي")
        enable_wireless_btn.clicked.connect(self.enable_wireless_adb)
        setup_layout.addWidget(enable_wireless_btn, 2, 3)

        notebook.addTab(setup_tab, "إعدادات الاتصال")
        
        # --- Tab 2: Connected Devices ---
        connected_tab = QWidget()
        connected_layout = QVBoxLayout(connected_tab)
        self.connected_devices_tree = QTreeWidget()
        self.connected_devices_tree.setHeaderLabels(["معرف الجهاز"])
        self.connected_devices_tree.header().setStretchLastSection(True)
        connected_layout.addWidget(self.connected_devices_tree)
        notebook.addTab(connected_tab, "الأجهزة المتصلة")

        # --- Tab 3: ADB Pairing ---
        self.create_pairing_tab(notebook)

        self.main_layout.addWidget(group)

    def create_pairing_tab(self, notebook):
        tab = QWidget()
        layout = QGridLayout(tab)

        self.ip_addresses, self.ports, self.pairing_codes = self.load_data()

        self.ip_combobox = QComboBox()
        self.ip_combobox.addItems(self.ip_addresses)
        self.ip_combobox.setEditable(True)
        
        self.port_combobox = QComboBox()
        self.port_combobox.addItems(self.ports)
        self.port_combobox.setEditable(True)
        
        self.pairing_combobox = QComboBox()
        self.pairing_combobox.addItems(self.pairing_codes)
        self.pairing_combobox.setEditable(True)

        layout.addWidget(QLabel("عنوان IP:"), 0, 0)
        layout.addWidget(self.ip_combobox, 0, 1)
        connect_btn = QPushButton("اتصال")
        connect_btn.clicked.connect(self.connect_device_tab3)
        layout.addWidget(connect_btn, 0, 2)

        layout.addWidget(QLabel("المنفذ:"), 1, 0)
        layout.addWidget(self.port_combobox, 1, 1)
        pair_btn = QPushButton("إقران")
        pair_btn.clicked.connect(self.pair_device_tab3)
        layout.addWidget(pair_btn, 1, 2)

        layout.addWidget(QLabel("رمز الإقران:"), 2, 0)
        layout.addWidget(self.pairing_combobox, 2, 1)
        default_connect_btn = QPushButton("اتصال بالمنافذ الافتراضية")
        default_connect_btn.clicked.connect(self.connect_default_port_tab3)
        layout.addWidget(default_connect_btn, 2, 2)

        adb_version_btn = QPushButton("عرض إصدار ADB")
        adb_version_btn.clicked.connect(self.show_adb_version_tab3)
        layout.addWidget(adb_version_btn, 3, 1)
        pair_without_code_btn = QPushButton("إقران بدون رمز")
        pair_without_code_btn.clicked.connect(self.pair_without_code_tab3)
        layout.addWidget(pair_without_code_btn, 3, 2)
        
        layout.addWidget(QLabel("الأجهزة المتصلة:"), 4, 0)
        update_devices_btn = QPushButton("عرض الأجهزة المتصلة")
        update_devices_btn.clicked.connect(self.update_devices_listbox_tab3)
        layout.addWidget(update_devices_btn, 4, 1)
        device_info_btn = QPushButton("عرض معلومات الجهاز")
        device_info_btn.clicked.connect(self.show_device_info_tab3)
        layout.addWidget(device_info_btn, 4, 2)

        self.devices_listbox = QListWidget()
        layout.addWidget(self.devices_listbox, 5, 0, 1, 3)

        disconnect_selected_btn = QPushButton("إلغاء الاتصال بالجهاز المحدد")
        disconnect_selected_btn.clicked.connect(self.disconnect_device_tab3)
        layout.addWidget(disconnect_selected_btn, 6, 0)
        
        disconnect_all_btn = QPushButton("إلغاء جميع الأجهزة المتصلة")
        disconnect_all_btn.clicked.connect(self.disconnect_all_devices_tab3)
        layout.addWidget(disconnect_all_btn, 6, 1)

        self.toggle_button = QPushButton("إيقاف التحديث التلقائي")
        self.toggle_button.clicked.connect(self.toggle_auto_update_tab3)
        layout.addWidget(self.toggle_button, 6, 2)

        restart_btn = QPushButton("إعادة تشغيل التطبيق")
        restart_btn.clicked.connect(self.restart_app_tab3)
        layout.addWidget(restart_btn, 7, 0)

        notebook.addTab(tab, "إقران ADB")

    def create_device_info_frame(self):
        group = QGroupBox("معلومات الجهاز")
        layout = QHBoxLayout(group)
        layout.addWidget(QLabel("التطبيق الحالي:"))
        self.current_app_label = QLabel(self.current_app_text)
        layout.addWidget(self.current_app_label)
        layout.addStretch()
        update_btn = QPushButton("تحديث المعلومات")
        update_btn.clicked.connect(self.update_device_info)
        layout.addWidget(update_btn)
        full_info_btn = QPushButton("معلومات الجهاز الكاملة")
        full_info_btn.clicked.connect(self.show_device_info)
        layout.addWidget(full_info_btn)
        self.main_layout.addWidget(group)

    def create_controls_section(self):
        notebook = QTabWidget()
        self.create_navigation_controls(notebook)
        self.create_control_buttons(notebook)
        self.create_media_controls(notebook)
        self.create_advanced_controls(notebook)
        self.main_layout.addWidget(notebook)

    def create_navigation_controls(self, notebook):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(QPushButton("▲ أعلى", clicked=lambda: self.send_key("KEYCODE_DPAD_UP")))
        
        mid_layout = QHBoxLayout()
        mid_layout.addWidget(QPushButton("◄ يسار", clicked=lambda: self.send_key("KEYCODE_DPAD_LEFT")))
        mid_layout.addWidget(QPushButton("OK", clicked=lambda: self.send_key("KEYCODE_DPAD_CENTER")))
        mid_layout.addWidget(QPushButton("► يمين", clicked=lambda: self.send_key("KEYCODE_DPAD_RIGHT")))
        layout.addLayout(mid_layout)

        layout.addWidget(QPushButton("▼ أسفل", clicked=lambda: self.send_key("KEYCODE_DPAD_DOWN")))
        notebook.addTab(widget, "أزرار التنقل")

    def create_control_buttons(self, notebook):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        row1 = QHBoxLayout()
        row1.addWidget(QPushButton("رجوع", clicked=lambda: self.send_key("KEYCODE_BACK")))
        row1.addWidget(QPushButton("الصفحة الرئيسية", clicked=lambda: self.send_key("KEYCODE_HOME")))
        row1.addWidget(QPushButton("القائمة", clicked=lambda: self.send_key("KEYCODE_MENU")))
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QPushButton("إدخال", clicked=lambda: self.send_key("KEYCODE_ENTER")))
        row2.addWidget(QPushButton("حذف", clicked=lambda: self.send_key("KEYCODE_DEL")))
        row2.addWidget(QPushButton("إعدادات", clicked=lambda: self.send_key("KEYCODE_SETTINGS")))
        shortcut_btn = QPushButton("فتح الإعدادات السريع")
        shortcut_btn.setObjectName("PurpleButton")
        shortcut_btn.clicked.connect(self.open_settings_shortcut)
        row2.addWidget(shortcut_btn)
        layout.addLayout(row2)

        num_group = QGroupBox("لوحة رقمية")
        num_layout = QGridLayout(num_group)
        
        buttons = {
            (0, 0): "1", (0, 1): "2", (0, 2): "3",
            (1, 0): "4", (1, 1): "5", (1, 2): "6",
            (2, 0): "7", (2, 1): "8", (2, 2): "9",
            (3, 0): "*", (3, 1): "0", (3, 2): "#"
        }
        
        keycodes = {"*": "STAR", "#": "POUND"}
        for pos, text in buttons.items():
            keycode = f"KEYCODE_{keycodes.get(text, text)}"
            btn = QPushButton(text)
            btn.setFixedSize(40, 40)
            btn.clicked.connect(lambda _, k=keycode: self.send_key(k))
            num_layout.addWidget(btn, pos[0], pos[1])

        layout.addWidget(num_group)
        notebook.addTab(widget, "أزرار التحكم")
    
    def create_media_controls(self, notebook):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        grid = QGridLayout()
        grid.addWidget(QPushButton("تشغيل/إيقاف", clicked=lambda: self.send_key("KEYCODE_MEDIA_PLAY_PAUSE")), 0, 0)
        grid.addWidget(QPushButton("توقف", clicked=lambda: self.send_key("KEYCODE_MEDIA_STOP")), 0, 1)
        grid.addWidget(QPushButton("التالي", clicked=lambda: self.send_key("KEYCODE_MEDIA_NEXT")), 1, 0)
        grid.addWidget(QPushButton("السابق", clicked=lambda: self.send_key("KEYCODE_MEDIA_PREVIOUS")), 1, 1)
        grid.addWidget(QPushButton("تقدم سريع", clicked=lambda: self.send_key("KEYCODE_MEDIA_FAST_FORWARD")), 2, 0)
        grid.addWidget(QPushButton("إعادة", clicked=lambda: self.send_key("KEYCODE_MEDIA_REWIND")), 2, 1)
        layout.addLayout(grid)

        vol_group = QGroupBox("التحكم بالصوت")
        vol_layout = QHBoxLayout(vol_group)
        vol_layout.addWidget(QPushButton("كتم", clicked=lambda: self.send_key("KEYCODE_VOLUME_MUTE")))
        vol_layout.addWidget(QPushButton("رفع الصوت ▲", clicked=lambda: self.send_key("KEYCODE_VOLUME_UP")))
        vol_layout.addWidget(QPushButton("خفض الصوت ▼", clicked=lambda: self.send_key("KEYCODE_VOLUME_DOWN")))
        layout.addWidget(vol_group)

        notebook.addTab(widget, "تحكم بالميديا")

    def create_advanced_controls(self, notebook):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QPushButton("إيقاف/تشغيل الجهاز", clicked=self.toggle_power))
        layout.addWidget(QPushButton("Sleep/Wakeup", clicked=self.sleep_wakeup))
        layout.addWidget(QPushButton("لقطة الشاشة", clicked=self.take_screenshot))

        text_group = QGroupBox("إرسال نص إلى الجهاز")
        text_layout = QHBoxLayout(text_group)
        
        self.text_editor = QTextEdit()
        self.text_editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.text_editor.customContextMenuRequested.connect(self.show_text_context_menu)
        text_layout.addWidget(self.text_editor)
        
        send_btn = QPushButton("إرسال")
        send_btn.clicked.connect(self.send_text_to_device)
        text_layout.addWidget(send_btn)

        layout.addWidget(text_group)
        notebook.addTab(widget, "أوامر متقدمة")
    
    def create_apps_section(self):
        group = QGroupBox("إدارة التطبيقات")
        layout = QGridLayout(group)
        
        popular_apps = [
            ("Netflix", "com.netflix.ninja"), ("Prime Video", "com.amazon.avod"),
            ("YouTube", "com.google.android.youtube.tv"), ("Disney+", "com.disney.disneyplus"),
            ("فتح التطبيقات", "show_apps"), ("إيقاف التطبيق", "force_stop")
        ]

        for i, (name, pkg) in enumerate(popular_apps):
            btn = QPushButton(name)
            if pkg == "show_apps":
                btn.clicked.connect(self.show_apps_list)
            elif pkg == "force_stop":
                btn.clicked.connect(self.force_stop_app)
            else:
                btn.clicked.connect(lambda _, p=pkg: self.launch_app(p))
            layout.addWidget(btn, i // 3, i % 3)
            
        self.main_layout.addWidget(group)

    def create_log_section(self):
        group = QGroupBox("سجل الأحداث")
        layout = QVBoxLayout(group)
        
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        layout.addWidget(self.log_text_edit)
        
        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("مسح السجل", clicked=self.clear_log)
        save_btn = QPushButton("حفظ السجل", clicked=self.save_log)
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.main_layout.addWidget(group)

    def setup_styles(self):
        self.setStyleSheet("""
            /* --- الوضع المظلم (Dark Mode) --- */

            /* النوافذ والويدجت الرئيسية */
            QMainWindow, QWidget {
                background-color: #2E2E2E; /* خلفية رمادية داكنة */
                color: #E0E0E0; /* لون النص: رمادي فاتح */
                font-family: Arial;
                font-size: 10pt;
            }

            /* مربعات التجميع (Group Boxes) */
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555555; /* حدود أغمق */
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #1E90FF; /* لون العنوان: أزرق فاتح */
            }

            /* العناوين (Labels) */
            QLabel {
                background-color: transparent;
                color: #E0E0E0; /* لون النص الافتراضي */
            }
            /* العنوان الرئيسي */
            QLabel h1 {
                font-size: 14pt;
                font-weight: bold;
                color: #FFFFFF; /* أبيض ناصع للعنوان الرئيسي */
            }

            /* الأزرار (Buttons) */
            QPushButton {
                padding: 8px;
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #4A4A4A; /* خلفية زر أغمق */
                color: #E0E0E0;
            }
            QPushButton:hover {
                background-color: #5A5A5A; /* إضاءة عند التمرير */
                border-color: #777777;
            }
            QPushButton:pressed {
                background-color: #3A3A3A; /* أغمق عند الضغط */
            }
            
            /* ألوان الأزرار الخاصة */
            QPushButton#RedButton {
                background-color: #B71C1C;
                color: white;
            }
            QPushButton#RedButton:hover { background-color: #D32F2F; }
            
            QPushButton#ConnectButton {
                background-color: #2E7D32;
                color: white;
            }
            QPushButton#ConnectButton:hover { background-color: #388E3C; }
            
            QPushButton#BlueButton {
                background-color: #1565C0;
                color: white;
            }
            QPushButton#BlueButton:hover { background-color: #1976D2; }
            
            QPushButton#PurpleButton {
                background-color: #6A1B9A;
                color: white;
            }
            QPushButton#PurpleButton:hover { background-color: #7B1FA2; }

            /* مربعات الإدخال والقوائم */
            QLineEdit, QComboBox, QTextEdit, QTreeWidget, QListWidget {
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px;
                background-color: #3C3C3C; /* خلفية حقل الإدخال */
                color: #E0E0E0;
            }
            QTreeWidget::item:hover, QListWidget::item:hover {
                 background-color: #4A4A4A; /* لون عند تحديد عنصر */
            }

            /* التبويبات (Tabs) */
            QTabWidget::pane {
                border-top: 2px solid #555555;
            }
            QTabBar::tab {
                background: #3C3C3C;
                color: #E0E0E0;
                padding: 8px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                border: 1px solid #555555;
                border-bottom: none;
            }
            QTabBar::tab:selected, QTabBar::tab:hover {
                background: #4A4A4A; /* لون التبويب المحدد */
            }
        """)

    # --- Event Handlers (Mouse, Context Menus) ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(self.pos() + event.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.1 if delta > 0 else 0.9
            self.resize(int(self.width() * factor), int(self.height() * factor))
        else:
            pass
            
    def show_text_context_menu(self, pos):
        menu = QMenu()
        menu.addAction("نسخ", self.text_editor.copy)
        menu.addAction("لصق", self.text_editor.paste)
        menu.addAction("تحديد الكل", self.text_editor.selectAll)
        menu.addAction("حذف", self.text_editor.cut)
        menu.exec(self.text_editor.mapToGlobal(pos))
    
    # --- Helper Functions for Threading ---
    def run_in_thread(self, command, *args, on_finish=None, on_log=None, on_progress=None):
        thread = QThread()
        worker = AdbWorker(command, *args)
        worker.moveToThread(thread)

        # Keep a reference to the thread and worker to prevent premature garbage collection
        setattr(self, f"thread_{id(thread)}", thread)
        setattr(self, f"worker_{id(worker)}", worker)

        if on_finish:
            worker.finished.connect(on_finish)
        if on_log:
            worker.log_message.connect(on_log)
        if on_progress:
            worker.progress.connect(on_progress)
        
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        thread.started.connect(worker.run)
        thread.start()
        
    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_messages.append(log_entry + "\n")
        self.log_text_edit.append(log_entry)

    def update_connection_status(self, status):
        self.connection_status_text = status
        self.connection_status_label.setText(f"<i>{status}</i>")

    def is_connected(self):
        return self.connection_status_text == "متصل"
    
    # --- Core Logic Methods (with threading) ---

    def check_adb_installation(self):
        try:
            result = subprocess.run(["adb", "version"], capture_output=True, text=True,
                                    creationflags=self._get_creation_flags())
            return "Android Debug Bridge" in result.stdout
        except FileNotFoundError:
            return False

    @staticmethod
    def _get_creation_flags():
        return subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0

    def on_device_selected(self, device_text):
        if device_text:
            self.device_ip_edit.setText(device_text)

    def populate_device_list(self):
        self.run_in_thread(self._populate_device_list_thread, on_finish=self._update_ui_after_device_list)
        
    def _populate_device_list_thread(self):
        try:
            devices_output = subprocess.check_output(["adb", "devices"], text=True, creationflags=self._get_creation_flags())
            detected = []
            connected = []
            for line in devices_output.strip().splitlines()[1:]:
                if line.strip() and "device" in line:
                    device_id = line.split()[0]
                    detected.append(device_id)
                    connected.append((device_id,))
            return {"detected": detected, "connected": connected}
        except Exception as e:
            self.log_message(f"خطأ في تحديث قائمة الأجهزة: {e}")
            return None

    def _update_ui_after_device_list(self, result):
        if result:
            self.detected_devices = result["detected"]
            current_device = self.device_combobox.currentText()
            
            self.device_combobox.clear()
            self.device_combobox.addItems(self.detected_devices)
            
            if current_device and current_device in self.detected_devices:
                self.device_combobox.setCurrentText(current_device)
            elif self.detected_devices:
                self.device_combobox.setCurrentIndex(0)

            self.connected_devices_tree.clear()
            for (device_id,) in result["connected"]:
                QTreeWidgetItem(self.connected_devices_tree, [device_id])

            self.update_devices_listbox_tab3()
            self.log_message(f"تم تحديث قائمة الأجهزة: {', '.join(self.detected_devices) if self.detected_devices else 'لا توجد أجهزة'}")

    def connect_device(self, ip_address=None):
        if not ip_address:
            QMessageBox.warning(self, "تحذير", "الرجاء اختيار جهاز من القائمة أو إدخال عنوان IP للجهاز يدوياً")
            return
        
        self.log_message(f"جاري الاتصال بـ {ip_address}...")
        self.update_connection_status("جاري الاتصال...")
        self.run_in_thread(self._connect_thread, ip_address.strip(), on_finish=self._connect_finished)

    def _connect_thread(self, ip):
        try:
            subprocess.run(["adb", "disconnect"], creationflags=self._get_creation_flags(), timeout=5)
            result = subprocess.run(["adb", "connect", ip], capture_output=True, text=True, timeout=10, creationflags=self._get_creation_flags())
            
            if "connected" in result.stdout:
                return {"success": True, "ip": ip, "message": "تم الاتصال بنجاح"}
            
            # Retry logic
            subprocess.run(["adb", "kill-server"], creationflags=self._get_creation_flags())
            subprocess.run(["adb", "start-server"], creationflags=self._get_creation_flags())
            time.sleep(2)
            retry_result = subprocess.run(["adb", "connect", ip], capture_output=True, text=True, creationflags=self._get_creation_flags())
            
            if "connected" in retry_result.stdout:
                return {"success": True, "ip": ip, "message": "تم الاتصال بنجاح بعد إعادة التشغيل"}
            else:
                return {"success": False, "message": retry_result.stderr or retry_result.stdout or "فشل الاتصال"}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "انتهى وقت انتظار الاتصال"}
        except Exception as e:
            return {"success": False, "message": f"خطأ: {e}"}

    def _connect_finished(self, result):
        if result and result["success"]:
            self.update_connection_status("متصل")
            self.log_message(result["message"])
            self.update_device_info()
            QMessageBox.information(self, "نجاح", f"اتصال ناجح بـ {result['ip']}")
            self.populate_device_list()
        else:
            self.update_connection_status("فشل الاتصال")
            msg = result['message'] if result else "حدث خطأ غير متوقع"
            self.log_message(f"فشل الاتصال: {msg}")
            QMessageBox.critical(self, "خطأ", f"فشل الاتصال بالجهاز:\n{msg}")

    def disconnect_device(self):
        ip = self.device_ip_edit.text()
        self.log_message(f"جاري قطع الاتصال عن {ip}...")
        self.update_connection_status("جاري قطع الاتصال...")
        self.run_in_thread(self._disconnect_thread, ip, on_finish=self._disconnect_finished)

    def _disconnect_thread(self, ip):
        try:
            result = subprocess.run(["adb", "disconnect", ip], capture_output=True, text=True, creationflags=self._get_creation_flags())
            if "disconnected" in result.stdout or not result.stderr:
                return {"success": True, "message": "تم قطع الاتصال بنجاح"}
            else:
                return {"success": False, "message": result.stderr}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _disconnect_finished(self, result):
        if result and result["success"]:
            self.update_connection_status("غير متصل")
            self.current_app_label.setText("غير معروف")
            self.log_message(result["message"])
            self.populate_device_list()
        else:
            msg = result['message'] if result else "خطأ"
            self.log_message(f"فشل قطع الاتصال: {msg}")
            self.run_in_thread(self._check_connection_status_thread, on_finish=lambda s: self.update_connection_status("متصل" if s else "غير متصل"))

    def _check_connection_status_thread(self):
        devices_output = subprocess.check_output(["adb", "devices"], text=True, creationflags=self._get_creation_flags())
        return "device" in devices_output

    def send_key(self, keycode):
        if not self.is_connected(): return
        self.log_message(f"إرسال أمر: {keycode}")
        self.run_in_thread(self._send_key_thread, keycode)

    def _send_key_thread(self, keycode):
        subprocess.run(["adb", "shell", "input", "keyevent", keycode], capture_output=True, creationflags=self._get_creation_flags())

    def update_device_info(self):
        if not self.is_connected(): return
        self.log_message("جاري تحديث معلومات الجهاز...")
        self.run_in_thread(self._update_device_info_thread, on_finish=self._update_device_info_finished)
    
    def _update_device_info_thread(self):
        try:
            result = subprocess.run(["adb", "shell", "dumpsys", "window", "windows"], capture_output=True, text=True, creationflags=self._get_creation_flags())
            if result.stdout:
                for line in result.stdout.splitlines():
                    if "mCurrentFocus" in line:
                        app = line.split()[-1].replace("}", "")
                        return app
            return None
        except Exception as e:
            print(f"Error updating device info: {e}")
            return None

    def _update_device_info_finished(self, app):
        if app:
            self.current_app_text = app
            self.current_app_label.setText(app)
            self.log_message(f"التطبيق الحالي: {app}")
        else:
            self.log_message("لم يتمكن من تحديد التطبيق الحالي")

    def take_screenshot(self):
        if not self.is_connected(): return
        self.log_message("جاري التقاط لقطة شاشة...")
        self.run_in_thread(self._take_screenshot_thread, on_finish=self._take_screenshot_finished)

    def _take_screenshot_thread(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            
            subprocess.run(["adb", "shell", "screencap", "-p", "/sdcard/screenshot.png"], creationflags=self._get_creation_flags())
            subprocess.run(["adb", "pull", "/sdcard/screenshot.png", filename], creationflags=self._get_creation_flags())
            subprocess.run(["adb", "shell", "rm", "/sdcard/screenshot.png"], creationflags=self._get_creation_flags())
            
            return {"success": True, "filename": filename}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _take_screenshot_finished(self, result):
        if result and result["success"]:
            self.log_message(f"تم حفظ لقطة الشاشة في: {result['filename']}")
            QMessageBox.information(self, "نجاح", f"تم حفظ لقطة الشاشة في:\n{result['filename']}")
        else:
            error = result['error'] if result else 'Unknown error'
            self.log_message(f"خطأ في التقاط لقطة الشاشة: {error}")
            QMessageBox.critical(self, "خطأ", f"فشل التقاط لقطة الشاشة:\n{error}")

    def clear_log(self):
        self.log_text_edit.clear()
        self.log_messages = []

    def save_log(self):
        filename, _ = QFileDialog.getSaveFileName(self, "حفظ السجل", f"firetv_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "Text Files (*.txt)")
        if not filename: return
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.writelines(self.log_messages)
            QMessageBox.information(self, "نجاح", f"تم حفظ السجل في {filename}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل حفظ السجل: {e}")

    # --- Auto-update timers ---
    def auto_update_info(self):
        if self.is_connected():
            self.update_device_info()
        QTimer.singleShot(10000, self.auto_update_info)

    def auto_update_devices(self):
        if self.auto_update_enabled:
            self.populate_device_list()
        QTimer.singleShot(5000, self.auto_update_devices)

    # ---FIX: Added missing methods from here ---
    
    def reset_adb_connection(self):
        self.log_message("جاري إعادة تعيين اتصال ADB...")
        self.run_in_thread(self._reset_adb_thread, on_finish=self._reset_adb_finished)

    def _reset_adb_thread(self):
        try:
            subprocess.run(["adb", "kill-server"], creationflags=self._get_creation_flags(), timeout=10)
            subprocess.run(["adb", "start-server"], creationflags=self._get_creation_flags(), timeout=10)
            time.sleep(2)
            return {"success": True, "message": "تم إعادة تعيين اتصال ADB بنجاح. يرجى محاولة الاتصال مرة أخرى."}
        except Exception as e:
            return {"success": False, "message": f"خطأ في إعادة تعيين ADB: {str(e)}"}

    def _reset_adb_finished(self, result):
        if result:
            self.log_message(result["message"])
            if result["success"]:
                self.populate_device_list()
            else:
                QMessageBox.critical(self, "خطأ", result["message"])

    def test_ping(self):
        ip = self.device_ip_edit.text().split(":")[0]
        self.log_message(f"جاري اختبار ping للعنوان {ip}...")
        self.run_in_thread(self._test_ping_thread, ip, on_finish=self._test_ping_finished)
    
    def _test_ping_thread(self, ip):
        try:
            param = "-n" if platform.system().lower() == "windows" else "-c"
            result = subprocess.run(["ping", param, "4", ip], capture_output=True, text=True, creationflags=self._get_creation_flags())
            if "TTL=" in result.stdout or "ttl=" in result.stdout:
                return {"success": True}
            else:
                return {"success": False}
        except Exception:
            return {"success": False}

    def _test_ping_finished(self, result):
        if result and result["success"]:
            self.log_message("نجاح: الجهاز يستجيب لـ ping")
            QMessageBox.information(self, "نجاح", "الجهاز يستجيب لـ ping\n\nتأكد من تفعيل ADB على الجهاز")
        else:
            self.log_message("فشل: الجهاز لا يستجيب لـ ping")
            QMessageBox.critical(self, "خطأ", "الجهاز لا يستجيب لـ ping\n\nتأكد من:\n1. أن الجهاز متصل بالشبكة\n2. أنك تستخدم الـ IP الصحيح")

    def enable_wireless_adb(self):
        ip = self.device_ip_edit.text().split(":")[0]
        self.log_message(f"جاري تفعيل ADB لاسلكي على {ip}...")
        self.run_in_thread(self._enable_wireless_adb_thread, ip, on_finish=self._enable_wireless_adb_finished)

    def _enable_wireless_adb_thread(self, ip):
        try:
            usb_result = subprocess.run(["adb", "devices"], capture_output=True, text=True, creationflags=self._get_creation_flags())
            if "device" not in usb_result.stdout:
                return {"success": False, "message": "يجب توصيل الجهاز عبر USB أولاً لتفعيل الوضع اللاسلكي"}
            
            subprocess.run(["adb", "tcpip", "5555"], creationflags=self._get_creation_flags())
            time.sleep(2)
            
            connect_result = subprocess.run(["adb", "connect", f"{ip}:5555"], capture_output=True, text=True, creationflags=self._get_creation_flags())
            if "connected" in connect_result.stdout:
                return {"success": True, "ip": ip}
            else:
                return {"success": False, "message": f"فشل تفعيل ADB لاسلكي:\n{connect_result.stderr}"}
        except Exception as e:
            return {"success": False, "message": f"خطأ: {e}"}

    def _enable_wireless_adb_finished(self, result):
        if result and result["success"]:
            self.log_message("تم تفعيل ADB لاسلكي بنجاح")
            QMessageBox.information(self, "نجاح", "تم تفعيل ADB لاسلكي بنجاح!\n\nيمكنك الآن فصل كابل USB")
            self.device_ip_edit.setText(f"{result['ip']}:5555")
            self.update_connection_status("متصل")
            self.populate_device_list()
        else:
            msg = result['message'] if result else "خطأ غير معروف"
            self.log_message(f"فشل تفعيل ADB لاسلكي: {msg}")
            QMessageBox.critical(self, "خطأ", msg)

    def toggle_power(self):
        self.send_key("KEYCODE_POWER")
    
    def sleep_wakeup(self):
        self.send_key("KEYCODE_SLEEP")

    def send_text_to_device(self):
        text = self.text_editor.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "تحذير", "الرجاء إدخال نص للإرسال")
            return
        if not self.is_connected(): return
        self.log_message(f"جاري إرسال النص: {text}")
        self.run_in_thread(self._send_text_thread, text, on_finish=lambda r: self.log_message("تم إرسال النص بنجاح"))
        
    def _send_text_thread(self, text):
        subprocess.run(["adb", "shell", "input", "text", text.replace(" ", "%s")], creationflags=self._get_creation_flags())

    def open_settings_shortcut(self):
        if not self.is_connected(): return
        self.log_message("جاري تنفيذ اختصار الإعدادات...")
        commands = [
            ("KEYCODE_SETTINGS", "فتح الإعدادات"),
            ("KEYCODE_DPAD_RIGHT", "التحرك يمين"),
            ("KEYCODE_DPAD_CENTER", "موافق/OK")
        ]
        self.run_in_thread(self._execute_sequence_thread, commands, on_finish=lambda r: self.log_message("تم تنفيذ الاختصار"))
        
    def _execute_sequence_thread(self, commands):
        for keycode, desc in commands:
            self.log_message(f"تنفيذ: {desc}")
            subprocess.run(["adb", "shell", "input", "keyevent", keycode], creationflags=self._get_creation_flags())
            time.sleep(0.5)
    
    # --- END of added methods ---
    
    def launch_app(self, package_name):
        if not self.is_connected(): return
        self.log_message(f"جاري تشغيل التطبيق: {package_name}")
        self.run_in_thread(self._launch_app_thread, package_name)
    
    def _launch_app_thread(self, package_name):
        result = subprocess.run(["adb", "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"],
                                capture_output=True, text=True, creationflags=self._get_creation_flags())
        if "Events injected: 1" not in result.stdout:
             subprocess.run(["adb", "shell", "am", "start", "-n", f"{package_name}/.MainActivity"],
                            capture_output=True, text=True, creationflags=self._get_creation_flags())
        time.sleep(1)
        # We need to emit a signal to run update_device_info in the main thread
        # A direct call is not thread-safe. Let's simplify and just log for now.
        # A more complex signal/slot mechanism would be needed for a direct update.
        # For simplicity, user can manually update.

    def force_stop_app(self):
        if not self.is_connected(): return
        current_app = self.current_app_text
        if current_app == "غير معروف":
            QMessageBox.warning(self, "تحذير", "لا يوجد تطبيق معروف قيد التشغيل")
            return
        self.log_message(f"جاري إيقاف التطبيق: {current_app}")
        self.run_in_thread(self._force_stop_thread, current_app)
    
    def _force_stop_thread(self, package_name):
        subprocess.run(["adb", "shell", "am", "force-stop", package_name],
                       capture_output=True, text=True, creationflags=self._get_creation_flags())
        time.sleep(1)

    def restart_app_tab3(self):
        if QMessageBox.question(self, "إعادة التشغيل", "هل تريد إغلاق التطبيق ثم فتحه مرة أخرى؟") == QMessageBox.StandardButton.Yes:
            QApplication.quit()
            os.execl(sys.executable, sys.executable, *sys.argv)
            
    def load_data(self):
        try:
            if not os.path.exists("device_data.txt"): return [], [], []
            with open("device_data.txt", "r") as file: lines = file.readlines()
            # Filter out empty or malformed lines
            valid_lines = [line.strip().split(',') for line in lines if line.strip() and len(line.strip().split(',')) == 3]
            if not valid_lines: return [], [], []
            ip_addresses, ports, pairing_codes = zip(*valid_lines)
            return list(set(ip_addresses)), list(set(ports)), list(set(pairing_codes))
        except Exception: return [], [], []
    
    def save_data(self, ip, port, code):
        try:
            with open("device_data.txt", "a") as file: file.write(f"{ip},{port},{code}\n")
        except Exception as e: QMessageBox.critical(self, "خطأ", f"لم يتم حفظ البيانات: {e}")

    def connect_device_tab3(self):
        ip, port = self.ip_combobox.currentText().strip(), self.port_combobox.currentText().strip()
        if not ip or not port:
            QMessageBox.critical(self, "خطأ", "يرجى إدخال عنوان IP والمنفذ")
            return
        self.connect_device(f"{ip}:{port}")

    def pair_device_tab3(self):
        ip, port, code = self.ip_combobox.currentText().strip(), self.port_combobox.currentText().strip(), self.pairing_combobox.currentText().strip()
        if not ip or not port or not code:
            QMessageBox.critical(self, "خطأ", "يرجى إدخال جميع الحقول")
            return
        self.run_in_thread(self._pair_device_thread, ip, port, code, on_finish=self._pair_finished)
        
    def _pair_device_thread(self, ip, port, code):
        command = ["adb", "pair", f"{ip}:{port}", code]
        result = subprocess.run(command, capture_output=True, text=True, creationflags=self._get_creation_flags())
        if "Successfully paired" in result.stdout:
            self.save_data(ip, port, code)
            return {"success": True, "ip": ip, "port": port}
        else:
            return {"success": False, "message": result.stdout or result.stderr}

    def _pair_finished(self, result):
        if result and result['success']:
            QMessageBox.information(self, "نجاح", f"تم إقران الجهاز بـ {result['ip']}:{result['port']} بنجاح!")
            self.populate_device_list()
        else:
            msg = result['message'] if result else "Unknown error"
            QMessageBox.critical(self, "فشل الإقران", msg)
            
    def update_devices_listbox_tab3(self):
        self.run_in_thread(self._update_devices_listbox_thread, on_finish=self._update_devices_listbox_finished)

    def _update_devices_listbox_thread(self):
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, creationflags=self._get_creation_flags())
        lines = [line for line in result.stdout.splitlines()[1:] if line.strip()]
        return lines

    def _update_devices_listbox_finished(self, lines):
        self.devices_listbox.clear()
        self.devices_listbox.addItems(lines)

    # Stubs for other methods to prevent crashes - you can implement them following the same pattern
    def show_apps_list(self):
        QMessageBox.information(self, "قيد الإنشاء", "وظيفة عرض التطبيقات لم يتم تنفيذها بالكامل بعد.")
        
    def show_device_info(self):
        QMessageBox.information(self, "قيد الإنشاء", "وظيفة معلومات الجهاز لم يتم تنفيذها بالكامل بعد.")

    def show_device_info_tab3(self):
        QMessageBox.information(self, "قيد الإنشاء", "وظيفة معلومات الجهاز لم يتم تنفيذها بالكامل بعد.")

    def connect_default_port_tab3(self):
        ip = self.ip_combobox.currentText().strip()
        if not ip:
            QMessageBox.critical(self, "خطأ", "يرجى إدخال عنوان IP")
            return
        self.connect_device(f"{ip}:5555")

    def pair_without_code_tab3(self):
        QMessageBox.information(self, "قيد الإنشاء", "وظيفة الإقران بدون رمز لم يتم تنفيذها بالكامل بعد.")

    def show_adb_version_tab3(self):
        self.run_in_thread(lambda: subprocess.check_output(['adb', 'version'], text=True), 
                           on_finish=lambda v: QMessageBox.information(self, "إصدار ADB", v))
    
    def disconnect_device_tab3(self):
        selected_item = self.devices_listbox.currentItem()
        if not selected_item:
            QMessageBox.critical(self, "خطأ", "يرجى اختيار جهاز")
            return
        ip_port = selected_item.text().split("\t")[0]
        self.run_in_thread(lambda ip: subprocess.run(['adb', 'disconnect', ip], capture_output=True), ip_port,
                           on_finish=lambda r: self.populate_device_list())

    def disconnect_all_devices_tab3(self):
        if QMessageBox.question(self, "تأكيد", "هل تريد فصل جميع الأجهزة؟") == QMessageBox.StandardButton.Yes:
            self.run_in_thread(lambda: subprocess.run(['adb', 'disconnect'], capture_output=True),
                               on_finish=lambda r: self.populate_device_list())
            
    def toggle_auto_update_tab3(self):
        self.auto_update_enabled = not self.auto_update_enabled
        if self.auto_update_enabled:
            self.toggle_button.setText("إيقاف التحديث التلقائي")
            self.auto_update_devices()
        else:
            self.toggle_button.setText("تشغيل التحديث التلقائي")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FireTVController()
    window.show()
    sys.exit(app.exec())