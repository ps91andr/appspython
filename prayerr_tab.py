import sys
import os
import datetime
import threading
import requests
import pycountry
from win10toast import ToastNotifier
from hijridate import Gregorian

# --- استيراد مكونات PyQt6 ---
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCompleter, QDateEdit, QFrame, QCheckBox,
    QSpinBox, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, QDate, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
# --- تعديل: استيراد QFontDatabase و QFont ---
from PyQt6.QtGui import QIcon, QFontDatabase, QFont


HIJRI_MONTHS_AR = [
    "محرم", "صفر", "ربيع الأول", "ربيع الثاني", "جمادى الأولى", "جمادى الآخرة",
    "رجب", "شعبان", "رمضان", "شوال", "ذو القعدة", "ذو الحجة"
]


class PrayerrTab(QWidget):
    """
    الواجهة الرئيسية لتطبيق مواقيت الصلاة.
    تحتوي على جميع عناصر الواجهة والوظائف المرتبطة بها.
    """
    adhan_should_play_signal = pyqtSignal(str)
    alert_should_play_signal = pyqtSignal(str, int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("تطبيق مواقيت الصلاة")
        self.setGeometry(100, 100, 440, 700)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        # --- المتغيرات ---
        self.api_data = None
        self.scheduled_events = []
        self.current_countdown_event = None
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.sounds_dir = os.path.join(self.base_dir, "pomodoro_sounds")
        self.default_audio_path = os.path.join(self.sounds_dir, "adein.mp3")
        # --- تعديل: اجعل المسار الافتراضي للتنبيه هو نفسه مسار الأذان ---
        self.default_post_adhan_audio_path = self.default_audio_path
        self.audio_file_path = None
        self.post_adhan_audio_path = None

        if not os.path.exists(self.sounds_dir):
            os.makedirs(self.sounds_dir)

        # مشغلات الصوت
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)

        self.post_adhan_media_player = QMediaPlayer(self)
        self.post_adhan_audio_output = QAudioOutput(self)
        self.post_adhan_media_player.setAudioOutput(self.post_adhan_audio_output)

        # مؤقت العداد الزمني في الواجهة
        self.countdown_ui_timer = QTimer(self)
        self.countdown_ui_timer.timeout.connect(self.update_countdown_label)

        # إشعارات Windows Toast
        self.toaster = ToastNotifier()

        # --- ربط الإشارات بالدوال (Slots) الآمنة ---
        self.adhan_should_play_signal.connect(self.handle_play_adhan)
        self.alert_should_play_signal.connect(self.handle_play_alert)

        # --- بناء الواجهة ---
        self.setup_ui()
        self.load_default_audio()
        self.load_default_post_adhan_audio()
        self.update_current_time()
        self.get_prayer_times() # <--- أضف هذا السطر هنا

    def setup_ui(self):
        """إنشاء واجهة المستخدم"""
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(12, 10, 12, 10)
        self.setLayout(layout)

        # تنسيق الواجهة
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #d0d0d0; }
            QFrame { border: 1px solid #444; border-radius: 8px; padding: 8px; background-color: #2a2a2a; }
            QLabel#group_label { color: #55aaff; font-weight: bold; border: none; padding: 0; background-color: transparent; }
            QLabel#countdown_label {
                background-color: #2c3e50; color: #ecf0f1; font-size: 16px; font-weight: bold;
                border-radius: 8px; padding: 10px; text-align: center;
            }
            QPushButton { 
                background-color: #3e3e3e; border: 1px solid #555; padding: 6px 12px; border-radius: 5px; 
            }
            QPushButton:hover { background-color: #4f4f4f; }
            QPushButton:pressed { background-color: #2a2a2a; }
            QLineEdit, QComboBox, QDateEdit, QSpinBox {
                padding: 5px; border: 1px solid #555; border-radius: 5px; background-color: #333;
            }
            QCheckBox { background-color: transparent; }
        """)

        # --- السطر العلوي: الوقت الحالي ---
        self.time_label = QLabel("")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.update_current_time)
        self.time_timer.start(1000)

        # --- السطر الثاني: إدخال المدينة، الدولة، التاريخ، تحديد الموقع ---
        row1_layout = QHBoxLayout()
        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("المدينة")
        self.city_input.setText("Sanaa")  # <--- هذا السطر

        self.country_combo = QComboBox()
        self.country_combo.setEditable(True)
        self.country_combo.setPlaceholderText("الدولة")
        self.country_combo.setCurrentText("Yemen") # <--- وهذا السطر

        self.country_list = sorted([country.name for country in pycountry.countries])
        self.country_combo.addItems(self.country_list)
        completer = QCompleter(self.country_list)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.country_combo.setCompleter(completer)

        self.locate_button = QPushButton("📍")
        self.locate_button.setFixedSize(45, 34)

        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setStyleSheet("QDateEdit::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 20px; }")


        row1_layout.addWidget(self.city_input, 3)
        row1_layout.addWidget(self.country_combo, 3)
        row1_layout.addWidget(self.locate_button)
        row1_layout.addWidget(self.date_input, 3)
        layout.addLayout(row1_layout)

        # --- مجموعة إعدادات صوت الأذان ---
        # --- مجموعة إعدادات صوت الأذان ---
        adhan_group = QFrame()
        adhan_layout = QVBoxLayout(adhan_group)
        adhan_layout.setSpacing(6)
        adhan_layout.addWidget(QLabel("إعدادات صوت الأذان", objectName="group_label"))

        # إنشاء تخطيط أفقي واحد لوضع جميع العناصر بجانب بعضها
        controls_layout = QHBoxLayout()

        # إنشاء جميع الأزرار ومربع الاختيار
        self.choose_sound_btn = QPushButton("🔊 اختر ملف صوت الأذان")
        self.choose_sound_btn.setToolTip("اختر ملف صوت الأذان") # إضافة تلميح

        self.reset_sound_btn = QPushButton("🔄استعادة الصوت الافتراضي")
        self.reset_sound_btn.setToolTip("استعادة الصوت الافتراضي") # إضافة تلميح

        self.test_sound_btn = QPushButton("▶️تجربة صوت الأذان")
        self.test_sound_btn.setToolTip("تجربة صوت الأذان") # إضافة تلميح

        self.stop_adhan_btn = QPushButton("⏹️إيقاف صوت الأذان")
        self.stop_adhan_btn.setToolTip("إيقاف صوت الأذان") # إضافة تلميح
        self.stop_adhan_btn.setStyleSheet("color: #e74c3c;")
        self.stop_adhan_btn.clicked.connect(self.stop_adhan_audio)

        self.sound_checkbox = QCheckBox("تشغيل صوت الأذان")
        self.sound_checkbox.setChecked(True)
        
        # إضافة مربع الاختيار أولاً في السطر
        controls_layout.addWidget(self.sound_checkbox)
        controls_layout.addStretch() # إضافة فاصل مرن

        # إضافة الأزرار بجانب بعضها
        controls_layout.addWidget(self.choose_sound_btn)
        controls_layout.addWidget(self.reset_sound_btn)
        controls_layout.addWidget(self.test_sound_btn)
        controls_layout.addWidget(self.stop_adhan_btn)

        # إضافة التخطيط الأفقي الذي يحتوي على كل شيء إلى الواجهة
        adhan_layout.addLayout(controls_layout)

        # عرض مسار الملف المختار
        self.audio_file_label = QLabel("...")
        self.audio_file_label.setWordWrap(True)
        self.audio_file_label.setStyleSheet("background-color: transparent;")
        adhan_layout.addWidget(self.audio_file_label)
        layout.addWidget(adhan_group)
        
        
        # --- مجموعة تنبيه بعد الأذان ---
        post_adhan_group = QFrame()
        post_adhan_layout = QVBoxLayout(post_adhan_group)
        post_adhan_layout.setSpacing(6)
        
        # تخطيط أفقي واحد لوضع جميع عناصر التحكم بجانب بعضها
        post_adhan_controls_layout = QHBoxLayout()

        # إنشاء وإضافة العناصر إلى التخطيط الأفقي
        self.post_adhan_checkbox = QCheckBox("تفعيل التنبيه")
        self.post_adhan_checkbox.setObjectName("group_label") # استخدام نفس التنسيق للعنوان
        post_adhan_controls_layout.addWidget(self.post_adhan_checkbox)

        # --- تعديل: سنجعل العنوان متغيرًا في الكلاس ليتم تحديثه ---
        # --- تعديل: سنجعل العنوان متغيرًا في الكلاس ليتم تحديثه ---
        self.reminder_text_label = QLabel("قبل (دقائق):")
        post_adhan_controls_layout.addWidget(self.reminder_text_label)

        self.post_adhan_delay_input = QSpinBox()
        self.post_adhan_delay_input.setRange(-120, 120)
        self.post_adhan_delay_input.setValue(-15)
        self.post_adhan_delay_input.setStyleSheet("QLineEdit { text-align: right; }")
        
        # --- تعديل: ربط تغيير القيمة في المربع بالدالة التي أنشأناها ---
        self.post_adhan_delay_input.valueChanged.connect(self.update_reminder_label)
        
        # --- هذا هو السطر بعد تصحيحه ---
        post_adhan_controls_layout.addWidget(self.post_adhan_delay_input)
        
        self.choose_post_adhan_sound_btn = QPushButton("🔊اختر صوت")
        self.choose_post_adhan_sound_btn.setToolTip("اختر ملف صوت التنبيه")
        post_adhan_controls_layout.addWidget(self.choose_post_adhan_sound_btn)

        self.test_post_adhan_sound_btn = QPushButton("▶️تجربة")
        self.test_post_adhan_sound_btn.setToolTip("تجربة صوت التنبيه")
        post_adhan_controls_layout.addWidget(self.test_post_adhan_sound_btn)
        
        self.stop_post_adhan_btn = QPushButton("⏹️إيقاف صوت")
        self.stop_post_adhan_btn.setToolTip("إيقاف صوت التنبيه الحالي")
        self.stop_post_adhan_btn.setStyleSheet("color: #e74c3c;")
        self.stop_post_adhan_btn.clicked.connect(self.stop_post_adhan_audio)
        post_adhan_controls_layout.addWidget(self.stop_post_adhan_btn)

        # إضافة التخطيط الأفقي الممتلئ بالعناصر إلى الواجهة
        post_adhan_layout.addLayout(post_adhan_controls_layout)

        # هذا الجزء يبقى كما هو لعرض مسار الملف
        self.post_adhan_audio_label = QLabel("...")
        self.post_adhan_audio_label.setWordWrap(True)
        self.post_adhan_audio_label.setStyleSheet("background-color: transparent;")
        post_adhan_layout.addWidget(self.post_adhan_audio_label)
        layout.addWidget(post_adhan_group)

        # --- زر جلب المواقيت ---
        self.get_button = QPushButton("📥 جلب المواقيت")
        self.get_button.setStyleSheet("background-color:#0078d7; color:white; font-weight:bold; padding:12px;")
        layout.addWidget(self.get_button)

        # --- العداد الزمني ---
        self.countdown_label = QLabel("اضغط على 'جلب المواقيت' لبدء العداد", objectName="countdown_label")
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.countdown_label)

        # --- عرض مواقيت الصلاة ---
        self.result_label = QLabel("")
        self.result_label.setObjectName("result_label")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.result_label, 1)

        # --- ربط الأحداث ---
        self.locate_button.clicked.connect(self.detect_location)
        self.choose_sound_btn.clicked.connect(self.select_audio_file)
        self.reset_sound_btn.clicked.connect(self.load_default_audio)
        self.test_sound_btn.clicked.connect(self.test_audio)
        self.choose_post_adhan_sound_btn.clicked.connect(self.select_post_adhan_audio_file)
        self.test_post_adhan_sound_btn.clicked.connect(self.test_post_adhan_audio)
        self.get_button.clicked.connect(self.get_prayer_times)
        self.post_adhan_checkbox.stateChanged.connect(self.update_prayer_times_display)
        self.post_adhan_delay_input.valueChanged.connect(self.update_prayer_times_display)

    def get_prayer_times(self):
        city = self.city_input.text().strip()
        country = self.country_combo.currentText().strip()
        if not city or not country:
            QMessageBox.warning(self, "بيانات ناقصة", "يرجى إدخال المدينة والدولة.")
            return

        try:
            url = "http://api.aladhan.com/v1/timingsByCity"
            selected_date = self.date_input.date().toPyDate()
            params = {
                "city": city, "country": country, "method": 2,
                "date": selected_date.strftime("%d-%m-%Y")
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data["code"] == 200:
                self.api_data = data["data"]
                self.update_prayer_times_display()
                self.schedule_all_events(self.api_data["timings"], selected_date)
            else:
                QMessageBox.critical(self, "خطأ من الخادم", f"فشل: {data.get('data', 'خطأ غير معروف')}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "خطأ في الشبكة", f"فشل الاتصال بالخادم: {e}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ غير متوقع: {e}")

    def schedule_all_events(self, timings, selected_date):
        self.scheduled_events.clear()
        self.current_countdown_event = None
        now = datetime.datetime.now()

        prayer_names_ar = {
            "Fajr": "الفجر", "Dhuhr": "الظهر", "Asr": "العصر",
            "Maghrib": "المغرب", "Isha": "العشاء"
        }

        for prayer_en, time_str in timings.items():
            if prayer_en not in prayer_names_ar: continue

            try:
                prayer_ar = prayer_names_ar[prayer_en]
                h, m = map(int, time_str.split(":"))
                adhan_time = datetime.datetime.combine(selected_date, datetime.time(h, m))

                if adhan_time > now and self.sound_checkbox.isChecked():
                    delay = (adhan_time - now).total_seconds()
                    threading.Timer(delay, self.trigger_adhan_signal, args=[prayer_ar]).start()
                    self.scheduled_events.append({"time": adhan_time, "prayer": prayer_ar, "type": "الأذان"})

                if self.post_adhan_checkbox.isChecked():
                    delay_minutes = self.post_adhan_delay_input.value()
                    alert_time = adhan_time + datetime.timedelta(minutes=delay_minutes)
                    if alert_time > now:
                        delay = (alert_time - now).total_seconds()
                        threading.Timer(delay, self.trigger_alert_signal, args=[prayer_ar, delay_minutes]).start()
                        alert_type = "تنبيه قبل" if delay_minutes < 0 else "تنبيه بعد"
                        self.scheduled_events.append({
                            "time": alert_time, "prayer": prayer_ar, "type": alert_type
                        })
            except Exception as e:
                print(f"ERROR scheduling {prayer_en}: {e}")

        self.scheduled_events.sort(key=lambda x: x["time"])
        self.update_countdown_target()
        self.countdown_ui_timer.start(1000)
        self.update_countdown_label()

    def trigger_adhan_signal(self, prayer_name):
        self.adhan_should_play_signal.emit(prayer_name)

    def trigger_alert_signal(self, prayer_name, delay_minutes):
        self.alert_should_play_signal.emit(prayer_name, delay_minutes)

    def handle_play_adhan(self, prayer_name):
        if self.sound_checkbox.isChecked() and self.audio_file_path and os.path.exists(self.audio_file_path):
            self.media_player.setSource(QUrl.fromLocalFile(self.audio_file_path))
            self.media_player.play()

        self.toaster.show_toast(
            title="🎵 وقت الأذان", msg=f"حان الآن موعد صلاة {prayer_name}.",
            duration=15, threaded=True, icon_path=None
        )
        self.update_countdown_target()

    def handle_play_alert(self, prayer_name, delay_minutes):
        if self.post_adhan_checkbox.isChecked() and self.post_adhan_audio_path and os.path.exists(self.post_adhan_audio_path):
            self.post_adhan_media_player.setSource(QUrl.fromLocalFile(self.post_adhan_audio_path))
            self.post_adhan_media_player.play()

        if delay_minutes > 0:
            msg = f"مضى {delay_minutes} دقيقة على أذان {prayer_name}."
            title = "⏰ تنبيه بعد الصلاة"
        elif delay_minutes < 0:
            msg = f"تبقى {abs(delay_minutes)} دقيقة على أذان {prayer_name}."
            title = "⏰ تنبيه قبل الصلاة"
        else:
            msg = f"موعد أذان {prayer_name} الآن."
            title = "⏰ تنبيه في وقت الصلاة"

        self.toaster.show_toast(
            title=title, msg=msg, duration=15, threaded=True, icon_path=None
        )
        self.update_countdown_target()

    def update_countdown_target(self):
        now = datetime.datetime.now()
        self.scheduled_events = [e for e in self.scheduled_events if e["time"] > now]
        self.current_countdown_event = self.scheduled_events[0] if self.scheduled_events else None

    def update_countdown_label(self):
        if not self.current_countdown_event:
            self.countdown_label.setText("لا توجد مواقيت أو تنبيهات قادمة لهذا اليوم")
            self.countdown_ui_timer.stop()
            return

        now = datetime.datetime.now()
        event_time = self.current_countdown_event["time"]
        if now >= event_time:
            self.update_countdown_target()
            if self.current_countdown_event: self.update_countdown_label()
            return

        time_diff = event_time - now
        total_seconds = int(time_diff.total_seconds())
        h, rem = divmod(total_seconds, 3600)
        m, s = divmod(rem, 60)

        event_type = self.current_countdown_event["type"]
        prayer_name = self.current_countdown_event["prayer"]
        countdown_text = (
            f"الوقت المتبقي على <b>{event_type} {prayer_name}</b>: "
            f"<span style='font-family:Consolas,monospace; color:#f1c40f;'>{h:02}:{m:02}:{s:02}</span>"
        )
        self.countdown_label.setText(countdown_text)

    def update_reminder_label(self, value):
        """تحديث نص العنوان (قبل/بعد) بناءً على قيمة الدقائق."""
        if value > 0:
            self.reminder_text_label.setText("بعد (دقائق):")
        elif value < 0:
            self.reminder_text_label.setText("قبل (دقائق):")
        else:
            # في حال كانت القيمة صفر
            self.reminder_text_label.setText("مع (دقائق):")

    def update_prayer_times_display(self):
        if not self.api_data: return
        html = self.format_prayer_times_html(
            self.post_adhan_checkbox.isChecked(),
            self.post_adhan_delay_input.value()
        )
        self.result_label.setText(html)

    def format_prayer_times_html(self, show_reminder, delay_minutes):
        timings = self.api_data["timings"]
        date_info = self.api_data["date"]["readable"]
        hijri_date_info = self.api_data["date"]["hijri"]["date"]
        city = self.city_input.text()
        country = self.country_combo.currentText()

        output = f"""
        <div style="background-color:#2a2a2a; border:1px solid #444; border-radius:8px; padding:15px; font-family:'Segoe UI',Arial,sans-serif;">
            <h3 style="color:#55aaff; text-align:center;">مواقيت الصلاة في {city}, {country}</h3>
            <p style="text-align:center; font-size:12px; color:#b0b0b0;">{date_info} | {hijri_date_info}</p>
            <table width="100%" border="0" cellspacing="5" style="font-size:14px; border-collapse:collapse;">
                <thead><tr style="text-align:right; color:#a0d8ff;">
                    <th style="padding:8px;">الصلاة</th><th style="padding:8px;">وقت الأذان</th>
                    {('<th style="padding:8px;">وقت التنبيه</th>' if show_reminder else '')}
                </tr></thead><tbody>
        """
        prayer_order = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]
        prayer_names_ar = {
            "Fajr": "الفجر", "Sunrise": "الشروق", "Dhuhr": "الظهر",
            "Asr": "العصر", "Maghrib": "المغرب", "Isha": "العشاء"
        }
        for prayer in prayer_order:
            if prayer not in timings: continue
            time_24h = timings[prayer]
            prayer_ar = prayer_names_ar[prayer]
            output += f'<tr style="border-top:1px solid #3a3a3a;">' \
                      f'<td style="padding:8px; color:#e0e0e0; font-weight:bold;">{prayer_ar}</td>' \
                      f'<td style="padding:8px; color:#87cefa; text-align:right; font-family:\'Consolas\',monospace;">{time_24h}</td>'
            if show_reminder and prayer != "Sunrise":
                try:
                    prayer_dt_obj = datetime.datetime.strptime(time_24h, "%H:%M")
                    reminder_dt_obj = prayer_dt_obj + datetime.timedelta(minutes=delay_minutes)
                    reminder_time_str = reminder_dt_obj.strftime("%H:%M")
                    sign = "قبل" if delay_minutes < 0 else "بعد"
                    title = f"تنبيه {abs(delay_minutes)} دقيقة {sign}"
                    output += f"<td style='padding:8px; color:#f9c86b; text-align:right; font-family:Consolas,monospace;' title='{title}'>{reminder_time_str}</td>"
                except Exception:
                    output += "<td style='padding:8px; text-align:right;'>-</td>"
            elif show_reminder:
                output += "<td style='padding:8px; text-align:right;'>-</td>"
            output += "</tr>"
        output += "</tbody></table></div>"
        return output

    def load_default_audio(self):
        if os.path.exists(self.default_audio_path):
            self.audio_file_path = self.default_audio_path
            self.audio_file_label.setText("✅ الصوت الافتراضي للأذان: adein.mp3")
        else:
            self.audio_file_path = None
            self.audio_file_label.setText("⚠️ لم يتم العثور على ملف الأذان الافتراضي (adein.mp3).")

    def load_default_post_adhan_audio(self):
        if os.path.exists(self.default_post_adhan_audio_path):
            self.post_adhan_audio_path = self.default_post_adhan_audio_path
            self.post_adhan_audio_label.setText("✅ الصوت الافتراضي للتنبيه: adein.mp3")
        else:
            self.post_adhan_audio_path = None
            self.post_adhan_audio_label.setText("⚠️ لم يتم العثور على ملف التنبيه الافتراضي (adein.mp3).")

    def select_audio_file(self):
        fp, _ = QFileDialog.getOpenFileName(self, "اختر ملف صوت للأذان", "", "ملفات صوت (*.mp3 *.wav)")
        if fp:
            self.audio_file_path = fp
            self.audio_file_label.setText(f"📁 ملف الأذان: {os.path.basename(fp)}")

    def select_post_adhan_audio_file(self):
        fp, _ = QFileDialog.getOpenFileName(self, "اختر ملف صوت للتنبيه", "", "ملفات صوت (*.mp3 *.wav)")
        if fp:
            self.post_adhan_audio_path = fp
            self.post_adhan_audio_label.setText(f"📁 ملف التنبيه: {os.path.basename(fp)}")

    def test_audio(self):
        if self.audio_file_path and os.path.exists(self.audio_file_path):
            self.media_player.setSource(QUrl.fromLocalFile(self.audio_file_path))
            self.media_player.play()
        else:
            QMessageBox.warning(self, "تحذير", "لم يتم تحديد ملف صوتي للأذان.")

    def test_post_adhan_audio(self):
        if self.post_adhan_audio_path and os.path.exists(self.post_adhan_audio_path):
            self.post_adhan_media_player.setSource(QUrl.fromLocalFile(self.post_adhan_audio_path))
            self.post_adhan_media_player.play()
        else:
            QMessageBox.warning(self, "تحذير", "لم يتم تحديد ملف صوتي للتنبيه.")

    def stop_adhan_audio(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.stop()

    def stop_post_adhan_audio(self):
        if self.post_adhan_media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.post_adhan_media_player.stop()

    def detect_location(self):
        try:
            r = requests.get("https://ipapi.co/json/")
            r.raise_for_status()
            d = r.json()
            city, country_name = d.get("city"), d.get("country_name")
            if city and country_name:
                self.city_input.setText(city)
                matched_country = self.match_country(country_name)
                if matched_country:
                    index = self.country_combo.findText(matched_country, Qt.MatchFlag.MatchFixedString)
                    if index >= 0: self.country_combo.setCurrentIndex(index)
                    else: self.country_combo.setCurrentText(country_name)
                else: self.country_combo.setCurrentText(country_name)
            else:
                QMessageBox.warning(self, "خطأ", "تعذر تحديد الموقع تلقائيًا.")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "خطأ في الشبكة", f"فشل في تحديد الموقع: {e}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل في تحديد الموقع: {e}")

    def match_country(self, name):
        try: return pycountry.countries.get(name=name).name
        except AttributeError:
            try: return pycountry.countries.search_fuzzy(name)[0].name
            except LookupError: return None

    def update_current_time(self):
        now = datetime.datetime.now()
        days_ar = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
        months_gregorian_ar = [
            "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
            "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
        ]
        
        try:
            hijri_date = Gregorian(now.year, now.month, now.day).to_hijri()
            hijri_month_name = HIJRI_MONTHS_AR[hijri_date.month - 1]
            hijri_str = f"<b style='color:#d8b8ff;'>{hijri_date.day} {hijri_month_name} {hijri_date.year} هـ</b>"
        except Exception:
            hijri_str = ""

        time_text = (
            f"<b style='color:#a0d8ff;'>{now.strftime('%I:%M:%S %p')}</b> | "
            f"{days_ar[now.weekday()]}, {now.day} {months_gregorian_ar[now.month - 1]} {now.year} م | "
            f"{hijri_str}"
        )
        self.time_label.setText(time_text)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 1. إنشاء كائن خط باسم الخط المثبت على النظام
    cairo_font = QFont("Cairo", 10) # يمكنك تغيير حجم الخط (10) حسب الرغبة

    # 2. تعيين هذا الخط كخط افتراضي للتطبيق بأكمله
    app.setFont(cairo_font)

    # 3. إنشاء وعرض النافذة الرئيسية
    main_window = PrayerrTab()
    main_window.show()
    sys.exit(app.exec())