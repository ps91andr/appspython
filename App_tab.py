import sys
import subprocess
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit, QTabWidget

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('تشغيل CMD كمسؤول')
        self.setGeometry(50, 50, 700, 100)

        tab_widget = QTabWidget()

        # إعداد التبويبات
        system_tab = QWidget()
        network_tab = QWidget()
        disk_tab = QWidget()
        file_explorer_tab = QWidget()
        troubleshooting_tab = QWidget()
        additional_fixes_tab = QWidget()
        internet_connection_tab = QWidget()

        tab_widget.addTab(system_tab, "أنظمة")
        tab_widget.addTab(network_tab, "شبكة")
        tab_widget.addTab(disk_tab, "قرص")
        tab_widget.addTab(file_explorer_tab, "مستكشف الملفات")
        tab_widget.addTab(troubleshooting_tab, "استكشاف الأخطاء")
        tab_widget.addTab(additional_fixes_tab, "إصلاحات إضافية")
        tab_widget.addTab(internet_connection_tab, "الإنترنت والاتصال")

        # إعداد تبويب النظام
        system_layout = QVBoxLayout()
        self.add_system_commands(system_layout)
        system_tab.setLayout(system_layout)

        # إعداد تبويب الشبكة
        network_layout = QVBoxLayout()
        self.add_network_commands(network_layout)
        network_tab.setLayout(network_layout)

        # إعداد تبويب القرص
        disk_layout = QVBoxLayout()
        self.add_disk_commands(disk_layout)
        disk_tab.setLayout(disk_layout)

        # إعداد تبويب مستكشف الملفات
        file_explorer_layout = QVBoxLayout()
        self.add_file_explorer_commands(file_explorer_layout)
        file_explorer_tab.setLayout(file_explorer_layout)

        # إعداد تبويب استكشاف الأخطاء
        troubleshooting_layout = QVBoxLayout()
        self.add_troubleshooting_commands(troubleshooting_layout)
        troubleshooting_tab.setLayout(troubleshooting_layout)

        # إعداد تبويب الإصلاحات الإضافية
        additional_fixes_layout = QVBoxLayout()
        self.add_additional_fixes_commands(additional_fixes_layout)
        additional_fixes_tab.setLayout(additional_fixes_layout)

        # إعداد تبويب الإنترنت والاتصال
        internet_connection_layout = QVBoxLayout()
        self.add_internet_connection_commands(internet_connection_layout)
        internet_connection_tab.setLayout(internet_connection_layout)

        # إعداد النص لعرض النتائج
        self.log_output = QTextEdit(self)
        self.log_output.setReadOnly(True)

        main_layout = QVBoxLayout()
        main_layout.addWidget(tab_widget)
        main_layout.addWidget(self.log_output)

        self.setLayout(main_layout)

    def add_system_commands(self, layout):
        commands = [
            ("تشغيل CMD كمسؤول", self.run_cmd_as_admin),
            ("sfc /scannow", self.run_sfc),
            ("DISM /CheckHealth", self.run_dism_checkhealth),
            ("DISM /ScanHealth", self.run_dism_scanhealth),
            ("DISM /RestoreHealth", self.run_dism_restorehealth),
        ]
        for name, method in commands:
            button = QPushButton(name, self)
            button.clicked.connect(method)
            layout.addWidget(button)

    def add_network_commands(self, layout):
        commands = [
            ("ipconfig", self.run_ipconfig),
            ("ipconfig /all", self.run_ipconfig_all),
            ("ipconfig /release", self.run_ipconfig_release),
            ("ipconfig /renew", self.run_ipconfig_renew),
            ("ping 8.8.8.8", self.run_ping),
            ("tracert 8.8.8.8", self.run_tracert),
            ("netsh int ip reset", self.run_netsh_reset),
            ("ipconfig /flushdns", self.run_ipconfig_flushdns),
        ]
        for name, method in commands:
            button = QPushButton(name, self)
            button.clicked.connect(method)
            layout.addWidget(button)

    def add_disk_commands(self, layout):
        commands = [
            ("chkdsk C:", lambda: self.run_chkdsk("")),
            ("chkdsk C: /f", lambda: self.run_chkdsk("/f")),
            ("chkdsk C: /r", lambda: self.run_chkdsk("/r")),
            ("chkdsk C: /x", lambda: self.run_chkdsk("/x")),
            ("chkdsk C: /scan", lambda: self.run_chkdsk("/scan")),
            ("chkdsk C: /b", lambda: self.run_chkdsk("/b")),
        ]
        for name, method in commands:
            button = QPushButton(name, self)
            button.clicked.connect(method)
            layout.addWidget(button)

    def add_file_explorer_commands(self, layout):
        commands = [
            ("إصلاح سلة المحذوفات", self.run_repair_recycle_bin),
            ("إعادة تعيين سلة المحذوفات", self.run_reset_recycle_bin),
            ("إصلاح خطأ WerMgr.exe", self.run_fix_wer),
            ("إظهار الملفات والمجلدات المخفية", self.run_show_hidden_files),
            ("إصلاح الصور المصغرة", self.run_fix_thumbnails),
            ("إصلاح محرك الأقراص المضغوطة", self.run_fix_cd_drive),
            ("إصلاح الفئة غير مسجلة", self.run_fix_class_not_registered),
        ]
        for name, method in commands:
            button = QPushButton(name, self)
            button.clicked.connect(method)
            layout.addWidget(button)

    def add_troubleshooting_commands(self, layout):
        commands = [
            ("تشغيل الصوت", self.run_audio_troubleshooter),
            ("تسجيل الصوت", self.run_audio_recording_troubleshooter),
            ("قوة", self.run_power_troubleshooter),
            ("طابعة", self.run_printer_troubleshooter),
            ("المجلدات المشتركة", self.run_shared_folders_troubleshooter),
            ("مجموعة", self.run_group_troubleshooter),
            ("أداء الإنترنت", self.run_internet_performance_troubleshooter),
            ("سلامة الإنترنت", self.run_internet_safety_troubleshooter),
            ("إعدادات Windows Media Player", self.run_wmp_settings_troubleshooter),
            ("مكتبة Windows Media Player", self.run_wmp_library_troubleshooter),
            ("Windows Media Player DVD", self.run_wmp_dvd_troubleshooter),
            ("اتصالات الإنترنت", self.run_internet_connections_troubleshooter),
            ("الأجهزة والأجهزة", self.run_hardware_devices_troubleshooter),
            ("الاتصالات الواردة", self.run_incoming_connections_troubleshooter),
            ("صيانة النظام", self.run_system_maintenance_troubleshooter),
            ("محول الشبكة", self.run_network_adapter_troubleshooter),
            ("تحديث Windows", self.run_windows_update_troubleshooter),
            ("البحث والفهرسة", self.run_search_indexing_troubleshooter),
            ("تعطل تطبيقات البريد والتقويم", self.run_mail_calendar_troubleshooter),
            ("لا يتم تشغيل تطبيق الإعدادات", self.run_settings_app_troubleshooter),
            ("محلل أخطاء طابعة Windows", self.run_printer_error_analyzer),
            ("استكشاف أخطاء تطبيقات Windows Store", self.run_windows_store_app_troubleshooter),
        ]
        for name, method in commands:
            button = QPushButton(name, self)
            button.clicked.connect(method)
            layout.addWidget(button)

    def add_additional_fixes_commands(self, layout):
        commands = [
            ("إضافة دعم ذاكرة التخزين المؤقت لرمز إعادة البناء", self.run_cache_icon_rebuild),
            ("تمكين السبات", self.run_enable_hibernation),
            ("استعادة مربع الحوار حذف Sticky Notes", self.run_restore_sticky_notes_dialog),
            ("إصلاح Aero Snap", self.run_fix_aero_snap),
            ("إصلاح أيقونات سطح المكتب التالفة", self.run_fix_desktop_icons),
            ("إصلاح قائمة قفزة شريط المهام", self.run_fix_jump_list),
            ("تمكين الإخطارات", self.run_enable_notifications),
            ("تمكين الوصول إلى Windows Script Host", self.run_enable_wsh_access),
            ("إصلاح مستندات Office", self.run_fix_office_documents),
            ("إصلاح صورة الاسترداد", self.run_fix_recovery_image),
            ("إصلاح Windows Media Player", self.run_fix_wmp_error),
        ]
        for name, method in commands:
            button = QPushButton(name, self)
            button.clicked.connect(method)
            layout.addWidget(button)

    def add_internet_connection_commands(self, layout):
        commands = [
            ("تمكين قائمة سياق النقر بزر الماوس الأيمن لـ IE", self.run_enable_ie_context_menu),
            ("إصلاح مشاكل بروتوكول الإنترنت (TCP/IP)", self.run_fix_tcp_ip),
            ("إصلاح مشكلة DNS", self.run_fix_dns),
            ("مسح محفوظات تحديث Windows", self.run_clear_windows_update_history),
            ("إعادة تعيين جدار حماية Windows", self.run_reset_firewall),
            ("إعادة تعيين إعدادات IE", self.run_reset_ie),
            ("إصلاح أخطاء وقت التشغيل في IE", self.run_fix_ie_runtime_errors),
            ("تحسين الحد الأقصى للاتصالات", self.run_improve_internet_connections),
            ("إعدادات الإنترنت مفقودة", self.run_fix_missing_internet_options),
            ("إصلاح Winsock", self.run_fix_winsock),
            ("تمكين Telnet", self.run_enable_telnet),
        ]
        for name, method in commands:
            button = QPushButton(name, self)
            button.clicked.connect(method)
            layout.addWidget(button)

    def log(self, message):
        self.log_output.append(message)

    def run_cmd_as_admin(self):
        self.log("تشغيل CMD كمسؤول...")
        subprocess.Popen('powershell -Command "Start-Process cmd -Verb RunAs"', shell=True)

    def run_sfc(self):
        self.log("بدء فحص ملفات النظام...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k sfc /scannow\'"', shell=True)

    def run_dism_checkhealth(self):
        self.log("تشغيل DISM /CheckHealth...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k DISM /Online /Cleanup-Image /CheckHealth\'"', shell=True)

    def run_dism_scanhealth(self):
        self.log("تشغيل DISM /ScanHealth...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k DISM /Online /Cleanup-Image /ScanHealth\'"', shell=True)

    def run_dism_restorehealth(self):
        self.log("تشغيل DISM /RestoreHealth...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k DISM /Online /Cleanup-Image /RestoreHealth\'"', shell=True)

    def run_ipconfig(self):
        self.log("تشغيل ipconfig...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k ipconfig\'"', shell=True)

    def run_ipconfig_all(self):
        self.log("تشغيل ipconfig /all...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k ipconfig /all\'"', shell=True)

    def run_ipconfig_release(self):
        self.log("تشغيل ipconfig /release...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k ipconfig /release\'"', shell=True)

    def run_ipconfig_renew(self):
        self.log("تشغيل ipconfig /renew...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k ipconfig /renew\'"', shell=True)

    def run_ping(self):
        self.log("جارٍ تشغيل ping...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k ping 8.8.8.8\'"', shell=True)

    def run_tracert(self):
        self.log("جارٍ تشغيل tracert...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k tracert 8.8.8.8\'"', shell=True)

    def run_netsh_reset(self):
        self.log("تشغيل netsh int ip reset...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k netsh int ip reset\'"', shell=True)

    def run_ipconfig_flushdns(self):
        self.log("تشغيل ipconfig /flushdns...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k ipconfig /flushdns\'"', shell=True)

    def run_chkdsk(self, flag):
        command = f'chkdsk C: {flag}' if flag else 'chkdsk C:'
        self.log(f"جارٍ تنفيذ الأمر: {command}")
        subprocess.run(f'powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k {command}\'"', shell=True)

    # أوامر مستكشف الملفات
    def run_repair_recycle_bin(self):
        self.log("إصلاح سلة المحذوفات...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k rd /s /q C:\\$Recycle.bin\'"', shell=True)

    def run_reset_recycle_bin(self):
        self.log("إعادة تعيين سلة المحذوفات...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k reg delete "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\BitBucket" /f & reg delete "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\BitBucket" /f\'"', shell=True)

    def run_fix_wer(self):
        self.log("إصلاح خطأ WerMgr.exe...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k taskkill /f /im WerMgr.exe & del /f /q %windir%\\System32\\WerMgr.exe\'"', shell=True)

    def run_show_hidden_files(self):
        self.log("إظهار الملفات والمجلدات المخفية...")
        subprocess.run('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" /v Hidden /t REG_DWORD /d 1 /f', shell=True)
        subprocess.run('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" /v ShowSuperHidden /t REG_DWORD /d 1 /f', shell=True)

    def run_fix_thumbnails(self):
        self.log("إصلاح الصور المصغرة...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k del /f /s /q /a %LocalAppData%\\Microsoft\\Windows\\Explorer\\thumbcache_*.db\'"', shell=True)

    def run_fix_cd_drive(self):
        self.log("إصلاح محرك الأقراص المضغوطة...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k reg delete "HKLM\\System\\CurrentControlSet\\Services\\cdrom" /v AutoRun /f & reg add "HKLM\\System\\CurrentControlSet\\Services\\cdrom" /v AutoRun /t REG_DWORD /d 1 /f\'"', shell=True)

    def run_fix_class_not_registered(self):
        self.log("إصلاح الفئة غير مسجلة...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k regsvr32 /i shell32.dll\'"', shell=True)

    # أوامر استكشاف الأخطاء وإصلاحها
    def run_audio_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء الصوت...")
        subprocess.run('msdt.exe -id AudioPlaybackDiagnostic', shell=True)

    def run_audio_recording_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء تسجيل الصوت...")
        subprocess.run('msdt.exe -id AudioRecordingDiagnostic', shell=True)

    def run_power_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء الطاقة...")
        subprocess.run('msdt.exe -id PowerDiagnostic', shell=True)

    def run_printer_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء الطابعة...")
        subprocess.run('msdt.exe -id PrinterDiagnostic', shell=True)

    def run_shared_folders_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء المجلدات المشتركة...")
        subprocess.run('msdt.exe -id WindowsFileSharingDiagnostic', shell=True)

    def run_group_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء المجموعة...")
        subprocess.run('msdt.exe -id HomeGroupDiagnostic', shell=True)

    def run_internet_performance_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء أداء الإنترنت...")
        subprocess.run('msdt.exe -id NetworkDiagnosticsWeb', shell=True)

    def run_internet_safety_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء سلامة الإنترنت...")
        subprocess.run('msdt.exe -id WindowsUpdateDiagnostic', shell=True)

    def run_wmp_settings_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء إعدادات Windows Media Player...")
        subprocess.run('msdt.exe -id WindowsMediaPlayerConfigurationDiagnostic', shell=True)

    def run_wmp_library_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء مكتبة Windows Media Player...")
        subprocess.run('msdt.exe -id WindowsMediaPlayerLibraryDiagnostic', shell=True)

    def run_wmp_dvd_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء Windows Media Player DVD...")
        subprocess.run('msdt.exe -id WindowsMediaPlayerDVDDiagnostic', shell=True)

    def run_internet_connections_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء اتصالات الإنترنت...")
        subprocess.run('msdt.exe -id NetworkDiagnosticsInbound', shell=True)

    def run_hardware_devices_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء الأجهزة والأجهزة...")
        subprocess.run('msdt.exe -id DeviceDiagnostic', shell=True)

    def run_incoming_connections_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء الاتصالات الواردة...")
        subprocess.run('msdt.exe -id NetworkDiagnosticsInbound', shell=True)

    def run_system_maintenance_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء صيانة النظام...")
        subprocess.run('msdt.exe -id MaintenanceDiagnostic', shell=True)

    def run_network_adapter_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء محول الشبكة...")
        subprocess.run('msdt.exe -id NetworkDiagnosticsNetworkAdapter', shell=True)

    def run_windows_update_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء تحديث Windows...")
        subprocess.run('msdt.exe -id WindowsUpdateDiagnostic', shell=True)

    def run_search_indexing_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء البحث والفهرسة...")
        subprocess.run('msdt.exe -id SearchDiagnostic', shell=True)

    def run_mail_calendar_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء تطبيقات البريد والتقويم...")
        subprocess.run('msdt.exe -id WindowsMailCalendarDiagnostic', shell=True)

    def run_settings_app_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء تطبيق الإعدادات...")
        subprocess.run('msdt.exe -id WindowsUpdateDiagnostic', shell=True)

    def run_printer_error_analyzer(self):
        self.log("تشغيل محلل أخطاء الطابعة...")
        subprocess.run('msdt.exe -id PrinterErrorDiagnostic', shell=True)

    def run_windows_store_app_troubleshooter(self):
        self.log("تشغيل مستكشف أخطاء تطبيقات Windows Store...")
        subprocess.run('msdt.exe -id WindowsStoreAppsDiagnostic', shell=True)

    # أوامر الإصلاحات الإضافية
    def run_cache_icon_rebuild(self):
        self.log("إضافة دعم ذاكرة التخزين المؤقت لرمز إعادة البناء...")
        subprocess.run('ie4uinit.exe -show', shell=True)

    def run_enable_hibernation(self):
        self.log("تمكين السبات...")
        subprocess.run('powercfg -h on', shell=True)

    def run_restore_sticky_notes_dialog(self):
        self.log("استعادة مربع الحوار حذف Sticky Notes...")
        subprocess.run('reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\StickyNotes" /v NoteDeleteWarning /f', shell=True)

    def run_fix_aero_snap(self):
        self.log("إصلاح Aero Snap...")
        subprocess.run('reg add "HKCU\\Control Panel\\Desktop" /v WindowArrangementActive /t REG_SZ /d 1 /f', shell=True)

    def run_fix_desktop_icons(self):
        self.log("إصلاح أيقونات سطح المكتب التالفة...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k taskkill /f /im explorer.exe & start explorer.exe\'"', shell=True)

    def run_fix_jump_list(self):
        self.log("إصلاح قائمة قفزة شريط المهام...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k del /f /q %AppData%\\Microsoft\\Windows\\Recent\\AutomaticDestinations\\*\'"', shell=True)

    def run_enable_notifications(self):
        self.log("تمكين الإخطارات...")
        subprocess.run('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\PushNotifications" /v ToastEnabled /t REG_DWORD /d 1 /f', shell=True)

    def run_enable_wsh_access(self):
        self.log("تمكين الوصول إلى Windows Script Host...")
        subprocess.run('reg add "HKLM\\SOFTWARE\\Microsoft\\Windows Script Host\\Settings" /v Enabled /t REG_DWORD /d 1 /f', shell=True)

    def run_fix_office_documents(self):
        self.log("إصلاح مستندات Office...")
        subprocess.run('reg add "HKCU\\Software\\Microsoft\\Office\\16.0\\Common" /v QMEnable /t REG_DWORD /d 1 /f', shell=True)

    def run_fix_recovery_image(self):
        self.log("إصلاح صورة الاسترداد...")
        subprocess.run('reagentc /enable', shell=True)

    def run_fix_wmp_error(self):
        self.log("إصلاح خطأ Windows Media Player...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k regsvr32 /i wmp.dll\'"', shell=True)

    # أوامر الإنترنت والاتصال
    def run_enable_ie_context_menu(self):
        self.log("تمكين قائمة سياق النقر بزر الماوس الأيمن لـ IE...")
        subprocess.run('reg add "HKCU\\Software\\Microsoft\\Internet Explorer\\Main" /v UseNewContextMenu /t REG_DWORD /d 1 /f', shell=True)

    def run_fix_tcp_ip(self):
        self.log("إصلاح مشاكل بروتوكول الإنترنت (TCP/IP)...")
        subprocess.run('netsh int ip reset', shell=True)

    def run_fix_dns(self):
        self.log("إصلاح مشكلة DNS...")
        subprocess.run('ipconfig /flushdns', shell=True)

    def run_clear_windows_update_history(self):
        self.log("مسح محفوظات تحديث Windows...")
        subprocess.run('powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k net stop wuauserv & del /f /q %windir%\\SoftwareDistribution\\* & net start wuauserv\'"', shell=True)

    def run_reset_firewall(self):
        self.log("إعادة تعيين جدار حماية Windows...")
        subprocess.run('netsh advfirewall reset', shell=True)

    def run_reset_ie(self):
        self.log("إعادة تعيين إعدادات IE...")
        subprocess.run('RunDll32.exe InetCpl.cpl,ClearMyTracksByProcess 255', shell=True)

    def run_fix_ie_runtime_errors(self):
        self.log("إصلاح أخطاء وقت التشغيل في Internet Explorer...")
        subprocess.run('reg add "HKCU\\Software\\Microsoft\\Internet Explorer\\Main" /v DisableScriptDebuggerIE /t REG_SZ /d yes /f', shell=True)

    def run_improve_internet_connections(self):
        self.log("تحسين الحد الأقصى للاتصالات...")
        subprocess.run('netsh int tcp set global autotuninglevel=restricted', shell=True)

    def run_fix_missing_internet_options(self):
        self.log("إصلاح خيارات الإنترنت المفقودة...")
        subprocess.run('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f', shell=True)

    def run_fix_winsock(self):
        self.log("إصلاح Winsock...")
        subprocess.run('netsh winsock reset', shell=True)

    def run_enable_telnet(self):
        self.log("تمكين Telnet...")
        subprocess.run('dism /online /Enable-Feature /FeatureName:TelnetClient', shell=True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec())