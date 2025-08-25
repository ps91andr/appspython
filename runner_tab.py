import sys
import subprocess
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtGui import QClipboard

class PythonRunnerTab(QWidget):
    """
    واجهة رسومية لاختيار وتشغيل ملفات بايثون،
    مع عرض المخرجات والأخطاء في نافذة مخصصة.
    """
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("تشغيل ملف Python وعرض الإخراج")
        self.setGeometry(100, 100, 600, 450)

        # -- تعريف العناصر --
        self.button_select = QPushButton("📁 اختر ملف Python")
        self.button_run = QPushButton("🚀 تشغيل في CMD + عرض الإخراج")
        self.button_run.setEnabled(False)  # يبدأ معطلاً حتى يتم اختيار ملف

        self.button_clear_output = QPushButton("🗑️ مسح الإخراج")
        self.button_copy_errors = QPushButton("📋 نسخ الأخطاء")
        self.button_copy_output = QPushButton("📋 نسخ الإخراج")

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)  # منطقة الإخراج للقراءة فقط

        self.selected_file = None

        # -- ربط الأزرار بالوظائف --
        self.button_select.clicked.connect(self.select_file)
        self.button_run.clicked.connect(self.run_file)
        self.button_clear_output.clicked.connect(self.clear_output)
        self.button_copy_errors.clicked.connect(self.copy_errors)
        self.button_copy_output.clicked.connect(self.copy_output)
        
        # -- تصميم الواجهة --
        self.setup_ui()

    def setup_ui(self):
        """
        يقوم بإعداد وتنسيق الواجهة الرسومية.
        """
        # تخطيط عمودي رئيسي
        layout = QVBoxLayout()
        
        # صف أفقي للأزرار الإضافية
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.button_clear_output)
        btn_row.addWidget(self.button_copy_errors)
        btn_row.addWidget(self.button_copy_output)

        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(self.button_select)
        layout.addWidget(self.button_run)
        layout.addLayout(btn_row)  # إضافة الصف الأفقي
        layout.addWidget(self.output_area)
        
        self.setLayout(layout)

    def select_file(self):
        """
        يفتح نافذة لاختيار ملف بايثون (.py).
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف Python", "", "Python Files (*.py)"
        )
        if file_path:
            self.selected_file = file_path
            self.button_run.setEnabled(True)  # تفعيل زر التشغيل
            self.output_area.append(f"📁 تم اختيار الملف:\n{file_path}\n")

    def run_file(self):
        """
        يقوم بتشغيل الملف المختار في نافذة CMD منفصلة
        ويعرض المخرجات والأخطاء في الواجهة.
        """
        if self.selected_file:
            self.output_area.append("🚀 بدء التنفيذ...\n")

            # 1. فتح نافذة CMD فعلية لتشغيل الكود بشكل مرئي
            try:
                # الأمر يفتح CMD، يشغل الملف، ثم ينتظر الضغط على أي مفتاح قبل الإغلاق
                cmd_command = f'start cmd /k "python \"{self.selected_file}\" & pause"'
                subprocess.Popen(cmd_command, shell=True)
                self.output_area.append("🖥️ تم فتح نافذة CMD لتشغيل الملف.\n")
            except Exception as e:
                self.output_area.append(f"❌ خطأ في فتح CMD:\n{e}\n")

            # 2. تشغيل الكود في الخلفية للحصول على المخرجات والأخطاء
            try:
                result = subprocess.run(
                    ["python", self.selected_file],
                    capture_output=True,
                    text=True,
                    check=False,  # لا يطلق استثناء عند وجود خطأ
                    encoding='utf-8' # تحديد الترميز لضمان قراءة صحيحة
                )
                if result.stdout:
                    self.output_area.append(f"✅ الإخراج:\n{result.stdout}")
                if result.stderr:
                    self.output_area.append(f"⚠️ الأخطاء:\n{result.stderr}")
            except FileNotFoundError:
                 self.output_area.append(f"❌ خطأ: لم يتم العثور على مفسر 'python'. تأكد من أنه في متغيرات البيئة.\n")
            except Exception as e:
                self.output_area.append(f"❌ استثناء أثناء التشغيل في الخلفية:\n{e}\n")
        else:
            QMessageBox.warning(self, "لم يتم التحديد", "يرجى اختيار ملف بايثون أولاً.")

    def clear_output(self):
        """
        يمسح محتوى منطقة الإخراج.
        """
        self.output_area.clear()

    def copy_errors(self):
        """
        ينسخ قسم الأخطاء فقط إلى الحافظة.
        """
        text = self.output_area.toPlainText()
        try:
            # يبحث عن بداية قسم الأخطاء وينسخ كل ما بعده
            error_section_index = text.rindex("⚠️ الأخطاء:")
            error_section = text[error_section_index:].strip()
            
            clipboard = QApplication.clipboard()
            clipboard.setText(error_section)
            QMessageBox.information(self, "تم النسخ", "✅ تم نسخ الأخطاء إلى الحافظة.")
        except ValueError:
            QMessageBox.information(self, "لا توجد أخطاء", "لم يتم العثور على أخطاء لنسخها.")

    def copy_output(self):
        """
        ينسخ كل المحتوى الموجود في منطقة الإخراج إلى الحافظة.
        """
        text = self.output_area.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "تم النسخ", "✅ تم نسخ الإخراج بالكامل إلى الحافظة.")
        else:
            QMessageBox.information(self, "لا يوجد إخراج", "لا يوجد شيء لنسخه.")

# --- نقطة انطلاق التطبيق ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PythonRunnerTab()
    window.show()
    sys.exit(app.exec())