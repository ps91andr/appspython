import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                            QLabel, QHBoxLayout, QComboBox, QSizePolicy)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon

class ScoresWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("365Scores - متابعة المباريات")
        self.setGeometry(100, 100, 900, 600)
        
        # قوائم البيانات
        self.teams = {
            "131": "ريال مدريد",
            "132": "برشلونة",
            "134": "أتلتيكو مدريد",
            "110": "مانشستر سيتي",
            "108": "ليفربول",
            "105": "مانشستر يونايتد",
            "106": "تشيلسي",
            "104": "أرسنال",
            "480": "باريس سان جيرمان",
            "331": "بايرن ميونخ",
            "227": "ميلان",
            "224": "إنتر ميلان",
            "5457": "الهلال",
            "8593": "نادي الاتحاد",
            "7549": "النصر"
        }
        
        self.leagues = {
            "572": {"name": "دوري أبطال أوروبا", "widget": "58052778-677a-4044-b1c6-b7d1f3412f8d"},
            "11": {"name": "الدوري الإسباني", "widget": "9932913f-ff63-4e6b-8285-99ff0397da2d"},
            "7": {"name": "الدوري الإنجليزي", "widget": "9388aaf9-f6e7-43cb-9eaa-4146e01d0cbb"},
            "25": {"name": "الدوري الألماني", "widget": "83d3ed92-5430-4edc-b7ab-e087d86cca28"},
            "17": {"name": "الدوري الإيطالي", "widget": "3834ddd1-dc19-4729-abe7-9853801f4d84"},
            "35": {"name": "الدوري الفرنسي", "widget": "7a60497b-dc93-4898-99cf-932d6162bd5b"},
            "384": {"name": "كأس العالم", "widget": "f67a6073-dc2d-4cfb-a994-e974fd80a0ef"}
        }

        # إعداد الواجهة
        self.setup_ui()
        
        # تحميل افتراضي
        self.load_team("132")
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        
        # الجزء الأيسر (التحكم)
        control_layout = QVBoxLayout()
        control_layout.setSpacing(15)
        
        # إعداد قائمة الفرق
        team_group = QVBoxLayout()
        team_group.addWidget(QLabel("اختر فريق:"))
        
        self.team_combo = QComboBox()
        self.team_combo.setFixedWidth(220)
        
        # تعيين الفريق الافتراضي (برشلونة)
        default_team_id = "132"
        for team_id, name in self.teams.items():
            icon = self.get_icon(team_id)
            self.team_combo.addItem(icon, f"  {name}", team_id)

        self.team_combo.setCurrentIndex(list(self.teams.keys()).index(default_team_id))  # تعيين الفريق الافتراضي
        
        # صورة الفريق
        self.team_image = QLabel()
        self.team_image.setFixedSize(180, 180)
        self.team_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        team_group.addWidget(self.team_image, 0, Qt.AlignmentFlag.AlignHCenter)
        
        control_layout.addLayout(team_group)

        # تحديث الصورة للفريق الافتراضي
        self.update_image(self.team_image, default_team_id, 180, 180)  # تعيين الصورة الافتراضية

        self.team_combo.setIconSize(QSize(40, 40))
        team_group.addWidget(self.team_combo)
        
        # إعداد قائمة البطولات
        league_group = QVBoxLayout()
        league_group.addWidget(QLabel("اختر بطولة:"))
        
        self.league_combo = QComboBox()
        self.league_combo.setFixedWidth(220)
        for league_id, data in self.leagues.items():
            icon = self.get_icon(league_id)
            self.league_combo.addItem(icon, f"  {data['name']}", league_id)
        self.league_combo.setIconSize(QSize(40, 40))
        league_group.addWidget(self.league_combo)
        
        # صورة البطولة
        self.league_image = QLabel()
        self.league_image.setFixedSize(220, 140)
        self.league_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        league_group.addWidget(self.league_image, 0, Qt.AlignmentFlag.AlignHCenter)
        
        control_layout.addLayout(league_group)
        control_layout.addStretch()
        
        # الجزء الأيمن (الويدجت)
        self.webview = QWebEngineView()
        
        # إضافة الأجزاء إلى التخطيط الرئيسي
        main_layout.addLayout(control_layout, 1)
        main_layout.addWidget(self.webview, 2)
        
        # اتصال الإشارات
        self.team_combo.currentIndexChanged.connect(self.on_team_selected)
        self.league_combo.currentIndexChanged.connect(self.on_league_selected)
    
    def get_icon(self, item_id):
        """الحصول على أيقونة من مجلد team_images"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(base_dir, "team_images", f"{item_id}.png")
        return QIcon(image_path) if os.path.exists(image_path) else QIcon()
    
    def update_image(self, label, item_id, width, height):
        """تحديث الصورة المعروضة"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(base_dir, "team_images", f"{item_id}.png")
        
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            label.setPixmap(pixmap.scaled(
                width, height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            label.clear()
    
    def on_team_selected(self):
        team_id = self.team_combo.currentData()
        self.update_image(self.team_image, team_id, 180, 180)
        self.load_team(team_id)
    
    def on_league_selected(self):
        league_id = self.league_combo.currentData()
        self.update_image(self.league_image, league_id, 220, 140)
        self.load_league(league_id)
    
    def load_team(self, team_id):
        if team_id not in self.teams:
            team_id = "132"
        
        team_name = self.teams[team_id]
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{team_name}</title>
        </head>
        <body>
            <div data-widget-type="entityScores" 
                 data-entity-type="team" 
                 data-entity-id="{team_id}" 
                 data-lang="ar" 
                 data-widget-id="f67a6073-dc2d-4cfb-a994-e974fd80a0ef" 
                 data-theme="dark"></div>
            <div id="powered-by">
                <a id="powered-by-link" href="https://www.365scores.com/ar" target="_blank">365Scores.com</a>مزود من
            </div>
            <script src="https://widgets.365scores.com/main.js"></script>
        </body>
        </html>
        """
        self.webview.setHtml(html, QUrl("https://widgets.365scores.com/"))
    
    def load_league(self, league_id):
        if league_id not in self.leagues:
            league_id = "572"
        
        league = self.leagues[league_id]
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{league['name']}</title>
        </head>
        <body>
            <div data-widget-type="entityScores" 
                 data-entity-type="league" 
                 data-entity-id="{league_id}" 
                 data-lang="ar" 
                 data-widget-id="{league['widget']}" 
                 data-theme="dark"></div>
            <div id="powered-by">
                <a id="powered-by-link" href="https://www.365scores.com/ar" target="_blank">365Scores.com</a>مزود من
            </div>
            <script src="https://widgets.365scores.com/main.js"></script>
        </body>
        </html>
        """
        self.webview.setHtml(html, QUrl("https://widgets.365scores.com/"))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScoresWidget()
    window.show()
    sys.exit(app.exec())