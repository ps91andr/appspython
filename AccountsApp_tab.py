# --- START OF FILE إدارة الديون والقروض.py ---

import sys
import json
from datetime import datetime
import time
import os
# --- إضافة المكتبات الجديدة المطلوبة ---
import tempfile
import atexit

# --- محاولة استيراد psutil وإظهار رسالة إذا لم تكن مثبتة ---
try:
    import psutil
except ImportError:
    print("Error: psutil library not found. Please install it using: pip install psutil")
    sys.exit(1)


from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeWidget, QTreeWidgetItem, QHeaderView, QLabel,
    QDialog, QDialogButtonBox, QMessageBox, QListWidget, QListWidgetItem,
    QGridLayout, QFrame, QInputDialog, QFileDialog, QLineEdit,
    QRadioButton, QComboBox, QDateEdit, QGroupBox
)
from PyQt6.QtGui import QFont, QAction, QDoubleValidator, QPixmap
from PyQt6.QtCore import Qt, QDate, QSize

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

from arabic_reshaper import reshape
from bidi.algorithm import get_display

try:
    import pandas as pd
except ImportError:
    QMessageBox.critical(None, "مكتبة ناقصة", "مكتبة 'pandas' غير مثبتة.")
    sys.exit(1)


class AccountsApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("إدارة الديون والقروض")
        self.setGeometry(100, 100, 1100, 700)
        self.autosave_file = "accounts_data_autosave.json"
        self.config_file = "config.json"
        self.config = {}
        self.contacts = []
        self.ledgers = {}

        self._load_config()
        self.create_widgets()
        self.create_menu_bar()
        self._autoload_data()
        self.update_display()

    def _load_config(self):
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.config = {
                "header_text": "تقرير الحسابات", 
                "center_header_text": "",
                "logo_path": "",
                "header_font": {"method": "default", "value": ""},
                "body_font": {"method": "default", "value": ""}
            }
            self._save_config()

    def _save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"فشل في حفظ ملف الإعدادات: {e}")

    def closeEvent(self, event):
        self._autosave_data()
        event.accept()

    def _autosave_data(self):
        data = {"contacts": self.contacts, "ledgers": self.ledgers}
        try:
            with open(self.autosave_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "خطأ فادح", f"فشل حفظ بياناتك تلقائياً!\n{e}")

    def _autoload_data(self):
        try:
            with open(self.autosave_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.contacts = data.get("contacts", [])
            self.ledgers = data.get("ledgers", {})
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def create_widgets(self):
        main_layout = QHBoxLayout()
        central_widget = QWidget(self)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        left_panel = QWidget()
        left_panel.setMaximumWidth(250)
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("<b>جهات الاتصال</b>"))
        self.contacts_list = QListWidget()
        self.contacts_list.currentItemChanged.connect(self.display_contact_statement)
        left_layout.addWidget(self.contacts_list)
        manage_contacts_btn = QPushButton("إدارة جهات الاتصال", clicked=self.manage_contacts)
        left_layout.addWidget(manage_contacts_btn)
        main_layout.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.Shape.StyledPanel)
        header_layout = QGridLayout(header_frame)
        self.account_name_label = QLabel("<b>اختر جهة اتصال لعرض كشف الحساب</b>", font=QFont("Arial", 14))
        self.account_balance_label = QLabel("", font=QFont("Arial", 12))
        header_layout.addWidget(self.account_name_label, 0, 0)
        header_layout.addWidget(self.account_balance_label, 1, 0)
        right_layout.addWidget(header_frame)
        
        self.account_statement_tree = QTreeWidget()
        self.account_statement_tree.setColumnCount(6)
        self.account_statement_tree.setHeaderLabels(["التاريخ", "البيان", "مدين لك", "دائن عليك", "الرصيد", "إجراءات"])
        self.account_statement_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.account_statement_tree)

        tx_control_layout = QHBoxLayout()
        tx_control_layout.addStretch()
        tx_control_layout.addWidget(QPushButton("إضافة معاملة جديدة", clicked=self.add_ledger_transaction))
        tx_control_layout.addWidget(QPushButton("تصدير إلى PDF", clicked=self.export_to_pdf))
        right_layout.addLayout(tx_control_layout)
        main_layout.addWidget(right_panel)

    def create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("الملف")
        file_menu.addAction(QAction("حفظ البيانات...", self, triggered=self.save_data))
        file_menu.addAction(QAction("تحميل البيانات...", self, triggered=self.load_data))
        file_menu.addSeparator()
        file_menu.addAction(QAction("تصدير إلى Excel...", self, triggered=self.export_to_excel))
        file_menu.addAction(QAction("استيراد من Excel...", self, triggered=self.import_from_excel))
        file_menu.addSeparator()
        file_menu.addAction(QAction("إعدادات التقرير (PDF)...", self, triggered=self.open_header_settings))
        file_menu.addSeparator()
        file_menu.addAction(QAction("خروج", self, triggered=self.close))

    def open_header_settings(self):
        dialog = HeaderSettingsDialog(self, self.config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config = dialog.get_config()
            self._save_config()

    def update_display(self):
        current = self.contacts_list.currentItem()
        current_name = current.text() if current else None
        self.contacts_list.clear()
        for contact in sorted(self.contacts, key=lambda c: c['name']):
            item = QListWidgetItem(contact['name'])
            self.contacts_list.addItem(item)
            if contact['name'] == current_name:
                self.contacts_list.setCurrentItem(item)
        if self.contacts_list.count() > 0 and not self.contacts_list.currentItem():
            self.contacts_list.setCurrentRow(0)
        self.display_contact_statement()

    def display_contact_statement(self):
        item = self.contacts_list.currentItem()
        self.account_statement_tree.clear()
        if not item:
            self.account_name_label.setText("<b>اختر جهة اتصال لعرض كشف الحساب</b>")
            self.account_balance_label.setText("")
            return
        contact_name = item.text()
        self.account_name_label.setText(f"<b>كشف حساب: {contact_name}</b>")
        transactions = sorted(self.ledgers.get(contact_name, []), key=lambda x: str(x.get('date', '')))
        balance = 0.0
        for tx in transactions:
            debit, credit = (tx.get('amount', 0), 0.0) if tx.get('type') in ['loan_to_them', 'payment_from_them'] else (0.0, tx.get('amount', 0))
            balance += (debit - credit)
            row_data = [str(tx.get('date', '')), str(tx.get('description', '')), f"{debit:.2f}" if debit > 0 else "", f"{credit:.2f}" if credit > 0 else "", f"{balance:.2f}"]
            row = QTreeWidgetItem(row_data)
            self.account_statement_tree.addTopLevelItem(row)
            self.add_action_buttons(self.account_statement_tree, row, contact_name, tx)
        bal_text, bal_color = (f"لك مبلغ {abs(balance):.2f}", "green") if balance > 0 else ((f"عليك مبلغ {abs(balance):.2f}", "red") if balance < 0 else ("0.00 (الحساب مسدد)", "black"))
        self.account_balance_label.setText(f"الرصيد النهائي: <span style='color:{bal_color};'>{bal_text}</span>")

    def add_action_buttons(self, tree, item, contact_name, record):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(5)
        edit_btn = QPushButton("تعديل", clicked=lambda: self.edit_ledger_transaction_record(contact_name, record))
        delete_btn = QPushButton("حذف", clicked=lambda: self.delete_ledger_transaction_record(contact_name, record))
        layout.addWidget(edit_btn); layout.addWidget(delete_btn)
        tree.setItemWidget(item, 5, widget)

    def manage_contacts(self):
        dialog = ManageContactsDialog(self, self.contacts, self.ledgers)
        if dialog.exec(): self.contacts, self.ledgers = dialog.get_data(); self.update_display()
    
    def add_ledger_transaction(self):
        if not self.contacts: QMessageBox.warning(self, "خطأ", "يجب إضافة جهة اتصال أولاً."); return
        current_item = self.contacts_list.currentItem()
        selected_contact = current_item.text() if current_item else None
        dialog = LedgerTransactionDialog(self, self.contacts, selected_contact=selected_contact)
        if dialog.exec():
            self._add_new_transaction(dialog.get_data())
            self.update_display()
            
    def _add_new_transaction(self, data):
        data['id'] = str(f"{int(time.time() * 1000)}")
        contact = data['contact']
        self.ledgers.setdefault(contact, []).append(data)

    def edit_ledger_transaction_record(self, original_contact_name, tx_to_edit):
        dialog = LedgerTransactionDialog(self, self.contacts, data=tx_to_edit)
        if dialog.exec():
            new_data = dialog.get_data()
            tx_id_to_remove = tx_to_edit.get('id')
            new_contact_name = new_data.get('contact')

            if original_contact_name in self.ledgers and tx_id_to_remove is not None:
                self.ledgers[original_contact_name] = [
                    tx for tx in self.ledgers[original_contact_name] if str(tx.get('id')) != str(tx_id_to_remove)
                ]
                if not self.ledgers[original_contact_name]:
                    del self.ledgers[original_contact_name]

            new_data['id'] = str(tx_id_to_remove) # Ensure ID is preserved and is a string
            self.ledgers.setdefault(new_contact_name, []).append(new_data)
            
            self.update_display()

    def delete_ledger_transaction_record(self, contact_name, tx_to_delete):
        reply = QMessageBox.question(self, "تأكيد الحذف", "هل أنت متأكد من حذف هذه المعاملة؟",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            tx_id_to_remove = tx_to_delete.get('id')
            if contact_name in self.ledgers and tx_id_to_remove is not None:
                self.ledgers[contact_name] = [
                    tx for tx in self.ledgers[contact_name] if str(tx.get('id')) != str(tx_id_to_remove)
                ]
                if not self.ledgers[contact_name]:
                    del self.ledgers[contact_name]
                
                self.update_display()

    def _get_font_path(self, font_config):
        method = font_config.get("method", "default")
        value = font_config.get("value", "")
        if method == "file" and value and os.path.exists(value):
            return value
        if method == "system" and value:
            font_path = HeaderSettingsDialog.get_system_font_path(value)
            if font_path: return font_path
        if os.path.exists('arial.ttf'): return 'arial.ttf'
        return None

    def _draw_pdf_header(self, canvas, doc, font_name='Helvetica'):
        canvas.saveState()
        width, height = doc.pagesize; margin = doc.leftMargin
        right_text = self.config.get("header_text", "")
        center_text = self.config.get("center_header_text", "")
        logo_path = self.config.get("logo_path", "")
        if logo_path and os.path.exists(logo_path):
            try:
                img = ImageReader(logo_path)
                w, h = img.getSize(); aspect = h / float(w)
                canvas.drawImage(img, margin, height - 70, width=70, height=70 * aspect, mask='auto')
            except Exception as e: print(f"Error drawing logo: {e}")
        canvas.setFont(font_name, 14)
        if right_text: canvas.drawRightString(width - margin, height - 60, get_display(reshape(right_text)))
        if center_text: canvas.drawCentredString(width / 2, height - 60, get_display(reshape(center_text)))
        canvas.line(margin, height - 80, width - margin, height - 80)
        canvas.restoreState()

    def _draw_pdf_footer(self, canvas, doc, font_name='Helvetica'):
        canvas.saveState()
        width, height = doc.pagesize
        page_num_text = f"صفحة {canvas.getPageNumber()}"
        arabic_text = get_display(reshape(page_num_text))
        canvas.setFont(font_name, 9)
        canvas.drawCentredString(width / 2, 30, arabic_text)
        canvas.restoreState()

    def export_to_pdf(self):
        item = self.contacts_list.currentItem()
        if not item: QMessageBox.warning(self, "خطأ", "يجب اختيار جهة اتصال أولاً"); return
        contact_name = item.text()
        transactions = sorted(self.ledgers.get(contact_name, []), key=lambda x: str(x.get('date', '')))
        if not transactions: QMessageBox.warning(self, "خطأ", "لا توجد معاملات لتصديرها"); return
        file_path, _ = QFileDialog.getSaveFileName(self, "حفظ كشف الحساب", f"كشف حساب {contact_name}.pdf", "PDF (*.pdf)")
        if not file_path: return
        try:
            header_font_path = self._get_font_path(self.config.get("header_font", {}))
            body_font_path = self._get_font_path(self.config.get("body_font", {}))
            header_font_name = 'HeaderFont'
            if header_font_path: pdfmetrics.registerFont(TTFont(header_font_name, header_font_path)) 
            else: header_font_name = 'Helvetica'
            body_font_name = 'BodyFont'
            if body_font_path: pdfmetrics.registerFont(TTFont(body_font_name, body_font_path))
            else: body_font_name = 'Helvetica'
            doc = SimpleDocTemplate(file_path, pagesize=letter, topMargin=100)
            story = []
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name='ArabicTitle', fontName=body_font_name, fontSize=16, alignment=TA_CENTER, spaceAfter=12))
            styles.add(ParagraphStyle(name='ArabicNormal', fontName=body_font_name, fontSize=10, alignment=TA_RIGHT))
            styles.add(ParagraphStyle(name='ArabicNormalCenter', fontName=body_font_name, fontSize=10, alignment=TA_CENTER))
            prepare = lambda text: get_display(reshape(str(text)))
            story.append(Paragraph(prepare(f"كشف حساب: {contact_name}"), styles['ArabicTitle']))
            start_date = transactions[0].get('date', ''); end_date = transactions[-1].get('date', '')
            period_string = f"فترة التقرير من: {start_date} إلى: {end_date}"
            story.append(Paragraph(prepare(period_string), styles['ArabicNormalCenter']))
            story.append(Spacer(1, 12))
            data = [[prepare(h) for h in ["التاريخ", "البيان", "مدين (لك)", "دائن (عليك)", "الرصيد"]]]
            total_debit, total_credit, balance = 0.0, 0.0, 0.0
            for tx in transactions:
                debit, credit = (tx['amount'], 0.0) if tx.get('type') in ['loan_to_them', 'payment_from_them'] else (0.0, tx['amount'])
                total_debit += debit; total_credit += credit; balance += (debit - credit)
                desc_p = Paragraph(prepare(tx.get('description', '')), styles['ArabicNormal'])
                data.append([prepare(tx.get('date', '')), desc_p, prepare(f"{debit:.2f}" if debit > 0 else ""), prepare(f"{credit:.2f}" if credit > 0 else ""), prepare(f"{abs(balance):.2f}")])
            bal_note = "لك" if balance > 0 else ("عليك" if balance < 0 else "متوازن")
            data.append([prepare("الإجمالي"), Paragraph(prepare(f"الرصيد النهائي {bal_note}"), styles['ArabicNormal']), prepare(f"{total_debit:.2f}"), prepare(f"{total_credit:.2f}"), prepare(f"{abs(balance):.2f}")])
            table = Table(data, colWidths=[80, 200, 80, 80, 80], repeatRows=1)
            table.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, -1), body_font_name), ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -2), colors.beige), ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey), ('GRID', (0, 0), (-1, -1), 1, colors.black), ('ALIGN', (1, 1), (1, -2), 'RIGHT')]))
            story.append(table)
            def draw_header_and_footer(canvas, doc):
                self._draw_pdf_header(canvas, doc, font_name=header_font_name)
                self._draw_pdf_footer(canvas, doc, font_name=body_font_name)
            doc.build(story, onFirstPage=draw_header_and_footer, onLaterPages=draw_header_and_footer)
            QMessageBox.information(self, "نجاح", f"تم تصدير كشف الحساب إلى:\n{file_path}")
        except Exception as e: QMessageBox.critical(self, "خطأ فادح", f"فشل تصدير الملف: {e}")

    def save_data(self):
        path, _ = QFileDialog.getSaveFileName(self, "حفظ", "data.json", "JSON (*.json)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f: json.dump({"contacts": self.contacts, "ledgers": self.ledgers}, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "نجاح", "تم الحفظ.")
            except Exception as e: QMessageBox.critical(self, "خطأ", f"فشل الحفظ: {e}")
    def load_data(self):
        path, _ = QFileDialog.getOpenFileName(self, "تحميل", "", "JSON (*.json)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f: data = json.load(f)
                self.contacts = data.get("contacts", [])
                self.ledgers = data.get("ledgers", {})
                self.update_display()
                QMessageBox.information(self, "نجاح", "تم التحميل.")
            except Exception as e: QMessageBox.critical(self, "خطأ", f"فشل التحميل: {e}")
    def export_to_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "تصدير", "data.xlsx", "Excel (*.xlsx)")
        if path:
            try:
                all_tx = [dict(tx, contact=name) for name, txs in self.ledgers.items() for tx in txs]
                with pd.ExcelWriter(path) as writer:
                    pd.DataFrame(all_tx).to_excel(writer, "المعاملات", index=False)
                    pd.DataFrame(self.contacts).to_excel(writer, "جهات الاتصال", index=False)
                QMessageBox.information(self, "نجاح", "تم التصدير.")
            except Exception as e: QMessageBox.critical(self, "خطأ", f"فشل التصدير: {e}")
            
    def import_from_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "استيراد", "", "Excel (*.xlsx *.xls)")
        if not path: return
        if QMessageBox.question(self, "تأكيد", "سيتم استبدال البيانات الحالية. متابعة؟") != QMessageBox.StandardButton.Yes: return
        try:
            xls = pd.ExcelFile(path)
            if 'جهات الاتصال' in xls.sheet_names: 
                self.contacts = pd.read_excel(xls, 'جهات الاتصال').fillna('').to_dict('records')
            if 'المعاملات' in xls.sheet_names:
                df = pd.read_excel(xls, 'المعاملات').fillna('')
                if 'date' in df.columns: 
                    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')
                if 'id' in df.columns:
                    df['id'] = df['id'].astype(str)
                self.ledgers = {name: g.to_dict('records') for name, g in df.groupby('contact')}
            self.update_display()
            QMessageBox.information(self, "نجاح", "تم الاستيراد.")
        except Exception as e: 
            QMessageBox.critical(self, "خطأ", f"فشل الاستيراد: {e}")


class HeaderSettingsDialog(QDialog):
    _system_fonts = {}
    def __init__(self, parent, config):
        super().__init__(parent); self.setWindowTitle("إعدادات التقرير (PDF)"); self.config = json.loads(json.dumps(config))
        if not HeaderSettingsDialog._system_fonts: HeaderSettingsDialog._populate_system_fonts()
        layout = QVBoxLayout(self)
        general_group = QGroupBox("إعدادات الرأس العامة"); general_layout = QGridLayout(general_group)
        general_layout.addWidget(QLabel("نص الرأس (يمين):"), 0, 0); self.header_text_edit = QLineEdit(self.config.get("header_text", "")); general_layout.addWidget(self.header_text_edit, 0, 1)
        general_layout.addWidget(QLabel("نص الرأس (وسط):"), 1, 0); self.center_header_text_edit = QLineEdit(self.config.get("center_header_text", "")); general_layout.addWidget(self.center_header_text_edit, 1, 1)
        general_layout.addWidget(QLabel("الشعار (يسار):"), 2, 0, alignment=Qt.AlignmentFlag.AlignTop)
        self.logo_preview = QLabel("اختر شعار", alignment=Qt.AlignmentFlag.AlignCenter, minimumSize=QSize(100, 100), styleSheet="border: 1px solid grey;"); general_layout.addWidget(self.logo_preview, 2, 1)
        logo_btn_layout = QHBoxLayout(); logo_btn_layout.addWidget(QPushButton("اختر...", clicked=self._select_logo)); logo_btn_layout.addWidget(QPushButton("إزالة", clicked=self._remove_logo)); general_layout.addLayout(logo_btn_layout, 3, 1)
        layout.addWidget(general_group)
        self.header_font_group = self._create_font_group("خط رأس الصفحة", self.config.get("header_font", {}))
        layout.addWidget(self.header_font_group)
        self.body_font_group = self._create_font_group("خط محتوى التقرير", self.config.get("body_font", {}))
        layout.addWidget(self.body_font_group)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, accepted=self.accept, rejected=self.reject); layout.addWidget(buttons)
        self._update_logo_preview()
    def _create_font_group(self, title, font_config):
        group = QGroupBox(title); layout = QGridLayout(group)
        rb_system = QRadioButton("اختيار من خطوط النظام"); rb_file = QRadioButton("اختيار ملف خط")
        combo_system = QComboBox(); combo_system.addItems(["[افتراضي]"] + sorted(HeaderSettingsDialog._system_fonts.keys()))
        file_layout = QHBoxLayout(); edit_file = QLineEdit(readOnly=True)
        btn_file = QPushButton("اختر ملف...", clicked=lambda: self._select_font_file(edit_file))
        file_layout.addWidget(edit_file); file_layout.addWidget(btn_file)
        layout.addWidget(rb_system, 0, 0); layout.addWidget(combo_system, 0, 1); layout.addWidget(rb_file, 1, 0); layout.addLayout(file_layout, 1, 1)
        group.data = {"rb_system": rb_system, "rb_file": rb_file, "combo": combo_system, "edit": edit_file, "btn_file": btn_file}
        rb_system.toggled.connect(lambda checked: self._update_font_ui(group.data, checked))
        method, value = font_config.get("method", "default"), font_config.get("value", "")
        if method == "system": rb_system.setChecked(True); combo_system.setCurrentText(value) if value in HeaderSettingsDialog._system_fonts else None
        else: rb_file.setChecked(True); (edit_file.setText(os.path.basename(value)), edit_file.setToolTip(value)) if method == "file" and value else None
        self._update_font_ui(group.data, rb_system.isChecked()); return group
    def _update_font_ui(self, data, is_system): data["combo"].setEnabled(is_system); data["edit"].setEnabled(not is_system); data["btn_file"].setEnabled(not is_system)
    def _select_font_file(self, edit): path, _ = QFileDialog.getOpenFileName(self, "اختر خط", "", "Font (*.ttf *.otf)"); (edit.setText(os.path.basename(path)), edit.setToolTip(path)) if path else None
    def _select_logo(self): path, _ = QFileDialog.getOpenFileName(self, "اختر صورة", "", "Images (*.png *.jpg)"); self.config["logo_path"] = path if path else ""; self._update_logo_preview()
    def _remove_logo(self): self.config["logo_path"] = ""; self._update_logo_preview()
    def _update_logo_preview(self):
        path = self.config.get("logo_path", "")
        if path and os.path.exists(path): self.logo_preview.setPixmap(QPixmap(path).scaled(self.logo_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else: self.logo_preview.setText("اختر شعار")
    def accept(self):
        self.config["header_text"] = self.header_text_edit.text()
        self.config["center_header_text"] = self.center_header_text_edit.text()
        self.config["header_font"] = self._get_font_config_from_group(self.header_font_group)
        self.config["body_font"] = self._get_font_config_from_group(self.body_font_group)
        super().accept()
    def _get_font_config_from_group(self, group):
        data = group.data
        if data["rb_system"].isChecked():
            value = data["combo"].currentText()
            return {"method": "system" if value != "[افتراضي]" else "default", "value": value if value != "[افتراضي]" else ""}
        path = data["edit"].toolTip(); return {"method": "file" if path else "default", "value": path}
    def get_config(self): return self.config
    @staticmethod
    def _populate_system_fonts():
        if HeaderSettingsDialog._system_fonts: return
        font_dirs = []
        if sys.platform == "win32":
            font_dirs.append(os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts"))
            local_app_data = os.environ.get("LOCALAPPDATA")
            if local_app_data: font_dirs.append(os.path.join(local_app_data, "Microsoft", "Windows", "Fonts"))
        elif sys.platform == "darwin": font_dirs.extend(['/System/Library/Fonts', '/Library/Fonts', os.path.expanduser('~/Library/Fonts')])
        else: font_dirs.extend(['/usr/share/fonts', '/usr/local/share/fonts', os.path.expanduser('~/.fonts'), os.path.expanduser('~/.local/share/fonts')])
        for d in font_dirs:
            if os.path.isdir(d):
                for r, _, files in os.walk(d):
                    for f in files:
                        if f.lower().endswith(('.ttf', '.otf')):
                            path = os.path.join(r, f)
                            try:
                                font = TTFont(None, path)
                                if font.name1 and font.name1 not in HeaderSettingsDialog._system_fonts: HeaderSettingsDialog._system_fonts[font.name1] = path
                            except: pass
    @staticmethod
    def get_system_font_path(name): return HeaderSettingsDialog._system_fonts.get(name)

class ManageContactsDialog(QDialog):
    def __init__(self, parent, contacts, ledgers):
        super().__init__(parent); self.setWindowTitle("إدارة جهات الاتصال"); self.contacts = [c.copy() for c in contacts]; self.ledgers = ledgers
        layout = QVBoxLayout(self); self.list_widget = QListWidget(itemDoubleClicked=self.edit_contact); layout.addWidget(self.list_widget)
        add_frame = QFrame(frameShape=QFrame.Shape.StyledPanel); add_layout = QGridLayout(add_frame)
        self.name_entry = QLineEdit(placeholderText="الاسم الجديد"); self.phone_entry = QLineEdit(placeholderText="الهاتف (اختياري)")
        add_btn = QPushButton("إضافة", clicked=self.add_contact)
        add_layout.addWidget(QLabel("الاسم:"), 0, 0); add_layout.addWidget(self.name_entry, 0, 1); add_layout.addWidget(QLabel("الهاتف:"), 1, 0); add_layout.addWidget(self.phone_entry, 1, 1)
        add_layout.addWidget(add_btn, 0, 2, 2, 1); layout.addWidget(add_frame)
        ctrl_layout = QHBoxLayout(); ctrl_layout.addStretch(); ctrl_layout.addWidget(QPushButton("تعديل", clicked=self.edit_contact)); ctrl_layout.addWidget(QPushButton("حذف", clicked=self.delete_contact))
        layout.addLayout(ctrl_layout); buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, accepted=self.accept, rejected=self.reject); layout.addWidget(buttons)
        self.update_list()
    def update_list(self):
        self.list_widget.clear()
        for c in sorted(self.contacts, key=lambda c: c['name']):
            item = QListWidgetItem(f"{c['name']} ({c.get('phone')})" if c.get('phone') else c['name']); item.setData(Qt.ItemDataRole.UserRole, c['name'])
            self.list_widget.addItem(item)
    def find_contact(self, name): return next((i for i, c in enumerate(self.contacts) if c['name'] == name), None)
    def add_contact(self):
        name = self.name_entry.text().strip()
        if not name: QMessageBox.warning(self, "خطأ", "الاسم مطلوب."); return
        if self.find_contact(name) is not None: QMessageBox.warning(self, "خطأ", "الاسم موجود بالفعل."); return
        self.contacts.append({"name": name, "phone": self.phone_entry.text().strip()}); self.update_list(); self.name_entry.clear(); self.phone_entry.clear()
    def edit_contact(self):
        item = self.list_widget.currentItem(); old_name = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not old_name: return
        idx = self.find_contact(old_name)
        dialog = EditContactDialog(self, self.contacts[idx])
        if dialog.exec():
            new_data = dialog.get_data(); new_name = new_data['name']
            if old_name != new_name and self.find_contact(new_name) is not None: QMessageBox.warning(self, "خطأ", "الاسم مستخدم."); return
            if old_name in self.ledgers: self.ledgers[new_name] = self.ledgers.pop(old_name)
            self.contacts[idx] = new_data; self.update_list()
    def delete_contact(self):
        item = self.list_widget.currentItem(); name = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not name: return
        if QMessageBox.question(self, "تأكيد", f"هل تريد حذف '{name}' وكل معاملاته؟") == QMessageBox.StandardButton.Yes:
            self.contacts = [c for c in self.contacts if c['name'] != name]
            if name in self.ledgers: del self.ledgers[name]
            self.update_list()
    def get_data(self): return self.contacts, self.ledgers
class EditContactDialog(QDialog):
    def __init__(self, parent, data):
        super().__init__(parent); self.setWindowTitle("تعديل")
        layout = QGridLayout(self)
        layout.addWidget(QLabel("الاسم:"), 0, 0); self.name_entry = QLineEdit(data.get("name", "")); layout.addWidget(self.name_entry, 0, 1)
        layout.addWidget(QLabel("الهاتف:"), 1, 0); self.phone_entry = QLineEdit(data.get("phone", "")); layout.addWidget(self.phone_entry, 1, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, accepted=self.accept, rejected=self.reject)
        layout.addWidget(buttons, 2, 0, 1, 2)
    def accept(self):
        if not self.name_entry.text().strip(): QMessageBox.warning(self, "خطأ", "الاسم مطلوب."); return
        super().accept()
    def get_data(self): return {"name": self.name_entry.text().strip(), "phone": self.phone_entry.text().strip()}
class LedgerTransactionDialog(QDialog):
    def __init__(self, parent, contacts, data=None, selected_contact=None):
        super().__init__(parent); self.setWindowTitle("معاملة"); self.data = data or {}
        layout = QGridLayout(self)
        layout.addWidget(QLabel("جهة الاتصال:"), 0, 0)
        self.contact_combo = QComboBox(); self.contact_combo.addItems(sorted([c['name'] for c in contacts]))
        if self.data.get('contact'): self.contact_combo.setCurrentText(self.data.get('contact'))
        elif selected_contact: self.contact_combo.setCurrentText(selected_contact)
        layout.addWidget(self.contact_combo, 0, 1)
        layout.addWidget(QLabel("النوع:"), 1, 0, alignment=Qt.AlignmentFlag.AlignTop)
        tx_vbox = QVBoxLayout()
        self.tx_types = {'loan_from_them': QRadioButton("استلمت (دين عليّ)"), 'loan_to_them': QRadioButton("سلمت (دين لي)"), 'payment_to_them': QRadioButton("سددتُ دفعة"), 'payment_from_them': QRadioButton("استلمتُ دفعة")}
        for rb in self.tx_types.values(): tx_vbox.addWidget(rb)
        layout.addLayout(tx_vbox, 1, 1)
        self.tx_types.get(self.data.get('type', 'loan_from_them'), list(self.tx_types.values())[0]).setChecked(True)
        layout.addWidget(QLabel("المبلغ:"), 2, 0); self.amount_entry = QLineEdit(str(self.data.get('amount', ''))); self.amount_entry.setValidator(QDoubleValidator(0.01, 9999999.99, 2)); layout.addWidget(self.amount_entry, 2, 1)
        layout.addWidget(QLabel("التاريخ:"), 3, 0); self.date_entry = QDateEdit(calendarPopup=True, displayFormat="yyyy-MM-dd"); self.date_entry.setDate(QDate.fromString(self.data.get('date', datetime.now().strftime("%Y-%m-%d")), "yyyy-MM-dd")); layout.addWidget(self.date_entry, 3, 1)
        layout.addWidget(QLabel("البيان:"), 4, 0); self.description_entry = QLineEdit(self.data.get('description', '')); layout.addWidget(self.description_entry, 4, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, accepted=self.accept, rejected=self.reject)
        layout.addWidget(buttons, 5, 0, 1, 2)
    def accept(self):
        if not self.amount_entry.text() or float(self.amount_entry.text()) <= 0: QMessageBox.critical(self, "خطأ", "المبلغ يجب أن يكون موجبًا"); return
        if not self.description_entry.text().strip(): QMessageBox.critical(self, "خطأ", "الوصف مطلوب"); return
        super().accept()
    def get_data(self):
        return {"contact": self.contact_combo.currentText(), "type": next((k for k, rb in self.tx_types.items() if rb.isChecked()), ""), "amount": float(self.amount_entry.text()), "date": self.date_entry.date().toString("yyyy-MM-dd"), "description": self.description_entry.text().strip(), "id": self.data.get('id')}

# --- بداية الجزء المعدل لمنع التشغيل المزدوج ---
# تحديد مسار واسم ملف القفل. يتم إنشاؤه في المجلد المؤقت للنظام
LOCK_FILE_PATH = os.path.join(tempfile.gettempdir(), "accounts_app.lock")

def cleanup_lock_file():
    """وظيفة لحذف ملف القفل عند الخروج من البرنامج."""
    try:
        if os.path.exists(LOCK_FILE_PATH):
            os.remove(LOCK_FILE_PATH)
    except Exception as e:
        print(f"Error cleaning up lock file: {e}")

if __name__ == "__main__":
    # التحقق من وجود نسخة أخرى تعمل
    if os.path.exists(LOCK_FILE_PATH):
        try:
            with open(LOCK_FILE_PATH, "r") as f:
                pid = int(f.read())
            # استخدام psutil للتحقق مما إذا كانت العملية (PID) لا تزال تعمل
            if psutil.pid_exists(pid):
                # إذا كانت تعمل، أظهر رسالة واخرج
                app = QApplication(sys.argv)
                QMessageBox.warning(None, "التطبيق يعمل بالفعل", "برنامج إدارة الديون والقروض يعمل بالفعل.")
                sys.exit(0)
            else:
                # إذا كانت العملية غير موجودة (بقايا من تعطل سابق)، احذف الملف
                os.remove(LOCK_FILE_PATH)
        except (IOError, ValueError):
            # في حالة وجود أي خطأ في قراءة الملف، احذفه
             os.remove(LOCK_FILE_PATH)

    # إذا لم يكن هناك نسخة أخرى، أنشئ ملف القفل
    try:
        with open(LOCK_FILE_PATH, "w") as f:
            f.write(str(os.getpid()))
        # تسجيل وظيفة الحذف ليتم استدعاؤها عند الخروج
        atexit.register(cleanup_lock_file)
    except IOError as e:
        app = QApplication(sys.argv)
        QMessageBox.critical(None, "خطأ فادح", f"فشل في إنشاء ملف القفل: {e}\nالبرنامج سيغلق.")
        sys.exit(1)

    # تشغيل التطبيق كالمعتاد
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setStyle("Fusion")
    window = AccountsApp()
    window.show()
    sys.exit(app.exec())
# --- نهاية الجزء المعدل ---