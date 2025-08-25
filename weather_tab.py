import sys
import requests
import geocoder
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QHBoxLayout, 
                             QMessageBox, QFormLayout, QComboBox, QProgressDialog,
                             QTabWidget, QToolButton, QMainWindow)
from PyQt6.QtGui import QPalette, QColor, QPixmap, QIcon, QDesktopServices
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QUrl

class CityLoader(QThread):
    progress_updated = pyqtSignal(int)
    cities_loaded = pyqtSignal(dict)

    def run(self):
        try:
            cities_data = [
                {"name": "Riyadh", "name_ar": "الرياض", "country": "السعودية"},
                {"name": "Jeddah", "name_ar": "جدة", "country": "السعودية"},
                {"name": "Dubai", "name_ar": "دبي", "country": "الإمارات"},
                {"name": "Cairo", "name_ar": "القاهرة", "country": "مصر"},
                {"name": "Alexandria", "name_ar": "الإسكندرية", "country": "مصر"},
                {"name": "Amman", "name_ar": "عمّان", "country": "الأردن"},
                {"name": "Beirut", "name_ar": "بيروت", "country": "لبنان"},
                {"name": "Doha", "name_ar": "الدوحة", "country": "قطر"},
                {"name": "Khartoum", "name_ar": "الخرطوم", "country": "السودان"},
                {"name": "Rabat", "name_ar": "الرباط", "country": "المغرب"},
                {"name": "Tunis", "name_ar": "تونس", "country": "تونس"},
                {"name": "Algiers", "name_ar": "الجزائر", "country": "الجزائر"},
                {"name": "Baghdad", "name_ar": "بغداد", "country": "العراق"},
                {"name": "Istanbul", "name_ar": "إسطنبول", "country": "تركيا"},
                {"name": "Ankara", "name_ar": "أنقرة", "country": "تركيا"},
                {"name": "Manama", "name_ar": "المنامة", "country": "البحرين"},
                {"name": "Kuwait City", "name_ar": "مدينة الكويت", "country": "الكويت"},
                {"name": "Muscat", "name_ar": "مسقط", "country": "عمان"},
                {"name": "Abu Dhabi", "name_ar": "أبوظبي", "country": "الإمارات"},
                {"name": "Sana'a", "name_ar": "صنعاء", "country": "اليمن"},
                {"name": "Damascus", "name_ar": "دمشق", "country": "سوريا"},
                {"name": "Nicosia", "name_ar": "نيقوسيا", "country": "قبرص"},
                {"name": "Tbilisi", "name_ar": "تبليسي", "country": "جورجيا"},
                {"name": "Yerevan", "name_ar": "يريفان", "country": "أرمينيا"},
                {"name": "Baku", "name_ar": "باكو", "country": "أذربيجان"},
                {"name": "Ashgabat", "name_ar": "عشق آباد", "country": "تركمانستان"},
                {"name": "Jerusalem", "name_ar": "القدس", "country": "فلسطين"},
                {"name": "Lagos", "name_ar": "لاغوس", "country": "نيجيريا"},
                {"name": "Nairobi", "name_ar": "نيروبي", "country": "كينيا"},
                {"name": "Addis Ababa", "name_ar": "أديس أبابا", "country": "إثيوبيا"},
                {"name": "Accra", "name_ar": "أكرا", "country": "غانا"},
                {"name": "Kampala", "name_ar": "كامبالا", "country": "أوغندا"},
                {"name": "Dar es Salaam", "name_ar": "دار السلام", "country": "تنزانيا"},
                {"name": "Kinshasa", "name_ar": "كينشاسا", "country": "الكونغو"},
                {"name": "Maputo", "name_ar": "مابوتو", "country": "موزمبيق"},
                {"name": "Douala", "name_ar": "دوالا", "country": "الكاميرون"},
                {"name": "Lomé", "name_ar": "لومي", "country": "توغو"},
                {"name": "Yaoundé", "name_ar": "ياوندي", "country": "الكاميرون"},
                {"name": "New York", "name_ar": "نيويورك", "country": "الولايات المتحدة"},
                {"name": "Los Angeles", "name_ar": "لوس أنجلوس", "country": "الولايات المتحدة"},
                {"name": "Chicago", "name_ar": "شيكاغو", "country": "الولايات المتحدة"},
                {"name": "Toronto", "name_ar": "تورونتو", "country": "كندا"},
                {"name": "Mexico City", "name_ar": "مدينة المكسيك", "country": "المكسيك"},
                {"name": "São Paulo", "name_ar": "ساو باولو", "country": "البرازيل"},
                {"name": "Buenos Aires", "name_ar": "بوينس آيرس", "country": "الأرجنتين"},
                {"name": "Tokyo", "name_ar": "طوكيو", "country": "اليابان"},
                {"name": "Beijing", "name_ar": "بكين", "country": "الصين"},
                {"name": "Seoul", "name_ar": "سيول", "country": "كوريا الجنوبية"},
                {"name": "Bangkok", "name_ar": "بانكوك", "country": "تايلاند"},
                {"name": "Mumbai", "name_ar": "مومباي", "country": "الهند"},
                {"name": "Jakarta", "name_ar": "جاكرتا", "country": "إندونيسيا"},
                {"name": "Kuala Lumpur", "name_ar": "كوالالمبور", "country": "ماليزيا"},
                {"name": "Hanoi", "name_ar": "هانوي", "country": "فيتنام"},
                {"name": "Manila", "name_ar": "مانيلا", "country": "الفلبين"},
                {"name": "Moscow", "name_ar": "موسكو", "country": "روسيا"},
                {"name": "Berlin", "name_ar": "برلين", "country": "ألمانيا"},
                {"name": "London", "name_ar": "لندن", "country": "بريطانيا"},
                {"name": "Paris", "name_ar": "باريس", "country": "فرنسا"},
                {"name": "Rome", "name_ar": "روما", "country": "إيطاليا"},
                {"name": "Madrid", "name_ar": "مدريد", "country": "إسبانيا"},
                {"name": "Athens", "name_ar": "أثينا", "country": "اليونان"},
                {"name": "Stockholm", "name_ar": "ستوكهولم", "country": "السويد"},
                {"name": "Vienna", "name_ar": "فيينا", "country": "النمسا"},
                {"name": "Prague", "name_ar": "براغ", "country": "التشيك"},
                {"name": "Budapest", "name_ar": "بودابست", "country": "المجر"}
            ]
            
            cities = {}
            total = len(cities_data)
            for i, city in enumerate(cities_data):
                display_name = f"{city['name_ar']} - {city['country']}"
                cities[display_name] = city['name']
                self.progress_updated.emit(int((i+1)/total*100))
            
            self.cities_loaded.emit(cities)
        except Exception as e:
            print(f"Error loading cities: {str(e)}")

class LocationFinder(QThread):
    location_found = pyqtSignal(str)
    location_error = pyqtSignal(str)

    def run(self):
        try:
            g = geocoder.ip('me')
            if g.ok and g.city:
                self.location_found.emit(g.city)
            else:
                self.location_error.emit("تعذر تحديد الموقع. قد تكون خدمة تحديد الموقع غير متاحة.")
        except Exception as e:
            self.location_error.emit(f"حدث خطأ أثناء الاتصال بخدمة تحديد الموقع: {e}")

class WeatherTab(QWidget): 
    def __init__(self):
        super().__init__()
        
        self.api_key = "73a7da62c69726c037a79640216011a1"
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
        self.forecast_url = "http://api.openweathermap.org/data/2.5/forecast"
        self.cities = {}
        
        self.setup_dark_theme()
        self.init_ui()
        self.load_cities()
        
    def setup_dark_theme(self):
        self.setStyleSheet("""
            WeatherTab { 
                background-color: #353535;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
            }
            QLineEdit, QComboBox {
                background-color: #232323;
                color: #FFFFFF;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                min-height: 25px;
            }
            QComboBox QAbstractItemView {
                background-color: #353535;
                color: white;
                selection-background-color: #2A82DA;
            }
            QPushButton, QToolButton {
                background-color: #2A82DA;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover, QToolButton:hover {
                background-color: #3A92EA;
            }
            QGroupBox {
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2A82DA;
                width: 10px;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #353535;
                color: white;
                padding: 8px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #2A82DA;
            }
        """)
    
    def init_ui(self):
        layout = QVBoxLayout(self) 
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.weather_tab = QWidget()
        self.setup_weather_tab()
        self.tabs.addTab(self.weather_tab, "حالة الطقس")
        
        self.settings_tab = QWidget()
        self.setup_settings_tab()
        self.tabs.addTab(self.settings_tab, "الإعدادات")
    
    def setup_weather_tab(self):
        tab_layout = QVBoxLayout()
        self.weather_tab.setLayout(tab_layout)
        
        title = QLabel("أداة التحقق من الطقس")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2A82DA; margin-bottom: 20px;")
        tab_layout.addWidget(title)
        
        method_layout = QHBoxLayout()
        method_label = QLabel("طريقة البحث:")
        self.search_method = QComboBox()
        self.search_method.addItems(["ابحث في جميع المدن", "ادخل اسم المدينة يدوياً"])
        self.search_method.currentIndexChanged.connect(self.toggle_search_method)
        method_layout.addWidget(method_label)
        method_layout.addWidget(self.search_method)
        tab_layout.addLayout(method_layout)
        
        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("أدخل اسم المدينة...")
        self.city_input.setVisible(False)
        tab_layout.addWidget(self.city_input)
        
        search_layout = QHBoxLayout()
        self.city_search = QLineEdit()
        self.city_search.setPlaceholderText("ابحث عن مدينة...")
        self.city_search.textChanged.connect(self.filter_cities)
        
        self.city_combo = QComboBox()
        self.city_combo.setEditable(True)
        self.city_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        
        search_layout.addWidget(self.city_search, 1)
        search_layout.addWidget(self.city_combo, 2)

        self.location_btn = QToolButton()
        self.location_btn.setText("موقعي الحالي")
        self.location_btn.setIcon(QIcon.fromTheme("find-location"))
        self.location_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.location_btn.clicked.connect(self.find_my_location)
        search_layout.addWidget(self.location_btn)
        
        tab_layout.addLayout(search_layout)
        
        self.search_btn = QPushButton("الحصول على بيانات الطقس")
        self.search_btn.setIcon(QIcon.fromTheme("edit-find"))
        self.search_btn.setIconSize(QSize(16, 16))
        self.search_btn.clicked.connect(self.get_weather)
        tab_layout.addWidget(self.search_btn)
        
        self.weather_group = QWidget()
        self.weather_group.setVisible(False)
        weather_layout = QFormLayout()
        self.weather_group.setLayout(weather_layout)
        
        self.city_name_label = QLabel()
        self.city_name_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        weather_layout.addRow("المدينة:", self.city_name_label)
        
        self.country_label = QLabel()
        weather_layout.addRow("الدولة:", self.country_label)
        
        self.weather_icon = QLabel()
        self.weather_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        weather_layout.addRow("الحالة الجوية:", self.weather_icon)
        
        self.temp_label = QLabel()
        weather_layout.addRow("درجة الحرارة:", self.temp_label)
        
        self.feels_like_label = QLabel()
        weather_layout.addRow("الشعور الحقيقي:", self.feels_like_label)
        
        self.humidity_label = QLabel()
        weather_layout.addRow("الرطوبة:", self.humidity_label)
        
        self.wind_label = QLabel()
        weather_layout.addRow("سرعة الرياح:", self.wind_label)
        
        self.pressure_label = QLabel()
        weather_layout.addRow("الضغط الجوي:", self.pressure_label)
        
        self.past_rain_label = QLabel()
        weather_layout.addRow("الأمطار (آخر 3 ساعات):", self.past_rain_label)
        
        self.future_rain_label = QLabel()
        weather_layout.addRow("توقعات الأمطار:", self.future_rain_label)
        
        tab_layout.addWidget(self.weather_group)
        
        tab_layout.addStretch()
    
    def setup_settings_tab(self):
        tab_layout = QVBoxLayout()
        self.settings_tab.setLayout(tab_layout)
        
        title = QLabel("إعدادات التطبيق")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2A82DA; margin-bottom: 20px;")
        tab_layout.addWidget(title)
        
        api_group = QWidget()
        api_layout = QFormLayout()
        api_group.setLayout(api_layout)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("أدخل مفتاح OpenWeatherMap API")
        self.api_key_input.setText(self.api_key)
        api_layout.addRow("مفتاح API:", self.api_key_input)
        
        self.save_api_btn = QPushButton("حفظ المفتاح")
        self.save_api_btn.clicked.connect(self.save_api_key)
        api_layout.addRow(self.save_api_btn)
        
        self.get_api_btn = QToolButton()
        self.get_api_btn.setText("الحصول على مفتاح API")
        self.get_api_btn.setIcon(QIcon.fromTheme("help-about"))
        self.get_api_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.get_api_btn.clicked.connect(self.open_api_website)
        api_layout.addRow(self.get_api_btn)
        
        warning = QLabel("ملاحظة: المفتاح الافتراضي قد لا يعمل، يرجى استخدام مفتاحك الخاص")
        warning.setStyleSheet("color: orange; font-size: 12px;")
        api_layout.addRow(warning)
        
        tab_layout.addWidget(api_group)
        tab_layout.addStretch()
    
    def open_api_website(self):
        QDesktopServices.openUrl(QUrl("https://home.openweathermap.org/api_keys"))
    
    def save_api_key(self):
        api_key = self.api_key_input.text().strip()
        if api_key:
            self.api_key = api_key
            QMessageBox.information(self, "تم الحفظ", "تم حفظ مفتاح API بنجاح")
        else:
            QMessageBox.warning(self, "خطأ", "الرجاء إدخال مفتاح API صحيح")
            
    def find_my_location(self):
        self.location_btn.setEnabled(False)
        self.location_btn.setText("جاري البحث...")

        self.finder = LocationFinder()
        self.finder.location_found.connect(self.on_location_found)
        self.finder.location_error.connect(self.on_location_error)
        self.finder.finished.connect(self.on_finder_finished)
        self.finder.start()

    def on_location_found(self, city):
        QMessageBox.information(self, "تم تحديد الموقع", f"تم تحديد موقعك الحالي: {city}")
        self.search_method.setCurrentIndex(1)
        self.city_input.setText(city)
        self.get_weather()

    def on_location_error(self, error_message):
        QMessageBox.warning(self, "خطأ في تحديد الموقع", error_message)

    def on_finder_finished(self):
        self.location_btn.setEnabled(True)
        self.location_btn.setText("موقعي الحالي")

    def load_cities(self):
        self.progress = QProgressDialog("جاري تحميل قائمة المدن...", "إلغاء", 0, 100, self)
        self.progress.setWindowTitle("تحميل البيانات")
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        self.loader = CityLoader()
        self.loader.progress_updated.connect(self.progress.setValue)
        self.loader.cities_loaded.connect(self.on_cities_loaded)
        self.loader.start()
    
    def on_cities_loaded(self, cities):
        self.cities = cities
        self.filter_cities()
        self.progress.close()
    
    def filter_cities(self):
        search_text = self.city_search.text().strip()
        filtered = {k:v for k,v in self.cities.items() if search_text.lower() in k.lower()}
        
        self.city_combo.clear()
        self.city_combo.addItems(sorted(filtered.keys()))
    
    def toggle_search_method(self, index):
        if index == 0:
            self.city_search.setVisible(True)
            self.city_combo.setVisible(True)
            self.location_btn.setVisible(True)
            self.city_input.setVisible(False)
        else:
            self.city_search.setVisible(False)
            self.city_combo.setVisible(False)
            self.location_btn.setVisible(False)
            self.city_input.setVisible(True)
            self.city_input.setFocus()
    
    def get_weather(self):
        if not self.api_key:
            QMessageBox.critical(self, "خطأ", "الرجاء إدخال مفتاح API أولاً من تبويب الإعدادات")
            self.tabs.setCurrentIndex(1)
            return
        
        city = ""
        city_display = ""
        
        if self.search_method.currentIndex() == 0:
            city_display = self.city_combo.currentText()
            if not city_display:
                QMessageBox.warning(self, "خطأ", "الرجاء اختيار مدينة من القائمة")
                return
            city = self.cities.get(city_display)
        else:
            city = self.city_input.text().strip()
            city_display = city
            if not city:
                QMessageBox.warning(self, "خطأ", "الرجاء إدخال اسم المدينة")
                return
        
        try:
            params = {
                'q': city,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'ar'
            }
            
            # جلب بيانات الطقس الحالية
            current_response = requests.get(self.base_url, params=params)
            # جلب بيانات التوقعات
            forecast_response = requests.get(self.forecast_url, params=params)
            
            if current_response.status_code == 200 and forecast_response.status_code == 200:
                current_data = current_response.json()
                forecast_data = forecast_response.json()
                self.display_weather(current_data, forecast_data, city_display)
            else:
                error_msg = current_response.json().get('message', 'حدث خطأ غير معروف')
                QMessageBox.critical(self, "خطأ", f"لا يمكن الحصول على بيانات الطقس: {error_msg}")
                
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "خطأ", f"فشل الاتصال بالخادم: {str(e)}")

    def parse_rain_forecast(self, forecast_data):
        next_rain_event = None
        # تحقق من أول 8 فترات زمنية (24 ساعة)
        for entry in forecast_data['list'][:8]:
            if 'rain' in entry and '3h' in entry['rain']:
                rain_amount = entry['rain']['3h']
                if rain_amount > 0:
                    # تحويل الوقت من timestamp إلى صيغة قابلة للقراءة
                    event_time = datetime.fromtimestamp(entry['dt']).strftime('%H:%M')
                    next_rain_event = f"متوقع {rain_amount} ملم حوالي الساعة {event_time}"
                    break  # نكتفي بأول توقع لهطول الأمطار
        
        if next_rain_event:
            return next_rain_event
        else:
            return "لا يتوقع هطول أمطار خلال الـ 24 ساعة القادمة"

    def display_weather(self, current_data, forecast_data, city_display):
        weather = current_data['weather'][0]
        main = current_data['main']
        wind = current_data['wind']
        sys_data = current_data.get('sys', {})
        
        self.city_name_label.setText(current_data.get('name', city_display.split(' - ')[0]))
        self.country_label.setText(sys_data.get('country', city_display.split(' - ')[1] if ' - ' in city_display else ''))
        
        icon_url = f"http://openweathermap.org/img/wn/{weather['icon']}@2x.png"
        icon_data = requests.get(icon_url).content
        pixmap = QPixmap()
        pixmap.loadFromData(icon_data)
        self.weather_icon.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio))
        
        self.temp_label.setText(f"{main['temp']}°C")
        self.feels_like_label.setText(f"{main['feels_like']}°C")
        self.humidity_label.setText(f"{main['humidity']}%")
        self.wind_label.setText(f"{wind['speed']} m/s")
        self.pressure_label.setText(f"{main['pressure']} hPa")
        
        # عرض بيانات الأمطار السابقة
        rain_data = current_data.get('rain', {})
        rain_3h = rain_data.get('3h')
        rain_1h = rain_data.get('1h')
        if rain_3h:
            self.past_rain_label.setText(f"{rain_3h} ملم")
        elif rain_1h:
            self.past_rain_label.setText(f"{rain_1h} ملم (آخر ساعة)")
        else:
            self.past_rain_label.setText("لا يوجد أمطار حالياً")
            
        # عرض توقعات الأمطار المستقبلية
        future_rain_text = self.parse_rain_forecast(forecast_data)
        self.future_rain_label.setText(future_rain_text)
        
        self.weather_group.setVisible(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    main_window = QMainWindow()
    weather_widget = WeatherTab()
    main_window.setCentralWidget(weather_widget)
    main_window.setWindowTitle("اختبار تبويب الطقس")
    main_window.setGeometry(100, 100, 650, 700)
    main_window.show()
    
    sys.exit(app.exec())