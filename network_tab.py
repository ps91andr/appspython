import sys
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QCheckBox,
    QTableWidget, QTextEdit, QHBoxLayout, QVBoxLayout,
    QTableWidgetItem, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt

class NetworkScannerTab(QWidget):
    """
    فئة تمثل علامة تبويب ماسح الشبكة في واجهة المستخدم الرسومية.
    تقوم بمسح الشبكة المحلية لعرض الأجهزة المتصلة، وتوفر أدوات شبكة إضافية.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("الأجهزة المتصلة بالشبكة")
        self.setGeometry(100, 100, 800, 600)
        self.init_ui()

    def init_ui(self):
        """
        تقوم بتهيئة مكونات واجهة المستخدم وتخطيطها.
        """
        self.title_label = QLabel("الأجهزة المتصلة بالشبكة المحلية", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")

        # --- أزرار التحكم ---
        self.scan_button = QPushButton("مسح الشبكة")
        self.arp_button = QPushButton("عرض جدول ARP")
        self.cmd_button = QPushButton("فتح CMD كمسؤول")
        self.flushdns_button = QPushButton("تفريغ DNS (Flush DNS)")
        self.hostname_checkbox = QCheckBox("استعلام اسم الجهاز")
        self.hostname_checkbox.setChecked(True) # تفعيل الخيار افتراضيًا

        # --- ربط الأزرار بالوظائف ---
        self.scan_button.clicked.connect(self.get_connected_devices)
        self.arp_button.clicked.connect(self.get_arp_table)
        self.cmd_button.clicked.connect(self.open_cmd_as_admin)
        self.flushdns_button.clicked.connect(self.flush_dns_as_admin)

        # --- جدول عرض الأجهزة ---
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(2)
        self.result_table.setHorizontalHeaderLabels(["عنوان IP", "اسم الجهاز (Hostname)"])
        self.result_table.setColumnWidth(0, 250)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # جعل الجدول للقراءة فقط

        # --- مربع نص لعرض المخرجات ---
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        # self.output_box.setStyleSheet("font-family: 'Courier New'; background-color: #f0f0f0;")
        self.output_box.setStyleSheet("font-family: 'Courier New'; background-color: #1e1e1e;")

        # --- التخطيطات ---
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(self.arp_button)
        button_layout.addWidget(self.cmd_button)
        button_layout.addWidget(self.flushdns_button)
        button_layout.addWidget(self.hostname_checkbox)
        button_layout.addStretch()

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.title_label)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.result_table)
        main_layout.addWidget(self.output_box)
        self.setLayout(main_layout)

    def get_connected_devices(self):
        """
        يمسح الشبكة بحثًا عن الأجهزة النشطة ويعرضها في الجدول.
        """
        self.result_table.setRowCount(0)
        self.output_box.setText("جاري مسح الشبكة، يرجى الانتظار...")
        QApplication.processEvents() # تحديث الواجهة لإظهار الرسالة

        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            network_prefix = '.'.join(local_ip.split('.')[:-1]) + '.'

            active_devices = []

            def ping_device(ip):
                try:
                    # استخدام مهلة قصيرة لجعل المسح أسرع
                    subprocess.check_output(
                        ['ping', '-n', '1', '-w', '500', ip],
                        shell=True,
                        text=True,
                        stderr=subprocess.DEVNULL
                    )
                    active_devices.append(ip)
                except subprocess.CalledProcessError:
                    pass # الجهاز غير موجود أو لا يرد

            with ThreadPoolExecutor(max_workers=100) as executor:
                ips_to_scan = [network_prefix + str(i) for i in range(1, 255)]
                executor.map(ping_device, ips_to_scan)

            # فرز الأجهزة بناءً على الجزء الأخير من عنوان IP
            sorted_devices = sorted(active_devices, key=lambda ip: int(ip.split('.')[-1]))

            for device_ip in sorted_devices:
                device_name = "N/A"
                if self.hostname_checkbox.isChecked():
                    try:
                        device_name = socket.gethostbyaddr(device_ip)[0]
                    except socket.herror:
                        device_name = "غير معروف"

                current_row = self.result_table.rowCount()
                self.result_table.insertRow(current_row)
                self.result_table.setCellWidget(current_row, 0, self.create_ip_cell_widget(device_ip))
                self.result_table.setItem(current_row, 1, QTableWidgetItem(device_name))

            self.output_box.setText(f"اكتمل المسح. تم العثور على {len(sorted_devices)} جهاز نشط.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ في المسح", str(e))
            self.output_box.setText("فشل المسح.")

    def get_arp_table(self):
        """
        ينفذ الأمر 'arp -a' ويعرض النتائج في مربع النص.
        """
        self.output_box.clear()
        try:
            result = subprocess.run(
                ['arp', '-a'],
                capture_output=True,
                shell=True,
                text=True,
                encoding='cp850', # استخدام ترميز يناسب موجه الأوامر
            )
            self.output_box.append("--- جدول ARP ---")
            self.output_box.append(result.stdout)
            if result.stderr:
                self.output_box.append("\n--- أخطاء ARP ---")
                self.output_box.append(result.stderr)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))

    def open_cmd_as_admin(self):
        """
        يفتح نافذة موجه الأوامر (CMD) بصلاحيات المسؤول.
        """
        try:
            subprocess.run(
                ["powershell", "-Command", "Start-Process cmd -Verb RunAs"],
                shell=True,
                check=True
            )
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل فتح CMD كمسؤول:\n{str(e)}")

    def flush_dns_as_admin(self):
        """
        ينفذ أمر تفريغ ذاكرة التخزين المؤقت لـ DNS بصلاحيات المسؤول.
        """
        self.output_box.setText("جاري طلب صلاحيات المسؤول لتفريغ ذاكرة DNS...")
        try:
            subprocess.run(
                [
                    "powershell",
                    "-Command",
                    'Start-Process "ipconfig" -ArgumentList "/flushdns" -Verb RunAs -Wait -WindowStyle Hidden'
                ],
                shell=True,
                check=True
            )
            QMessageBox.information(self, "نجاح", "تم طلب تفريغ ذاكرة التخزين المؤقت لـ DNS بنجاح.")
            self.output_box.setText("تم طلب تفريغ ذاكرة التخزين المؤقت لـ DNS بنجاح.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل تنفيذ الأمر:\n{str(e)}")
            self.output_box.setText(f"فشل تنفيذ الأمر:\n{str(e)}")

    def create_ip_cell_widget(self, ip):
        """
        ينشئ ويدجت مخصص لخلية IP يحتوي على العنوان وزر للنسخ.
        """
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(10)

        ip_label = QLabel(ip)
        copy_button = QPushButton("نسخ")
        copy_button.setFixedWidth(50)

        # استخدام lambda لتمرير قيمة IP الحالية إلى الدالة
        copy_button.clicked.connect(lambda _, bound_ip=ip: self.copy_to_clipboard(bound_ip))

        layout.addWidget(ip_label)
        layout.addStretch()
        layout.addWidget(copy_button)
        
        return container

    def copy_to_clipboard(self, text):
        """
        ينسخ النص المحدد إلى حافظة النظام.
        """
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "تم النسخ", f"تم نسخ '{text}' إلى الحافظة.")

# --- نقطة الدخول الرئيسية للتطبيق ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NetworkScannerTab()
    window.show()
    sys.exit(app.exec())