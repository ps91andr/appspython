import sys
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFileDialog
)
from PyQt6.QtCore import QProcess

class AdminToolsTab(QWidget):
    """
    واجهة رسومية لإدارة حزم بايثون مع صلاحيات المسؤول.
    """
    def __init__(self):
        """
        إعداد الواجهة الرسومية والمكونات.
        """
        super().__init__()
        self.setWindowTitle("أدوات المسؤول - تحديث الحزم")
        self.setGeometry(100, 100, 800, 600)

        # التخطيط الرئيسي
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # تخطيط الأزرار العلوية
        top_buttons_layout = QHBoxLayout()
        main_layout.addLayout(top_buttons_layout)

        btn_admin_cmd = QPushButton("فتح موجه الأوامر كمسؤول")
        btn_admin_cmd.clicked.connect(self.open_admin_cmd)
        top_buttons_layout.addWidget(btn_admin_cmd)

        btn_pip_list = QPushButton("عرض الحزم المثبتة")
        btn_pip_list.clicked.connect(self.run_pip_list)
        top_buttons_layout.addWidget(btn_pip_list)

        btn_pip_review = QPushButton("تثبيت pip-review (عبر CMD)")
        btn_pip_review.clicked.connect(self.install_pip_review_cmd)
        top_buttons_layout.addWidget(btn_pip_review)

        btn_pip_revieww = QPushButton("تثبيت pip-review (عبر PowerShell)")
        btn_pip_revieww.clicked.connect(self.install_pip_review_ps)
        top_buttons_layout.addWidget(btn_pip_revieww)

        # تخطيط الأزرار الوسطى
        middle_buttons_layout = QHBoxLayout()
        main_layout.addLayout(middle_buttons_layout)

        btn_auto_update = QPushButton("تحديث الكل تلقائياً (عبر CMD)")
        btn_auto_update.clicked.connect(self.auto_update_packages_cmd)
        middle_buttons_layout.addWidget(btn_auto_update)

        btn_auto_updatee = QPushButton("تحديث الكل تلقائياً (عبر PowerShell)")
        btn_auto_updatee.clicked.connect(self.auto_update_packages_ps)
        middle_buttons_layout.addWidget(btn_auto_updatee)
        
        # تخطيط الأزرار السفلية
        bottom_buttons_layout = QHBoxLayout()
        main_layout.addLayout(bottom_buttons_layout)

        btn_clear = QPushButton("مسح المخرجات")
        btn_clear.clicked.connect(self.clear_output)
        bottom_buttons_layout.addWidget(btn_clear)

        btn_save = QPushButton("حفظ المخرجات")
        btn_save.clicked.connect(self.save_output)
        bottom_buttons_layout.addWidget(btn_save)

        # منطقة عرض المخرجات
        output_label = QLabel("سجل التنفيذ:")
        main_layout.addWidget(output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        main_layout.addWidget(self.output_text)

        # إعداد QProcess للمعالجة غير المتزامنة
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_output)
        self.process.readyReadStandardError.connect(self.handle_error)
        self.process.finished.connect(self.command_finished)

    def run_command_as_admin_ps(self, command, message):
        """
        تشغيل أمر PowerShell بصلاحيات المسؤول.
        """
        try:
            self.append_output(message)
            script = f"{command}"
            # استخدام PowerShell لتشغيل أمر آخر في نافذة PowerShell جديدة بصلاحيات المسؤول
            subprocess.run(f'powershell -Command "Start-Process powershell -ArgumentList \'{script}\' -Verb RunAs"', shell=True, check=True)
            self.append_output(f"تم تنفيذ الأمر كمسؤول (تحقق من نافذة PowerShell): {command}")
        except Exception as e:
            self.append_output(f"خطأ في تنفيذ الأمر: {e}", error=True)

    def run_command_as_admin_cmd(self, batch_content, message):
        """
        إنشاء وتشغيل ملف دفعي (bat) بصلاحيات المسؤول.
        """
        try:
            self.append_output(message)
            file_name = "temp_script.bat"
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(batch_content)
            # استخدام PowerShell لتشغيل الملف الدفعي بصلاحيات المسؤول
            subprocess.run(f'powershell -Command "Start-Process {file_name} -Verb RunAs"', shell=True, check=True)
            self.append_output(f"تم تنفيذ الأمر كمسؤول (تحقق من نافذة CMD).")
        except Exception as e:
            self.append_output(f"خطأ في تنفيذ الأمر: {e}", error=True)

    def auto_update_packages_ps(self):
        """
        تحديث جميع الحزم باستخدام pip-review في PowerShell.
        """
        self.run_command_as_admin_ps("pip-review --auto", "جاري تحديث جميع الحزم عبر PowerShell...")

    def install_pip_review_ps(self):
        """
        تثبيت pip-review باستخدام pip في PowerShell.
        """
        self.run_command_as_admin_ps("pip install pip-review", "جاري تثبيت pip-review عبر PowerShell...")

    def open_admin_cmd(self):
        """
        فتح نافذة موجه الأوامر (CMD) بصلاحيات المسؤول.
        """
        try:
            subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs"', shell=True, check=True)
            self.append_output("تم فتح موجه الأوامر كمسؤول.")
        except subprocess.CalledProcessError as e:
            self.append_output(f"خطأ في فتح موجه الأوامر: {e}", error=True)

    def run_pip_list(self):
        """
        عرض قائمة بجميع حزم بايثون المثبتة حالياً.
        """
        self.append_output("جاري عرض الحزم المثبتة...")
        self.process.start("pip", ["list"])

    def install_pip_review_cmd(self):
        """
        تثبيت pip-review باستخدام ملف دفعي (CMD).
        """
        batch_script = (
            "@echo off\n"
            "title تثبيت pip-review\n"
            "echo جاري تثبيت pip-review...\n"
            "pip install pip-review\n"
            "echo.\n"
            "echo تم الانتهاء من التثبيت. اضغط أي مفتاح للخروج.\n"
            "pause > nul\n"
        )
        self.run_command_as_admin_cmd(batch_script, "جاري تثبيت pip-review عبر CMD...")

    def auto_update_packages_cmd(self):
        """
        تحديث جميع الحزم باستخدام pip-review في ملف دفعي (CMD).
        """
        batch_script = (
            "@echo off\n"
            "title تحديث الحزم\n"
            "echo جاري تحديث جميع الحزم...\n"
            "pip-review --auto\n"
            "echo.\n"
            "echo تم الانتهاء من التحديث. اضغط أي مفتاح للخروج.\n"
            "pause > nul\n"
        )
        self.run_command_as_admin_cmd(batch_script, "جاري تحديث جميع الحزم عبر CMD...")

    def clear_output(self):
        """
        مسح محتويات مربع النص.
        """
        self.output_text.clear()

    def save_output(self):
        """
        حفظ سجل المخرجات في ملف نصي.
        """
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "حفظ السجل كملف نصي", "", "ملفات النصوص (*.txt);;جميع الملفات (*)")
            if file_path:
                if not file_path.lower().endswith('.txt'):
                    file_path += '.txt'
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(self.output_text.toPlainText())
                self.append_output(f"تم حفظ السجل في: {file_path}")
        except Exception as e:
            self.append_output(f"خطأ في حفظ الملف: {e}", error=True)

    def append_output(self, text, error=False):
        """
        إضافة نص إلى مربع المخرجات، مع تلوين الأخطاء باللون الأحمر.
        """
        if error:
            self.output_text.append(f'<span style="color:red;">{text}</span>')
        else:
            self.output_text.append(text)
        self.output_text.ensureCursorVisible() # التمرير لأسفل تلقائياً

    def handle_output(self):
        """
        معالجة المخرجات القياسية من QProcess.
        """
        output = self.process.readAllStandardOutput().data().decode("utf-8", errors='ignore')
        self.append_output(output)

    def handle_error(self):
        """
        معالجة مخرجات الخطأ من QProcess.
        """
        error = self.process.readAllStandardError().data().decode("utf-8", errors='ignore')
        self.append_output(error, error=True)

    def command_finished(self):
        """
        يتم استدعاؤها عند انتهاء العملية التي بدأتها QProcess.
        """
        self.append_output("--- تم الانتهاء من العملية ---")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AdminToolsTab()
    window.show()
    sys.exit(app.exec())