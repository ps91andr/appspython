from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QLabel, QComboBox, QPushButton, QScrollArea, QFrame, QGridLayout)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
import subprocess
import sys

class RemoteControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Remote Control - Performance Edition")
        self.setGeometry(100, 100, 1040, 750)

# تعريف التنسيقات المختلفة
        self.themes = {
            "التنسيق الفاخر (مذهل)": """
        QMainWindow {
            background-color: #1c1c1c;
            border: 2px solid #2a2a2a;
            border-radius: 10px;
        }
        QPushButton {
            background-color: #3e8e41;
            color: white;
            border: 2px solid #4caf50;
            border-radius: 6px;
            padding: 10px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2e7031;
            border-color: #388e3c;
        }
        QPushButton:pressed {
            background-color: #257a2f;
        }
        QLabel {
            color: #f0f0f0;
            background-color: transparent;
            font-size: 16px;
            font-weight: 600;
        }
        QComboBox {
            background-color: #2b2b2b;
            color: #e0e0e0;
            border: 1px solid #4f4f4f;
            border-radius: 4px;
            padding: 8px;
        }
        QComboBox:hover {
            border-color: #66bb6a;
        }
        QScrollArea {
            border: none;
        }
        QLineEdit {
            background-color: #2b2b2b;
            color: white;
            border: 1px solid #4f4f4f;
            border-radius: 4px;
            padding: 6px;
        }
        QLineEdit:focus {
            border-color: #66bb6a;
        }
    """,

            "تنسيق أزرق ملكي": """
        QMainWindow {
            background-color: #0a2d51;
            border: 2px solid #1b3d75;
            border-radius: 10px;
        }
        QPushButton {
            background-color: #003366;
            color: white;
            border: 2px solid #0066cc;
            border-radius: 6px;
            padding: 12px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #005cbf;
            border-color: #004c99;
        }
        QPushButton:pressed {
            background-color: #004e8c;
        }
        QLabel {
            color: #f1f1f1;
            background-color: transparent;
            font-size: 16px;
            font-weight: 600;
        }
        QComboBox {
            background-color: #1a3e6a;
            color: #f1f1f1;
            border: 1px solid #003366;
            border-radius: 4px;
            padding: 8px;
        }
        QComboBox:hover {
            border-color: #0066cc;
        }
        QLineEdit {
            background-color: #1a3e6a;
            color: white;
            border: 1px solid #003366;
            border-radius: 4px;
            padding: 6px;
        }
        QLineEdit:focus {
            border-color: #0066cc;
        }
    """,

            "تنسيق فاخر (ذهبي)": """
        QMainWindow {
            background-color: #2a2a2a;
            border: 3px solid #3b3b3b;
            border-radius: 12px;
        }
        QPushButton {
            background-color: #f1c40f;
            color: #2c3e50;
            border: 2px solid #f39c12;
            border-radius: 8px;
            padding: 14px;
            font-size: 15px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #e67e22;
            border-color: #d35400;
        }
        QPushButton:pressed {
            background-color: #e74c3c;
        }
        QLabel {
            color: #ecf0f1;
            background-color: transparent;
            font-size: 17px;
            font-weight: 600;
        }
        QComboBox {
            background-color: #34495e;
            color: #ecf0f1;
            border: 1px solid #16a085;
            border-radius: 5px;
            padding: 10px;
        }
        QComboBox:hover {
            border-color: #1abc9c;
        }
        QLineEdit {
            background-color: #34495e;
            color: white;
            border: 1px solid #16a085;
            border-radius: 5px;
            padding: 8px;
        }
        QLineEdit:focus {
            border-color: #1abc9c;
        }
    """,

            "تنسيق سيلفر (فضي)": """
        QMainWindow {
            background-color: #f4f4f4;
            border: 2px solid #bdc3c7;
            border-radius: 8px;
        }
        QPushButton {
            background-color: #95a5a6;
            color: white;
            border: 2px solid #7f8c8d;
            border-radius: 6px;
            padding: 10px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #7f8c8d;
            border-color: #95a5a6;
        }
        QPushButton:pressed {
            background-color: #34495e;
        }
        QLabel {
            color: #2c3e50;
            background-color: transparent;
            font-size: 16px;
            font-weight: 600;
        }
        QComboBox {
            background-color: #ecf0f1;
            color: #2c3e50;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            padding: 8px;
        }
        QComboBox:hover {
            border-color: #95a5a6;
        }
        QLineEdit {
            background-color: #ecf0f1;
            color: #2c3e50;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            padding: 6px;
        }
        QLineEdit:focus {
            border-color: #95a5a6;
        }
    """,

            "التنسيق الافتراضي": """
        QMainWindow {
            background-color: #f0f0f0;
        }
        QPushButton {
            background-color: #e0e0e0;
            color: black;
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            padding: 5px;
            min-width: 40px;
            min-height: 30px;
        }
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        QLabel {
            color: black;
            background-color: #f0f0f0;
        }
        QComboBox {
            background-color: white;
            color: black;
            border: 1px solid #c0c0c0;
            padding: 3px;
        }
        QScrollArea {
            border: none;
        }
    """,

            "تنسيق أزرق فاتح": """
        QMainWindow {
            background-color: #f5f9ff;
        }
        QPushButton {
            background-color: #4a90e2;
            color: white;
            border: 1px solid #3a7bc8;
            border-radius: 4px;
            padding: 5px;
        }
        QPushButton:hover {
            background-color: #3a7bc8;
        }
        QLabel {
            color: #333333;
            background-color: transparent;
        }
        QComboBox {
            background-color: white;
            color: #333333;
            border: 1px solid #cccccc;
        }
    """,

            "تنسيق داكن (Dark Mode)": """
        QMainWindow {
            background-color: #2d2d2d;
        }
        QPushButton {
            background-color: #3a3a3a;
            color: #e0e0e0;
            border: 1px solid #4a4a4a;
            border-radius: 4px;
            padding: 5px;
        }
        QPushButton:hover {
            background-color: #4a4a4a;
        }
        QLabel {
            color: #e0e0e0;
            background-color: transparent;
        }
        QComboBox {
            background-color: #3a3a3a;
            color: #e0e0e0;
            border: 1px solid #4a4a4a;
        }
    """,

            "تنسيق أخضر": """
        QMainWindow {
            background-color: #f0f7f0;
        }
        QPushButton {
            background-color: #4caf50;
            color: white;
            border: 1px solid #3d8b40;
            border-radius: 4px;
            padding: 5px;
        }
        QPushButton:hover {
            background-color: #3d8b40;
        }
        QLabel {
            color: #2e7d32;
            background-color: transparent;
        }
        QComboBox {
            background-color: white;
            color: #2e7d32;
            border: 1px solid #a5d6a7;
        }
    """
        }


        # تطبيق التنسيق الافتراضي
        self.setStyleSheet(self.themes["تنسيق داكن (Dark Mode)"])

        # إنشاء الواجهة الرئيسية
        self.init_ui()

    def init_ui(self):
        # الإطار الرئيسي
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # التخطيط الرئيسي
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # إطار العلوي لاختيار الجهاز والتنسيق
        top_frame = QWidget()
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # تسمية اختيار الجهاز
        device_label = QLabel("اختر الجهاز:")
        device_label.setFont(QFont("Arial", 12))
        top_layout.addWidget(device_label)

        # القائمة المنسدلة لاختيار الجهاز
        self.device_combo = QComboBox()
        self.device_combo.setFont(QFont("Arial", 12))
        self.device_combo.addItems(self.get_connected_devices())
        top_layout.addWidget(self.device_combo)

        # إذا لم تكن هناك أجهزة متصلة
        if self.device_combo.count() == 0:
            self.device_combo.addItem("لا توجد أجهزة متصلة")

        # زر تحديث الأجهزة
        refresh_devices_button = QPushButton("تحديث الأجهزة")
        refresh_devices_button.setFont(QFont("Arial", 12))
        refresh_devices_button.clicked.connect(self.refresh_device_list)
        top_layout.addWidget(refresh_devices_button)

        # إضافة مسافة
        top_layout.addStretch()

        # تسمية اختيار التنسيق
        theme_label = QLabel("اختر التنسيق:")
        theme_label.setFont(QFont("Arial", 12))
        top_layout.addWidget(theme_label)

        # القائمة المنسدلة لاختيار التنسيق
        self.theme_combo = QComboBox()
        self.theme_combo.setFont(QFont("Arial", 12))
        self.theme_combo.addItems(self.themes.keys())
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        top_layout.addWidget(self.theme_combo)

        main_layout.addWidget(top_frame)

        # منطقة التمرير للأزرار
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # إطار داخلي لمنطقة التمرير
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        scroll_layout.setSpacing(10)

        # أزرار التشغيل والإيقاف
        self.create_power_buttons(scroll_layout)

        # أزرار الوسائط
        self.create_media_buttons(scroll_layout)

        # أزرار التنقل الأساسية
        self.create_nav_buttons(scroll_layout)

        # أزرار الاتجاهات
        self.create_direction_buttons(scroll_layout)

        # أزرار النسخ واللصق
        self.create_copy_paste_buttons(scroll_layout)

        # أزرار إضافية
        self.create_extra_buttons(scroll_layout)

        # أزرار الأرقام
        self.create_number_buttons(scroll_layout)

        # أزرار الحروف
        self.create_letter_buttons(scroll_layout)

        # إضافة عنصر مطاطي لدفع كل شيء للأعلى
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

    def change_theme(self, theme_name):
        """تغيير التنسيق بناءً على الاختيار من القائمة المنسدلة"""
        self.setStyleSheet(self.themes[theme_name])

    def get_connected_devices(self):
        """استرداد قائمة الأجهزة المتصلة باستخدام adb devices."""
        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
            lines = result.stdout.strip().split("\n")[1:]
            devices = [line.split("\t")[0] for line in lines if "device" in line]
            return devices
        except Exception as e:
            print(f"خطأ أثناء استرداد الأجهزة: {e}")
            return []

    def refresh_device_list(self):
        """تحديث قائمة الأجهزة في القائمة المنسدلة."""
        self.device_combo.clear()
        devices = self.get_connected_devices()
        if devices:
            self.device_combo.addItems(devices)
        else:
            self.device_combo.addItem("لا توجد أجهزة متصلة")


    def create_power_buttons(self, layout):
        frame = QFrame()
        frame_layout = QHBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(5)

        power_buttons = [
            ('⏻', "تشغيل"), ('⏼', "إيقاف"), ('🔄', "إعادة تشغيل"),
            ('🔌', "تبديل حالة تشغيل الجهاز"), ('💤🌙😴', "نوم"),
            ('☀🌅🌞', "إيقاظ"), ('🔅⬇☀', "تخفيف_السطوع"),
            ('🔆⬆☀', "زيادة_السطوع"), ('🔇', "كتم الصوت"),
            ('🔊+', "رفع الصوت"), ('🔉-', "خفض الصوت")
        ]

        for text, cmd in power_buttons:
            btn = QPushButton(text)
            btn.setFont(QFont("Arial", 12))
            btn.setToolTip(f"وظيفة الزر: {cmd}")
            btn.clicked.connect(lambda _, v=cmd: self.button_click(v))
            frame_layout.addWidget(btn)

        layout.addWidget(frame)

    def create_media_buttons(self, layout):
        frame = QFrame()
        frame_layout = QHBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(5)

        media_buttons = [
            ('▶', "تشغيل الوسائط"), ('⏸️', "إيقاف الوسائط"), ('⏭️', "التالي"),
            ('⏮️', "السابق"), ('⏩', "تسريع"), ('⏪', "تأخير"),
            ('🖼️', "صورة داخل صورة"), ('🎬', "ترجمات"),
            ('📻', "مسار_صوتي"), ('📢', "وصف_صوتي")
        ]

        for text, cmd in media_buttons:
            btn = QPushButton(text)
            btn.setFont(QFont("Arial", 12))
            btn.setToolTip(f"وظيفة الزر: {cmd}")
            btn.clicked.connect(lambda _, v=cmd: self.button_click(v))
            frame_layout.addWidget(btn)

        layout.addWidget(frame)

    def create_nav_buttons(self, layout):
        frame = QFrame()
        frame_layout = QHBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(5)

        nav_buttons = [
            ('🏠', "Home"), ('⬅️', "Back"), ('📱', "قائمة"),
            ('🔔', "إشعارات"), ('📂', "كل_التطبيقات"), ('🔄', "تحديث"),
            ('Tab', "Tab"), ('🔍', "تركيز"), ('🔎', "بحث"),
            ('↩️', "محاكاة الضغط على Enter"), ('🖨📸⚡', "SysRq"),
            ('🔄', "تبديل_التطبيق"), ('❌', "خروج"), ('⚙️', "إعدادات"),
            ('⌫', "محاكاة الحذف (Backspace)")
        ]

        for text, cmd in nav_buttons:
            btn = QPushButton(text)
            btn.setFont(QFont("Arial", 12))
            btn.setToolTip(f"وظيفة الزر: {cmd}")
            btn.clicked.connect(lambda _, v=cmd: self.button_click(v))
            frame_layout.addWidget(btn)

        layout.addWidget(frame)

    def create_direction_buttons(self, layout):
        frame = QFrame()
        frame_layout = QGridLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(5)

        direction_buttons = [
            ('↑', 0, 1, "↑"), ('←', 1, 0, "←"), ('OK', 1, 1, "OK"),
            ('→', 1, 2, "→"), ('↓', 2, 1, "↓"), ('تنقل_لأعلى', 0, 5, "تنقل_لأعلى"),
            ('تنقل_لأسفل', 2, 5, "تنقل_لأسفل"), ('تنقل_ليسار', 1, 4, "تنقل_ليسار"),
            ('تنقل_ليمين', 1, 6, "تنقل_ليمين"), ('🔔', 0, 0, "إشعارات"),
            ('📱', 0, 2, "قائمة"), ('🏠', 2, 0, "Home"), ('⬅️', 2, 2, "Back")
        ]

        for text, row, col, cmd in direction_buttons:
            btn = QPushButton(text)
            btn.setFont(QFont("Arial", 12))
            btn.setToolTip(f"وظيفة الزر: {cmd}")
            btn.clicked.connect(lambda _, v=cmd: self.button_click(v))
            frame_layout.addWidget(btn, row, col)

        layout.addWidget(frame)

    def create_copy_paste_buttons(self, layout):
        frame = QFrame()
        frame_layout = QGridLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(5)

        copy_buttons = [
            ('✂️', 0, 0, "قص"), ('📋', 0, 1, "نسخ"), ('📄', 0, 2, "لصق"),
            ('Select All', 0, 3, "تحديد الكل"), ('Shift+Home', 0, 4, "تحديد الكل1"),
            ('Shift+End', 0, 5, "تحديد الكل2")
        ]

        for text, row, col, cmd in copy_buttons:
            btn = QPushButton(text)
            btn.setFont(QFont("Arial", 12))
            btn.setToolTip(f"وظيفة الزر: {cmd}")
            btn.clicked.connect(lambda _, v=cmd: self.button_click(v))
            frame_layout.addWidget(btn, row, col)

        layout.addWidget(frame)

    def create_extra_buttons(self, layout):
        frame = QFrame()
        frame_layout = QGridLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(5)

        extra_buttons = [
            ('📞', 0, 0, "جهات_الاتصال"), ('👥', 0, 1, "فتح جهات الاتصال"),
            ('📅', 0, 2, "تقويم"), ('🎵', 0, 3, "موسيقى"),
            ('🧮', 0, 4, "آلة_حاسبة"), ('📷', 0, 5, "فتح الكاميرا"),
            ('🌐', 0, 6, "فتح المتصفح"), ('📞', 0, 7, "محاكاة مكالمة"),
            ('📴', 0, 8, "إنهاء مكالمة"), ('🏠', 1, 0, "نقل_للبداية"),
            ('🔚', 1, 1, "نقل_للنهاية"), ('➕', 1, 2, "إدراج"),
            ('🔗', 1, 3, "CapsLock"), ('⏩', 1, 4, "أمام"),
            ('ℹ️', 1, 5, "معلومات"), ('🌐', 1, 6, "تبديل_اللغة"),
            ('🔖', 1, 7, "علامة"), ('🔗', 1, 8, "فتح عنوان URL"),
            ('🖼️', 2, 0, "فتح المعرض"), ('🤖', 2, 1, "مساعدة"),
            ('🔗', 2, 2, "إقران"), ('⏹️', 2, 3, "إيقاف الوسائط"),
            ('📸', 2, 4, "التقاط لقطة شاشة"), ('🎥', 2, 5, "تسجيل شاشة الجهاز"),
            ('🖨️', 2, 6, "طباعة نص"), ('🖼️', 2, 7, "ScrollLock")
        ]

        for text, row, col, cmd in extra_buttons:
            btn = QPushButton(text)
            btn.setFont(QFont("Arial", 12))
            btn.setToolTip(f"وظيفة الزر: {cmd}")
            btn.clicked.connect(lambda _, v=cmd: self.button_click(v))
            frame_layout.addWidget(btn, row, col)

        layout.addWidget(frame)

    def create_number_buttons(self, layout):
        frame = QFrame()
        frame_layout = QGridLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(5)

        number_buttons = [
            ('1', 0, 0, "1"), ('2', 0, 1, "2"), ('3', 0, 2, "3"),
            ('4', 1, 0, "4"), ('5', 1, 1, "5"), ('6', 1, 2, "6"),
            ('7', 2, 0, "7"), ('8', 2, 1, "8"), ('9', 2, 2, "9"),
            ('*', 3, 0, "نجمة"), ('0', 3, 1, "0"), ('#', 3, 2, "مربع"),
            ('+', 0, 3, "زائد"), ('DEL', 0, 4, "حذف_أمامي"), ('⌫', 0, 5, "حذف"),
            ('C', 1, 3, "مسح"), ('/', 1, 4, "قسمة"), ('*', 1, 5, "ضرب"),
            ('-', 2, 3, "طرح"), ('+', 2, 4, "جمع"), ('.', 2, 5, "نقطة"),
            (',', 3, 3, "فاصلة"), ('Ent', 3, 4, "إدخال"), ('=', 3, 5, "يساوي"),
            ('(', 0, 6, "قوس_يسار"), (')', 0, 7, "قوس_يمين"), ('Tab', 0, 8, "Tab"),
            ('Space', 1, 6, "مسافة"), ('Sym', 1, 7, "رموز"), ('`', 1, 8, "علامة_التنوين"),
            ('-', 2, 6, "ناقص"), ('=', 2, 7, "يساوي"), ('[', 2, 8, "قوس_يسار"),
            (']', 3, 6, "قوس_يمين"), ('\\', 3, 7, "شرطة_مائلة"), (';', 3, 8, "فاصلة_منقوطة"),
            ("'", 0, 9, "فاصلة_عليا"), ('/', 1, 9, "شرطة"), ('@', 2, 9, "@"),
            ('Num', 3, 9, "أرقام"), ('Call', 0, 10, "اتصال"), ('End', 1, 10, "إنهاء_الاتصال"),
            ('Menu', 2, 10, "قائمة")
        ]

        for text, row, col, cmd in number_buttons:
            btn = QPushButton(text)
            btn.setFont(QFont("Arial", 12))
            btn.setToolTip(f"وظيفة الزر: {cmd}")
            btn.clicked.connect(lambda _, v=cmd: self.button_click(v))
            frame_layout.addWidget(btn, row, col)

        layout.addWidget(frame)

    def create_letter_buttons(self, layout):
        frame = QFrame()
        frame_layout = QGridLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(5)

        english_letters = [
            'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
            'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
            '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '.', ';', ':',
            'www.', 'https://', 'http://', '.com'
        ]

        row, col = 0, 0
        for letter in english_letters:
            btn = QPushButton(letter)
            btn.setFont(QFont("Arial", 12))
            btn.setToolTip(f"وظيفة الزر: {letter}")
            btn.clicked.connect(lambda _, v=letter: self.button_click(v))
            frame_layout.addWidget(btn, row, col)

            col += 1
            if col > 12:
                col = 0
                row += 1

        layout.addWidget(frame)

    def button_click(self, value):
        """تنفيذ الأوامر بناءً على الزر المضغوط."""
        target_device = self.device_combo.currentText()
        if not target_device or target_device == "لا توجد أجهزة متصلة":
            print("يرجى اختيار جهاز من القائمة المنسدلة.")
            return

        commands = {
            "تشغيل": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_POWER"],
            "إيقاف": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_POWER"],
            "إعادة تشغيل": ["adb", "-s", target_device, "reboot"],
            "كتم الصوت": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_VOLUME_MUTE"],
            "رفع الصوت": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_VOLUME_UP"],
            "خفض الصوت": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_VOLUME_DOWN"],
            "نوم": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_SLEEP"],
            "إيقاظ": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_WAKEUP"],
            "Home": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_HOME"],
            "Back": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_BACK"],
            "OK": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_DPAD_CENTER"],
            "↑": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_DPAD_UP"],
            "↓": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_DPAD_DOWN"],
            "←": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_DPAD_LEFT"],
            "→": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_DPAD_RIGHT"],
            "تشغيل الوسائط": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_MEDIA_PLAY"],
            "إيقاف الوسائط": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_MEDIA_PAUSE"],
            "التالي": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_MEDIA_NEXT"],
            "السابق": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_MEDIA_PREVIOUS"],
            "تسريع": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_MEDIA_FAST_FORWARD"],
            "تأخير": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_MEDIA_REWIND"],
            "صورة داخل صورة": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_WINDOW"],
            "نجمة": ["adb", "-s", target_device, "shell", "input", "keyevent", "17"],
            "مربع": ["adb", "-s", target_device, "shell", "input", "keyevent", "18"],
            "قص": ["adb", "-s", target_device, "shell", "input", "keyevent", "277"],
            "نسخ": ["adb", "-s", target_device, "shell", "input", "keyevent", "278"],
            "لصق": ["adb", "-s", target_device, "shell", "input", "keyevent", "279"],
            "تركيز": ["adb", "-s", target_device, "shell", "input", "keyevent", "80"],
            "قائمة": ["adb", "-s", target_device, "shell", "input", "keyevent", "82"],
            "إشعارات": ["adb", "-s", target_device, "shell", "input", "keyevent", "83"],
            "بحث": ["adb", "-s", target_device, "shell", "input", "keyevent", "84"],
            "تنقل_لأعلى": ["adb", "-s", target_device, "shell", "input", "keyevent", "280"],
            "تنقل_لأسفل": ["adb", "-s", target_device, "shell", "input", "keyevent", "281"],
            "تنقل_ليسار": ["adb", "-s", target_device, "shell", "input", "keyevent", "282"],
            "تنقل_ليمين": ["adb", "-s", target_device, "shell", "input", "keyevent", "283"],
            "كل_التطبيقات": ["adb", "-s", target_device, "shell", "input", "keyevent", "284"],
            "تحديث": ["adb", "-s", target_device, "shell", "input", "keyevent", "285"],
            "Tab": ["adb", "-s", target_device, "shell", "input", "keyevent", "61"],
            "خروج": ["adb", "-s", target_device, "shell", "input", "keyevent", "111"],
            "SysRq": ["adb", "-s", target_device, "shell", "input", "keyevent", "120"],
            "إيقاف الوسائط": ["adb", "-s", target_device, "shell", "input", "keyevent", "121"], # corrected from "إيقاف" to "إيقاف الوسائط" to differentiate from power off
            "نقل_للبداية": ["adb", "-s", target_device, "shell", "input", "keyevent", "122"],
            "نقل_للنهاية": ["adb", "-s", target_device, "shell", "input", "keyevent", "123"],
            "إدراج": ["adb", "-s", target_device, "shell", "input", "keyevent", "124"],
            "أمام": ["adb", "-s", target_device, "shell", "input", "keyevent", "125"],
            "معلومات": ["adb", "-s", target_device, "shell", "input", "keyevent", "165"],
            "علامة": ["adb", "-s", target_device, "shell", "input", "keyevent", "174"],
            "ترجمات": ["adb", "-s", target_device, "shell", "input", "keyevent", "175"],
            "إعدادات": ["adb", "-s", target_device, "shell", "input", "keyevent", "176"],
            "تبديل_التطبيق": ["adb", "-s", target_device, "shell", "input", "keyevent", "187"],
            "تبديل_اللغة": ["adb", "-s", target_device, "shell", "input", "keyevent", "204"],
            "جهات_الاتصال": ["adb", "-s", target_device, "shell", "input", "keyevent", "207"],
            "تقويم": ["adb", "-s", target_device, "shell", "input", "keyevent", "208"],
            "موسيقى": ["adb", "-s", target_device, "shell", "input", "keyevent", "209"],
            "آلة_حاسبة": ["adb", "-s", target_device, "shell", "input", "keyevent", "210"],
            "مساعدة": ["adb", "-s", target_device, "shell", "input", "keyevent", "219"],
            "تخفيف_السطوع": ["adb", "-s", target_device, "shell", "input", "keyevent", "220"],
            "زيادة_السطوع": ["adb", "-s", target_device, "shell", "input", "keyevent", "221"],
            "مسار_صوتي": ["adb", "-s", target_device, "shell", "input", "keyevent", "222"],
            "إقران": ["adb", "-s", target_device, "shell", "input", "keyevent", "225"],
            "وصف_صوتي": ["adb", "-s", target_device, "shell", "input", "keyevent", "252"],
            "رفع_المزيج": ["adb", "-s", target_device, "shell", "input", "keyevent", "253"],
            "خفض_المزيج": ["adb", "-s", target_device, "shell", "input", "keyevent", "254"],
            "التقاط لقطة شاشة": ["adb", "-s", target_device, "shell", "screencap", "-p", "/sdcard/screenshot.png"], # corrected path
            "تسجيل شاشة الجهاز": ["adb", "-s", target_device, "shell", "screenrecord", "/sdcard/record.mp4"], # corrected path
            "محاكاة مكالمة": ["adb", "-s", target_device, "shell", "input", "keyevent", "5"],
            "إنهاء مكالمة": ["adb", "-s", target_device, "shell", "input", "keyevent", "6"],
            "تبديل حالة تشغيل الجهاز": ["adb", "-s", target_device, "shell", "input", "keyevent", "26"],
            "فتح الكاميرا": ["adb", "-s", target_device, "shell", "input", "keyevent", "27"],
            "فتح المتصفح": ["adb", "-s", target_device, "shell", "input", "keyevent", "64"],
            "محاكاة الضغط على Enter": ["adb", "-s", target_device, "shell", "input", "keyevent", "66"],
            "محاكاة الحذف (Backspace)": ["adb", "-s", target_device, "shell", "input", "keyevent", "67"],
            "فتح جهات الاتصال": ["adb", "-s", target_device, "shell", "input", "keyevent", "207"],
            "طباعة نص": ["adb", "-s", target_device, "shell", "input", "text", "'Wow, it so cool feature'"],
            "فتح عنوان URL": ["adb", "-s", target_device, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "URL"],
            "فتح المعرض": ["adb", "-s", target_device, "shell", "am", "start", "-t", "image/*", "-a", "android.intent.action.VIEW"],
            "زائد": ["adb", "-s", target_device, "shell", "input", "text", "+"],
            "حذف_أمامي": ["adb", "-s", target_device, "shell", "input", "keyevent", "112"],
            "حذف": ["adb", "-s", target_device, "shell", "input", "keyevent", "67"],
            "مسح": ["adb", "-s", target_device, "shell", "input", "keyevent", "28"],
            "قسمة": ["adb", "-s", target_device, "shell", "input", "text", "/"],
            "ضرب": ["adb", "-s", target_device, "shell", "input", "keyevent", "17"],
            "طرح": ["adb", "-s", target_device, "shell", "input", "text", "-"],
            "جمع": ["adb", "-s", target_device, "shell", "input", "text", "+"],
            "نقطة": ["adb", "-s", target_device, "shell", "input", "text", "."],
            "فاصلة": ["adb", "-s", target_device, "shell", "input", "text", ","],
            "إدخال": ["adb", "-s", target_device, "shell", "input", "keyevent", "66"],
            "يساوي": ["adb", "-s", target_device, "shell", "input", "text", "="],
            "قوس_يسار": ["adb", "-s", target_device, "shell", "input", "text", "("],
            "قوس_يمين": ["adb", "-s", target_device, "shell", "input", "text", ")"],
            "Tab": ["adb", "-s", target_device, "shell", "input", "keyevent", "61"],
            "مسافة": ["adb", "-s", target_device, "shell", "input", "keyevent", "62"],
            "رموز": ["adb", "-s", target_device, "shell", "input", "keyevent", "63"],
            "علامة_التنوين": ["adb", "-s", target_device, "shell", "input", "text", "`"],
            "ناقص": ["adb", "-s", target_device, "shell", "input", "text", "-"],
            "قوس_يسار": ["adb", "-s", target_device, "shell", "input", "text", "["],
            "قوس_يمين": ["adb", "-s", target_device, "shell", "input", "text", "]"],
            "شرطة_مائلة": ["adb", "-s", target_device, "shell", "input", "text", "\\"],
                       "فاصلة_منقوطة": ["adb", "-s", target_device, "shell", "input", "text", ";"],
            "فاصلة_عليا": ["adb", "-s", target_device, "shell", "input", "text", "'"],
            "شرطة": ["adb", "-s", target_device, "shell", "input", "text", "/"],
            ".com": ["adb", "-s", target_device, "shell", "input", "text", ".com"],
            "@": ["adb", "-s", target_device, "shell", "input", "text", "@"],
            "أرقام": ["adb", "-s", target_device, "shell", "input", "keyevent", "11"],
            "اتصال": ["adb", "-s", target_device, "shell", "input", "keyevent", "5"],
            "إنهاء_الاتصال": ["adb", "-s", target_device, "shell", "input", "keyevent", "6"],
            "قائمة": ["adb", "-s", target_device, "shell", "input", "keyevent", "82"],
            "CapsLock": ["adb", "-s", target_device, "shell", "input", "keyevent", "115"],
            "ScrollLock": ["adb", "-s", target_device, "shell", "input", "keyevent", "116"],
            "www.": ["adb", "-s", target_device, "shell", "input", "text", "www."],
            "https://": ["adb", "-s", target_device, "shell", "input", "text", "https://"],
            "http://": ["adb", "-s", target_device, "shell", "input", "text", "http://"],
            "Shift+Home": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_MOVE_HOME"], # Shift + Home for select all start
            "Shift+End": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_MOVE_END"], # Shift + End for select all end
            "Select All": ["adb", "-s", target_device, "shell", "input", "keyevent", "KEYCODE_CTRL_A"], # Ctrl + A for select all
        }
        if value in commands:
            try:
                subprocess.run(commands[value], check=True, capture_output=True)
                print(f"تم تنفيذ الأمر: {value} على الجهاز: {target_device}")
            except subprocess.CalledProcessError as e:
                print(f"خطأ في تنفيذ الأمر: {value} - {e.stderr.decode()}")
            except FileNotFoundError:
                print("لم يتم العثور على adb. تأكد من تثبيته وإضافته إلى PATH.")
        elif value.isdigit():
            subprocess.run(["adb", "-s", target_device, "shell", "input", "text", value])
            print(f"تم إدخال الرقم: {value}")
        elif value.isalpha():
            subprocess.run(["adb", "-s", target_device, "shell", "input", "text", value])
            print(f"تم إدخال الحرف: {value}")
        else:
            print(f"لا يوجد أمر محدد لهذا الزر: {value}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RemoteControlApp()
    window.show()
    sys.exit(app.exec())