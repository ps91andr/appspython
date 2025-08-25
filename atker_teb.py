import sys
import os
import json # لاستخدام ملفات JSON للحفظ والتحميل

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QMessageBox, QFileDialog, QLineEdit,
    QSizePolicy, QDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import QTimer, QUrl, QPropertyAnimation, QEasingCurve, Qt
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

AZKAR_FILE = 'azkar.json'
SOUNDS_FOLDER = 'atker_sounds'

# ---- فئة الإشعار المخصص (Toast) - لا تغييرات هنا ----
class ToastNotification(QWidget):
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet("""
            QWidget { background-color: rgba(30, 30, 30, 220); color: white;
                      border-radius: 10px; border: 1px solid #555; padding: 15px; }
            QLabel#title_label { font-weight: bold; font-size: 16px; }
            QLabel#message_label { font-size: 14px; }
        """)
        layout = QVBoxLayout(self)
        title_label = QLabel(title); title_label.setObjectName("title_label")
        message_label = QLabel(message); message_label.setObjectName("message_label")
        layout.addWidget(title_label); layout.addWidget(message_label)
        self.timer = QTimer(self); self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out); self.timer.start(20000)
    def show_toast(self):
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(screen_geometry.right() - self.width() - 15, screen_geometry.bottom() - self.height() - 15)
        self.fade_in()
    def fade_in(self):
        self.setWindowOpacity(0.0); self.show()
        self.animation = QPropertyAnimation(self, b"windowOpacity"); self.animation.setDuration(300)
        self.animation.setStartValue(0.0); self.animation.setEndValue(1.0); self.animation.start()
    def fade_out(self):
        self.animation = QPropertyAnimation(self, b"windowOpacity"); self.animation.setDuration(300)
        self.animation.setStartValue(1.0); self.animation.setEndValue(0.0)
        self.animation.finished.connect(self.close); self.animation.start()


# ---- فئة نافذة إدارة الأذكار (جديدة) ----
class AzkarManagerDialog(QDialog):
    def __init__(self, azkar_list, parent=None):
        super().__init__(parent)
        self.azkar_list = azkar_list # العمل على نفس القائمة
        self.setWindowTitle("إدارة الأذكار")
        self.setMinimumSize(500, 400)
        self.layout = QVBoxLayout(self)

        # قائمة عرض الأذكار
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.on_item_selected)
        self.layout.addWidget(self.list_widget)

        # حقل لإضافة ذكر جديد
        add_layout = QHBoxLayout()
        self.zikr_input = QLineEdit()
        self.zikr_input.setPlaceholderText("اكتب الذكر الجديد هنا...")
        self.add_button = QPushButton("إضافة الذكر")
        self.add_button.clicked.connect(self.add_zikr)
        add_layout.addWidget(self.zikr_input)
        add_layout.addWidget(self.add_button)
        self.layout.addLayout(add_layout)
        
        # زر الحذف
        self.delete_button = QPushButton("حذف الذكر المحدد")
        self.delete_button.setEnabled(False) # تعطيل مبدئي
        self.delete_button.clicked.connect(self.delete_zikr)
        self.layout.addWidget(self.delete_button)

        self.populate_list()

    def populate_list(self):
        self.list_widget.clear()
        for zikr in self.azkar_list:
            item_text = f"({zikr['key']}) {zikr['text']}"
            self.list_widget.addItem(QListWidgetItem(item_text))

    def on_item_selected(self, current_item, previous_item):
        self.delete_button.setEnabled(current_item is not None)

    def add_zikr(self):
        text = self.zikr_input.text().strip()
        if not text:
            QMessageBox.warning(self, "خطأ", "لا يمكن إضافة ذكر فارغ.")
            return

        # إيجاد أكبر مفتاح (رقم) موجود لإضافة الرقم الذي يليه
        max_key = 0
        if self.azkar_list:
            max_key = max(int(z['key']) for z in self.azkar_list)
        
        new_zikr = {
            "text": text,
            "key": str(max_key + 1),
            "sound": None
        }
        
        self.azkar_list.append(new_zikr)
        self.save_azkar_to_file()
        self.populate_list() # تحديث القائمة المعروضة
        self.zikr_input.clear()

    def delete_zikr(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0: return

        zikr_to_delete = self.azkar_list[current_row]
        reply = QMessageBox.question(self, "تأكيد الحذف", 
            f"هل أنت متأكد من حذف الذكر التالي؟\n\n{zikr_to_delete['text']}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            del self.azkar_list[current_row]
            self.save_azkar_to_file()
            self.populate_list()

    def save_azkar_to_file(self):
        try:
            with open(AZKAR_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.azkar_list, f, ensure_ascii=False, indent=4)
        except IOError as e:
            QMessageBox.critical(self, "خطأ في الحفظ", f"لم يتمكن من حفظ ملف الأذكار: {e}")


# ---- النافذة الرئيسية للتطبيق ----
class AzkarReminder(QMainWindow):
    def __init__(self):
        super().__init__()
        self.active_toasts = []
        self.setWindowTitle("تذكير الأذكار")
        if os.path.exists("icon.png"): self.setWindowIcon(QIcon("icon.png"))
        self.setMinimumSize(450, 450)
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.load_azkar_from_file() # تحميل الأذكار عند البداية
        
        # --- قسم العد التنازلي ---
        countdown_layout = QVBoxLayout(); countdown_layout.setContentsMargins(10, 20, 10, 20)
        info_label = QLabel("الذكر التالي بعد"); info_label.setAlignment(Qt.AlignmentFlag.AlignCenter); info_label.setFont(QFont("Arial", 16))
        self.countdown_label = QLabel("--:--"); self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.countdown_label.setFont(QFont("Segment7", 60, QFont.Weight.Bold))
        self.countdown_label.setStyleSheet("color: #ccc; border: 2px solid #555; border-radius: 10px; background-color: #333;")
        self.countdown_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        countdown_layout.addWidget(info_label); countdown_layout.addWidget(self.countdown_label)
        main_layout.addLayout(countdown_layout)

        # --- قسم إدارة الأذكار واختيار الأصوات ---
        manage_layout = QHBoxLayout()
        browse_button = QPushButton("اختر مجلد الأصوات"); browse_button.clicked.connect(self.browse_for_sounds_folder)
        manage_button = QPushButton("إدارة الأذكار"); manage_button.clicked.connect(self.open_azkar_manager)
        manage_layout.addWidget(browse_button); manage_layout.addWidget(manage_button)
        main_layout.addLayout(manage_layout)
        
        self.sound_path_edit = QLineEdit(); self.sound_path_edit.setReadOnly(True)
        self.sound_path_edit.setPlaceholderText("لم يتم اختيار مجلد الأصوات بعد")
        main_layout.addWidget(self.sound_path_edit)
        self.status_label = QLabel("لم يتم اختيار مجلد بعد.")
        main_layout.addWidget(self.status_label)

        # --- قسم اختيار الفاصل الزمني ---
        time_layout = QHBoxLayout(); time_label = QLabel("التذكير كل:")
        time_layout.addWidget(time_label); self.time_value_spinbox = QSpinBox(self)
        self.time_value_spinbox.setRange(1, 999); self.time_value_spinbox.setValue(30)
        time_layout.addWidget(self.time_value_spinbox); self.time_unit_combo = QComboBox(self)
        self.time_unit_combo.addItems(["ثواني", "دقائق"]); time_layout.addWidget(self.time_unit_combo)
        main_layout.addLayout(time_layout)

        # --- زر البدء/الإيقاف ---
        self.start_button = QPushButton("بدء التذكير"); self.start_button.clicked.connect(self.toggle_reminder)
        self.start_button.setFixedHeight(40); main_layout.addWidget(self.start_button)
        
        # --- الإعدادات ---
        self.current_zikr_index = 0; self.sounds_folder_path = ""
        self.main_timer = QTimer(self); self.main_timer.timeout.connect(self.show_notification)
        self.countdown_timer = QTimer(self); self.countdown_timer.timeout.connect(self.update_countdown_display)
        self.remaining_seconds = 0
        self._player = QMediaPlayer(); self._audio_output = QAudioOutput(); self._player.setAudioOutput(self._audio_output)
        # محاولة تحميل مجلد الأصوات الافتراضي تلقائياً
        default_sounds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), SOUNDS_FOLDER)
        if os.path.exists(default_sounds_path):
            self.sound_path_edit.setText(default_sounds_path)
            self.map_sounds_to_azkar(default_sounds_path)    
    def load_azkar_from_file(self):
        default_azkar = [
            {"text": "سبحان الله", "key": "1", "sound": None}, {"text": "الحمد لله", "key": "2", "sound": None},
            {"text": "لا إله إلا الله", "key": "3", "sound": None}, {"text": "الله أكبر", "key": "4", "sound": None}
        ]
        try:
            with open(AZKAR_FILE, 'r', encoding='utf-8') as f:
                self.azkar_list = json.load(f)
                if not self.azkar_list: self.azkar_list = default_azkar
        except (FileNotFoundError, json.JSONDecodeError):
            self.azkar_list = default_azkar
            # حفظ الملف الافتراضي لأول مرة
            with open(AZKAR_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.azkar_list, f, ensure_ascii=False, indent=4)

    def open_azkar_manager(self):
        dialog = AzkarManagerDialog(self.azkar_list, self)
        dialog.exec() # إظهار النافذة وانتظار إغلاقها
        # بعد إغلاق النافذة، أعد تحميل الأذكار للتأكد من أن القائمة محدثة
        self.load_azkar_from_file()
        self.status_label.setText("تم تحديث قائمة الأذكار. قد تحتاج لإعادة اختيار مجلد الأصوات.")
        
    def browse_for_sounds_folder(self, *args):
        folder_path = QFileDialog.getExistingDirectory(self, "اختر مجلد الأصوات")
        if folder_path:
            self.sound_path_edit.setText(folder_path)
            self.map_sounds_to_azkar(folder_path)

    def map_sounds_to_azkar(self, folder_path):
        self.sounds_folder_path = folder_path
        found_count = 0
        sound_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.mp3', '.wav'))]
        for zikr in self.azkar_list: zikr["sound"] = None
        for file_name in sound_files:
            file_key = os.path.splitext(file_name)[0]
            for zikr in self.azkar_list:
                if file_key == zikr["key"]:
                    zikr["sound"] = os.path.join(folder_path, file_name); found_count += 1; break
        self.status_label.setText(f"تم ربط {found_count} من {len(self.azkar_list)} ملف صوت.")
        help_message = f"تم ربط {found_count} ملف صوتي بنجاح.\n\n" + "أسماء الملفات المطلوبة:\n"
        for zikr in self.azkar_list:
            status = "✓ تم" if zikr["sound"] else "✗ مفقود"
            help_message += f" • {zikr['key']}.mp3  ->  {zikr['text']}  ({status})\n"
        # QMessageBox.information(self, "نتيجة الربط", help_message)

    def get_interval_in_milliseconds(self):
        value = self.time_value_spinbox.value()
        return value * (1000 if self.time_unit_combo.currentText() == "ثواني" else 60 * 1000)

    def toggle_reminder(self):
        if self.main_timer.isActive():
            self.main_timer.stop(); self.countdown_timer.stop()
            self.start_button.setText("بدء التذكير")
            self.countdown_label.setText("--:--")
            self.countdown_label.setStyleSheet("color: #ccc; border: 2px solid #555; border-radius: 10px; background-color: #333;")
        else:
            if not self.sounds_folder_path:
                QMessageBox.warning(self, "خطأ", "الرجاء اختيار مجلد يحتوي على الأصوات أولاً."); return
            if not self.azkar_list:
                QMessageBox.warning(self, "خطأ", "قائمة الأذكار فارغة. الرجاء إضافة أذكار أولاً."); return
            interval = self.get_interval_in_milliseconds()
            self.main_timer.start(interval); self.countdown_timer.start(1000)
            self.remaining_seconds = interval // 1000
            self.update_countdown_display()
            self.start_button.setText("إيقاف التذكير")
            self.countdown_label.setStyleSheet("color: #00Aaff; border: 2px solid #555; border-radius: 10px; background-color: #333;")
            self.show_notification()

    def show_notification(self):
        if not self.azkar_list: return
        zikr_data = self.azkar_list[self.current_zikr_index]
        toast = ToastNotification("تذكير", zikr_data["text"]); toast.show_toast(); self.active_toasts.append(toast)
        if zikr_data.get("sound"):
            self._player.setSource(QUrl.fromLocalFile(zikr_data["sound"])); self._player.play()
        self.current_zikr_index = (self.current_zikr_index + 1) % len(self.azkar_list)
        self.remaining_seconds = self.main_timer.interval() // 1000
        self.update_countdown_display()
        
    def update_countdown_display(self):
        if self.remaining_seconds < 0: return
        self.countdown_label.setText(f"{self.remaining_seconds // 60:02d}:{self.remaining_seconds % 60:02d}")
        self.remaining_seconds -= 1
    def browse_for_sounds_folder(self, *args):
        # المسار الافتراضي: مجلد 'atker_sounds' بنفس مكان البرنامج
        default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), SOUNDS_FOLDER)
        
        # إنشاء المجلد إذا لم يكن موجوداً
        if not os.path.exists(default_path):
            try:
                os.makedirs(default_path)
            except OSError as e:
                QMessageBox.warning(self, "خطأ", f"تعذر إنشاء مجلد الأصوات الافتراضي: {e}")
        
        # فتح نافذة اختيار المجلد مع المسار الافتراضي
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "اختر مجلد الأصوات", 
            default_path,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder_path:
            self.sound_path_edit.setText(folder_path)
            self.map_sounds_to_azkar(folder_path)
    def closeEvent(self, event):
        reply = QMessageBox.question(self, "تأكيد الخروج", "هل أنت متأكد أنك تريد الخروج؟",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.main_timer.stop(); self.countdown_timer.stop()
            for toast in self.active_toasts: toast.close()
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AzkarReminder()
    window.show()
    sys.exit(app.exec())