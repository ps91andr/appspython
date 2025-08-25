# -*- coding: utf-8 -*-

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget

# =============================================================================
# استيراد جميع فئات التبويبات من ملفاتها المنفصلة
# =============================================================================
# ملاحظة: تأكد من أن جميع هذه الملفات موجودة في نفس المجلد
# وأن كل ملف يحتوي على الفئة المذكورة.

# يجب توفير ملف editor_tab.py الذي يحتوي على فئة AdvancedEditorTab
from editor_tab import AdvancedEditorTab 

from date_time_tab import DateTimeApp
from image_downloader_tab import ImageDownloaderTab
from scores_tab import ScoresWidget
from weather_tab import WeatherTab
from py_to_exe_tab import PyToExeTab
from translation_tab import TranslationTab
from water_reminder_tab import WaterReminder
from icon_converter_tab import IconConverterTab
from runner_tab import PythonRunnerTab
from code_tab import CodeEditorTab
from admin_tools_tab import AdminToolsTab
from atker_teb import AzkarReminder
from PasswordManager_teb import PasswordManager
from App_tab import App
from satimages_tab import StarsatRemote
from AccountsApp_tab import AccountsApp
from main_app_tab import MainApplication
from network_tab import NetworkScannerTab
from pomodoro_tab import CustomStartPomodoroApp
from prayerr_tab import PrayerrTab
from prayer_tab import PrayerTimesWindow
from currency_tab import CurrencyConverter
from password_generator_tab import PasswordGenerator
from speed_test_tab import InternetSpeedTestTab

# =============================================================================
# الفئة الرئيسية للنافذة التي تجمع كل التبويبات
# =============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("لوحة التحكم الرئيسية")
        self.setGeometry(100, 100, 1280, 720)

        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.tabs.removeTab)

        # 1. إنشاء كائنات من كل فئة تم استيرادها
        self.editor_tab = AdvancedEditorTab()
        self.code_tab = CodeEditorTab()
        self.py_to_exe_tab = PyToExeTab()
        self.icon_converter_tab = IconConverterTab()
        self.runner_tab = PythonRunnerTab()
        self.network_tab = NetworkScannerTab()
        self.admin_tools_tab = AdminToolsTab()
        self.translation_tab = TranslationTab()
        self.pomodoro_tab = CustomStartPomodoroApp()
        self.water_reminder_tab = WaterReminder()
        self.speed_test_tab = InternetSpeedTestTab()
        self.image_downloader_tab = ImageDownloaderTab() 
        self.weather_tab = WeatherTab()
        self.currency_tab = CurrencyConverter()
        self.prayerr_tab = PrayerrTab()
        self.prayer_tab = PrayerTimesWindow()
        self.password_generator_tab = PasswordGenerator()
        self.scores_tab = ScoresWidget()
        self.date_time_tab = DateTimeApp()
        self.atker_teb = AzkarReminder()
        self.PasswordManager_teb = PasswordManager()
        self.App_tab = App()
        self.satimages_tab = StarsatRemote()
        self.AccountsApp_tab = AccountsApp()
        self.main_app_tab = MainApplication()
        
        # منطق بدء التشغيل الخاص بالمحرر المتقدم
        if hasattr(self.editor_tab, 'tab_widget') and self.editor_tab.tab_widget.count() > 0:
            self.editor_tab.tab_widget.removeTab(0)
        if hasattr(self.editor_tab, 'new_tab'):
            self.editor_tab.new_tab(is_welcome_tab=True)

        # 2. إضافة التبويبات إلى الواجهة الرئيسية
        self.tabs.addTab(self.editor_tab, "محرر متقدم")
        self.tabs.addTab(self.code_tab, "إضافة مسافات للأكواد")
        self.tabs.addTab(self.runner_tab, "تشغيل بايثون")
        self.tabs.addTab(self.py_to_exe_tab, "تحويل إلى EXE")
        self.tabs.addTab(self.icon_converter_tab, "محول الأيقونات")
        self.tabs.addTab(self.image_downloader_tab, "🖼️ تنزيل الصور من الويب")
        self.tabs.addTab(self.network_tab, "الشبكة المحلية")
        self.tabs.addTab(self.admin_tools_tab, "أدوات المسؤول")
        self.tabs.addTab(self.translation_tab, "📖 الترجمة الفورية")
        self.tabs.addTab(self.pomodoro_tab, "مؤقت Pomodoro")
        self.tabs.addTab(self.water_reminder_tab, "💧 تذكير شرب الماء")
        self.tabs.addTab(self.speed_test_tab, "🌐 فحص سرعة الإنترنت") 
        self.tabs.addTab(self.weather_tab, "🌤️ الطقس")
        self.tabs.addTab(self.currency_tab, "العملات")
        self.tabs.addTab(self.prayerr_tab, "🕌 مواقيت الصلاة")
        self.tabs.addTab(self.prayer_tab, "🕌 مواقيت الصلاة صنعاء")
        self.tabs.addTab(self.password_generator_tab, "🔒 مولد كلمات المرور")
        self.tabs.addTab(self.scores_tab, "⚽ متابعة المباريات")
        self.tabs.addTab(self.date_time_tab, "📅 الوقت والتاريخ")
        self.tabs.addTab(self.atker_teb, "الاذكار")
        self.tabs.addTab(self.PasswordManager_teb, "PASS")
        self.tabs.addTab(self.App_tab, "App")
        self.tabs.addTab(self.satimages_tab, "Starsat Remote")
        self.tabs.addTab(self.AccountsApp_tab, "AccountsApp")
        self.tabs.addTab(self.main_app_tab, "ADBmainapp")
        
        # 3. تعيين الواجهة الرئيسية
        self.setCentralWidget(self.tabs)

# =============================================================================
# نقطة انطلاق تشغيل التطبيق
# =============================================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())