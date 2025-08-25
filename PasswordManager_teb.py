import sys
import csv
import os
import shutil
import sqlite3
from PyQt6.QtWidgets import QDialog
from datetime import datetime
from collections import defaultdict
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox, QTableWidget,
    QHeaderView, QCompleter, QListView, QFileDialog, QTableWidgetItem
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtGui import QIcon


class PasswordManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مدير كلمات السر")
        
        self.resize(1400, 850)             # الحجم المبدئي
        self.setMinimumSize(800, 600)      # لا تقل عن هذا
        self.setMaximumSize(2200, 1200)    # لا تزيد عن هذا

        # تأكد من وجود مجلد الصور
        if not os.path.exists("images"):
            os.makedirs("images")
            
        self.db_file = "passwords.db"
        self.conn = sqlite3.connect(self.db_file)
        self.create_table()

        self.data = []
        self.editing_index = None
        self.show_passwords = False  # حالة إظهار كلمات السر

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
    
        # ====== شريط البحث ======
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("ابحث عن أي حقل")
        self.search_input.textChanged.connect(self.search_data)
        clear_button = QPushButton("إظهار الكل")
        clear_button.clicked.connect(lambda: self.search_input.clear())
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(clear_button)
        layout.addLayout(search_layout)
    
        # ====== ComboBox فلاتر الحقول الأساسية ======
        self.name_filter = QComboBox()
        self.name_filter.addItem("فرز حسب الاسم")
        self.name_filter.currentTextChanged.connect(self.filter_by_name)
    
        self.url_filter = QComboBox()
        self.url_filter.addItem("فرز حسب الرابط")
        self.url_filter.currentTextChanged.connect(self.filter_by_url)
    
        self.username_filter = QComboBox()
        self.username_filter.addItem("فرز حسب اسم المستخدم")
        self.username_filter.currentTextChanged.connect(self.filter_by_username)
    
        self.password_filter = QComboBox()
        self.password_filter.addItem("فرز حسب كلمة السر")
        self.password_filter.currentTextChanged.connect(self.filter_by_password)
    
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.name_filter)

        # فلتر المفضلة (تمت الإضافة هنا)
        self.favorite_filter = QComboBox()
        self.favorite_filter.addItems(["عرض الكل", "المفضلة فقط"])
        self.favorite_filter.currentTextChanged.connect(self.search_data)
        filter_layout.addWidget(self.favorite_filter)
        
        filter_layout.addWidget(self.url_filter)
        filter_layout.addWidget(self.username_filter)
        filter_layout.addWidget(self.password_filter)
    
        # ====== ComboBox جديدة لفلاتر الإيميل ======
        self.gmail_filter = QComboBox()
        self.gmail_filter.addItem("📧 Gmail فقط")
        self.gmail_filter.currentTextChanged.connect(self.search_input.setText)
    
        self.hotmail_filter = QComboBox()
        self.hotmail_filter.addItem("📧 Hotmail فقط")
        self.hotmail_filter.currentTextChanged.connect(self.search_input.setText)

        self.icloud_filter = QComboBox()
        self.icloud_filter.addItem("📧 iCloud فقط")
        self.icloud_filter.currentTextChanged.connect(self.search_input.setText)
   
        self.other_email_filter = QComboBox()
        self.other_email_filter.addItem("📧 نطاقات أخرى")
        self.other_email_filter.currentTextChanged.connect(self.search_input.setText)
    
        self.non_email_filter = QComboBox()
        self.non_email_filter.addItem("🧍 بدون نطاق بريد")
        self.non_email_filter.currentTextChanged.connect(self.search_input.setText)
    
        # إضافتهم إلى نفس السطر
        filter_layout.addWidget(self.gmail_filter)
        filter_layout.addWidget(self.hotmail_filter)
        filter_layout.addWidget(self.other_email_filter)
        filter_layout.addWidget(self.non_email_filter)
        filter_layout.addWidget(self.icloud_filter)

        layout.addLayout(filter_layout)
    
        # ====== الحقول النصية للإدخال ======
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("الاسم")
    
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("الرابط")
    
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("اسم المستخدم")
    
        pw_layout = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("كلمة السر")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
    
        self.toggle_pw_button = QPushButton("👁️")
        self.toggle_pw_button.setCheckable(True)
        self.toggle_pw_button.setFixedWidth(30)
        self.toggle_pw_button.clicked.connect(self.toggle_password_visibility)
    
        pw_layout.addWidget(self.password_input)
        pw_layout.addWidget(self.toggle_pw_button)
    
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("ملاحظات")

        # حقل اختيار المفضلة
        self.favorite_input = QComboBox()
        self.favorite_input.addItems(["غير مفضلة", "مفضلة"])
    
        # ====== أزرار الإدارة ======
        self.save_button = QPushButton("حفظ البيانات")
        self.save_button.clicked.connect(self.save_data)
    
        self.backup_button = QPushButton("إنشاء نسخة احتياطية")
        self.backup_button.clicked.connect(self.backup_csv)
    
        self.import_button = QPushButton("استيراد من ملف")
        self.import_button.clicked.connect(self.import_csv)
    
        self.export_button = QPushButton("تصدير إلى ملف")
        self.export_button.clicked.connect(self.export_csv)
    
        self.duplicates_button = QPushButton("عرض التكرارات فقط")
        self.duplicates_button.clicked.connect(self.show_duplicates)
    
        self.cancel_duplicates_button = QPushButton("إلغاء عرض التكرارات")
        self.cancel_duplicates_button.clicked.connect(self.load_data)
    
        self.delete_duplicates_button = QPushButton("حذف التكرارات والإبقاء على نسخة واحدة")
        self.delete_duplicates_button.clicked.connect(self.delete_duplicates)
    
        self.export_duplicates_button = QPushButton("تصدير التكرارات فقط")
        self.export_duplicates_button.clicked.connect(self.export_duplicates)
    
        self.toggle_column_pw_button = QPushButton("👁️ إخفاء كلمات السر")
        self.toggle_column_pw_button.setCheckable(True)
        self.toggle_column_pw_button.clicked.connect(self.toggle_column_passwords_visibility)
    
        # ====== تجميع كل عناصر الإدخال ======
        layout.addWidget(QLabel("الاسم:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("الرابط:"))
        layout.addWidget(self.url_input)
        layout.addWidget(QLabel("اسم المستخدم:"))
        layout.addWidget(self.username_input)
        layout.addWidget(QLabel("كلمة السر:"))
        layout.addLayout(pw_layout)
        layout.addWidget(QLabel("ملاحظات:"))
        layout.addWidget(self.note_input)
        layout.addWidget(QLabel("المفضلة:"))
        layout.addWidget(self.favorite_input)
    
        # ====== أزرار الصف الأول ======
        actions_layout1 = QHBoxLayout()
        actions_layout1.addWidget(self.save_button)
        actions_layout1.addWidget(self.import_button)
        actions_layout1.addWidget(self.export_button)
        actions_layout1.addWidget(self.backup_button)
        layout.addLayout(actions_layout1)
    
        # ====== أزرار الصف الثاني ======
        actions_layout2 = QHBoxLayout()
        actions_layout2.addWidget(self.cancel_duplicates_button)
        actions_layout2.addWidget(self.duplicates_button)
        actions_layout2.addWidget(self.delete_duplicates_button)
        actions_layout2.addWidget(self.export_duplicates_button)
        actions_layout1.addWidget(self.toggle_column_pw_button)

        layout.addLayout(actions_layout2)
    
        # ====== جدول البيانات ======
        self.table = QTableWidget()
        self.table.setColumnCount(8)  # تمت الزيادة إلى 8 بإضافة عمود المفضلة
        self.table.setHorizontalHeaderLabels(["الاسم", "الرابط", "اسم المستخدم", "كلمة السر", "ملاحظات", "إجراءات", "الصورة", "⭐ المفضلة"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setSortingEnabled(True)
    
        self.table.setColumnWidth(0, 170)  # الاسم
        self.table.setColumnWidth(1, 300)  # الرابط
        self.table.setColumnWidth(2, 250)  # اسم المستخدم
        self.table.setColumnWidth(3, 150)  # كلمة السر
        self.table.setColumnWidth(4, 120)  # ملاحظات
        self.table.setColumnWidth(5, 150)  # إجراءات
        self.table.setColumnWidth(6, 100)  # الصورة
    
        layout.addWidget(QLabel("البيانات المخزنة:"))
        layout.addWidget(self.table)
    
        # ====== التهيئة ======
        self.setLayout(layout)
        self.load_data()
        self.setup_autocomplete()
        self.table.horizontalHeader().sortIndicatorChanged.connect(self.rebuild_table_after_sort)

    def rebuild_table_after_sort(self):
        # استخراج البيانات من الخلايا المفروزة (الأعمدة من 0 إلى 4 فقط)
        sorted_data = []
        for row in range(self.table.rowCount()):
            row_values = []
            for col in range(5):  # أول 5 أعمدة هي البيانات
                item = self.table.item(row, col)
                row_values.append(item.text() if item else "")
            sorted_data.append(row_values)
    
        # مطابقة السجلات مع self.data للحصول على الصف الكامل (مع id)
        new_ordered_data = []
        used_ids = set()
        for sorted_row in sorted_data:
            for full_row in self.data:
                # قارن الاسم + الرابط + اسم المستخدم + كلمة السر + الملاحظات
                if list(full_row[1:6]) == sorted_row and full_row[0] not in used_ids:
                    new_ordered_data.append(full_row)
                    used_ids.add(full_row[0])
                    break
    
        # إعادة تحميل الجدول بالكامل مع أزرار الإجراءات
        self.table.setSortingEnabled(False)  # إيقاف الفرز التلقائي
        self.table.setRowCount(0)
        for idx, row in enumerate(new_ordered_data):
            self.insert_row(row, idx)
        self.table.setSortingEnabled(True)  # إعادة تفعيله بعد الإدخال اليدوي
    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS passwords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                note TEXT,
                favorite INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()    
    
    def toggle_column_passwords_visibility(self):
        self.show_passwords = not self.show_passwords
        
        if self.show_passwords:
            self.toggle_column_pw_button.setText("🙈 إظهار كلمات السر")
            self.toggle_column_pw_button.setIcon(QIcon.fromTheme("visibility-off"))
        else:
            self.toggle_column_pw_button.setText("👁️ إخفاء كلمات السر")
            self.toggle_column_pw_button.setIcon(QIcon.fromTheme("visibility"))
        
        self.load_data()
        
    def update_filters(self):
        # إيقاف الإشارات أثناء التحديث
        self.name_filter.blockSignals(True)
        self.url_filter.blockSignals(True)
        self.username_filter.blockSignals(True)
        self.password_filter.blockSignals(True)
        self.gmail_filter.blockSignals(True)
        self.hotmail_filter.blockSignals(True)
        self.other_email_filter.blockSignals(True)
        self.non_email_filter.blockSignals(True)
        self.icloud_filter.blockSignals(True)
 
        # تفريغ القوائم
        self.name_filter.clear()
        self.url_filter.clear()
        self.username_filter.clear()
        self.password_filter.clear()
        self.gmail_filter.clear()
        self.hotmail_filter.clear()
        self.other_email_filter.clear()
        self.non_email_filter.clear()
        self.icloud_filter.clear()
        

        # إضافة العناوين الأساسية
        self.name_filter.addItem("فرز حسب الاسم")
        self.url_filter.addItem("فرز حسب الرابط")
        self.username_filter.addItem("فرز حسب اسم المستخدم")
        self.password_filter.addItem("فرز حسب كلمة السر")
        self.gmail_filter.addItem("📧 Gmail فقط")
        self.hotmail_filter.addItem("📧 Hotmail فقط")
        self.other_email_filter.addItem("📧 نطاقات أخرى")
        self.non_email_filter.addItem("🧍 بدون نطاق بريد")
        self.icloud_filter.addItem("📧 iCloud فقط")
        
        # استخراج القيم من البيانات
        names = sorted(set(str(row[1]).strip() for row in self.data if row[1].strip()))
        urls = sorted(set(str(row[2]).strip() for row in self.data if row[2].strip()))
        usernames = sorted(set(str(row[3]).strip() for row in self.data if row[3].strip()))
        passwords = sorted(set(str(row[4]).strip() for row in self.data if row[4].strip()))
    
        self.name_filter.addItems(names)
        self.url_filter.addItems(urls)
        self.username_filter.addItems(usernames)
        self.password_filter.addItems(passwords)
    
        # تصنيف الإيميلات من عمود اسم المستخدم
        gmail_set = set()
        hotmail_set = set()
        other_domains_set = set()
        no_domain_set = set()
        icloud_set = set()
        
        for username in usernames:
            lower_u = username.lower()
            if "@gmail" in lower_u:
                gmail_set.add(username)
            elif "@hotmail.com" in lower_u:
                hotmail_set.add(username)
            elif "@icloud.com" in lower_u:
                icloud_set.add(username)
            elif "@" in lower_u:
                other_domains_set.add(username)
            else:
                no_domain_set.add(username)
    
        self.gmail_filter.addItems(sorted(gmail_set))
        self.hotmail_filter.addItems(sorted(hotmail_set))
        self.other_email_filter.addItems(sorted(other_domains_set))
        self.non_email_filter.addItems(sorted(no_domain_set))
        self.icloud_filter.addItems(sorted(icloud_set))

        # إعادة تفعيل الإشارات
        self.name_filter.blockSignals(False)
        self.url_filter.blockSignals(False)
        self.username_filter.blockSignals(False)
        self.password_filter.blockSignals(False)
        self.gmail_filter.blockSignals(False)
        self.hotmail_filter.blockSignals(False)
        self.other_email_filter.blockSignals(False)
        self.non_email_filter.blockSignals(False)
        self.icloud_filter.blockSignals(False)

    def filter_by_name(self, value):
        if value != "فرز حسب الاسم":
            self.search_input.setText(value)
        else:
            self.search_input.clear()
    
    def filter_by_url(self, value):
        if value != "فرز حسب الرابط":
            self.search_input.setText(value)
        else:
            self.search_input.clear()
    
    def filter_by_username(self, value):
        if value != "فرز حسب اسم المستخدم":
            self.search_input.setText(value)
        else:
            self.search_input.clear()
    
    def filter_by_password(self, value):
        if value != "فرز حسب كلمة السر":
            self.search_input.setText(value)
        else:
            self.search_input.clear()     
    
    
    def save_data(self):
        name = self.name_input.text().strip()
        url = self.url_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        note = self.note_input.text().strip()
        favorite = 1 if self.favorite_input.currentText() == "مفضلة" else 0

        # تحقق من الحقول الأساسية
        if not name or not url or not username or not password:
            QMessageBox.warning(self, "خطأ", "يرجى تعبئة جميع الحقول المطلوبة.")
            return

        try:
            cursor = self.conn.cursor()

            if self.editing_index is not None:
                # تحديث بيانات موجودة
                cursor.execute(
                    '''UPDATE passwords
                       SET name = ?, url = ?, username = ?, password = ?, note = ?, favorite = ?
                       WHERE id = ?''',
                    (name, url, username, password, note, favorite, self.editing_index)
                )
                self.editing_index = None
            else:
                # التحقق من وجود بيانات مكررة
                cursor.execute(
                    '''SELECT COUNT(*) FROM passwords
                       WHERE url = ? AND username = ? AND password = ?''',
                    (url, username, password)
                )
                count = cursor.fetchone()[0]

                if count > 0:
                    confirm = QMessageBox.question(
                        self,
                        "تكرار موجود",
                        "توجد بيانات مشابهة (رابط + اسم مستخدم + كلمة سر). هل تريد الحفظ على أي حال؟",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if confirm != QMessageBox.StandardButton.Yes:
                        return

                # إدخال جديد
                cursor.execute(
                    '''INSERT INTO passwords (name, url, username, password, note, favorite)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (name, url, username, password, note, favorite)
                )

            self.conn.commit()
            self.clear_inputs()
            self.load_data()
            QMessageBox.information(self, "تم", "تم حفظ البيانات بنجاح.")

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء الحفظ: {str(e)}")

    def clear_inputs(self):
        self.name_input.clear()
        self.url_input.clear()
        self.username_input.clear()
        self.password_input.clear()
        self.note_input.clear()
        self.favorite_input.setCurrentIndex(0)
        
    def load_data(self):
        self.data.clear()
        self.table.setRowCount(0)
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, url, username, password, note, favorite FROM passwords")
        rows = cursor.fetchall()
        for row in rows:
            self.data.append(row)
        
        # تحديث حالة زر إخفاء كلمات السر
        if hasattr(self, 'toggle_column_pw_button'):
            if self.show_passwords:
                self.toggle_column_pw_button.setText("🙈 إظهار كلمات السر")
            else:
                self.toggle_column_pw_button.setText("👁️ إخفاء كلمات السر")
        
        self.search_data()
        self.update_filters()

    def search_data(self):
        keyword = self.search_input.text().strip().lower()
        show_favorites_only = self.favorite_filter.currentText() == "المفضلة فقط"
        
        self.table.setRowCount(0)
    
        for idx, row in enumerate(self.data):
            # Match against keyword
            keyword_match = not keyword or any(keyword in str(cell).lower() for cell in row)
            
            # Match against favorite filter
            # row[6] is the 'favorite' column (0 or 1)
            favorite_match = not show_favorites_only or (len(row) > 6 and row[6] == 1)
    
            if keyword_match and favorite_match:
                self.insert_row(row, idx)

    def open_edit_dialog(self, row):
        # row = (id, name, url, username, password, note, favorite)
        dialog = EditDialog(
            self,
            record_id=row[0],
            name=row[1],
            url=row[2],
            username=row[3],
            password=row[4],
            note=row[5],
            favorite=row[6]
        )
        dialog.exec()

    def insert_row(self, row, idx):
        # row = (id, name, url, username, password, note, favorite)
        row_id, name, url, username, password, note, favorite = row
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)

        # ارتفاع الصف
        self.table.setRowHeight(row_idx, 60)

        values = [name, url, username, password, note]
    
        for col_idx, val in enumerate(values):
            # العنصر الخفي الذي يُستخدم للفرز
            item = QTableWidgetItem(val)
            self.table.setItem(row_idx, col_idx, item)
    
            # المكون المرئي داخل الخلية
            display_text = str(val) if val else ""
            
            # إذا كان عمود كلمة السر (المؤشر 3) وحالة الإخفاء مفعلة
            if col_idx == 3 and not self.show_passwords and val:
                display_text = "*" * 8
    
            label = QLabel(display_text)
            label.setToolTip(str(val))  # التلميح يظهر القيمة الكاملة دائماً
    
            copy_btn = QPushButton("📋")
            copy_btn.setFixedSize(24, 24)
            copy_btn.clicked.connect(lambda _, text=str(val): QApplication.clipboard().setText(text))
    
            item_widget = QWidget()
            layout = QHBoxLayout()
            layout.addWidget(copy_btn)
            layout.addWidget(label)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(5)
            item_widget.setLayout(layout)
    
            self.table.setCellWidget(row_idx, col_idx, item_widget)
    
        # أزرار الإجراءات
        edit_btn = QPushButton("🛠️")
        delete_btn = QPushButton("🗑️")
        preview_btn = QPushButton("👁️")
    
        edit_btn.clicked.connect(lambda _, r=row: self.open_edit_dialog(r))
        delete_btn.clicked.connect(lambda _, r=row_id: self.delete_row(r))
        preview_btn.clicked.connect(lambda _, r=row: self.preview_entry(r))
    
        action_layout = QHBoxLayout()
        action_layout.addWidget(edit_btn)
        action_layout.addWidget(delete_btn)
        action_layout.addWidget(preview_btn)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(5)
        action_widget = QWidget()
        action_widget.setLayout(action_layout)
        self.table.setCellWidget(row_idx, 5, action_widget)

        # ===== إضافة الصورة =====
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # ابحث عن امتدادات مختلفة
        possible_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
        image_path = None
        for ext in possible_extensions:
            path = os.path.join("images", f"{name}{ext}")
            if os.path.exists(path):
                image_path = path
                break

        if image_path:
            pixmap = QPixmap(image_path)
            # تصغير الصورة لتناسب الخلية مع الحفاظ على الأبعاد
            image_label.setPixmap(pixmap.scaled(80, 55, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            image_label.setText("-") # أو اتركها فارغة
            
        self.table.setCellWidget(row_idx, 6, image_label)

        # ===== زر المفضلة =====
        fav_btn = QPushButton("⭐" if favorite else "☆")
        fav_btn.setFixedSize(40, 30)
        fav_btn.clicked.connect(lambda _, r=row_id, btn=fav_btn: self.toggle_favorite(r, btn))
        self.table.setCellWidget(row_idx, 7, fav_btn)
        

    def toggle_favorite(self, row_id, button):
        cursor = self.conn.cursor()
        cursor.execute("SELECT favorite FROM passwords WHERE id=?", (row_id,))
        current = cursor.fetchone()[0]
        new_value = 0 if current else 1
        cursor.execute("UPDATE passwords SET favorite=? WHERE id=?", (new_value, row_id))
        self.conn.commit()
        button.setText("⭐" if new_value else "☆")

    def load_into_inputs(self, row_id):
        self.editing_index = row_id
        cursor = self.conn.cursor()
        cursor.execute("SELECT name, url, username, password, note, favorite FROM passwords WHERE id = ?", (row_id,))
        row = cursor.fetchone()
    
        if row:
            self.name_input.setText(row[0])
            self.url_input.setText(row[1])
            self.username_input.setText(row[2])
            self.password_input.setText(row[3])
            self.note_input.setText(row[4])
            self.favorite_input.setCurrentIndex(1 if row[5] else 0)
            
    def delete_row(self, row_id):
        reply = QMessageBox.question(self, "تأكيد الحذف", "هل تريد حذف هذا السطر؟",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM passwords WHERE id=?", (row_id,))
            self.conn.commit()
            self.load_data()
            
    def preview_entry(self, row):
        # row = (id, name, url, ...)
        msg = f"الاسم: {row[1]}\nالرابط: {row[2]}\nاسم المستخدم: {row[3]}\nكلمة السر: {row[4]}\nملاحظات: {row[5]}"
        QMessageBox.information(self, "معاينة البيانات", msg)

    def find_duplicates(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM passwords
            WHERE (url, username, password) IN (
                SELECT url, username, password
                FROM passwords
                GROUP BY url, username, password
                HAVING COUNT(*) > 1
            )
        ''')
        return cursor.fetchall()

    def show_duplicates(self):
        duplicates = self.find_duplicates()
        self.table.setRowCount(0)
        seen_counts = defaultdict(int)
    
        for row in duplicates:
            # row = (id, name, url, username, password, note, favorite)
            key = (row[2].strip().lower(), row[3].strip().lower(), row[4].strip())  # url, username, password
            seen_counts[key] += 1
    
            # عدّل الملاحظات لإظهار رقم التكرار
            note_with_count = f"{row[5]} (تكرار رقم {seen_counts[key]})" if row[5] else f"تكرار رقم {seen_counts[key]}"
    
            # استخدم البيانات مع الملاحظة المعدّلة
            display_row = (row[0], row[1], row[2], row[3], row[4], note_with_count, row[6])
            self.insert_row(display_row, idx=0)  # idx وهمي)

    def delete_duplicates(self):
        try:
            cursor = self.conn.cursor()
    
            # الحصول على التكرارات باستثناء أول إدخال لكل مجموعة
            cursor.execute('''
                DELETE FROM passwords
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM passwords
                    GROUP BY url, username, password
                )
            ''')
            self.conn.commit()
    
            QMessageBox.information(self, "تم", "تم حذف التكرارات والإبقاء على نسخة واحدة فقط.")
            self.load_data()
    
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء حذف التكرارات: {str(e)}")

    def export_duplicates(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "تصدير التكرارات", "تكرارات.csv", "CSV Files (*.csv)")
        if file_path:
            try:
                cursor = self.conn.cursor()
                # استعلام يجلب فقط التكرارات مع كل الأعمدة
                cursor.execute('''
                    SELECT id, name, url, username, password, note, favorite
                    FROM passwords
                    WHERE (url, username, password) IN (
                        SELECT url, username, password
                        FROM passwords
                        GROUP BY url, username, password
                        HAVING COUNT(*) > 1
                    )
                    ORDER BY url, username, password
                ''')
                duplicates = cursor.fetchall()
    
                with open(file_path, "w", newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(["ID", "الاسم", "الرابط", "اسم المستخدم", "كلمة السر", "ملاحظات", "مفضلة"])  # العناوين
                    writer.writerows(duplicates)
    
                QMessageBox.information(self, "تم", "تم تصدير التكرارات بنجاح.")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل في تصدير التكرارات: {str(e)}")

    def toggle_password_visibility(self):
        if self.toggle_pw_button.isChecked():
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pw_button.setText("🙈")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pw_button.setText("👁️")

    def backup_csv(self):
        db_file = self.db_file  # "passwords.db"
        
        if not os.path.exists(db_file):
            QMessageBox.warning(self, "تحذير", "لا يوجد قاعدة بيانات لإنشاء نسخة احتياطية.")
            return
    
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "اختر مكان حفظ النسخة الاحتياطية",
            f"backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.db",
            "SQLite Files (*.db)"
        )
        
        if file_path:
            try:
                shutil.copy(db_file, file_path)
                QMessageBox.information(self, "تم", "تم حفظ النسخة الاحتياطية من قاعدة البيانات بنجاح.")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل في حفظ النسخة الاحتياطية: {str(e)}")

    def import_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "استيراد ملف CSV", "", "CSV Files (*.csv)")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    reader = csv.reader(file)
                    # تخطي الهيدر إذا كان موجوداً
                    next(reader, None)
                    imported_data = [row for row in reader if len(row) >= 5]
    
                cursor = self.conn.cursor()
                for row in imported_data:
                    # افترض أن العمود السادس (إن وجد) هو للمفضلة
                    favorite = 1 if len(row) > 5 and row[5] in ['1', 'true', 'yes', 'مفضلة'] else 0
                    cursor.execute('''
                        INSERT INTO passwords (name, url, username, password, note, favorite)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (row[0], row[1], row[2], row[3], row[4], favorite))
                self.conn.commit()
    
                QMessageBox.information(self, "تم", "تم استيراد البيانات إلى قاعدة البيانات بنجاح.")
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء الاستيراد: {str(e)}")
                
    def export_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "تصدير الملف", "كلمات_السر.csv", "CSV Files (*.csv)")
        if file_path:
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT name, url, username, password, note, favorite FROM passwords")
                all_data = cursor.fetchall()
    
                with open(file_path, "w", newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    # كتابة الهيدر
                    writer.writerow(["Name", "URL", "Username", "Password", "Note", "Favorite"])
                    writer.writerows(all_data)
    
                QMessageBox.information(self, "تم", "تم تصدير البيانات بنجاح.")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء التصدير: {str(e)}")

    def setup_autocomplete(self):
        if not self.data:
            return
        fields = list(zip(*self.data))
        inputs = [
            (self.name_input, list(set(fields[1]))),
            (self.url_input, list(set(fields[2]))),
            (self.username_input, list(set(fields[3]))),
            (self.password_input, list(set(fields[4]))),
            (self.note_input, list(set(fields[5])))
        ]
        for line_edit, values in inputs:
            # فلترة القيم الفارغة وتحويلها إلى نص
            valid_values = sorted([str(v) for v in values if v])
            completer = QCompleter(valid_values)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setPopup(QListView())
            line_edit.setCompleter(completer)
            
    def __del__(self):
        self.conn.close()


class EditDialog(QDialog):
    def __init__(self, parent, record_id, name, url, username, password, note, favorite):
        super().__init__(parent)
        self.setWindowTitle("تعديل السجل")
        self.record_id = record_id
        self.conn = parent.conn
        self.parent = parent

        layout = QVBoxLayout()

        self.name_input = QLineEdit(name)
        self.url_input = QLineEdit(url)
        self.username_input = QLineEdit(username)
        self.password_input = QLineEdit(password)
        self.note_input = QLineEdit(note)

        self.favorite_input = QComboBox()
        self.favorite_input.addItems(["غير مفضلة", "مفضلة"])
        self.favorite_input.setCurrentIndex(1 if favorite else 0)

        layout.addWidget(QLabel("الاسم:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("الرابط:"))
        layout.addWidget(self.url_input)
        layout.addWidget(QLabel("اسم المستخدم:"))
        layout.addWidget(self.username_input)
        layout.addWidget(QLabel("كلمة السر:"))
        layout.addWidget(self.password_input)
        layout.addWidget(QLabel("ملاحظات:"))
        layout.addWidget(self.note_input)
        layout.addWidget(QLabel("المفضلة:"))
        layout.addWidget(self.favorite_input)

        save_button = QPushButton("حفظ التعديلات")
        save_button.clicked.connect(self.save_edit)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def save_edit(self):
        try:
            cursor = self.conn.cursor()
            favorite_value = 1 if self.favorite_input.currentText() == "مفضلة" else 0
            cursor.execute('''
                UPDATE passwords
                SET name = ?, url = ?, username = ?, password = ?, note = ?, favorite = ?
                WHERE id = ?
            ''', (
                self.name_input.text().strip(),
                self.url_input.text().strip(),
                self.username_input.text().strip(),
                self.password_input.text().strip(),
                self.note_input.text().strip(),
                favorite_value,
                self.record_id
            ))
            self.conn.commit()
            QMessageBox.information(self, "تم", "تم حفظ التعديلات بنجاح.")
            self.parent.load_data()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء التعديل: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PasswordManager()
    window.show()
    sys.exit(app.exec())