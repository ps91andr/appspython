import sys
import os
import re
import requests
import base64
import mimetypes
import uuid
from urllib.parse import urljoin, urlparse

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QProgressBar, QMessageBox, QFileDialog, QDialog, QScrollArea,
    QFrame, QCheckBox, QMainWindow
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QPixmap, QClipboard

from bs4 import BeautifulSoup

# ======[ دالة مساعدة للإشعارات (Toast) ]======
# تمت إضافة هذه الدالة لأنها كانت مستخدمة في الكود ولكن غير معرّفة.
def show_toast(parent, title, message, icon_type="info", duration=5000):
    """
    يعرض إشعارًا منبثقًا (toast) فوق النافذة الرئيسية.
    """
    toast = QLabel(message, parent)
    
    # تحديد لون الخلفية بناءً على نوع الرسالة
    style = {
        "info": "background-color: #3498db; color: white;",
        "success": "background-color: #2ecc71; color: white;",
        "warning": "background-color: #f39c12; color: black;",
        "error": "background-color: #e74c3c; color: white;"
    }.get(icon_type, "background-color: #95a5a6; color: white;")
    
    toast.setStyleSheet(f"""
        {style}
        border-radius: 10px;
        padding: 10px 15px;
        font-size: 14px;
        font-weight: bold;
    """)
    toast.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
    toast.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    
    # تحديد موقع الإشعار في منتصف الجزء العلوي من النافذة
    parent_rect = parent.geometry()
    toast.adjustSize()
    toast_pos = parent.mapToGlobal(parent_rect.center())
    toast_pos.setX(toast_pos.x() - toast.width() // 2)
    toast_pos.setY(parent.mapToGlobal(parent.rect().topLeft()).y() + 20)
    toast.move(toast_pos)
    
    toast.show()
    QTimer.singleShot(duration, toast.deleteLater)

# ======[ فئة استخراج روابط الصور ]======
class ImageExtractor(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(list, str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            self.status.emit("جاري تحميل الصفحة...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(self.url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            image_urls = set()

            for img in soup.find_all('img'):
                for attr in ['src', 'data-src', 'data-lazy-src']:
                    if img.has_attr(attr):
                        src = img[attr]
                        if src and not src.strip().startswith('data:image'):
                            full_url = urljoin(self.url, src.strip())
                            image_urls.add(full_url)

            for source in soup.find_all('source'):
                if source.has_attr('srcset'):
                    srcset = source['srcset'].split(',')[0].strip().split(' ')[0]
                    image_urls.add(urljoin(self.url, srcset))

            data_uris = soup.find_all('img', src=re.compile(r"^data:image/"))
            for img in data_uris:
                image_urls.add(img['src'])

            urls_list = list(image_urls)
            self.finished.emit(urls_list, f"تم العثور على {len(urls_list)} صورة.")
        except Exception as e:
            self.finished.emit([], f"فشل الاستخراج: {e}")


# ======[ مربع حوار لمعاينة الصور ]======
class PreviewDialog(QDialog):
    def __init__(self, image_urls, parent=None):
        super().__init__(parent)
        self.image_urls = image_urls
        self.selected_urls = []
        self.setWindowTitle("اختر الصور للتنزيل")
        self.resize(700, 500)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QFrame()
        scroll.setWidget(content)

        grid_layout = QVBoxLayout()
        content.setLayout(grid_layout)

        self.checkboxes = []

        for url in self.image_urls:
            row = QHBoxLayout()
            checkbox = QCheckBox()
            label = QLabel("؟")
            label.setMaximumWidth(100)
            label.setMinimumSize(100, 100)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("border: 1px solid #ccc;")

            self.load_thumbnail(label, url)

            row.addWidget(checkbox)
            row.addWidget(label)
            row.addWidget(QLabel(url[:60] + "..." if len(url) > 60 else url))
            row.addStretch()

            grid_layout.addLayout(row)
            self.checkboxes.append((checkbox, url))

        layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("تحديد الكل")
        deselect_all_btn = QPushButton("إلغاء التحديد")
        download_btn = QPushButton("تنزيل المحددة")

        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn.clicked.connect(self.deselect_all)
        download_btn.clicked.connect(self.accept)

        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(deselect_all_btn)
        btn_layout.addWidget(download_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_thumbnail(self, label, url):
        try:
            if url.startswith('data:image'):
                header, encoded = url.split(',', 1)
                data = base64.b64decode(encoded)
                pixmap = QPixmap()
                pixmap.loadFromData(data)
            else:
                # Note: This is synchronous and can freeze the dialog.
                # For a better UX, this should be done in a separate thread.
                response = requests.get(url, timeout=5, stream=True)
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
            label.setPixmap(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio))
        except Exception:
            label.setText("؟")

    def select_all(self):
        for cb, _ in self.checkboxes:
            cb.setChecked(True)

    def deselect_all(self):
        for cb, _ in self.checkboxes:
            cb.setChecked(False)

    def get_selected_urls(self):
        return [url for cb, url in self.checkboxes if cb.isChecked()]


# ======[ فئة تنزيل كل الصور من الصفحة ]======
class ImageDownloader(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        try:
            self.status.emit("جاري استخراج روابط الصور...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(self.url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            image_urls = set()

            for img in soup.find_all('img'):
                for attr in ['src', 'data-src', 'data-lazy-src']:
                    if img.has_attr(attr):
                        src = img[attr]
                        if src and not src.strip().startswith('data:image'):
                            image_urls.add(urljoin(self.url, src.strip()))

            for source in soup.find_all('source'):
                if source.has_attr('srcset'):
                    srcset = source['srcset'].split(',')[0].strip().split(' ')[0]
                    image_urls.add(urljoin(self.url, srcset))
            
            self.status.emit(f"تم العثور على {len(image_urls)} رابط صورة فريد.")
            
            if not image_urls:
                self.finished.emit(True, "لم يتم العثور على روابط صور قابلة للتنزيل.")
                return

            os.makedirs(self.save_path, exist_ok=True)
            total_images = len(image_urls)
            downloaded_count = 0

            for i, img_url in enumerate(image_urls):
                if not self.is_running:
                    break

                progress_value = int(((i + 1) / total_images) * 100)
                self.progress.emit(progress_value)

                try:
                    self.status.emit(f"جاري تنزيل: {img_url[:80]}...")
                    img_response = requests.get(img_url, headers=headers, stream=True, timeout=10)
                    img_response.raise_for_status()

                    content_type = img_response.headers.get('content-type')
                    if content_type:
                        extension = mimetypes.guess_extension(content_type.split(';')[0])
                        if not extension or extension == '.jpe':
                            extension = '.jpg'
                    else:
                        extension = os.path.splitext(urlparse(img_url).path)[1] or '.jpg'

                    parsed_path = urlparse(img_url).path
                    basename = os.path.basename(parsed_path)
                    if not basename or '.' not in basename:
                        filename = f"image_{uuid.uuid4().hex[:8]}{extension}"
                    else:
                        filename = f"{os.path.splitext(basename)[0]}{extension}"

                    filepath = os.path.join(self.save_path, filename)

                    count = 1
                    original_filepath = filepath
                    while os.path.exists(filepath):
                        name, ext = os.path.splitext(original_filepath)
                        filepath = f"{name}_{count}{ext}"
                        count += 1
                    
                    with open(filepath, 'wb') as f:
                        for chunk in img_response.iter_content(8192):
                            f.write(chunk)

                    downloaded_count += 1

                except Exception as e:
                    self.status.emit(f"فشل تنزيل {img_url[:80]}: {e}")

            self.handle_data_uris(soup)

            final_message = f"اكتمل التنزيل! تم حفظ {downloaded_count} صورة."
            self.status.emit(final_message)
            self.finished.emit(True, final_message)

        except requests.exceptions.RequestException as e:
            self.finished.emit(False, f"خطأ في الشبكة أو الرابط: {e}")
        except Exception as e:
            self.finished.emit(False, f"حدث خطأ غير متوقع: {e}")

    def handle_data_uris(self, soup):
        data_uris = soup.find_all('img', src=re.compile(r"data:image/([a-zA-Z]+);base64,"))
        if not data_uris:
            return
            
        self.status.emit(f"جاري معالجة {len(data_uris)} صورة مضمنة...")
        for img_tag in data_uris:
            try:
                header, encoded_data = img_tag['src'].split(',', 1)
                file_ext = "." + header.split('/')[1].split(';')[0]
                image_data = base64.b64decode(encoded_data)
                
                filename = f"inline_image_{uuid.uuid4().hex[:8]}{file_ext}"
                filepath = os.path.join(self.save_path, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(image_data)
            except Exception as e:
                self.status.emit(f"فشل معالجة صورة مضمنة: {e}")


# ======[ فئة تنزيل الصور المحددة ]======
class ImageDownloaderDirect(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, urls, save_path):
        super().__init__()
        self.urls = urls
        self.save_path = save_path
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        try:
            os.makedirs(self.save_path, exist_ok=True)
            total = len(self.urls)
            downloaded = 0
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            for i, url in enumerate(self.urls):
                if not self.is_running:
                    break

                self.progress.emit(int((i + 1) / total * 100))
                self.status.emit(f"تنزيل: {url[:60]}...")

                try:
                    if url.startswith('data:image'):
                        header, encoded = url.split(',', 1)
                        file_ext = header.split('/')[1].split(';')[0]
                        data = base64.b64decode(encoded)
                        filename = f"image_{uuid.uuid4().hex[:8]}.{file_ext}"
                        filepath = os.path.join(self.save_path, filename)
                        with open(filepath, 'wb') as f:
                            f.write(data)
                    else:
                        response = requests.get(url, headers=headers, stream=True, timeout=10)
                        response.raise_for_status()

                        content_type = response.headers.get('content-type')
                        ext = mimetypes.guess_extension(content_type.split(';')[0]) if content_type else ''
                        if not ext or ext == '.jpe':
                            ext = '.jpg'

                        parsed = urlparse(url)
                        basename = os.path.basename(parsed.path)
                        name = os.path.splitext(basename)[0] if basename and '.' in basename else f"image_{uuid.uuid4().hex[:8]}"
                        filename = f"{name}{ext}"
                        filepath = os.path.join(self.save_path, filename)

                        count = 1
                        original = filepath
                        while os.path.exists(filepath):
                            name_part, ext_part = os.path.splitext(original)
                            filepath = f"{name_part}_{count}{ext_part}"
                            count += 1

                        with open(filepath, 'wb') as f:
                            for chunk in response.iter_content(8192):
                                f.write(chunk)

                    downloaded += 1
                except Exception as e:
                    print(f"فشل في تنزيل {url}: {e}")

            msg = f"تم تنزيل {downloaded}/{total} صورة."
            self.status.emit(msg)
            self.finished.emit(True, msg)
        except Exception as e:
            self.finished.emit(False, f"خطأ: {e}")


# ======[ الواجهة الرسومية الرئيسية ]======
class ImageDownloaderTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('أداة تنزيل الصور من الويب (متكاملة)')
        self.setMinimumWidth(620)
        self.downloader_thread = None
        self.extractor_thread = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("أدخل رابط صفحة الويب هنا")

        self.paste_button = QPushButton("📋")
        self.copy_button = QPushButton("📤")
        self.clear_button = QPushButton("🗑️")
        self.clear_paste_button = QPushButton("🧹📋")

        for btn in [self.paste_button, self.copy_button, self.clear_button]:
            btn.setFixedWidth(50)
            btn.setFixedHeight(30)
        self.clear_paste_button.setFixedWidth(60)
        self.clear_paste_button.setFixedHeight(30)

        self.paste_button.setToolTip("لصق الرابط (Ctrl+V)")
        self.copy_button.setToolTip("نسخ الرابط (Ctrl+C)")
        self.clear_button.setToolTip("مسح الرابط")
        self.clear_paste_button.setToolTip("مسح ثم لصق (Ctrl+Shift+V)")

        self.paste_button.clicked.connect(self.paste_url)
        self.copy_button.clicked.connect(self.copy_url)
        self.clear_button.clicked.connect(self.clear_url)
        self.clear_paste_button.clicked.connect(self.clear_and_paste)

        self.url_input.textChanged.connect(self.update_buttons)
        self.url_input.cursorPositionChanged.connect(self.update_buttons)

        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.paste_button)
        url_layout.addWidget(self.copy_button)
        url_layout.addWidget(self.clear_button)
        url_layout.addWidget(self.clear_paste_button)

        layout.addLayout(url_layout)

        self.help_label = QLabel("💡 نصيحة: انسخ الرابط من المتصفح ثم اضغط Ctrl+V أو انقر على 📋 للصق.")
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #555; font-size: 11px; padding: 5px;")
        layout.addWidget(self.help_label)

        buttons_layout = QHBoxLayout()

        self.preview_button = QPushButton("استخراج الصور")
        self.preview_button.clicked.connect(self.extract_images)
        buttons_layout.addWidget(self.preview_button)

        self.download_button = QPushButton("بدء تنزيل الصور")
        self.download_button.clicked.connect(self.start_download)
        buttons_layout.addWidget(self.download_button)

        layout.addLayout(buttons_layout)

        self.status_label = QLabel("الحالة: جاهز")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)
        self.update_buttons()

    def update_buttons(self):
        has_text = self.url_input.text().strip() != ""
        clipboard = QApplication.clipboard()
        clipboard_has_text = clipboard.text().strip() != "" if clipboard is not None else False

        self.copy_button.setEnabled(has_text)
        self.clear_button.setEnabled(has_text)
        self.paste_button.setEnabled(clipboard_has_text)
        self.clear_paste_button.setEnabled(clipboard_has_text)
        self.preview_button.setEnabled(has_text)
        self.download_button.setEnabled(has_text)

    def copy_url(self):
        text = self.url_input.text().strip()
        if not text:
            QMessageBox.information(self, "فارغ", "لا يوجد رابط لنسخه.")
            return

        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
            self.status_label.setText("تم نسخ الرابط إلى الحافظة.")
            self.copy_button.setText("✓")
            QTimer.singleShot(800, lambda: self.copy_button.setText("📤"))

    def paste_url(self):
        clipboard = QApplication.clipboard()
        if not clipboard: return
        text = clipboard.text().strip()
        if not text:
            QMessageBox.information(self, "الحافظة فارغة", "لا يوجد نص في الحافظة.")
            return

        if text.startswith(('http://', 'https://')):
            self.url_input.setText(text)
            self.status_label.setText("تم لصق الرابط بنجاح.")
        else:
            reply = QMessageBox.question(
                self,
                "هل ترغب في اللصق؟",
                f"النص في الحافظة ليس رابطًا صالحًا. هل تريد لصقه؟\n\n{text[:100]}...",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.url_input.setText(text)
        self.update_buttons()

    def clear_url(self):
        self.url_input.clear()
        self.status_label.setText("تم مسح الرابط.")
        self.update_buttons()

    def clear_and_paste(self):
        self.url_input.clear()
        self.status_label.setText("تم مسح الرابط. جاري المحاولة في اللصق...")

        clipboard = QApplication.clipboard()
        if not clipboard: return
        text = clipboard.text().strip()

        if not text:
            self.status_label.setText("الحافظة فارغة بعد المسح.")
            return

        if text.startswith(('http://', 'https://')):
            self.url_input.setText(text)
            self.status_label.setText("تم المسح واللصق بنجاح.")
        else:
            reply = QMessageBox.question(
                self,
                "لصق كرابط؟",
                f"النص ليس رابطًا صالحًا. هل تريد لصقه مع ذلك؟\n\n{text[:100]}...",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.url_input.setText(text)
                self.status_label.setText("تم اللصق رغم عدم الصلاحية.")
            else:
                self.status_label.setText("تم الإلغاء بعد المسح.")
        self.update_buttons()

    def extract_images(self):
        url = self.url_input.text().strip()
        if not url.startswith(('http://', 'https://')):
            QMessageBox.warning(self, "خطأ", "الرجاء إدخال رابط صالح يبدأ بـ http:// أو https://")
            return

        show_toast(self.window(), "🔍 استخراج", "جاري استخراج الصور...", "info", 7000)

        self.preview_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.preview_button.setText("جاري الاستخراج...")
        self.progress_bar.setValue(0)

        self.extractor_thread = ImageExtractor(url)
        self.extractor_thread.progress.connect(self.progress_bar.setValue)
        self.extractor_thread.status.connect(self.status_label.setText)
        self.extractor_thread.finished.connect(self.on_extract_finished)
        self.extractor_thread.start()

    def on_extract_finished(self, image_urls, message):
        self.extractor_thread = None
        self.preview_button.setEnabled(True)
        self.download_button.setEnabled(True)
        self.preview_button.setText("استخراج الصور")
        self.status_label.setText(message)

        if not image_urls:
            show_toast(self.window(), "❌ فشل", "لم يتم العثور على صور.", "warning", 7000)
            return

        show_toast(self.window(), "✅ نجاح", f"تم العثور على {len(image_urls)} صورة.", "success", 7000)

        dialog = PreviewDialog(image_urls, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = dialog.get_selected_urls()
            if not selected:
                show_toast(self.window(), "ℹ️ تنبيه", "لم تُختر أي صور.", "info", 7000)
                return

            save_dir = QFileDialog.getExistingDirectory(self, "اختر مجلد الحفظ", "downloaded_images")
            if not save_dir:
                return

            self.start_download_direct(selected, save_dir)

    def start_download(self):
        url = self.url_input.text().strip()
        if not url.startswith(('http://', 'https://')):
            QMessageBox.warning(self, "خطأ في الإدخال", "الرجاء إدخال رابط صالح يبدأ بـ http:// أو https://")
            return

        save_dir = QFileDialog.getExistingDirectory(self, "اختر مجلد الحفظ", "downloaded_images")
        if not save_dir:
            return

        show_toast(self.window(), "📥 تنزيل", "جاري تنزيل جميع الصور...", "info", 7000)

        self.download_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.download_button.setText("جاري التنزيل...")
        self.progress_bar.setValue(0)

        self.downloader_thread = ImageDownloader(url, save_dir)
        self.downloader_thread.progress.connect(self.progress_bar.setValue)
        self.downloader_thread.status.connect(self.status_label.setText)
        self.downloader_thread.finished.connect(self.on_download_finished)
        self.downloader_thread.start()

    def start_download_direct(self, urls, save_path):
        self.download_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.download_button.setText("جاري التنزيل...")
        self.progress_bar.setValue(0)

        self.downloader_thread = ImageDownloaderDirect(urls, save_path)
        self.downloader_thread.progress.connect(self.progress_bar.setValue)
        self.downloader_thread.status.connect(self.status_label.setText)
        self.downloader_thread.finished.connect(self.on_download_finished)
        self.downloader_thread.start()

    def on_download_finished(self, success, message):
        self.update_button_states()
        self.download_button.setText("بدء تنزيل الصور")
        self.status_label.setText(message)
        
        if success:
            show_toast(self.window(), "🎉 نجاح", "اكتمل التنزيل!", "success", 7000)
            QMessageBox.information(self, "اكتمل", message)
        else:
            show_toast(self.window(), "❌ خطأ", "فشل التنزيل.", "error", 7000)
            QMessageBox.critical(self, "خطأ", message)
            
        self.downloader_thread = None

    def update_button_states(self):
        has_text = self.url_input.text().strip() != ""
        self.preview_button.setEnabled(has_text)
        self.download_button.setEnabled(has_text)

    def closeEvent(self, event):
        if self.extractor_thread and self.extractor_thread.isRunning():
            self.extractor_thread.wait() # Extractor does not have a stop method
        if self.downloader_thread and self.downloader_thread.isRunning():
            self.downloader_thread.stop()
            self.downloader_thread.wait()
        event.accept()

# ============= [#--- مضاف ---#] مكونات تبويب تنزيل الصور من الويب 1005 =============

# ======[ نقطة تشغيل التطبيق الرئيسية ]======
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft) # دعم التخطيط من اليمين لليسار

    main_window = QMainWindow()
    main_window.setWindowTitle('أداة تنزيل الصور')
    
    downloader_tab = ImageDownloaderTab()
    main_window.setCentralWidget(downloader_tab)
    
    # ربط حدث الإغلاق الخاص بالنافذة بدالة الإغلاق في الويدجت
    main_window.closeEvent = downloader_tab.closeEvent

    main_window.show()
    sys.exit(app.exec())