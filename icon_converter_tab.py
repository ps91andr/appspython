import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QMessageBox, QGroupBox, QCheckBox, QProgressBar, QSizePolicy,
    QColorDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor
from PIL import Image

class ConvertThread(QThread):
    """
    مهمة منفصلة (Thread) لمعالجة تحويل الصور لتجنب تجميد الواجهة.
    """
    progress_updated = pyqtSignal(int)
    conversion_finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, image_path, icon_path, sizes, bg_color=None):
        super().__init__()
        self.image_path = image_path
        self.icon_path = icon_path
        self.sizes = sorted(sizes)  # التأكد من أن الأحجام مرتبة
        self.bg_color = bg_color

    def run(self):
        try:
            img = Image.open(self.image_path)

            # معالجة الصور الشفافة إذا تم تحديد لون خلفية
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                if self.bg_color:
                    # إنشاء خلفية باللون المحدد
                    background = Image.new('RGBA', img.size, self.bg_color)
                    # دمج الصورة الشفافة فوق الخلفية
                    img = Image.alpha_composite(background, img.convert('RGBA'))

            # تحويل الصورة إلى RGB إذا كانت تحتوي على قناة ألفا وتم تطبيق خلفية
            if 'A' in img.mode and self.bg_color:
                img = img.convert('RGB')

            images_to_save = []
            total_sizes = len(self.sizes)
            # إنشاء صور مصغرة لكل حجم مطلوب
            for i, size in enumerate(self.sizes):
                img_copy = img.copy()
                img_copy.thumbnail((size, size), Image.Resampling.LANCZOS)
                images_to_save.append(img_copy)
                # إرسال إشارة بتحديث شريط التقدم
                self.progress_updated.emit(int((i + 1) / total_sizes * 100))

            # حفظ الصور في ملف .ico واحد متعدد الأحجام
            if images_to_save:
                images_to_save[0].save(
                    self.icon_path,
                    format='ICO',
                    append_images=images_to_save[1:]  # إضافة باقي الأحجام
                )

            # إرسال إشارة بانتهاء التحويل بنجاح
            self.conversion_finished.emit(self.icon_path)
        except Exception as e:
            # إرسال إشارة في حالة حدوث خطأ
            self.error_occurred.emit(f"خطأ في مكتبة Pillow: {e}")


class IconConverterTab(QWidget):
    """
    الواجهة الرئيسية للتطبيق.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("محول الصور إلى أيقونات")
        self.setAcceptDrops(True) # تفعيل السحب والإفلات

        # تهيئة متغيرات الحالة
        self.selected_image_path = None
        self.bg_color = None
        self.convert_thread = None
        self.files_to_process = []
        self.save_dir_for_batch = ""
        self.sizes_for_batch = []

        # بناء الواجهة الرسومية
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- قسم معاينة الصورة ---
        preview_group = QGroupBox("معاينة الصورة")
        preview_layout = QVBoxLayout()

        self.image_label = QLabel("اسحب وأسقط الصورة هنا أو اختر ملف", self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 20px;
                font-size: 16px;
                min-height: 300px;
            }
        """)
        preview_layout.addWidget(self.image_label)

        # معاينات الأحجام الصغيرة
        size_preview_layout = QHBoxLayout()
        size_preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.size_previews = {}
        for size in [32, 48, 64]:
            preview = QLabel()
            preview.setFixedSize(size, size)
            preview.setStyleSheet("border: 1px solid #ccc; background-color: white;")
            preview.setScaledContents(True)
            self.size_previews[size] = preview
            size_preview_layout.addWidget(preview)

        preview_layout.addLayout(size_preview_layout)
        preview_group.setLayout(preview_layout)
        main_layout.addWidget(preview_group)

        # --- قسم الإعدادات ---
        settings_group = QGroupBox("إعدادات التحويل")
        settings_layout = QVBoxLayout()

        # أحجام الأيقونات
        sizes_group = QGroupBox("أحجام الأيقونات المطلوبة")
        sizes_layout = QHBoxLayout()
        self.size_options = {
            16: QCheckBox('16x16'), 32: QCheckBox('32x32'), 48: QCheckBox('48x48'),
            64: QCheckBox('64x64'), 128: QCheckBox('128x128'), 256: QCheckBox('256x256')
        }
        for cb in self.size_options.values():
            cb.setChecked(True)
            sizes_layout.addWidget(cb)
        sizes_group.setLayout(sizes_layout)
        settings_layout.addWidget(sizes_group)

        # خيارات إضافية (لون الخلفية)
        options_layout = QHBoxLayout()
        self.bg_color_btn = QPushButton("اختر لون الخلفية (للشفافية)", self)
        self.bg_color_btn.clicked.connect(self.set_background_color)
        self.bg_color_label = QLabel()
        self.bg_color_label.setFixedSize(22, 22)
        self.bg_color_label.setStyleSheet("border: 1px solid black;")
        
        options_layout.addWidget(self.bg_color_btn)
        options_layout.addWidget(self.bg_color_label)
        options_layout.addStretch()
        settings_layout.addLayout(options_layout)
        
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # --- شريط التقدم وأزرار التحكم ---
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        self.select_btn = QPushButton("📂 اختر صورة", self)
        self.select_btn.clicked.connect(self.select_image)
        self.convert_btn = QPushButton("🔄 تحويل إلى .ico", self)
        self.convert_btn.clicked.connect(self.convert_to_icon)
        self.batch_btn = QPushButton("🔢 تحويل مجموعة صور", self)
        self.batch_btn.clicked.connect(self.batch_convert)
        
        btn_layout.addWidget(self.select_btn)
        btn_layout.addWidget(self.convert_btn)
        btn_layout.addWidget(self.batch_btn)
        main_layout.addLayout(btn_layout)

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "اختر صورة", "",
            "ملفات الصور (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*)"
        )
        if file_path:
            self.load_image(file_path)

    def load_image(self, file_path):
        self.selected_image_path = file_path
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            QMessageBox.warning(self, "خطأ", "فشل تحميل الصورة. قد يكون الملف تالفًا أو غير مدعوم.")
            self.selected_image_path = None
            return
        
        # عرض الصورة الرئيسية
        self.image_label.setPixmap(pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
        
        # تحديث المعاينات الصغيرة
        for size, preview in self.size_previews.items():
            preview.setPixmap(pixmap.scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

    def set_background_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.bg_color = (color.red(), color.green(), color.blue(), color.alpha())
            self.bg_color_label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")

    def convert_to_icon(self):
        if not self.selected_image_path:
            QMessageBox.warning(self, "خطأ", "يرجى اختيار صورة أولاً.")
            return

        sizes = [size for size, cb in self.size_options.items() if cb.isChecked()]
        if not sizes:
            QMessageBox.warning(self, "خطأ", "يرجى تحديد حجم واحد على الأقل.")
            return

        base_name = os.path.splitext(os.path.basename(self.selected_image_path))[0]
        save_path, _ = QFileDialog.getSaveFileName(
            self, "حفظ ملف الأيقونة",
            os.path.join(os.path.dirname(self.selected_image_path), f"{base_name}.ico"),
            "ملفات الأيقونات (*.ico)"
        )
        
        if save_path:
            self.start_conversion(self.selected_image_path, save_path, sizes)

    def start_conversion(self, image_path, icon_path, sizes):
        self.set_ui_enabled(False)
        self.progress_bar.setValue(0)
        
        self.convert_thread = ConvertThread(image_path, icon_path, sizes, self.bg_color)
        self.convert_thread.progress_updated.connect(self.update_progress)
        self.convert_thread.conversion_finished.connect(self.on_conversion_complete)
        self.convert_thread.error_occurred.connect(self.on_conversion_error)
        self.convert_thread.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_conversion_complete(self, icon_path):
        # هذه الدالة قد تُستدعى أثناء التحويل الجماعي، لذا لا تعرض رسالة إلا إذا لم تكن في وضع التحويل الجماعي
        if not self.files_to_process:
            self.set_ui_enabled(True)
            self.progress_bar.setValue(100)
            
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("اكتمل التحويل")
            msg.setText(f"تم إنشاء الأيقونة بنجاح:\n{icon_path}")
            open_folder_btn = msg.addButton("فتح المجلد", QMessageBox.ButtonRole.ActionRole)
            open_folder_btn.clicked.connect(lambda: self.open_folder(icon_path))
            msg.addButton("موافق", QMessageBox.ButtonRole.AcceptRole)
            msg.exec()

    def on_conversion_error(self, error_msg):
        # نفس منطق الدالة السابقة، لا تعرض خطأ إلا إذا لم تكن في وضع التحويل الجماعي
        if not self.files_to_process:
            self.set_ui_enabled(True)
            QMessageBox.critical(self, "خطأ في التحويل", f"حدث خطأ:\n{error_msg}")

    def set_ui_enabled(self, enabled):
        self.select_btn.setEnabled(enabled)
        self.convert_btn.setEnabled(enabled)
        self.batch_btn.setEnabled(enabled)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if os.path.splitext(file_path)[1].lower() in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']:
                self.load_image(file_path)

    def batch_convert(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "اختر مجموعة صور للتحويل", "",
            "ملفات الصور (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*)"
        )
        if not files: return

        sizes = [size for size, cb in self.size_options.items() if cb.isChecked()]
        if not sizes:
            QMessageBox.warning(self, "خطأ", "يرجى تحديد حجم واحد على الأقل.")
            return

        save_dir = QFileDialog.getExistingDirectory(self, "اختر مجلد لحفظ الأيقونات")
        if not save_dir: return

        self.files_to_process = files
        self.save_dir_for_batch = save_dir
        self.sizes_for_batch = sizes
        self.process_next_batch_file()

    def process_next_batch_file(self):
        if not self.files_to_process:
            self.set_ui_enabled(True)
            QMessageBox.information(self, "اكتمل التحويل الجماعي", "تم تحويل جميع الملفات بنجاح.")
            return

        file_path = self.files_to_process.pop(0)
        self.load_image(file_path) # عرض الصورة الحالية في الواجهة
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        icon_path = os.path.join(self.save_dir_for_batch, f"{base_name}.ico")

        # إعادة ربط الإشارات لمعالجة الملف التالي في الطابور
        if self.convert_thread:
            try:
                self.convert_thread.conversion_finished.disconnect()
                self.convert_thread.error_occurred.disconnect()
            except TypeError:
                pass # الإشارة غير مرتبطة بالفعل

        self.start_conversion(file_path, icon_path, self.sizes_for_batch)
        self.convert_thread.conversion_finished.connect(self.on_batch_file_done)
        self.convert_thread.error_occurred.connect(self.on_batch_file_error)

    def on_batch_file_done(self, icon_path):
        print(f"تم بنجاح: {icon_path}")
        self.process_next_batch_file()

    def on_batch_file_error(self, error_msg):
        print(f"خطأ في ملف: {error_msg}")
        self.process_next_batch_file() # الاستمرار مع الملف التالي حتى لو فشل الحالي

    def open_folder(self, path):
        folder = os.path.dirname(path)
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin": # macOS
                os.system(f'open "{folder}"')
            else: # Linux
                os.system(f'xdg-open "{folder}"')
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"ไม่สามารถเปิด المجلد: {e}")

    def resizeEvent(self, event):
        # إعادة تحجيم الصورة في المعاينة عند تغيير حجم النافذة
        if self.selected_image_path:
            self.load_image(self.selected_image_path)
        super().resizeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = IconConverterTab()
    window.resize(500, 600) # تحديد حجم مبدئي مناسب
    window.show()
    sys.exit(app.exec())