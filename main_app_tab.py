import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget

# --- الخطوة 1: استيراد الواجهات من الملفات الأخرى ---
# تأكد من أن هذا الملف (main_app.py) موجود في نفس المجلد
# مع جميع ملفات الواجهات الأخرى حتى تعمل عملية الاستيراد بنجاح.
try:
    from ai_studio_code_tab import FireTVRemote
    from ai_tab import ADBManager
    from remot_tab import RemoteControlApp
    # --- START OF NEW CODE ---
    from remoot_tab import FireTVController # استيراد الواجهة الجديدة
    # --- END OF NEW CODE ---

except ImportError as e:
    print(f"خطأ في الاستيراد: {e}")
    print("يرجى التأكد من وجود ملفات 'ai_studio_code_tab.py', 'ai_tab.py', 'remot_tab.py', و 'remoot_tab.py' في نفس المجلد.")
    sys.exit(1)


class MainApplication(QMainWindow):
    """
    النافذة الرئيسية التي تحتوي على واجهات متعددة في تبويبات.
    """
    def __init__(self):
        super().__init__()

        # --- إعداد النافذة الرئيسية ---
        self.setWindowTitle("تطبيق متعدد الواجهات")
        self.setGeometry(50, 50, 1050, 900)  # تحديث حجم النافذة لاستيعاب الواجهة الجديدة

        # --- إنشاء أداة التبويبات ---
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North) # وضع التبويبات في الأعلى
        self.tabs.setMovable(True)  # السماح للمستخدم بتحريك وترتيب التبويبات

        # --- الخطوة 2: إنشاء نسخة من كل واجهة وإضافتها كـ تبويب ---

        # --- START OF NEW CODE ---
        # إنشاء نسخة من واجهة "FireTV Controller Pro" وإضافتها كأول تبويب
        self.fire_tv_controller_widget = FireTVController()
        self.tabs.addTab(self.fire_tv_controller_widget, "⚙️ FireTV Controller Pro")
        # --- END OF NEW CODE ---
        
        # إنشاء نسخة من واجهة "FireTV Remote"
        self.fire_tv_remote_widget = FireTVRemote()
        self.tabs.addTab(self.fire_tv_remote_widget, "🎮 FireTV Remote")

        # إنشاء نسخة من واجهة "ADB Manager"
        self.adb_manager_widget = ADBManager()
        self.tabs.addTab(self.adb_manager_widget, "📡 ADB Manager")

        # إنشاء نسخة من واجهة "Remote Control"
        self.remote_control_widget = RemoteControlApp()
        self.tabs.addTab(self.remote_control_widget, "📱 Remote Control")

        # --- الخطوة 3: تعيين أداة التبويبات كواجهة مركزية للنافذة الرئيسية ---
        self.setCentralWidget(self.tabs)


if __name__ == '__main__':
    # --- نقطة انطلاق التطبيق ---
    app = QApplication(sys.argv)
    main_window = MainApplication()
    main_window.show()
    sys.exit(app.exec())