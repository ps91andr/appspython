import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QSpinBox, QGroupBox
)
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import Qt

class CodeEditorTab(QMainWindow):
    """
    فئة تمثل نافذة محرر الأكواد مع وظائف متقدمة لتنسيق النص والتحكم فيه.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("محرر الأكواد مع إضافة المسافات")
        self.setGeometry(100, 100, 1100, 700)

        self.init_ui()

    def init_ui(self):
        """
        تقوم هذه الدالة بإعداد واجهة المستخدم وترتيب العناصر.
        """
        main_layout = QGridLayout()

        # --- منطقة النص ---
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("اكتب كودك هنا...")
        main_layout.addWidget(self.text_edit, 0, 0, 1, 4)

        # --- SpinBox لعدد المسافات ---
        self.space_count_label = QLabel("عدد المسافات:")
        self.space_count_spinbox = QSpinBox()
        self.space_count_spinbox.setRange(0, 20)
        self.space_count_spinbox.setValue(4)

        space_layout = QHBoxLayout()
        space_layout.addWidget(self.space_count_label)
        space_layout.addWidget(self.space_count_spinbox)
        main_layout.addLayout(space_layout, 1, 0, 1, 4)

        # --- قسم المسافات ---
        indent_group = QGroupBox("المسافات")
        indent_layout = QHBoxLayout()

        self.indent_button = QPushButton("إضافة مسافات لكل النص")
        self.remove_indent_button = QPushButton("إزالة مسافات من كل النص")
        self.indent_selected_button = QPushButton("إضافة مسافات للأسطر المحددة")
        self.remove_indent_selected_button = QPushButton("إزالة مسافات من الأسطر المحددة")
        self.indent_current_line_button = QPushButton("إضافة مسافات للسطر الحالي")
        self.remove_indent_current_line_button = QPushButton("إزالة مسافات من السطر الحالي")

        indent_layout.addWidget(self.indent_button)
        indent_layout.addWidget(self.remove_indent_button)
        indent_layout.addWidget(self.indent_selected_button)
        indent_layout.addWidget(self.remove_indent_selected_button)
        indent_layout.addWidget(self.indent_current_line_button)
        indent_layout.addWidget(self.remove_indent_current_line_button)

        indent_group.setLayout(indent_layout)
        main_layout.addWidget(indent_group, 2, 0, 1, 4)

        # --- قسم التعليقات ---
        comment_group = QGroupBox("التعليقات")
        comment_layout = QHBoxLayout()

        self.comment_selected_button = QPushButton("إضافة تعليق للأسطر المحددة")
        self.uncomment_selected_button = QPushButton("إزالة تعليق من الأسطر المحددة")
        self.comment_current_line_button = QPushButton("إضافة تعليق للسطر الحالي")
        self.uncomment_current_line_button = QPushButton("إزالة تعليق من السطر الحالي")

        comment_layout.addWidget(self.comment_selected_button)
        comment_layout.addWidget(self.uncomment_selected_button)
        comment_layout.addWidget(self.comment_current_line_button)
        comment_layout.addWidget(self.uncomment_current_line_button)

        comment_group.setLayout(comment_layout)
        main_layout.addWidget(comment_group, 3, 0, 1, 4)

        # --- قسم التحرير (مع تحديد أماكن محددة لكل زر) ---
        edit_group = QGroupBox("الأدوات")
        edit_grid = QGridLayout()

        self.select_all_button = QPushButton("تحديد الكل")
        self.copy_button = QPushButton("نسخ")
        self.paste_button = QPushButton("لصق هنا")
        self.paste_above_button = QPushButton("لصق فوق النص المحدد")
        self.paste_only_button = QPushButton("لصق فقط")
        self.clear_selection_button = QPushButton("مسح محدد")
        self.clear_all_button = QPushButton("مسح الكل")
        self.select_and_copy_button = QPushButton("تحديد الكل ثم نسخ")
        self.clear_and_paste_button = QPushButton("مسح الكل ثم لصق")
        self.refresh_button = QPushButton("تجديد الكل")

        edit_grid.addWidget(self.select_all_button, 0, 0)
        edit_grid.addWidget(self.copy_button, 0, 1)
        edit_grid.addWidget(self.paste_button, 0, 2)
        edit_grid.addWidget(self.refresh_button, 0, 3)

        edit_grid.addWidget(self.paste_above_button, 1, 0)
        edit_grid.addWidget(self.paste_only_button, 1, 1)
        edit_grid.addWidget(self.clear_selection_button, 1, 2)
        edit_grid.addWidget(self.clear_all_button, 1, 3)

        edit_grid.addWidget(self.select_and_copy_button, 2, 0)
        edit_grid.addWidget(self.clear_and_paste_button, 2, 1)

        edit_group.setLayout(edit_grid)
        main_layout.addWidget(edit_group, 4, 0, 1, 4)

        # --- إعداد النافذة الرئيسية ---
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.setup_connections()

    def setup_connections(self):
        """
        تقوم هذه الدالة بربط الأزرار بالدوال الخاصة بها.
        """
        # --- المسافات ---
        self.indent_button.clicked.connect(self.add_indent)
        self.remove_indent_button.clicked.connect(self.remove_indent)
        self.indent_selected_button.clicked.connect(self.add_indent_to_selected_lines)
        self.remove_indent_selected_button.clicked.connect(self.remove_indent_from_selected_lines)
        self.indent_current_line_button.clicked.connect(self.add_indent_to_current_line)
        self.remove_indent_current_line_button.clicked.connect(self.remove_indent_from_current_line)

        # --- التعليقات ---
        self.comment_selected_button.clicked.connect(self.comment_selected_lines)
        self.uncomment_selected_button.clicked.connect(self.uncomment_selected_lines)
        self.comment_current_line_button.clicked.connect(self.comment_current_line)
        self.uncomment_current_line_button.clicked.connect(self.uncomment_current_line)

        # --- التحرير ---
        self.refresh_button.clicked.connect(self.refresh_text)
        self.select_all_button.clicked.connect(self.select_all_text)
        self.copy_button.clicked.connect(self.copy_text)
        self.paste_button.clicked.connect(self.paste_text)
        self.paste_above_button.clicked.connect(self.paste_above_text)
        self.paste_only_button.clicked.connect(self.paste_only_text)
        self.clear_selection_button.clicked.connect(self.clear_selection)
        self.clear_all_button.clicked.connect(self.clear_all)
        self.select_and_copy_button.clicked.connect(self.select_and_copy)
        self.clear_and_paste_button.clicked.connect(self.clear_and_paste)

    # === الدوال التنفيذية ===

    def add_indent(self):
        """إضافة مسافات بادئة لجميع أسطر النص."""
        text = self.text_edit.toPlainText()
        spaces = self.space_count_spinbox.value()
        if text.strip():
            indented_text = "\n".join(" " * spaces + line for line in text.splitlines())
            self.text_edit.setPlainText(indented_text)

    def remove_indent(self):
        """إزالة المسافات البادئة من جميع أسطر النص."""
        text = self.text_edit.toPlainText()
        spaces = self.space_count_spinbox.value()
        if text.strip():
            unindented_text = "\n".join(line[spaces:] if line.startswith(" " * spaces) else line for line in text.splitlines())
            self.text_edit.setPlainText(unindented_text)

    def add_indent_to_selected_lines(self):
        """إضافة مسافات بادئة للأسطر المحددة فقط."""
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            return

        start_pos = cursor.selectionStart()
        selected_text = cursor.selectedText()
        lines = selected_text.splitlines()
        spaces = self.space_count_spinbox.value()

        # إذا كان التحديد لا ينتهي بسطر جديد، تجاهل السطر الأخير لتجنب إضافة مسافة له
        if not selected_text.endswith('\n') and len(lines) > 1:
            last_line = lines.pop()
            indented_lines = [" " * spaces + line for line in lines]
            new_text = "\n".join(indented_lines) + "\n" + last_line
        else:
            indented_lines = [" " * spaces + line for line in lines]
            new_text = "\n".join(indented_lines)
            
        cursor.insertText(new_text)
        # إعادة تحديد النص بعد التعديل
        cursor.setPosition(start_pos)
        cursor.setPosition(start_pos + len(new_text), QTextCursor.MoveMode.KeepAnchor)
        self.text_edit.setTextCursor(cursor)

    def remove_indent_from_selected_lines(self):
        """إزالة المسافات البادئة من الأسطر المحددة."""
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            return

        start_pos = cursor.selectionStart()
        selected_text = cursor.selectedText()
        lines = selected_text.splitlines()
        spaces = self.space_count_spinbox.value()
        space_str = " " * spaces

        unindented_lines = [line[len(space_str):] if line.startswith(space_str) else line for line in lines]
        new_text = "\n".join(unindented_lines)

        cursor.insertText(new_text)
        cursor.setPosition(start_pos)
        cursor.setPosition(start_pos + len(new_text), QTextCursor.MoveMode.KeepAnchor)
        self.text_edit.setTextCursor(cursor)


    def comment_selected_lines(self):
        """إضافة علامة التعليق '#' للأسطر المحددة."""
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            return

        start_pos = cursor.selectionStart()
        selected_text = cursor.selectedText()
        lines = selected_text.splitlines()

        commented_lines = ["# " + line if line.strip() else "#" for line in lines]
        new_text = "\n".join(commented_lines)

        cursor.insertText(new_text)
        cursor.setPosition(start_pos)
        cursor.setPosition(start_pos + len(new_text), QTextCursor.MoveMode.KeepAnchor)
        self.text_edit.setTextCursor(cursor)


    def uncomment_selected_lines(self):
        """إزالة علامة التعليق '#' من الأسطر المحددة."""
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            return

        start_pos = cursor.selectionStart()
        selected_text = cursor.selectedText()
        lines = selected_text.splitlines()

        uncommented_lines = [line[2:] if line.startswith("# ") else (line[1:] if line.startswith("#") else line) for line in lines]
        new_text = "\n".join(uncommented_lines)

        cursor.insertText(new_text)
        cursor.setPosition(start_pos)
        cursor.setPosition(start_pos + len(new_text), QTextCursor.MoveMode.KeepAnchor)
        self.text_edit.setTextCursor(cursor)


    def comment_current_line(self):
        """إضافة تعليق للسطر الحالي."""
        cursor = self.text_edit.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.insertText("# ")
        cursor.endEditBlock()
        self.text_edit.setTextCursor(cursor)

    def uncomment_current_line(self):
        """إزالة التعليق من السطر الحالي."""
        cursor = self.text_edit.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 2)
        if cursor.selectedText() == "# ":
            cursor.removeSelectedText()
        else:
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 1)
            if cursor.selectedText() == "#":
                cursor.removeSelectedText()
        cursor.endEditBlock()
        self.text_edit.setTextCursor(cursor)


    def add_indent_to_current_line(self):
        """إضافة مسافة بادئة للسطر الحالي."""
        cursor = self.text_edit.textCursor()
        spaces = self.space_count_spinbox.value()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.insertText(" " * spaces)
        cursor.endEditBlock()

    def remove_indent_from_current_line(self):
        """إزالة مسافة بادئة من السطر الحالي."""
        cursor = self.text_edit.textCursor()
        spaces = self.space_count_spinbox.value()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        for _ in range(spaces):
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 1)
        if cursor.selectedText() == " " * spaces:
            cursor.removeSelectedText()
        else:
            # إذا لم يكن هناك عدد كافٍ من المسافات، قم بإلغاء التحديد
            cursor.clearSelection()
        cursor.endEditBlock()

    def refresh_text(self):
        """مسح كل النص."""
        self.text_edit.clear()

    def select_all_text(self):
        """تحديد كل النص."""
        self.text_edit.selectAll()

    def copy_text(self):
        """نسخ النص المحدد."""
        self.text_edit.copy()

    def paste_text(self):
        """لصق النص من الحافظة."""
        self.text_edit.paste()

    def paste_above_text(self):
        """لصق النص فوق النص المحدد."""
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            clipboard = QApplication.clipboard()
            clipboard_text = clipboard.text()
            start_pos = cursor.selectionStart()
            cursor.setPosition(start_pos)
            cursor.insertText(clipboard_text + "\n")

    def paste_only_text(self):
        """لصق النص فقط (دون استبدال)."""
        self.text_edit.paste()

    def clear_selection(self):
        """مسح النص المحدد فقط."""
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            cursor.removeSelectedText()

    def clear_all(self):
        """مسح كل النص في المحرر."""
        self.text_edit.clear()

    def select_and_copy(self):
        """تحديد الكل ثم النسخ."""
        self.text_edit.selectAll()
        self.text_edit.copy()

    def clear_and_paste(self):
        """مسح كل النص ثم اللصق."""
        self.text_edit.clear()
        self.text_edit.paste()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    editor = CodeEditorTab()
    editor.show()
    sys.exit(app.exec())