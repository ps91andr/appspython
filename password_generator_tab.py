import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpinBox, QCheckBox
from PyQt6.QtCore import Qt
import random
import string
import re
from PyQt6.QtGui import QGuiApplication

class PasswordGenerator(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("مولد كلمات المرور")
        self.setGeometry(100, 100, 400, 400)
        
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # عنصر إدخال طول كلمة المرور
        length_layout = QHBoxLayout()
        self.length_spinbox = QSpinBox()
        self.length_spinbox.setRange(8, 32)
        self.length_spinbox.setValue(12)
        length_label = QLabel("طول كلمة المرور:")
        length_layout.addWidget(length_label)
        length_layout.addStretch()
        length_layout.addWidget(self.length_spinbox)
        
        # خيارات تخصيص كلمة المرور
        options_layout = QVBoxLayout()
        self.uppercase_checkbox = QCheckBox("الحروف الكبيرة")
        self.lowercase_checkbox = QCheckBox("الحروف الصغيرة")
        self.numbers_checkbox = QCheckBox("الأرقام")
        self.special_checkbox = QCheckBox("الرموز الخاصة")
        
        # تعيين الخيارات افتراضياً
        self.uppercase_checkbox.setChecked(True)
        self.lowercase_checkbox.setChecked(True)
        self.numbers_checkbox.setChecked(True)
        self.special_checkbox.setChecked(True)
        
        options_layout.addWidget(self.uppercase_checkbox)
        options_layout.addWidget(self.lowercase_checkbox)
        options_layout.addWidget(self.numbers_checkbox)
        options_layout.addWidget(self.special_checkbox)
        
        # زر التوليد وعرض النتيجة
        generate_button = QPushButton("توليد كلمة مرور")
        generate_button.clicked.connect(self.generate_password)
        
        self.password_display = QLabel("")
        self.strength_display = QLabel("")
        self.strength_bar = QLabel()
        
        # زر النسخ
        copy_button = QPushButton("نسخ")
        copy_button.clicked.connect(self.copy_password)
        
        # ترتيب العناصر
        self.layout.addLayout(length_layout)
        self.layout.addLayout(options_layout)
        self.layout.addWidget(generate_button)
        self.layout.addWidget(self.password_display)
        self.layout.addWidget(copy_button)
        self.layout.addWidget(self.strength_display)
        self.layout.addWidget(self.strength_bar)
        self.layout.addStretch()

    def calculate_strength(self, password):
        # حساب طول كلمة المرور
        length = len(password)
        
        # حساب أنواع الأحرف
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_numbers = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password))
        
        # حساب النمط
        repeated = len(password) - len(set(password))
        sequences = self._check_sequences(password)
        
        # حساب القوة الإجمالية
        strength = 0.0
        
        # طول كلمة المرور
        if length >= 12:
            strength += 0.25
        elif length >= 8:
            strength += 0.15
            
        # أنواع الأحرف
        if has_upper and has_lower:
            strength += 0.15
        if has_numbers:
            strength += 0.15
        if has_special:
            strength += 0.15
            
        # خصائص إضافية
        if repeated == 0:
            strength += 0.15
        if not sequences:
            strength += 0.15
            
        # تقييد القوة بين 0 و 1
        strength = max(0.0, min(1.0, strength))
        
        return strength

    def _check_sequences(self, password):
        # التحقق من التسلسلات الشائعة
        sequences = ['123', 'abc', 'qwe', 'asd', 'zxc']
        for seq in sequences:
            if seq in password.lower():
                return True
        return False

    def generate_password(self):
        length = self.length_spinbox.value()
        characters = ""
        
        if self.uppercase_checkbox.isChecked():
            characters += string.ascii_uppercase
        if self.lowercase_checkbox.isChecked():
            characters += string.ascii_lowercase
        if self.numbers_checkbox.isChecked():
            characters += string.digits
        if self.special_checkbox.isChecked():
            characters += "!@#$%^&*()_+-=[]{}|;:,.<>?"
            
        # التأكد من وجود على الأقل حرف واحد من كل نوع تم اختياره
        password = []
        if self.uppercase_checkbox.isChecked():
            password.append(random.choice(string.ascii_uppercase))
        if self.lowercase_checkbox.isChecked():
            password.append(random.choice(string.ascii_lowercase))
        if self.numbers_checkbox.isChecked():
            password.append(random.choice(string.digits))
        if self.special_checkbox.isChecked():
            password.append(random.choice("!@#$%^&*()_+-=[]{}|;:,.<>?"))
            
        # ملء البقية بشكل عشوائي
        for _ in range(length - len(password)):
            password.append(random.choice(characters))
            
        # خلط كلمة المرور
        random.shuffle(password)
        
        password = "".join(password)
        strength = self.calculate_strength(password)
        
        self.password_display.setText(f"كلمة المرور: {password}")
        
        # عرض مستوى القوة
        if strength < 0.33:
            strength_text = "ضعيف جداً"
            color = "red"
        elif strength < 0.66:
            strength_text = "متوسط"
            color = "orange"
        else:
            strength_text = "قوي"
            color = "green"
            
        self.strength_display.setText(f"قوة كلمة المرور: {strength_text} ({strength:.2f})")
        self.strength_bar.setStyleSheet(f"background-color: {color}; height: 10px;")
    
    def copy_password(self):
        # استخراج كلمة المرور من النص المعروض
        password_text = self.password_display.text()
        if password_text.startswith("كلمة المرور: "):
            password = password_text[13:]  # إزالة النص الثابت
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(password)
            self.password_display.setText("كلمة المرور: " + password + " (تم النسخ!)")
        else:
            self.password_display.setText("لا يوجد كلمة مرور لنسخها")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PasswordGenerator()
    window.show()
    sys.exit(app.exec())