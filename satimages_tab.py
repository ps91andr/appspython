
import sys
import socket
import zlib
import json
import time
import subprocess
import os
import logging
import vlc
import time
from PyQt6.QtGui import QIntValidator

from queue import Queue
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor  # ✅ للفحص المتوازي
from PyQt6.QtCore import QSize
# ✅ استيرادات PyQt6 الأساسية
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, pyqtSlot, QSettings, QTimer, QObject
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QPushButton, QLabel, QLineEdit, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QComboBox, QCheckBox, QMenuBar, QMenu, QFileDialog, QSizePolicy,
    QTabWidget, QGroupBox, QDialog, QDialogButtonBox, QFormLayout, QTextBrowser,
    QMessageBox, QInputDialog, QScrollArea, QProgressBar, QListWidget, QFrame   # ✅ أُضيفت QListWidget
)
from PyQt6.QtGui import QIcon, QKeySequence, QAction, QPalette, QColor, QFont
# بقية الكود هنا...

# إعداد نظام تسجيل الأخطاء
logging.basicConfig(filename='starsat_remote.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def build_message(body: str | bytes) -> bytes:
    try:
        body_bytes = body.encode('utf-8') if isinstance(body, str) else body
        length = len(body_bytes)
        header = f"Start{length:07d}End"
        return header.encode('ascii') + body_bytes
    except Exception as e:
        logging.error(f"Error in build_message: {e}")
        return b"Start0000000End"

def generate_handshake() -> bytes:
    xml = ("<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
           "<Command request=\"998\">"
           "<data>PythonQtClient</data>"
           "<uuid>da9c9e4b-64b7-4bf2-8a26-5550d58c42d1-02:00:00:00:00:00</uuid>"
           "</Command>")
    return build_message(xml)

def decompress_zlib(data: bytes) -> str | None:
    try:
        decompressed_data = zlib.decompress(data)
        return decompressed_data.decode('utf-8', errors='replace')
    except zlib.error:
        return None
    except Exception as e:
        logging.error(f"Decompression error: {e}")
        return None

class NetworkThread(QThread):
    connected_signal = pyqtSignal()
    disconnected_signal = pyqtSignal()
    message_signal = pyqtSignal(str)
    data_signal = pyqtSignal(str, str) # نوع البيانات، المحتوى
    channel_data_signal = pyqtSignal(list) # قائمة القنوات المستلمة
    connection_status_signal = pyqtSignal(bool) # True للاتصال, False لقطع الاتصال
    ping_result_signal = pyqtSignal(float) # زمن الاستجابة بالمللي ثانية, -1 للخطأ

    def __init__(self, ip, port):
        super().__init__()
        self.ip, self.port = ip, port
        self.socket, self.running = None, False
        self.received_buffer, self.command_queue = b'', Queue()
        self.expecting_channel_list = False # هل نتوقع قائمة قنوات حاليًا
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5 # عدد محاولات إعادة الاتصال
        self.ping_timer = QTimer()
        self.ping_timer.timeout.connect(self.check_connection_quality)
        self.ping_timer.setInterval(5000) # فحص جودة الاتصال كل 5 ثوانٍ

    def run(self):
        self.running = True
        self.received_buffer = b''
        self.expecting_channel_list = False
        self.connect_to_device()

    def connect_to_device(self):
        try:
            self.message_signal.emit(f"⏳ جارٍ الاتصال بـ {self.ip}:{self.port}...")
            self.socket = socket.create_connection((self.ip, self.port), timeout=10)
            self.socket.settimeout(1.0) # مهلة للقراءة
            self.message_signal.emit("✅ تم الاتصال الأولي")
            self.socket.sendall(generate_handshake())
            self.message_signal.emit("🤝 تم إرسال المصافحة")
            time.sleep(0.1) # إعطاء الجهاز وقتًا للمعالجة

            # أوامر تهيئة إضافية قد يحتاجها الجهاز
            init_cmds = ["16", "20", "22", "24", "15", "12"] # مثال لأوامر طلب معلومات أساسية
            for cmd_req in init_cmds:
                if not self.running: break
                try:
                    cmd_msg_body = f'{{"request":"{cmd_req}"}}'
                    self.socket.sendall(build_message(cmd_msg_body))
                    time.sleep(0.01)
                except Exception as send_err:
                    self.message_signal.emit(f"❌ خطأ إرسال طلب أولي {cmd_req}: {send_err}")
                    self.stop() # إيقاف الخيط إذا فشل الإرسال
                    break

            if not self.running: # إذا تم الإيقاف أثناء التهيئة
                raise ConnectionAbortedError("Stopped during init")

            self.connected_signal.emit() # إرسال إشارة نجاح الاتصال
            self.connection_status_signal.emit(True)
            self.reconnect_attempts = 0 # إعادة تعيين عداد المحاولات عند النجاح
            self.ping_timer.start() # بدء فحص جودة الاتصال
            self.main_loop()

        except Exception as e:
            self.message_signal.emit(f"❌ خطأ في الاتصال: {e}")
            self.handle_connection_error()

    def main_loop(self):
        while self.running:
            # إرسال الأوامر من قائمة الانتظار
            while not self.command_queue.empty():
                if not self.running: break
                cmd_data = self.command_queue.get()

                if isinstance(cmd_data, tuple) and cmd_data[0] == "fetch_channels":
                    self.expecting_channel_list = True
                    cmd_to_send = cmd_data[1] # الأمر الفعلي
                else:
                    cmd_to_send = cmd_data # الأمر هو البيانات مباشرة

                try:
                    self.socket.sendall(cmd_to_send)
                except Exception as send_err:
                    self.message_signal.emit(f"❌ خطأ في إرسال الأمر: {send_err}")
                    self.handle_connection_error()
                    break # الخروج من حلقة إرسال الأوامر
                finally:
                    self.command_queue.task_done()
            if not self.running: break # التحقق مرة أخرى قبل الاستقبال

            # استقبال البيانات
            try:
                data = self.socket.recv(4096)
                if not data: # قطع الاتصال من الطرف الآخر
                    self.message_signal.emit("🔌 قطع الاتصال من الطرف الآخر.")
                    self.handle_connection_error()
                    break
                self.received_buffer += data

                # معالجة المخزن المؤقت للبيانات المستلمة
                processed_something = True # للدخول في الحلقة الداخلية أول مرة
                while processed_something and len(self.received_buffer) > 0 and self.running:
                    processed_something = False # افتراض عدم المعالجة في هذه الدورة
                    original_buffer_len = len(self.received_buffer)

                    # 1. التحقق من رأس GCDH (إذا كان جهازك يستخدمه)
                    if self.received_buffer.startswith(b'GCDH') and len(self.received_buffer) >= 16:
                        # تجاهل رأس GCDH (16 بايت)
                        self.received_buffer = self.received_buffer[16:]
                        processed_something = True
                        continue # العودة لبداية حلقة المعالجة

                    # 2. التحقق من بيانات zlib المضغوطة (تبدأ عادة بـ 0x78 0x9c)
                    elif self.received_buffer.startswith(b'\x78\x9c'): # Zlib header
                        decompressed_string = decompress_zlib(self.received_buffer)
                        if decompressed_string is not None:
                            self.received_buffer = b'' # تم استهلاك المخزن المؤقت
                            processed_something = True
                            is_channel_list_parsed = False
                            try:
                                # محاولة تحليل البيانات المفكوكة كـ JSON
                                parsed_data = json.loads(decompressed_string)
                                # التحقق إذا كانت هذه هي قائمة القنوات المتوقعة
                                if self.expecting_channel_list and isinstance(parsed_data, list) and \
                                   (len(parsed_data) == 0 or (len(parsed_data) > 0 and isinstance(parsed_data[0], dict) and 'ServiceName' in parsed_data[0])):
                                    self.channel_data_signal.emit(parsed_data)
                                    self.expecting_channel_list = False # لم نعد نتوقع قائمة قنوات
                                    is_channel_list_parsed = True
                                elif not is_channel_list_parsed: # إذا لم تكن قائمة قنوات، أرسلها كـ JSON عام
                                    self.data_signal.emit("zlib_json", decompressed_string)
                            except json.JSONDecodeError: # إذا لم تكن JSON صالح
                                if not is_channel_list_parsed: # ولم تكن قائمة قنوات تم تحليلها
                                    self.data_signal.emit("zlib_raw", decompressed_string)
                                # إذا كنا نتوقع قائمة قنوات وفشل التحليل كـ JSON، يجب إعادة تعيين العلامة
                                if self.expecting_channel_list and not is_channel_list_parsed:
                                    self.expecting_channel_list = False # تجنب التعليق في هذا الوضع
                        # إذا فشل فك الضغط (decompressed_string is None)، اترك المخزن كما هو للمحاولة التالية
                        else: pass # لا يمكن فك الضغط، قد تكون البيانات غير كاملة

                    # 3. التحقق من بيانات تبدأ بـ [[ (قد تكون خاصة بالجهاز)
                    elif self.received_buffer.startswith(b'\x5b\x5b'): # '[['
                        self.data_signal.emit("unknown_[[", f"{self.received_buffer[:100]!r}...") # أرسل عينة
                        if len(self.received_buffer) < 500: # إذا كانت صغيرة، افترض أنها كاملة
                           self.received_buffer = b''
                           processed_something = True
                        else: pass # اتركها إذا كانت كبيرة، قد تكون غير كاملة

                    # 4. التحقق من بيانات XML
                    elif self.received_buffer.strip().startswith(b'<?xml'):
                        try:
                            xml_content = self.received_buffer.decode('utf-8', errors='replace')
                            # تحقق بسيط من اكتمال XML (وجود علامة إغلاق في السطر الأخير)
                            if '>' in xml_content.splitlines()[-1]:
                                self.data_signal.emit("xml", xml_content)
                                self.received_buffer = b''
                                processed_something = True
                            else: pass # XML غير مكتمل
                        except Exception: pass # خطأ في فك التشفير أو التحليل

                    # 5. التحقق من بيانات JSON غير مضغوطة
                    elif self.received_buffer.strip().startswith(b'{') or \
                         self.received_buffer.strip().startswith(b'['):
                        try:
                            json_str = self.received_buffer.decode('utf-8', errors='replace').strip()
                            # تحقق بسيط من اكتمال JSON
                            if (json_str.startswith('{') and json_str.endswith('}')) or \
                               (json_str.startswith('[') and json_str.endswith(']')):
                                json.loads(json_str) # محاولة التحليل للتحقق من الصحة
                                self.data_signal.emit("json", json_str)
                                self.received_buffer = b''
                                processed_something = True
                            else: pass # JSON غير مكتمل
                        except Exception: pass # خطأ في فك التشفير أو التحليل

                    # إذا لم تتم معالجة أي شيء ولم يتغير طول المخزن، اخرج من الحلقة الداخلية
                    if not processed_something and len(self.received_buffer) == original_buffer_len:
                        break

            except socket.timeout:
                pass # مهلة القراءة طبيعية إذا لم يكن هناك بيانات
            except socket.error as e:
                self.message_signal.emit(f"❌ خطأ في استقبال البيانات: {e}")
                self.handle_connection_error()
                break # الخروج من حلقة الاستقبال الرئيسية
            except Exception as e:
                self.message_signal.emit(f"❌ خطأ غير متوقع في الاستقبال: {e}")
                logging.error(f"Unexpected receive error: {e} - Buffer: {self.received_buffer[:200]!r}")
                self.handle_connection_error() # محاولة معالجة الخطأ
                break

            time.sleep(0.05) # استراحة قصيرة لمنع استهلاك وحدة المعالجة المركزية

    # def handle_connection_error(self):
        # self.connection_status_signal.emit(False)
        # self.ping_timer.stop()
        # if self.socket:
            # try: self.socket.close()
            # except Exception: pass
        # self.socket = None
        # self.disconnected_signal.emit() # إرسال إشارة قطع الاتصال

        # # محاولة إعادة الاتصال التلقائي
        # if self.running and self.reconnect_attempts < self.max_reconnect_attempts:
            # self.reconnect_attempts += 1
            # self.message_signal.emit(f"♻️ محاولة إعادة الاتصال ({self.reconnect_attempts}/{self.max_reconnect_attempts})...")
            # time.sleep(5 * self.reconnect_attempts) # زيادة وقت الانتظار مع كل محاولة
            # if self.running: # تحقق مرة أخرى قبل المحاولة
                # self.connect_to_device()
        # elif self.running: # إذا تم تجاوز عدد المحاولات
            # self.message_signal.emit("🚫 فشلت جميع محاولات إعادة الاتصال.")
            # self.running = False # إيقاف الخيط نهائيًا
    def handle_connection_error(self):
        self.connection_status_signal.emit(False)
        self.ping_timer.stop()
        if self.socket:
            try: self.socket.close()
            except Exception: pass
        self.socket = None
        self.disconnected_signal.emit()
        
        # تحقق من إعدادات إعادة الاتصال التلقائي
        if hasattr(QApplication.instance(), 'auto_reconnect') and not QApplication.instance().auto_reconnect:
            self.message_signal.emit("🚫 إعادة الاتصال التلقائي معطلة.")
            self.running = False
            return
            
        # محاولة إعادة الاتصال التلقائي
        if self.running and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            self.message_signal.emit(f"♻️ محاولة إعادة الاتصال ({self.reconnect_attempts}/{self.max_reconnect_attempts})...")
            time.sleep(5 * self.reconnect_attempts)
            if self.running:
                self.connect_to_device()
        elif self.running:
            self.message_signal.emit("🚫 فشلت جميع محاولات إعادة الاتصال.")
            self.running = False
    def check_connection_quality(self):
        if not self.running or not self.socket:
            return

        try:
            start_time = time.time()
            cmd_msg_body = '{"request":"12"}' # أمر بسيط للتحقق
            self.socket.sendall(build_message(cmd_msg_body))
            self.socket.settimeout(2.0) # مهلة قصيرة للـ ping
            # لا نتوقع بالضرورة استجابة محددة، مجرد نجاح الإرسال والاستقبال البسيط
            _ = self.socket.recv(16) # محاولة قراءة أي شيء صغير كإقرار
            self.socket.settimeout(1.0) # إعادة المهلة الافتراضية
            latency = (time.time() - start_time) * 1000
            self.ping_result_signal.emit(latency)
        except socket.timeout: # هذا طبيعي إذا كان الأمر لا يرسل إقرارًا فوريًا
            latency = (time.time() - start_time) * 1000 # قياس وقت الإرسال على الأقل
            self.ping_result_signal.emit(latency) # إرسال زمن الوصول حتى لو كان هناك مهلة قراءة
        except Exception: # أي خطأ آخر يعني فشل الـ ping
            self.ping_result_signal.emit(-1)

    def send_command(self, command_data: bytes | tuple):
        if self.running:
            self.command_queue.put(command_data)
        else:
            self.message_signal.emit("⚠️ لا يمكن الإرسال، الخيط متوقف.")

    def stop(self):
        self.running = False
        self.ping_timer.stop() # إيقاف مؤقت الـ ping
        # مسح قائمة الأوامر المعلقة لتجنب محاولة الإرسال بعد الإيقاف
        while not self.command_queue.empty():
            try:
                self.command_queue.get_nowait()
                self.command_queue.task_done()
            except:
                break
        if self.socket:
            try: self.socket.close()
            except Exception: pass
        self.message_signal.emit("🛑 تم إيقاف خيط الشبكة.")

class ScannerWorker(QObject):
    result_ready = pyqtSignal(list)

    def run_scan(self):
        def get_ip():
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()

            return ip

        def scan(ip):
            try:
                s = socket.socket()
                s.settimeout(0.1)
                return ip if s.connect_ex((ip, 20000)) == 0 else None
            except:
                return None

        base = ".".join(get_ip().split(".")[:3])
        with ThreadPoolExecutor(100) as e:
            futures = e.map(scan, [f"{base}.{i}" for i in range(1, 255)])
            active_hosts = list(filter(None, futures))
        self.result_ready.emit(active_hosts)

class ScannerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("فحص الأجهزة على الشبكة")
        self.resize(300, 300)

        self.label = QLabel("الأجهزة المكتشفة:")
        self.list_widget = QListWidget()
        self.button = QPushButton("ابدأ الفحص")
        self.button.clicked.connect(self.start_scan)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.button)

        self.list_widget.itemDoubleClicked.connect(self.select_device)

    def start_scan(self):
        self.list_widget.clear()
        self.list_widget.addItem("جاري الفحص...")
        self.thread = QThread()
        self.worker = ScannerWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run_scan)
        self.worker.result_ready.connect(self.show_results)
        self.worker.result_ready.connect(self.thread.quit)
        self.worker.result_ready.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def show_results(self, results):
        self.list_widget.clear()
        if results:
            self.list_widget.addItems(results)
        else:
            self.list_widget.addItem("لا يوجد أجهزة")

    def select_device(self, item):
        if self.parent():
            self.parent().ip_input.setText(item.text())
        self.accept()

class SettingsManager:
    def __init__(self):
        self.settings = QSettings("StarsatRemote", "StarsatRemoteApp")

    def validate_settings(self):
        """التحقق من صحة بيانات الإعدادات"""
        try:
            if not self.settings.contains("device_ip") or \
               not self.settings.contains("device_port"):
                return False

            devices = self.settings.value("connected_devices", [])
            if not isinstance(devices, list): return False

            for device_entry in devices:
                if not isinstance(device_entry, dict):
                    if isinstance(device_entry, str):
                        try:
                            device_dict_check = json.loads(device_entry)
                            if not isinstance(device_dict_check, dict): return False
                            if not ('name' in device_dict_check and \
                                    'ip' in device_dict_check and \
                                    'port' in device_dict_check):
                                return False
                        except json.JSONDecodeError:
                            return False
                    else:
                        return False
                else:
                    if not ('name' in device_entry and \
                            'ip' in device_entry and \
                            'port' in device_entry):
                        return False
            return True
        except Exception as e:
            logging.error(f"Error validating settings: {e}")
            return False

    def repair_settings(self):
        """إصلاح الإعدادات التالفة"""
        default_settings = {
            "device_ip": "192.168.1.100",
            "device_port": "20000",
            "connected_devices": [
                {
                    "name": "جهاز افتراضي",
                    "ip": "192.168.1.100",
                    "port": "20000"
                }
            ],
            "dark_mode": False,
            "font_size": 9,
            "vlc_path": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            "record_path": os.path.expanduser("~/Videos"),
            "channels": "[]",
            "favorites": "[]"
        }

        for key, value in default_settings.items():
            self.settings.setValue(key, value)

        self.settings.sync()
        logging.info("تم استعادة الإعدادات الافتراضية بسبب بيانات تالفة")

    def backup_settings(self, backup_path):
        try:
            backup_data = {}
            for key in self.settings.allKeys():
                backup_data[key] = self.settings.value(key)

            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=4)

            logging.info(f"تم إنشاء نسخة احتياطية في: {backup_path}")
            return True
        except Exception as e:
            logging.error(f"فشل في إنشاء النسخة الاحتياطية: {e}")
            return False

    def restore_settings(self, backup_path):
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            self.settings.clear()
            for key, value in backup_data.items():
                self.settings.setValue(key, value)

            self.settings.sync()
            logging.info(f"تم استعادة الإعدادات من: {backup_path}")
            return True
        except Exception as e:
            logging.error(f"فشل في استعادة النسخة الاحتياطية: {e}")
            return False

    def save_window_state(self, window):
        self.settings.setValue("window_geometry", window.saveGeometry())
        self.settings.setValue("window_state", window.saveState())
        self.settings.setValue("dark_mode", window.dark_mode)
        self.settings.setValue("font_size", window.current_font_size)

    def restore_window_state(self, window):
        geometry = self.settings.value("window_geometry")
        if geometry:
            window.restoreGeometry(geometry)
        state = self.settings.value("window_state")
        if state:
            window.restoreState(state)
        window.dark_mode = self.settings.value("dark_mode", False, type=bool)
        window.current_font_size = self.settings.value("font_size", 9, type=int)

    def save_device_settings(self, ip, port):
        self.settings.setValue("device_ip", ip)
        self.settings.setValue("device_port", port)

    def load_device_settings(self):
        return (
            self.settings.value("device_ip", "192.168.1.100"),
            self.settings.value("device_port", "20000", type=str)
        )

    def save_channels(self, channels):
        try:
            self.settings.setValue("channels", json.dumps(channels))
        except TypeError as e:
            logging.error(f"خطأ في حفظ القنوات: {e}")
            self.settings.setValue("channels", "[]")

    def load_channels(self):
        channels_json = self.settings.value("channels", "[]")

        if isinstance(channels_json, list):
            return channels_json

        try:
            return json.loads(channels_json)
        except json.JSONDecodeError:
            logging.error("فشل تحميل القنوات، سيتم إرجاع قائمة فارغة.")
            return []

    def save_favorites(self, favorites):
        self.settings.setValue("favorites", json.dumps(favorites))

    def load_favorites(self):
        favorites_json = self.settings.value("favorites", "[]")
        try:
            return json.loads(favorites_json)
        except json.JSONDecodeError:
            logging.error("Failed to load favorites, returning empty list.")
            return []

    def get_connected_devices(self):
        devices_setting = self.settings.value("connected_devices", [])
        result = []

        if not isinstance(devices_setting, list):
            logging.warning("connected_devices setting is not a list. Resetting.")
            return []

        for device_entry in devices_setting:
            if isinstance(device_entry, dict):
                result.append(device_entry)
            elif isinstance(device_entry, str):
                try:
                    device_dict = json.loads(device_entry)
                    if isinstance(device_dict, dict):
                        result.append(device_dict)
                except json.JSONDecodeError:
                    logging.warning(f"Could not parse device entry string: {device_entry}")
                    continue
        return result

class StarsatRemote(QMainWindow):
    DIGIT_COMMAND_MAP = { # Key codes for digits 0-9
        "0": "12", "1": "13", "2": "14", "3": "15", "4": "16",
        "5": "17", "6": "18", "7": "19", "8": "20", "9": "21"
    }
    def open_scanner_dialog(self):
        dialog = ScannerDialog(self)
        dialog.exec()
    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()

        self.dark_mode = False
        self.current_font_size = 9
        self.favorite_groups = []
        self.favorites = []
        self.channels = [] # القائمة الداخلية لبيانات القنوات
        self.connected_devices = []
        self.current_device_index = -1
        self.embedded_instance = None  # ← تمت إضافته هنا
        self.embedded_player = None
        self.is_muted = False  # حالة كتم الصوت
        self.auto_reconnect = True  # إضافة هذا المتغير

        self.network_thread = None
        self.is_fetching_all = False # لجلب جميع القنوات
        self.current_fetch_from = 0
        self.batch_size = 25
        self.connected = False
        self.is_expanded = False
        # متغيرات جديدة لتحديث روابط البث لجميع القنوات
        self.is_updating_all_urls = False
        self.current_url_update_index = 0
        self.url_update_timer = QTimer(self)
        self.url_update_timer.timeout.connect(self.process_next_url_update)
        self.url_update_delay = 10 # تأخير بالمللي ثانية بين كل طلب تحديث رابط
        self.last_requested_service_id_for_url = None # لتتبع القناة التي طلب رابطها مؤخراً
        self.dark_mode = self.settings_manager.settings.value("dark_mode", False, type=bool)

        self.init_ui()
        self.settings_manager.restore_window_state(self)
        self.load_device_settings()
        self.apply_ui_settings()

    def init_ui(self):
        self.setWindowTitle("برنامج تحكم ستارسات مع قائمة القنوات و VLC")
        self.setGeometry(100, 100, 1000, 700) # تعديل الحجم
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.create_menu_bar()

        self.status_bar = self.statusBar()
        # إنشاء العلامات الجديدة
        self.connection_status_label = QLabel("غير متصل")
        self.ping_status_label = QLabel("زمن الاستجابة: -")
        self.channel_count_label = QLabel("إجمالي القنوات: 0") # ✨ سطر جديد: إضافة تسمية لعدد القنوات
# ✨ أضف هذين السطرين لإنشاء التسميات الجديدة
        self.favorite_count_label = QLabel("المفضلة: 0")
        self.device_count_label = QLabel("الأجهزة المحفوظة: 0")
        # ✨ أضف هذا السطر لإنشاء تسمية معلومات الجهاز
        self.device_info_status_label = QLabel("معلومات الجهاز: --")
        
        # ✨ أضف هذا السطر لإضافة التسمية الجديدة إلى شريط الحالة
        self.status_bar.addPermanentWidget(self.device_info_status_label)
                        
        self.status_bar.addPermanentWidget(self.connection_status_label)
        self.status_bar.addPermanentWidget(self.ping_status_label)
        self.status_bar.addPermanentWidget(self.channel_count_label) # ✨ سطر جديد: إضافة التسمية إلى شريط الحالة
        # ✨ أضف هذين السطرين لإضافة التسميات الجديدة إلى شريط الحالة
        self.status_bar.addPermanentWidget(self.favorite_count_label)
        self.status_bar.addPermanentWidget(self.device_count_label)

        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.main_layout = QVBoxLayout(self.central)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self.remote_tab = QWidget()
        self.tabs.addTab(self.remote_tab, "الريموت")
        self.init_remote_tab()

        self.channels_tab = QWidget()
        self.tabs.addTab(self.channels_tab, "القنوات")
        self.init_channels_tab() # سيتم إضافة الزر الجديد هنا

        self.settings_tab = QWidget()
        self.tabs.addTab(self.settings_tab, "الإعدادات")
        self.init_settings_tab()
      

    def create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("ملف")

        fullscreen_action = QAction("ملء الشاشة", self)
        fullscreen_action.setShortcut(QKeySequence("F11"))
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        file_menu.addAction(fullscreen_action)

        exit_action = QAction("خروج", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("عرض")
        # في دالة create_menu_bar، أضف هذا بعد إنشاء view_menu:
        dark_mode_action = QAction("الوضع الداكن", self)
        dark_mode_action.setCheckable(True)
        dark_mode_action.setChecked(self.dark_mode)
        dark_mode_action.triggered.connect(lambda checked: self.set_dark_mode(checked))
        view_menu.addAction(dark_mode_action)
        font_menu = view_menu.addMenu("حجم الخط")
        sizes = {"صغير (8pt)": 8, "متوسط (10pt)": 10, "كبير (12pt)": 12}
        for text, size in sizes.items():
            action = QAction(text, self)
            action.triggered.connect(lambda checked=False, s=size: self.change_font_size(s))
            font_menu.addAction(action)

        tools_menu = menubar.addMenu("أدوات")

        backup_action = QAction("نسخ احتياطي للإعدادات", self)
        backup_action.triggered.connect(self.backup_settings)
        tools_menu.addAction(backup_action)

        restore_action = QAction("استعادة الإعدادات", self)
        restore_action.triggered.connect(self.restore_settings)
        tools_menu.addAction(restore_action)

        reset_action = QAction("استعادة الإعدادات الافتراضية", self)
        reset_action.triggered.connect(self.reset_settings)
        tools_menu.addAction(reset_action)

        help_menu = menubar.addMenu("مساعدة")

        about_action = QAction("حول البرنامج", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        help_action = QAction("مساعدة", self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

    def init_remote_tab(self):
        layout = QVBoxLayout(self.remote_tab)

        conn_group = QGroupBox("إعدادات الاتصال")
        conn_layout = QGridLayout(conn_group)

        conn_layout.addWidget(QLabel("عنوان الآي بي:"), 0, 0)
        self.ip_input = QLineEdit()
        conn_layout.addWidget(self.ip_input, 0, 1)

        conn_layout.addWidget(QLabel("رقم المنفذ:"), 1, 0)
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("مثال: 20000")
        conn_layout.addWidget(self.port_input, 1, 1)

        self.connect_btn = QPushButton("اتصال 🔌")
        self.connect_btn.clicked.connect(self.connect_to_device)
        conn_layout.addWidget(self.connect_btn, 0, 2)

        self.fetch_channels_checkbox = QCheckBox("جلب القنوات بعد الاتصال")
        conn_layout.addWidget(self.fetch_channels_checkbox, 0, 3)
        
        self.disconnect_btn = QPushButton("إلغاء الاتصال 🔗")
        self.disconnect_btn.clicked.connect(self.disconnect_from_device)
        self.disconnect_btn.setEnabled(False)
        if hasattr(self, 'fetch_and_update_btn'):
            self.fetch_and_update_btn.setEnabled(False)
        conn_layout.addWidget(self.disconnect_btn, 1, 2)

        self.device_selector = QComboBox()
        self.device_selector.currentIndexChanged.connect(self.device_selected)
        conn_layout.addWidget(self.device_selector, 2, 0, 1, 3)

        self.add_device_btn = QPushButton("إضافة جهاز")
        self.add_device_btn.clicked.connect(self.add_device)
        conn_layout.addWidget(self.add_device_btn, 3, 0)

        self.remove_device_btn = QPushButton("حذف جهاز")
        self.remove_device_btn.clicked.connect(self.remove_device)
        conn_layout.addWidget(self.remove_device_btn, 3, 1)

   
    # إضافة هذا بعد الأزرار الموجودة
        self.auto_reconnect_checkbox = QCheckBox("إعادة الاتصال التلقائي")
        self.auto_reconnect_checkbox.setChecked(True)
        self.auto_reconnect_checkbox.stateChanged.connect(self.toggle_auto_reconnect)
        conn_layout.addWidget(self.auto_reconnect_checkbox, 3, 3)  # ضعه في الصف 3، العمود 3

        self.scan_devices_btn = QPushButton("🔍 فحص الشبكة")
        self.scan_devices_btn.clicked.connect(self.open_scanner_dialog)
        conn_layout.addWidget(self.scan_devices_btn, 1, 3)  # بجانب زر الاتصال مثلاً
        
        layout.addWidget(conn_group)

        remote_group = QGroupBox("أزرار التحكم")
        remote_layout = QVBoxLayout(remote_group)

        self.mode_selector = QComboBox()
        self.mode_selector.addItem("الوضع العادي")
        remote_layout.addWidget(self.mode_selector)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.remote_grid = QGridLayout(scroll_content)

        self.add_remote_buttons()

        scroll.setWidget(scroll_content)
        remote_layout.addWidget(scroll)

        digit_group = QWidget()
        digit_layout = QHBoxLayout(digit_group)

        digit_layout.addWidget(QLabel("إرسال رقم قناة:"))
        self.digit_input = QLineEdit()
        self.digit_input.setPlaceholderText("مثال: 123")
        self.digit_input.setMaximumWidth(100)
        self.digit_input.setEnabled(False)
        digit_layout.addWidget(self.digit_input)

        self.go_button = QPushButton("Go")
        self.go_button.setEnabled(False)
        self.go_button.clicked.connect(self.handle_go_button_click)
        digit_layout.addWidget(self.go_button)

        remote_layout.addWidget(digit_group)
        layout.addWidget(remote_group)
      
        # إنشاء مجموعة إدخال الأمر المباشر
        direct_cmd_group = QWidget()
        direct_cmd_layout = QHBoxLayout(direct_cmd_group)
        direct_cmd_layout.addWidget(QLabel("إرسال كود أمر مباشر:"))
        
        # حقل إدخال الأمر المباشر
        self.direct_cmd_input = QLineEdit()
        self.direct_cmd_input.setPlaceholderText("مثال: 23 لكتم الصوت")
        validator = QIntValidator(0, 9999)  # يسمح بأكواد من 0 إلى 9999
        self.direct_cmd_input.setValidator(validator)
        self.direct_cmd_input.setMaximumWidth(150)
        direct_cmd_layout.addWidget(self.direct_cmd_input)
        
        # زر إرسال الأمر المباشر
        self.send_direct_cmd_btn = QPushButton("إرسال")
        self.send_direct_cmd_btn.clicked.connect(self.handle_send_direct_command)
        direct_cmd_layout.addWidget(self.send_direct_cmd_btn)
        direct_cmd_layout.addStretch()  # إضافة مسافة
        
        layout.addWidget(direct_cmd_group)


        custom_group = QGroupBox("أوامر مخصصة (JSON)")
        custom_layout = QVBoxLayout(custom_group)

        self.custom_cmd_input = QLineEdit()
        self.custom_cmd_input.setPlaceholderText('{"request":"1009", "ProgramId":"123"}')
        custom_layout.addWidget(self.custom_cmd_input)

        self.send_custom_btn = QPushButton("إرسال أمر مخصص")
        self.send_custom_btn.clicked.connect(self.send_custom_command)
        custom_layout.addWidget(self.send_custom_btn)

        layout.addWidget(custom_group)

        log_group = QGroupBox("سجل الأحداث")
        log_layout = QVBoxLayout(log_group)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumHeight(150)
        log_layout.addWidget(self.output)

        layout.addWidget(log_group)

    def init_channels_tab(self):
        layout = QVBoxLayout(self.channels_tab)

        controls_group = QGroupBox("تحكم القنوات")
        controls_layout_grid = QGridLayout(controls_group) # استخدام QGridLayout لتنظيم أفضل

        self.fetch_channels_btn = QPushButton(f"جلب أول {self.batch_size} قناة 📺تجريبي")
        self.fetch_channels_btn.clicked.connect(self.fetch_channel_list)
        self.fetch_channels_btn.setEnabled(False)
        controls_layout_grid.addWidget(self.fetch_channels_btn, 0, 0)

        self.fetch_all_btn = QPushButton("جلب جميع القنوات")
        self.fetch_all_btn.clicked.connect(self.start_fetching_all)
        self.fetch_all_btn.setEnabled(False)
        controls_layout_grid.addWidget(self.fetch_all_btn, 0, 1)

        # الزر الجديد لتحديث جميع الروابط
        self.update_all_urls_btn = QPushButton("تحديث روابط البث للكل 🔄")
        self.update_all_urls_btn.clicked.connect(self.start_updating_all_urls)
        self.update_all_urls_btn.setEnabled(False) # يتم تفعيله عند الاتصال ووجود قنوات
        controls_layout_grid.addWidget(self.update_all_urls_btn, 0, 2)


        # زر دمج الجلب والتحديث
        self.fetch_and_update_btn = QPushButton("جلب + تحديث القنوات 🔁")
        self.fetch_and_update_btn.setShortcut(QKeySequence("Ctrl+J"))
        self.fetch_and_update_btn.clicked.connect(self.fetch_and_update_all)
        if hasattr(self, 'fetch_and_update_btn'):
            self.fetch_and_update_btn.setEnabled(True)
        controls_layout_grid.addWidget(self.fetch_and_update_btn, 0, 3)

        btn_style = """
        QPushButton {
            background-color: #3498db;
            color: white;
            font-family: 'Calibri';
            font-size: 14px;
            font-weight: bold;
            padding: 6px;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        """
        self.fetch_and_update_btn.setStyleSheet(btn_style)
        
        self.stop_fetch_btn = QPushButton("إيقاف التحميل")
        self.stop_fetch_btn.clicked.connect(self.stop_fetching_all) # يشمل إيقاف تحديث الروابط أيضاً
        self.stop_fetch_btn.setEnabled(False)
        controls_layout_grid.addWidget(self.stop_fetch_btn, 0, 4)


        self.clear_table_btn = QPushButton("مسح الجدول 🗑️")
        self.clear_table_btn.clicked.connect(self.clear_channel_table)
        controls_layout_grid.addWidget(self.clear_table_btn, 0, 5)

        self.goto_channel_btn = QPushButton("تحديث الرابط للقناة المحددة ▶️")
        self.goto_channel_btn.clicked.connect(self.go_to_selected_channel)
        self.goto_channel_btn.setEnabled(False)
        controls_layout_grid.addWidget(self.goto_channel_btn, 1, 0)

        self.open_channel_btn = QPushButton("فتح القناة المحددة🚀")
        self.open_channel_btn.clicked.connect(self.channel_selected_action)
        self.open_channel_btn.setEnabled(True)
        controls_layout_grid.addWidget(self.open_channel_btn,1, 1)
        # self.fetch_tv_btn = QPushButton("📺 جلب قنوات التلفاز فقط")


        self.show_playing_btn = QPushButton("عرض القنوات قيد التشغيل 🎥")
        self.show_playing_btn.clicked.connect(self.show_playing_channels)
        controls_layout_grid.addWidget(self.show_playing_btn, 1, 2)


        self.play_vlc_btn = QPushButton("تشغيل VLC 🎬")
        self.play_vlc_btn.clicked.connect(self.play_selected_in_vlc)
        self.play_vlc_btn.setEnabled(False)
        controls_layout_grid.addWidget(self.play_vlc_btn, 1, 3)

        # مكان جديد للتسجيل
        self.record_btn = QPushButton("تسجيل ⏺️")
        self.record_btn.clicked.connect(self.record_channel)
        self.record_btn.setEnabled(False)
        controls_layout_grid.addWidget(self.record_btn, 0, 8)

        # self.recordM_btn = QPushButton("تسجيل recordMP4_channel⏺️")
        # self.recordM_btn.clicked.connect(self.recordMP4_channel)
        # self.recordM_btn.setEnabled(True)
        # controls_layout_grid.addWidget(self.recordM_btn, 1, 5)

        self.recordMT_btn = QPushButton("تسجيل recordMP4TS_channel⏺️")
        self.recordMT_btn.clicked.connect(self.recordMP4TS_channel)
        self.recordMT_btn.setEnabled(True)
        controls_layout_grid.addWidget(self.recordMT_btn, 0, 9)                
        
        self.play_embedded_btn = QPushButton("تشغيل المدمج ▶")
        self.play_embedded_btn.clicked.connect(self.play_selected_embedded)
        self.play_embedded_btn.setEnabled(True)
        controls_layout_grid.addWidget(self.play_embedded_btn, 0, 6)


        self.stop_embedded_btn = QPushButton("إيقاف المدمج ⏹️")
        self.stop_embedded_btn.clicked.connect(self.stop_embedded_player)
        self.stop_embedded_btn.setEnabled(True)
        controls_layout_grid.addWidget(self.stop_embedded_btn, 0, 7)

    # أزرار حفظ واستعادة القنوات
        self.save_channels_btn = QPushButton("حفظ القنوات 💾")
        self.save_channels_btn.clicked.connect(self.save_channels_to_file)
        controls_layout_grid.addWidget(self.save_channels_btn, 1, 8)

        self.load_channels_btn = QPushButton("استعادة القنوات 📂")
        self.load_channels_btn.clicked.connect(self.load_channels_from_file)
        controls_layout_grid.addWidget(self.load_channels_btn,1, 9)

        # --- بداية الكود الجديد ---
        self.delete_selected_btn = QPushButton("حذف المحدد 🗑️")
        self.delete_selected_btn.clicked.connect(self.handle_delete_selected_channels)
        controls_layout_grid.addWidget(self.delete_selected_btn,1, 4)
        # --- نهاية الكود الجديد ---
        # ==========================================================
        # ======= 🎯 أضف هذا الكود داخل دالة init_channels_tab =======
        # ==========================================================
        
        # (ابحث عن مكان إضافة الأزرار الأخرى في controls_layout_grid)
        
        # --- بداية الكود الجديد ---
        self.move_selected_btn = QPushButton("نقل المحدد ↕️")
        self.move_selected_btn.clicked.connect(self.handle_move_selected_channels)
        # يمكنك وضعه في أي مكان فارغ بالشبكة، مثلاً في الصف 2، العمود 7
        controls_layout_grid.addWidget(self.move_selected_btn, 1,5)
        # --- نهاية الكود الجديد ---

        # ✨ --- بداية الكود الجديد ---
        # إضافة إعدادات حجم الدفعة إلى تبويب القنوات
        # التسمية
        # التسمية
        batch_label = QLabel("عدد القنوات في كل دفعة:")
        batch_label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        batch_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        batch_label.setStyleSheet("""
            QLabel {
                background-color: #1abc9c;
                color: black;
                font-family: 'Calibri';
                font-size: 14px;
                font-weight: bold;
                padding: 6px 10px;
                border-radius: 6px;
            }
        """)
        
        # حقل الإدخال
        self.batch_size_input = QLineEdit()
        self.batch_size_input.setPlaceholderText("مثال: 250")
        self.batch_size_input.setText(str(self.batch_size))
        self.batch_size_input.setFixedWidth(110)
        self.batch_size_input.editingFinished.connect(self.save_batch_size_setting)
        
        self.batch_size_input.setStyleSheet("""
            QLineEdit {
                background-color: #f5f7fa;
                color: #2c3e50;
                border: 2px solid #dcdde1;
                border-radius: 6px;
                padding: 6px 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #2980b9;
                background-color: #ffffff;
            }
        """)
        controls_layout_grid.addWidget(batch_label, 1,6)
        controls_layout_grid.addWidget(self.batch_size_input, 1, 7)        
        # ✨ --- نهاية الكود الجديد ---                                
                                                                
                                                                                                                                
        # إنشاء إطار للأزرار
        buttons_frame = QFrame()
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(0, 0, 0, 0)  # إزالة الهوامش
        
        # إعداد أزرار التحكم بالمشغل المدمج
        self.toggle_embedded_btn = QPushButton("إظهار المشغل المدمج")
        self.toggle_embedded_btn.clicked.connect(self.toggle_embedded_frame)
        
        self.expand_embedded_btn = QPushButton("تكبير/تصغير")
        self.expand_embedded_btn.clicked.connect(self.expand_embedded_player)
        
        self.mute_btn = QPushButton("كتم الصوت 🔇")
        self.mute_btn.clicked.connect(self.toggle_mute)
        
        # إضافة الأزرار إلى التخطيط الأفقي
        buttons_layout.addWidget(self.toggle_embedded_btn)
        buttons_layout.addWidget(self.expand_embedded_btn)
        buttons_layout.addWidget(self.mute_btn)
        
        # إضافة الإطار والأزرار إلى التخطيط الرئيسي
        self.embedded_frame = QFrame()
        self.embedded_frame.setMinimumHeight(300)
        self.embedded_frame.setStyleSheet("background-color: black;")
        self.embedded_frame.hide()  # إخفاء الإطار عند البدء
        layout.addWidget(self.embedded_frame)
        layout.addWidget(buttons_frame)  # إضافة إطار الأزرار بعد إطار المشغل




        button_style = """
        QPushButton {
            background-color: #1abc9c;
            color: black;
            font-family: 'Calibri';
            font-size: 14px;
            font-weight: bold;
            padding: 6px 10px;
            border-radius: 6px;
        }
        QPushButton:hover {
            background-color: #16a085;
        }
        """
        buttons_to_style = [
            self.fetch_channels_btn,
            self.fetch_all_btn,
            self.update_all_urls_btn,
            self.fetch_and_update_btn,
            self.stop_fetch_btn,
            self.clear_table_btn,
            self.goto_channel_btn,
            self.open_channel_btn,
            self.show_playing_btn,
            self.play_vlc_btn,
            self.record_btn,
            self.recordMT_btn,
            self.toggle_embedded_btn,
            self.stop_embedded_btn,
            self.play_embedded_btn,
            self.delete_selected_btn,
            self.move_selected_btn
        ]
        
        for btn in buttons_to_style:
            btn.setStyleSheet(button_style)



        btn_style = """
        QPushButton {
            background-color: #3498db;
            color: white;
            font-family: 'Calibri';
            font-size: 14px;
            font-weight: bold;
            padding: 6px;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        """
        self.fetch_and_update_btn.setStyleSheet(btn_style)

        layout.addWidget(controls_group)
        # في دالة init_channels_tab بعد إنشاء الأزرار
        btn_style = """
        QPushButton {
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
            padding: 5px;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        """

        self.save_channels_btn.setStyleSheet(btn_style)
        self.load_channels_btn.setStyleSheet(btn_style)

        export_group = QGroupBox("خيارات التصدير")
        export_layout = QHBoxLayout(export_group)

        self.export_excel_btn = QPushButton("Excel", self)
        self.export_excel_btn.setIcon(QIcon.fromTheme("x-office-spreadsheet"))
        self.export_excel_btn.clicked.connect(self.export_to_excel)

        self.export_csv_btn = QPushButton("CSV", self)
        self.export_csv_btn.setIcon(QIcon.fromTheme("text-csv"))
        self.export_csv_btn.clicked.connect(self.export_to_csv)

        self.export_json_btn = QPushButton("JSON", self)
        self.export_json_btn.setIcon(QIcon.fromTheme("text-x-json"))
        self.export_json_btn.clicked.connect(self.export_to_json)

        self.export_html_btn = QPushButton("HTML", self)
        self.export_html_btn.setIcon(QIcon.fromTheme("text-html"))
        self.export_html_btn.clicked.connect(self.export_to_html)
        
        self.export_m3u_btn = QPushButton("M3U > IPTV", self)
        self.export_m3u_btn.setIcon(QIcon.fromTheme("text-x-m3u"))
        self.export_m3u_btn.clicked.connect(self.export_to_m3u)

        export_layout.addWidget(self.export_m3u_btn)
        export_layout.addWidget(self.export_excel_btn)
        export_layout.addWidget(self.export_csv_btn)
        export_layout.addWidget(self.export_json_btn)
        export_layout.addWidget(self.export_html_btn)
        
        button_style = """
        QPushButton {
            background-color: #63E0F5;
            color: black;
            font-family: 'Calibri';
            font-size: 14px;
            font-weight: bold;
            padding: 6px 10px;
            border-radius: 6px;
        }
        QPushButton:hover {
            background-color: #16a085;
        }
        """
        
        # ✅ تأكد من إغلاق القائمة بشكل صحيح
        buttons_to_style = [
            self.export_excel_btn,
            self.export_csv_btn,
            self.export_json_btn,
            self.export_html_btn
        ]
        
        for btn in buttons_to_style:
            btn.setStyleSheet(button_style)
        
        # تخصيص زر M3U بشكل مستقل
        btn_style = """
        QPushButton {
            padding: 5px;
            margin: 2px;
            min-width: 70px;
            background-color: red;
            color: black;
            font-family: 'Berlin Sans FB Demi';
            font-weight: bold;
            font-size: 14px;
            border: none;
            border-radius: 6px;
        }
        QPushButton:hover {
            background-color: darkred;
        }
        """
        self.export_m3u_btn.setStyleSheet(btn_style)
        controls_layout_grid.addWidget(export_group, 3, 0, 1, 4)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - %v/%m قناة") # تنسيق شريط التقدم
        layout.addWidget(self.progress_bar)

        filter_group = QGroupBox("بحث وتصفية")
        filter_layout = QVBoxLayout(filter_group)

        # الصف العلوي: بحث بالاسم + تصنيف عام
        top_filter_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("ابحث عن قناة بالاسم...")
        self.search_input.textChanged.connect(self.filter_channels)
        top_filter_layout.addWidget(self.search_input)

        self.category_filter = QComboBox()
        self.category_filter.addItem("جميع القنوات")
        self.category_filter.addItem("المفضلة")
        self.category_filter.addItem("قيد التشغيل فقط")
        self.category_filter.currentIndexChanged.connect(self.filter_channels)
        top_filter_layout.addWidget(self.category_filter)
        # زر إلغاء التصفية
        self.clear_filter_btn = QPushButton("إلغاء التصفية")
        self.clear_filter_btn.clicked.connect(self.clear_all_filters)
        top_filter_layout.addWidget(self.clear_filter_btn)
        # الصف السفلي: تصفية متقدمة
        adv_filter_layout = QHBoxLayout()

        # تصفية حسب النوع
        self.type_filter = QComboBox()
        self.type_filter.addItem("كل الأنواع")
        self.type_filter.addItem("تلفاز")
        self.type_filter.addItem("راديو")
        self.type_filter.currentIndexChanged.connect(self.filter_channels)
        adv_filter_layout.addWidget(QLabel("النوع:"))
        adv_filter_layout.addWidget(self.type_filter)

        # تصفية حسب الجودة
        self.quality_filter = QComboBox()
        self.quality_filter.addItem("كل الجودات")
        self.quality_filter.addItem("HD")
        self.quality_filter.addItem("SD")
        self.quality_filter.currentIndexChanged.connect(self.filter_channels)
        adv_filter_layout.addWidget(QLabel("الجودة:"))
        adv_filter_layout.addWidget(self.quality_filter)

        # تصفية حسب الحماية
        self.scramble_filter = QComboBox()
        self.scramble_filter.addItem("كل الحمايات")
        self.scramble_filter.addItem("مشفرة")
        self.scramble_filter.addItem("مفتوحة")
        self.scramble_filter.currentIndexChanged.connect(self.filter_channels)
        adv_filter_layout.addWidget(QLabel("الحماية:"))
        adv_filter_layout.addWidget(self.scramble_filter)

        # تصفية حسب القفل
        self.lock_filter = QComboBox()
        self.lock_filter.addItem("كل الحالات")
        self.lock_filter.addItem("مقفولة")
        self.lock_filter.addItem("غير مقفولة")
        self.lock_filter.currentIndexChanged.connect(self.filter_channels)
        adv_filter_layout.addWidget(QLabel("القفل:"))
        adv_filter_layout.addWidget(self.lock_filter)

        # تصفية حسب EPG
        self.epg_filter = QComboBox()
        self.epg_filter.addItem("كل الحالات")
        self.epg_filter.addItem("بدعم EPG")
        self.epg_filter.addItem("بدون دعم EPG")
        self.epg_filter.currentIndexChanged.connect(self.filter_channels)
        adv_filter_layout.addWidget(QLabel("EPG:"))
        adv_filter_layout.addWidget(self.epg_filter)

        # إضافة الصفوف إلى التخطيط الرئيسي
        filter_layout.addLayout(top_filter_layout)
        filter_layout.addLayout(adv_filter_layout)

        layout.addWidget(filter_group)
# اااااااا
        self.channel_table = QTableWidget()
        # self.channel_table.setColumnCount(25)  # زيادة بمقدار 1
        self.channel_table.setColumnCount(19)  # كان 18، أصبح 19
        self.channel_table.setHorizontalHeaderLabels([
        "⭐", "اسم القناة", "معرف الخدمة", "رابط البث", "النوع", "الجودة", "الحماية", 
        "مقفلة؟", "دعم EPG؟", "عدد مسارات الصوت", "Video PID", "Audio PID(s)", 
        "PMT PID", "مفضلة (FavBit)", "قيد التشغيل (Playing)", 
        "مؤشر الخدمة (ServiceIndex)", "رقم", "تحديد", "📷 صورة"  # العمود الجديد
        ])
        header = self.channel_table.horizontalHeader()
        header.setSectionsMovable(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.channel_table.setIconSize(QSize(100, 100))  # هنا
        self.channel_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.channel_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.channel_table.itemClicked.connect(self.handle_favorite_click)
        self.channel_table.itemDoubleClicked.connect(self.channel_selected)
        self.channel_table.currentItemChanged.connect(self.update_channel_action_buttons_state)
        header = self.channel_table.horizontalHeader()
        header.setFixedHeight(60)
        # تفعيل قائمة السياق
        self.channel_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.channel_table.customContextMenuRequested.connect(self.context_menu_event)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        # last_column_index = self.channel_table.columnCount() - 1
        self.set_custom_column_widths()
        layout.addWidget(self.channel_table)

    def init_settings_tab(self):
        layout = QVBoxLayout(self.settings_tab)
    
  
        # إضافة قسم جديد لعرض المجموعات المفضلة
        favorites_group = QGroupBox("المجموعات المفضلة")
        favorites_layout = QVBoxLayout(favorites_group)
        
        # عناصر واجهة لعرض المجموعات
        self.fav_groups_label = QLabel("عدد المجموعات: 0")
        self.fav_groups_list = QListWidget()
        
        favorites_layout.addWidget(self.fav_groups_label)
        favorites_layout.addWidget(self.fav_groups_list)
        
        layout.addWidget(favorites_group)    
        # --- إضافة مجموعة معلومات الجهاز في الأعلى ---
        device_info_group = QGroupBox("معلومات الجهاز")
        device_info_layout = QVBoxLayout(device_info_group)
        
        self.device_info_label = QLabel("❗ لم يتم الاتصال بعد.")
        self.device_info_label.setWordWrap(True)
        # self.device_info_label.setStyleSheet("font-size: 12px; padding: 12px;")
        # self.device_info_label.setStyleSheet("font-size: 12px; padding: 12px; color: red;")
        device_info_layout.addWidget(self.device_info_label)
        layout.addWidget(device_info_group)
        
        appearance_group = QGroupBox("إعدادات المظهر")
        appearance_layout = QFormLayout(appearance_group)

        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems(["صغير (8pt)", "متوسط (10pt)", "كبير (12pt)"])
        self.font_size_combo.currentIndexChanged.connect(self.change_font_size_combo)
        appearance_layout.addRow("حجم الخط:", self.font_size_combo)

        layout.addWidget(appearance_group)

        paths_group = QGroupBox("إعدادات المسارات")
        paths_layout = QFormLayout(paths_group)

        self.vlc_path_input = QLineEdit()
        vlc_browse_layout = QHBoxLayout()
        vlc_browse_layout.addWidget(self.vlc_path_input)
        self.vlc_browse_btn = QPushButton("...")
        self.vlc_browse_btn.setFixedWidth(30)
        self.vlc_browse_btn.clicked.connect(self.browse_vlc_path)
        vlc_browse_layout.addWidget(self.vlc_browse_btn)
        paths_layout.addRow("مسار VLC:", vlc_browse_layout)

        self.record_path_input = QLineEdit()
        record_browse_layout = QHBoxLayout()
        record_browse_layout.addWidget(self.record_path_input)
        self.record_browse_btn = QPushButton("...")
        self.record_browse_btn.setFixedWidth(30)
        self.record_browse_btn.clicked.connect(self.browse_record_path)
        record_browse_layout.addWidget(self.record_browse_btn)
        paths_layout.addRow("مسار حفظ التسجيلات:", record_browse_layout)

        layout.addWidget(paths_group)

        backup_group = QGroupBox("النسخ الاحتياطي والاستعادة")
        backup_layout = QHBoxLayout(backup_group)

        self.backup_btn = QPushButton("إنشاء نسخة احتياطية")
        self.backup_btn.clicked.connect(self.backup_settings)
        backup_layout.addWidget(self.backup_btn)

        self.restore_btn = QPushButton("استعادة النسخة الاحتياطية")
        self.restore_btn.clicked.connect(self.restore_settings)
        backup_layout.addWidget(self.restore_btn)

        self.reset_btn = QPushButton("استعادة الإعدادات الافتراضية")
        self.reset_btn.clicked.connect(self.reset_settings)
        backup_layout.addWidget(self.reset_btn)

        layout.addWidget(backup_group)



        stats_group = QGroupBox("إحصائيات")
        stats_layout = QFormLayout(stats_group)

        self.total_channels_label = QLabel("0")
        stats_layout.addRow("إجمالي القنوات المحملة:", self.total_channels_label)

        self.favorite_channels_label = QLabel("0")
        stats_layout.addRow("القنوات المفضلة:", self.favorite_channels_label)

        self.connected_devices_label = QLabel("0")
        stats_layout.addRow("الأجهزة المحفوظة:", self.connected_devices_label)

        layout.addWidget(stats_group)

        layout.addStretch()

    def add_remote_buttons(self):
        buttons = {
            "كتم 🔇": "23",
            "خفض الصوت 🔉": "3",
            "رفع الصوت 🔊": "4",
            "احمر 🔴": "8",
            "ازرق 🔵": "11",
            "إصفر 🟡": "10",
            "يسار 🡄": "3",
            "أعلى ⬆️": "1",
            "أسفل ⬇️": "2",
            "يمين ➔": "4",
            "موافق ✅": "5",
            "رجوع 🔙": "7",
            "قائمة 📋": "6",
            "أخضر 🟢": "9",
            "طريقة العرض DISPLAY": "24",
            "ايقاف تشغيل 📋": "42",
            "F1+333": "38",
            "SAT": "30",
            "حجم الشاشة MODE": "25",
            "موْقت التسجيل": "26",
            "رفع الصوت🔼": "35",
            "INFO29": "36",
            "خفض الصوت🔽": "36",
            "المفضلة FAV": "33",
            "دليل البرامج EPG": "32",
            "نص TXT": "34",
            "ترجمة SUB": "31",
            "USB": "43",
            "تلفزيون/راديو TV/R": "22",
            "إيقاف مؤقت ⏸": "63",
            "إيقاف STOP⏹": "62",
            "تشغيل PLAY▶": "61",
            "تسجيل RCD🛑": "58",
            "السابق PREV⏮": "64",
            "التالي NEXT⏭": "65",
            "رجوع سريع ⏪": "59",
            "تقدم سريع ⏩": "60",
            "RECall": "29",
            "0": "12", "1": "13", "2": "14", "3": "15",
            "4": "16", "5": "17", "6": "18", "7": "19",
            "8": "20", "9": "21",
            "بحث 🔍": "39",
            "موقت النوم ⏾": "41",
            "لغة الصوت 🔊": "54",
            "TIME SHIFT": "55",
            "زوم 🔍": "56",
            "معلومات ℹ️": "57",
            "القائمة MENU": "68",
            "C+🔺": "69",
            "C-🔻": "70",
            "جميع التطبيقات 📱": "76",
            "FHD+": "77",
            "يوتيوب ▶️": "81"
        }

        layout_map = {
            "ايقاف تشغيل 📋": (0, 0),
            "تلفزيون/راديو TV/R": (0, 1),
            "رفع الصوت 🔊": (0, 2),
            "خفض الصوت 🔉": (0, 3),
            "كتم 🔇": (0, 4),
            "رجوع 🔙": (0, 5),
            "طريقة العرض DISPLAY": (1, 0),
            "حجم الشاشة MODE": (1, 1),
            "جميع التطبيقات 📱": (1, 2),
            "يوتيوب ▶️": (1, 3),
            "USB": (1, 4),
            "FHD+": (2, 0),
            "SAT": (2, 1),
            "المفضلة FAV": (2, 2),
            "بحث 🔍": (2, 3),
            "دليل البرامج EPG": (2, 4),
            "القائمة MENU": (2, 5),
            "إصفر 🟡": (3, 0),
            "ازرق 🔵": (3, 1),
            "احمر 🔴": (3, 2),
            "أخضر 🟢": (3,3),
            "موقت النوم ⏾": (3, 4),
            "معلومات ℹ️": (4, 0),
            "ترجمة SUB": (4, 1),
            "لغة الصوت 🔊": (4, 2),
            "زوم 🔍": (4, 3),
            "نص TXT": (4, 4),
            "F1+333": (3, 5),
            "رفع الصوت🔼": (6, 4),
            "خفض الصوت🔽": (7, 4),
            "C+🔺": (6, 2),
            "C-🔻": (6, 3),
            "RECall": (2, 7),
            "أعلى ⬆️": (0, 6),
            "قائمة 📋": (0, 7),
            "يسار 🡄": (1, 7),
            "موافق ✅": (1, 6),
            "يمين ➔": (1, 5),
            "أسفل ⬇️": (2, 6),
            "رجوع 🔙": (0, 5),
            "TIME SHIFT": (6, 0),
            "تسجيل RCD🛑": (7, 0),
            "موْقت التسجيل": (6,1),
            "تشغيل PLAY▶": (8, 1),
            "إيقاف STOP⏹": (7, 1),
            "إيقاف مؤقت ⏸": (8, 0),
            "تقدم سريع ⏩": (7, 2),
            "رجوع سريع ⏪": (7, 3),
            "التالي NEXT⏭": (8, 2),
            "السابق PREV⏮": (8, 3),
            "1": (4, 7),
            "2": (4, 6),
            "3": (4, 5),
            "4": (5, 7),
            "5": (5, 6),
            "6": (5, 5),
            "7": (6, 7),
            "8": (6, 6),
            "9": (6, 5),
            "0": (3, 6),
        }

        for i in reversed(range(self.remote_grid.count())):
            widget = self.remote_grid.itemAt(i).widget()
            if widget: widget.setParent(None)

        for label, key_val in buttons.items():
            if label in layout_map:
                btn = QPushButton(label)
                btn.clicked.connect(lambda checked=False, k=key_val: self.send_key(k))
                row, col = layout_map[label]
                self.remote_grid.addWidget(btn, row, col)

    def apply_ui_settings(self):
        font = QFont()
        font.setPointSize(self.current_font_size)
        QApplication.instance().setFont(font)

        for i in range(self.remote_grid.count()):
            widget_item = self.remote_grid.itemAt(i)
            if widget_item:
                widget = widget_item.widget()
                if widget and isinstance(widget, QPushButton):
                    widget.setFont(font)
                    widget.setStyleSheet(f"font-size: {self.current_font_size}px; padding: 5px;")

        if self.current_font_size == 8: self.font_size_combo.setCurrentIndex(0)
        elif self.current_font_size == 10: self.font_size_combo.setCurrentIndex(1)
        elif self.current_font_size == 12: self.font_size_combo.setCurrentIndex(2)
        else: self.font_size_combo.setCurrentIndex(1)

    # استبدل دالة set_dark_mode الحالية بهذه النسخة المعدلة:
    def set_dark_mode(self, enabled):
        self.dark_mode = enabled
        self.settings_manager.settings.setValue("dark_mode", enabled)
        
        if enabled:
            style_sheet = """
                QMainWindow, QDialog, QWidget {
                    background-color: #353535;
                    color: #ffffff;
                }
                QTextEdit, QLineEdit, QComboBox, QListWidget {
                    background-color: #252525;
                    color: #ffffff;
                    border: 1px solid #555555;
                    selection-background-color: #2a82da;
                }
                QComboBox QAbstractItemView {
                    background-color: #252525;
                    color: #ffffff;
                    selection-background-color: #2a82da;
                }
                QPushButton {
                    background-color: #505050;
                    color: white;
                    border: 1px solid #555555;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #606060;
                }
                QPushButton:pressed {
                    background-color: #404040;
                }
                QGroupBox {
                    border: 1px solid gray;
                    margin-top: 0.5em;
                    padding: 5px;
                    color: #ffffff;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 3px 0 3px;
                    color: #ffffff;
                }
                QTabWidget::pane {
                    border: 1px solid gray;
                }
                QTabBar::tab {
                    background: #505050;
                    color: white;
                    padding: 8px;
                    border: 1px solid gray;
                }
                QTabBar::tab:selected {
                    background: #353535;
                }
                QTabBar::tab:hover {
                    background: #606060;
                }
                QTableWidget {
                    gridline-color: #555555;
                    background-color: #252525;
                    color: white;
                }
                QHeaderView::section {
                    background-color: #505050;
                    color: white;
                    border: 1px solid #555555;
                    padding: 4px;
                }
                QStatusBar {
                    background-color: #353535;
                    color: white;
                }
                QProgressBar {
                    border: 1px solid grey;
                    border-radius: 5px;
                    text-align: center;
                    color: white;
                }
                QProgressBar::chunk {
                    background-color: #2a82da;
                    width: 10px;
                    margin: 0.5px;
                }
                QMenuBar {
                    background-color: #353535;
                    color: white;
                }
                QMenuBar::item:selected {
                    background-color: #505050;
                }
                QMenu {
                    background-color: #353535;
                    color: white;
                    border: 1px solid #555555;
                }
                QMenu::item:selected {
                    background-color: #505050;
                }
            """
        else:
            style_sheet = ""  # إعادة تعيين إلى الوضع الفاتح
            
        self.setStyleSheet(style_sheet)
        # تحديث الألوان للأطفال
        for child in self.findChildren(QWidget):
            child.setStyleSheet(style_sheet)

    def change_font_size(self, size):
        self.current_font_size = size
        self.apply_ui_settings()
        self.settings_manager.save_window_state(self)

    def change_font_size_combo(self, index):
        sizes = {0: 8, 1: 10, 2: 12}
        selected_size = sizes.get(index, 10) # Default to 10 if index is somehow invalid
        if self.current_font_size != selected_size:
             self.change_font_size(selected_size)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def load_device_settings(self):
        if not self.settings_manager.validate_settings():
            self.settings_manager.repair_settings()
            self.update_output("تم استعادة الإعدادات الافتراضية بسبب بيانات تالفة أو مفقودة.")

        ip, port = self.settings_manager.load_device_settings()
        self.ip_input.setText(ip)
        self.port_input.setText(port)

        self.connected_devices = self.settings_manager.get_connected_devices()
        self.update_device_selector()

        self.vlc_path_input.setText(self.settings_manager.settings.value("vlc_path", r"C:\Program Files\VideoLAN\VLC\vlc.exe"))
        self.record_path_input.setText(self.settings_manager.settings.value("record_path", os.path.expanduser("~/Videos")))
        self.batch_size = int(self.settings_manager.settings.value("batch_size", 250))

        self.channels = self.settings_manager.load_channels()
        self.favorites = self.settings_manager.load_favorites()
        self.update_stats()

    def update_device_selector(self):
        self.device_selector.blockSignals(True)
        self.device_selector.clear()

        for i, device in enumerate(self.connected_devices):
            try:
                name = str(device.get('name', f'جهاز {i+1}'))
                ip_addr = str(device.get('ip', '0.0.0.0'))
                port_num = str(device.get('port', '20000'))
                self.device_selector.addItem(f"{name} ({ip_addr}:{port_num})", userData=device)
            except Exception as e:
                logging.error(f"Error adding device to selector: {device} - {e}")
                continue

        if self.connected_devices:
            last_ip = self.settings_manager.settings.value("device_ip", "")
            last_port = self.settings_manager.settings.value("device_port", "")
            found_last = False
            for i, device in enumerate(self.connected_devices):
                if device.get('ip') == last_ip and device.get('port') == last_port:
                    self.device_selector.setCurrentIndex(i)
                    self.current_device_index = i
                    self.device_selected(i)
                    found_last = True
                    break
            if not found_last:
                self.current_device_index = 0
                self.device_selector.setCurrentIndex(0)
                self.device_selected(0)
        else:
            self.current_device_index = -1
            self.ip_input.clear()
            self.port_input.clear()
        self.device_selector.blockSignals(False)

    def export_to_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ ملف CSV",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            if not file_path.lower().endswith('.csv'):
                file_path += '.csv'

            with open(file_path, 'w', encoding='utf-8-sig') as f:
                # كتابة العناوين
                headers = []
                for col in range(self.channel_table.columnCount()):
                    headers.append(self.channel_table.horizontalHeaderItem(col).text())
                f.write(','.join(headers) + '\n')

                # كتابة البيانات
                for row in range(self.channel_table.rowCount()):
                    row_data = []
                    for col in range(self.channel_table.columnCount()):
                        item = self.channel_table.item(row, col)
                        row_data.append(f'"{item.text()}"' if item else '""')
                    f.write(','.join(row_data) + '\n')

            self.update_output(f"✅ تم التصدير إلى CSV: {file_path}")

    def export_to_json(self):
        import json
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ ملف JSON",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            if not file_path.lower().endswith('.json'):
                file_path += '.json'

            data = {
                "headers": [self.channel_table.horizontalHeaderItem(col).text()
                           for col in range(self.channel_table.columnCount())],
                "rows": [
                    [self.channel_table.item(row, col).text() if self.channel_table.item(row, col) else ""
                    for col in range(self.channel_table.columnCount())]
                    for row in range(self.channel_table.rowCount())
                ]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            self.update_output(f"✅ تم التصدير إلى JSON: {file_path}")

    def export_to_html(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ صفحة HTML",
            "",
            "HTML Files (*.html);;All Files (*)"
        )

        if file_path:
            if not file_path.lower().endswith('.html'):
                file_path += '.html'

            html = """<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>قنوات ستارسات</title>
    <style>
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: right; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <table>
        <thead>
            <tr>
"""
            # العناوين
            for col in range(self.channel_table.columnCount()):
                html += f"<th>{self.channel_table.horizontalHeaderItem(col).text()}</th>"

            html += """
            </tr>
        </thead>
        <tbody>
"""
            # البيانات
            for row in range(self.channel_table.rowCount()):
                html += "<tr>"
                for col in range(self.channel_table.columnCount()):
                    item = self.channel_table.item(row, col)
                    html += f"<td>{item.text() if item else ''}</td>"
                html += "</tr>"

            html += """
        </tbody>
    </table>
</body>
</html>"""

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html)

            self.update_output(f"✅ تم التصدير إلى HTML: {file_path}")

    def export_to_sqlite(self):
        import sqlite3
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ قاعدة بيانات SQLite",
            "",
            "SQLite Databases (*.db);;All Files (*)"
        )

        if file_path:
            if not file_path.lower().endswith('.db'):
                file_path += '.db'

            conn = sqlite3.connect(file_path)
            c = conn.cursor()

            # إنشاء الجدول
            c.execute('''CREATE TABLE channels
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          favorite TEXT,
                          name TEXT,
                          service_id TEXT,
                          stream_url TEXT)''')

            # إدراج البيانات
            for row in range(self.channel_table.rowCount()):
                fav = "نعم" if self.channel_table.item(row, 0).checkState() == Qt.Checked else "لا"
                name = self.channel_table.item(row, 1).text()
                service_id = self.channel_table.item(row, 2).text()
                url = self.channel_table.item(row, 3).text()

                c.execute("INSERT INTO channels VALUES (NULL,?,?,?,?)",
                          (fav, name, service_id, url))

            conn.commit()
            conn.close()

            self.update_output(f"✅ تم التصدير إلى SQLite: {file_path}")

    def setup_cell_tooltips(self):
        """تعيين تلميحات للخلايا تعرض اسم العمود والمحتوى"""
        for row in range(self.channel_table.rowCount()):
            for col in range(self.channel_table.columnCount()):
                item = self.channel_table.item(row, col)
                if item:
                    # الحصول على اسم العمود من العنوان
                    header = self.channel_table.horizontalHeaderItem(col)
                    header_text = header.text() if header else f"Column {col}"

                    # تعيين التلميح
                    item.setToolTip(
                        f"{header_text}\n"  # السطر الأول: اسم العمود
                        f"----------------\n"
                        f"{item.text()}"     # السطر الثاني: محتوى الخلية
                    )
    def enable_header_word_wrap(self):
        """تمكين التفاف النص في رأس الجدول"""
        header = self.channel_table.horizontalHeader()

        # تفعيل التفاف النص
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        # إذا أردت أن يكون النص في سطرين أو أكثر:
        header.setStyleSheet("""
            QHeaderView::section {
                padding: 5px;
                text-align: center;
                background-color: #424242;
                color: white;
                border: 1px solid #555555;
            }
        """)

        header.setFixedHeight(60)
    def set_custom_column_widths(self):
        """ضبط عرض الأعمدة حسب القيم المحددة"""
        column_widths = {
            0: 1,
            1: 8,
            2: 5,
            3: 15,
            4: 2,
            5: 2,
            6: 3,
            7: 3,
            8: 3,
            9: 1,
            10: 5,
            11: 3,
            12: 3,
            13: 2,
            14: 5,
            15: 5,
            16: 1,
            17: 1,
            18: 1,
            19: 1,
            20: 1,
            21: 1,




            # يمكنك إضافة المزيد من الأعمدة هنا حسب الحاجة
        }

        for column, width in column_widths.items():
            self.channel_table.setColumnWidth(column, width * 20)
    def export_to_m3u(self):
        """تصدير القنوات إلى ملف بصيغة M3U"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ ملف M3U",
            "",
            "M3U Files (*.m3u);;All Files (*)"
        )

        if not file_path:
            return

        if not file_path.lower().endswith('.m3u'):
            file_path += '.m3u'

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # كتابة رأس الملف
                f.write("#EXTM3U\n")

                # كتابة كل قناة
                for row in range(self.channel_table.rowCount()):
                    name_item = self.channel_table.item(row, 1)  # اسم القناة
                    url_item = self.channel_table.item(row, 3)   # رابط البث
                    type_item = self.channel_table.item(row, 4)  # النوع (تلفاز/راديو)

                    if name_item and url_item and type_item:
                        channel_name = name_item.text()
                        stream_url = url_item.text()
                        channel_type = type_item.text()

                        if stream_url:  # فقط إذا كان هناك رابط بث
                            # كتابة معلومات القناة
                            f.write(f"#EXTINF:-1 group-title=\"Starsat\",{channel_name}\n")
                            f.write(f"{stream_url}\n")

            self.update_output(f"✅ تم التصدير إلى M3U: {file_path}")
            QMessageBox.information(self, "نجاح", f"تم إنشاء ملف M3U بنجاح:\n{file_path}")
        except Exception as e:
            self.update_output(f"❌ خطأ في التصدير إلى M3U: {str(e)}")
            QMessageBox.critical(self, "خطأ", f"فشل في حفظ الملف:\n{str(e)}")

    def show_playing_channels(self):
        for row in range(self.channel_table.rowCount()):
            playing_item = self.channel_table.item(row, 14)
            if playing_item and playing_item.text().strip() == "نعم":
                dialog = QDialog(self)
                dialog.setWindowTitle(f"تفاصيل القناة (الصف {row + 1})")
                layout = QVBoxLayout(dialog)

                table = QTableWidget()
                table.setColumnCount(2)
                table.setHorizontalHeaderLabels(["اسم الحقل", "القيمة"])
                table.setRowCount(self.channel_table.columnCount())
                table.horizontalHeader().setStretchLastSection(True)
                table.verticalHeader().setVisible(False)

                table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

                table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)

                table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

                for col in range(self.channel_table.columnCount()):
                    header_item = self.channel_table.horizontalHeaderItem(col)
                    item = self.channel_table.item(row, col)
                    header = header_item.text() if header_item else f"عمود {col + 1}"
                    value = item.text().strip() if item else ""

                    table.setItem(col, 0, QTableWidgetItem(header))
                    table.setItem(col, 1, QTableWidgetItem(value))

                layout.addWidget(table)

                # أزرار النسخ والإغلاق
                btn_box = QDialogButtonBox()
                copy_btn = QPushButton("📋 نسخ الخلية المحددة")
                ok_btn = QPushButton("موافق")

                def copy_selected_cell():
                    selected_items = table.selectedItems()
                    if selected_items:
                        text = selected_items[0].text()
                        QApplication.clipboard().setText(text)

                copy_btn.clicked.connect(copy_selected_cell)
                ok_btn.clicked.connect(dialog.accept)

                btn_box.addButton(copy_btn, QDialogButtonBox.ButtonRole.ActionRole)
                btn_box.addButton(ok_btn, QDialogButtonBox.ButtonRole.AcceptRole)
                layout.addWidget(btn_box)

                self.channel_table.selectRow(row)
                self.channel_table.scrollToItem(self.channel_table.item(row, 1), QAbstractItemView.ScrollHint.PositionAtCenter)

                dialog.resize(600, 500)
                dialog.exec()


    def clear_channel_table(self):
        """مسح جميع بيانات الجدول والقنوات المحفوظة"""
        reply = QMessageBox.question(
            self,
            "تأكيد المسح",
            "هل أنت متأكد أنك تريد مسح جميع بيانات القنوات؟\nهذا الإجراء لا يمكن التراجع عنه!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # مسح الجدول المرئي
            self.channel_table.setRowCount(0)

            # مسح البيانات الداخلية
            self.channels = []
            self.favorites = []

            # تحديث الإحصائيات
            self.update_stats()

            # مسح التفضيلات المحفوظة
            self.settings_manager.save_channels([])
            self.settings_manager.save_favorites([])

            self.update_output("✅ تم مسح جميع بيانات القنوات بنجاح")


    def export_to_excel(self):
        try:
            # إنشاء DataFrame من بيانات الجدول
            data = []
            for row in range(self.channel_table.rowCount()):
                row_data = []
                for column in range(self.channel_table.columnCount()):
                    item = self.channel_table.item(row, column)
                    row_data.append(item.text() if item else "")
                data.append(row_data)

            # أسماء الأعمدة
            headers = [self.channel_table.horizontalHeaderItem(i).text()
                      for i in range(self.channel_table.columnCount())]

            import pandas as pd
            df = pd.DataFrame(data, columns=headers)

            # اختيار مسار الحفظ
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "حفظ ملف Excel",
                "",
                "Excel Files (*.xlsx);;All Files (*)"
            )

            if file_path:
                # التأكد من أن الملف ينتهي بـ .xlsx
                if not file_path.lower().endswith('.xlsx'):
                    file_path += '.xlsx'

                df.to_excel(file_path, index=False)
                self.update_output(f"✅ تم تصدير البيانات إلى: {file_path}")
                QMessageBox.information(self, "نجاح", "تم حفظ الملف بنجاح!")

        except Exception as e:
            self.update_output(f"❌ خطأ في التصدير إلى Excel: {str(e)}")
            QMessageBox.critical(self, "خطأ", f"فشل في حفظ الملف:\n{str(e)}")


    def add_device(self):
        name, ok = QInputDialog.getText(self, "إضافة جهاز", "اسم الجهاز:")
        if not ok or not name.strip():
            return
        name = name.strip()

        ip = self.ip_input.text().strip()
        port_str_val = self.port_input.text().strip()
        
        if not ip or not port_str_val:
            QMessageBox.warning(self, "تحذير", "الرجاء إدخال عنوان IP ورقم المنفذ للجهاز الحالي أولاً لحفظه.")
            return
        try:
            int(port_str_val) # Validate port is number
        except ValueError:
            QMessageBox.warning(self, "تحذير", "رقم المنفذ يجب أن يكون رقماً.")
            return

        new_device = {'name': name, 'ip': ip, 'port': port_str_val}

        self.connected_devices.append(new_device)
        self.settings_manager.settings.setValue("connected_devices", self.connected_devices)
        self.update_device_selector()
        self.device_selector.setCurrentIndex(len(self.connected_devices) - 1)
        self.update_stats()

    def remove_device(self):
        current_idx = self.device_selector.currentIndex()
        if current_idx < 0: # No item selected
            QMessageBox.information(self, "معلومة", "الرجاء تحديد جهاز من القائمة لحذفه.")
            return

        if current_idx >= len(self.connected_devices):
            logging.error("Device selector index out of bounds with internal list.")
            self.update_device_selector() # Attempt to resync
            return

        device_to_remove = self.connected_devices[current_idx]
        reply = QMessageBox.question(
            self, "حذف جهاز",
            f"هل أنت متأكد من حذف الجهاز '{device_to_remove.get('name', 'غير معروف')}'؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.connected_devices.pop(current_idx)
            self.settings_manager.settings.setValue("connected_devices", self.connected_devices)
            self.update_device_selector()
            self.update_stats()

    def device_selected(self, index):
        if 0 <= index < self.device_selector.count(): # Use selector's count for safety
            device_data = self.device_selector.itemData(index)
            if device_data and isinstance(device_data, dict):
                self.ip_input.setText(device_data.get('ip', ''))
                self.port_input.setText(device_data.get('port', ''))
                self.current_device_index = index # Update internal index
            else:
                # Fallback if itemData is missing, try to parse from text
                selected_text = self.device_selector.itemText(index)
                try:
                    ip_port_str = selected_text[selected_text.rfind("(")+1:selected_text.rfind(")")]
                    ip_addr, port_num = ip_port_str.split(':')
                    self.ip_input.setText(ip_addr)
                    self.port_input.setText(port_num)
                    self.current_device_index = index
                except Exception as e:
                    logging.error(f"Could not parse device info from selector text: {selected_text} - {e}")
                    self.ip_input.clear()
                    self.port_input.clear()
                    self.current_device_index = -1 # Indicate error or unknown selection
        elif self.device_selector.count() == 0: # No devices left
            self.ip_input.clear()
            self.port_input.clear()
            self.current_device_index = -1


    def connect_to_device(self):
        if hasattr(self, 'network_thread') and self.network_thread and self.network_thread.isRunning():
            self.update_output("⚠️ الاتصال جارٍ بالفعل.")
            return

        ip = self.ip_input.text().strip()
        port_str = self.port_input.text().strip()

        if not ip:
            QMessageBox.warning(self, "خطأ", "يرجى إدخال عنوان IP.")
            return
        try:
            port_val = int(port_str)
            if not (0 < port_val < 65536): raise ValueError("Port out of range")
        except ValueError:
            QMessageBox.warning(self, "خطأ", "رقم المنفذ غير صالح.")
            return

        self.settings_manager.save_device_settings(ip, port_str)

        self.connect_btn.setEnabled(False)

        self.output.clear()
        self.channel_table.setRowCount(0)
        self.channels = []
        self.update_stats()
        self.update_output(f"⏳ جارٍ الاتصال بـ {ip}:{port_str}...")
        
        self.network_thread = NetworkThread(ip, port_val)
        self.network_thread.max_reconnect_attempts = 5 if self.auto_reconnect else 0  # إضافة هذا السطر

        self.network_thread.connected_signal.connect(self.handle_connected)
        self.network_thread.connected_signal.connect(self.on_connected)
        self.network_thread.disconnected_signal.connect(self.handle_disconnected)
        self.network_thread.message_signal.connect(self.update_output)
        self.network_thread.data_signal.connect(self.handle_received_data)
        self.network_thread.channel_data_signal.connect(self.populate_channel_table)
        self.network_thread.connection_status_signal.connect(self.update_connection_status)
        self.network_thread.ping_result_signal.connect(self.update_ping_status)
        self.network_thread.start()

    def disconnect_from_device(self):
        if self.is_updating_all_urls:
            self.stop_updating_all_urls()
        if self.is_fetching_all:
            self.stop_fetching_all()

        if self.network_thread and self.network_thread.isRunning():
            self.update_output("⏳ جاري قطع الاتصال...")
            self.network_thread.stop()
        else:
            self.handle_disconnected()
            self.update_output("⚠️ لا يوجد اتصال نشط أو تم قطع الاتصال بالفعل.")

    def update_connection_status(self, connected_status):
        self.connected = connected_status
        if self.connected:
            self.connection_status_label.setText("✅ متصل")
            self.connection_status_label.setStyleSheet("color: lightgreen;")
            self.fetch_channels_btn.setEnabled(True)
            self.fetch_all_btn.setEnabled(True)
            self.update_all_urls_btn.setEnabled(self.channel_table.rowCount() > 0)
            self.disconnect_btn.setEnabled(True)
            if hasattr(self, 'fetch_and_update_btn'):
                self.fetch_and_update_btn.setEnabled(True)
            self.connect_btn.setEnabled(False)
            self.digit_input.setEnabled(True)
            self.go_button.setEnabled(True)
        else:
            self.connection_status_label.setText("❌ غير متصل")
            self.connection_status_label.setStyleSheet("color: red;")
            self.fetch_channels_btn.setEnabled(False)
            self.fetch_all_btn.setEnabled(False)
            self.update_all_urls_btn.setEnabled(False)
            self.stop_fetch_btn.setEnabled(False)
            self.is_fetching_all = False
            self.is_updating_all_urls = False
            self.url_update_timer.stop()
            self.progress_bar.setVisible(False)
            self.disconnect_btn.setEnabled(False)
            if hasattr(self, 'fetch_and_update_btn'):
                self.fetch_and_update_btn.setEnabled(False)
            self.connect_btn.setEnabled(True)
            self.digit_input.setEnabled(False)
            self.go_button.setEnabled(False)
        self.update_channel_action_buttons_state()

    def update_ping_status(self, latency):
        if latency >= 0:
            self.ping_status_label.setText(f"زمن الاستجابة: {latency:.1f} ms")
            if latency < 100: self.ping_status_label.setStyleSheet("color: lightgreen;")
            elif latency < 300: self.ping_status_label.setStyleSheet("color: orange;")
            else: self.ping_status_label.setStyleSheet("color: red;")
        else:
            self.ping_status_label.setText("زمن الاستجابة: --")
            self.ping_status_label.setStyleSheet("color: red;")

    def fetch_channel_list(self):
        if not self.connected or not self.network_thread or not self.network_thread.isRunning():
            QMessageBox.warning(self, "غير متصل", "يرجى الاتصال بالجهاز أولاً.")
            return

        self.update_output(f"📡 طلب أول {self.batch_size} قناة...")
        self.channel_table.setRowCount(0)
        self.channels = []
        self.is_fetching_all = False
        self.is_updating_all_urls = False
        self.url_update_timer.stop()
        self.progress_bar.setVisible(False)
        self.setup_cell_tooltips()

        try:
            request_body = f'{{"request":"0", "FromIndex":"0", "ToIndex":"{self.batch_size -1}"}}'
            channel_command = build_message(request_body)
            self.network_thread.send_command(("fetch_channels", channel_command))
        except Exception as e:
            self.update_output(f"❌ خطأ أثناء إعداد طلب القنوات: {e}")

    def start_fetching_all(self):
        if not self.connected or not self.network_thread or not self.network_thread.isRunning():
            QMessageBox.warning(self, "غير متصل", "يرجى الاتصال بالجهاز أولاً.")
            return

        if self.is_updating_all_urls:
            QMessageBox.warning(self, "عملية جارية", "يتم حاليًا تحديث روابط البث. يرجى الانتظار أو الإيقاف أولاً.")
            return

        self.is_fetching_all = True
        self.current_fetch_from = 0
        self.channel_table.setRowCount(0)
        self.channels = []

        self.fetch_channels_btn.setEnabled(False)
        self.fetch_all_btn.setEnabled(False)
        self.update_all_urls_btn.setEnabled(False)
        self.stop_fetch_btn.setEnabled(True)
        self.progress_bar.setRange(0,100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p% - تحميل القنوات...")
        self.progress_bar.setVisible(True)

        self.update_output("⏳ بدء جلب جميع القنوات...")
        self.fetch_next_batch()

    def fetch_next_batch(self):
        if not self.is_fetching_all or not self.connected:
            self.stop_fetching_all()
            return

        to_index = self.current_fetch_from + self.batch_size - 1
        self.update_output(f"📡 جلب القنوات من {self.current_fetch_from} إلى {to_index}...")

        try:
            request_body = f'{{"request":"0", "FromIndex":"{self.current_fetch_from}", "ToIndex":"{to_index}"}}'
            channel_command = build_message(request_body)
            self.network_thread.send_command(("fetch_channels", channel_command))
        except Exception as e:
            self.update_output(f"❌ خطأ في طلب القنوات: {e}")
            self.stop_fetching_all()

    def stop_fetching_all(self):
        if self.is_fetching_all:
            self.is_fetching_all = False
            self.update_output("⏹ توقف جلب القنوات.")

        if self.is_updating_all_urls:
            self.is_updating_all_urls = False
            self.url_update_timer.stop()
            self.update_output("⏹ توقف تحديث روابط البث.")
            self.last_requested_service_id_for_url = None

        if self.connected:
            self.fetch_channels_btn.setEnabled(True)
            self.fetch_all_btn.setEnabled(True)
            self.update_all_urls_btn.setEnabled(self.channel_table.rowCount() > 0)
        else:
            self.fetch_channels_btn.setEnabled(False)
            self.fetch_all_btn.setEnabled(False)
            self.update_all_urls_btn.setEnabled(False)

        self.stop_fetch_btn.setEnabled(False)
        if not self.is_fetching_all and not self.is_updating_all_urls:
            self.progress_bar.setVisible(False)

    @pyqtSlot(list)
    def populate_channel_table(self, channels_batch: list):
        import os
        from PyQt6.QtGui import QPixmap, QIcon, QColor
        from PyQt6.QtCore import Qt
    
        batch_size_received = len(channels_batch)
        self.update_output(f"📊 تعبئة الجدول بـ {batch_size_received} قناة جديدة...")
        self.channel_table.setSortingEnabled(False)
        receiver_ip = self.ip_input.text().strip()
    
        if not self.is_fetching_all:
            self.channels = list(channels_batch)
        else:
            self.channels.extend(channels_batch)
    
        self.favorites = self.settings_manager.load_favorites()
    
        starting_row_index = self.channel_table.rowCount()
        last_column_index = self.channel_table.columnCount() - 1  # العمود الأخير
    
        for i, channel_data in enumerate(channels_batch):
            channel_name = channel_data.get('ServiceName', '؟؟؟')
            channel_id = str(channel_data.get('ServiceID', '؟؟؟'))
            initial_stream_url = ""
    
            if receiver_ip and channel_id != '؟؟؟':
                initial_stream_url = f"http://{receiver_ip}:8085/player.{channel_id}"
    
            current_row_count = starting_row_index + i
            self.channel_table.insertRow(current_row_count)
    
            fav_item = QTableWidgetItem()
            fav_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            fav_item.setCheckState(Qt.CheckState.Checked if channel_id in self.favorites else Qt.CheckState.Unchecked)
            self.channel_table.setItem(current_row_count, 0, fav_item)
    
            name_item = QTableWidgetItem(channel_name)
            self.channel_table.setItem(current_row_count, 1, name_item)
    
            id_item = QTableWidgetItem(channel_id)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_table.setItem(current_row_count, 2, id_item)
    
            url_item = QTableWidgetItem(initial_stream_url)
            self.channel_table.setItem(current_row_count, 3, url_item)
    
            radio_flag = channel_data.get("Radio", 0)
            type_item = QTableWidgetItem("راديو" if radio_flag else "تلفاز")
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_table.setItem(current_row_count, 4, type_item)
    
            hd_flag = channel_data.get("HD", 0)
            quality_item = QTableWidgetItem("HD" if hd_flag else "SD")
            quality_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_table.setItem(current_row_count, 5, quality_item)
    
            scramble_flag = channel_data.get("Scramble", 0)
            scramble_text = "مشفرة" if scramble_flag else "مفتوحة"
            scramble_item = QTableWidgetItem(scramble_text)
            scramble_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_table.setItem(current_row_count, 6, scramble_item)
    
            for col in range(self.channel_table.columnCount() - 1):
                cell_item = self.channel_table.item(current_row_count, col)
                if cell_item and scramble_flag:
                    cell_item.setBackground(QColor(255, 228, 196))
                    cell_item.setForeground(QColor(0, 0, 0))
    
            lock_flag = channel_data.get("Lock", 0)
            lock_text = "نعم" if lock_flag else "لا"
            lock_item = QTableWidgetItem(lock_text)
            lock_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_table.setItem(current_row_count, 7, lock_item)
    
            epg_flag = channel_data.get("EPG", 0)
            epg_text = "نعم" if epg_flag else "لا"
            epg_item = QTableWidgetItem(epg_text)
            epg_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_table.setItem(current_row_count, 8, epg_item)
    
# اااااااا
    
            audio_array = channel_data.get("AudioArray", [])
            audio_count = len(audio_array)
            audio_count_item = QTableWidgetItem(str(audio_count))
            audio_count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_table.setItem(current_row_count, 9, audio_count_item)
    
            video_pid = channel_data.get("VideoPID", 0)
            video_pid_item = QTableWidgetItem(str(video_pid))
            video_pid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_table.setItem(current_row_count, 10, video_pid_item)
    
            audio_pids = ",".join(str(a.get("PID", "?")) for a in audio_array)
            audio_pids_item = QTableWidgetItem(audio_pids)
            audio_pids_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_table.setItem(current_row_count, 11, audio_pids_item)
    
            pmt_pid = channel_data.get("PMTPID", 0)
            pmt_pid_item = QTableWidgetItem(str(pmt_pid))
            pmt_pid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_table.setItem(current_row_count, 12, pmt_pid_item)
    
            favbit = channel_data.get("FavBit", 0)
            fav_groups = self.get_favorite_group_names(favbit)
            fav_text = ", ".join(fav_groups) if fav_groups else "لا"
            favbit_item = QTableWidgetItem(fav_text)
            favbit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_table.setItem(current_row_count, 13, favbit_item)
    
            playing = channel_data.get("Playing", 0)
            playing_item = QTableWidgetItem("نعم" if playing else "لا")
            playing_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_table.setItem(current_row_count, 14, playing_item)

    

     
            service_index = channel_data.get("ServiceIndex", 0)
            service_index_item = QTableWidgetItem(str(service_index))
            service_index_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_table.setItem(current_row_count, 15, service_index_item)
    
            auto_index = current_row_count + 1
            auto_index_item = QTableWidgetItem(str(auto_index))
            auto_index_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_table.setItem(current_row_count, 16, auto_index_item)
            # إضافة خانة تحديد في العمود الأخير
            select_item = QTableWidgetItem()
            select_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            select_item.setCheckState(Qt.CheckState.Unchecked)
            self.channel_table.setItem(current_row_count, 17, select_item)  # العمود 18 للتحديد    
            
            # 🔷 الصورة في العمود الأخير - برقم الصف
            row_number = current_row_count + 1
            image_name = str(row_number)
    
            image_path = f"images/{image_name}.png"
            if not os.path.exists(image_path):
                image_path = "images/default.png"
    
            pixmap = QPixmap(image_path).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio)
            image_item = QTableWidgetItem()
            image_item.setIcon(QIcon(pixmap))
            self.channel_table.setItem(current_row_count, 18, image_item) # العمود 17 للصورة
            self.channel_table.setRowHeight(current_row_count, 40)
        self.setup_cell_tooltips()
        self.channel_table.setSortingEnabled(True)
        self.update_output(f"✅ إجمالي القنوات في الجدول الآن: {self.channel_table.rowCount()}.")
        self.update_stats()
        self.filter_channels()
        self.update_stats()
    
        if self.connected:
            self.update_all_urls_btn.setEnabled(self.channel_table.rowCount() > 0)
    
        if self.is_fetching_all:
            self.current_fetch_from += batch_size_received
            if batch_size_received < self.batch_size and batch_size_received > 0:
                self.progress_bar.setRange(0, self.current_fetch_from)
                self.progress_bar.setValue(self.current_fetch_from)
            elif batch_size_received > 0:
                if self.progress_bar.maximum() == 100:
                    estimated_total = 5000
                    progress_val = min(100, int((self.current_fetch_from / estimated_total) * 100))
                    self.progress_bar.setValue(progress_val)
                else:
                    self.progress_bar.setValue(self.current_fetch_from)
    
            if batch_size_received == 0 or batch_size_received < self.batch_size:
                self.update_output(f"🏁 اكتمل جلب جميع القنوات. الإجمالي: {len(self.channels)}.")
                self.progress_bar.setValue(self.progress_bar.maximum())
                self.stop_fetching_all()
    
                QTimer.singleShot(2000, lambda: self.progress_bar.setVisible(False) if not (self.is_fetching_all or self.is_updating_all_urls) else None)
            else:
                QTimer.singleShot(100, self.fetch_next_batch)


    # --- دوال جديدة لتحديث روابط البث لجميع القنوات ---
    def start_updating_all_urls(self):
        if not self.connected or not self.network_thread or not self.network_thread.isRunning():
            QMessageBox.warning(self, "غير متصل", "يرجى الاتصال بالجهاز أولاً.")
            return
        if self.channel_table.rowCount() == 0:
            QMessageBox.information(self, "لا قنوات", "لا توجد قنوات في الجدول لتحديث روابطها.")
            return
        if self.is_fetching_all:
             QMessageBox.warning(self, "عملية جارية", "يتم حاليًا جلب قائمة القنوات. يرجى الانتظار أو الإيقاف أولاً.")
             return

        self.is_updating_all_urls = True
        self.current_url_update_index = 0
        self.last_requested_service_id_for_url = None

        self.progress_bar.setRange(0, self.channel_table.rowCount())
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p% - تحديث الروابط: %v/%m")
        self.progress_bar.setVisible(True)

        self.fetch_channels_btn.setEnabled(False)
        self.fetch_all_btn.setEnabled(False)
        self.update_all_urls_btn.setEnabled(False) # تعطيل نفسه أثناء التشغيل
        self.stop_fetch_btn.setEnabled(True) # زر الإيقاف يمكنه إيقاف هذه العملية

        self.update_output("⏳ بدء تحديث روابط البث لجميع القنوات...")
        self.process_next_url_update()

    def process_next_url_update(self):
        if not self.is_updating_all_urls or not self.connected:
            self.stop_updating_all_urls()
            self.setup_cell_tooltips()
            return

        if self.current_url_update_index >= self.channel_table.rowCount():
            self.stop_updating_all_urls()
            self.update_output("🏁 اكتمل تحديث جميع روابط البث.")
            QMessageBox.information(self, "اكتمل", "تم تحديث جميع روابط البث.")
            self.setup_cell_tooltips()

            return

        row = self.current_url_update_index
        service_id_item = self.channel_table.item(row, 2)
        channel_name_item = self.channel_table.item(row, 1)

        if service_id_item and channel_name_item:
            service_id = service_id_item.text()
            channel_name = channel_name_item.text()

            if service_id and service_id != '؟؟؟':
                self.update_output(f"🔄 طلب رابط البث للقناة: {channel_name} (ID: {service_id}) - {row + 1}/{self.channel_table.rowCount()}")
                self.last_requested_service_id_for_url = service_id # تتبع هذه القناة
                self.change_channel(service_id, channel_name)
                self.progress_bar.setValue(self.current_url_update_index + 1)
            else:
                self.process_next_url_update()
        else:
            self.process_next_url_update()
            self.setup_cell_tooltips()

    def stop_updating_all_urls(self):
        if not self.is_updating_all_urls: return
        self.setup_cell_tooltips()

        self.is_updating_all_urls = False
        self.url_update_timer.stop()
        self.last_requested_service_id_for_url = None
        self.update_output("⏹ توقف تحديث روابط البث.")
        self.setup_cell_tooltips()

        if self.connected:
            self.fetch_channels_btn.setEnabled(True)
            self.fetch_all_btn.setEnabled(True)
            self.update_all_urls_btn.setEnabled(self.channel_table.rowCount() > 0 and not self.is_fetching_all and not self.is_updating_all_urls)
        self.stop_fetch_btn.setEnabled(False)
        self.setup_cell_tooltips()

        if not self.is_fetching_all:
            self.progress_bar.setVisible(False)
            self.setup_cell_tooltips()
    @pyqtSlot(str, str)
    def handle_received_data(self, data_type: str, content: str):
        cleaned_content = content.strip()
        parsed_json_data = None
    
        if data_type in ["zlib_json", "json"] or \
           (cleaned_content.startswith('{') and cleaned_content.endswith('}')) or \
           (cleaned_content.startswith('[') and cleaned_content.endswith(']')):
            try:
                potential_data = json.loads(cleaned_content)
                if isinstance(potential_data, dict):
                    parsed_json_data = potential_data
                elif isinstance(potential_data, list) and len(potential_data) > 0 and isinstance(potential_data[0], dict):
                    parsed_json_data = potential_data[0]
            except json.JSONDecodeError:
                pass
            except Exception as e:
                logging.error(f"Error processing received JSON data: {e}")
    
        # ✅ معالجة معلومات الجهاز العامة
        if isinstance(parsed_json_data, dict) and \
           all(k in parsed_json_data for k in ["ProductName", "SoftwareVersion", "SerialNumber"]):
            self.show_device_info(parsed_json_data)
            return
    
        # ✅ معالجة تحديث رابط البث
        if isinstance(parsed_json_data, dict) and \
           parsed_json_data.get("success") == "1" and \
           "url" in parsed_json_data and \
           self.last_requested_service_id_for_url is not None:
    
            received_url = parsed_json_data['url']
            found_and_updated = False
    
            for row in range(self.channel_table.rowCount()):
                service_id_item = self.channel_table.item(row, 2)
                url_item = self.channel_table.item(row, 3)
                if service_id_item and url_item and service_id_item.text() == self.last_requested_service_id_for_url:
                    url_item.setText(received_url)
                    found_and_updated = True
                    break
    
            if self.is_updating_all_urls:
                self.current_url_update_index += 1
                self.progress_bar.setValue(self.current_url_update_index)
                QTimer.singleShot(self.url_update_delay, self.process_next_url_update)
    
            if not found_and_updated:
                if parsed_json_data.get("success") == "1" and "url" not in parsed_json_data:
                    fallback_sid = self.last_requested_service_id_for_url.lstrip("0")
                    rtsp_url = f"rtsp://{self.ip_input.text().strip()}:554/?prognumber={fallback_sid}"
                    self.update_output(f"🌐 لم يتم استلام رابط بث، تم توليد رابط RTSP بديل: {rtsp_url}")
    
                    for row in range(self.channel_table.rowCount()):
                        service_id_item = self.channel_table.item(row, 2)
                        url_item = self.channel_table.item(row, 3)
                        if service_id_item and url_item and service_id_item.text() == self.last_requested_service_id_for_url:
                            url_item.setText(rtsp_url)
                            break
    
                    if self.is_updating_all_urls:
                        self.current_url_update_index += 1
                        self.progress_bar.setValue(self.current_url_update_index)
                        QTimer.singleShot(self.url_update_delay, self.process_next_url_update)
    
                    self.last_requested_service_id_for_url = None
                else:
                    self.update_output(f"⚠️ تم استلام رابط ({received_url}) ولكن لم يتم العثور على قناة مطابقة لـ ID: {self.last_requested_service_id_for_url}")
    
            if self.is_updating_all_urls:
                self.last_requested_service_id_for_url = None
    
        # ✅ معالجة بيانات المجموعات المفضلة (الجزء الجديد)
        try:
            # قد تأتي البيانات في شكل قائمة تحتوي على كائن واحد
            if isinstance(parsed_json_data, list) and len(parsed_json_data) > 0:
                # نأخذ العنصر الأول من القائمة
                first_item = parsed_json_data[0]
                if isinstance(first_item, dict) and "favGroupNames" in first_item:
                    # استخراج قائمة أسماء المجموعات
                    self.favorite_groups = first_item["favGroupNames"]
                    # تحديث العرض في واجهة المستخدم
                    self.update_favorite_groups_display()
                    return
                    
            # أو قد تأتي البيانات في شكل كائن مباشر
            elif isinstance(parsed_json_data, dict) and "favGroupNames" in parsed_json_data:
                self.favorite_groups = parsed_json_data["favGroupNames"]
                self.update_favorite_groups_display()
                return
                
            # معالجة الحالة الخاصة حيث تكون البيانات مباشرة في القائمة
            elif isinstance(parsed_json_data, list) and all(isinstance(item, str) for item in parsed_json_data):
                self.favorite_groups = parsed_json_data
                self.update_favorite_groups_display()
                return
        except Exception as e:
            logging.error(f"Error processing favorite groups: {e}")

    def update_favorite_groups_display(self):
        """تحديث عرض المجموعات المفضلة في تبويب الإعدادات"""
        # تحديث الـ QListWidget
        self.fav_groups_list.clear()
        self.fav_groups_list.addItems(self.favorite_groups)
        
        # تحديث التسمية بعدد المجموعات
        self.fav_groups_label.setText(f"عدد المجموعات: {len(self.favorite_groups)}")
        
        # إضافة تلميح يظهر جميع المجموعات
        tooltip_text = "المجموعات المفضلة:\n" + "\n".join(self.favorite_groups)
        self.fav_groups_list.setToolTip(tooltip_text)
        
        # تمييز المجموعة الأولى بلون خفيف (اختياري)
        if self.favorite_groups:
            item = self.fav_groups_list.item(0)
            # item.setBackground(QColor(240, 248, 255))  # لون أزرق فاتح                     

    def filter_channels(self):
        """تطبيق عوامل التصفية الحالية على الجدول"""
        # الحصول على قيم التصفية الحالية
        search_text = self.search_input.text().strip().lower()
        category = self.category_filter.currentText()
        channel_type = self.type_filter.currentText()
        quality = self.quality_filter.currentText()
        scramble = self.scramble_filter.currentText()
        locked = self.lock_filter.currentText()
        epg = self.epg_filter.currentText()

        # إذا كانت جميع عوامل التصفية في وضعها الافتراضي
        if (not search_text and
            category == "جميع القنوات" and
            channel_type == "كل الأنواع" and
            quality == "كل الجودات" and
            scramble == "كل الحمايات" and
            locked == "كل الحالات" and
            epg == "كل الحالات"):

            # إظهار جميع الصفوف
            for row in range(self.channel_table.rowCount()):
                self.channel_table.setRowHidden(row, False)
            return

        # تطبيق التصفية على كل صف
        for row in range(self.channel_table.rowCount()):
            # الحصول على بيانات الصف
            name_item = self.channel_table.item(row, 1)
            channel_name = name_item.text().lower() if name_item else ""

            fav_item = self.channel_table.item(row, 0)
            is_favorite = fav_item.checkState() == Qt.CheckState.Checked if fav_item else False

            type_item = self.channel_table.item(row, 4)
            channel_type_val = type_item.text() if type_item else ""

            quality_item = self.channel_table.item(row, 5)
            quality_val = quality_item.text() if quality_item else ""

            scramble_item = self.channel_table.item(row, 6)
            scramble_val = scramble_item.text() if scramble_item else ""

            lock_item = self.channel_table.item(row, 7)
            lock_val = lock_item.text() if lock_item else ""

            epg_item = self.channel_table.item(row, 8)
            epg_val = epg_item.text() if epg_item else ""

            playing_item = self.channel_table.item(row, 14)
            is_playing = playing_item.text() == "نعم" if playing_item else False

            # تطبيق معايير التصفية
            name_match = not search_text or search_text in channel_name

            category_match = True
            if category == "المفضلة":
                category_match = is_favorite
            elif category == "قيد التشغيل فقط":
                category_match = is_playing

            type_match = True
            if channel_type == "تلفاز":
                type_match = channel_type_val == "تلفاز"
            elif channel_type == "راديو":
                type_match = channel_type_val == "راديو"

            quality_match = True
            if quality == "HD":
                quality_match = quality_val == "HD"
            elif quality == "SD":
                quality_match = quality_val == "SD"

            scramble_match = True
            if scramble == "مشفرة":
                scramble_match = scramble_val == "مشفرة"
            elif scramble == "مفتوحة":
                scramble_match = scramble_val == "مفتوحة"

            lock_match = True
            if locked == "مقفولة":
                lock_match = lock_val == "نعم"
            elif locked == "غير مقفولة":
                lock_match = lock_val == "لا"

            epg_match = True
            if epg == "بدون دعم EPG":
                epg_match = epg_val == "لا"
            elif epg == "بدعم EPG":
                epg_match = epg_val == "نعم"

            # تحديد إذا كان يجب إظهار الصف أم لا
            show_row = (name_match and category_match and type_match and
                       quality_match and scramble_match and lock_match and epg_match)

            self.channel_table.setRowHidden(row, not show_row)

    def clear_all_filters(self):
        """إعادة تعيين جميع عوامل التصفية وعرض جميع القنوات"""
        # إعادة تعيين عناصر التحكم
        self.search_input.clear()
        self.category_filter.setCurrentIndex(0)  # جميع القنوات
        self.type_filter.setCurrentIndex(0)      # كل الأنواع
        self.quality_filter.setCurrentIndex(0)   # كل الجودات
        self.scramble_filter.setCurrentIndex(0)  # كل الحمايات
        self.lock_filter.setCurrentIndex(0)      # كل الحالات
        self.epg_filter.setCurrentIndex(0)       # كل الحالات

        # عرض جميع الصفوف
        for row in range(self.channel_table.rowCount()):
            self.channel_table.setRowHidden(row, False)
        self.setup_cell_tooltips()

        self.update_output("تم إلغاء جميع عوامل التصفية وعرض جميع القنوات")
    def toggle_advanced_filters(self, enabled):
        self.type_filter.setEnabled(enabled)
        self.quality_filter.setEnabled(enabled)
        self.scramble_filter.setEnabled(enabled)
        self.lock_filter.setEnabled(enabled)
        self.epg_filter.setEnabled(enabled)
        self.setup_cell_tooltips()

    def update_stats(self):
        """ ✨ دالة معدلة: تحديث جميع الإحصائيات بما في ذلك شريط الحالة """
        total_channels = len(self.channels)
        total_favorites = len(self.favorites)
        total_devices = len(self.connected_devices)
    
        # تحديث التسميات في تبويب "الإعدادات"
        self.total_channels_label.setText(str(total_channels))
        self.favorite_channels_label.setText(str(total_favorites))
        self.connected_devices_label.setText(str(total_devices))
        
        # ✨ تحديث التسميات في شريط الحالة السفلي
        self.channel_count_label.setText(f"إجمالي القنوات: {total_channels}")
        self.favorite_count_label.setText(f"المفضلة: {total_favorites}")
        self.device_count_label.setText(f"الأجهزة المحفوظة: {total_devices}")
    
        self.setup_cell_tooltips()

    @pyqtSlot(QTableWidgetItem, QTableWidgetItem)
    def update_channel_action_buttons_state(self, current_item=None, previous_item=None):
        is_enabled = False
        if self.connected and self.channel_table.currentRow() >= 0:
            selected_row = self.channel_table.currentRow()
            service_id_item = self.channel_table.item(selected_row, 2)
            if service_id_item and service_id_item.text() and service_id_item.text() != '؟؟؟':
                is_enabled = True

        self.goto_channel_btn.setEnabled(is_enabled)
        self.play_vlc_btn.setEnabled(is_enabled)
        self.record_btn.setEnabled(is_enabled)
        if self.connected:
            self.update_all_urls_btn.setEnabled(self.channel_table.rowCount() > 0 and not self.is_fetching_all and not self.is_updating_all_urls)


    @pyqtSlot(QTableWidgetItem)
    def handle_favorite_click(self, item: QTableWidgetItem):
        if item.column() == 0:
            row_index = item.row()
            service_id_item = self.channel_table.item(row_index, 2)
            if not service_id_item: return

            service_id = service_id_item.text()
            if not service_id or service_id == '؟؟؟': return

            if item.checkState() == Qt.CheckState.Checked:
                if service_id not in self.favorites: self.favorites.append(service_id)
            else:
                if service_id in self.favorites: self.favorites.remove(service_id)

            self.settings_manager.save_favorites(self.favorites)
            self.update_stats()
            if self.category_filter.currentText() == "المفضلة":
                self.filter_channels()

    @pyqtSlot(QTableWidgetItem)
    def channel_selected(self, item: QTableWidgetItem):
        if not self.connected:
            self.update_output("⚠️ يرجى الاتصال بالرسيفر أولاً.")
            return
    
        row_index = item.row()
    
        try:
            self.send_row_number(row_index)
            self.update_playing_column(row_index)
        except Exception as e:
            self.update_output(f"❌ فشل في تنفيذ التسلسل: {str(e)}")
    def send_row_number(self, row_index):
        if not self.connected:
            return
    
        current_row = row_index
        service_id_item = self.channel_table.item(current_row, 2)
        channel_name_item = self.channel_table.item(current_row, 1)
        service_index_item = self.channel_table.item(current_row, 16)  # العمود 23
    
        if service_id_item and channel_name_item:
            service_id = service_id_item.text()
            channel_name = channel_name_item.text()
            old_url = self.channel_table.item(current_row, 3).text() if self.channel_table.item(current_row, 3) else ""
    
            if not service_index_item or not service_index_item.text().isdigit():
                self.update_output(f"⚠️ ServiceIndex غير صالح أو مفقود للقناة: '{channel_name}'")
                return
    
            service_index = service_index_item.text()
    
            if service_id and service_id != '؟؟؟':
                self.last_requested_service_id_for_url = service_id
                try:
                    change_cmd_body = f'{{"request":"1009", "TvState":"0", "ProgramId":"{service_id}"}}'
                    change_message = build_message(change_cmd_body)
                    self.network_thread.send_command(change_message)
                    self.update_output(f"📺 أمر الانتقال إلى: {channel_name} (ID: {service_id})")
                except Exception as e:
                    self.update_output(f"❌ خطأ إرسال أمر تغيير القناة: {e}")
                    return
            else:
                self.update_output(f"⚠️ معرف الخدمة غير صالح للقناة المحددة: '{channel_name}'.")
                return
        else:
            self.update_output("⚠️ لم يتم العثور على بيانات القناة للصف المحدد.")
            return
    
        digits = list(str(service_index))
        self.update_output(f"🔢 إرسال ServiceIndex {service_index}...")
        for digit in digits:
            if digit in self.DIGIT_COMMAND_MAP:
                key_code = self.DIGIT_COMMAND_MAP[digit]
                self.send_key(key_code)
                QApplication.processEvents()
                time.sleep(0.4)
    
        QTimer.singleShot(3000, lambda: self.show_action_report(
            channel_name=channel_name,
            service_id=service_id,
            row_number=service_index,  # ✅ استخدم ServiceIndex بدل row_index + 1
            old_url=old_url,
            new_url=self.channel_table.item(current_row, 3).text() if self.channel_table.item(current_row, 3) else ""
        ))
    def show_action_report(self, channel_name, service_id, row_number, old_url, new_url):
        log_report = f"""
        [تقرير تنفيذ الإجراءات - {time.strftime("%H:%M:%S")}]
        القناة: {channel_name}
        رقم القناة: {row_number}
        معرف الخدمة: {service_id}
    
        التغييرات:
        - {'تم تغيير رابط البث' if old_url != new_url else 'لم يتم تغيير رابط البث'}
        - الرابط القديم: {old_url if old_url else 'غير متوفر'}
        - الرابط الجديد: {new_url if new_url else 'غير متوفر'}
    
        الإجراءات المنفذة:
        1. تم إرسال أمر تغيير القناة باستخدام معرف الخدمة
        2. تم إرسال رقم القناة {row_number} عبر الأزرار الرقمية
        3. تم تحديث حالة القناة في الواجهة
        """
        self.update_output(log_report)
    
        msg_report = f"""
        <html>
        <body style="font-family: Arial; font-size: 12pt;">
        <h3 style="color: #2a82da;">تقرير تنفيذ الإجراءات - {channel_name}</h3>
        <table border="0" cellpadding="5">
        <tr><td><b>🕒 الوقت:</b></td><td>{time.strftime("%H:%M:%S")}</td></tr>
        <tr><td><b>🎬 القناة:</b></td><td>{channel_name}</td></tr>
        <tr><td><b>🔢 الرقم:</b></td><td>{row_number}</td></tr>
        <tr><td><b>🆔 المعرف:</b></td><td>{service_id}</td></tr>
        </table>
    
        <h4 style="color: #2a82da; margin-top: 10px;">التغييرات</h4>
        <table border="0" cellpadding="5">
        <tr><td><b>حالة الرابط:</b></td><td style="color: {'green' if old_url != new_url else 'gray'}">
            {'تم التحديث' if old_url != new_url else 'بدون تغيير'}
        </td></tr>
        <tr><td><b>الرابط القديم:</b></td><td>{old_url if old_url else 'غير متوفر'}</td></tr>
        <tr><td><b>الرابط الجديد:</b></td><td><a href="{new_url if new_url else '#'}" style="color: blue; text-decoration: underline;">{new_url if new_url else 'غير متوفر'}</a></td></tr>
        </table>
    
        <h4 style="color: #2a82da; margin-top: 10px;">الإجراءات</h4>
        <ol>
        <li>إرسال أمر تغيير القناة (ID: {service_id})</li>
        <li>إرسال رقم القناة: {row_number}</li>
        <li>تحديث حالة الواجهة</li>
        </ol>
        </body>
        </html>
        """
    
        # إعداد الرسالة
        msg = QMessageBox(self)
        msg.setWindowTitle(f"تقرير التنفيذ - {channel_name}")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(msg_report)
        msg.setIcon(QMessageBox.Icon.Information)
    
        # إضافة الأزرار
        if new_url:
            # زر فتح في VLC
            open_vlc_btn = msg.addButton("فتح في VLC", QMessageBox.ButtonRole.ActionRole)
            open_vlc_btn.clicked.connect(lambda: self.open_vlc(new_url, channel_name))
            
            # زر تشغيل المدمج
            open_embedded_btn = msg.addButton("تشغيل المدمج", QMessageBox.ButtonRole.ActionRole)
            open_embedded_btn.clicked.connect(lambda: self.play_selected_embedded_with_url(new_url, channel_name))
    
        cancel_btn = msg.addButton("إلغاء", QMessageBox.ButtonRole.RejectRole)
        msg.addButton(QMessageBox.StandardButton.Ok)
    
        msg.exec()
    def play_selected_embedded_with_url(self, url: str, channel_name: str):
        """تشغيل القناة في المشغل المدمج باستخدام الرابط المحدد"""
        try:
            if self.embedded_instance is None:
                self.embedded_instance = vlc.Instance()
    
            if self.embedded_player:
                self.embedded_player.stop()
                self.embedded_player.release()
    
            self.embedded_player = self.embedded_instance.media_player_new()
            media = self.embedded_instance.media_new(url)
            self.embedded_player.set_media(media)
    
            if not self.embedded_frame.winId():
                self.embedded_frame.show()
                QApplication.processEvents()
    
            if sys.platform.startswith("linux"):
                self.embedded_player.set_xwindow(self.embedded_frame.winId())
            elif sys.platform == "win32":
                self.embedded_player.set_hwnd(int(self.embedded_frame.winId()))
            elif sys.platform == "darwin":
                self.embedded_player.set_nsobject(int(self.embedded_frame.winId()))
    
            self.embedded_player.play()
            self.update_output(f"▶️ تشغيل المدمج: {channel_name}")
    
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل تشغيل VLC المدمج:\n{e}")
            self.update_output(f"❌ فشل تشغيل المدمج: {e}")    
        # إغلاق الرسالة بعد الضغط على الزر
    def update_playing_column(self, selected_row):
        for row in range(self.channel_table.rowCount()):
            playing_item = self.channel_table.item(row, 14)
            if playing_item:
                if row == selected_row:
                    playing_item.setText("نعم")
                else:
                    playing_item.setText("لا")
    def open_vlc(self, stream_url, channel_name):
        vlc_path = self.vlc_path_input.text().strip()
        if not vlc_path or not os.path.exists(vlc_path):
            common_paths = [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
            ]
            for path in common_paths:
                if os.path.exists(path):
                    vlc_path = path
                    break

        if vlc_path and os.path.exists(vlc_path):
            try:
                subprocess.Popen([vlc_path, stream_url, f"--meta-title={channel_name}"])
                self.update_output(f"🎬 تشغيل القناة في VLC: {channel_name}")
            except Exception as e:
                self.update_output(f"❌ فشل في تشغيل VLC: {e}")
                QMessageBox.warning(self, "خطأ", f"فشل في تشغيل VLC:\n{e}")
        else:
            QMessageBox.warning(self, "خطأ", "لم يتم العثور على مسار VLC الصحيح!")

    def send_goto_channel(self, row_index):
        self.channel_table.selectRow(row_index)

        self.go_to_selected_channel()

    def send_play_vlc(self, row_index):
        self.channel_table.selectRow(row_index)

        self.play_selected_in_vlc()

    def go_to_selected_channel(self):
        if not self.connected or not self.network_thread or not self.network_thread.isRunning():
            QMessageBox.warning(self, "غير متصل", "يرجى الاتصال بالجهاز أولاً.")
            return

        current_row = self.channel_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "تنبيه", "لم يتم تحديد قناة في الجدول.")
            return

        service_id_item = self.channel_table.item(current_row, 2)
        channel_name_item = self.channel_table.item(current_row, 1)

        if service_id_item and channel_name_item:
            service_id = service_id_item.text()
            channel_name = channel_name_item.text()

            if service_id and service_id != '؟؟؟':
                self.last_requested_service_id_for_url = service_id
                self.change_channel(service_id, channel_name)
            else:
                self.update_output(f"⚠️ معرف الخدمة غير صالح للقناة المحددة: '{channel_name}'.")
        else:
            self.update_output("⚠️ لم يتم العثور على بيانات القناة للصف المحدد.")

    def change_channel(self, service_id: str, channel_name: str):
        try:
            change_cmd_body = f'{{"request":"1009", "TvState":"0", "ProgramId":"{service_id}"}}'
            change_message = build_message(change_cmd_body)
            self.network_thread.send_command(change_message)
            self.update_output(f"📺 أمر الانتقال إلى: {channel_name} (ID: {service_id})")
        except Exception as e:
            self.update_output(f"❌ خطأ إرسال أمر تغيير القناة: {e}")

    def play_selected_in_vlc(self):
        current_row = self.channel_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "تنبيه", "يرجى تحديد قناة من الجدول لتشغيلها.")
            return

        channel_name_item = self.channel_table.item(current_row, 1)
        url_item = self.channel_table.item(current_row, 3)

        channel_name = channel_name_item.text() if channel_name_item else "قناة غير معروفة"
        stream_url = url_item.text() if url_item and url_item.text() else ""

        if stream_url:
            self.update_output(f"🎬 محاولة تشغيل '{channel_name}' في VLC ({stream_url})...")

            vlc_path = self.vlc_path_input.text().strip()
            if not vlc_path or not os.path.exists(vlc_path):
                # محاولة إيجاد VLC في المسارات الشائعة
                common_paths = [r"C:\Program Files\VideoLAN\VLC\vlc.exe", r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"]
                vlc_found = False
                for p_val in common_paths:
                    if os.path.exists(p_val):
                        vlc_path = p_val
                        vlc_found = True
                        break
                if not vlc_found:
                    QMessageBox.warning(self, "خطأ VLC", f"لم يتم العثور على VLC في '{vlc_path}'. يرجى تحديد المسار الصحيح في الإعدادات.")
                    return
            try:
                subprocess.Popen([vlc_path, stream_url, f"--meta-title={channel_name}"])
            except Exception as e:
                self.update_output(f"❌ فشل في تشغيل VLC: {e}")
                QMessageBox.critical(self, "خطأ VLC", f"فشل في تشغيل VLC: {e}")
        else:
            QMessageBox.information(self, "تنبيه", f"لا يوجد رابط بث متاح للقناة '{channel_name}'.\nقد تحتاج لتحديثه أولاً (مثلاً بالانتقال للقناة على الجهاز أو استخدام زر 'تحديث روابط البث للكل').")


    # def play_selected_embedded(self):
        # QMessageBox.information(self, "غير متوفر", "ميزة التشغيل المدمج غير متوفرة حالياً.")

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.mute_btn.setText("إلغاء كتم الصوت 🔊")  # تغيير النص عند كتم الصوت
            # كتم الصوت في مشغل VLC
            if self.embedded_player:
                self.embedded_player.audio_set_mute(True)
        else:
            self.mute_btn.setText("كتم الصوت 🔇")  # تغيير النص عند إلغاء كتم الصوت
            # إلغاء كتم الصوت في مشغل VLC
            if self.embedded_player:
                self.embedded_player.audio_set_mute(False)
    def expand_embedded_player(self):
        heights = [500, 600, 700, 300]  # قائمة بالارتفاعات
        current_index = heights.index(self.embedded_frame.minimumHeight()) if self.embedded_frame.minimumHeight() in heights else 0
        
        # تحديث الارتفاع
        new_index = (current_index + 1) % len(heights)
        self.embedded_frame.setMinimumHeight(heights[new_index])
        
        # تحديث نص الزر
        if new_index == 0:
            self.expand_embedded_btn.setText("تكبير  ⏹️")
        elif new_index == 1:
            self.expand_embedded_btn.setText("تكبير  ⏹️")
        elif new_index == 2:
            self.expand_embedded_btn.setText("تصغير  ⏹️")
        else:
            self.expand_embedded_btn.setText("تكبير  ⏹️")
    
        # تحديث حالة is_expanded
        self.is_expanded = (new_index == 3)  # إذا كان في الحالة الأخيرة، اعتبره متمددًا
        
    # def expand_embedded_player(self):
        # if self.is_expanded:
            # self.embedded_frame.setMinimumHeight(300)
            # self.expand_embedded_btn.setText("تكبير  ⏹️")
        # else:
            # self.embedded_frame.setMinimumHeight(600)  # ارتفاع أكبر عند التكبير
            # self.expand_embedded_btn.setText("تصغير")
        # self.is_expanded = not self.is_expanded
        
    def toggle_embedded_frame(self):
        if self.embedded_frame.isVisible():
            self.embedded_frame.hide()
            self.toggle_embedded_btn.setText("اظهار المشغل المدمج")
        else:
            self.embedded_frame.show()
            self.toggle_embedded_btn.setText("إخفاء االمشغل المدمج")
    def play_selected_embedded(self):
        from PyQt6.QtWidgets import QApplication
    
        selected_items = self.channel_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "تحذير", "يرجى اختيار قناة أولاً")
            return
    
        url = self.channel_table.item(selected_items[0].row(), 3).text().strip()
        if not url:
            QMessageBox.warning(self, "تحذير", "رابط القناة فارغ")
            return
    
        try:
            if self.embedded_instance is None:
                self.embedded_instance = vlc.Instance()
    
            if self.embedded_player:
                self.embedded_player.stop()
                self.embedded_player.release()
    
            self.embedded_player = self.embedded_instance.media_player_new()
            media = self.embedded_instance.media_new(url)
            self.embedded_player.set_media(media)
    
            if not self.embedded_frame.winId():
                self.embedded_frame.show()
                QApplication.processEvents()
    
            if sys.platform.startswith("linux"):
                self.embedded_player.set_xwindow(self.embedded_frame.winId())
            elif sys.platform == "win32":
                self.embedded_player.set_hwnd(int(self.embedded_frame.winId()))
            elif sys.platform == "darwin":
                self.embedded_player.set_nsobject(int(self.embedded_frame.winId()))
    
            self.embedded_player.play()
    
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل تشغيل VLC المدمج:\n{e}")
    def stop_embedded_player(self):
        if hasattr(self, 'embedded_player') and self.embedded_player:
            try:
                self.embedded_player.stop()
                self.update_output("⏹️ تم إيقاف البث المدمج.")
                # self.stop_embedded_btn.setEnabled(False)
            except Exception as e:
                self.update_output(f"❌ فشل في إيقاف التشغيل المدمج: {str(e)}")

    
        
    def record_channel(self):
        current_row = self.channel_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "تنبيه", "يرجى تحديد قناة للتسجيل.")
            return

        channel_name_item = self.channel_table.item(current_row, 1)
        url_item = self.channel_table.item(current_row, 3)

        channel_name = channel_name_item.text() if channel_name_item else "غير معروف"
        stream_url = url_item.text() if url_item and url_item.text() else ""

        if not stream_url:
            QMessageBox.information(self, "تنبيه", "لا يوجد رابط بث متاح للتسجيل.")
            return

        record_path_dir = self.record_path_input.text().strip()
        if not record_path_dir or not os.path.isdir(record_path_dir):
            record_path_dir = os.path.expanduser("~/Videos")
            os.makedirs(record_path_dir, exist_ok=True)
            self.record_path_input.setText(record_path_dir)

        safe_name = "".join(c for c in channel_name if c.isalnum() or c in " _-").strip() or "recording"
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_file = os.path.join(record_path_dir, f"{safe_name}_{timestamp}.ts")

        vlc_path = self.vlc_path_input.text().strip()
        if not vlc_path or not os.path.exists(vlc_path):
             QMessageBox.warning(self, "خطأ VLC", "مسار VLC غير صحيح أو غير موجود. يرجى التحقق من الإعدادات.")
             return

        duration, ok = QInputDialog.getInt(self, "مدة التسجيل", "أدخل مدة التسجيل بالثواني:", 600, 300, 72000, 600)
        if not ok: return

        try:
            cmd = [vlc_path, stream_url, "--sout", f"#std{{access=file,mux=ts,dst='{output_file}'}}", f"--run-time={duration}", "vlc://quit"]
            subprocess.Popen(cmd)
            self.update_output(f"⏺️ بدء تسجيل '{channel_name}' لمدة {duration} ثانية إلى: {output_file}")
        except Exception as e:
            self.update_output(f"❌ فشل بدء التسجيل: {e}")
            QMessageBox.critical(self, "خطأ تسجيل", f"فشل بدء التسجيل: {e}")


    def recordMP4TS_channel(self):
        current_row = self.channel_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "تنبيه", "يرجى تحديد قناة للتسجيل.")
            return
    
        # اختيار صيغة التسجيل
        formats = {"MP4": "mp4", "TS": "ts"}
        format_choice, ok = QInputDialog.getItem(
            self,
            "اختيار صيغة التسجيل",
            "اختر صيغة ملف التسجيل:",
            list(formats.keys()),
            0,
            False
        )
        
        if not ok:
            return  # تم الضغط على إلغاء
        
        selected_format = formats[format_choice]
    
        channel_name_item = self.channel_table.item(current_row, 1)
        url_item = self.channel_table.item(current_row, 3)
    
        channel_name = channel_name_item.text() if channel_name_item else "غير معروف"
        stream_url = url_item.text() if url_item and url_item.text() else ""
    
        if not stream_url:
            QMessageBox.information(self, "تنبيه", "لا يوجد رابط بث متاح للتسجيل.")
            return
    
        record_path_dir = self.record_path_input.text().strip()
        if not record_path_dir or not os.path.isdir(record_path_dir):
            record_path_dir = os.path.expanduser("~/Videos")
            os.makedirs(record_path_dir, exist_ok=True)
            self.record_path_input.setText(record_path_dir)
    
        safe_name = "".join(c for c in channel_name if c.isalnum() or c in " _-").strip() or "recording"
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_file = os.path.join(record_path_dir, f"{safe_name}_{timestamp}.{selected_format}")
    
        vlc_path = self.vlc_path_input.text().strip()
        if not vlc_path or not os.path.exists(vlc_path):
            QMessageBox.warning(self, "خطأ VLC", "مسار VLC غير صحيح أو غير موجود. يرجى التحقق من الإعدادات.")
            return
    
        duration, ok = QInputDialog.getInt(self, "مدة التسجيل", "أدخل مدة التسجيل بالثواني:", 300, 10, 7200, 60)
        if not ok:
            return
    
        try:
            if selected_format == "mp4":
                cmd = [
                    vlc_path,
                    stream_url,
                    "--sout",
                    f"#transcode{{vcodec=h264,acodec=mp4a}}:std{{access=file,mux=mp4,dst='{output_file}'}}",
                    f"--run-time={duration}",
                    "vlc://quit"
                ]
            else:  # TS
                cmd = [
                    vlc_path,
                    stream_url,
                    "--sout",
                    f"#std{{access=file,mux=ts,dst='{output_file}'}}",
                    f"--run-time={duration}",
                    "vlc://quit"
                ]
            
            subprocess.Popen(cmd)
            self.update_output(f"⏺️ بدء تسجيل '{channel_name}' لمدة {duration} ثانية بصيغة {format_choice} إلى: {output_file}")
        except Exception as e:
            self.update_output(f"❌ فشل بدء التسجيل: {e}")
            QMessageBox.critical(self, "خطأ تسجيل", f"فشل بدء التسجيل: {e}")


    def send_key(self, key_value: str):
        if not self.connected or not self.network_thread or not self.network_thread.isRunning():
            self.update_output("⚠️ لم يتم إرسال المفتاح، الجهاز غير متصل.")
            return

        try:
            msg_body = f'{{"array":[{{"KeyValue":"{key_value}"}}],"request":"1040"}}'
            full_message = build_message(msg_body)
            self.network_thread.send_command(full_message)
            self.update_output(f"↗️ إرسال مفتاح: {key_value}")
        except Exception as e:
            self.update_output(f"❌ خطأ إرسال مفتاح {key_value}: {e}")

    def handle_go_button_click(self):
        if not self.connected:
            QMessageBox.warning(self, "غير متصل", "يرجى الاتصال بالجهاز أولاً.")
            return

        digit_text = self.digit_input.text().strip()
        if not digit_text.isdigit():
            QMessageBox.warning(self, "خطأ إدخال", "يرجى إدخال أرقام فقط.")
            return

        for digit in digit_text:
            if digit in self.DIGIT_COMMAND_MAP:
                key_code = self.DIGIT_COMMAND_MAP[digit]
                self.update_output(f"🔢 إرسال رقم '{digit}' (كود {key_code})...")
                self.send_key(key_code)
                QApplication.processEvents()
                time.sleep(0.3)

    def send_custom_command(self):
        if not self.connected or not self.network_thread or not self.network_thread.isRunning():
            QMessageBox.warning(self, "غير متصل", "يرجى الاتصال بالجهاز أولاً.")
            return

        cmd_text = self.custom_cmd_input.text().strip()
        if not cmd_text:
            QMessageBox.warning(self, "خطأ إدخال", "يرجى إدخال أمر JSON مخصص.")
            return

        try:
            json.loads(cmd_text)
            full_message = build_message(cmd_text)
            self.network_thread.send_command(full_message)
            self.update_output(f"↗️ إرسال أمر مخصص: {cmd_text}")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "خطأ JSON", "نص الأمر غير صالح (ليس JSON صحيح).")
        except Exception as e:
            self.update_output(f"❌ خطأ إرسال أمر مخصص: {e}")

    def browse_vlc_path(self):
        path, _ = QFileDialog.getOpenFileName(self, "حدد مسار VLC", self.vlc_path_input.text(), "ملفات تنفيذية (*.exe);;All Files (*)")
        if path:
            self.vlc_path_input.setText(path)
            self.settings_manager.settings.setValue("vlc_path", path)

    def browse_record_path(self):
        path = QFileDialog.getExistingDirectory(self, "حدد مجلد التسجيلات", self.record_path_input.text())
        if path:
            self.record_path_input.setText(path)
            self.settings_manager.settings.setValue("record_path", path)

    def backup_settings(self):
        path, _ = QFileDialog.getSaveFileName(self, "حفظ النسخة الاحتياطية", os.path.expanduser("~/starsat_backup.json"), "JSON files (*.json)")
        if path:
            self.settings_manager.save_window_state(self)
            self.settings_manager.save_device_settings(self.ip_input.text().strip(), self.port_input.text().strip())
            self.settings_manager.settings.setValue("vlc_path", self.vlc_path_input.text())
            self.settings_manager.settings.setValue("record_path", self.record_path_input.text())
            self.settings_manager.save_channels(self.channels)
            self.settings_manager.save_favorites(self.favorites)
            self.settings_manager.settings.setValue("connected_devices", self.connected_devices)

            if self.settings_manager.backup_settings(path):
                QMessageBox.information(self, "نجاح", f"تم حفظ النسخة الاحتياطية في:\n{path}")
            else:
                QMessageBox.critical(self, "فشل", "فشل في إنشاء النسخة الاحتياطية.")

    def restore_settings(self):
        path, _ = QFileDialog.getOpenFileName(self, "استعادة النسخة الاحتياطية", os.path.expanduser("~/"), "JSON files (*.json)")
        if path:
            if self.settings_manager.restore_settings(path):
                self.settings_manager.restore_window_state(self)
                self.load_device_settings()
                self.apply_ui_settings()
                self.update_stats()
                QMessageBox.information(self, "نجاح", f"تم استعادة الإعدادات من:\n{path}\nقد تحتاج لإعادة تشغيل البرنامج لتطبيق كافة التغييرات.")
            else:
                QMessageBox.critical(self, "فشل", "فشل في استعادة النسخة الاحتياطية.")

    def reset_settings(self):
        reply = QMessageBox.question(self, "استعادة الافتراضيات", "هل أنت متأكد أنك تريد استعادة جميع الإعدادات إلى قيمها الافتراضية؟", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.repair_settings()
            self.settings_manager.restore_window_state(self)
            self.load_device_settings()
            self.apply_ui_settings()
            self.update_stats()
            QMessageBox.information(self, "نجاح", "تم استعادة الإعدادات الافتراضية.")
            self.setup_cell_tooltips()

    @pyqtSlot()
    def handle_connected(self):
        self.update_output("✅✅✅ الاتصال بالجهاز مكتمل وجاهز للاستخدام.")

    @pyqtSlot()
    def handle_disconnected(self):
        self.update_output("🔌 تم قطع الاتصال بالجهاز.")
        if self.network_thread and not self.network_thread.isRunning():
            self.network_thread.quit()
            self.network_thread.wait(500)
            self.network_thread = None

    @pyqtSlot(str)
    def update_output(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.output.append(f"[{timestamp}] {message}")
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())
        logging.info(message)

    def show_about(self):
        QMessageBox.about(self, "حول البرنامج",
            "<p>برنامج تحكم ستارسات مع قائمة القنوات و VLC</p>"
            "<p> الإصدار : 2.2.5</p>"
            "<p>برنامج مفتوح المصدر للتحكم بأجهزة استقبال ستارسات.</p>"
            "<p> المطور</p>"
            "<p>المطور: <a href='mailto:fahedali19899@gmail.com'>fahedali19899@gmail.com</a></p>"
            "<p>موقع تونيزياسات</p>"              
            "<p><a href='https://www.tunisia-sat.com/'>منتدى تونيزياسات - دعم واستقبال الأقمار</a></p>"           
            "<p>موقع Mango</p>"           
            "<p><a href='https://www.metamango.org/#/home'>موقع Mango - دعم واستقبال القنوات</a></p>"
            "<p>موقع معرفة الاشتراك السيرفرات</p>" 
            "<p><a href='https://check.dzagame.com/'>تحقق من SN - dzagame.com</a></p>"
            "<p>مواقع تحديثات</p>"           
            "<p><a href='https://satdl.com/'>موقع satdl.com - تخزين ومشاركة ملفات الأجهزة</a></p>"
            "<p><a href='http://cwdw.net/'>تحميل أحدث برامج الإقلاع والتحديثاتcwdw</a></p>"
            "<p><a href='https://starsatsoftware.com/  '>اشترك في تحديثات Starsat Software</a></p>"
            "<p><a href='https://dishdl.com/'>أكواد IKS، وبرامج الأجهزة المدعومةdishdl</a></p>"
            "<p><a href='https://satdw.org/'>آخر التحديثات satdwللأجهزة مثل PREMIUM وiBOX وSENATOR</a></p>"
            "<p><a href='https://swdw.net/'>برامج واستقبال الأجهزة - swdw.net</a></p>"
            "<p><a href='https://swmediastars.com/'>موقع swmediastars.com - تحديثات Mediastar</a></p>"
            "<p><a href='https://mediastar.co/'>موقع mediastar.co - تطويرات الأجهزة الاستقبال</a></p>") 



    def show_help(self):
        help_file_name = "help_document.txt"
        help_text_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), help_file_name)

        if not os.path.exists(help_text_path):
            default_help_text = (
                "مستند المساعدة لبرنامج تحكم ستارسات.\n\n"
                "1. الاتصال: أدخل IP ومنفذ الجهاز ثم اضغط 'اتصال'.\n"
                "   يمكنك حفظ الأجهزة المتصلة بها بشكل متكرر.\n\n"
                "2. القنوات: \n"
                "   - 'جلب أول X قناة': لتحميل دفعة أولى من القنوات.\n"
                "   - 'جلب جميع القنوات': لتحميل كافة القنوات.\n"
                "   - 'تحديث روابط البث للكل': لمحاولة تحديث روابط البث لجميع القنوات في الجدول (قد يغير القناة على التلفاز بشكل متتالٍ).\n"
                "   - انقر نقراً مزدوجاً على قناة للانتقال إليها على جهاز الاستقبال.\n"
                "   - استخدم مربع البحث والتصنيف لتصفية القنوات.\n"
                "   - ضع علامة ⭐ لإضافة قناة للمفضلة.\n\n"
                "3. تشغيل VLC: \n"
                "   - حدد قناة من الجدول.\n"
                "   - اضغط 'انتقال للقناة المحددة ▶️' لتأكيد القناة على الجهاز (يساعد في تحديث رابط البث).\n"
                "   - ثم اضغط 'تشغيل VLC 🎬'.\n"
                "   - تأكد من صحة مسار برنامج VLC في علامة تبويب 'الإعدادات'.\n\n"
                "4. الإعدادات:\n"
                "   - قم بتخصيص مظهر البرنامج (الوضع الليلي، حجم الخط).\n"
                "   - حدد مسارات برنامج VLC ومجلد حفظ التسجيلات.\n"
                "  "
            )
            try:
                with open(help_text_path, "w", encoding="utf-8") as f:
                    f.write(default_help_text)
                self.update_output(f"تم إنشاء ملف مساعدة افتراضي: {help_text_path}")
            except Exception as e:
                QMessageBox.warning(self, "خطأ", f"فشل في إنشاء ملف المساعدة: {e}")
                return

        try:
            if sys.platform == 'win32': os.startfile(help_text_path)
            elif sys.platform == 'darwin': subprocess.call(['open', help_text_path])
            else: subprocess.call(['xdg-open', help_text_path])
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"فشل في فتح ملف المساعدة '{help_file_name}': {e}\nتأكد من وجوده في مجلد البرنامج.")

    
    def get_favorite_group_names(self, fav_bit: int) -> list:
        """تحويل قيمة FavBit إلى أسماء المجموعات المفضلة"""
        if not self.favorite_groups or fav_bit == 0:
            return []
        
        group_names = []
        # تحويل الرقم إلى ثنائي لتحديد المجموعات المختارة
        # مثال: إذا كان fav_bit = 5 (ثنائي: 101) فهذا يعني المجموعتين 1 و 3
        binary_str = bin(fav_bit)[2:]  # إزالة '0b' من البداية
        binary_str = binary_str.zfill(len(self.favorite_groups))  # إضافة أصفار لجعل الطول متساوي
        
        # قراءة البتات من اليمين لليسار (أقل بت يمثل المجموعة الأولى)
        for i, bit in enumerate(reversed(binary_str)):
            if bit == '1' and i < len(self.favorite_groups):
                group_names.append(self.favorite_groups[i])
        
        return group_names

    def channel_selected_action(self):
        current_item = self.channel_table.currentItem()
        if current_item:
            self.channel_selected(current_item)

    def toggle_auto_reconnect(self, state):
        """تفعيل/تعطيل إعادة الاتصال التلقائي"""
        self.auto_reconnect = self.auto_reconnect_checkbox.isChecked()
        if self.network_thread:
            self.network_thread.max_reconnect_attempts = 5 if self.auto_reconnect else 0
        self.update_output(f"♻️ إعادة الاتصال التلقائي: {'مفعل' if self.auto_reconnect else 'معطل'}")  

        
    @pyqtSlot()
    def on_connected(self):
        if self.fetch_channels_checkbox.isChecked():  # تحقق من حالة QCheckBox
           QTimer.singleShot(5000, self.ask_to_fetch_channels)

           # QTimer.singleShot(5000, self.ask_to_fetch_channels)

    def ask_to_fetch_channels(self):
        reply = QMessageBox.question(
            self,
            "تأكيد جلب القنوات",
            "هل تريد جلب القنوات الآن؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.perform_post_connection_tasks()
        else:
            self.update_output("❗ تم إلغاء جلب القنوات بناءً على طلب المستخدم.")

    def save_batch_size_setting(self):
        try:
            new_size = int(self.batch_size_input.text())
            if new_size > 0:
                self.batch_size = new_size
                self.settings_manager.settings.setValue("batch_size", new_size)
                self.fetch_channels_btn.setText(f"جلب أول {self.batch_size} قناة 📺تجريبي")
            else:
                self.update_output("⚠️ يجب أن يكون العدد أكبر من صفر.")
        except ValueError:
            self.update_output("⚠️ الرجاء إدخال رقم صحيح.")

    def perform_post_connection_tasks(self):
        self.fetch_and_update_all()

    def fetch_and_update_all(self):
        if not self.connected:
            QMessageBox.warning(self, "غير متصل", "يرجى الاتصال بالجهاز أولاً.")
            return

        self.update_output("🔁 بدء جلب القنوات ثم تحديث الروابط...")

        def after_fetch_done():
            self.update_output("✅ تم جلب القنوات. بدء تحديث الروابط...")
            self.update_stats()
            self.start_updating_all_urls()
            self.setup_cell_tooltips()

        self.fetch_all_btn.setEnabled(False)
        if hasattr(self, 'fetch_and_update_btn'):
            self.fetch_and_update_btn.setEnabled(False)

        self.is_fetching_all = True
        self.current_fetch_from = 0
        self.channel_table.setRowCount(0)
        self.channels = []

        self.fetch_channels_btn.setEnabled(False)
        self.update_all_urls_btn.setEnabled(False)
        self.stop_fetch_btn.setEnabled(True)

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p% - تحميل القنوات...")
        self.progress_bar.setVisible(True)
        self.setup_cell_tooltips()

        def monitor_completion():
            if not self.is_fetching_all:
                QTimer.singleShot(100, after_fetch_done)
            else:
                QTimer.singleShot(500, monitor_completion)

        self.fetch_next_batch()
        self.setup_cell_tooltips()

        monitor_completion()
        
    # تعديل دالة show_device_info
    # استبدل دالة show_device_info الحالية بهذه النسخة المحدثة بالكامل
    def show_device_info(self, device_info: dict):
        """
        تحديث معلومات الجهاز في تبويب "الإعدادات" وفي شريط الحالة السفلي.
        - تعرض معلومات مفصلة في تبويب الإعدادات.
        - تعرض معلومات مختصرة في شريط الحالة مع تلميح (tooltip) يحتوي على كافة التفاصيل.
        """
        # --- 1. تحديث التسمية التفصيلية في تبويب "الإعدادات" (مع HTML) ---
        info_html = (
            f"<b>🔹 اسم الجهاز:</b> {device_info.get('ProductName', 'غير معروف')}<br>"
            f"<b>🔹 الإصدار:</b> {device_info.get('SoftwareVersion', '؟')}<br>"
            f"<b>🔹 الرقم التسلسلي:</b> {device_info.get('SerialNumber', '؟')}<br>"
            f"<b>🔹 عدد القنوات الحالية:</b> {device_info.get('ChannelNum', '؟')}<br>"
            f"<b>🔹 الحد الأقصى للقنوات:</b> {device_info.get('MaxNumOfPrograms', '؟')}"
        )
        self.device_info_label.setText(info_html)
    
        # --- 2. تحديث التسمية والتلميح في شريط الحالة السفلي ---
    
        # استخراج كل المعلومات المطلوبة مع قيم افتراضية آمنة
        product_name = device_info.get('ProductName', 'غير معروف')
        sw_version = device_info.get('SoftwareVersion', '؟')
        serial_number = device_info.get('SerialNumber', '؟')
        channel_num = device_info.get('ChannelNum', '؟')
        max_programs = device_info.get('MaxNumOfPrograms', '؟')
    
        # إنشاء النص المختصر الذي سيظهر بشكل دائم في شريط الحالة
        status_bar_text = f"الجهاز: {product_name} | الإصدار: {sw_version}"
    
        # إنشاء النص المفصل الذي سيظهر في التلميح عند تمرير الفأرة
        tooltip_text = (
            f"اسم المنتج: {product_name}\n"
            f"إصدار البرنامج: {sw_version}\n"
            f"الرقم التسلسلي: {serial_number}\n"
            f"عدد القنوات: {channel_num}\n"
            f"الحد الأقصى للقنوات: {max_programs}"
        )
    
        # تطبيق النص المختصر والتلميح المفصل على التسمية في شريط الحالة
        self.device_info_status_label.setText(status_bar_text)
        self.device_info_status_label.setToolTip(tooltip_text)
        # self.tabs.setCurrentWidget(self.settings_tab) # يمكنك إلغاء أو إبقاء هذا السطر حسب تفضيلك        


    def context_menu_event(self, pos):
        """Display context menu on right-click"""
        menu = QMenu()
        
        # قائمة النسخ الفرعية
        copy_submenu = QMenu("📋 نسخ", self)
        copy_name_action = QAction("اسم القناة", self)
        copy_id_action = QAction("المعرف", self)
        copy_url_action = QAction("الرابط", self)
        copy_row_action = QAction("رقم الصف", self)
        
        copy_name_action.triggered.connect(lambda: self.copy_cell_content(1))  # العمود 1 لاسم القناة
        copy_id_action.triggered.connect(lambda: self.copy_cell_content(2))    # العمود 2 للمعرف
        copy_url_action.triggered.connect(lambda: self.copy_cell_content(3))   # العمود 3 للرابط
        copy_row_action.triggered.connect(lambda: self.copy_row_number())      # رقم الصف
        
        copy_submenu.addAction(copy_name_action)
        copy_submenu.addAction(copy_id_action)
        copy_submenu.addAction(copy_url_action)
        copy_submenu.addAction(copy_row_action)
        
        rename_action = QAction("📝 إعادة التسمية القناة", self)
        delete_action = QAction("🗑️ حذف القناة", self)
        move_action = QAction("↕️ نقل القناة", self)
        lock_action = QAction("🔒 قفل القناة", self)
        unlock_action = QAction("🔓 إلغاء قفل القناة", self)
        save_m3u_action = QAction("💾 حفظ كملف M3U", self)
        favorite_action = QMenu("📌 إضافة إلى المفضلة", self)    
        
        rename_action.triggered.connect(self.handle_rename_channel)
        delete_action.triggered.connect(self.handle_delete_channel)
        move_action.triggered.connect(self.handle_move_channel)
        lock_action.triggered.connect(self.handle_lock_channel)
        unlock_action.triggered.connect(self.handle_unlock_channel)
        save_m3u_action.triggered.connect(self.save_channel_as_m3u)
        favorite_groups = self.settings_manager.load_favorites()
        
        if favorite_groups:
            for group in favorite_groups:
                group_action = QAction(group, self)
                group_action.triggered.connect(lambda checked, g=group: self.add_channel_to_favorite_group(g))
                favorite_action.addAction(group_action)
        else:
            no_group_action = QAction("لا توجد مجموعات", self)
            no_group_action.setEnabled(False)
            favorite_action.addAction(no_group_action)
        
        # إضافة القائمة الفرعية للنسخ إلى القائمة الرئيسية
        menu.addMenu(copy_submenu)
        menu.addAction(rename_action)
        menu.addAction(delete_action)
        menu.addAction(move_action)
        menu.addAction(lock_action)
        menu.addAction(unlock_action)
        menu.addAction(save_m3u_action)
        menu.addMenu(favorite_action)
        
        menu.exec(self.channel_table.viewport().mapToGlobal(pos))

    def copy_cell_content(self, column: int):
        """نسخ محتوى خلية محددة"""
        row = self.channel_table.currentRow()
        if row >= 0:
            item = self.channel_table.item(row, column)
            if item and item.text():
                QApplication.clipboard().setText(item.text())
                self.update_output(f"📋 تم نسخ: {item.text()}")
            else:
                self.update_output("⚠️ لا يوجد محتوى للنسخ في الخلية المحددة")
        else:
            self.update_output("⚠️ لم يتم تحديد صف للنسخ")
    
    def copy_row_number(self):
        """نسخ رقم الصف المحدد"""
        row = self.channel_table.currentRow()
        if row >= 0:
            QApplication.clipboard().setText(str(row + 1))  # +1 لأن الصفوف تبدأ من 0
            self.update_output(f"📋 تم نسخ رقم الصف: {row + 1}")
        else:
            self.update_output("⚠️ لم يتم تحديد صف للنسخ")  
      
    def handle_rename_channel(self):
        """Handle channel rename process"""
        if not self.connected:
            QMessageBox.warning(self, "خطأ", "الاتصال غير نشط!")
            return
    
        row = self.channel_table.currentRow()
        if row < 0:
            return
    
        service_id_item = self.channel_table.item(row, 2)
        name_item = self.channel_table.item(row, 1)
    
        if not service_id_item or not name_item:
            return
    
        old_name = name_item.text()
        service_id = service_id_item.text()
    
        new_name, ok = QInputDialog.getText(
            self,
            "إعادة تسمية",
            "الاسم الجديد:",
            QLineEdit.EchoMode.Normal,
            old_name
        )
    
        if ok and new_name.strip() and new_name != old_name:
            self._update_channel_name(service_id, new_name, row)
    
    def _update_channel_name(self, service_id: str, new_name: str, row: int):
        """Update channel name locally and send to device"""
        try:
            self.channel_table.item(row, 1).setText(new_name)
    
            cmd = {
                "array": [{
                    "ProgramId": service_id,
                    "ProgramName": new_name,
                    "TvState": "0"
                }],
                "request": "1001"
            }
            self.network_thread.send_command(build_message(json.dumps(cmd)))
            self.update_output(f"♻️ تم تحديث اسم القناة إلى: {new_name}")
    
        except Exception as e:
            self.update_output(f"❌ فشل في تحديث الاسم: {str(e)}")
    
    def handle_delete_channel(self):
        """Handle channel deletion process"""
        if not self.connected:
            QMessageBox.warning(self, "خطأ", "الاتصال غير نشط!")
            return
    
        row = self.channel_table.currentRow()
        if row < 0:
            return
    
        reply = QMessageBox.question(
            self,
            "تأكيد الحذف",
            "هل أنت متأكد من رغبتك في حذف هذه القناة نهائيًا؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
    
        if reply != QMessageBox.StandardButton.Yes:
            return
    
        service_id_item = self.channel_table.item(row, 2)
        channel_name_item = self.channel_table.item(row, 1)
    
        if not service_id_item or not channel_name_item:
            return
    
        service_id = service_id_item.text()
        channel_name = channel_name_item.text()
    
        try:
            self._send_delete_command(service_id)
            self.channel_table.removeRow(row)
            self.update_output(f"🗑️ تم حذف القناة: {channel_name} (ID: {service_id})")
            self.update_stats()
        except Exception as e:
            self.update_output(f"❌ فشل في حذف القناة: {str(e)}")
            logging.error(f"Delete error: {str(e)}")
    
    def _send_delete_command(self, program_id: str):
        """Send delete command to device (Request 1002)"""
        delete_cmd = {
            "request": "1002",
            "TvState": "0",
            "array": [{
                "ProgramId": program_id
            }],
            "TotalNum": "1"
        }
        cmd_body = json.dumps(delete_cmd, ensure_ascii=False)
        self.network_thread.send_command(build_message(cmd_body))
    
    # def show_device_info(self, device_info: dict):
        # info_html = (
            # f"<b>🔹 اسم الجهاز:</b> {device_info.get('ProductName', 'غير معروف')}<br>"
            # f"<b>🔹 الإصدار:</b> {device_info.get('SoftwareVersion', '؟')}<br>"
            # f"<b>🔹 الرقم التسلسلي:</b> {device_info.get('SerialNumber', '؟')}<br>"
            # f"<b>🔹 عدد القنوات الحالية:</b> {device_info.get('ChannelNum', '؟')}<br>"
            # f"<b>🔹 الحد الأقصى للقنوات:</b> {device_info.get('MaxNumOfPrograms', '؟')}"
        # )
        # self.device_info_label.setText(info_html)
        # self.tabs.setCurrentWidget(self.device_info_tab)  # التبديل إلى التبويب تلقائيًا
        
    # def init_device_info_tab(self):
        # layout = QVBoxLayout(self.device_info_tab)
        # self.device_info_label = QLabel("❗ لم يتم الاتصال بعد.")
        # self.device_info_label.setWordWrap(True)
        # layout.addWidget(self.device_info_label)

    def handle_lock_channel(self):
        """Handle channel lock process"""
        if not self.connected:
            QMessageBox.warning(self, "خطأ", "الاتصال غير نشط!")
            return
    
        row = self.channel_table.currentRow()
        if row < 0:
            return
    
        reply = QMessageBox.question(
            self,
            "تأكيد القفل",
            "هل تريد قفل هذه القناة؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
    
        if reply != QMessageBox.StandardButton.Yes:
            return
    
        service_id_item = self.channel_table.item(row, 2)
        channel_name_item = self.channel_table.item(row, 1)
    
        if not service_id_item or not channel_name_item:
            return
    
        service_id = service_id_item.text()
        channel_name = channel_name_item.text()
    
        try:

            self._send_lock_command(service_id)
 
            self.channel_table.setItem(row, 7, QTableWidgetItem("نعم"))  # ← عدّل العمود حسب تصميمك 

            self.update_output(f"🔒 تم قفل القناة: {channel_name} (ID: {service_id})")
            self._request_channel_list()  # ← أضف هنا
        except Exception as e:
            self.update_output(f"❌ فشل في قفل القناة: {str(e)}")
            logging.error(f"Lock error: {str(e)}")
    
    def _send_lock_command(self, program_id: str):
        """Send lock command to device (Request 1003)"""
        lock_cmd = {
            "request": "1003",
            "array": [{
                "ProgramId": program_id,
                "TvState": "0"  # ← القيمة الصحيحة للقفل
            }],
            "TotalNum": "1"
        }
        cmd_body = json.dumps(lock_cmd, ensure_ascii=False)
        self.network_thread.send_command(build_message(cmd_body))
    
    def handle_unlock_channel(self):
        """Handle channel unlock process"""
        if not self.connected:
            QMessageBox.warning(self, "خطأ", "الاتصال غير نشط!")
            return
    
        row = self.channel_table.currentRow()
        if row < 0:
            return
    
        reply = QMessageBox.question(
            self,
            "تأكيد إلغاء القفل",
            "هل تريد إلغاء قفل هذه القناة؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
    
        if reply != QMessageBox.StandardButton.Yes:
            return
    
        service_id_item = self.channel_table.item(row, 2)
        channel_name_item = self.channel_table.item(row, 1)
    
        if not service_id_item or not channel_name_item:
            return
    
        service_id = service_id_item.text()
        channel_name = channel_name_item.text()
    
        try:

            self._send_unlock_command(service_id)

            self.channel_table.setItem(row, 7, QTableWidgetItem("لا"))  # ← عدّل العمود حسب تصميمك 


            self.update_output(f"🔓 تم إلغاء قفل القناة: {channel_name} (ID: {service_id})")
           
            self._request_channel_list()  # ← أضف هنا
        except Exception as e:
            self.update_output(f"❌ فشل في إلغاء قفل القناة: {str(e)}")
            logging.error(f"Unlock error: {str(e)}")
    
    def _send_unlock_command(self, program_id: str):
        """Send unlock command to device (Request 1003, TvState=1)"""
        unlock_cmd = {
            "request": "1003",
            "array": [{
                "ProgramId": program_id,
                "TvState": "0"  # ← 1 تعني إلغاء القفل
            }],
            "TotalNum": "1"
        }
        cmd_body = json.dumps(unlock_cmd, ensure_ascii=False)
        self.network_thread.send_command(build_message(cmd_body))
    
    def _request_channel_list(self):
        """طلب تحديث قائمة القنوات من الجهاز"""
        try:
            request = {
                "request": "0",
                "FromIndex": "0",
                "ToIndex": "99"  # غطِ كل القنوات المتاحة
            }
            cmd_body = json.dumps(request, ensure_ascii=False)
            self.network_thread.send_command(build_message(cmd_body))
            self.update_output("🔄 تم إرسال طلب تحديث القنوات إلى الجهاز.")
        except Exception as e:
            self.update_output(f"❌ فشل في طلب القنوات: {str(e)}")            
    def save_channel_as_m3u(self):
        """حفظ القناة المحددة كملف M3U"""
        current_row = self.channel_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "تنبيه", "يرجى تحديد قناة أولاً")
            return
    
        channel_name_item = self.channel_table.item(current_row, 1)
        url_item = self.channel_table.item(current_row, 3)
    
        channel_name = channel_name_item.text() if channel_name_item else "قناة غير معروفة"
        stream_url = url_item.text() if url_item and url_item.text() else ""
    
        if not stream_url:
            QMessageBox.warning(self, "تنبيه", "لا يوجد رابط بث متاح للقناة المحددة")
            return
    
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ ملف M3U",
            f"{channel_name}.m3u",
            "M3U Files (*.m3u);;All Files (*)"
        )
    
        if file_path:
            if not file_path.lower().endswith('.m3u'):
                file_path += '.m3u'
    
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("#EXTM3U\n")
                    f.write(f"#EXTINF:-1,{channel_name}\n")
                    f.write(f"{stream_url}\n")
    
                self.update_output(f"✅ تم حفظ القناة '{channel_name}' في ملف M3U: {file_path}")
                QMessageBox.information(self, "نجاح", f"تم حفظ الملف بنجاح:\n{file_path}")
            except Exception as e:
                self.update_output(f"❌ فشل في حفظ ملف M3U: {str(e)}")
                QMessageBox.critical(self, "خطأ", f"فشل في حفظ الملف:\n{str(e)}")
    def add_channel_to_favorite_group(self, group_name):
        selected_items = self.channel_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد قناة أولاً.")
            return
    
        row = selected_items[0].row()
        service_id_item = self.channel_table.item(row, 2)  # عمود معرف الخدمة
        if not service_id_item:
            QMessageBox.warning(self, "خطأ", "لا يمكن العثور على معرف الخدمة للقناة المحددة.")
            return
    
        service_id = service_id_item.text()
    
        # توليد الأمر وإرساله
        request_body = {
            "request": "203",  # تأكد من رقم الأمر حسب الوثائق الخاصة بالجهاز
            "ServiceId": service_id,
            "Group": group_name
        }
        json_cmd = json.dumps(request_body)
        self.network_thread.send_command(build_message(json_cmd))
    
        self.update_output(f"📌 تمت إضافة القناة إلى مجموعة '{group_name}'")

    def handle_move_channel(self):
        if not self.connected:
            QMessageBox.warning(self, "خطأ", "الاتصال غير نشط!")
            return
    
        current_row = self.channel_table.currentRow()
        if current_row < 0:
            return
    
        # جلب ProgramId للقناة الحالية
        source_program_id_item = self.channel_table.item(current_row, 2)
        channel_name_item = self.channel_table.item(current_row, 1)
    
        if not source_program_id_item or not channel_name_item:
            return
    
        source_program_id = source_program_id_item.text()
        channel_name = channel_name_item.text()
    
        new_row_index, ok = QInputDialog.getInt(
            self,
            "نقل القناة",
            f"رقم الصف الجديد لـ {channel_name} (1-{self.channel_table.rowCount()}):",
            value=current_row + 1,
            min=1,
            max=self.channel_table.rowCount()
        )
    
        # تنفيذ النقل
        if ok and (new_row_index - 1) != current_row:
            # جلب ProgramId من الصف الهدف
            target_program_id_item = self.channel_table.item(new_row_index - 1, 2)
            if not target_program_id_item:
                QMessageBox.warning(self, "خطأ", "تعذر الحصول على ProgramId في الصف الهدف.")
                return
    
            target_program_id = target_program_id_item.text()
    
            self._perform_channel_move(
                program_id=source_program_id,
                old_pos=current_row,
                new_pos=new_row_index - 1,
                move_position_str=target_program_id  # نستخدم program_id كـ MoveToPosition
            )    
    # def handle_move_channel(self):
        # if not self.connected:
            # QMessageBox.warning(self, "خطأ", "الاتصال غير نشط!")
            # return
    
        # current_row = self.channel_table.currentRow()
        # if current_row < 0:
            # return
    
        # service_id_item = self.channel_table.item(current_row, 2)
        # channel_name_item = self.channel_table.item(current_row, 1)
        # service_index_item = self.channel_table.item(current_row, 23)  # العمود 23
        # if not service_id_item or not channel_name_item:
            # return
    
        # service_id = service_id_item.text()
        # channel_name = channel_name_item.text()
    
        # new_row_index, ok = QInputDialog.getInt(
            # self,
            # "نقل القناة",
            # f"رقم الصف الجديد لـ {channel_name} (1-{self.channel_table.rowCount()}):",
            # value=current_row + 1,
            # min=1,
            # max=self.channel_table.rowCount()
        # )
    
        # if ok and (new_row_index - 1) != current_row:
            # # استخراج القيمة من عمود "رقم" (نفترض أنه العمود الأخير)
            # رقم_item = self.channel_table.item(new_row_index - 1, self.channel_table.columnCount() - 1)
            # if not رقم_item:
                # QMessageBox.warning(self, "خطأ", "تعذر الحصول على رقم القناة في الصف الهدف.")
                # return
    
            # move_position_str = رقم_item.text().zfill(8)  # تأكد من أن القيمة 8 أرقام
            # self._perform_channel_move(service_id, current_row, new_row_index - 1, move_position_str)
    
    def _perform_channel_move(self, program_id: str, old_pos: int, new_pos: int, move_position_str: str):
        try:
            move_cmd = {
                "request": "1005",
                "array": [{
                    "ProgramId": program_id,
                    "MoveToPosition": move_position_str,
                    "TvState": "0"
                }],
                "TotalNum": "1"
            }
    
            cmd_body = json.dumps(move_cmd, ensure_ascii=False)
            self.update_output(f"📤 إرسال أمر نقل: {cmd_body}")
            self.network_thread.send_command(build_message(cmd_body))
    
            self._move_table_row(old_pos, new_pos)
            self.update_output(f"↕️ تم نقل القناة إلى الرقم {int(move_position_str)}")
    
        except Exception as e:
            self.update_output(f"❌ فشل في نقل القناة: {str(e)}")
            logging.error(f"Move error: {str(e)}")
    
    
    def _move_table_row(self, old_row: int, new_row: int):
        """Visually move row in the table"""
        row_items = [self.channel_table.takeItem(old_row, col)
                     for col in range(self.channel_table.columnCount())]
    
        self.channel_table.removeRow(old_row)
        self.channel_table.insertRow(new_row)
    
        for col, item in enumerate(row_items):
            if item:
                self.channel_table.setItem(new_row, col, item)
    
        # تحديث أرقام الصفوف إن وُجدت في العمود رقم 23
        for row in range(self.channel_table.rowCount()):
            item = self.channel_table.item(row, 16)
            if item:
                item.setText(str(row + 1))

    def save_channels_to_file(self):
        """حفظ قائمة القنوات إلى ملف"""
        if not self.channels:
            QMessageBox.warning(self, "تحذير", "لا توجد قنوات لحفظها!")
            return
    
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ ملف القنوات",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
    
        if file_path:
            if not file_path.lower().endswith('.json'):
                file_path += '.json'
    
            try:
                data = {
                    "channels": self.channels,
                    "favorites": self.favorites,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
    
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
    
                self.update_output(f"✅ تم حفظ {len(self.channels)} قناة في الملف: {file_path}")
                QMessageBox.information(self, "نجاح", f"تم حفظ القنوات بنجاح في:\n{file_path}")
            except Exception as e:
                self.update_output(f"❌ فشل في حفظ الملف: {str(e)}")
                QMessageBox.critical(self, "خطأ", f"فشل في حفظ الملف:\n{str(e)}")
    
    def load_channels_from_file(self):
        """استعادة قائمة القنوات من ملف"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "فتح ملف القنوات",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
    
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
    
                if "channels" not in data:
                    raise ValueError("الملف لا يحتوي على بيانات قنوات صالحة")
    
                self.channels = data.get("channels", [])
                self.favorites = data.get("favorites", [])
                
                # تحديث الجدول
                self.channel_table.setRowCount(0)
                self.populate_channel_table(self.channels)
                
                self.update_output(f"✅ تم تحميل {len(self.channels)} قناة من الملف: {file_path}")
                QMessageBox.information(self, "نجاح", f"تم تحميل القنوات بنجاح من:\n{file_path}")
                
                # تحديث الإحصائيات
                self.update_stats()
                
            except Exception as e:
                self.update_output(f"❌ فشل في تحميل الملف: {str(e)}")
                QMessageBox.critical(self, "خطأ", f"فشل في تحميل الملف:\n{str(e)}")

             
                          
                                       
                                                    
                                                                 
                                                                              
      # ==========================================================
    # ===== 🎯 أضف هاتين الدالتين الجديدتين إلى كلاس StarsatRemote =====
    # ==========================================================
    
    def handle_move_selected_channels(self):
        """
        ينقل كتلة من القنوات المحددة باستخدام خانة الاختيار إلى موقع جديد.
        """
        if not self.connected:
            QMessageBox.warning(self, "خطأ", "الاتصال غير نشط!")
            return
    
        # 1. جمع القنوات المحددة ومعرفاتها
        selected_channels_info = []
        for row in range(self.channel_table.rowCount()):
            selection_item = self.channel_table.item(row, 17) # عمود التحديد
            if selection_item and selection_item.checkState() == Qt.CheckState.Checked:
                service_id_item = self.channel_table.item(row, 2) # عمود معرف الخدمة
                if service_id_item and service_id_item.text():
                    selected_channels_info.append({
                        "program_id": service_id_item.text(),
                        "row": row
                    })
    
        if not selected_channels_info:
            QMessageBox.information(self, "لا يوجد تحديد", "الرجاء تحديد قناة واحدة على الأقل لنقلها باستخدام خانة الاختيار.")
            return
    
        # 2. سؤال المستخدم عن الموقع الجديد
        new_row_index, ok = QInputDialog.getInt(
            self,
            "نقل القنوات المحددة",
            f"سيتم نقل {len(selected_channels_info)} قناة.\nأدخل رقم الصف الجديد الذي تريد النقل إليه (1-{self.channel_table.rowCount()}):",
            value=1,
            min=1,
            max=self.channel_table.rowCount()
        )
    
        if not ok:
            return
    
        destination_row = new_row_index - 1
    
        # لا تسمح بنقل القنوات إلى موقعها الحالي أو ضمن التحديد نفسه
        selected_rows = [info['row'] for info in selected_channels_info]
        if destination_row in selected_rows:
            QMessageBox.warning(self, "خطأ", "لا يمكن نقل القنوات المحددة إلى موقع ضمن التحديد نفسه.")
            return
    
        # 3. الحصول على معرف القناة في الموقع الهدف الذي سيتم النقل قبله
        target_program_id_item = self.channel_table.item(destination_row, 2)
        if not target_program_id_item or not target_program_id_item.text():
            QMessageBox.warning(self, "خطأ", "تعذر الحصول على معرف الخدمة في الصف الهدف.")
            return
        move_to_position_id = target_program_id_item.text()
    
        try:
            # 4. بناء وإرسال أمر النقل الجماعي
            program_id_array = []
            for channel_info in selected_channels_info:
                program_id_array.append({
                    "ProgramId": channel_info['program_id'],
                    "MoveToPosition": move_to_position_id,
                    "TvState": "0"
                })
    
            move_cmd = {
                "request": "1005",
                "array": program_id_array,
                "TotalNum": str(len(program_id_array))
            }
            cmd_body = json.dumps(move_cmd, ensure_ascii=False)
            full_message = build_message(cmd_body)
            self.network_thread.send_command(full_message)
    
            # 5. تحديث الجدول بصريًا
            self._move_multiple_table_rows(selected_rows, destination_row)
    
            self.update_output(f"↕️ تم إرسال أمر نقل لـ {len(selected_channels_info)} قناة إلى الموقع الجديد.")
            self.update_stats()
    
        except Exception as e:
            error_msg = f"❌ فشل في إرسال أمر النقل الجماعي: {str(e)}"
            self.update_output(error_msg)
            logging.error(f"Bulk move error: {str(e)}")
            QMessageBox.critical(self, "خطأ فادح", error_msg)
    
    
    def _move_multiple_table_rows(self, source_rows: list, destination_row: int):
        """
        ينقل مجموعة من الصفوف بصريًا في الجدول.
        """
        self.channel_table.setSortingEnabled(False)
    
        # 1. استخراج بيانات الصفوف المراد نقلها وحذفها من موقعها القديم
        moving_rows_data = []
        # الحذف بترتيب عكسي لتجنب مشاكل تغير الفهارس
        for row in sorted(source_rows, reverse=True):
            row_data = [self.channel_table.takeItem(row, col) for col in range(self.channel_table.columnCount())]
            moving_rows_data.insert(0, row_data) # الحفاظ على ترتيبها الأصلي
            self.channel_table.removeRow(row)
    
        # تعديل مؤشر الوجهة إذا كانت الصفوف المحذوفة تقع قبل الموقع الهدف
        final_destination = destination_row
        num_rows_before_dest = len([r for r in source_rows if r < destination_row])
        final_destination -= num_rows_before_dest
    
        # 2. إدراج الصفوف في الموقع الجديد
        for i, row_data in enumerate(moving_rows_data):
            insert_pos = final_destination + i
            self.channel_table.insertRow(insert_pos)
            for col, item in enumerate(row_data):
                self.channel_table.setItem(insert_pos, col, item)
                # مسح تحديد خانة الاختيار بعد النقل
                if col == 18 and item:
                    item.setCheckState(Qt.CheckState.Unchecked)
    
        # 3. إعادة ترقيم عمود "رقم" ليعكس الترتيب الجديد
        for row in range(self.channel_table.rowCount()):
            item = self.channel_table.item(row, 16) # العمود 16 هو "رقم"
            if item:
                item.setText(str(row + 1))
    
        self.channel_table.setSortingEnabled(True)
  
    def _send_delete_command(self, program_id: str):
        """Send delete command to device (Request 1002)"""
        delete_cmd = {
            "request": "1002",
            "TvState": "0",
            "array": [{
                "ProgramId": program_id
            }],
            "TotalNum": "1"
        }
        cmd_body = json.dumps(delete_cmd, ensure_ascii=False)
        self.network_thread.send_command(build_message(cmd_body)) 
    # --- بداية الدالة الجديدة ---
    def handle_delete_selected_channels(self):
        """
        تحذف جميع القنوات التي تم تحديدها في عمود التحديد (18) من الجهاز
        والجدول.
        """
        if not self.connected:
            QMessageBox.warning(self, "خطأ", "الاتصال غير نشط!")
            return

        selected_ids = []
        rows_to_delete = []
        # العمود 18 هو خانة الاختيار، العمود 2 هو معرف الخدمة
        for row in range(self.channel_table.rowCount()):
            selection_item = self.channel_table.item(row, 17)
            if selection_item and selection_item.checkState() == Qt.CheckState.Checked:
                service_id_item = self.channel_table.item(row, 2)
                if service_id_item and service_id_item.text():
                    selected_ids.append(service_id_item.text())
                    rows_to_delete.append(row)

        if not selected_ids:
            QMessageBox.information(self, "لا يوجد تحديد", "الرجاء تحديد قناة واحدة على الأقل لحذفها باستخدام خانة الاختيار.")
            return

        reply = QMessageBox.question(
            self,
            "تأكيد الحذف الجماعي",
            f"هل أنت متأكد من رغبتك في حذف {len(selected_ids)} قناة نهائيًا من الجهاز؟\nهذا الإجراء لا يمكن التراجع عنه.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # بناء حمولة الأمر
            program_id_array = [{"ProgramId": pid} for pid in selected_ids]
            delete_cmd = {
                "request": "1002",
                "TvState": "0",
                "array": program_id_array,
                "TotalNum": str(len(selected_ids))
            }
            cmd_body = json.dumps(delete_cmd, ensure_ascii=False)
            full_message = build_message(cmd_body)

            # إرسال الأمر
            self.network_thread.send_command(full_message)

            # تحديث واجهة المستخدم عن طريق حذف الصفوف بترتيب عكسي
            for row_index in sorted(rows_to_delete, reverse=True):
                self.channel_table.removeRow(row_index)

            self.update_output(f"🗑️ تم إرسال أمر حذف لـ {len(selected_ids)} قناة.")
            self.update_stats()

        except Exception as e:
            error_msg = f"❌ فشل في إرسال أمر الحذف الجماعي: {str(e)}"
            self.update_output(error_msg)
            logging.error(f"Bulk delete error: {str(e)}")
            QMessageBox.critical(self, "خطأ فادح", error_msg)
    # --- نهاية الدالة الجديدة --- 
                                                                                                                                                                                     
    def handle_send_direct_command(self):
        """
        يقرأ الكود الرقمي من مربع الإدخال ويرسله كأمر مفتاح.
        """
        if not self.connected:
            QMessageBox.warning(self, "غير متصل", "يرجى الاتصال بالجهاز أولاً لإرسال الأوامر.")
            return
    
        key_code = self.direct_cmd_input.text().strip()
        if not key_code:
            QMessageBox.warning(self, "خطأ إدخال", "يرجى إدخال كود الأمر الرقمي.")
            return
        
        # يقوم QIntValidator بالتحقق من أنه رقم، لذا نحتاج فقط لإرساله
        self.update_output(f"▶️ إرسال كود الأمر المباشر: {key_code}")
        self.send_key(key_code)           
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          
                                                                                                                     
def closeEvent(self, event):
        self.update_output("⏳ جاري إغلاق التطبيق وحفظ الإعدادات...")
        if self.is_updating_all_urls: self.stop_updating_all_urls()
        if self.is_fetching_all: self.stop_fetching_all()

        if self.network_thread and self.network_thread.isRunning():
            self.network_thread.stop()
            if not self.network_thread.wait(1000):
                self.update_output("⚠️ لم يتم إنهاء خيط الشبكة بشكل طبيعي.")

        self.settings_manager.save_window_state(self)
        self.settings_manager.save_device_settings(self.ip_input.text().strip(), self.port_input.text().strip())
        self.settings_manager.settings.setValue("vlc_path", self.vlc_path_input.text())
        self.settings_manager.settings.setValue("record_path", self.record_path_input.text())
        self.settings_manager.save_channels(self.channels)
        self.settings_manager.save_favorites(self.favorites)
        self.settings_manager.settings.setValue("connected_devices", self.connected_devices)

        self.settings_manager.settings.sync()
        logging.info("التطبيق مغلق، تم حفظ الإعدادات.")
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    settings_mgr_init = SettingsManager()
    if not settings_mgr_init.validate_settings():
        logging.warning("إعدادات تالفة أو مفقودة عند بدء التشغيل، جاري الإصلاح...")
        settings_mgr_init.repair_settings()

    win = StarsatRemote()
    win.show()
    sys.exit(app.exec())
# ```