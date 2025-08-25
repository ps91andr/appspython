import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

# تم تغيير الوراثة من QMainWindow إلى QWidget لتكون مناسبة كـ "تبويب"
class PrayerTimesWindow(QWidget):
    def __init__(self):
        super().__init__()
        # لم نعد بحاجة لـ setWindowTitle أو setGeometry هنا

        # الأداة الأولى (العلوية)
        self.widget1 = QWebEngineView()
        url1 = QUrl("https://timesprayer.com/widgets.php?frame=1&lang=ar&name=sanaa&sound=true")
        self.widget1.setUrl(url1)
        self.widget1.setMinimumHeight(130)
        self.widget1.setMaximumHeight(130)

        # الأداة الثانية (السفلية)
        self.widget2 = QWebEngineView()
        url2 = QUrl("https://timesprayer.com/widgets.php?frame=1&lang=ar&name=sanaa&sound=true&time=0")
        self.widget2.setUrl(url2)
        self.widget2.setMinimumHeight(130)
        self.widget2.setMaximumHeight(130)

        # التخطيط الرأسي
        layout = QVBoxLayout()
        layout.addWidget(self.widget1)
        layout.addWidget(self.widget2)
        
        # تطبيق التخطيط مباشرة على الويدجت
        self.setLayout(layout)
        
        # لم نعد بحاجة لـ central_widget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # لاختبار هذا الملف بشكل مستقل، نضعه داخل نافذة رئيسية
    main_test_window = QMainWindow()
    prayer_widget = PrayerTimesWindow()
    main_test_window.setCentralWidget(prayer_widget)
    main_test_window.setWindowTitle("مواقيت الصلاة - صنعاء (اختبار)")
    main_test_window.setGeometry(100, 100, 600, 300)
    main_test_window.show()
    sys.exit(app.exec())