import sys
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QGridLayout, QSpinBox,
    QPushButton, QHBoxLayout, QLineEdit, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QFont
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

# --- فئة الإشعارات المنبثقة (Toast) ---
class Toast(QWidget):
    # متغير ثابت لتتبع عدد الإشعارات وتكديسها
    toast_count = 0
    
    def __init__(self, parent=None, message="", level="info", duration=3000):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose) # للتنظيف التلقائي
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout()
        self.label = QLabel(message)
        self.label.setWordWrap(True)
        self.label.setStyleSheet(self.get_style(level))
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.adjustSize()
        self.setFixedWidth(300)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.hide_toast)
        self.timer.start(duration)

        self.fade_timer = None
        self.opacity = 1.0

    def get_style(self, level):
        """تحديد ألوان الإشعار بناءً على مستواه"""
        colors = {
            "info": "#17a2b8",    # أزرق
            "success": "#28a745", # أخضر
            "warning": "#ffc107", # أصفر
            "error": "#dc3545"    # أحمر
        }
        bg = colors.get(level, "#17a2b8")
        return f"""
        QLabel {{
            background-color: {bg};
            color: white;
            padding: 10px;
            margin: 0px;
            border-radius: 8px;
            font-size: 13px;
        }}
        """

    def show_and_stack(self):
        """إظهار الإشعار في الركن الأيمن السفلي من الشاشة وتكديسه"""
        screen_geometry = QApplication.primaryScreen().geometry()
        toast_height = self.height()
        
        # حساب الموضع بناءً على عدد الإشعارات المفتوحة
        x = screen_geometry.right() - self.width() - 20
        y = screen_geometry.bottom() - toast_height - 50 - (Toast.toast_count * (toast_height + 10))
        
        self.move(x, y)
        self.show()
        Toast.toast_count += 1

    def hide_toast(self):
        """بدء تأثير التلاشي للإخفاء"""
        self.timer.stop()
        if not self.fade_timer:
            self.fade_timer = QTimer(self)
            self.fade_timer.timeout.connect(self.fade_out)
            self.fade_timer.start(25) # سرعة التلاشي

    def fade_out(self):
        """تقليل الشفافية تدريجيًا ثم إغلاق الإشعار"""
        self.opacity -= 0.02
        if self.opacity <= 0:
            self.fade_timer.stop()
            Toast.toast_count = max(0, Toast.toast_count - 1) # إنقاص العداد
            self.close() # إغلاق وحذف الويدجت
        else:
            self.setWindowOpacity(self.opacity)


# --- فئة نافذة التطبيق الرئيسية ---
class WaterReminder(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("تذكير بشرب الماء💧")
        self.setGeometry(100, 100, 400, 320)

        # متغيرات الحالة
        self.remaining_seconds = 0
        self.sound_file_path = None
        self.is_paused = False

        # --- مشغل الصوت ---
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        # --- واجهة المستخدم ---
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 1. شاشة العد التنازلي
        self.countdown_label = QLabel("00:00", self)
        font = QFont("Arial", 56, QFont.Weight.Bold)
        self.countdown_label.setFont(font)
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.countdown_label)

        # 2. قسم الإعدادات
        settings_layout = QGridLayout()
        settings_layout.setColumnStretch(0, 1)
        settings_layout.setColumnStretch(1, 1)
        
        settings_layout.addWidget(QLabel("<b>الوقت (دقائق):</b>"), 0, 1, Qt.AlignmentFlag.AlignRight)
        self.time_input = QSpinBox()
        self.time_input.setMinimum(1)
        self.time_input.setMaximum(120)
        self.time_input.setValue(30)
        settings_layout.addWidget(self.time_input, 1, 1)

        settings_layout.addWidget(QLabel("<b>الصوت:</b>"), 0, 0, Qt.AlignmentFlag.AlignLeft)
        sound_buttons_layout = QHBoxLayout()
        self.select_sound_button = QPushButton("اختر ملف")
        self.select_sound_button.clicked.connect(self.select_sound_file)
        sound_buttons_layout.addWidget(self.select_sound_button)

        self.test_sound_button = QPushButton("تجربة💧")
        self.test_sound_button.clicked.connect(self.test_sound)
        self.test_sound_button.setEnabled(False)
        sound_buttons_layout.addWidget(self.test_sound_button)
        settings_layout.addLayout(sound_buttons_layout, 1, 0)
        
        main_layout.addLayout(settings_layout)

        # 3. عرض مسار الملف الصوتي
        self.sound_path_display = QLineEdit()
        self.sound_path_display.setPlaceholderText("اختر ملف صوتي أو استخدم الافتراضي...")
        self.sound_path_display.setReadOnly(True)
        self.sound_path_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.sound_path_display)

        # 4. أزرار التحكم الرئيسية
        action_buttons_layout = QHBoxLayout()
        
        self.start_button = QPushButton("💧💧بدء💧💧")
        self.start_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        self.start_button.clicked.connect(self.start_reminders)
        action_buttons_layout.addWidget(self.start_button)
        
        self.pause_resume_button = QPushButton("إيقاف مؤقت💧")
        self.pause_resume_button.setStyleSheet("background-color: #2196F3; color: white; padding: 10px; font-weight: bold;")
        self.pause_resume_button.clicked.connect(self.toggle_pause)
        self.pause_resume_button.setEnabled(False)
        action_buttons_layout.addWidget(self.pause_resume_button)

        self.stop_button = QPushButton("إيقاف كلي💧")
        self.stop_button.setStyleSheet("background-color: #f44336; color: white; padding: 10px; font-weight: bold;")
        self.stop_button.clicked.connect(self.stop_reminders)
        self.stop_button.setEnabled(False)
        action_buttons_layout.addWidget(self.stop_button)
        
        main_layout.addLayout(action_buttons_layout)
        
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_countdown)

        # --- تحميل الإعدادات المحفوظة ---
        self.load_settings()

        # --- ربط الحفظ التلقائي عند التغيير ---
        self.time_input.valueChanged.connect(self.save_settings)

    def closeEvent(self, event):
        """حفظ الإعدادات عند إغلاق النافذة"""
        self.save_settings()
        super().closeEvent(event)

    def get_config_path(self):
        """إرجاع مسار ملف الإعدادات"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "config.json")

    def load_settings(self):
        """تحميل الإعدادات من ملف JSON"""
        config_file = self.get_config_path()
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                self.time_input.setValue(config.get("time_minutes", 30))
                sound_path = config.get("sound_file_path")
                if sound_path and os.path.exists(sound_path):
                    self.load_sound(sound_path)
                    return
        except Exception as e:
            print(f"خطأ في تحميل الإعدادات: {e}")

        # تحميل الصوت الافتراضي إذا لم يتم العثور على إعدادات
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_sound_path = os.path.join(base_dir, "pomodoro_sounds", "water.mp3")
        self.load_sound(default_sound_path)

    def save_settings(self):
        """حفظ الإعدادات إلى ملف JSON"""
        config = {
            "time_minutes": self.time_input.value(),
            "sound_file_path": self.sound_file_path
        }
        try:
            with open(self.get_config_path(), 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.show_toast("خطأ", f"خطأ في حفظ الإعدادات: {e}", level="error")

    def select_sound_file(self):
        """فتح نافذة اختيار الصوت، ثم حفظ الإعدادات"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف الصوت", "", "ملفات الصوت (*.mp3 *.wav *.ogg);;كل الملفات (*.*)"
        )
        if file_path:
            self.load_sound(file_path)
            self.save_settings()

    def toggle_pause(self):
        """تبديل حالة المؤقت بين الإيقاف المؤقت والاستئناف"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.countdown_timer.stop()
            self.pause_resume_button.setText("استئناف💧")
            self.show_toast("إيقاف مؤقت", "تم إيقاف المؤقت مؤقتًا.", level="warning")
        else:
            self.countdown_timer.start(1000)
            self.pause_resume_button.setText("إيقاف مؤقت💧")
            self.show_toast("استئناف", "تم استئناف المؤقت.", level="info")

    def start_reminders(self):
        minutes = self.time_input.value()
        self.remaining_seconds = minutes * 60
        self.update_time_display()
        self.countdown_timer.start(1000)
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.pause_resume_button.setEnabled(True)
        self.time_input.setEnabled(False)
        self.select_sound_button.setEnabled(False)
        
        self.show_toast("بدء", f"تم بدء التذكيرات! سيتم تذكيرك كل {minutes} دقيقة.", level="success")

    def stop_reminders(self):
        """إيقاف كلي يعيد كل شيء إلى حالته الأولية"""
        self.countdown_timer.stop()
        self.remaining_seconds = 0
        self.update_time_display()
        self.is_paused = False
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.pause_resume_button.setEnabled(False)
        self.pause_resume_button.setText("إيقاف مؤقت💧")
        self.time_input.setEnabled(True)
        self.select_sound_button.setEnabled(True)
        
        self.show_toast("إيقاف", "تم إيقاف التذكيرات بشكل كامل.", level="error")
        
    def load_sound(self, file_path):
        if file_path and os.path.exists(file_path):
            self.sound_file_path = file_path
            self.sound_path_display.setText(os.path.basename(file_path))
            self.sound_path_display.setToolTip(file_path)
            self.player.setSource(QUrl.fromLocalFile(self.sound_file_path))
            self.test_sound_button.setEnabled(True) 
        else:
            self.sound_file_path = None
            self.sound_path_display.setText("")
            self.sound_path_display.setPlaceholderText("لم يتم العثور على الملف الصوتي!")
            self.test_sound_button.setEnabled(False) 

    def test_sound(self):
        if self.sound_file_path and self.player.source().isValid():
            self.player.setPosition(0) 
            self.player.play()
        else:
            self.show_toast("خطأ", "الرجاء اختيار ملف صوتي صالح أولاً!", level="warning")

    def update_countdown(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
        else:
            self.show_notification()
            minutes = self.time_input.value()
            self.remaining_seconds = minutes * 60
        self.update_time_display()

    def update_time_display(self):
        mins = self.remaining_seconds // 60
        secs = self.remaining_seconds % 60
        time_str = f"{mins:02d}:{secs:02d}"
        self.countdown_label.setText(time_str)

    def show_notification(self):
        self.test_sound()
        self.show_toast("💧تنبيه💧", "حان الآن وقت شرب الماء!", duration=5000)

    def show_toast(self, title, message, level="info", duration=4000):
        full_msg = f"<b>{title}</b><br>{message}"
        toast = Toast(self, full_msg, level, duration)
        toast.show_and_stack()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WaterReminder()
    window.show()
    sys.exit(app.exec())