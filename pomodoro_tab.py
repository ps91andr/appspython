import sys
import os
import json
import threading
import time
import platform

# --- PyQt6 Imports ---
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QGroupBox, QSpinBox, QCheckBox, QRadioButton, QProgressBar,
    QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen

# --- Pygame for sound ---
# تأكد من تثبيت مكتبة pygame باستخدام: pip install pygame
from pygame import mixer

# --- فئة الإشعارات (Toast) ---
class Toast(QWidget):
    """
    فئة لإنشاء إشعار مؤقت (Toast) يظهر ويختفي.
    يتم تتبّع عدد الإشعارات المعروضة لتجنب تداخلها.
    """
    # متغير ثابت لتتبع عدد الإشعارات النشطة
    active_toasts = []

    def __init__(self, parent=None, message="", level="info", duration=3000):
        super().__init__(parent)
        # إعدادات النافذة لتكون بدون إطار، شفافة، وتبقى في الأعلى
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        self.label = QLabel(message)
        self.label.setWordWrap(True)
        self.label.setStyleSheet(self.get_style(level))
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.setContentsMargins(10, 5, 10, 5)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.adjustSize()
        self.setFixedWidth(300)

        # مؤقت لبدء التلاشي بعد انتهاء المدة
        QTimer.singleShot(duration, self.start_fade_out)

        # متغيرات لتأثير التلاشي
        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self.fade_out)
        self.current_opacity = 1.0

    def get_style(self, level):
        """تحديد لون الخلفية بناءً على مستوى الإشعار."""
        colors = {
            "info": "#17a2b8",      # أزرق
            "success": "#28a745",   # أخضر
            "warning": "#ffc107",   # أصفر
            "error": "#dc3545"      # أحمر
        }
        bg_color = colors.get(level, "#17a2b8")
        
        return f"""
        QLabel {{
            background-color: {bg_color};
            color: white;
            padding: 10px;
            border-radius: 8px;
            font-size: 13px;
            font-family: Arial, sans-serif;
        }}
        """

    def show_toast(self):
        """عرض الإشعار في الركن السفلي الأيمن من الشاشة."""
        screen_geometry = QApplication.primaryScreen().geometry()
        
        # حساب الموضع الرأسي لتجنب التداخل
        y_pos = screen_geometry.bottom() - self.height() - 40
        for t in Toast.active_toasts:
            y_pos -= (t.height() + 10)

        x_pos = screen_geometry.right() - self.width() - 20
        
        self.move(x_pos, y_pos)
        self.setWindowOpacity(1.0)
        self.show()
        Toast.active_toasts.append(self)

    def start_fade_out(self):
        """بدء تأثير التلاشي عند إخفاء الإشعار."""
        self.fade_timer.start(20) # تحديث الشفافية كل 20 مللي ثانية

    def fade_out(self):
        """تقليل الشفافية تدريجياً."""
        self.current_opacity -= 0.05
        if self.current_opacity <= 0:
            self.fade_timer.stop()
            Toast.active_toasts.remove(self)
            self.close() # إغلاق الويدجت لتحرير الذاكرة
        else:
            self.setWindowOpacity(self.current_opacity)

# دالة مساعدة لعرض الإشعارات بسهولة
def show_toast(parent, title, message, level="info", duration=3000):
    """إنشاء وعرض إشعار Toast."""
    full_message = f"<b>{title}</b><br>{message}"
    toast = Toast(parent, full_message, level, duration)
    toast.show_toast()

# --- فئة المؤشر الدائري ---
class CircularProgress(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress = 0.0  # القيمة من 0.0 إلى 1.0
        self.primary_color = QColor("#4C566A")
        self.progress_color = QColor("#A3BE8C")
        self.setMinimumSize(180, 180)

    def setProgress(self, value: float):
        """تحديث قيمة التقدم وإعادة رسم الويدجت."""
        self.progress = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, event):
        """رسم المؤشر الدائري."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(10, 10, -10, -10)
        
        # رسم خلفية الدائرة (المسار الكامل)
        pen = QPen(self.primary_color, 14, Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        # رسم التقدم
        pen.setColor(self.progress_color)
        painter.setPen(pen)
        
        angle = int(self.progress * 360)
        painter.drawArc(rect, 90 * 16, -angle * 16)

# --- فئة التطبيق الرئيسية ---
class CustomStartPomodoroApp(QWidget):
    def __init__(self):
        super().__init__()
 
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.run_timer)
 
        self.is_running = False
        self.pomodoro_count = 0
        self.completed_sessions = 0
        self.is_work_session = True
        
        mixer.init()
        
        self.default_dir = os.path.join(os.getcwd(), "pomodoro_sounds")
        self.work_sound = os.path.join(self.default_dir, "work_start.wav")
        self.break_sound = os.path.join(self.default_dir, "break_start.wav")
        self.alarm_sound = os.path.join(self.default_dir, "alarm.wav")
        
        if not os.path.exists(self.default_dir):
            os.makedirs(self.default_dir)
            self.create_default_sounds()
        
        self.settings_file = os.path.join(os.getcwd(), "pomodoro_settings.json")
        
        self.init_ui()
        self.apply_styles()
        self.load_settings()
        self.reset_timer()

    def create_default_sounds(self):
        """إنشاء أصوات افتراضية إذا لم تكن موجودة."""
        if platform.system() == "Windows":
            try:
                import winsound
                # الأفضل هو توفير ملفات صوتية حقيقية مع التطبيق
                if not os.path.exists(self.alarm_sound):
                     winsound.Beep(1000, 1000)
            except Exception as e:
                print(f"لا يمكن إنشاء الأصوات الافتراضية: {e}")

    def play_sound(self, sound_type):
        """تشغيل الصوت في خيط منفصل لتجنب تجميد الواجهة."""
        if not self.sound_check.isChecked():
            return
            
        def play():
            sound_path = ""
            if sound_type == "work": sound_path = self.work_sound
            elif sound_type == "break": sound_path = self.break_sound
            elif sound_type == "alarm": sound_path = self.alarm_sound
            
            if os.path.exists(sound_path):
                try:
                    mixer.music.load(sound_path)
                    mixer.music.play()
                except Exception as e:
                    show_toast(self, "خطأ صوتي", f"لم يتمكن من تشغيل: {os.path.basename(sound_path)}", level="error")
            else:
                show_toast(self, "ملف مفقود", f"ملف الصوت غير موجود: {os.path.basename(sound_path)}", level="warning")
        
        threading.Thread(target=play, daemon=True).start()

    def select_sound_file(self, sound_type):
        """فتح حوار لاختيار ملف صوتي."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"اختر ملف صوتي لـ {sound_type}", self.default_dir,
            "ملفات الصوت (*.wav *.mp3);;كل الملفات (*.*)"
        )
        if file_path:
            label_to_update = None
            if sound_type == "work":
                self.work_sound = file_path
                label_to_update = self.work_sound_label
            elif sound_type == "break":
                self.break_sound = file_path
                label_to_update = self.break_sound_label
            elif sound_type == "alarm":
                self.alarm_sound = file_path
                label_to_update = self.alarm_sound_label
            
            if label_to_update:
                label_to_update.setText(os.path.basename(file_path))
            
            show_toast(self, "تحديث", f"تم تعيين صوت {sound_type} بنجاح.", level="info")
            self.save_settings()

    def init_ui(self):
        """بناء واجهة المستخدم الرسومية."""
        self.setWindowTitle("Pomodoro Pro")
        self.setMinimumWidth(480)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # --- العنوان ---
        self.title_label = QLabel("Pomodoro Pro")
        self.title_label.setObjectName("title_label")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.title_label)
        
        # --- مؤشر التقدم الدائري ---
        canvas_container_layout = QGridLayout()
        canvas_container_layout.setContentsMargins(0, 10, 0, 10)
        self.progress_canvas = CircularProgress()
        
        self.time_label = QLabel("25:00")
        self.time_label.setObjectName("time_label")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.session_state_label = QLabel("ابدأ جلسة عمل")
        self.session_state_label.setObjectName("session_state_label")
        self.session_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        canvas_container_layout.addWidget(self.progress_canvas, 0, 0, Qt.AlignmentFlag.AlignCenter)
        canvas_container_layout.addWidget(self.time_label, 0, 0, Qt.AlignmentFlag.AlignCenter)
        # تعديل موضع تسمية الحالة لتكون أسفل الوقت
        vbox_in_grid = QVBoxLayout()
        vbox_in_grid.addStretch()
        vbox_in_grid.addWidget(self.session_state_label)
        vbox_in_grid.addSpacing(40) # إضافة مسافة فارغة أسفل التسمية
        canvas_container_layout.addLayout(vbox_in_grid, 0, 0, Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(canvas_container_layout)
        
        # --- شريط تقدم الجلسات ---
        self.sessions_progress_label = QLabel("تقدم الجلسات: 0/4 (0%)")
        self.sessions_progress = QProgressBar()
        main_layout.addWidget(self.sessions_progress_label)
        main_layout.addWidget(self.sessions_progress)
        
        # --- أزرار التحكم ---
        control_layout = QHBoxLayout()
        self.start_button = QPushButton("بدء")
        self.pause_button = QPushButton("إيقاف مؤقت")
        self.reset_button = QPushButton("إعادة تعيين")
        self.start_button.setObjectName("start_button")
        self.pause_button.setObjectName("pause_button")
        self.reset_button.setObjectName("reset_button")
        self.pause_button.setEnabled(False)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.reset_button)
        main_layout.addLayout(control_layout)
        
        # --- Tabs للإعدادات ---
        from PyQt6.QtWidgets import QTabWidget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # --- Tab 1: إعدادات الجلسة ---
        session_settings_widget = QWidget()
        settings_layout = QGridLayout(session_settings_widget)
        self.work_var = QSpinBox(minimum=1, maximum=90, value=25)
        self.short_break_var = QSpinBox(minimum=1, maximum=30, value=5)
        self.long_break_var = QSpinBox(minimum=1, maximum=60, value=15)
        self.sessions_var = QSpinBox(minimum=1, maximum=12, value=4)
        
        start_with_layout = QHBoxLayout()
        self.start_with_work = QRadioButton("العمل")
        self.start_with_break = QRadioButton("الراحة")
        self.start_with_work.setChecked(True)
        start_with_layout.addWidget(self.start_with_work)
        start_with_layout.addWidget(self.start_with_break)
        
        settings_layout.addWidget(QLabel("وقت العمل (دقائق):"), 0, 0)
        settings_layout.addWidget(self.work_var, 0, 1)
        settings_layout.addWidget(QLabel("راحة قصيرة (دقائق):"), 1, 0)
        settings_layout.addWidget(self.short_break_var, 1, 1)
        settings_layout.addWidget(QLabel("راحة طويلة (دقائق):"), 2, 0)
        settings_layout.addWidget(self.long_break_var, 2, 1)
        settings_layout.addWidget(QLabel("جلسات قبل الراحة الطويلة:"), 3, 0)
        settings_layout.addWidget(self.sessions_var, 3, 1)
        settings_layout.addWidget(QLabel("بدء الجلسة الأولى بـ:"), 4, 0)
        settings_layout.addLayout(start_with_layout, 4, 1)

        # --- Tab 2: إعدادات الأصوات ---
        sound_settings_widget = QWidget()
        sound_layout = QGridLayout(sound_settings_widget)
        
        self.auto_start_check = QCheckBox("البدء التلقائي للجلسة التالية")
        self.sound_check = QCheckBox("تشغيل مؤثرات صوتية")
        sound_layout.addWidget(self.auto_start_check, 0, 0, 1, 2)
        sound_layout.addWidget(self.sound_check, 1, 0, 1, 2)
        
        sound_layout.addWidget(QLabel("صوت بدء العمل:"), 2, 0)
        self.work_sound_label = QLabel(os.path.basename(self.work_sound))
        work_sound_button = QPushButton("اختيار")
        sound_layout.addWidget(self.work_sound_label, 2, 1)
        sound_layout.addWidget(work_sound_button, 2, 2)

        sound_layout.addWidget(QLabel("صوت بدء الراحة:"), 3, 0)
        self.break_sound_label = QLabel(os.path.basename(self.break_sound))
        break_sound_button = QPushButton("اختيار")
        sound_layout.addWidget(self.break_sound_label, 3, 1)
        sound_layout.addWidget(break_sound_button, 3, 2)
        
        sound_layout.addWidget(QLabel("صوت التنبيه:"), 4, 0)
        self.alarm_sound_label = QLabel(os.path.basename(self.alarm_sound))
        alarm_sound_button = QPushButton("اختيار")
        sound_layout.addWidget(self.alarm_sound_label, 4, 1)
        sound_layout.addWidget(alarm_sound_button, 4, 2)
        
        self.tabs.addTab(session_settings_widget, "إعدادات الجلسة")
        self.tabs.addTab(sound_settings_widget, "إعدادات الصوت والإشعارات")
        
        # --- ربط الإشارات (Signals) ---
        self.start_button.clicked.connect(self.start_timer)
        self.pause_button.clicked.connect(self.pause_timer)
        self.reset_button.clicked.connect(lambda: self.reset_timer(show_toast_msg=True))
        
        work_sound_button.clicked.connect(lambda: self.select_sound_file("work"))
        break_sound_button.clicked.connect(lambda: self.select_sound_file("break"))
        alarm_sound_button.clicked.connect(lambda: self.select_sound_file("alarm"))
        
        self.work_var.valueChanged.connect(self.settings_changed)
        self.short_break_var.valueChanged.connect(self.settings_changed)
        self.long_break_var.valueChanged.connect(self.settings_changed)
        self.sessions_var.valueChanged.connect(self.settings_changed)
        self.start_with_work.toggled.connect(self.settings_changed)
        self.auto_start_check.stateChanged.connect(self.save_settings)
        self.sound_check.stateChanged.connect(self.save_settings)
        
    def apply_styles(self):
        """تطبيق تنسيقات CSS على الواجهة."""
        self.setStyleSheet("""
            QWidget {
                background-color: #2E3440;
                color: #ECEFF4;
                font-family: Arial, sans-serif;
            }
            #title_label {
                font-size: 28px;
                font-weight: bold;
                color: #88C0D0;
                padding-bottom: 5px;
            }
            #time_label {
                font-size: 64px;
                font-weight: bold;
                color: #ECEFF4;
            }
            #session_state_label {
                font-size: 16px;
                font-weight: bold;
                color: #81A1C1;
            }
            QGroupBox {
                font-size: 14px;
                border: 1px solid #4C566A;
                border-radius: 8px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
            }
            QTabWidget::pane {
                border: 1px solid #4C566A;
                border-top: none;
            }
            QTabBar::tab {
                background: #3B4252;
                color: #D8DEE9;
                padding: 8px 20px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #434C5E;
                color: #ECEFF4;
            }
            QPushButton {
                background-color: #4C566A;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover { background-color: #5E81AC; }
            QPushButton:disabled { background-color: #3B4252; color: #4C566A; }
            
            #start_button { background-color: #A3BE8C; }
            #pause_button { background-color: #EBCB8B; }
            #reset_button { background-color: #BF616A; }
            
            QProgressBar {
                border: 1px solid #4C566A;
                border-radius: 5px;
                text-align: center;
                color: #2E3440;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #A3BE8C;
                border-radius: 4px;
            }
            QSpinBox, QCheckBox, QRadioButton, QLabel { font-size: 13px; }
        """)
        
    def settings_changed(self):
        """يتم استدعاؤها عند تغيير إعدادات الجلسة لإعادة الضبط."""
        if not self.is_running:
            self.reset_timer()
        self.save_settings()

    def load_settings(self):
        """تحميل الإعدادات من ملف JSON."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.work_var.setValue(settings.get('work_time', 25))
                    self.short_break_var.setValue(settings.get('short_break', 5))
                    self.long_break_var.setValue(settings.get('long_break', 15))
                    self.sessions_var.setValue(settings.get('sessions', 4))
                    self.start_with_work.setChecked(settings.get('start_with_work', True))
                    self.auto_start_check.setChecked(settings.get('auto_start', True))
                    self.sound_check.setChecked(settings.get('sound_enabled', True))
                    self.work_sound = settings.get('work_sound', self.work_sound)
                    self.break_sound = settings.get('break_sound', self.break_sound)
                    self.alarm_sound = settings.get('alarm_sound', self.alarm_sound)
                    show_toast(self, "نجاح", "تم تحميل الإعدادات المحفوظة.", level="success")
        except (json.JSONDecodeError, KeyError) as e:
            show_toast(self, "خطأ", f"خطأ في ملف الإعدادات: {e}", level="error")
        # تحديث تسميات الملفات الصوتية
        self.work_sound_label.setText(os.path.basename(self.work_sound))
        self.break_sound_label.setText(os.path.basename(self.break_sound))
        self.alarm_sound_label.setText(os.path.basename(self.alarm_sound))

    def save_settings(self):
        """حفظ الإعدادات الحالية في ملف JSON."""
        settings = {
            'work_time': self.work_var.value(),
            'short_break': self.short_break_var.value(),
            'long_break': self.long_break_var.value(),
            'sessions': self.sessions_var.value(),
            'start_with_work': self.start_with_work.isChecked(),
            'auto_start': self.auto_start_check.isChecked(),
            'sound_enabled': self.sound_check.isChecked(),
            'work_sound': self.work_sound,
            'break_sound': self.break_sound,
            'alarm_sound': self.alarm_sound
        }
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            show_toast(self, "خطأ", f"لم يتم حفظ الإعدادات: {e}", level="error")
            
    def update_time_display(self):
        """تحديث عرض الوقت والتقدم الدائري."""
        minutes, seconds = divmod(self.remaining_seconds, 60)
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}")
        
        total_time = self.get_total_time()
        if total_time > 0:
            progress = (total_time - self.remaining_seconds) / total_time
            self.progress_canvas.setProgress(progress)
        else:
            self.progress_canvas.setProgress(0)

    def update_sessions_progress(self):
        """تحديث شريط تقدم الجلسات."""
        total = self.sessions_var.value()
        progress_percent = int((self.completed_sessions / total) * 100) if total > 0 else 0
        self.sessions_progress.setValue(progress_percent)
        self.sessions_progress_label.setText(
            f"تقدم الجلسات: {self.completed_sessions}/{total} ({progress_percent}%)"
        )

    def get_total_time(self):
        """الحصول على مدة الجلسة الحالية بالثواني."""
        if self.is_work_session:
            return self.work_var.value() * 60
        # تحديد نوع الراحة
        elif (self.completed_sessions + 1) % self.sessions_var.value() == 0:
             return self.long_break_var.value() * 60
        else:
            return self.short_break_var.value() * 60

    def start_timer(self):
        if self.is_running: return
        self.is_running = True
        
        if self.is_work_session:
            show_toast(self, "تركيز", "بدأت جلسة العمل. حان وقت الإنتاج!", level="info")
            self.play_sound("work")
        else:
            show_toast(self, "استرخاء", "بدأت فترة الراحة. خذ نفساً عميقاً!", level="success")
            self.play_sound("break")
        
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.tabs.setEnabled(False) # تعطيل الإعدادات أثناء التشغيل
        self.timer.start(1000)

    def pause_timer(self):
        if not self.is_running: return
        self.is_running = False
        self.timer.stop()
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.tabs.setEnabled(True) # إعادة تفعيل الإعدادات
        show_toast(self, "إيقاف مؤقت", "تم إيقاف المؤقت مؤقتاً.", level="warning")
        
    def reset_timer(self, show_toast_msg=False):
        """إعادة تعيين المؤقت إلى حالته الأولية."""
        self.is_running = False
        self.timer.stop()
        self.completed_sessions = 0
        self.is_work_session = self.start_with_work.isChecked()
        
        if self.is_work_session:
            self.remaining_seconds = self.work_var.value() * 60
            self.session_state_label.setText("جلسة عمل")
        else:
            self.remaining_seconds = self.short_break_var.value() * 60
            self.session_state_label.setText("استراحة قصيرة")
        
        self.update_time_display()
        self.update_sessions_progress()
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.tabs.setEnabled(True)
        if show_toast_msg:
            show_toast(self, "إعادة تعيين", "تم إعادة تعيين المؤقت.", level="info")
        
    def run_timer(self):
        """يتم استدعاؤها كل ثانية بواسطة المؤقت."""
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.update_time_display()
        else:
            self.timer.stop()
            self.timer_complete()
            
    def timer_complete(self):
        """تُنفذ عند انتهاء وقت الجلسة."""
        self.is_running = False
        self.play_sound("alarm")

        if self.is_work_session:
            self.completed_sessions += 1
            self.pomodoro_count += 1
            self.is_work_session = False
            
            if self.completed_sessions % self.sessions_var.value() == 0:
                self.remaining_seconds = self.long_break_var.value() * 60
                self.session_state_label.setText("استراحة طويلة")
                show_toast(self, "إنجاز رائع!", "تستحق راحة طويلة!", level="success")
            else:
                self.remaining_seconds = self.short_break_var.value() * 60
                self.session_state_label.setText("استراحة قصيرة")
                show_toast(self, "أحسنت!", "انتهت جلسة العمل. خذ استراحة.", level="success")
        else: 
            self.is_work_session = True
            self.remaining_seconds = self.work_var.value() * 60
            self.session_state_label.setText("جلسة عمل")
            show_toast(self, "انتهت الراحة", "حان وقت العودة إلى العمل!", level="info")
        
        self.update_time_display()
        self.update_sessions_progress()

        if self.auto_start_check.isChecked():
            self.start_timer()
        else:
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.tabs.setEnabled(True)
            
    def closeEvent(self, event):
        """حفظ الإعدادات عند إغلاق التطبيق."""
        self.save_settings()
        mixer.quit()
        event.accept()

# --- نقطة انطلاق التطبيق ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CustomStartPomodoroApp()
    window.show()
    sys.exit(app.exec())