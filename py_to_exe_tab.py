import sys
import os
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QLineEdit, QCheckBox,
    QProgressBar, QTextEdit, QMessageBox, QGridLayout
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

# ============= تبويب تحويل بايثون إلى تطبيق 3207 =============
class PyInstallerThread(QThread):
    """
    يعمل هذا الخيط في الخلفية لتشغيل PyInstaller دون تجميد الواجهة الرسومية.
    """
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)

    def __init__(self, py_file, icon_file, version_file, exe_name, onefile, noconsole):
        super().__init__()
        self.py_file = py_file
        self.icon_file = icon_file
        self.version_file = version_file
        self.exe_name = exe_name
        self.onefile = onefile
        self.noconsole = noconsole

    def run(self):
        """
        يقوم بإعداد وتشغيل أمر PyInstaller.
        """
        dist_path = os.path.dirname(self.py_file)
        build_path = os.path.join(dist_path, "build")

        cmd = [
            "pyinstaller",
            "--clean",
            f"--name={self.exe_name}",
            f"--distpath={dist_path}",
            f"--workpath={build_path}",
            f"--specpath={dist_path}",
        ]

        if self.onefile:
            cmd.append("--onefile")
        if self.noconsole:
            cmd.append("--noconsole")
        if self.icon_file:
            cmd.append(f"--icon={self.icon_file}")
        if self.version_file:
            cmd.append(f"--version-file={self.version_file}")

        cmd.append(self.py_file)

        # بدء العملية وقراءة المخرجات سطراً بسطر
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        self.progress_signal.emit(10)

        for line in process.stdout:
            self.output_signal.emit(line)
        process.wait()

        self.progress_signal.emit(100)


class VersionFileDialog(QWidget):
    """
    نافذة حوار لإنشاء ملف معلومات الإصدار لملف EXE.
    """
    def __init__(self, parent=None):
        super().__init__()
        self.main_window = parent
        self.setWindowTitle("🧾 إنشاء ملف معلومات الإصدار")
        self.resize(500, 500)

        layout = QVBoxLayout()

        self.fields = {
            "CompanyName": QLineEdit("TAHA ABDULJALIL"),
            "FileDescription": QLineEdit("py"),
            "FileVersion": QLineEdit("1.0.0.0"),
            "InternalName": QLineEdit("py"),
            "OriginalFilename": QLineEdit("py.exe"),
            "ProductName": QLineEdit("py"),
            "ProductVersion": QLineEdit("1.0.0.0"),
            "LegalCopyright": QLineEdit("© 2025 TAHA ABDULJALIL")
        }

        tooltips = {
            "CompanyName": "اسم الشركة",
            "FileDescription": "وصف الملف",
            "FileVersion": "إصدار الملف (مثلاً 1.0.0.0)",
            "InternalName": "الاسم الداخلي للملف التنفيذي",
            "OriginalFilename": "اسم الملف الأصلي (مثلاً StarsatRemoteonly.exe)",
            "ProductName": "اسم المنتج",
            "ProductVersion": "إصدار المنتج (مثلاً 1.0.0.0)",
            "LegalCopyright": "حقوق الطبع والنشر القانونية"
        }

        for label, widget in self.fields.items():
            widget.setToolTip(tooltips.get(label, ""))
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(widget)
            layout.addLayout(row)

        self.save_btn = QPushButton("💾 حفظ ملف الإصدار")
        self.save_btn.clicked.connect(self.save_version_file)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

    def save_version_file(self):
        """
        يحفظ المعلومات التي أدخلها المستخدم في ملف نصي بتنسيق PyInstaller.
        """
        file_path, _ = QFileDialog.getSaveFileName(self, "احفظ ملف معلومات الإصدار", "", "Text Files (*.txt)")
        if not file_path:
            return

        filevers = self.format_version(self.fields["FileVersion"].text())
        prodvers = self.format_version(self.fields["ProductVersion"].text())

        content = (
            "VSVersionInfo(\n"
            "  ffi=FixedFileInfo(\n"
            f"    filevers=({filevers}),\n"
            f"    prodvers=({prodvers}),\n"
            "    mask=0x3f,\n"
            "    flags=0x0,\n"
            "    OS=0x4,\n"
            "    fileType=0x1,\n"
            "    subtype=0x0,\n"
            "    date=(0, 0)\n"
            "  ),\n"
            "  kids=[\n"
            "    StringFileInfo([\n"
            "      StringTable(\n"
            "        '040904B0',\n"
            "        [\n"
        )

        for key, widget in self.fields.items():
            content += f"          StringStruct('{key}', '{widget.text()}'),\n"

        content += (
            "        ]\n"
            "      )\n"
            "    ]),\n"
            "    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n"
            "  ]\n"
            ")"
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        if self.main_window:
            self.main_window.version_file = file_path
            self.main_window.select_version_btn.setText(f"📝 {os.path.basename(file_path)}")

        QMessageBox.information(self, "تم الحفظ", "✅ تم إنشاء ملف معلومات الإصدار بنجاح!")
        self.close()

    def format_version(self, version_str):
        """
        يضمن أن يكون رقم الإصدار مكونًا من أربعة أجزاء.
        """
        parts = version_str.strip().split(".")
        while len(parts) < 4:
            parts.append("0")
        return ", ".join(parts[:4])

class PyToExeTab(QWidget):
    """
    الواجهة الرئيسية لتبويب تحويل ملفات بايثون إلى EXE.
    """
    def __init__(self):
        super().__init__()
        self.py_file = ""
        self.icon_file = ""
        self.version_file = ""

        main_layout = QVBoxLayout()
        self.setAcceptDrops(True)

        # استخدام QGridLayout لتحكم دقيق في تموضع العناصر
        grid_layout = QGridLayout()

        self.select_py_btn = QPushButton("📂 اختر ملف البايثون")
        self.select_py_btn.clicked.connect(self.select_py_file)
        grid_layout.addWidget(self.select_py_btn, 0, 0)

        self.delete_py_btn = QPushButton("🗑️ مسح ملف البايثون")
        self.delete_py_btn.clicked.connect(self.delete_python_file)
        grid_layout.addWidget(self.delete_py_btn, 0, 1)

        icon_row = QHBoxLayout()
        self.select_icon_btn = QPushButton("🖼️ اختر أيقونة (اختياري)")
        self.select_icon_btn.clicked.connect(self.select_icon_file)
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(32, 32)
        self.icon_preview.setScaledContents(True)
        self.icon_preview.setStyleSheet("border: 1px solid gray;")
        icon_row.addWidget(self.select_icon_btn)
        icon_row.addWidget(self.icon_preview)
        grid_layout.addLayout(icon_row, 1, 0)

        self.delete_icon_btn = QPushButton("🗑️ مسح الأيقونة")
        self.delete_icon_btn.clicked.connect(self.delete_icon_file)
        grid_layout.addWidget(self.delete_icon_btn, 1, 1)

        self.create_version_btn = QPushButton("🧾 إنشاء ملف معلومات الإصدار")
        self.create_version_btn.clicked.connect(self.open_version_dialog)
        grid_layout.addWidget(self.create_version_btn, 2, 0)
        
        self.delete_version_btn = QPushButton("🗑️ مسح ملف الإصدار")
        self.delete_version_btn.clicked.connect(self.delete_version_file)
        grid_layout.addWidget(self.delete_version_btn, 2, 1)

        self.select_version_btn = QPushButton("📝 اختر ملف الإصدار (اختياري)")
        self.select_version_btn.clicked.connect(self.select_version_file)
        grid_layout.addWidget(self.select_version_btn, 3, 0, 1, 2)
        
        main_layout.addLayout(grid_layout)

        main_layout.addWidget(QLabel("✏️ اسم الملف التنفيذي:"))
        self.exe_name_input = QLineEdit()
        self.exe_name_input.setPlaceholderText("اكتب اسم الملف بدون .exe")
        main_layout.addWidget(self.exe_name_input)

        self.onefile_cb = QCheckBox("🔒 إنشاء ملف تنفيذي واحد (--onefile)")
        self.noconsole_cb = QCheckBox("🕶️ إخفاء نافذة الكونسول (--noconsole)")
        main_layout.addWidget(self.onefile_cb)
        main_layout.addWidget(self.noconsole_cb)

        self.convert_btn = QPushButton("⚙️ تحويل إلى EXE")
        self.convert_btn.clicked.connect(self.convert_to_exe)
        main_layout.addWidget(self.convert_btn)

        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        main_layout.addWidget(self.output_text)
        
        self.delete_output_btn = QPushButton("🗑️ مسح سجل الإخراج")
        self.delete_output_btn.clicked.connect(self.delete_output_log)
        
        self.open_output_btn = QPushButton("📁 فتح مجلد الإخراج")
        self.open_output_btn.setEnabled(False)
        self.open_output_btn.clicked.connect(self.open_output_folder)

        # إضافة الأزرار السفلية في تخطيط أفقي
        bottom_buttons_layout = QHBoxLayout()
        bottom_buttons_layout.addWidget(self.open_output_btn)
        bottom_buttons_layout.addWidget(self.delete_output_btn)
        main_layout.addLayout(bottom_buttons_layout)


        self.setLayout(main_layout)

    def select_py_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "اختر ملف .py", "", "Python Files (*.py)")
        if file:
            self.py_file = file
            self.select_py_btn.setText(f"📂 {os.path.basename(file)}")

    def select_icon_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "اختر ملف أيقونة", "", "Icon Files (*.ico)")
        if file:
            self.icon_file = file
            self.select_icon_btn.setText(f"🖼️ {os.path.basename(file)}")
            self.update_icon_preview()

    def delete_python_file(self):
        self.py_file = ""
        self.select_py_btn.setText("📂 اختر ملف البايثون")

    def delete_icon_file(self):
        self.icon_file = ""
        self.select_icon_btn.setText("🖼️ اختر أيقونة (اختياري)")
        self.icon_preview.clear()

    def delete_version_file(self):
        self.version_file = ""
        self.select_version_btn.setText("📝 اختر ملف الإصدار (اختياري)")

    def delete_output_log(self):
        self.output_text.clear()

    def update_icon_preview(self):
        if self.icon_file and os.path.exists(self.icon_file):
            self.icon_preview.setPixmap(QPixmap(self.icon_file))
        else:
            self.icon_preview.clear()

    def select_version_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "اختر ملف معلومات الإصدار", "", "Text Files (*.txt)")
        if file:
            self.version_file = file
            self.select_version_btn.setText(f"📝 {os.path.basename(file)}")

    def open_version_dialog(self):
        self.version_dialog = VersionFileDialog(parent=self)
        self.version_dialog.show()

    def convert_to_exe(self):
        if not self.py_file:
            self.output_text.append("⚠️ الرجاء اختيار ملف بايثون أولاً.")
            return

        name = self.exe_name_input.text().strip() or os.path.splitext(os.path.basename(self.py_file))[0]

        self.output_text.clear()
        self.progress_bar.setValue(0)
        self.open_output_btn.setEnabled(False)

        self.thread = PyInstallerThread(
            self.py_file,
            self.icon_file,
            self.version_file,
            name,
            self.onefile_cb.isChecked(),
            self.noconsole_cb.isChecked()
        )
        self.thread.output_signal.connect(self.append_output)
        self.thread.progress_signal.connect(self.progress_bar.setValue)
        self.thread.finished.connect(self.on_conversion_finished)
        self.thread.start()

    def append_output(self, text):
        self.output_text.append(text.strip())
        
    def on_conversion_finished(self):
        self.output_text.append("\n✅ تمت عملية التحويل بنجاح!")
        self.open_output_btn.setEnabled(True)

    def open_output_folder(self):
        if self.py_file:
            folder = os.path.dirname(self.py_file)
            if os.path.exists(folder):
                # استخدام os.startfile لفتح المجلد (متوافق مع ويندوز)
                # لمنصات أخرى، يمكن استخدام subprocess.Popen(['xdg-open', folder]) على لينكس
                # أو subprocess.Popen(['open', folder]) على ماك
                try:
                    os.startfile(folder)
                except AttributeError:
                    # بديل للمنصات غير ويندوز
                    opener = "open" if sys.platform == "darwin" else "xdg-open"
                    subprocess.Popen([opener, folder])


    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile().strip()

            if file_path.endswith(".py"):
                self.py_file = file_path
                self.select_py_btn.setText(f"📂 {os.path.basename(file_path)}")

            elif file_path.endswith(".ico"):
                self.icon_file = file_path
                self.select_icon_btn.setText(f"🖼️ {os.path.basename(file_path)}")
                self.update_icon_preview()

            elif file_path.endswith(".txt"):
                self.version_file = file_path
                self.select_version_btn.setText(f"📝 {os.path.basename(file_path)}")
                
# ============= النافذة الرئيسية والتطبيق =============

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("محول بايثون إلى EXE")
        self.setCentralWidget(PyToExeTab())
        self.resize(650, 700)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())