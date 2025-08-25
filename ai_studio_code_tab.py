from PyQt6.QtCore import Qt, QObject, pyqtSignal
import sys
import subprocess
import threading
import json
import os
from datetime import datetime
import socket
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox, QFileDialog, QTextEdit,
    QComboBox, QListWidget, QFrame
)

# --- START OF NEW CODE ---
# كائن للتواصل بين خيط الفحص والواجهة الرئيسية لتجنب التعارض
class Communicate(QObject):
    scan_finished = pyqtSignal(list)
# --- END OF NEW CODE ---

class FireTVRemote(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎮 FireTV Remote")
        self.setGeometry(100, 100, 900, 800)

        # --- START OF MODIFIED CODE ---
        # إعداد آلية التواصل بين الخيوط
        self.scanner_comm = Communicate()
        self.scanner_comm.scan_finished.connect(self.update_devices_from_scan)
        # --- END OF MODIFIED CODE ---

        self.label_input = QLineEdit()
        self.ip_input = QLineEdit()
        self.port_input = QLineEdit("5555")
        self.connection_status = QLabel("❌ غير متصل")
        self.text_input = QLineEdit()
        
        self.device_info_label = QLabel("ℹ️ لم يتم توصيل أي جهاز")
        self.device_info_label.setWordWrap(True)
        self.device_info_label.setStyleSheet("padding: 5px; border: 1px solid lightgray; border-radius: 5px;")

        self.devices_file = "devices.json"
        self.saved_devices = []
        self.device_selector = QComboBox()
        self.log_content = []
        self.apps_filter_input = QLineEdit()
        self.apps_filter_input.setPlaceholderText("🔎 ابحث عن تطبيق")
        self.apps_filter_input.textChanged.connect(self.filter_apps)

        self.apps_listbox = QListWidget()
        self.apps_listbox.itemDoubleClicked.connect(self.show_app_details_dialog)
        self.all_packages = []

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)

        self.main_layout = QHBoxLayout()
        self.left_panel = QVBoxLayout()
        self.right_panel = QVBoxLayout()
        self.build_ui()
        self.load_devices()

    def build_ui(self):
        layout = QVBoxLayout()

        device_details_layout = QHBoxLayout()
        name_layout = QVBoxLayout()
        name_layout.addWidget(QLabel("💼 الاسم:"))
        name_layout.addWidget(self.label_input)
        device_details_layout.addLayout(name_layout)
        ip_layout = QVBoxLayout()
        ip_layout.addWidget(QLabel("🌐 IP:"))
        ip_layout.addWidget(self.ip_input)
        device_details_layout.addLayout(ip_layout)
        port_layout = QVBoxLayout()
        port_layout.addWidget(QLabel("🔌 Port:"))
        port_layout.addWidget(self.port_input)
        device_details_layout.addLayout(port_layout)
        layout.addLayout(device_details_layout)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("📂 حفظ الجهاز")
        btn_save.clicked.connect(self.save_device)
        btn_clear = QPushButton("🗑️ مسح الكل")
        btn_clear.clicked.connect(self.clear_saved_devices)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_clear)
        layout.addLayout(btn_row)

        self.device_selector.currentTextChanged.connect(self.select_device)
        layout.addWidget(self.device_selector)

        conn_row = QHBoxLayout()
        btn_conn = QPushButton("🟢 اتصال")
        btn_conn.clicked.connect(self.connect_device)
        btn_disc = QPushButton("❌ قطع")
        btn_disc.clicked.connect(self.disconnect_device)
        
        # --- START OF MODIFIED CODE ---
        btn_scan = QPushButton("📡 فحص الشبكة")
        btn_scan.setObjectName("scanButton") # اسم برمجي للوصول للزر
        btn_scan.clicked.connect(self.scan_for_devices)
        # --- END OF MODIFIED CODE ---

        conn_row.addWidget(btn_conn)
        conn_row.addWidget(btn_disc)
        conn_row.addWidget(btn_scan) # إضافة الزر للواجهة
        layout.addLayout(conn_row)
        layout.addWidget(self.connection_status)

        info_title = QLabel("--- ℹ️ معلومات الجهاز ---")
        info_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_title)
        layout.addWidget(self.device_info_label)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        nav = QHBoxLayout()
        for text, code in [("🔼", "KEYCODE_DPAD_UP"), ("◀️", "KEYCODE_DPAD_LEFT"), ("✔", "KEYCODE_DPAD_CENTER"), ("▶️", "KEYCODE_DPAD_RIGHT"), ("🔽", "KEYCODE_DPAD_DOWN")]:
            btn = QPushButton(text)
            btn.clicked.connect(lambda _, c=code: self.send_key(c))
            nav.addWidget(btn)
        layout.addLayout(nav)

        sys_row = QHBoxLayout()
        for text, code in [("🏠 الرئيسية", "KEYCODE_HOME"), ("🔙 رجوع", "KEYCODE_BACK")]:
            btn = QPushButton(text)
            btn.clicked.connect(lambda _, c=code: self.send_key(c))
            sys_row.addWidget(btn)
        layout.addLayout(sys_row)

        pow_row = QHBoxLayout()
        btn_power = QPushButton("⏻ إيقاف التشغيل")
        btn_power.clicked.connect(lambda: self.send_key("KEYCODE_POWER"))
        btn_reboot = QPushButton("🔄 إعادة التشغيل")
        btn_reboot.clicked.connect(self.reboot_device)
        pow_row.addWidget(btn_power)
        pow_row.addWidget(btn_reboot)
        layout.addLayout(pow_row)

        vol_row = QHBoxLayout()
        for text, code in [("🔊", "KEYCODE_VOLUME_UP"), ("🔇", "KEYCODE_VOLUME_MUTE"), ("🔉", "KEYCODE_VOLUME_DOWN")]:
            btn = QPushButton(text)
            btn.clicked.connect(lambda _, c=code: self.send_key(c))
            vol_row.addWidget(btn)
        layout.addLayout(vol_row)

        media_row = QHBoxLayout()
        for text, code in [("⏮️", "KEYCODE_MEDIA_PREVIOUS"), ("⏯️", "KEYCODE_MEDIA_PLAY_PAUSE"), ("⏭️", "KEYCODE_MEDIA_NEXT"), ("⏪10s", "KEYCODE_MEDIA_REWIND"), ("⏩10s", "KEYCODE_MEDIA_FAST_FORWARD")]:
            btn = QPushButton(text)
            btn.clicked.connect(lambda _, c=code: self.send_key(c))
            media_row.addWidget(btn)
        layout.addLayout(media_row)

        app_row1 = QHBoxLayout()
        for text, pkg in [("📺 YouTube", "com.google.android.youtube.tv"), ("🎬 Netflix", "com.netflix.ninja"), ("🛒 Google Play", "com.android.vending"), ("🔄 Orientation", "com.googlecode.eyesfree.setorientation")]:
            btn = QPushButton(text)
            btn.clicked.connect(lambda _, p=pkg: self.launch_app(p))
            app_row1.addWidget(btn)
        layout.addLayout(app_row1)

        app_row2 = QHBoxLayout()
        for text, pkg in [("▶️ SmartTube", "com.teamsmart.videomanager.tv"), ("🅱️ STube Beta", "com.liskovsoft.smarttubetv.beta"), ("🔧 Proj Menu", "com.spocky.projengmenu"), ("⚡️ Quick Actions", "dev.vodik7.tvquickactions")]:
            btn = QPushButton(text)
            btn.clicked.connect(lambda _, p=pkg: self.launch_app(p))
            app_row2.addWidget(btn)
        layout.addLayout(app_row2)

        settings_row = QHBoxLayout()
        for text, func in [("⚖️ الإعدادات", self.open_settings), ("🌐 الشبكة", self.open_network_settings), ("📱 التطبيقات", self.open_app_settings), ("🖥️ الشاشة", self.open_display_settings)]:
            btn = QPushButton(text)
            btn.clicked.connect(func)
            settings_row.addWidget(btn)
        layout.addLayout(settings_row)

        layout.addWidget(QPushButton("📋 عرض التطبيقات", clicked=self.list_installed_apps))
        layout.addWidget(QLabel("⌨️ أدخل نص"))
        layout.addWidget(self.text_input)
        layout.addWidget(QPushButton("📤", clicked=self.send_text))
        layout.addWidget(self.log_box)
        layout.addWidget(QPushButton("📂 حفظ السجل", clicked=self.save_log))

        self.left_panel.addLayout(layout)
        self.right_panel.addWidget(QLabel("📋 قائمة التطبيقات المثبتة:"))
        self.right_panel.addWidget(self.apps_filter_input)
        self.right_panel.addWidget(self.apps_listbox)
        launch_btn = QPushButton("🚀 تشغيل المحدد")
        launch_btn.clicked.connect(self.launch_selected_app)
        self.right_panel.addWidget(launch_btn)

        self.main_layout.addLayout(self.left_panel, 2)
        self.main_layout.addLayout(self.right_panel, 1)
        self.setLayout(self.main_layout)

    def log(self, msg):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        entry = f"{timestamp} {msg}"
        self.log_box.append(entry)
        self.log_content.append(entry)
        
    # --- START OF NEW/MODIFIED FUNCTIONS ---
    def scan_for_devices(self):
        self.log("📡 جارٍ فحص الشبكة عن الأجهزة... قد يستغرق هذا بضع ثوانٍ.")
        scan_button = self.findChild(QPushButton, "scanButton")
        if scan_button:
            scan_button.setEnabled(False)
            scan_button.setText("... جارٍ الفحص ...")
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _get_local_ip_prefix(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(("8.8.8.8", 53)) # الاتصال بخادم خارجي لتحديد IP المحلي
                ip = s.getsockname()[0]
                return ".".join(ip.split('.')[:-1]) + "."
        except Exception:
            self.log("⚠️ تعذر تحديد IP المحلي. تأكد من اتصالك بالشبكة.")
            return None

    def _check_port(self, ip, port, timeout=0.2):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                if sock.connect_ex((ip, port)) == 0:
                    return ip
        except socket.error:
            return None
        return None

    def _scan_worker(self):
        prefix = self._get_local_ip_prefix()
        if not prefix:
            self.scanner_comm.scan_finished.emit([]) # إرسال قائمة فارغة لإنهاء العملية
            return

        potential_ips = []
        with ThreadPoolExecutor(max_workers=100) as executor:
            # فحص جميع الـ IPs الممكنة من 1 إلى 254
            futures = [executor.submit(self._check_port, f"{prefix}{i}", 5555) for i in range(1, 255)]
            for future in futures:
                result = future.result()
                if result:
                    potential_ips.append(result)
        
        # إرسال النتائج إلى الواجهة الرئيسية بأمان
        self.scanner_comm.scan_finished.emit(potential_ips)

    def update_devices_from_scan(self, ips):
        if not ips:
            self.log("✅ انتهى الفحص. لم يتم العثور على أجهزة جديدة.")
        else:
            self.log(f"🔬 تم العثور على {len(ips)} جهازًا محتملاً.")
            current_ips = [d['ip'] for d in self.saved_devices]
            added_count = 0
            for ip in ips:
                if ip not in current_ips:
                    # إضافة الجهاز المكتشف باسم مؤقت
                    device_name = f"جهاز مكتشف ({ip})"
                    new_device = {"label": device_name, "ip": ip, "port": "5555"}
                    self.saved_devices.append(new_device)
                    added_count += 1
            
            if added_count > 0:
                self._write_devices()
                self.load_devices() # إعادة تحميل القائمة المنسدلة
                self.log(f"✅ تمت إضافة {added_count} جهاز جديد إلى القائمة.")
            else:
                self.log("ℹ️ جميع الأجهزة التي تم العثور عليها موجودة بالفعل في القائمة.")

        scan_button = self.findChild(QPushButton, "scanButton")
        if scan_button:
            scan_button.setEnabled(True)
            scan_button.setText("📡 فحص الشبكة")
    # --- END OF NEW/MODIFIED FUNCTIONS ---

    def connect_device(self):
        ip = self.ip_input.text()
        port = self.port_input.text()
        full = f"{ip}:{port}"
        self.log(f"الاتصال بـ {full}...")
        threading.Thread(target=lambda: self._connect(full), daemon=True).start()

    def _connect(self, full):
        try:
            res = subprocess.run(["adb", "connect", full], capture_output=True, text=True, timeout=5)
            if "connected" in res.stdout:
                self.connection_status.setText("✅ متصل")
                self.log("✅ تم الاتصال")
                self.get_device_info()
                self.list_installed_apps()
            else:
                self.connection_status.setText("❌ فشل الاتصال")
                self.log(res.stdout or res.stderr)
        except Exception as e:
            self.log(f"❌ خطأ: {e}")
            self.connection_status.setText("❌ فشل الاتصال")

    def get_device_info(self):
        self.log("ℹ️ جارٍ جلب معلومات الجهاز...")
        def worker():
            try:
                props_to_fetch = {"طراز الجهاز": "ro.product.model", "إصدار أندرويد": "ro.build.version.release", "مستوى SDK": "ro.build.version.sdk", "المعالج": "ro.product.cpu.abi"}
                info_parts = []
                for desc, prop in props_to_fetch.items():
                    res = subprocess.run(["adb", "shell", "getprop", prop], capture_output=True, text=True, encoding='utf-8', errors='ignore')
                    value = res.stdout.strip()
                    info_parts.append(f"🔹 {desc}: {value}")
                res = subprocess.run(["adb", "shell", "wm", "size"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
                resolution = res.stdout.replace("Physical size:", "").strip()
                info_parts.append(f"🔹 دقة الشاشة: {resolution}")
                res = subprocess.run(["adb", "get-serialno"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
                serial = res.stdout.strip()
                info_parts.append(f"🔹 الرقم التسلسلي: {serial}")
                final_text = "\n".join(info_parts)
                self.device_info_label.setText(final_text)
                log_text = "\n--- ℹ️ معلومات الجهاز ---\n" + final_text + "\n---------------------------"
                self.log(log_text)
            except Exception as e:
                self.log(f"❌ خطأ أثناء جلب معلومات الجهاز: {e}")
                self.device_info_label.setText("❌ فشل جلب المعلومات")
        threading.Thread(target=worker, daemon=True).start()

    def disconnect_device(self):
        full = f"{self.ip_input.text()}:{self.port_input.text()}"
        subprocess.run(["adb", "disconnect", full], capture_output=True)
        self.connection_status.setText("❌ غير متصل")
        self.log("🔌 تم فصل الاتصال")
        self.device_info_label.setText("ℹ️ لم يتم توصيل أي جهاز")

    def send_key(self, code):
        if "متصل" not in self.connection_status.text():
            QMessageBox.warning(self, "خطأ", "يرجى الاتصال أولًا")
            return
        self.log(f"🔘 {code}")
        threading.Thread(target=lambda: subprocess.run(["adb", "shell", "input", "keyevent", code]), daemon=True).start()

    def reboot_device(self):
        if "متصل" not in self.connection_status.text():
            QMessageBox.warning(self, "خطأ", "يرجى الاتصال أولًا")
            return
        self.log("🔄 إعادة تشغيل الجهاز")
        threading.Thread(target=lambda: subprocess.run(["adb", "reboot"]), daemon=True).start()

    def launch_app(self, pkg):
        self.log(f"📲 فتح: {pkg}")
        threading.Thread(target=lambda: subprocess.run(["adb", "shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"]), daemon=True).start()

    def open_settings(self):
        self._start_adb_activity("android.settings.SETTINGS", "⚙️ فتح الإعدادات")

    def open_network_settings(self):
        self._start_adb_activity("android.settings.WIFI_SETTINGS", "🌐 فتح إعدادات الشبكة")

    def open_app_settings(self):
        self._start_adb_activity("android.settings.APPLICATION_SETTINGS", "📱 فتح إعدادات التطبيقات")

    def open_display_settings(self):
        self._start_adb_activity("android.settings.DISPLAY_SETTINGS", "🖥️ فتح إعدادات الشاشة")

    def _start_adb_activity(self, action, log_msg):
        if "متصل" not in self.connection_status.text():
            QMessageBox.warning(self, "خطأ", "يرجى الاتصال أولًا")
            return
        self.log(log_msg)
        threading.Thread(target=lambda: subprocess.run(["adb", "shell", "am", "start", "-a", action]), daemon=True).start()

    def list_installed_apps(self):
        if "متصل" not in self.connection_status.text():
            return
        self.log("📦 جارٍ جلب التطبيقات...")
        def worker():
            try:
                res = subprocess.run(["adb", "shell", "pm", "list", "packages"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
                packages = [line.strip().replace("package:", "") for line in res.stdout.splitlines()]
                self.apps_listbox.clear()
                self.all_packages = packages
                for pkg in packages:
                    self.apps_listbox.addItem(pkg)
                self.log(f"✅ تم جلب {len(packages)} تطبيقًا")
            except Exception as e:
                self.log(f"❌ خطأ أثناء الجلب: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def filter_apps(self):
        query = self.apps_filter_input.text().strip().lower()
        self.apps_listbox.clear()
        for pkg in self.all_packages:
            if query in pkg.lower():
                self.apps_listbox.addItem(pkg)

    def show_app_details_dialog(self, item):
        pkg = item.text()
        if not pkg: return
        def get_app_size():
            try:
                cmd = ["adb", "shell", "pm", "path", pkg]
                res = subprocess.run(cmd, capture_output=True, text=True)
                path_line = res.stdout.strip().replace("package:", "")
                if not path_line: return "N/A"
                stat_cmd = ["adb", "shell", "du", "-h", path_line]
                size_res = subprocess.run(stat_cmd, capture_output=True, text=True)
                return size_res.stdout.split("\t")[0].strip()
            except: return "N/A"
        version = "N/A"
        permissions = ""
        try:
            version_res = subprocess.run(["adb", "shell", "dumpsys", "package", pkg], capture_output=True, text=True, encoding='utf-8', errors='ignore')
            for line in version_res.stdout.splitlines():
                if "versionName" in line: version = line.strip().split('=')[-1]
                if line.strip().startswith("uses-permission"): permissions += f"- {line.strip().split(':')[-1]}\n"
        except: pass
        size = get_app_size()
        msg = QMessageBox(self)
        msg.setWindowFlag(msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        msg.setWindowTitle("📦 معلومات التطبيق")
        msg.setText(f"**اسم الحزمة:** {pkg}\n**الإصدار:** {version}\n**الحجم:** {size}\n\n**الأذونات:**\n{permissions.strip() if permissions else 'لا توجد'}")
        msg.setTextFormat(Qt.TextFormat.MarkdownText)
        open_btn = msg.addButton("🚀 فتح", QMessageBox.ButtonRole.AcceptRole)
        stop_btn = msg.addButton("⛔ إيقاف", QMessageBox.ButtonRole.DestructiveRole)
        info_btn = msg.addButton("⚙️ معلومات التطبيق", QMessageBox.ButtonRole.ActionRole)
        clear_data_btn = msg.addButton("🧹 مسح البيانات", QMessageBox.ButtonRole.ActionRole)
        clear_cache_btn = msg.addButton("🧼 مسح المؤقتة", QMessageBox.ButtonRole.ActionRole)
        uninstall_btn = msg.addButton("🗑️ إلغاء التثبيت", QMessageBox.ButtonRole.ActionRole)
        install_btn = msg.addButton("📥 تثبيت تطبيق...", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg.addButton("إلغاء", QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        button = msg.clickedButton()
        if button == open_btn: self.launch_app(pkg)
        elif button == stop_btn: self.stop_app(pkg)
        elif button == info_btn: self.open_app_info(pkg)
        elif button == clear_data_btn: self.clear_app_data(pkg)
        elif button == clear_cache_btn: self.clear_app_cache(pkg)
        elif button == uninstall_btn: self.uninstall_app(pkg)
        elif button == install_btn: self.install_app()

    def open_app_info(self, pkg):
        self.log(f"⚙️ معلومات التطبيق: {pkg}")
        threading.Thread(target=lambda: subprocess.run(["adb", "shell", "am", "start", "-a", "android.settings.APPLICATION_DETAILS_SETTINGS", "-d", f"package:{pkg}"], capture_output=True), daemon=True).start()

    def clear_app_data(self, pkg):
        self.log(f"🧹 مسح بيانات التطبيق: {pkg}")
        threading.Thread(target=lambda: subprocess.run(["adb", "shell", "pm", "clear", pkg], capture_output=True), daemon=True).start()

    def clear_app_cache(self, pkg):
        self.log(f"🧼 مسح البيانات المؤقتة للتطبيق: {pkg}")
        threading.Thread(target=lambda: subprocess.run(["adb", "shell", "pm", "trim-caches", "1G"], capture_output=True), daemon=True).start()

    def uninstall_app(self, pkg):
        self.log(f"🗑️ إلغاء تثبيت التطبيق: {pkg}")
        threading.Thread(target=lambda: subprocess.run(["adb", "uninstall", pkg], capture_output=True), daemon=True).start()

    def install_app(self):
        path, _ = QFileDialog.getOpenFileName(self, "تثبيت تطبيق APK", "", "APK Files (*.apk)")
        if path:
            self.log(f"📥 تثبيت التطبيق من: {path}")
            def installer():
                try:
                    result = subprocess.run(["adb", "install", path], capture_output=True, text=True, encoding='utf-8', errors='ignore')
                    if "Success" in result.stdout:
                        self.log("✅ تم التثبيت بنجاح")
                        QMessageBox.information(self, "نجاح", "✅ تم تثبيت التطبيق بنجاح")
                        self.list_installed_apps()
                    else:
                        self.log(f"❌ فشل التثبيت: {result.stdout.strip()}")
                        QMessageBox.warning(self, "فشل التثبيت", f"❌ فشل التثبيت:\n{result.stdout.strip()}")
                except Exception as e:
                    self.log(f"❌ خطأ أثناء التثبيت: {e}")
                    QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء التثبيت:\n{e}")
            threading.Thread(target=installer, daemon=True).start()

    def stop_app(self, pkg):
        self.log(f"⛔ إيقاف التطبيق: {pkg}")
        threading.Thread(target=lambda: subprocess.run(["adb", "shell", "am", "force-stop", pkg]), daemon=True).start()

    def launch_selected_app(self):
        item = self.apps_listbox.currentItem()
        pkg = item.text() if item else ""
        if not pkg:
            QMessageBox.information(self, "❗️تنبيه", "يرجى اختيار تطبيق")
            return
        self.log(f"🚀 تشغيل التطبيق: {pkg}")
        threading.Thread(target=lambda: subprocess.run(["adb", "shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"]), daemon=True).start()

    def send_text(self):
        txt = self.text_input.text().strip().replace(" ", "%s")
        if txt:
            self.log(f"⌨️ إرسال: {txt}")
            threading.Thread(target=lambda: subprocess.run(["adb", "shell", "input", "text", txt]), daemon=True).start()

    def save_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "حفظ السجل", "", "Text Files (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.log_content))
            self.log("📁 تم حفظ السجل")

    def save_device(self):
        label = self.label_input.text().strip()
        ip = self.ip_input.text().strip()
        port = self.port_input.text().strip()
        if not (label and ip and port):
            QMessageBox.warning(self, "بيانات ناقصة", "يرجى ملء جميع الحقول")
            return
        self.saved_devices.append({"label": label, "ip": ip, "port": port})
        self._write_devices()
        self.load_devices()
        self.log(f"💾 تم حفظ: {label}")

    def load_devices(self):
        if os.path.exists(self.devices_file):
            with open(self.devices_file, "r", encoding="utf-8") as f:
                self.saved_devices = json.load(f)
        self.device_selector.clear()
        self.device_selector.addItem("اختر جهازًا محفوظًا...")
        for d in self.saved_devices:
            self.device_selector.addItem(d["label"])

    def select_device(self, label):
        if self.device_selector.currentIndex() == 0:
            self.label_input.clear()
            self.ip_input.clear()
            self.port_input.setText("5555")
            return
        for d in self.saved_devices:
            if d["label"] == label:
                self.label_input.setText(d["label"])
                self.ip_input.setText(d["ip"])
                self.port_input.setText(d["port"])
                self.log(f"📌 تم اختيار: {label}")
                break

    def clear_saved_devices(self):
        confirm = QMessageBox.question(self, "تأكيد", "هل تريد مسح جميع الأجهزة المحفوظة؟")
        if confirm == QMessageBox.StandardButton.Yes:
            self.saved_devices = []
            self._write_devices()
            self.load_devices()
            self.log("🗑️ تم مسح جميع المحفوظات")

    def _write_devices(self):
        with open(self.devices_file, "w", encoding="utf-8") as f:
            json.dump(self.saved_devices, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FireTVRemote()
    window.show()
    sys.exit(app.exec())