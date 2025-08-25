import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QLabel, QTextEdit, QGroupBox
)
from PyQt6.QtCore import QTimer
from deep_translator import GoogleTranslator

class TranslationTab(QWidget):
    """
    واجهة مستخدم لتطبيق ترجمة فوري ثنائي الاتجاه باستخدام PyQt6 ومكتبة deep_translator.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مترجم فوري متعدد اللغات")
        self.setGeometry(100, 100, 850, 650)

        # قائمة اللغات المدعومة مع رموزها
        self.supported_languages = {
            'العربية': 'ar',
            'الإنجليزية': 'en',
            'الإسبانية': 'es',
            'الفرنسية': 'fr',
            'الألمانية': 'de',
            'الإيطالية': 'it',
            'البرتغالية': 'pt',
            'الروسية': 'ru',
            'الصينية (المبسطة)': 'zh-CN',
            'اليابانية': 'ja',
            'الكورية': 'ko',
            'الهندية': 'hi',
            'التركية': 'tr',
            'الهولندية': 'nl',
            'البولندية': 'pl',
            'السويدية': 'sv',
            'الدنماركية': 'da',
            'الفنلندية': 'fi',
            'النرويجية': 'no',
            'العبرية': 'he',
            'اليونانية': 'el',
            'الرومانية': 'ro',
            'المجرية': 'hu',
            'التشيكية': 'cs',
            'التايلاندية': 'th',
            'الفارسية': 'fa',
            'الأردية': 'ur',
            'البنغالية': 'bn',
            'التاميلية': 'ta',
            'الفيتنامية': 'vi',
            'الإندونيسية': 'id',
            'الماليزية': 'ms',
            'السواحيلية': 'sw'
        }
        
        self.last_text = ""
        self.translation_delay = 1000  # زيادة التأخير إلى 1000 ميلي ثانية (1 ثانية)

        self.init_ui()

        # مؤقت لتنظيم طلبات الترجمة عند الكتابة
        self.translation_timer = QTimer()
        self.translation_timer.setSingleShot(True)
        self.translation_timer.timeout.connect(self.translate_text)

    def init_ui(self):
        """
        تقوم بتهيئة وبناء واجهة المستخدم الرسومية.
        """
        main_layout = QVBoxLayout(self)

        self.setup_language_bar(main_layout)
        self.setup_translation_area(main_layout)

        self.status_label = QLabel("جاهز للترجمة...")
        main_layout.addWidget(self.status_label)

    def setup_language_bar(self, layout):
        """
        إعداد شريط اختيار اللغات وزر التبديل والترجمة اليدوية.
        """
        lang_layout = QHBoxLayout()

        self.source_lang = QComboBox()
        # إضافة جميع اللغات المدعومة
        self.source_lang.addItems(list(self.supported_languages.keys()))
        self.source_lang.setCurrentText("العربية")
        self.source_lang.currentIndexChanged.connect(self.on_language_changed)

        self.swap_btn = QPushButton("⇄")
        self.swap_btn.setFixedWidth(60)
        self.swap_btn.setToolTip("تبديل اللغات")
        self.swap_btn.clicked.connect(self.swap_languages)

        self.target_lang = QComboBox()
        # إضافة جميع اللغات المدعومة
        self.target_lang.addItems(list(self.supported_languages.keys()))
        self.target_lang.setCurrentText("الإنجليزية")
        self.target_lang.currentIndexChanged.connect(self.on_language_changed)

        self.manual_translate_btn = QPushButton("ترجم الآن")
        self.manual_translate_btn.setToolTip("بدء الترجمة يدويًا")
        self.manual_translate_btn.clicked.connect(self.manual_translate)

        lang_layout.addWidget(QLabel("من:"))
        lang_layout.addWidget(self.source_lang)
        lang_layout.addWidget(self.swap_btn)
        lang_layout.addWidget(QLabel("إلى:"))
        lang_layout.addWidget(self.target_lang)
        lang_layout.addStretch()
        lang_layout.addWidget(self.manual_translate_btn)

        layout.addLayout(lang_layout)

    def setup_translation_area(self, layout):
        """
        إعداد مربعات النص للنص الأصلي والمترجم مع أزرار التحكم.
        """
        trans_layout = QHBoxLayout()

        # --- صندوق النص الأصلي ---
        source_group = QGroupBox("النص الأصلي")
        source_layout = QVBoxLayout()
        
        self.source_text = QTextEdit()
        self.source_text.setPlaceholderText("اكتب هنا للترجمة الفورية...")
        self.source_text.textChanged.connect(self.schedule_translation)
        
        btn_source_layout = self.create_button_bar(
            self.copy_source_text, self.paste_to_source, self.clear_source_text
        )
        source_layout.addLayout(btn_source_layout)
        source_layout.addWidget(self.source_text)
        source_group.setLayout(source_layout)

        # --- صندوق النص المترجم ---
        target_group = QGroupBox("الترجمة")
        target_layout = QVBoxLayout()
        
        self.target_text = QTextEdit()
        self.target_text.setReadOnly(True)
        
        btn_target_layout = self.create_button_bar(
            self.copy_target_text, None, self.clear_target_text, paste_enabled=False
        )
        target_layout.addLayout(btn_target_layout)
        target_layout.addWidget(self.target_text)
        target_group.setLayout(target_layout)

        trans_layout.addWidget(source_group, stretch=1)
        trans_layout.addWidget(target_group, stretch=1)
        layout.addLayout(trans_layout)

    def create_button_bar(self, copy_fn, paste_fn, clear_fn, paste_enabled=True):
        """
        إنشاء شريط أزرار (نسخ، لصق، مسح) لتجنب تكرار الكود.
        """
        btn_layout = QHBoxLayout()
        
        copy_btn = QPushButton("نسخ")
        copy_btn.clicked.connect(copy_fn)
        
        clear_btn = QPushButton("مسح")
        clear_btn.clicked.connect(clear_fn)

        btn_layout.addStretch()
        btn_layout.addWidget(copy_btn)
        if paste_enabled and paste_fn:
            paste_btn = QPushButton("لصق")
            paste_btn.clicked.connect(paste_fn)
            btn_layout.addWidget(paste_btn)
        btn_layout.addWidget(clear_btn)
        
        return btn_layout

    def schedule_translation(self):
        """
        جدولة عملية الترجمة بعد فترة قصيرة من توقف المستخدم عن الكتابة.
        """
        # إعادة تشغيل المؤقت عند كل تغيير في النص
        self.translation_timer.stop()
        self.translation_timer.start(self.translation_delay)
        self.status_label.setText("يكتب المستخدم...")

    def translate_text(self):
        """
        تنفيذ عملية الترجمة الفعلية.
        """
        current_text = self.source_text.toPlainText().strip()

        if not current_text:
            self.target_text.clear()
            self.status_label.setText("جاهز للترجمة...")
            self.last_text = ""
            return

        if current_text == self.last_text:
            return

        try:
            self.status_label.setText("جارٍ الترجمة...")
            QApplication.processEvents()  # تحديث الواجهة فورًا
            
            # تحديد اللغات بناءً على اختيار المستخدم
            source_lang_text = self.source_lang.currentText()
            target_lang_text = self.target_lang.currentText()
            
            source_code = self.supported_languages[source_lang_text]
            target_code = self.supported_languages[target_lang_text]

            # إنشاء كائن المترجم والترجمة
            translated = GoogleTranslator(source=source_code, target=target_code).translate(current_text)
            self.target_text.setPlainText(translated)
            self.last_text = current_text
            self.status_label.setText("تمت الترجمة بنجاح")

        except Exception as e:
            self.status_label.setText(f"خطأ في الترجمة: {str(e)}")
            self.last_text = ""  # إعادة تعيين last_text في حالة الخطأ

    def manual_translate(self):
        """
        ترجمة يدوية عند النقر على زر 'ترجم الآن'.
        """
        # إلغاء المؤقت الحالي وإجراء الترجمة فورًا
        self.translation_timer.stop()
        self.translate_text()

    def on_language_changed(self):
        """
        يتم استدعاؤها عند تغيير لغة المصدر أو الهدف.
        """
        current_text = self.source_text.toPlainText().strip()
        if current_text:
            # إذا كان هناك نص، قم بالترجمة فورًا بدون استخدام المؤقت
            self.translation_timer.stop()
            self.last_text = ""  # إجبار الترجمة حتى لو كان النص نفسه
            self.translate_text()

    def swap_languages(self):
        """
        تبديل بين لغة المصدر والهدف.
        """
        # حفظ المحتوى الحالي
        source_text_content = self.source_text.toPlainText()
        target_text_content = self.target_text.toPlainText()

        # تبديل اللغات
        current_source_index = self.source_lang.currentIndex()
        current_target_index = self.target_lang.currentIndex()
        self.source_lang.setCurrentIndex(current_target_index)
        self.target_lang.setCurrentIndex(current_source_index)

        # تبديل المحتوى النصي بين المربعين
        self.source_text.setPlainText(target_text_content)
        self.target_text.setPlainText(source_text_content)
        
        # إعادة الترجمة فورًا بعد التبديل إذا كان هناك نص
        if source_text_content.strip():
            self.translation_timer.stop()
            self.last_text = ""  # إجبار الترجمة
            self.translate_text()

    def copy_source_text(self):
        text = self.source_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.status_label.setText("تم نسخ النص الأصلي")

    def paste_to_source(self):
        self.source_text.setPlainText(QApplication.clipboard().text())

    def clear_source_text(self):
        self.source_text.clear()
        self.last_text = ""  # إعادة تعيين last_text عند المسح

    def copy_target_text(self):
        text = self.target_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.status_label.setText("تم نسخ النص المترجم")

    def clear_target_text(self):
        self.target_text.clear()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TranslationTab()
    window.show()
    sys.exit(app.exec())