import sys
import os
import re
import subprocess
import threading # لاستخدام الخيوط
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QListWidget, QListWidgetItem, QMessageBox, QScrollArea,
    QGroupBox, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QStatusBar, QFrame # لإضافة شريط الحالة و خط فاصل
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal # لاستخدام خيوط PyQt وإشاراتها
from PyQt6.QtGui import QFont, QIcon, QCursor # لإضافة أيقونات وتغيير مؤشر الفأرة

# --- تعريف خيط العامل لتشغيل أوامر ADB في الخلفية ---
class Worker(QThread):
    """
    خيط عامل لتشغيل المهام التي تستغرق وقتًا طويلاً (مثل أوامر ADB)
    دون تجميد الواجهة الرسومية الرئيسية.
    """
    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)
    started_operation = pyqtSignal(str)
    finished_operation = pyqtSignal()
    # task_description can be set on the instance after creation

    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.task_description = None # Initialize description attribute

    def run(self):
        """
        يتم تشغيل هذه الدالة عند بدء الخيط.
        """
        try:
            # Use task_description if available for the message
            op_name = getattr(self, 'task_description', None) or getattr(self.function, '__name__', 'العملية')
            self.started_operation.emit(f"جارٍ تنفيذ {op_name}...")
            result = self.function(*self.args, **self.kwargs)
            self.result_ready.emit(result)
        except FileNotFoundError as e:
            self.error_occurred.emit(f"خطأ: لم يتم العثور على الأمر 'adb'. يرجى التأكد من تثبيته وإضافته إلى متغير البيئة PATH.\n{e}")
        except subprocess.TimeoutExpired as e:
             cmd_str = ' '.join(e.cmd) if hasattr(e, 'cmd') and e.cmd else 'الأمر'
             self.error_occurred.emit(f"خطأ: انتهت مهلة انتظار {cmd_str}. قد يكون الجهاز غير مستجيب أو الاتصال ضعيف.")
        except subprocess.CalledProcessError as e:
             error_output = e.stderr or e.stdout or "لا يوجد خرج خطأ محدد"
             cmd_str = ' '.join(e.cmd) if hasattr(e, 'cmd') and e.cmd else ''
             self.error_occurred.emit(f"خطأ أثناء تنفيذ أمر ADB:\n{error_output}\n(الأمر: {cmd_str})")
        except Exception as e:
            # Include exception type for better debugging
            self.error_occurred.emit(f"حدث خطأ غير متوقع ({type(e).__name__}): {e}")
        finally:
            self.finished_operation.emit()

# --- الفئة الرئيسية للتطبيق ---
class ADBManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("إدارة اتصالات ADB عبر Wi-Fi وأوامر الإدخال")
        self.setGeometry(100, 100, 950, 780) # زيادة الارتفاع قليلاً للزر الجديد

        self.active_workers = []
        self.auto_update_enabled = True

        self.setup_ui()
        self.load_data()

        QTimer.singleShot(100, self.initial_adb_check_and_update)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("جاهز.")

    def setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        splitter = QSplitter(Qt.Orientation.Vertical)

        # --- الجزء العلوي: عناصر التحكم بالاتصال ---
        top_widget = QWidget()
        top_layout = QGridLayout()

        ip_label = QLabel("عنوان IP:")
        ip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(ip_label, 0, 0)
        self.ip_combo = QComboBox()
        self.ip_combo.setEditable(True)
        top_layout.addWidget(self.ip_combo, 0, 1)

        port_label = QLabel("المنفذ:")
        port_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(port_label, 1, 0)
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.addItems(["5555", "9000"])
        top_layout.addWidget(self.port_combo, 1, 1)

        pairing_label = QLabel("رمز الإقران:")
        pairing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(pairing_label, 2, 0)
        self.pairing_combo = QComboBox()
        self.pairing_combo.setEditable(True)
        top_layout.addWidget(self.pairing_combo, 2, 1)

        # أزرار الاتصال والإقران
        self.connect_btn = QPushButton("اتصال")
        self.connect_btn.setObjectName("connect_btn") # Set object name
        self.connect_btn.clicked.connect(self.connect_device)
        self.connect_btn.setIcon(QIcon.fromTheme("network-connect"))
        self.connect_btn.setToolTip("اتصل بالجهاز باستخدام عنوان IP والمنفذ المدخلين")
        top_layout.addWidget(self.connect_btn, 0, 2)

        self.pair_btn = QPushButton("إقران")
        self.pair_btn.setObjectName("pair_btn")
        self.pair_btn.clicked.connect(self.pair_device)
        self.pair_btn.setIcon(QIcon.fromTheme("network-wireless-encrypted"))
        self.pair_btn.setToolTip("إقران جهاز جديد باستخدام عنوان IP والمنفذ ورمز الإقران")
        top_layout.addWidget(self.pair_btn, 1, 2)

        self.default_connect_btn = QPushButton("اتصال افتراضي (5555)")
        self.default_connect_btn.setObjectName("default_connect_btn")
        self.default_connect_btn.clicked.connect(self.connect_default_port)
        self.default_connect_btn.setIcon(QIcon.fromTheme("network-wired"))
        self.default_connect_btn.setToolTip("اتصل بالجهاز باستخدام عنوان IP والمنفذ الافتراضي (5555)")
        top_layout.addWidget(self.default_connect_btn, 0, 3)

        self.pair_without_code_btn = QPushButton("إقران بدون رمز")
        self.pair_without_code_btn.setObjectName("pair_without_code_btn")
        self.pair_without_code_btn.clicked.connect(self.pair_without_code)
        self.pair_without_code_btn.setIcon(QIcon.fromTheme("network-wireless"))
        self.pair_without_code_btn.setToolTip("إقران جهاز جديد بدون استخدام رمز الإقران (يتطلب تأكيدًا على الجهاز أو إدخال رمز)")
        top_layout.addWidget(self.pair_without_code_btn, 1,3)

        adb_version_btn = QPushButton("إصدار ADB")
        # adb_version_btn.setObjectName("adb_version_btn") # Not strictly needed unless referenced later
        adb_version_btn.clicked.connect(self.show_adb_version)
        adb_version_btn.setIcon(QIcon.fromTheme("help-about"))
        adb_version_btn.setToolTip("عرض معلومات إصدار ADB المثبت")
        top_layout.addWidget(adb_version_btn, 2, 3)

        top_widget.setLayout(top_layout)

        # --- الجزء الأوسط: قائمة الأجهزة وأزرار التحكم ---
        middle_widget = QWidget()
        middle_layout = QVBoxLayout()

        devices_group = QGroupBox("الأجهزة المتصلة")
        devices_layout = QVBoxLayout()
        self.devices_list = QListWidget()
        self.devices_list.itemSelectionChanged.connect(self.update_dependent_buttons)
        devices_layout.addWidget(self.devices_list)
        devices_group.setLayout(devices_layout)
        middle_layout.addWidget(devices_group)

        general_controls_group = QGroupBox("تحكم عام")
        general_controls_layout = QHBoxLayout()

        self.update_btn = QPushButton("تحديث")
        self.update_btn.setObjectName("update_btn")
        self.update_btn.clicked.connect(self.trigger_update_devices_list)
        self.update_btn.setIcon(QIcon.fromTheme("view-refresh"))
        self.update_btn.setToolTip("تحديث قائمة الأجهزة المتصلة")
        general_controls_layout.addWidget(self.update_btn)

        self.disconnect_btn = QPushButton("فصل المحدد")
        self.disconnect_btn.setObjectName("disconnect_btn")
        self.disconnect_btn.clicked.connect(self.disconnect_device)
        self.disconnect_btn.setIcon(QIcon.fromTheme("network-disconnect"))
        self.disconnect_btn.setToolTip("فصل الجهاز المحدد من قائمة الأجهزة")
        general_controls_layout.addWidget(self.disconnect_btn)

        self.disconnect_all_btn = QPushButton("فصل الكل")
        self.disconnect_all_btn.setObjectName("disconnect_all_btn")
        self.disconnect_all_btn.clicked.connect(self.disconnect_all_devices)
        self.disconnect_all_btn.setIcon(QIcon.fromTheme("network-offline"))
        self.disconnect_all_btn.setToolTip("فصل جميع الأجهزة المتصلة")
        general_controls_layout.addWidget(self.disconnect_all_btn)

        self.toggle_update_btn = QPushButton("إيقاف التحديث التلقائي")
        self.toggle_update_btn.setObjectName("toggle_update_btn")
        self.toggle_update_btn.clicked.connect(self.toggle_auto_update)
        self.toggle_update_btn.setIcon(QIcon.fromTheme("media-playback-stop"))
        self.toggle_update_btn.setToolTip("تشغيل/إيقاف التحديث التلقائي لقائمة الأجهزة (كل 8 ثوانٍ)")
        general_controls_layout.addWidget(self.toggle_update_btn)

        general_controls_group.setLayout(general_controls_layout)
        middle_layout.addWidget(general_controls_group)

        keyevent_group = QGroupBox("أوامر الإدخال (للجهاز المحدد)")
        keyevent_layout = QGridLayout()

        self.keyevent_243_btn = QPushButton("الرئيسية")
        self.keyevent_243_btn.setObjectName("keyevent_243_btn")
        self.keyevent_243_btn.setToolTip("الرئيسية")
        self.keyevent_243_btn.clicked.connect(lambda: self.send_keyevent("3"))
        keyevent_layout.addWidget(self.keyevent_243_btn, 0, 0)

        self.keyevent_244_btn = QPushButton("الرجوع")
        self.keyevent_244_btn.setObjectName("keyevent_244_btn")
        self.keyevent_244_btn.setToolTip("الرجوع")
        self.keyevent_244_btn.clicked.connect(lambda: self.send_keyevent("4"))
        keyevent_layout.addWidget(self.keyevent_244_btn, 0, 1)

        self.keyevent_245_btn = QPushButton("OK")
        self.keyevent_245_btn.setObjectName("keyevent_245_btn")
        self.keyevent_245_btn.setToolTip("OK")
        self.keyevent_245_btn.clicked.connect(lambda: self.send_keyevent("66"))
        keyevent_layout.addWidget(self.keyevent_245_btn, 0,2)

        self.keyevent_246_btn = QPushButton("كتم")
        self.keyevent_246_btn.setObjectName("keyevent_246_btn")
        self.keyevent_246_btn.setToolTip("كتم")
        self.keyevent_246_btn.clicked.connect(lambda: self.send_keyevent("91"))
        keyevent_layout.addWidget(self.keyevent_246_btn, 1, 0)

        self.keyevent_vol_down_btn = QPushButton("خفض الصوت")
        self.keyevent_vol_down_btn.setObjectName("keyevent_vol_down_btn")
        self.keyevent_vol_down_btn.setToolTip("خفض الصوت")
        self.keyevent_vol_down_btn.clicked.connect(lambda: self.send_keyevent("25"))  # KEYCODE_VOLUME_DOWN
        keyevent_layout.addWidget(self.keyevent_vol_down_btn, 1, 1)


        self.keyevent_vol_up_btn = QPushButton("رفع الصوت")
        self.keyevent_vol_up_btn.setObjectName("keyevent_vol_up_btn")
        self.keyevent_vol_up_btn.setToolTip("رفع الصوت")
        self.keyevent_vol_up_btn.clicked.connect(lambda: self.send_keyevent("24"))  # KEYCODE_VOLUME_UP
        keyevent_layout.addWidget(self.keyevent_vol_up_btn, 1, 2)

        self.keyevent_sleep_btn = QPushButton("نوم")
        self.keyevent_sleep_btn.setObjectName("keyevent_sleep_btn")
        self.keyevent_sleep_btn.setToolTip("إدخال الجهاز في وضع النوم")
        self.keyevent_sleep_btn.clicked.connect(lambda: self.send_keyevent("223"))  # KEYCODE_SLEEP
        keyevent_layout.addWidget(self.keyevent_sleep_btn, 4, 0)

        self.keyevent_power_btn = QPushButton("تشغيل / إيقاف")
        self.keyevent_power_btn.setObjectName("keyevent_power_btn")
        self.keyevent_power_btn.setToolTip("تشغيل أو إيقاف الجهاز")
        self.keyevent_power_btn.clicked.connect(lambda: self.send_keyevent("26"))  # KEYCODE_POWER
        keyevent_layout.addWidget(self.keyevent_power_btn, 2, 0)

        self.keyevent_reboot_btn = QPushButton("إعادة تشغيل")
        self.keyevent_reboot_btn.setObjectName("keyevent_reboot_btn")
        self.keyevent_reboot_btn.setToolTip("إعادة تشغيل الجهاز")
        self.keyevent_reboot_btn.clicked.connect(lambda: self.send_reboot())  # تحتاج دالة خاصة لأن الأمر ليس keyevent
        keyevent_layout.addWidget(self.keyevent_reboot_btn, 2, 1)




        self.keyevent_wakeup_btn = QPushButton("إيقاظ")
        self.keyevent_wakeup_btn.setObjectName("keyevent_wakeup_btn")
        self.keyevent_wakeup_btn.setToolTip("إيقاظ الجهاز")
        self.keyevent_wakeup_btn.clicked.connect(lambda: self.send_keyevent("224"))  # KEYCODE_WAKEUP
        keyevent_layout.addWidget(self.keyevent_wakeup_btn, 4, 1)

        self.keyevent_up_btn = QPushButton("↑")
        self.keyevent_up_btn.setObjectName("keyevent_up_btn")
        self.keyevent_up_btn.setToolTip("أعلى")
        self.keyevent_up_btn.clicked.connect(lambda: self.send_keyevent("19"))  # KEYCODE_DPAD_UP
        keyevent_layout.addWidget(self.keyevent_up_btn, 5, 0)

        self.keyevent_down_btn = QPushButton("↓")
        self.keyevent_down_btn.setObjectName("keyevent_down_btn")
        self.keyevent_down_btn.setToolTip("أسفل")
        self.keyevent_down_btn.clicked.connect(lambda: self.send_keyevent("20"))  # KEYCODE_DPAD_DOWN
        keyevent_layout.addWidget(self.keyevent_down_btn, 5, 1)

        self.keyevent_left_btn = QPushButton("←")
        self.keyevent_left_btn.setObjectName("keyevent_left_btn")
        self.keyevent_left_btn.setToolTip("يسار")
        self.keyevent_left_btn.clicked.connect(lambda: self.send_keyevent("21"))  # KEYCODE_DPAD_LEFT
        keyevent_layout.addWidget(self.keyevent_left_btn, 6, 0)

        self.keyevent_right_btn = QPushButton("→")
        self.keyevent_right_btn.setObjectName("keyevent_right_btn")
        self.keyevent_right_btn.setToolTip("يمين")
        self.keyevent_right_btn.clicked.connect(lambda: self.send_keyevent("22"))  # KEYCODE_DPAD_RIGHT
        keyevent_layout.addWidget(self.keyevent_right_btn, 6, 1)

        self.keyevent_up_btn = QPushButton("↑1")
        self.keyevent_up_btn.setObjectName("keyevent_up_btn")
        self.keyevent_up_btn.setToolTip("أعلى")
        self.keyevent_up_btn.clicked.connect(lambda: self.send_keyevent("243"))  # KEYCODE_DPAD_UP
        keyevent_layout.addWidget(self.keyevent_up_btn, 7, 0)

        self.keyevent_down_btn = QPushButton("↓2")
        self.keyevent_down_btn.setObjectName("keyevent_down_btn")
        self.keyevent_down_btn.setToolTip("أسفل")
        self.keyevent_down_btn.clicked.connect(lambda: self.send_keyevent("244"))  # KEYCODE_DPAD_DOWN
        keyevent_layout.addWidget(self.keyevent_down_btn, 7, 1)

        self.keyevent_left_btn = QPushButton("←3")
        self.keyevent_left_btn.setObjectName("keyevent_left_btn")
        self.keyevent_left_btn.setToolTip("يسار")
        self.keyevent_left_btn.clicked.connect(lambda: self.send_keyevent("245"))  # KEYCODE_DPAD_LEFT
        keyevent_layout.addWidget(self.keyevent_left_btn, 7, 2)

        self.keyevent_right_btn = QPushButton("→4")
        self.keyevent_right_btn.setObjectName("keyevent_right_btn")
        self.keyevent_right_btn.setToolTip("يمين")
        self.keyevent_right_btn.clicked.connect(lambda: self.send_keyevent("246"))  # KEYCODE_DPAD_RIGHT
        keyevent_layout.addWidget(self.keyevent_right_btn, 7, 3)




        keyevent_group.setLayout(keyevent_layout)
        middle_layout.addWidget(keyevent_group)

        middle_widget.setLayout(middle_layout)


        # --- الجزء السفلي: معلومات الجهاز و getprop ---
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout()

        # Container for info buttons
        info_buttons_layout = QHBoxLayout()

        self.info_btn = QPushButton("عرض معلومات الجهاز") # نص أقصر
        self.info_btn.setObjectName("info_btn")
        self.info_btn.clicked.connect(self.show_device_info)
        self.info_btn.setIcon(QIcon.fromTheme("system-search"))
        self.info_btn.setToolTip("عرض معلومات مفصلة عن الجهاز المحدد في المربع أدناه")
        info_buttons_layout.addWidget(self.info_btn)

        # ***** زر getprop الجديد *****
        self.getprop_btn = QPushButton("عرض الخصائص (getprop)")
        self.getprop_btn.setObjectName("getprop_btn") # Set object name
        self.getprop_btn.clicked.connect(self.show_raw_properties) # Connect to new handler
        self.getprop_btn.setIcon(QIcon.fromTheme("document-properties")) # Suggestion
        self.getprop_btn.setToolTip("عرض قائمة الخصائص الأولية للجهاز المحدد (adb shell getprop)")
        info_buttons_layout.addWidget(self.getprop_btn) # Add to the same layout as info_btn
        # ***** نهاية زر getprop *****

        bottom_layout.addLayout(info_buttons_layout) # Add the horizontal layout for buttons

        self.info_display = QTextEdit()
        self.info_display.setReadOnly(True)
        font = QFont("Monospace")
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.info_display.setFont(font)
        bottom_layout.addWidget(self.info_display)

        bottom_widget.setLayout(bottom_layout)

        # إضافة الأجزاء إلى الفاصل
        splitter.addWidget(top_widget)
        splitter.addWidget(middle_widget)
        splitter.addWidget(bottom_widget)

        # تعيين الأحجام الأولية النسبية للأجزاء
        splitter.setSizes([150, 280, 350]) # تعديل الأحجام قليلاً

        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        # --- نهاية setup_ui ---

    def set_ui_busy(self, busy, message="جارٍ العمل..."):
        """
        تعطيل/تمكين عناصر الواجهة وتغيير مؤشر الفأرة وشريط الحالة.
        """
        buttons_to_manage = [
            self.connect_btn, self.pair_btn, self.default_connect_btn,
            self.pair_without_code_btn, self.update_btn, self.disconnect_btn,
            self.disconnect_all_btn, self.info_btn, self.getprop_btn, # إضافة زر getprop
            self.keyevent_243_btn, self.keyevent_244_btn,
            self.keyevent_245_btn, self.keyevent_246_btn
        ]

        if busy:
            self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
            self.status_bar.showMessage(message)
            for btn in buttons_to_manage:
                if btn: # Check if button exists
                    btn.setEnabled(False)
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            self.status_bar.showMessage("جاهز.")
            # Enable general buttons first
            self.connect_btn.setEnabled(True)
            self.pair_btn.setEnabled(True)
            self.default_connect_btn.setEnabled(True)
            self.pair_without_code_btn.setEnabled(True)
            self.update_btn.setEnabled(True)
            # Let update_dependent_buttons handle the rest based on selection/list state
            self.update_dependent_buttons()


    def initial_adb_check_and_update(self):
        """
        يقوم بالفحص الأولي لوجود ADB وتحديث قائمة الأجهزة.
        """
        if self.check_adb_exists():
            self.trigger_update_devices_list()
            self.start_auto_update()
        else:
             self.set_ui_busy(True, "خطأ: لم يتم العثور على ADB.")
             # Disable all buttons that rely on ADB
             buttons_to_disable = [
                 self.connect_btn, self.pair_btn, self.default_connect_btn,
                 self.pair_without_code_btn, self.update_btn, self.disconnect_btn,
                 self.disconnect_all_btn, self.info_btn, self.toggle_update_btn, # Keep toggle update maybe? debatable
                 self.getprop_btn, # إضافة زر getprop
                 self.keyevent_243_btn, self.keyevent_244_btn,
                 self.keyevent_245_btn, self.keyevent_246_btn
             ]
             for btn in buttons_to_disable:
                 if btn: # Check if button exists
                     btn.setEnabled(False)


    def run_adb_command(self, command_list, success_message=None, failure_title="خطأ", on_success=None, show_success_popup=True, command_timeout=15, task_description=None):
        """
        دالة مساعدة لتشغيل أمر ADB في خيط منفصل.
        """
        def command_executor():
            cmd_list_str = [str(part) for part in command_list]
            result = subprocess.run(cmd_list_str, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore', timeout=command_timeout)
            return result.stdout

        worker = Worker(command_executor)

        if task_description:
            worker.task_description = task_description
        else:
             try:
                 worker.task_description = ' '.join(map(str, command_list))
             except Exception:
                 worker.task_description = "adb_command"

        worker.result_ready.connect(lambda result: self._handle_adb_success(result, success_message, on_success, show_success_popup))
        worker.error_occurred.connect(lambda error_msg: self._handle_adb_error(error_msg, failure_title))
        worker.started_operation.connect(lambda msg: self.set_ui_busy(True, msg))
        worker.finished_operation.connect(lambda: self._worker_finished(worker))

        self.active_workers.append(worker)
        worker.start()


    def _handle_adb_success(self, result, success_message, on_success_callback, show_popup):
        """معالجة نجاح أمر ADB."""
        if show_popup and success_message:
            QMessageBox.information(self, "نجاح", success_message)
        elif success_message:
             self.status_bar.showMessage(success_message, 3000)
        if on_success_callback:
            on_success_callback(result)


    def _handle_adb_error(self, error_msg, failure_title):
        """معالجة فشل أمر ADB."""
        QMessageBox.critical(self, failure_title, error_msg)
        self.status_bar.showMessage(f"{failure_title}: خطأ - انظر الرسالة", 5000)


    def _worker_finished(self, worker):
        """يتم استدعاؤها عند انتهاء الخيط العامل."""
        if worker in self.active_workers:
            self.active_workers.remove(worker)
        if not self.active_workers:
            self.set_ui_busy(False)
        else:
            running_tasks = [getattr(w, 'task_description', 'عملية أخرى') for w in self.active_workers if w.isRunning()]
            if running_tasks:
                 self.status_bar.showMessage(f"جارٍ تنفيذ: {running_tasks[0]}...")
            else:
                 self.set_ui_busy(False)


    # --- دوال الأوامر ---

    def connect_device(self):
        ip_address = self.ip_combo.currentText().strip()
        port = self.port_combo.currentText().strip()
        if not ip_address or not port:
            QMessageBox.warning(self, "إدخال ناقص", "يرجى إدخال عنوان IP والمنفذ.")
            return
        target = f"{ip_address}:{port}"
        command = ["adb", "connect", target]
        task_desc = f"connect_{target}"

        def on_connect_success(result_stdout):
            if re.search(r"(already )?connected to {}".format(re.escape(target)), result_stdout):
                self.status_bar.showMessage(f"تم الاتصال بـ {target} بنجاح!", 4000)
                self.save_data(ip_address, port, "")
                self.load_data()
                self.trigger_update_devices_list()
            elif "failed to connect to" in result_stdout or "unable to connect" in result_stdout:
                 self._handle_adb_error(f"فشل الاتصال بـ {target}:\n{result_stdout}", "فشل الاتصال")
                 self.trigger_update_devices_list()
            else:
                 QMessageBox.warning(self, "نتيجة غير مؤكدة", f"ADB لم يؤكد الاتصال أو الفشل بشكل صريح:\n{result_stdout}")
                 self.trigger_update_devices_list()

        self.run_adb_command(command, failure_title="فشل الاتصال", on_success=on_connect_success, show_success_popup=False, task_description=task_desc)


    def pair_device(self):
        ip_address = self.ip_combo.currentText().strip()
        port = self.port_combo.currentText().strip()
        pairing_code = self.pairing_combo.currentText().strip()
        if not ip_address or not port or not pairing_code:
            QMessageBox.warning(self, "إدخال ناقص", "يرجى إدخال عنوان IP، المنفذ، ورمز الإقران.")
            return
        target = f"{ip_address}:{port}"
        command = ["adb", "pair", target, pairing_code]
        task_desc = f"pair_{target}"

        def on_pair_success(result_stdout):
             if "Successfully paired to" in result_stdout:
                 QMessageBox.information(self, "نجاح", f"تم إقران الجهاز بـ {target} بنجاح!")
                 self.save_data(ip_address, port, pairing_code)
                 self.load_data()
                 self.trigger_update_devices_list()
             elif "Failed to pair to" in result_stdout:
                 self._handle_adb_error(f"فشل الإقران مع {target}:\n{result_stdout}", "فشل الإقران")
             else:
                 self._handle_adb_error(f"فشل الإقران مع {target} (نتيجة غير متوقعة):\n{result_stdout}", "فشل الإقران")

        self.run_adb_command(command, failure_title="فشل الإقران", on_success=on_pair_success, show_success_popup=False, task_description=task_desc)


    def connect_default_port(self):
        ip_address = self.ip_combo.currentText().strip()
        default_port = "5555"
        if not ip_address:
            QMessageBox.warning(self, "إدخال ناقص", "يرجى إدخال عنوان IP.")
            return
        target = f"{ip_address}:{default_port}"
        command = ["adb", "connect", target]
        task_desc = f"connect_default_{ip_address}"

        def on_connect_success(result_stdout):
             if re.search(r"(already )?connected to {}".format(re.escape(target)), result_stdout):
                 self.status_bar.showMessage(f"تم الاتصال بـ {target} بنجاح!", 4000)
                 self.save_data(ip_address, default_port, "")
                 self.load_data()
                 self.trigger_update_devices_list()
             elif "failed to connect to" in result_stdout or "unable to connect" in result_stdout:
                 self._handle_adb_error(f"فشل الاتصال بـ {target}:\n{result_stdout}", "فشل الاتصال")
                 self.trigger_update_devices_list()
             else:
                 QMessageBox.warning(self, "نتيجة غير مؤكدة", f"ADB لم يؤكد الاتصال أو الفشل بشكل صريح:\n{result_stdout}")
                 self.trigger_update_devices_list()

        self.run_adb_command(command, failure_title="فشل الاتصال", on_success=on_connect_success, show_success_popup=False, task_description=task_desc)


    def pair_without_code(self):
        ip_address = self.ip_combo.currentText().strip()
        port = self.port_combo.currentText().strip()
        if not ip_address or not port:
             QMessageBox.warning(self, "إدخال ناقص", "يرجى إدخال عنوان IP والمنفذ.")
             return
        target = f"{ip_address}:{port}"
        command = ["adb", "pair", target]
        task_desc = f"pair_nocode_{target}"

        def on_pair_success(result_stdout):
            if "Successfully paired to" in result_stdout:
                 QMessageBox.information(self, "نجاح", f"تم إقران الجهاز بـ {target} بنجاح!\nقد تحتاج لإدخال رمز يظهر على الجهاز إذا لم يتم الاتصال تلقائيًا.")
                 self.save_data(ip_address, port, "")
                 self.load_data()
                 self.trigger_update_devices_list()
            elif "Enter pairing code" in result_stdout:
                  QMessageBox.warning(self, "مطلوب إدخال رمز", f"يرجى إدخال رمز الإقران الظاهر على الجهاز في الطرفية (الكونسول) التي يعمل منها هذا البرنامج.\n\nخرج ADB:\n{result_stdout}")
            elif "Failed to pair to" in result_stdout:
                self._handle_adb_error(f"فشل الإقران مع {target}:\n{result_stdout}", "فشل الإقران")
            else:
                 self._handle_adb_error(f"فشل الإقران مع {target} (نتيجة غير متوقعة):\n{result_stdout}", "فشل الإقران")

        self.run_adb_command(command, failure_title="فشل الإقران", on_success=on_pair_success, show_success_popup=False, command_timeout=30, task_description=task_desc)


    def trigger_update_devices_list(self):
        """ يبدأ تحديث قائمة الأجهزة في خيط منفصل. """
        command = ["adb", "devices"]

        def on_devices_list_success(result_stdout):
            current_selection_text = self.devices_list.currentItem().text() if self.devices_list.currentItem() else None
            self.devices_list.clear()
            lines = result_stdout.splitlines()
            device_lines = []
            in_device_list = False
            for line in lines:
                line = line.strip()
                if line.startswith("List of devices attached"):
                    in_device_list = True
                    continue
                if in_device_list and line:
                    if re.match(r"^[a-zA-Z0-9.:_-]+\s+(device|offline|unauthorized|authorizing|connecting)", line):
                         device_lines.append(line)
                    elif not line.startswith('*') and 'daemon' not in line:
                        pass

            if not device_lines:
                 self.devices_list.addItem("لا توجد أجهزة متصلة.")
                 self.devices_list.setEnabled(False)
            else:
                self.devices_list.setEnabled(True)
                restored_selection = False
                for line in device_lines:
                    item = QListWidgetItem(line)
                    self.devices_list.addItem(item)
                    if current_selection_text and line == current_selection_text:
                        self.devices_list.setCurrentItem(item)
                        restored_selection = True
                if not restored_selection:
                     self.devices_list.clearSelection()

            self.update_dependent_buttons()

        self.run_adb_command(
            command,
            failure_title="فشل تحديث القائمة",
            on_success=on_devices_list_success,
            show_success_popup=False,
            task_description="adb_devices"
        )


    def update_dependent_buttons(self):
        """تحديث حالة الأزرار التي تعتمد على قائمة الأجهزة أو العنصر المحدد."""
        selected_item = self.devices_list.currentItem()
        is_valid_selection = selected_item is not None and "لا توجد أجهزة متصلة" not in selected_item.text()

        has_real_items = self.devices_list.count() > 0 and (self.devices_list.count() > 1 or "لا توجد أجهزة متصلة" not in self.devices_list.item(0).text())

        # تمكين/تعطيل الأزرار المعتمدة
        self.disconnect_btn.setEnabled(is_valid_selection)
        self.info_btn.setEnabled(is_valid_selection)
        self.getprop_btn.setEnabled(is_valid_selection) # إضافة زر getprop
        self.keyevent_243_btn.setEnabled(is_valid_selection)
        self.keyevent_244_btn.setEnabled(is_valid_selection)
        self.keyevent_245_btn.setEnabled(is_valid_selection)
        self.keyevent_246_btn.setEnabled(is_valid_selection)

        self.disconnect_all_btn.setEnabled(has_real_items)


    def _get_selected_device_id(self):
        """Helper function to get the validated device ID from the list selection."""
        selected = self.devices_list.currentItem()
        if not selected or "لا توجد أجهزة متصلة" in selected.text():
            QMessageBox.warning(self, "خطأ", "يرجى تحديد جهاز صالح أولاً.")
            return None
        try:
            match = re.match(r"([^\s\t]+)", selected.text())
            if not match: raise ValueError("لم يتم العثور على معرف جهاز صالح.")
            device_id = match.group(1).strip()
            if not device_id: raise ValueError("معرف جهاز فارغ")
            return device_id
        except (IndexError, ValueError, AttributeError) as e:
            QMessageBox.critical(self, "خطأ", f"لا يمكن استخلاص معرف الجهاز: {selected.text()}\n{e}")
            return None


    def disconnect_device(self):
        device_id = self._get_selected_device_id()
        if not device_id:
            return

        command = ["adb", "disconnect", device_id]
        task_desc = f"disconnect_{device_id}"
        self.run_adb_command(
            command,
            success_message=f"تم طلب فصل الاتصال بـ {device_id}.",
            failure_title="فشل فصل الاتصال",
            on_success=lambda r: self.trigger_update_devices_list(),
            show_success_popup=False,
            task_description=task_desc
        )


    def disconnect_all_devices(self):
        if self.devices_list.count() == 0 or (self.devices_list.count() == 1 and "لا توجد أجهزة متصلة" in self.devices_list.item(0).text()):
            QMessageBox.information(self, "معلومة", "لا توجد أجهزة متصلة حاليًا لفصلها.")
            return

        reply = QMessageBox.question(
            self, "تأكيد", "هل أنت متأكد أنك تريد فصل جميع الأجهزة المتصلة عبر ADB؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            command = ["adb", "disconnect"]
            task_desc = "disconnect_all"
            self.run_adb_command(
                command,
                success_message="تم إرسال أمر فصل جميع الأجهزة.",
                failure_title="فشل فصل الكل",
                on_success=lambda r: self.trigger_update_devices_list(),
                show_success_popup=True,
                task_description=task_desc
            )


    def show_device_info(self):
        """ عرض معلومات الجهاز المحدد (تجميع مفصل). """
        device_id = self._get_selected_device_id()
        if not device_id:
            return

        self.info_display.clear()
        self.info_display.setPlainText(f"جارٍ جلب المعلومات للجهاز: {device_id}...")

        def get_info(dev_id): # Pass device_id as argument
            all_info = f"=== معلومات الجهاز: {dev_id} ===\n\n"
            prop_cmd = ["adb", "-s", dev_id, "shell", "getprop"]
            battery_cmd = ["adb", "-s", dev_id, "shell", "dumpsys", "battery"]
            storage_cmd = ["adb", "-s", dev_id, "shell", "df", "-h"]
            timeout_val = 25 # مهلة أطول قليلاً

            # --- getprop ---
            try:
                prop_result = subprocess.run(prop_cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore', timeout=timeout_val)
                properties = {}
                for line in prop_result.stdout.splitlines():
                     match_prop = re.match(r'\[(.*?)\]: \[(.*?)\]', line)
                     if match_prop:
                         key, value = match_prop.groups()
                         properties[key.strip()] = value.strip()

                all_info += f"الشركة المصنعة: {properties.get('ro.product.manufacturer', 'N/A')}\n"
                all_info += f"الموديل: {properties.get('ro.product.model', 'N/A')}\n"
                all_info += f"اسم الجهاز: {properties.get('ro.product.device', 'N/A')}\n"
                all_info += f"الرقم التسلسلي: {properties.get('ro.serialno', properties.get('adb.device.serial', 'N/A'))}\n"
                all_info += f"إصدار الأندرويد: {properties.get('ro.build.version.release', 'N/A')} (API {properties.get('ro.build.version.sdk', 'N/A')})\n"
                all_info += f"المعالج (ABI): {properties.get('ro.product.cpu.abi', 'N/A')}\n\n"
            except subprocess.CalledProcessError as e:
                 error_out = e.stderr or e.stdout or ""
                 if "device offline" in error_out:
                      all_info += "خطأ: الجهاز غير متصل (offline).\n\n"
                 elif "device unauthorized" in error_out:
                      all_info += "خطأ: الجهاز غير مصرح به. يرجى السماح باتصال ADB على الجهاز.\n\n"
                 else:
                      all_info += f"خطأ في جلب getprop: {type(e).__name__} - {e}\n{error_out}\n\n"
            except Exception as e:
                all_info += f"خطأ في جلب getprop: {type(e).__name__} - {e}\n\n"

            # --- Battery ---
            try:
                battery_result = subprocess.run(battery_cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore', timeout=timeout_val)
                battery_info = {}
                current_section = {}
                in_current_section = False
                for line in battery_result.stdout.splitlines():
                    line = line.strip()
                    if line == "Current Battery Service state:":
                         in_current_section = True
                         continue
                    if in_current_section and line:
                         if ":" in line:
                              key_val = line.split(":", 1)
                              if len(key_val) == 2:
                                   battery_info[key_val[0].strip()] = key_val[1].strip()
                         else:
                              in_current_section = False
                    elif not line and in_current_section:
                        in_current_section = False

                all_info += "=== معلومات البطارية ===\n\n"
                all_info += f"نسبة الشحن: {battery_info.get('level', '?')}%\n"
                status_code = battery_info.get('status', '?')
                status_text = {'1': 'غير معروف', '2': 'يشحن', '3': 'لا يشحن', '4': 'غير متصل', '5': 'ممتلئ'}.get(status_code, f'({status_code})')
                all_info += f"الحالة: {status_text}\n"
                plug_code = battery_info.get('plugged', '?')
                plug_text = {'0': 'غير متصل', '1': 'AC', '2': 'USB', '4': 'لاسلكي'}.get(plug_code, f'({plug_code})')
                all_info += f"مصدر الطاقة: {plug_text}\n"
                temp_val = battery_info.get('temperature')
                temp_text = f"{int(temp_val) / 10.0:.1f}°C" if temp_val and temp_val.isdigit() else '?'
                all_info += f"درجة الحرارة: {temp_text}\n"
                volt_val = battery_info.get('voltage')
                volt_text = f"{int(volt_val) / 1000.0:.2f}V" if volt_val and volt_val.isdigit() else '?'
                all_info += f"الجهد: {volt_text}\n"
                health_code = battery_info.get('health', '?')
                health_text = {'1': 'غير معروف', '2': 'جيدة', '3': 'سخونة زائدة', '4': 'تالفة', '5': 'فولتية زائدة', '6': 'فشل غير محدد', '7': 'برودة زائدة'}.get(health_code, f'({health_code})')
                all_info += f"صحة البطارية: {health_text}\n\n"
            except subprocess.CalledProcessError as e:
                 error_out = e.stderr or e.stdout or ""
                 if "device offline" in error_out:
                      all_info += "خطأ: الجهاز غير متصل (offline) أثناء جلب معلومات البطارية.\n\n"
                 elif "device unauthorized" in error_out:
                      all_info += "خطأ: الجهاز غير مصرح به أثناء جلب معلومات البطارية.\n\n"
                 else:
                      all_info += f"خطأ في جلب معلومات البطارية: {type(e).__name__} - {e}\n{error_out}\n\n"
            except Exception as e:
                 all_info += f"خطأ في جلب معلومات البطارية: {type(e).__name__} - {e}\n\n"

            # --- Storage ---
            try:
                 storage_result = subprocess.run(storage_cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore', timeout=timeout_val)
                 all_info += "=== معلومات التخزين (df -h) ===\n\n"
                 cleaned_df = "\n".join(line for line in storage_result.stdout.splitlines() if line.strip())
                 all_info += cleaned_df if cleaned_df else "لا يمكن قراءة معلومات التخزين."

            except subprocess.CalledProcessError as e:
                 error_out = e.stderr or e.stdout or ""
                 if "device offline" in error_out:
                      all_info += "خطأ: الجهاز غير متصل (offline) أثناء جلب معلومات التخزين.\n"
                 elif "device unauthorized" in error_out:
                      all_info += "خطأ: الجهاز غير مصرح به أثناء جلب معلومات التخزين.\n"
                 else:
                      all_info += f"خطأ في جلب معلومات التخزين (df): {type(e).__name__} - {e}\n{error_out}\n"
            except Exception as e:
                 all_info += f"خطأ في جلب معلومات التخزين (df): {type(e).__name__} - {e}\n"

            return all_info
        # --- End of get_info definition ---

        def on_info_success(info_text):
            self.info_display.setPlainText(info_text)
            self.status_bar.showMessage(f"تم عرض معلومات الجهاز {device_id}.", 3000)

        worker = Worker(get_info, device_id)
        worker.task_description = f"get_info_{device_id}"

        worker.started_operation.connect(lambda msg: self.set_ui_busy(True, msg))
        worker.result_ready.connect(on_info_success)
        worker.error_occurred.connect(lambda error_msg: self._handle_adb_error(error_msg, "فشل جلب المعلومات"))
        worker.finished_operation.connect(lambda: self._worker_finished(worker))

        self.active_workers.append(worker)
        worker.start()


    # ***** دالة زر getprop الجديدة *****
    def show_raw_properties(self):
        """عرض الخصائص الأولية للجهاز المحدد (adb shell getprop)."""
        device_id = self._get_selected_device_id()
        if not device_id:
            return

        self.info_display.clear()
        self.info_display.setPlainText(f"جارٍ جلب الخصائص (getprop) للجهاز: {device_id}...")

        command = ["adb", "-s", device_id, "shell", "getprop"]
        task_desc = f"getprop_{device_id}"

        def on_getprop_success(result_stdout):
            # قد يكون الخرج طويلاً جداً، نعرضه كما هو
            self.info_display.setPlainText(result_stdout)
            self.status_bar.showMessage(f"تم عرض الخصائص (getprop) للجهاز {device_id}.", 3000)

        # استخدام مهلة أطول قليلاً لـ getprop
        self.run_adb_command(
            command,
            on_success=on_getprop_success,
            failure_title="فشل جلب الخصائص",
            show_success_popup=False, # لا تظهر نافذة منبثقة
            command_timeout=20, # مهلة أطول لـ getprop
            task_description=task_desc
        )
    # ***** نهاية دالة زر getprop *****


    def send_keyevent(self, keycode):
        """يرسل أمر keyevent للجهاز المحدد."""
        device_id = self._get_selected_device_id()
        if not device_id:
            return

        command = ["adb", "-s", device_id, "shell", "input", "keyevent", keycode]
        success_msg = f"تم إرسال Keyevent {keycode} إلى {device_id}"
        task_desc = f"keyevent_{keycode}_{device_id}"
        self.run_adb_command(
            command,
            success_message=success_msg,
            failure_title=f"فشل إرسال Keyevent {keycode}",
            show_success_popup=False,
            command_timeout=5,
            task_description=task_desc
        )


    # --- دوال إدارة البيانات والتحقق من ADB ---
    def save_data(self, ip_address, port, pairing_code):
        """يحفظ بيانات الجهاز، مع منع تكرار عناوين IP."""
        try:
            existing_ips = set()
            data_lines = []
            file_path = "device_data.txt"
            if os.path.exists(file_path):
                with open(file_path, "r", encoding='utf-8') as file:
                    for line in file:
                        line = line.strip()
                        if not line: continue
                        try:
                            parts = line.split(',', 2)
                            ip = parts[0].strip()
                            if ip and ip not in existing_ips:
                                data_lines.append(line)
                                existing_ips.add(ip)
                            elif ip in existing_ips:
                                pass
                        except IndexError:
                            print(f"Skipping invalid line format in {file_path}: {line}")

            ip_address = ip_address.strip()
            if ip_address and ip_address not in existing_ips:
                port = port.strip()
                pairing_code = pairing_code.strip()
                data_lines.append(f"{ip_address},{port},{pairing_code}")
                existing_ips.add(ip_address)

            with open(file_path, "w", encoding='utf-8') as file:
                for line in data_lines:
                    file.write(line + "\n")

        except Exception as e:
            print(f"تحذير: لم يتم حفظ البيانات تلقائيًا: {e}")


    def load_data(self):
        """تحميل البيانات من الملف وتحديث القوائم المنسدلة."""
        try:
            ip_addresses = []
            ports = set(["5555"])
            pairing_codes = set()
            file_path = "device_data.txt"

            if os.path.exists(file_path):
                with open(file_path, "r", encoding='utf-8') as file:
                    for line in file:
                        line = line.strip()
                        if not line: continue
                        try:
                            parts = line.split(',', 2)
                            ip = parts[0].strip()
                            port = parts[1].strip() if len(parts) > 1 else ""
                            pairing = parts[2].strip() if len(parts) > 2 else ""

                            if ip: ip_addresses.append(ip)
                            if port: ports.add(port)
                            if pairing: pairing_codes.add(pairing)
                        except IndexError:
                             print(f"Skipping invalid line format during load: {line}")

            self.ip_combo.blockSignals(True)
            self.port_combo.blockSignals(True)
            self.pairing_combo.blockSignals(True)

            current_ip = self.ip_combo.currentText()
            current_port = self.port_combo.currentText()
            current_pairing = self.pairing_combo.currentText()

            self.ip_combo.clear()
            seen_ips = set()
            unique_ips_ordered = [ip for ip in ip_addresses if not (ip in seen_ips or seen_ips.add(ip))]
            self.ip_combo.addItems(unique_ips_ordered)
            if current_ip in unique_ips_ordered:
                 self.ip_combo.setCurrentText(current_ip)
            elif unique_ips_ordered:
                 self.ip_combo.setCurrentIndex(0)

            self.port_combo.clear()
            sorted_ports = sorted(list(ports))
            self.port_combo.addItems(sorted_ports)
            if current_port in sorted_ports:
                 self.port_combo.setCurrentText(current_port)
            elif "5555" in sorted_ports:
                 self.port_combo.setCurrentText("5555")
            elif sorted_ports:
                 self.port_combo.setCurrentIndex(0)

            self.pairing_combo.clear()
            sorted_codes = sorted(list(pairing_codes))
            self.pairing_combo.addItems(sorted_codes)
            if current_pairing in sorted_codes:
                 self.pairing_combo.setCurrentText(current_pairing)

            self.ip_combo.blockSignals(False)
            self.port_combo.blockSignals(False)
            self.pairing_combo.blockSignals(False)

        except Exception as e:
            QMessageBox.critical(self, "خطأ تحميل البيانات", f"حدث خطأ أثناء تحميل البيانات: {e}")


    def check_adb_exists(self):
        """التحقق من وجود adb."""
        try:
            subprocess.run(["adb", "--version"], capture_output=True, text=True, check=True, timeout=3)
            return True
        except FileNotFoundError:
            QMessageBox.critical(self, "ADB غير موجود", "لم يتم العثور على 'adb'.\nتأكد من تثبيت Android SDK Platform Tools وإضافة مجلدها إلى PATH.")
            return False
        except subprocess.TimeoutExpired:
             QMessageBox.warning(self, "مهلة ADB", "استغرق أمر 'adb --version' وقتًا طويلاً للرد.")
             return False
        except subprocess.CalledProcessError as e:
             QMessageBox.warning(self, "خطأ ADB", f"أمر ADB أرجع خطأ:\n{e.stderr or e.stdout or 'لا يوجد تفاصيل'}")
             return False
        except Exception as e:
             QMessageBox.critical(self, "خطأ ADB", f"خطأ غير متوقع أثناء التحقق من ADB: {e}")
             return False

    def show_adb_version(self):
        """عرض إصدار ADB."""
        command = ["adb", "--version"]
        try:
             result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore', timeout=5)
             QMessageBox.information(self, "إصدار ADB", result.stdout)
        except Exception as e:
             self._handle_adb_error(f"فشل في الحصول على إصدار ADB: {e}", "خطأ ADB")


    # --- دوال التحديث التلقائي ---
    def toggle_auto_update(self):
        self.auto_update_enabled = not self.auto_update_enabled
        if self.auto_update_enabled:
            self.start_auto_update()
            self.toggle_update_btn.setText("إيقاف التحديث التلقائي")
            self.toggle_update_btn.setIcon(QIcon.fromTheme("media-playback-stop"))
            self.status_bar.showMessage("تم تشغيل التحديث التلقائي.", 3000)
        else:
            self.stop_auto_update()
            self.toggle_update_btn.setText("تشغيل التحديث التلقائي")
            self.toggle_update_btn.setIcon(QIcon.fromTheme("media-playback-start"))


    def start_auto_update(self):
        if not hasattr(self, 'update_timer'):
            self.update_timer = QTimer(self)
            self.update_timer.timeout.connect(self.trigger_update_devices_list)

        if self.auto_update_enabled and not self.update_timer.isActive():
            is_update_running = any(
                w.isRunning() and getattr(w, 'task_description', None) == "adb_devices"
                for w in self.active_workers
            )

            if not is_update_running:
                QTimer.singleShot(0, self.trigger_update_devices_list)
                self.update_timer.start(8000)
                print("Auto-update timer started.")
            else:
                print("Auto-update start skipped: 'adb devices' is already running.")
        elif self.auto_update_enabled and self.update_timer.isActive():
             print("Auto-update timer is already active.")


    def stop_auto_update(self):
        if hasattr(self, 'update_timer') and self.update_timer.isActive():
            self.update_timer.stop()
            self.status_bar.showMessage("تم إيقاف التحديث التلقائي.", 3000)
            print("Auto-update timer stopped.")

    def closeEvent(self, event):
        """ التعامل مع إغلاق النافذة. """
        print("إغلاق التطبيق...")
        self.stop_auto_update()
        print(f"الخيوط النشطة عند الإغلاق: {len(self.active_workers)}")
        event.accept()


if __name__ == "__main__":
    # Enable High DPI scaling - PyQt6 handles this differently, often automatically
    # or via environment variables (QT_ENABLE_HIGHDPI_SCALING=1, QT_SCALE_FACTOR=...).
    # The setAttribute calls below are generally not needed for PyQt6.
    # QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True) # Removed
    # QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)    # Removed

    app = QApplication(sys.argv)
    # app.setStyle('Fusion') # Optional styling
    window = ADBManager()
    window.show()
    sys.exit(app.exec())