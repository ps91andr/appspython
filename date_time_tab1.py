# START OF FILE date_time_tab.py

import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                             QLabel, QHBoxLayout, QFrame, QCalendarWidget,
                             QSpinBox, QComboBox, QScrollArea)
from PyQt6.QtCore import QTimer, QDateTime, Qt, QDate
from PyQt6.QtGui import QFont, QFontDatabase

# حاول استيراد المكتبة، إذا لم تكن موجودة، استمر بدونها
try:
    from hijridate import Hijri, Gregorian
except ImportError:
    print("Warning: 'hijridate' library not found. Hijri conversion will not work.")
    Hijri = Gregorian = None

class DateTimeApp(QWidget): # <--- (تم التغيير هنا من QMainWindow إلى QWidget)
    def __init__(self):
        super().__init__()
        # لم نعد بحاجة لـ setWindowTitle أو setGeometry هنا

        # --- تحقق من توفر المكتبة ---
        if Hijri is None:
            self.setup_error_ui("مكتبة 'hijridate' غير مثبتة. يرجى تثبيتها باستخدام: pip install hijridate")
            return

        # --- تحميل خط Cairo المخصص ---
        try:
            QFontDatabase.addApplicationFont("Cairo-Regular.ttf")
        except Exception as e:
            print(f"لم يتم العثور على ملف الخط 'Cairo-Regular.ttf': {e}")

        self.hijri_months_list = [
            "1. محرم", "2. صفر", "3. ربيع الأول", "4. ربيع الثاني", "5. جمادى الأولى",
            "6. جمادى الآخرة", "7. رجب", "8. شعبان", "9. رمضان", "10. شوال",
            "11. ذو القعدة", "12. ذو الحجة"
        ]

        # --- تعريف كائنات خط Cairo بأحجام مختلفة ---
        self.font_main_title = QFont("Cairo", 28, QFont.Weight.Bold)
        self.font_subtitle = QFont("Cairo", 20, QFont.Weight.Bold)
        self.font_clock = QFont("Cairo", 46, QFont.Weight.Bold)
        self.font_date_header = QFont("Cairo", 22, QFont.Weight.Bold)
        self.font_date_body = QFont("Cairo", 18, QFont.Weight.Bold)
        self.font_regular_small = QFont("Cairo", 12)
        self.font_regular_medium = QFont("Cairo", 14)
        self.font_result = QFont("Cairo", 16, QFont.Weight.Bold)
        self.font_input = QFont("Cairo", 12, QFont.Weight.Bold)

        self.initUI()
        self.connect_signals_and_set_defaults()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_live_time)
        self.timer.start(1000)
        self.update_all_displays()

    def setup_error_ui(self, message):
        """
        واجهة بسيطة لعرض رسالة الخطأ إذا كانت المكتبة غير موجودة
        """
        layout = QVBoxLayout(self)
        error_label = QLabel(message)
        error_label.setFont(QFont("Arial", 16))
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setWordWrap(True)
        layout.addWidget(error_label)
        self.setLayout(layout)

    def initUI(self):
        # <--- (تم التغيير هنا: استخدام layout مباشر بدلاً من setCentralWidget)
        outer_layout = QVBoxLayout(self)
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True); scroll_area.setObjectName("scrollArea");
        outer_layout.addWidget(scroll_area)
        outer_layout.setContentsMargins(0,0,0,0)


        content_widget = QWidget(); content_widget.setObjectName("mainWidget"); scroll_area.setWidget(content_widget)
        main_layout = QVBoxLayout(content_widget); main_layout.setContentsMargins(30, 30, 30, 30); main_layout.setSpacing(15)

        # القسم 1: الوقت والتاريخ الحي
        title1 = QLabel("الوقت والتاريخ الحالي"); title1.setFont(self.font_main_title); title1.setObjectName("titleLabel"); main_layout.addWidget(title1)
        time_box, self.time_12_label, self.time_24_label = self.create_time_display(); main_layout.addLayout(time_box)
        main_layout.addWidget(self.create_separator())
        date_grid = QHBoxLayout(); date_grid.setSpacing(20); g_box, self.day_en_label, self.g_month_ar, self.g_month_en, self.g_date_label = self.create_date_box("dEn", "gMAr", "gMEn", "gDate"); h_box, self.day_ar_label, self.h_month_ar, self.h_month_en, self.h_date_label = self.create_date_box("dAr", "hMAr", "hMEn", "hDate"); date_grid.addLayout(g_box); date_grid.addLayout(h_box); main_layout.addLayout(date_grid)

        # الأقسام الأخرى
        main_layout.addWidget(self.create_separator()); self.setup_gregorian_to_hijri_converter(main_layout)
        main_layout.addWidget(self.create_separator()); self.setup_hijri_to_gregorian_converter(main_layout)
        main_layout.addWidget(self.create_separator()); self.setup_gregorian_age_calculator(main_layout)
        main_layout.addWidget(self.create_separator()); self.setup_hijri_age_calculator(main_layout)
        main_layout.addStretch()
        self.setStyleSheet(self.get_stylesheet())

    def setup_gregorian_to_hijri_converter(self, layout):
        title = QLabel("تحويل من ميلادي إلى هجري"); title.setFont(self.font_subtitle); title.setObjectName("converterTitle"); layout.addWidget(title)
        self.calendar = QCalendarWidget(); self.calendar.setObjectName("calendarWidget"); self.calendar.setFont(self.font_regular_medium); layout.addWidget(self.calendar)
        self.hijri_result_label = QLabel(); self.hijri_result_label.setFont(self.font_result); self.hijri_result_label.setObjectName("resultLabel"); layout.addWidget(self.hijri_result_label)

    def setup_hijri_to_gregorian_converter(self, layout):
        title = QLabel("تحويل من هجري إلى ميلادي"); title.setFont(self.font_subtitle); title.setObjectName("converterTitle"); layout.addWidget(title)
        hijri_input_layout, self.h_day_input, self.h_month_combo, self.h_year_input = self.create_hijri_spinboxes(); layout.addLayout(hijri_input_layout)
        self.gregorian_result_label = QLabel(); self.gregorian_result_label.setFont(self.font_result); self.gregorian_result_label.setObjectName("resultLabel"); layout.addWidget(self.gregorian_result_label)
        
    def setup_gregorian_age_calculator(self, layout):
        title = QLabel("حاسبة العمر بالميلادي"); title.setFont(self.font_subtitle); title.setObjectName("converterTitle"); layout.addWidget(title)
        age_calc_layout = QHBoxLayout(); dob_layout = QVBoxLayout(); dob_label = QLabel("تاريخ الميلاد (يوم/شهر/سنة)"); dob_label.setFont(self.font_regular_medium); dob_label.setAlignment(Qt.AlignmentFlag.AlignCenter); dob_spinboxes, self.dob_day, self.dob_month, self.dob_year = self.create_gregorian_spinboxes(); dob_layout.addWidget(dob_label); dob_layout.addLayout(dob_spinboxes); end_date_layout = QVBoxLayout(); end_date_label = QLabel("تاريخ حساب العمر (يوم/شهر/سنة)"); end_date_label.setFont(self.font_regular_medium); end_date_label.setAlignment(Qt.AlignmentFlag.AlignCenter); end_date_spinboxes, self.end_day, self.end_month, self.end_year = self.create_gregorian_spinboxes(); end_date_layout.addWidget(end_date_label); end_date_layout.addLayout(end_date_spinboxes); age_calc_layout.addLayout(dob_layout); age_calc_layout.addLayout(end_date_layout); layout.addLayout(age_calc_layout)
        self.age_result_label = QLabel(); self.age_result_label.setFont(self.font_result); self.age_result_label.setObjectName("resultLabel"); layout.addWidget(self.age_result_label)

    def setup_hijri_age_calculator(self, layout):
        title = QLabel("حاسبة العمر بالهجري"); title.setFont(self.font_subtitle); title.setObjectName("converterTitle"); layout.addWidget(title)
        hijri_age_layout = QHBoxLayout(); h_dob_layout = QVBoxLayout(); h_dob_label = QLabel("تاريخ الميلاد الهجري"); h_dob_label.setFont(self.font_regular_medium); h_dob_label.setAlignment(Qt.AlignmentFlag.AlignCenter); h_dob_spinboxes, self.h_dob_day, self.h_dob_month, self.h_dob_year = self.create_hijri_spinboxes(); h_dob_layout.addWidget(h_dob_label); h_dob_layout.addLayout(h_dob_spinboxes); h_end_layout = QVBoxLayout(); h_end_label = QLabel("تاريخ حساب العمر الهجري"); h_end_label.setFont(self.font_regular_medium); h_end_label.setAlignment(Qt.AlignmentFlag.AlignCenter); h_end_spinboxes, self.h_end_day, self.h_end_month, self.h_end_year = self.create_hijri_spinboxes(); h_end_layout.addWidget(h_end_label); h_end_layout.addLayout(h_end_spinboxes)
        hijri_age_layout.addLayout(h_dob_layout); hijri_age_layout.addLayout(h_end_layout); layout.addLayout(hijri_age_layout)
        self.hijri_age_result_label = QLabel(); self.hijri_age_result_label.setFont(self.font_result); self.hijri_age_result_label.setObjectName("resultLabel"); layout.addWidget(self.hijri_age_result_label)
        
    def connect_signals_and_set_defaults(self):
        self.calendar.selectionChanged.connect(self.convert_selected_date)
        for spinbox in [self.dob_day, self.dob_month, self.dob_year, self.end_day, self.end_month, self.end_year]:
            spinbox.valueChanged.connect(self.calculate_age)
        self.h_day_input.valueChanged.connect(self.convert_hijri_to_gregorian)
        self.h_month_combo.currentIndexChanged.connect(self.convert_hijri_to_gregorian)
        self.h_year_input.valueChanged.connect(self.convert_hijri_to_gregorian)
        for widget in [self.h_dob_day, self.h_dob_month, self.h_dob_year, self.h_end_day, self.h_end_month, self.h_end_year]:
            if isinstance(widget, QSpinBox): widget.valueChanged.connect(self.calculate_hijri_age)
            else: widget.currentIndexChanged.connect(self.calculate_hijri_age)
        self.dob_year.setValue(2000)
        current_g_date = QDate.currentDate()
        self.end_day.setValue(current_g_date.day()); self.end_month.setValue(current_g_date.month()); self.end_year.setValue(current_g_date.year())
        self.h_year_input.setValue(1447); self.h_dob_year.setValue(1420)
        current_h_date = Gregorian(current_g_date.year(), current_g_date.month(), current_g_date.day()).to_hijri()
        self.h_end_day.setValue(current_h_date.day); self.h_end_month.setCurrentIndex(current_h_date.month - 1); self.h_end_year.setValue(current_h_date.year)

    def update_all_displays(self):
        self.update_live_time()
        self.convert_selected_date()
        self.convert_hijri_to_gregorian()
        self.calculate_age()
        self.calculate_hijri_age()

    def create_separator(self):
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setObjectName("separator"); return sep

    def create_time_display(self):
        layout = QVBoxLayout(); layout.setSpacing(0); time12 = QLabel(); time12.setFont(self.font_clock); time12.setObjectName("timeLabel"); time12.setAlignment(Qt.AlignmentFlag.AlignCenter); time24 = QLabel(); time24.setFont(self.font_regular_medium); time24.setObjectName("timeLabel24"); time24.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(time12); layout.addWidget(time24); return layout, time12, time24

    def create_gregorian_spinboxes(self):
        layout=QHBoxLayout();layout.setSpacing(10);day=QSpinBox();day.setRange(1,31);day.setFont(self.font_input);day.setObjectName("hijriInput");month=QSpinBox();month.setRange(1,12);month.setFont(self.font_input);month.setObjectName("hijriInput");year=QSpinBox();year.setRange(1900,2100);year.setFont(self.font_input);year.setObjectName("hijriInput");layout.addWidget(day);layout.addWidget(month);layout.addWidget(year);return layout,day,month,year

    def create_hijri_spinboxes(self):
        layout = QHBoxLayout(); layout.setSpacing(10); day = QSpinBox(); day.setRange(1, 30); day.setFont(self.font_input); day.setObjectName("hijriInput"); month = QComboBox(); month.addItems(self.hijri_months_list); month.setFont(self.font_input); month.setObjectName("hijriInput"); year = QSpinBox(); year.setRange(1300, 1600); year.setFont(self.font_input); year.setObjectName("hijriInput"); layout.addWidget(day, 1); layout.addWidget(month, 2); layout.addWidget(year, 1); return layout, day, month, year
    
    def create_date_box(self, d, mar, men, dt):
        b=QVBoxLayout();b.setSpacing(10);dl=QLabel();dl.setFont(self.font_date_header);dl.setObjectName(d);dl.setAlignment(Qt.AlignmentFlag.AlignCenter);ml=QHBoxLayout();ma=QLabel();ma.setFont(self.font_regular_small);ma.setObjectName(mar);ma.setAlignment(Qt.AlignmentFlag.AlignCenter);me=QLabel();me.setFont(self.font_regular_small);me.setObjectName(men);me.setAlignment(Qt.AlignmentFlag.AlignCenter);ml.addWidget(me);ml.addWidget(ma);dtl=QLabel();dtl.setFont(self.font_date_body);dtl.setObjectName(dt);dtl.setAlignment(Qt.AlignmentFlag.AlignCenter);b.addWidget(dl);b.addLayout(ml);b.addWidget(dtl);return b,dl,ma,me,dtl

    def calculate_age(self):
        try:
            start_date = QDate(self.dob_year.value(), self.dob_month.value(), self.dob_day.value())
            end_date = QDate(self.end_year.value(), self.end_month.value(), self.end_day.value())
            if not start_date.isValid() or not end_date.isValid():
                self.age_result_label.setText("تاريخ غير صالح، يرجى التأكد من الأرقام.")
                return
        except Exception:
            self.age_result_label.setText("خطأ في بناء التاريخ، يرجى التأكد.")
            return

        if start_date > end_date:
            self.age_result_label.setText("تاريخ الميلاد يجب أن يكون قبل تاريخ الحساب")
            return

        years = end_date.year() - start_date.year()
        months = end_date.month() - start_date.month()
        days = end_date.day() - start_date.day()

        if days < 0:
            months -= 1
            days += start_date.daysInMonth()
        if months < 0:
            years -= 1
            months += 12
        
        self.age_result_label.setText(f"العمر الميلادي: {years} سنوات، و {months} أشهر، و {days} أيام")

    def calculate_hijri_age(self):
        try:
            start_y, start_m, start_d = self.h_dob_year.value(), self.h_dob_month.currentIndex() + 1, self.h_dob_day.value()
            end_y, end_m, end_d = self.h_end_year.value(), self.h_end_month.currentIndex() + 1, self.h_end_day.value()
            start_date = Hijri(start_y, start_m, start_d)
            end_date = Hijri(end_y, end_m, end_d)
        except (ValueError, OverflowError):
            self.hijri_age_result_label.setText("تاريخ هجري غير صالح. يرجى التأكد من الأرقام.")
            return
            
        if start_date > end_date:
            self.hijri_age_result_label.setText("تاريخ الميلاد الهجري يجب أن يكون قبل تاريخ الحساب")
            return

        years = end_y - start_y
        months = end_m - start_m
        days = end_d - start_d

        if days < 0:
            months -= 1
            days += start_date.month_length()
        if months < 0:
            years -= 1
            months += 12
        
        self.hijri_age_result_label.setText(f"العمر الهجري: {years} سنوات، و {months} أشهر، و {days} أيام")

    def convert_hijri_to_gregorian(self):
        try:
            y, m, d = self.h_year_input.value(), self.h_month_combo.currentIndex() + 1, self.h_day_input.value()
            if m == 12 and d > 29 and not Hijri(y, m, d).is_leap_year():
                raise ValueError("Day is out of range for this month")
            g = Hijri(y, m, d).to_gregorian()
            gdn = self.get_arabic_day_name(g.weekday() + 1)
            gmn = self.get_arabic_gregorian_month_name(g.month)
            self.gregorian_result_label.setText(f"يوافق: يوم {gdn}، {g.day} {gmn} {g.year} م")
        except (ValueError, OverflowError):
            self.gregorian_result_label.setText("تاريخ هجري غير صالح.")

    def update_live_time(self):
        ct = QDateTime.currentDateTime()
        cd = ct.date()
        self.time_12_label.setText(ct.toString("h:mm:ss AP"))
        self.time_24_label.setText(ct.toString("HH:mm:ss"))
        self.day_en_label.setText(ct.toString("dddd"))
        self.g_month_en.setText(ct.toString("MMMM"))
        self.g_month_ar.setText(self.get_arabic_gregorian_month_name(cd.month()))
        self.g_date_label.setText(ct.toString("yyyy/MM/dd"))
        try:
            g = Gregorian(cd.year(), cd.month(), cd.day())
            h = g.to_hijri()
            self.day_ar_label.setText(self.get_arabic_day_name(cd.dayOfWeek()))
            self.h_month_en.setText(self.get_english_hijri_month_name(h.month))
            self.h_month_ar.setText(self.get_arabic_hijri_month_name(h.month))
            self.h_date_label.setText(f"{h.year}/{h.month:02d}/{h.day:02d} هـ")
        except Exception:
            self.h_date_label.setText("خطأ في التحويل")

    def convert_selected_date(self):
        sd = self.calendar.selectedDate()
        y, m, d = sd.year(), sd.month(), sd.day()
        try:
            h = Gregorian(y, m, d).to_hijri()
            hmn = self.get_arabic_hijri_month_name(h.month)
            self.hijri_result_label.setText(f"يوافق: {h.day} {hmn} {h.year} هـ")
        except Exception:
            self.hijri_result_label.setText("لا يمكن تحويل هذا التاريخ")

    def get_stylesheet(self):
        return """
            #mainWidget { background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(45, 52, 54, 255), stop:1 rgba(99, 110, 114, 255)); }
            #scrollArea { border: none; }
            QLabel { color: #ffffff; }
            #titleLabel { color: #ffffff; text-shadow: 2px 2px 4px #1e272e;}
            #converterTitle { color: #f1c40f; text-align: center; }
            #timeLabel { color: #ffffff; } 
            #timeLabel24 { color: #bdc3c7; }
            .separator { background-color: #7f8c8d; height: 2px; }
            #dEn, #dAr { color: #f1c40f; }
            #gDate, #hDate { color: #ffffff; letter-spacing: 2px; }
            #resultLabel { color: #ffffff; padding: 5px; min-height: 25px; text-align: center; }
            #calendarWidget { border: none; }
            #calendarWidget QToolButton { color: white; background-color: transparent; }
            #calendarWidget QToolButton:hover { background-color: #7f8c8d; }
            #calendarWidget QWidget#qt_calendar_navigationbar { background-color: #2d3436; }
            #calendarWidget QAbstractItemView:enabled { color: #ffffff; background-color: #636e72; selection-background-color: #f1c40f; selection-color: #000000; }
            #hijriInput, QComboBox { background-color: #636e72; color: white; border: 1px solid #7f8c8d; border-radius: 5px; padding: 10px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: #2d3436; color: white; selection-background-color: #f1c40f; }
            QScrollBar:vertical { border: none; background: #2d3436; width: 14px; margin: 0px; }
            QScrollBar::handle:vertical { background: #7f8c8d; min-height: 20px; border-radius: 7px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """
    def get_arabic_day_name(self, dow): return {1:"الاثنين",2:"الثلاثاء",3:"الأربعاء",4:"الخميس",5:"الجمعة",6:"السبت",7:"الأحد"}.get(dow,"")
    def get_arabic_gregorian_month_name(self, m): return {1:"يناير",2:"فبراير",3:"مارس",4:"أبريل",5:"مايو",6:"يونيو",7:"يوليو",8:"أغسطس",9:"سبتمبر",10:"أكتوبر",11:"نوفمبر",12:"ديسمبر"}.get(m,"")
    def get_arabic_hijri_month_name(self, m): return self.hijri_months_list[m-1].split(". ")[1] if 1<=m<=12 else ""
    def get_english_hijri_month_name(self, m): return {1:"Muharram",2:"Safar",3:"Rabi' al-awwal",4:"Rabi' al-thani",5:"Jumada al-awwal",6:"Jumada al-thani",7:"Rajab",8:"Sha'ban",9:"Ramadan",10:"Shawwal",11:"Dhu al-Qi'dah",12:"Dhu al-Hijjah"}.get(m,"")

# الكود التالي لتشغيل النافذة بشكل مستقل (للتجربة فقط)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DateTimeApp()
    window.show()
    sys.exit(app.exec())
# END OF FILE date_time_tab.py