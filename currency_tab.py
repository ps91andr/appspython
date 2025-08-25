import sys
import os
import requests
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFrame, QMessageBox, QCompleter
)
from PyQt6.QtCore import (
    Qt, QObject, pyqtSignal, QThread, QStringListModel
)
# --- [# تعديل #] --- تم نقل QDoubleValidator إلى QtGui ---
from PyQt6.QtGui import QDoubleValidator
# --- قاموس شامل للبيانات ثنائي اللغة (عربي وإنجليزي) ---
# هذا القاموس ضروري لعرض أسماء العملات والدول بشكل صحيح
CURRENCY_DATA_BILINGUAL = {
    "AED": ("Emirati Dirham", "درهم إماراتي", "United Arab Emirates", "الإمارات العربية المتحدة"), "AFN": ("Afghan Afghani", "أفغاني أفغاني", "Afghanistan", "أفغانستان"), "ALL": ("Albanian Lek", "ليك ألباني", "Albania", "ألبانيا"), "AMD": ("Armenian Dram", "درام أرميني", "Armenia", "أرمينيا"), "ANG": ("Netherlands Antillean Guilder", "غيلدر الأنتيل الهولندية", "Netherlands Antilles", "جزر الأنتيل الهولندية"), "AOA": ("Angolan Kwanza", "كوانزا أنغولي", "Angola", "أنغولا"), "ARS": ("Argentine Peso", "بيزو أرجنتيني", "Argentina", "الأرجنتين"), "AUD": ("Australian Dollar", "دولار أسترالي", "Australia", "أستراليا"), "AWG": ("Aruban Florin", "فلورن أروبي", "Aruba", "أروبا"), "AZN": ("Azerbaijani Manat", "مانات أذربيجاني", "Azerbaijan", "أذربيجان"), "BAM": ("Bosnia-Herzegovina Convertible Mark", "مارك بوسني قابل للتحويل", "Bosnia and Herzegovina", "البوسنة والهرسك"), "BBD": ("Barbadian Dollar", "دولار بربادوسي", "Barbados", "بربادوس"), "BDT": ("Bangladeshi Taka", "تاكا بنغلاديشي", "Bangladesh", "بنغلاديش"), "BGN": ("Bulgarian Lev", "ليف بلغاري", "Bulgaria", "بلغاريا"), "BHD": ("Bahraini Dinar", "دينار بحريني", "Bahrain", "البحرين"), "BIF": ("Burundian Franc", "فرنك بوروندي", "Burundi", "بوروندي"), "BMD": ("Bermudian Dollar", "دولار برمودي", "Bermuda", "برمودا"), "BND": ("Brunei Dollar", "دولار بروناي", "Brunei", "بروناي"), "BOB": ("Bolivian Boliviano", "بوليفيانو بوليفي", "Bolivia", "بوليفيا"), "BRL": ("Brazilian Real", "ريال برازيلي", "Brazil", "البرازيل"), "BSD": ("Bahamian Dollar", "دولار باهامي", "Bahamas", "جزر البهاما"), "BTN": ("Bhutanese Ngultrum", "نغولترم بوتاني", "Bhutan", "بوتان"), "BWP": ("Botswanan Pula", "بولا بوتسواني", "Botswana", "بوتسوانا"), "BYN": ("Belarusian Ruble", "روبل بيلاروسي", "Belarus", "بيلاروسيا"), "BZD": ("Belize Dollar", "دولار بليزي", "Belize", "بليز"), "CAD": ("Canadian Dollar", "دولار كندي", "Canada", "كندا"), "CDF": ("Congolese Franc", "فرنك كونغولي", "Congo, DR", "جمهورية الكونغو الديمقراطية"), "CHF": ("Swiss Franc", "فرنك سويسري", "Switzerland", "سويسرا"), "CLP": ("Chilean Peso", "بيزو تشيلي", "Chile", "تشيلي"), "CNY": ("Chinese Yuan", "يوان صيني", "China", "الصين"), "COP": ("Colombian Peso", "بيزو كولومبي", "Colombia", "كولومبيا"), "CRC": ("Costa Rican Colón", "كولون كوستاريكي", "Costa Rica", "كوستاريكا"), "CUP": ("Cuban Peso", "بيزو كوبي", "Cuba", "كوبا"), "CVE": ("Cape Verdean Escudo", "إيسكودو جزر الرأس الأخضر", "Cape Verde", "الرأس الأخضر"), "CZK": ("Czech Koruna", "كرونة تشيكية", "Czech Republic", "جمهورية التشيك"), "DJF": ("Djiboutian Franc", "فرنك جيبوتي", "Djibouti", "جيبوتي"), "DKK": ("Danish Krone", "كرونة دنماركية", "Denmark", "الدنمارك"), "DOP": ("Dominican Peso", "بيزو دومنيكاني", "Dominican Republic", "جمهورية الدومينيكان"), "DZD": ("Algerian Dinar", "دينار جزائري", "Algeria", "الجزائر"), "EGP": ("Egyptian Pound", "جنيه مصري", "Egypt", "مصر"), "ERN": ("Eritrean Nakfa", "ناكفا إريتري", "Eritrea", "إريتريا"), "ETB": ("Ethiopian Birr", "بير إثيوبي", "Ethiopia", "إثيوبيا"), "EUR": ("Euro", "يورو", "European Union", "الاتحاد الأوروبي"), "FJD": ("Fijian Dollar", "دولار فيجي", "Fiji", "فيجي"), "FKP": ("Falkland Islands Pound", "جنيه جزر فوكلاند", "Falkland Islands", "جزر فوكلاند"), "FOK": ("Faroese Króna", "كرونة فاروية", "Faroe Islands", "جزر فارو"), "GBP": ("British Pound", "جنيه إسترليني", "United Kingdom", "المملكة المتحدة"), "GEL": ("Georgian Lari", "لاري جورجي", "Georgia", "جورجيا"), "GGP": ("Guernsey Pound", "جنيه غيرنسي", "Guernsey", "غيرنسي"), "GHS": ("Ghanaian Cedi", "سيدي غاني", "Ghana", "غانا"), "GIP": ("Gibraltar Pound", "جنيه جبل طارق", "Gibraltar", "جبل طارق"), "GMD": ("Gambian Dalasi", "دالاسي غامبي", "Gambia", "غامبيا"), "GNF": ("Guinean Franc", "فرنك غيني", "Guinea", "غينيا"), "GTQ": ("Guatemalan Quetzal", "كيتزال غواتيمالي", "Guatemala", "غواتيمالا"), "GYD": ("Guyanaese Dollar", "دولار غياني", "Guyana", "غيانا"), "HKD": ("Hong Kong Dollar", "دولار هونغ كونغ", "Hong Kong", "هونغ كونغ"), "HNL": ("Honduran Lempira", "لمبيرا هندوراسي", "Honduras", "هندوراس"), "HRK": ("Croatian Kuna", "كونا كرواتي", "Croatia", "كرواتيا"), "HTG": ("Haitian Gourde", "غورد هايتي", "Haiti", "هايتي"), "HUF": ("Hungarian Forint", "فورنت مجري", "Hungary", "المجر"), "IDR": ("Indonesian Rupiah", "روبية إندونيسية", "Indonesia", "إندونيسيا"), "ILS": ("Israeli New Shekel", "شيكل إسرائيلي جديد", "Israel", "إسرائيل"), "IMP": ("Isle of Man Pound", "جنيه مانكس", "Isle of Man", "جزيرة مان"), "INR": ("Indian Rupee", "روبية هندية", "India", "الهند"), "IQD": ("Iraqi Dinar", "دينار عراقي", "Iraq", "العراق"), "IRR": ("Iranian Rial", "ريال إيراني", "Iran", "إيران"), "ISK": ("Icelandic Króna", "كرونة آيسلندية", "Iceland", "آيسلندا"), "JEP": ("Jersey Pound", "جنيه جيرسي", "Jersey", "جيرسي"), "JMD": ("Jamaican Dollar", "دولار جامايكي", "Jamaica", "جامايكا"), "JOD": ("Jordanian Dinar", "دينار أردني", "Jordan", "الأردن"), "JPY": ("Japanese Yen", "ين ياباني", "Japan", "اليابان"), "KES": ("Kenyan Shilling", "شلن كيني", "Kenya", "كينيا"), "KGS": ("Kyrgystani Som", "سوم قيرغيزستاني", "Kyrgyzstan", "قيرغيزستان"), "KHR": ("Cambodian Riel", "ريال كمبودي", "Cambodia", "كمبوديا"), "KID": ("Kiribati Dollar", "دولار كيريباتي", "Kiribati", "كيريباتي"), "KMF": ("Comorian Franc", "فرنك قمري", "Comoros", "جزر القمر"), "KRW": ("South Korean Won", "وون كوريا الجنوبية", "South Korea", "كوريا الجنوبية"), "KWD": ("Kuwaiti Dinar", "دينار كويتي", "Kuwait", "الكويت"), "KYD": ("Cayman Islands Dollar", "دولار جزر كايمان", "Cayman Islands", "جزر كايمان"), "KZT": ("Kazakhstani Tenge", "تينغ كازاخستاني", "Kazakhstan", "كازاخستان"), "LAK": ("Laotian Kip", "كيب لاوسي", "Laos", "لاوس"), "LBP": ("Lebanese Pound", "ليرة لبنانية", "Lebanon", "لبنان"), "LKR": ("Sri Lankan Rupee", "روبية سريلانكية", "Sri Lanka", "سريلانكا"), "LRD": ("Liberian Dollar", "دولار ليبيري", "Liberia", "ليبيريا"), "LSL": ("Lesotho Loti", "لوتي ليسوتو", "Lesotho", "ليسوتو"), "LYD": ("Libyan Dinar", "دينار ليبي", "Libya", "ليبيا"), "MAD": ("Moroccan Dirham", "درهم مغربي", "Morocco", "المغرب"), "MDL": ("Moldovan Leu", "ليو مولدوفي", "Moldova", "مولدوفا"), "MGA": ("Malagasy Ariary", "أرياري مدغشقري", "Madagascar", "مدغشقر"), "MKD": ("Macedonian Denar", "دينار مقدوني", "North Macedonia", "مقدونيا الشمالية"), "MMK": ("Myanmar Kyat", "كيات ميانماري", "Myanmar", "ميانمار"), "MNT": ("Mongolian Tugrik", "توغروغ منغولي", "Mongolia", "منغوليا"), "MOP": ("Macanese Pataca", "باتاكا ماكاوية", "Macau", "ماكاو"), "MRU": ("Mauritanian Ouguiya", "أوقية موريتانية", "Mauritania", "موريتانيا"), "MUR": ("Mauritian Rupee", "روبية موريشية", "Mauritius", "موريشيوس"), "MVR": ("Maldivian Rufiyaa", "روفية مالديفية", "Maldives", "جزر المالديف"), "MWK": ("Malawian Kwacha", "كواتشا ملاوية", "Malawi", "مالاوي"), "MXN": ("Mexican Peso", "بيزو مكسيكي", "Mexico", "المكسيك"), "MYR": ("Malaysian Ringgit", "رينغيت ماليزي", "Malaysia", "ماليزيا"), "MZN": ("Mozambican Metical", "متكال موزمبيقي", "Mozambique", "موزمبيق"), "NAD": ("Namibian Dollar", "دولار ناميبي", "Namibia", "ناميبيا"), "NGN": ("Nigerian Naira", "نيرة نيجيرية", "Nigeria", "نيجيريا"), "NIO": ("Nicaraguan Córdoba", "كوردوبا نيكاراغوا", "Nicaragua", "نيكاراغوا"), "NOK": ("Norwegian Krone", "كرونة نرويجية", "Norway", "النرويج"), "NPR": ("Nepalese Rupee", "روبية نيبالية", "Nepal", "نيبال"), "NZD": ("New Zealand Dollar", "دولار نيوزيلندي", "New Zealand", "نيوزيلندا"), "OMR": ("Omani Rial", "ريال عماني", "Oman", "عمان"), "PAB": ("Panamanian Balboa", "بالبوا بنمي", "Panama", "بنما"), "PEN": ("Peruvian Sol", "سول بيروفي", "Peru", "بيرو"), "PGK": ("Papua New Guinean Kina", "كينا بابوا غينيا الجديدة", "Papua New Guinea", "بابوا غينيا الجديدة"), "PHP": ("Philippine Peso", "بيزو فلبيني", "Philippines", "الفلبين"), "PKR": ("Pakistani Rupee", "روبية باكستانية", "Pakistan", "باكستان"), "PLN": ("Polish Złoty", "زلوتي بولندي", "Poland", "بولندا"), "PYG": ("Paraguayan Guarani", "غواراني باراغواي", "Paraguay", "باراغواي"), "QAR": ("Qatari Riyal", "ريال قطري", "Qatar", "قطر"), "RON": ("Romanian Leu", "ليو روماني", "Romania", "رومانيا"), "RSD": ("Serbian Dinar", "دينار صربي", "Serbia", "صربيا"), "RUB": ("Russian Ruble", "روبل روسي", "Russia", "روسيا"), "RWF": ("Rwandan Franc", "فرنك رواندي", "Rwanda", "رواندا"), "SAR": ("Saudi Riyal", "ريال سعودي", "Saudi Arabia", "المملكة العربية السعودية"), "SBD": ("Solomon Islands Dollar", "دولار جزر سليمان", "Solomon Islands", "جزر سليمان"), "SCR": ("Seychellois Rupee", "روبية سيشيلية", "Seychelles", "سيشيل"), "SDG": ("Sudanese Pound", "جنيه سوداني", "Sudan", "السودان"), "SEK": ("Swedish Krona", "كرونة سويدية", "Sweden", "السويد"), "SGD": ("Singapore Dollar", "دولار سنغافوري", "Singapore", "سنغافورة"), "SHP": ("Saint Helena Pound", "جنيه سانت هيلين", "Saint Helena", "سانت هيلينا"), "SLE": ("Sierra Leonean Leone", "ليون سيراليوني", "Sierra Leone", "سيراليون"), "SOS": ("Somali Shilling", "شلن صومالي", "Somalia", "الصومال"), "SRD": ("Surinamese Dollar", "دولار سورينامي", "Suriname", "سورينام"), "SSP": ("South Sudanese Pound", "جنيه جنوب السودان", "South Sudan", "جنوب السودان"), "STN": ("São Tomé and Príncipe Dobra", "دوبرا ساو تومي وبرينسيب", "São Tomé and Príncipe", "ساو تومي وبرينسيب"), "SYP": ("Syrian Pound", "ليرة سورية", "Syria", "سوريا"), "SZL": ("Swazi Lilangeni", "ليلانغيني سوازيلندي", "Eswatini", "إسواتيني"), "THB": ("Thai Baht", "بات تايلاندي", "Thailand", "تايلاند"), "TJS": ("Tajikistani Somoni", "سوموني طاجيكستاني", "Tajikistan", "طاجيكستان"), "TMT": ("Turkmenistani Manat", "منات تركمانستاني", "Turkmenistan", "تركمانستان"), "TND": ("Tunisian Dinar", "دينار تونسي", "Tunisia", "تونس"), "TOP": ("Tongan Paʻanga", "بانجا تونغي", "Tonga", "تونغا"), "TRY": ("Turkish Lira", "ليرة تركية", "Turkey", "تركيا"), "TTD": ("Trinidad and Tobago Dollar", "دولار ترينيداد وتوباغو", "Trinidad and Tobago", "ترينيداد وتوباغو"), "TVD": ("Tuvaluan Dollar", "دولار توفالي", "Tuvalu", "توفالو"), "TWD": ("New Taiwan Dollar", "دولار تايواني جديد", "Taiwan", "تايوان"), "TZS": ("Tanzanian Shilling", "شلن تنزاني", "Tanzania", "تنزانيا"), "UAH": ("Ukrainian Hryvnia", "هريفنيا أوكرانية", "Ukraine", "أوكرانيا"), "UGX": ("Ugandan Shilling", "شلن أوغندي", "Uganda", "أوغندا"), "UYU": ("Uruguayan Peso", "بيزو أوروغواي", "Uruguay", "الأوروغواي"), "UZS": ("Uzbekistani Som", "سوم أوزبكستاني", "Uzbekistan", "أوزبكستان"), "VES": ("Venezuelan Bolívar", "بوليفار فنزويلي", "Venezuela", "فنزويلا"), "VND": ("Vietnamese Dong", "دونغ فيتنامي", "Vietnam", "فيتنام"), "VUV": ("Vanuatu Vatu", "فاتو فانواتي", "Vanuatu", "فانواتو"), "WST": ("Samoan Tālā", "تالا ساموي", "Samoa", "ساموا"), "XAF": ("Central African CFA Franc", "فرنك وسط أفريقي", "CEMAC", "مجموعة دول وسط أفريقيا"), "XCD": ("East Caribbean Dollar", "دولار شرق الكاريبي", "OECS", "منظمة دول شرق الكاريبي"), "XDR": ("Special Drawing Rights", "حقوق السحب الخاصة", "IMF", "صندوق النقد الدولي"), "XOF": ("West African CFA Franc", "فرنك غرب أفريقي", "CFA", "مجموعة دول غرب أفريقيا"), "XPF": ("CFP Franc", "فرنك سي إف بي", "Collectivités d'Outre-Mer", "الأقاليم الفرنسية ما وراء البحار"), "YER": ("Yemeni Rial", "ريال يمني", "Yemen", "اليمن"), "ZAR": ("South African Rand", "راند جنوب أفريقي", "South Africa", "جنوب أفريقيا"), "ZMW": ("Zambian Kwacha", "كواتشا زامبي", "Zambia", "زامبيا"), "ZWL": ("Zimbabwean Dollar", "دولار زيمبابوي", "Zimbabwe", "زيمبابوي")
}

# --- أنماط تصميم الواجهة (CSS) ---
APP_STYLE = """
QWidget { background-color: #2d3436; color: #dfe6e9; font-family: 'Cairo', 'Segoe UI', Arial; font-size: 12pt; }
QComboBox { background-color: #636e72; border: 1px solid #b2bec3; border-radius: 5px; padding: 8px; min-width: 6em; }
QComboBox:editable { background-color: #3f494c; }
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background-color: #636e72; selection-background-color: #0984e3; color: #dfe6e9; }
QLineEdit { background-color: #636e72; border: 1px solid #b2bec3; border-radius: 5px; padding: 8px; font-size: 16pt; font-weight: bold; }
QLineEdit#apiKeyInput { font-size: 10pt; font-weight: normal; }
QPushButton { background-color: #0984e3; color: white; font-weight: bold; border: none; border-radius: 5px; padding: 10px; }
QPushButton:hover { background-color: #74b9ff; }
QLabel#titleLabel { font-size: 24pt; font-weight: bold; color: #55efc4; padding-bottom: 10px; }
QLabel#resultLabel { font-size: 20pt; font-weight: bold; color: #55efc4; padding-top: 15px; }
QFrame { border: 1px solid #636e72; border-radius: 8px; }
QLabel#apiKeyLabel a { color: #FFFFFF; text-decoration: none; }
QLabel#apiKeyLabel a:hover { text-decoration: underline; }
"""

class ApiWorker(QObject):
    """
    عامل (Worker) يعمل في خيط منفصل لجلب بيانات API لتجنب تجميد الواجهة.
    """
    success = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key

    def run(self):
        """
        يقوم بطلب البيانات من API ويرسل إشارة نجاح أو خطأ.
        """
        if not self.api_key:
            self.error.emit("API key is missing.")
            return

        url = f"https://v6.exchangerate-api.com/v6/{self.api_key}/latest/USD"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # يثير استثناء لأكواد الخطأ (4xx أو 5xx)
            data = response.json()
            if data.get("result") == "success":
                self.success.emit(data["conversion_rates"])
            else:
                error_type = data.get("error-type", "unknown_error")
                self.error.emit(f"API Error: {error_type}")
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Network Error: {e}")
        except Exception as e:
            self.error.emit(f"Unexpected Error: {e}")

class CurrencyConverter(QWidget):
    """
    الواجهة الرئيسية لتطبيق محول العملات.
    """
    API_KEY_FILE = "api_key.txt"

    def __init__(self):
        super().__init__()
        self.rates = {}
        self.currency_model = QStringListModel()
        self.api_key = self.load_key_from_file()
        self.initUI()
        self.load_exchange_rates()

    def initUI(self):
        """
        يقوم بإعداد وبناء واجهة المستخدم الرسومية.
        """
        self.setWindowTitle('محول العملات الفوري')
        self.setGeometry(300, 300, 750, 550)
        self.setStyleSheet(APP_STYLE)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("محول العملات")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- إطار قسم التحويل ---
        converter_frame = QFrame()
        converter_layout = QVBoxLayout(converter_frame)
        self.amount_input = QLineEdit("1")
        # السماح بإدخال الأرقام العشرية فقط
        self.amount_input.setValidator(QDoubleValidator(0.0, 999999999.0, 8, self))
        self.amount_input.setAlignment(Qt.AlignmentFlag.AlignCenter)

        selectors_layout = QHBoxLayout()
        self.from_currency = self.create_searchable_combobox()
        self.to_currency = self.create_searchable_combobox()
        swap_button = QPushButton("⇄")
        swap_button.setFixedWidth(40)
        swap_button.clicked.connect(self.swap_currencies)
        selectors_layout.addWidget(self.from_currency)
        selectors_layout.addWidget(swap_button)
        selectors_layout.addWidget(self.to_currency)

        # ربط الأدوات بوظيفة التحويل مباشرة للتحديث التلقائي
        self.amount_input.textChanged.connect(self.convert_currency)
        self.from_currency.currentIndexChanged.connect(self.convert_currency)
        self.to_currency.currentIndexChanged.connect(self.convert_currency)

        converter_layout.addWidget(QLabel("المبلغ:"))
        converter_layout.addWidget(self.amount_input)
        converter_layout.addSpacing(15)
        converter_layout.addWidget(QLabel("من عملة / إلى عملة:"))
        converter_layout.addLayout(selectors_layout)

        self.result_label = QLabel("")
        self.result_label.setObjectName("resultLabel")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        # --- إطار قسم مفتاح API ---
        api_key_frame = QFrame()
        api_key_layout = QVBoxLayout(api_key_frame)
        api_key_input_layout = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setObjectName("apiKeyInput")
        self.api_key_input.setPlaceholderText("أدخل مفتاح الـ API هنا")
        self.api_key_input.setText(self.api_key)
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.toggle_visibility_button = QPushButton("إظهار")
        self.toggle_visibility_button.setFixedWidth(80)
        self.toggle_visibility_button.clicked.connect(self.toggle_api_key_visibility)
        
        api_key_input_layout.addWidget(self.api_key_input)
        api_key_input_layout.addWidget(self.toggle_visibility_button)

        save_key_button = QPushButton("حفظ المفتاح وتحديث البيانات")
        save_key_button.clicked.connect(self.save_and_reload)

        api_key_layout.addWidget(QLabel("مفتاح API:"))
        api_key_layout.addLayout(api_key_input_layout)
        api_key_layout.addWidget(save_key_button)

        api_link_label = QLabel(
            '<a href="https://app.exchangerate-api.com/keys">الحصول على مفتاح API مجاني</a>'
        )
        api_link_label.setObjectName("apiKeyLabel")
        api_link_label.setOpenExternalLinks(True)
        api_link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- تجميع الواجهة ---
        main_layout.addWidget(title)
        main_layout.addWidget(converter_frame)
        main_layout.addWidget(self.result_label)
        main_layout.addStretch() # فاصل مرن
        main_layout.addWidget(api_key_frame)
        main_layout.addWidget(api_link_label)

        self.setLayout(main_layout)

    def load_key_from_file(self):
        """
        يحاول قراءة مفتاح API من ملف محلي، وإذا فشل يعيد مفتاحًا افتراضيًا.
        """
        if os.path.exists(self.API_KEY_FILE):
            with open(self.API_KEY_FILE, 'r') as f:
                return f.read().strip()
        # مفتاح افتراضي إذا لم يتم العثور على الملف
        return "a1e5aab94f0d22a7d9759df9"

    def save_key_to_file(self, key):
        """
        يحفظ مفتاح API في ملف نصي.
        """
        try:
            with open(self.API_KEY_FILE, 'w') as f:
                f.write(key)
            return True
        except IOError as e:
            QMessageBox.critical(self, "خطأ في الحفظ", f"لم أتمكن من حفظ المفتاح: {e}")
            return False

    def save_and_reload(self):
        """
        يحفظ مفتاح API الجديد من حقل الإدخال ثم يعيد تحميل أسعار الصرف.
        """
        new_key = self.api_key_input.text().strip()
        if not new_key:
            QMessageBox.warning(self, "فارغ", "حقل مفتاح API لا يمكن أن يكون فارغًا.")
            return

        if self.save_key_to_file(new_key):
            self.api_key = new_key
            QMessageBox.information(self, "تم الحفظ", "تم حفظ مفتاح API بنجاح. سيتم الآن تحديث البيانات.")
            self.load_exchange_rates()

    def toggle_api_key_visibility(self):
        """
        يغير وضع عرض حقل إدخال مفتاح API بين العادي والمخفي (كلمة مرور).
        """
        if self.api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_visibility_button.setText("إخفاء")
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_visibility_button.setText("إظهار")
        
    def create_searchable_combobox(self):
        """
        ينشئ قائمة منسدلة قابلة للبحث.
        """
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setCompleter(QCompleter(self.currency_model, self))
        # جعل البحث غير حساس لحالة الأحرف ويطابق أي جزء من النص
        combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        combo.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        return combo

    def load_exchange_rates(self):
        """
        يبدأ عملية تحميل أسعار الصرف في خيط منفصل.
        """
        self.thread = QThread()
        self.worker = ApiWorker(self.api_key)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.success.connect(self.on_data_loaded)
        self.worker.error.connect(self.on_data_error)
        self.thread.finished.connect(self.thread.deleteLater) # تنظيف الخيط بعد الانتهاء
        self.thread.start()
        self.result_label.setText("جاري تحميل أسعار الصرف...")

    def on_data_loaded(self, rates):
        """
        يتم استدعاؤها عند نجاح جلب البيانات من API.
        """
        self.rates = rates
        self.from_currency.clear()
        self.to_currency.clear()
        
        display_list = []
        # تعبئة القوائم المنسدلة ببيانات العملات
        for code in sorted(self.rates.keys()):
            if code in CURRENCY_DATA_BILINGUAL:
                en_name, ar_name, en_country, ar_country = CURRENCY_DATA_BILINGUAL[code]
                display_text = f"{code} | {ar_name} ({en_name}) - {ar_country}"
            else:
                display_text = code
            
            display_list.append(display_text)
            self.from_currency.addItem(display_text, code)
            self.to_currency.addItem(display_text, code)
            
        self.currency_model.setStringList(display_list)
        
        # تعيين عملات افتراضية عند بدء التشغيل
        usd_index = self.from_currency.findData("USD")
        if usd_index != -1: self.from_currency.setCurrentIndex(usd_index)
        
        sar_index = self.to_currency.findData("SAR")
        if sar_index != -1: self.to_currency.setCurrentIndex(sar_index)
        
        self.result_label.setText("تم تحميل البيانات بنجاح.")
        # إجراء تحويل أولي عند بدء التشغيل
        self.convert_currency()
        
    def on_data_error(self, error_message):
        """
        يتم استدعاؤها عند فشل جلب البيانات من API.
        """
        self.result_label.setText("فشل تحميل البيانات.")
        if "invalid-key" in error_message:
            title = "مفتاح API غير صالح"
            text = "مفتاح الـ API المستخدم غير صالح. الرجاء إدخال مفتاح صحيح في الحقل المخصص والضغط على 'حفظ'."
        else:
            title = "خطأ في الشبكة أو الـ API"
            text = f"حدث خطأ أثناء الاتصال:\n{error_message}"
        
        QMessageBox.critical(self, title, text)

    def swap_currencies(self):
        """
        يبدل بين العملتين المحددتين في القوائم المنسدلة.
        """
        from_idx = self.from_currency.currentIndex()
        to_idx = self.to_currency.currentIndex()

        # منع استدعاء convert_currency مرتين عند التبديل
        self.from_currency.blockSignals(True)
        self.to_currency.blockSignals(True)
        
        self.from_currency.setCurrentIndex(to_idx)
        self.to_currency.setCurrentIndex(from_idx)

        self.from_currency.blockSignals(False)
        self.to_currency.blockSignals(False)

        # استدعاء التحويل مرة واحدة بعد التبديل
        self.convert_currency()

    def convert_currency(self):
        """
        يقوم بعملية التحويل الفعلية ويعرض النتيجة.
        """
        amount_text = self.amount_input.text().replace(',', '.')
        
        if not amount_text or amount_text == ".":
            self.result_label.setText("")
            return

        try:
            amount = float(amount_text)
            from_code = self.from_currency.currentData()
            to_code = self.to_currency.currentData()

            # التأكد من وجود بيانات قبل محاولة التحويل
            if not from_code or not to_code or not self.rates:
                return

            # التحويل يتم عبر الدولار الأمريكي (العملة الأساسية في الـ API)
            amount_in_usd = amount / self.rates[from_code]
            converted_amount = amount_in_usd * self.rates[to_code]

            self.result_label.setText(f"{converted_amount:,.4f} {to_code}")

        except ValueError:
            # هذا يحدث أثناء الكتابة (مثلاً كتابة "1.")، يمكن تجاهله
            self.result_label.setText("...")
        except Exception as e:
            self.result_label.setText(f"خطأ: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CurrencyConverter()
    ex.show()
    sys.exit(app.exec())