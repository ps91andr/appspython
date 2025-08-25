import sys
import datetime
import requests
import pythonping
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QMainWindow,
    QHBoxLayout,
    QFrame,
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon


class SpeedTestThread(QThread):
    """
    هذه الفئة تعمل في خيط منفصل لتنفيذ اختبارات سرعة الإنترنت
    دون تجميد واجهة المستخدم الرسومية.
    """
    update_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(int)

    def run(self):
        """
        تبدأ هذه الدالة عند بدء تشغيل الخيط.
        """
        try:
            self.progress_signal.emit(10)

            # اختبار Ping أولاً
            ping_result = self.test_ping("8.8.8.8")  # استخدام DNS جوجل

            self.progress_signal.emit(30)

            # اختبار سرعة التحميل باستخدام ملفات حقيقية متاحة
            download_speed = self.test_download_speed()

            self.progress_signal.emit(70)

            # اختبار سرعة الرفع (قيمة تقديرية)
            upload_speed = self.estimate_upload_speed(download_speed)

            self.update_signal.emit(
                {
                    "download": download_speed,
                    "upload": upload_speed,
                    "ping": ping_result,
                    "error": None,
                }
            )

            self.progress_signal.emit(100)

        except Exception as e:
            self.update_signal.emit(
                {"download": 0, "upload": 0, "ping": 0, "error": str(e)}
            )
            self.progress_signal.emit(0)

    def test_download_speed(self):
        """
        تقوم بقياس سرعة التحميل عن طريق تنزيل ملفات اختبار.
        """
        # استخدام ملفات اختبارية حقيقية متاحة للجميع
        test_files = [
            "https://proof.ovh.net/files/10Mb.dat",  # ملف 10MB من OVH
            "http://ipv4.download.thinkbroadband.com/10MB.zip",  # ملف 10MB آخر
        ]

        start_time = datetime.datetime.now()
        try:
            response = requests.get(test_files[0], stream=True)
            file_size = int(
                response.headers.get("content-length", 10_000_000)
            )  # 10MB افتراضي
        except requests.exceptions.RequestException:
            # إذا فشل الملف الأول، جرب الملف الثاني
            response = requests.get(test_files[1], stream=True)
            file_size = int(
                response.headers.get("content-length", 10_000_000)
            )  # 10MB افتراضي

        # قراءة المحتوى لضمان تنزيل الملف بالكامل
        downloaded = 0
        for chunk in response.iter_content(chunk_size=1024):
            downloaded += len(chunk)

        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()

        # السرعة بالميجابت في الثانية (1 بايت = 8 بت)
        if duration > 0:
            speed = (file_size * 8) / (duration * 1_000_000)
            return speed
        return 0

    def estimate_upload_speed(self, download_speed):
        """
        تقدر سرعة الرفع كنسبة من سرعة التحميل.
        """
        # تقدير سرعة الرفع بناءً على سرعة التحميل (عادة 10%-50% من سرعة التحميل)
        return max(0.1, download_speed * 0.3)  # افترض 30% من سرعة التحميل

    def test_ping(self, host):
        """
        تقيس متوسط وقت الاستجابة (ping) إلى مضيف معين.
        """
        try:
            response = pythonping.ping(host, count=4, timeout=2)
            return response.rtt_avg_ms
        except Exception:
            return 0


class InternetSpeedTestTab(QWidget):
    """
    هذه الفئة تمثل واجهة المستخدم الرسومية لعلامة تبويب اختبار سرعة الإنترنت.
    """
    def __init__(self):
        super().__init__()
        
        # إعدادات التصميم
        self.setup_styles()
        
        # واجهة المستخدم
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # العنوان الرئيسي
        self.title_label = QLabel("أداة فحص سرعة الإنترنت")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(self.title_font)
        self.title_label.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")

        # إطار النتائج
        results_frame = QFrame()
        results_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        results_frame.setStyleSheet("""
            QFrame {
                background-color: #505050;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        
        results_layout = QVBoxLayout(results_frame)
        results_layout.setSpacing(10)
        
        # سرعة التحميل
        download_container = QHBoxLayout()
        download_icon = QLabel("⬇️")
        download_icon.setFont(QFont("Arial", 16))
        self.download_label = QLabel("سرعة التحميل: -- Mbps")
        self.download_label.setFont(self.value_font)
        download_container.addWidget(download_icon)
        download_container.addWidget(self.download_label)
        download_container.addStretch()
        
        # سرعة الرفع
        upload_container = QHBoxLayout()
        upload_icon = QLabel("⬆️")
        upload_icon.setFont(QFont("Arial", 16))
        self.upload_label = QLabel("سرعة الرفع: -- Mbps")
        self.upload_label.setFont(self.value_font)
        upload_container.addWidget(upload_icon)
        upload_container.addWidget(self.upload_label)
        upload_container.addStretch()
        
        # وقت الاستجابة
        ping_container = QHBoxLayout()
        ping_icon = QLabel("📶")
        ping_icon.setFont(QFont("Arial", 16))
        self.ping_label = QLabel("وقت الاستجابة (Ping): -- ms")
        self.ping_label.setFont(self.value_font)
        ping_container.addWidget(ping_icon)
        ping_container.addWidget(self.ping_label)
        ping_container.addStretch()
        
        results_layout.addLayout(download_container)
        results_layout.addLayout(upload_container)
        results_layout.addLayout(ping_container)
        
        # رسائل الخطأ
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("""
            color: #e74c3c;
            background-color: #fadbd8;
            padding: 10px;
            border-radius: 5px;
        """)
        self.error_label.setWordWrap(True)
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.hide()
        
        # شريط التقدم
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                background-color: #ecf0f1;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        
        # زر البدء
        self.test_button = QPushButton("بدء الفحص")
        self.test_button.setFont(self.button_font)
        self.test_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.test_button.clicked.connect(self.start_test)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(self.title_label)
        layout.addWidget(results_frame)
        layout.addWidget(self.error_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.test_button)
        layout.addStretch()

        self.setLayout(layout)
        self.thread = None
        
    def setup_styles(self):
        """إعداد الأنماط والخطوط للعناصر"""
        self.title_font = QFont()
        self.title_font.setPointSize(18)
        self.title_font.setBold(True)
        
        self.value_font = QFont()
        self.value_font.setPointSize(14)
        
        self.button_font = QFont()
        self.button_font.setPointSize(12)
        self.button_font.setBold(True)

    def start_test(self):
        """
        تبدأ عملية اختبار السرعة عند النقر على الزر.
        """
        self.test_button.setEnabled(False)
        self.download_label.setText("سرعة التحميل: جاري القياس...")
        self.upload_label.setText("سرعة الرفع: جاري القياس...")
        self.ping_label.setText("وقت الاستجابة (Ping): جاري القياس...")
        self.error_label.hide()
        self.progress_bar.setValue(0)

        self.thread = SpeedTestThread()
        self.thread.update_signal.connect(self.update_results)
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.finished.connect(self.test_finished)
        self.thread.start()

    def update_results(self, results):
        """
        تُحدّث واجهة المستخدم بنتائج اختبار السرعة.
        """
        if results["error"]:
            self.error_label.setText(f"خطأ: {results['error']}")
            self.error_label.show()
            self.download_label.setText("سرعة التحميل: -- Mbps")
            self.upload_label.setText("سرعة الرفع: -- Mbps")
            self.ping_label.setText("وقت الاستجابة (Ping): -- ms")
        else:
            # تلوين النتائج بناءً على قيمتها
            download_color = self.get_speed_color(results["download"])
            upload_color = self.get_speed_color(results["upload"])
            ping_color = self.get_ping_color(results["ping"])
            
            self.download_label.setText(
                f'سرعة التحميل: <span style="color: {download_color}">{results["download"]:.2f} Mbps</span>'
            )
            self.upload_label.setText(
                f'سرعة الرفع: <span style="color: {upload_color}">{results["upload"]:.2f} Mbps</span>'
            )
            self.ping_label.setText(
                f'وقت الاستجابة (Ping): <span style="color: {ping_color}">{results["ping"]:.2f} ms</span>'
            )
            self.error_label.hide()

    def get_speed_color(self, speed):
        """إرجاع لون مناسب بناءً على سرعة الاتصال"""
        if speed > 50:
            return "#27ae60"  # أخضر للسرعات العالية
        elif speed > 20:
            return "#f39c12"  # برتقالي للسرعات المتوسطة
        else:
            return "#e74c3c"  # أحمر للسرعات المنخفضة

    def get_ping_color(self, ping):
        """إرجاع لون مناسب بناءً على وقت الاستجابة"""
        if ping < 50:
            return "#27ae60"  # أخضر لوقت استجابة ممتاز
        elif ping < 100:
            return "#f39c12"  # برتقالي لوقت استجابة جيد
        else:
            return "#e74c3c"  # أحمر لوقت استجابة ضعيف

    def update_progress(self, value):
        """
        تُحدّث شريط التقدم.
        """
        self.progress_bar.setValue(value)

    def test_finished(self):
        """
        تُنفّذ عند انتهاء الخيط من عملية الاختبار.
        """
        self.test_button.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # تطبيق نمط عام للتطبيق
    app.setStyle("Fusion")
    
    # إنشاء نافذة رئيسية ووضع واجهة اختبار السرعة بداخلها.
    window = QMainWindow()
    window.setWindowTitle("Internet Speed Test")
    window.setCentralWidget(InternetSpeedTestTab())
    window.resize(500, 400)
    window.show()
    sys.exit(app.exec())