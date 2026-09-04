import os
import sys
import json
import shutil
import socket
import threading
import winreg
import ctypes
from ctypes import wintypes
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageDraw, ImageTk
import pystray

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# UYGULAMA / MONITOR AYARLARI
# ============================================================

APP_NAME = "Connection Check"
APP_VERSION = "1.0.0"

KONTROL_ARALIGI = 2
BASARISIZLIK_LIMITI = 3

SUNUCULAR = [
    ("1.1.1.1", 443),  # Cloudflare
    ("8.8.8.8", 53),   # Google DNS
    ("9.9.9.9", 53),   # Quad9
]

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# DOSYA YOLLARI
# ============================================================

def uygulama_klasoru():
    """
    Kullanıcının kalıcı dosyalarının tutulacağı klasör.
    EXE olarak çalışırken Connection Check.exe'nin bulunduğu dizindir.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def kaynak_yolu(*parcalar):
    """
    PyInstaller --onefile ile paketlenen salt-okunur kaynaklara erişim.
    EXE çalışırken gömülü dosyalar sys._MEIPASS altında açılır.
    Python ile çalışırken kaynak dosyanın klasörünü kullanır.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_dir, *parcalar)


APP_DIR = uygulama_klasoru()
# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# KULLANICI VERİLERİ
# ============================================================

ORGANIZATION_NAME = "G-SOFTWARE"
DATA_FOLDER_NAME = "Connection Check"

LOCAL_APPDATA = os.environ.get("LOCALAPPDATA")

if not LOCAL_APPDATA:
    # Beklenmedik bir ortamda güvenli geri dönüş.
    LOCAL_APPDATA = os.path.join(
        os.path.expanduser("~"),
        "AppData",
        "Local"
    )

DATA_DIR = os.path.join(
    LOCAL_APPDATA,
    ORGANIZATION_NAME,
    DATA_FOLDER_NAME
)

LOG_DIR = os.path.join(DATA_DIR, "logs")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)


ICON_FILE = kaynak_yolu("icon", "icon.ico")


def eski_verileri_appdata_ya_tasi():
    """
    Önceki geliştirme sürümündeki EXE-yanı ayar/log verilerini
    LocalAppData yapısına bir kez KOPYALAR.

    Güvenlik için kaynak dosyalar silinmez.
    """
    eski_ayar_adaylari = [
        os.path.join(APP_DIR, "ayarlar.json"),
        os.path.join(APP_DIR, "settings.json"),
    ]

    # Yeni settings.json yoksa eski ayar dosyasından kopyala.
    if not os.path.exists(SETTINGS_FILE):
        for eski_ayar in eski_ayar_adaylari:
            if os.path.isfile(eski_ayar):
                try:
                    shutil.copy2(eski_ayar, SETTINGS_FILE)
                    break
                except Exception:
                    pass

    eski_log_klasorleri = [
        os.path.join(APP_DIR, "logs"),
        os.path.join(APP_DIR, "internet_kayitlari"),
    ]

    for eski_log_dir in eski_log_klasorleri:
        if not os.path.isdir(eski_log_dir):
            continue

        try:
            for ad in os.listdir(eski_log_dir):
                kaynak = os.path.join(eski_log_dir, ad)
                hedef = os.path.join(LOG_DIR, ad)

                if (
                    os.path.isfile(kaynak)
                    and ad.lower().endswith(".txt")
                    and not os.path.exists(hedef)
                ):
                    try:
                        shutil.copy2(kaynak, hedef)
                    except Exception:
                        pass
        except Exception:
            pass


eski_verileri_appdata_ya_tasi()

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# AYARLAR
# ============================================================

DEFAULT_SETTINGS = {
    "close_to_tray": True,
    "start_with_windows": False,
    "language": "tr",
}


def ayarlari_yukle():
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        sonuc = DEFAULT_SETTINGS.copy()
        sonuc.update(data)

        if sonuc.get("language") not in ("tr", "en"):
            sonuc["language"] = "tr"

        return sonuc
    except Exception:
        return DEFAULT_SETTINGS.copy()


def ayarlari_kaydet():
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)


settings = ayarlari_yukle()

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# DİL / ÇEVİRİLER
# ============================================================

TRANSLATIONS = {
    "tr": {
        "subtitle": "İnternet bağlantınızı gerçek zamanlı izler ve günlük kesinti kaydı tutar.",
        "settings": "Ayarlar",
        "connection_status": "BAĞLANTI DURUMU",
        "last_action": "Son işlem",
        "today_outages": "BUGÜNKÜ KESİNTİ SAYISI",
        "tracking_status": "TAKİP DURUMU",
        "log_folder": "Kayıt klasörü",
        "start": "Takibi Başlat",
        "stop": "Takibi Durdur",
        "open_logs": "Kayıtları Aç",
        "active": "Aktif",
        "paused": "Durduruldu",
        "starting": "Başlatılıyor...",
        "checking": "●  Kontrol ediliyor...",
        "online": "●  Çevrimiçi — İnternet bağlantısı mevcut",
        "offline": "●  Çevrimdışı — İnternet erişimi yok",
        "tracking_paused": "●  Takip durduruldu",
        "internet_came": "İnternet geldi: {time}",
        "internet_went": "İnternet gitti: {time}",
        "error": "Hata: {error}",
        "footer": "Bu program G-SOFTWARE tarafından yardımcı olması amacıyla kodlanmıştır. (www.g-software.org)",
        "settings_title": "Ayarlar",
        "settings_subtitle": "Connection Check davranışını kişiselleştirin.",
        "close_to_tray": "X işaretine basıldığında sistem tepsisine küçült",
        "close_to_tray_desc": "Pencere kapanır ancak bağlantı takibi arka planda devam eder.",
        "startup": "Bilgisayar açıldığında programı çalıştır ve takibe başla",
        "startup_desc": "Windows oturumu açıldığında Connection Check otomatik başlatılır.",
        "cancel": "İptal",
        "save": "Kaydet",
        "startup_error_title": "Başlangıç Ayarı",
        "startup_error": "Windows başlangıç ayarı değiştirilemedi:\n\n{error}",
        "generic_error": "Hata",
        "tray_open": "Connection Check'i Aç",
        "tray_start": "Takibi Başlat",
        "tray_stop": "Takibi Durdur",
        "tray_exit": "Çıkış",
        "turkish": "Türkçe",
        "english": "English",

        # Günlük log metinleri
        "log_title": "İNTERNET BAĞLANTI KAYDI",
        "log_date_label": "Tarih",
        "log_date_format_info": "Tarih bilgisi GÜN/AY/YIL - SAAT:DAKİKA:SALİSE şeklinde yazılmaktadır.",
        "log_connection_lost": "BAĞLANTI GİTTİ",
        "log_connection_restored": "BAĞLANTI GELDİ",
        "log_outage_duration": "Kesinti süresi",
        "duration_hour": "saat",
        "duration_minute": "dakika",
        "duration_second": "saniye",

        # Günlük sayaç sıfırlama
        "reset_count": "Sayacı Sıfırla",
        "reset_count_title": "Bugünkü Kesinti Sayacını Sıfırla",
        "reset_count_confirm": "Bugünkü kesinti sayısı programda 0 olarak sıfırlanacak. Mevcut log kayıtları silinmeyecek. Yeni kayıtlar şu dosyaya yazılacak:\n\n{filename}\n\nDevam edilsin mi?",
        "reset_offline_title": "Sıfırlama Bekletildi",
        "reset_offline_message": "Aktif bir internet kesintisi devam ederken sayaç sıfırlanamaz. Bağlantı geri geldikten sonra tekrar deneyin.",

        # Tek örnek (single instance)
        "already_running_title": "Connection Check",
        "already_running_message": "Connection Check zaten açık.",
    },
    "en": {
        "subtitle": "Monitors your internet connection in real time and keeps a daily outage log.",
        "settings": "Settings",
        "connection_status": "CONNECTION STATUS",
        "last_action": "Last action",
        "today_outages": "TODAY'S OUTAGES",
        "tracking_status": "MONITORING STATUS",
        "log_folder": "Log folder",
        "start": "Start Monitoring",
        "stop": "Stop Monitoring",
        "open_logs": "Open Logs",
        "active": "Active",
        "paused": "Paused",
        "starting": "Starting...",
        "checking": "●  Checking connection...",
        "online": "●  Online — Internet connection available",
        "offline": "●  Offline — No internet access",
        "tracking_paused": "●  Monitoring paused",
        "internet_came": "Internet restored: {time}",
        "internet_went": "Internet lost: {time}",
        "error": "Error: {error}",
        "footer": "This program was developed by G-SOFTWARE to provide assistance. (www.g-software.org)",
        "settings_title": "Settings",
        "settings_subtitle": "Customize how Connection Check behaves.",
        "close_to_tray": "Minimize to the system tray when the X button is pressed",
        "close_to_tray_desc": "The window closes while connection monitoring continues in the background.",
        "startup": "Run the program and start monitoring when the computer starts",
        "startup_desc": "Connection Check starts automatically when you sign in to Windows.",
        "cancel": "Cancel",
        "save": "Save",
        "startup_error_title": "Startup Setting",
        "startup_error": "The Windows startup setting could not be changed:\n\n{error}",
        "generic_error": "Error",
        "tray_open": "Open Connection Check",
        "tray_start": "Start Monitoring",
        "tray_stop": "Stop Monitoring",
        "tray_exit": "Exit",
        "turkish": "Türkçe",
        "english": "English",

        # Daily log texts
        "log_title": "INTERNET CONNECTION LOG",
        "log_date_label": "Date",
        "log_date_format_info": "Date information is written in DAY/MONTH/YEAR - HOUR:MINUTE:SECOND format.",
        "log_connection_lost": "CONNECTION LOST",
        "log_connection_restored": "CONNECTION RESTORED",
        "log_outage_duration": "Outage duration",
        "duration_hour": "hour",
        "duration_minute": "minute",
        "duration_second": "second",

        # Daily counter reset
        "reset_count": "Reset Count",
        "reset_count_title": "Reset Today's Outage Count",
        "reset_count_confirm": "Today's outage count will be reset to 0 in the program. Existing log records will not be deleted. New records will be written to:\n\n{filename}\n\nDo you want to continue?",
        "reset_offline_title": "Reset Delayed",
        "reset_offline_message": "The counter cannot be reset while an active internet outage is in progress. Try again after the connection is restored.",

        # Single instance
        "already_running_title": "Connection Check",
        "already_running_message": "Connection Check is already running.",
    },
}


def t(key):
    dil = settings.get("language", "tr")
    return TRANSLATIONS.get(dil, TRANSLATIONS["tr"]).get(key, key)


def t_lang(key, language=None):
    """Belirtilen dilde çeviri döndürür; dil verilmezse aktif dili kullanır."""
    dil = language or settings.get("language", "tr")
    return TRANSLATIONS.get(dil, TRANSLATIONS["tr"]).get(key, key)

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# TEK ÖRNEK / SINGLE INSTANCE
# ============================================================

SINGLE_INSTANCE_MUTEX_NAME = r"Local\G-SOFTWARE.ConnectionCheck.SingleInstance"
SINGLE_INSTANCE_HANDLE = None


def tek_ornek_kontrolu():
    """
    Aynı Windows oturumunda Connection Check'in yalnızca bir kez
    çalışmasına izin verir.

    İkinci kez çalıştırılırsa Tkinter açmadan, seçili dilde Windows
    uyarı kutusu gösterilir ve ikinci süreç kapanır.
    """
    global SINGLE_INSTANCE_HANDLE

    try:
        kernel32 = ctypes.windll.kernel32

        kernel32.CreateMutexW.argtypes = [
            ctypes.c_void_p,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        ]
        kernel32.CreateMutexW.restype = wintypes.HANDLE

        kernel32.GetLastError.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.CreateMutexW(
            None,
            False,
            SINGLE_INSTANCE_MUTEX_NAME
        )

        if not handle:
            # Mutex oluşturulamazsa program engellenmeyecek.
            return

        ERROR_ALREADY_EXISTS = 183

        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            try:
                ctypes.windll.user32.MessageBoxW(
                    None,
                    t("already_running_message"),
                    t("already_running_title"),
                    0x00000030 | 0x00000000  # MB_ICONWARNING | MB_OK
                )
            finally:
                kernel32.CloseHandle(handle)

            raise SystemExit(0)

        SINGLE_INSTANCE_HANDLE = handle

    except SystemExit:
        raise
    except Exception:
        SINGLE_INSTANCE_HANDLE = None


def tek_ornek_kilidini_birak():
    global SINGLE_INSTANCE_HANDLE

    if SINGLE_INSTANCE_HANDLE:
        try:
            ctypes.windll.kernel32.CloseHandle(
                SINGLE_INSTANCE_HANDLE
            )
        except Exception:
            pass

        SINGLE_INSTANCE_HANDLE = None


# GUI oluşturulmadan önce kontrol et.
tek_ornek_kontrolu()

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# MODERN TEMA / RENKLER
# ============================================================

BG_MAIN = "#08111f"
BG_CARD = "#0f1b2d"
BG_CARD_2 = "#0c1728"
BG_ELEVATED = "#142238"

TEXT_MAIN = "#f8fafc"
TEXT_MUTED = "#91a4bf"
TEXT_DIM = "#64748b"

BORDER = "#22324a"
BORDER_HOVER = "#365274"

ACCENT = "#22c55e"
ACCENT_BLUE = "#38bdf8"
ACCENT_AMBER = "#f59e0b"
ACCENT_RED = "#ef4444"

BTN_BLUE = "#2563eb"
BTN_BLUE_HOVER = "#3b82f6"
BTN_RED = "#dc2626"
BTN_RED_HOVER = "#ef4444"
BTN_GRAY = "#334155"
BTN_GRAY_HOVER = "#475569"
BTN_DISABLED = "#1c2a3e"

FONT = "Segoe UI"

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# PREMIUM YUVARLATILMIŞ BUTON
# ============================================================

class PremiumButton(tk.Canvas):
    """
    Tkinter Canvas üzerinde PIL ile yüksek çözünürlükte çizilip küçültülen
    anti-aliased, yuvarlatılmış modern buton.
    """

    def __init__(
        self,
        parent,
        text,
        bg,
        hover_bg,
        command,
        width=170,
        height=44,
        radius=11,
        font=(FONT, 10, "bold"),
        canvas_bg=None,
    ):
        self.normal_bg = bg
        self.hover_bg = hover_bg
        self.command = command
        self.button_text = text
        self.state = "normal"
        self.radius = radius
        self.text_font = font
        self.text_color = "#ffffff"
        self.disabled_text_color = "#9aa9be"
        self.current_fill = bg
        self._photo = None
        self._draw_job = None

        # Widget henüz ekrana yerleşmeden set_text() çağrılabilir.
        # Bu yüzden gerçek pencere boyutu 1x1 olsa bile güvenli çizim için
        # istenen başlangıç ölçülerini saklıyoruz.
        self.requested_width = max(20, int(width))
        self.requested_height = max(20, int(height))

        if canvas_bg is None:
            try:
                canvas_bg = parent.cget("bg")
            except Exception:
                canvas_bg = BG_MAIN

        self.canvas_bg = canvas_bg

        super().__init__(
            parent,
            width=width,
            height=height,
            bg=canvas_bg,
            highlightthickness=0,
            bd=0,
            relief="flat",
            cursor="hand2",
        )

        self.bind("<Configure>", self._schedule_draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

        self.after_idle(self._draw)

    def _schedule_draw(self, _event=None):
        if self._draw_job is not None:
            try:
                self.after_cancel(self._draw_job)
            except Exception:
                pass
        self._draw_job = self.after(10, self._draw)

    def _make_background(self, width, height, fill):
        scale = 4
        w = max(1, width * scale)
        h = max(1, height * scale)
        r = max(2, self.radius * scale)

        img = Image.new("RGB", (w, h), self.canvas_bg)
        draw = ImageDraw.Draw(img)

        # Hafif dış çizgi
        outline = BORDER_HOVER if fill != BTN_DISABLED else BORDER

        pad = 1 * scale
        x0 = pad
        y0 = pad
        x1 = max(x0 + 1, w - pad - 1)
        y1 = max(y0 + 1, h - pad - 1)

        draw.rounded_rectangle(
            (x0, y0, x1, y1),
            radius=r,
            fill=fill,
            outline=outline,
            width=1 * scale
        )

        img = img.resize(
            (max(1, width), max(1, height)),
            Image.Resampling.LANCZOS
        )

        return ImageTk.PhotoImage(img)

    def _draw(self):
        self._draw_job = None
        self.delete("all")

        w = max(self.requested_width, self.winfo_width(), 20)
        h = max(self.requested_height, self.winfo_height(), 20)

        if self.state == "disabled":
            fill = BTN_DISABLED
            fg = self.disabled_text_color
        else:
            fill = self.current_fill
            fg = self.text_color

        self._photo = self._make_background(w, h, fill)

        self.create_image(
            0,
            0,
            image=self._photo,
            anchor="nw"
        )

        self.create_text(
            w / 2,
            h / 2,
            text=self.button_text,
            fill=fg,
            font=self.text_font,
            anchor="center"
        )

    def _on_enter(self, _event):
        if self.state == "normal":
            self.current_fill = self.hover_bg
            self._draw()

    def _on_leave(self, _event):
        self.current_fill = self.normal_bg
        self._draw()

    def _on_click(self, _event):
        if self.state == "normal" and self.command:
            self.command()

    def set_text(self, text):
        self.button_text = text
        self._draw()

    def set_state(self, state):
        self.state = state
        self.current_fill = self.normal_bg
        self.configure(
            cursor="arrow" if state == "disabled" else "hand2"
        )
        self._draw()

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# WINDOWS BAŞLANGIÇ AYARI
# ============================================================

def windows_baslangic_ayarla(aktif):
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE
        )

        if aktif:
            if getattr(sys, "frozen", False):
                komut = f'"{sys.executable}"'
            else:
                python_yolu = sys.executable
                script_yolu = os.path.abspath(__file__)
                komut = f'"{python_yolu}" "{script_yolu}"'

            winreg.SetValueEx(
                key,
                APP_NAME,
                0,
                winreg.REG_SZ,
                komut
            )
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass

        winreg.CloseKey(key)
        return True

    except Exception as hata:
        messagebox.showerror(
            t("startup_error_title"),
            t("startup_error").format(error=hata)
        )
        return False

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# TARİH / SAAT / LOG
# ============================================================

def simdi():
    return datetime.now()


def zaman_yaz(dt):
    return dt.strftime("%d/%m/%Y - %H:%M:%S.%f")[:-3]


# Aynı gün içinde sayaç sıfırlandığında logların silinmemesi için aktif günlük log dosyasını ve sürümünü takip eder.
log_state_lock = threading.RLock()
aktif_log_dosyasi = None
aktif_log_tarihi = None


def tarih_anahtari(dt):
    return dt.strftime("%d-%m-%Y")


def gunun_log_dosyalari(dt=None):
    """
    Günün log dosyalarını [(surum, tam_yol), ...] şeklinde döndürür.

    1  -> 04-09-2026.txt
    2  -> 04-09-2026.v2.txt
    3  -> 04-09-2026.v3.txt
    """
    if dt is None:
        dt = simdi()

    tarih = tarih_anahtari(dt)
    bulunanlar = []

    try:
        adlar = os.listdir(LOG_DIR)
    except Exception:
        adlar = []

    ana_ad = f"{tarih}.txt"

    for ad in adlar:
        if ad == ana_ad:
            bulunanlar.append((1, os.path.join(LOG_DIR, ad)))
            continue

        prefix = f"{tarih}.v"
        suffix = ".txt"

        if ad.startswith(prefix) and ad.endswith(suffix):
            surum_metni = ad[len(prefix):-len(suffix)]

            try:
                surum = int(surum_metni)
            except ValueError:
                continue

            if surum >= 2:
                bulunanlar.append((surum, os.path.join(LOG_DIR, ad)))

    bulunanlar.sort(key=lambda item: item[0])
    return bulunanlar


def aktif_logu_sec(dt=None):
    """
    Gün değiştiğinde veya uygulama yeniden açıldığında o günün en son
    sürümlü log dosyasını aktif eder. Dosya yoksa normal tarih.txt kullanılır.
    """
    global aktif_log_dosyasi, aktif_log_tarihi

    if dt is None:
        dt = simdi()

    tarih = tarih_anahtari(dt)

    with log_state_lock:
        if (
            aktif_log_tarihi == tarih
            and aktif_log_dosyasi is not None
        ):
            return aktif_log_dosyasi

        dosyalar = gunun_log_dosyalari(dt)

        if dosyalar:
            aktif_log_dosyasi = dosyalar[-1][1]
        else:
            aktif_log_dosyasi = os.path.join(
                LOG_DIR,
                f"{tarih}.txt"
            )

        aktif_log_tarihi = tarih
        return aktif_log_dosyasi


def sonraki_log_dosyasi(dt=None):
    """
    Sayaç sıfırlaması sonrası kullanılacak bir sonraki günlük dosya adını üretir.
    Örn: 04-09-2026.txt -> 04-09-2026.v2.txt -> 04-09-2026.v3.txt
    """
    if dt is None:
        dt = simdi()

    tarih = tarih_anahtari(dt)
    dosyalar = gunun_log_dosyalari(dt)

    if not dosyalar:
        return os.path.join(LOG_DIR, f"{tarih}.txt")

    sonraki_surum = max(surum for surum, _ in dosyalar) + 1

    return os.path.join(
        LOG_DIR,
        f"{tarih}.v{sonraki_surum}.txt"
    )


def dosya_adi(dt=None):
    if dt is None:
        dt = simdi()

    return aktif_logu_sec(dt)


def dosya_hazirla(dt=None):
    """
    Günlük log dosyasını hazırlar.

    Yeni dosyada başlık ve tarih formatı açıklaması aktif dile göre yazılır.
    Aynı günün dosyası daha önce oluşturulmuşsa, yalnızca üst bilgi bölümü
    aktif dile göre güncellenir; geçmiş olay satırlarına dokunulmaz.
    """
    if dt is None:
        dt = simdi()

    dosya = dosya_adi(dt)
    dil = settings.get("language", "tr")

    baslik = t_lang("log_title", dil)
    tarih_satiri = f'{t_lang("log_date_label", dil)}: {dt.strftime("%d/%m/%Y")}'
    format_bilgisi = t_lang("log_date_format_info", dil)
    ayirici = "=" * 72

    if not os.path.exists(dosya):
        with open(dosya, "w", encoding="utf-8") as f:
            f.write(baslik + "\n")
            f.write(tarih_satiri + "\n")
            f.write(format_bilgisi + "\n")
            f.write(ayirici + "\n\n")
        return dosya

    # Var olan günlük dosyanın yalnızca üst bilgi bölümünü güncelle.
    try:
        with open(dosya, "r", encoding="utf-8") as f:
            icerik = f.read()

        satirlar = icerik.splitlines()

        olay_baslangici = None
        for i, satir in enumerate(satirlar):
            temiz = satir.strip()
            if (
                "BAĞLANTI GİTTİ" in temiz
                or "BAĞLANTI GELDİ" in temiz
                or "CONNECTION LOST" in temiz
                or "CONNECTION RESTORED" in temiz
            ):
                olay_baslangici = i
                break

        if olay_baslangici is None:
            # Başlıktan sonra boş olmayan özel içerik yoksa sadece header tutulur.
            olay_satirlari = []
        else:
            olay_satirlari = satirlar[olay_baslangici:]

        yeni_satirlar = [
            baslik,
            tarih_satiri,
            format_bilgisi,
            ayirici,
            "",
        ]

        if olay_satirlari:
            yeni_satirlar.extend(olay_satirlari)

        yeni_icerik = "\n".join(yeni_satirlar).rstrip() + "\n"

        if yeni_icerik != icerik:
            with open(dosya, "w", encoding="utf-8") as f:
                f.write(yeni_icerik)

    except Exception:
        # Header güncellenemese bile takip/log yazımı devam eder.
        pass

    return dosya


def kayit_yaz(metin, dt=None):
    if dt is None:
        dt = simdi()

    dosya = dosya_hazirla(dt)

    with open(dosya, "a", encoding="utf-8") as f:
        f.write(metin + "\n")


def gunluk_kesinti_sayisi(dt=None):
    if dt is None:
        dt = simdi()

    dosya = dosya_adi(dt)

    if not os.path.exists(dosya):
        return 0

    try:
        with open(dosya, "r", encoding="utf-8") as f:
            icerik = f.read()

        return (
            icerik.count("BAĞLANTI GİTTİ")
            + icerik.count("CONNECTION LOST")
        )
    except Exception:
        return 0


def sure_yaz(toplam_saniye, language=None):
    toplam_saniye = int(toplam_saniye)
    dil = language or settings.get("language", "tr")

    saat = toplam_saniye // 3600
    dakika = (toplam_saniye % 3600) // 60
    saniye = toplam_saniye % 60

    parcalar = []

    if dil == "en":
        if saat > 0:
            parcalar.append(
                f"{saat} {t_lang('duration_hour', dil)}"
                + ("" if saat == 1 else "s")
            )

        if dakika > 0:
            parcalar.append(
                f"{dakika} {t_lang('duration_minute', dil)}"
                + ("" if dakika == 1 else "s")
            )

        parcalar.append(
            f"{saniye} {t_lang('duration_second', dil)}"
            + ("" if saniye == 1 else "s")
        )
    else:
        if saat > 0:
            parcalar.append(f"{saat} {t_lang('duration_hour', dil)}")

        if dakika > 0:
            parcalar.append(f"{dakika} {t_lang('duration_minute', dil)}")

        parcalar.append(f"{saniye} {t_lang('duration_second', dil)}")

    return " ".join(parcalar)

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# İNTERNET KONTROLÜ
# ============================================================

def internet_kontrol():
    for ip, port in SUNUCULAR:
        try:
            baglanti = socket.create_connection((ip, port), timeout=2)
            baglanti.close()
            return True
        except OSError:
            continue

    return False

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# ANA PENCERE
# ============================================================

root = tk.Tk()
root.title(APP_NAME)
root.configure(bg=BG_MAIN)


def windows_calisma_alani():
    """
    Windows görev çubuğunu hariç tutarak kullanılabilir masaüstü alanını döndürür.
    Dönüş: left, top, right, bottom
    """
    try:
        rect = wintypes.RECT()
        SPI_GETWORKAREA = 0x0030

        sonuc = ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETWORKAREA,
            0,
            ctypes.byref(rect),
            0
        )

        if sonuc:
            return rect.left, rect.top, rect.right, rect.bottom

    except Exception:
        pass

    return (
        0,
        0,
        root.winfo_screenwidth(),
        root.winfo_screenheight()
    )


root.update_idletasks()

work_left, work_top, work_right, work_bottom = windows_calisma_alani()
work_width = max(1, work_right - work_left)
work_height = max(1, work_bottom - work_top)

# Normal ekranda 640x710 kullan; küçük ekranlarda görev çubuğunun üstüne taşmayı engeller.
window_width = min(640, max(540, work_width - 40))
window_height = min(710, max(500, work_height - 70))

window_x = work_left + max(0, (work_width - window_width) // 2)
window_y = work_top + max(0, (work_height - window_height) // 2)

root.geometry(
    f"{window_width}x{window_height}+{window_x}+{window_y}"
)

# Küçük yüksekliklerde içerik kaydırılır.
root.minsize(
    min(540, window_width),
    min(500, window_height)
)
root.resizable(True, True)

style = ttk.Style()
style.theme_use("clam")

try:
    if os.path.exists(ICON_FILE):
        root.iconbitmap(ICON_FILE)
except Exception:
    pass

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# DURUM DEĞİŞKENLERİ
# ============================================================

takip_aktif = False
takip_thread = None
takip_stop_event = None

internet_var = None
basarisiz_kontrol = 0
ilk_basarisizlik_zamani = None
kesinti_baslangici = None

aktif_tarih = None
kesinti_numarasi = 0
uygulama_kapaniyor = False

durum_anahtari = "starting"
takip_anahtari = "starting"

son_olay_turu = None
son_olay_degeri = "-"

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# GUI STRING DEĞİŞKENLERİ
# ============================================================

durum_var = tk.StringVar(value="")
son_islem_var = tk.StringVar(value="-")
kesinti_var = tk.StringVar(value="0")
takip_var = tk.StringVar(value="")

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# GUI YARDIMCILARI
# ============================================================

def gui_cagir(fonksiyon, *args):
    try:
        root.after(0, lambda: fonksiyon(*args))
    except Exception:
        pass


def durum_rengi():
    if durum_anahtari == "online":
        return ACCENT
    if durum_anahtari == "offline":
        return ACCENT_RED
    if durum_anahtari == "paused":
        return TEXT_MUTED
    if durum_anahtari in ("checking", "starting"):
        return ACCENT_BLUE
    return TEXT_MAIN


def durum_render():
    durum_var.set(t(durum_anahtari))
    if "durum_label" in globals():
        durum_label.config(fg=durum_rengi())


def takip_render():
    takip_var.set(t(takip_anahtari))

    if "takip_durum_label" in globals():
        if takip_anahtari == "active":
            takip_durum_label.config(fg=ACCENT)
        elif takip_anahtari == "paused":
            takip_durum_label.config(fg=TEXT_MUTED)
        else:
            takip_durum_label.config(fg=ACCENT_BLUE)


def son_islem_render():
    if son_olay_turu == "came":
        son_islem_var.set(t("internet_came").format(time=son_olay_degeri))
    elif son_olay_turu == "went":
        son_islem_var.set(t("internet_went").format(time=son_olay_degeri))
    elif son_olay_turu == "error":
        son_islem_var.set(t("error").format(error=son_olay_degeri))
    else:
        son_islem_var.set(son_olay_degeri)


def durum_ayarla(anahtar):
    global durum_anahtari
    durum_anahtari = anahtar
    durum_render()


def takip_ayarla(anahtar):
    global takip_anahtari
    takip_anahtari = anahtar
    takip_render()


def son_islem_ayarla(tur, deger):
    global son_olay_turu, son_olay_degeri
    son_olay_turu = tur
    son_olay_degeri = deger
    son_islem_render()


def kesinti_sayisi_guncelle(sayi):
    kesinti_var.set(str(sayi))


def gunluk_sayaci_sifirla():
    """
    Ekrandaki bugünkü kesinti sayacını sıfırlar.
    Eski loglar kesinlikle silinmez. Yeni kayıtlar aynı gün için
    .v2, .v3 ... şeklinde yeni bir log dosyasına yazılır.
    """
    global kesinti_numarasi
    global aktif_log_dosyasi
    global aktif_log_tarihi

    # Devam eden bir kesintiyi iki farklı log dosyasına bölmemek için
    # bağlantı geri gelene kadar sıfırlamaya izin verilmez.
    if internet_var is False:
        messagebox.showwarning(
            t("reset_offline_title"),
            t("reset_offline_message")
        )
        return

    su_an = simdi()

    with log_state_lock:
        # Aktif dosyanın mevcut olduğundan emin ol.
        dosya_hazirla(su_an)

        yeni_dosya = sonraki_log_dosyasi(su_an)

        onay = messagebox.askyesno(
            t("reset_count_title"),
            t("reset_count_confirm").format(
                filename=os.path.basename(yeni_dosya)
            )
        )

        if not onay:
            return

        aktif_log_dosyasi = yeni_dosya
        aktif_log_tarihi = tarih_anahtari(su_an)

        kesinti_numarasi = 0
        kesinti_sayisi_guncelle(0)

        # Yeni sürümün başlığını hemen oluştur.
        # Uygulama kapanıp yeniden açılsa da sıfırlama durumu korunur.
        dosya_hazirla(su_an)

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# TAKİP MOTORU
# ============================================================

def takip_motoru(local_stop_event):
    global internet_var
    global basarisiz_kontrol
    global ilk_basarisizlik_zamani
    global kesinti_baslangici
    global aktif_tarih
    global kesinti_numarasi
    global takip_aktif
    global takip_stop_event

    while not local_stop_event.is_set():
        try:
            su_an = simdi()
            bugun = su_an.strftime("%d-%m-%Y")

            if aktif_tarih != bugun:
                aktif_tarih = bugun

                with log_state_lock:
                    aktif_logu_sec(su_an)
                    dosya_hazirla(su_an)
                    kesinti_numarasi = gunluk_kesinti_sayisi(su_an)

                gui_cagir(kesinti_sayisi_guncelle, kesinti_numarasi)

            baglanti_var = internet_kontrol()

            if baglanti_var:
                basarisiz_kontrol = 0
                ilk_basarisizlik_zamani = None

                if internet_var is None:
                    internet_var = True
                    gui_cagir(durum_ayarla, "online")
                    gui_cagir(son_islem_ayarla, None, zaman_yaz(su_an))

                elif internet_var is False:
                    internet_var = True
                    gelis_zamani = simdi()

                    olay_dili = settings.get("language", "tr")

                    kayit_yaz(
                        f"[{kesinti_numarasi}] "
                        f"{t_lang('log_connection_restored', olay_dili)} : "
                        f"{zaman_yaz(gelis_zamani)}",
                        gelis_zamani
                    )

                    gui_cagir(durum_ayarla, "online")
                    gui_cagir(
                        son_islem_ayarla,
                        "came",
                        zaman_yaz(gelis_zamani)
                    )

                    if kesinti_baslangici is not None:
                        kesinti_suresi = (
                            gelis_zamani - kesinti_baslangici
                        ).total_seconds()

                        kayit_yaz(
                            f"    {t_lang('log_outage_duration', olay_dili)}  : "
                            f"{sure_yaz(kesinti_suresi, olay_dili)}\n",
                            gelis_zamani
                        )

                    kesinti_baslangici = None

            else:
                if basarisiz_kontrol == 0:
                    ilk_basarisizlik_zamani = simdi()

                basarisiz_kontrol += 1

                if (
                    basarisiz_kontrol >= BASARISIZLIK_LIMITI
                    and internet_var is not False
                ):
                    internet_var = False
                    kesinti_baslangici = ilk_basarisizlik_zamani

                    olay_dili = settings.get("language", "tr")

                    with log_state_lock:
                        kesinti_numarasi += 1
                        olay_numarasi = kesinti_numarasi

                        kayit_yaz(
                            f"\n[{olay_numarasi}] "
                            f"{t_lang('log_connection_lost', olay_dili)} : "
                            f"{zaman_yaz(kesinti_baslangici)}",
                            kesinti_baslangici
                        )

                    gui_cagir(durum_ayarla, "offline")
                    gui_cagir(
                        son_islem_ayarla,
                        "went",
                        zaman_yaz(kesinti_baslangici)
                    )
                    gui_cagir(
                        kesinti_sayisi_guncelle,
                        olay_numarasi
                    )

            local_stop_event.wait(KONTROL_ARALIGI)

        except Exception as hata:
            gui_cagir(son_islem_ayarla, "error", str(hata))
            local_stop_event.wait(2)

    if takip_stop_event is local_stop_event:
        takip_aktif = False


def takibi_baslat():
    global takip_aktif
    global takip_thread
    global takip_stop_event
    global internet_var
    global basarisiz_kontrol
    global ilk_basarisizlik_zamani

    if takip_aktif:
        return

    takip_aktif = True
    internet_var = None
    basarisiz_kontrol = 0
    ilk_basarisizlik_zamani = None

    takip_stop_event = threading.Event()

    takip_ayarla("active")
    durum_ayarla("checking")

    baslat_btn.set_state("disabled")
    durdur_btn.set_state("normal")

    takip_thread = threading.Thread(
        target=takip_motoru,
        args=(takip_stop_event,),
        daemon=True
    )
    takip_thread.start()


def takibi_durdur():
    global takip_aktif

    if not takip_aktif:
        return

    if takip_stop_event is not None:
        takip_stop_event.set()

    takip_aktif = False

    takip_ayarla("paused")
    durum_ayarla("paused")

    baslat_btn.set_state("normal")
    durdur_btn.set_state("disabled")

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# LOG KLASÖRÜ
# ============================================================

def log_klasorunu_ac():
    """
    Her zaman LocalAppData içindeki gerçek log klasörünü açar.
    """
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        os.startfile(os.path.normpath(LOG_DIR))
    except Exception as hata:
        messagebox.showerror(t("generic_error"), str(hata))

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# AYARLAR PENCERESİ
# ============================================================

def ayarlar_penceresi():
    pencere = tk.Toplevel(root)
    pencere.title(t("settings_title"))
    pencere.geometry("555x380")
    pencere.resizable(False, False)
    pencere.configure(bg=BG_MAIN)

    try:
        if os.path.exists(ICON_FILE):
            pencere.iconbitmap(ICON_FILE)
    except Exception:
        pass

    pencere.transient(root)
    pencere.grab_set()

    wrapper = tk.Frame(pencere, bg=BG_MAIN)
    wrapper.pack(fill="both", expand=True, padx=24, pady=22)

    tk.Label(
        wrapper,
        text=t("settings_title"),
        bg=BG_MAIN,
        fg=TEXT_MAIN,
        font=(FONT, 22, "bold")
    ).pack(anchor="w")

    tk.Label(
        wrapper,
        text=t("settings_subtitle"),
        bg=BG_MAIN,
        fg=TEXT_MUTED,
        font=(FONT, 10)
    ).pack(anchor="w", pady=(4, 18))

    card = tk.Frame(
        wrapper,
        bg=BG_CARD,
        highlightthickness=1,
        highlightbackground=BORDER,
        bd=0
    )
    card.pack(fill="x")

    accent_line = tk.Frame(card, bg=ACCENT_BLUE, height=2)
    accent_line.pack(fill="x")

    card_inner = tk.Frame(card, bg=BG_CARD)
    card_inner.pack(fill="x", padx=18, pady=14)

    close_to_tray_var = tk.BooleanVar(
        value=settings["close_to_tray"]
    )
    startup_var = tk.BooleanVar(
        value=settings["start_with_windows"]
    )

    def modern_checkbutton(parent, text, variable):
        return tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            onvalue=True,
            offvalue=False,
            bg=BG_CARD,
            fg=TEXT_MAIN,
            activebackground=BG_CARD,
            activeforeground=TEXT_MAIN,
            selectcolor=BG_ELEVATED,
            font=(FONT, 10),
            cursor="hand2",
            anchor="w",
            justify="left",
            wraplength=475,
            bd=0,
            highlightthickness=0,
            padx=2,
            pady=7
        )

    close_checkbox = modern_checkbutton(
        card_inner,
        t("close_to_tray"),
        close_to_tray_var
    )
    close_checkbox.pack(anchor="w", fill="x")

    tk.Label(
        card_inner,
        text=t("close_to_tray_desc"),
        bg=BG_CARD,
        fg=TEXT_MUTED,
        font=(FONT, 9),
        wraplength=465,
        justify="left"
    ).pack(anchor="w", padx=(22, 0), pady=(0, 9))

    startup_checkbox = modern_checkbutton(
        card_inner,
        t("startup"),
        startup_var
    )
    startup_checkbox.pack(anchor="w", fill="x")

    tk.Label(
        card_inner,
        text=t("startup_desc"),
        bg=BG_CARD,
        fg=TEXT_MUTED,
        font=(FONT, 9),
        wraplength=465,
        justify="left"
    ).pack(anchor="w", padx=(22, 0), pady=(0, 2))

    buttons = tk.Frame(wrapper, bg=BG_MAIN)
    buttons.pack(fill="x", pady=(18, 0))

    def kaydet():
        yeni_startup = startup_var.get()

        if windows_baslangic_ayarla(yeni_startup):
            settings["close_to_tray"] = close_to_tray_var.get()
            settings["start_with_windows"] = yeni_startup
            ayarlari_kaydet()
            pencere.destroy()

    cancel_btn = PremiumButton(
        buttons,
        t("cancel"),
        BTN_GRAY,
        BTN_GRAY_HOVER,
        pencere.destroy,
        width=110,
        height=42,
        canvas_bg=BG_MAIN
    )
    cancel_btn.pack(side="right", padx=(8, 0))

    save_btn = PremiumButton(
        buttons,
        t("save"),
        BTN_BLUE,
        BTN_BLUE_HOVER,
        kaydet,
        width=120,
        height=42,
        canvas_bg=BG_MAIN
    )
    save_btn.pack(side="right")

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# SİSTEM TEPSİSİ
# ============================================================

tray_icon = None


def tray_resmi_olustur():
    if os.path.exists(ICON_FILE):
        try:
            return Image.open(ICON_FILE)
        except Exception:
            pass

    image = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), outline="black", width=5)
    draw.ellipse((27, 27, 37, 37), fill="black")
    return image


def pencereyi_goster(icon=None, item=None):
    root.after(0, root.deiconify)
    root.after(0, root.lift)
    root.after(100, root.focus_force)


def tray_baslat():
    global tray_icon

    if tray_icon is not None:
        return

    menu = pystray.Menu(
        pystray.MenuItem(
            t("tray_open"),
            pencereyi_goster,
            default=True
        ),
        pystray.MenuItem(
            t("tray_start"),
            lambda icon, item: root.after(0, takibi_baslat)
        ),
        pystray.MenuItem(
            t("tray_stop"),
            lambda icon, item: root.after(0, takibi_durdur)
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            t("tray_exit"),
            lambda icon, item: root.after(0, programdan_cik)
        )
    )

    tray_icon = pystray.Icon(
        APP_NAME,
        tray_resmi_olustur(),
        APP_NAME,
        menu
    )

    threading.Thread(
        target=tray_icon.run,
        daemon=True
    ).start()


def tray_yenile():
    global tray_icon

    if tray_icon is None:
        return

    try:
        tray_icon.stop()
    except Exception:
        pass

    tray_icon = None
    root.after(200, tray_baslat)

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# PENCERE KAPATMA / PROGRAMDAN ÇIKIŞ
# ============================================================

def pencere_kapat():
    if settings["close_to_tray"]:
        root.withdraw()
    else:
        programdan_cik()


def programdan_cik():
    global uygulama_kapaniyor

    if uygulama_kapaniyor:
        return

    uygulama_kapaniyor = True

    if takip_stop_event is not None:
        takip_stop_event.set()

    try:
        if tray_icon is not None:
            tray_icon.stop()
    except Exception:
        pass

    tek_ornek_kilidini_birak()
    root.destroy()


root.protocol("WM_DELETE_WINDOW", pencere_kapat)

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# DİL DEĞİŞTİRME
# ============================================================

def dili_degistir(dil):
    if dil not in ("tr", "en"):
        return

    settings["language"] = dil
    ayarlari_kaydet()

    # Bugünkü log dosyasının yalnızca üst bilgi bölümünü yeni dile geçir.
    # Önceden kaydedilmiş olay satırları değiştirmez.
    try:
        dosya_hazirla(simdi())
    except Exception:
        pass

    dili_uygula()
    tray_yenile()


def dil_menusu_ac():
    menu = tk.Menu(
        root,
        tearoff=0,
        bg=BG_ELEVATED,
        fg=TEXT_MAIN,
        activebackground=BTN_BLUE,
        activeforeground="#ffffff",
        bd=0,
        relief="flat",
        font=(FONT, 10)
    )

    menu.add_command(
        label="✓  Türkçe" if settings["language"] == "tr" else "   Türkçe",
        command=lambda: dili_degistir("tr")
    )
    menu.add_command(
        label="✓  English" if settings["language"] == "en" else "   English",
        command=lambda: dili_degistir("en")
    )

    x = lang_btn.winfo_rootx()
    y = lang_btn.winfo_rooty() + lang_btn.winfo_height() + 4

    try:
        menu.tk_popup(x, y)
    finally:
        menu.grab_release()

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# ARAYÜZ
# ============================================================

# Küçük ekranlarda içeriğin alttan kesilmemesi için kaydırılabilir ana alan.
scroll_shell = tk.Frame(root, bg=BG_MAIN)
scroll_shell.pack(fill="both", expand=True)

main_canvas = tk.Canvas(
    scroll_shell,
    bg=BG_MAIN,
    highlightthickness=0,
    bd=0
)

main_scrollbar = tk.Scrollbar(
    scroll_shell,
    orient="vertical",
    command=main_canvas.yview,
    bg=BG_ELEVATED,
    activebackground=BTN_GRAY_HOVER,
    troughcolor=BG_MAIN,
    relief="flat",
    bd=0,
    width=10
)

main_canvas.configure(yscrollcommand=main_scrollbar.set)

main_scrollbar.pack(side="right", fill="y")
main_canvas.pack(side="left", fill="both", expand=True)

ana_frame = tk.Frame(main_canvas, bg=BG_MAIN)

ana_window = main_canvas.create_window(
    (0, 0),
    window=ana_frame,
    anchor="nw"
)


def ana_frame_scrollregion_guncelle(_event=None):
    main_canvas.configure(
        scrollregion=main_canvas.bbox("all")
    )


def ana_frame_genislik_guncelle(event):
    # İçerik her zaman görünür Canvas genişliğine uysun.
    main_canvas.itemconfigure(
        ana_window,
        width=max(1, event.width)
    )


def mousewheel_scroll(event):
    bbox = main_canvas.bbox("all")

    if not bbox:
        return

    content_height = bbox[3] - bbox[1]

    if content_height <= main_canvas.winfo_height():
        return

    delta = int(-1 * (event.delta / 120))

    if delta == 0:
        delta = -1 if event.delta > 0 else 1

    main_canvas.yview_scroll(delta, "units")


ana_frame.bind("<Configure>", ana_frame_scrollregion_guncelle)
main_canvas.bind("<Configure>", ana_frame_genislik_guncelle)
root.bind_all("<MouseWheel>", mousewheel_scroll)

# Ana içeriğin kendi yatay/dikey boşlukları
content_frame = tk.Frame(ana_frame, bg=BG_MAIN)
content_frame.pack(fill="both", expand=True, padx=22, pady=(20, 14))

# Bundan sonraki mevcut arayüz content_frame içinde oluşturulur.
ana_frame = content_frame

# Üst başlık
header_frame = tk.Frame(ana_frame, bg=BG_MAIN)
header_frame.pack(fill="x", pady=(0, 16))

header_top = tk.Frame(header_frame, bg=BG_MAIN)
header_top.pack(fill="x")

title_group = tk.Frame(header_top, bg=BG_MAIN)
title_group.pack(side="left", anchor="w")

title_label = tk.Label(
    title_group,
    text="Connection Check",
    bg=BG_MAIN,
    fg=TEXT_MAIN,
    font=(FONT, 25, "bold")
)
title_label.pack(anchor="w")

version_label = tk.Label(
    title_group,
    text=f"v{APP_VERSION}",
    bg=BG_MAIN,
    fg=TEXT_DIM,
    font=(FONT, 8)
)
version_label.pack(anchor="w", pady=(1, 0))

header_actions = tk.Frame(header_top, bg=BG_MAIN)
header_actions.pack(side="right", anchor="e")

lang_btn = PremiumButton(
    header_actions,
    "TR",
    BG_ELEVATED,
    BTN_GRAY_HOVER,
    dil_menusu_ac,
    width=72,
    height=42,
    canvas_bg=BG_MAIN
)
lang_btn.pack(side="left", padx=(0, 8))

ayar_btn = PremiumButton(
    header_actions,
    "",
    BTN_GRAY,
    BTN_GRAY_HOVER,
    ayarlar_penceresi,
    width=122,
    height=42,
    canvas_bg=BG_MAIN
)
ayar_btn.pack(side="left")

subtitle_label = tk.Label(
    header_frame,
    text="",
    bg=BG_MAIN,
    fg=TEXT_MUTED,
    font=(FONT, 9),
    justify="left",
    anchor="w"
)
subtitle_label.pack(fill="x", anchor="w", pady=(7, 0))

separator = tk.Frame(ana_frame, bg=BORDER_HOVER, height=1)
separator.pack(fill="x", pady=(0, 16))

# Bağlantı durumu kartı
status_card = tk.Frame(
    ana_frame,
    bg=BG_CARD,
    highlightthickness=1,
    highlightbackground=BORDER,
    bd=0
)
status_card.pack(fill="x", pady=(0, 14))

status_accent = tk.Frame(status_card, bg=ACCENT_BLUE, height=2)
status_accent.pack(fill="x")

status_inner = tk.Frame(status_card, bg=BG_CARD)
status_inner.pack(fill="x", padx=20, pady=(16, 18))

status_title = tk.Label(
    status_inner,
    text="",
    bg=BG_CARD,
    fg="#a9bce0",
    font=(FONT, 9, "bold")
)
status_title.pack(anchor="w")

durum_label = tk.Label(
    status_inner,
    textvariable=durum_var,
    bg=BG_CARD,
    fg=TEXT_MAIN,
    font=(FONT, 17, "bold")
)
durum_label.pack(anchor="w", pady=(9, 4))

son_islem_baslik = tk.Label(
    status_inner,
    text="",
    bg=BG_CARD,
    fg=TEXT_MUTED,
    font=(FONT, 9)
)
son_islem_baslik.pack(anchor="w", pady=(9, 0))

son_islem_label = tk.Label(
    status_inner,
    textvariable=son_islem_var,
    bg=BG_CARD,
    fg=TEXT_MAIN,
    font=(FONT, 10)
)
son_islem_label.pack(anchor="w", pady=(4, 0))

# İstatistik kartları
stats_frame = tk.Frame(ana_frame, bg=BG_MAIN)
stats_frame.pack(fill="x", pady=(0, 14))

left_card = tk.Frame(
    stats_frame,
    bg=BG_CARD,
    highlightthickness=1,
    highlightbackground=BORDER,
    bd=0
)
left_card.pack(side="left", fill="both", expand=True, padx=(0, 7))

left_inner = tk.Frame(left_card, bg=BG_CARD)
left_inner.pack(fill="both", expand=True, padx=20, pady=16)

kesinti_baslik = tk.Label(
    left_inner,
    text="",
    bg=BG_CARD,
    fg="#a9bce0",
    font=(FONT, 9, "bold")
)
kesinti_baslik.pack(anchor="w")

kesinti_deger_label = tk.Label(
    left_inner,
    textvariable=kesinti_var,
    bg=BG_CARD,
    fg=ACCENT_AMBER,
    font=(FONT, 25, "bold")
)
kesinti_deger_label.pack(anchor="w", pady=(8, 6))

reset_count_btn = PremiumButton(
    left_inner,
    "",
    "#92400e",
    "#b45309",
    gunluk_sayaci_sifirla,
    width=145,
    height=32,
    radius=8,
    font=(FONT, 9, "bold"),
    canvas_bg=BG_CARD
)
reset_count_btn.pack(anchor="w", pady=(2, 0))

right_card = tk.Frame(
    stats_frame,
    bg=BG_CARD,
    highlightthickness=1,
    highlightbackground=BORDER,
    bd=0
)
right_card.pack(side="left", fill="both", expand=True, padx=(7, 0))

right_inner = tk.Frame(right_card, bg=BG_CARD)
right_inner.pack(fill="both", expand=True, padx=20, pady=16)

takip_baslik = tk.Label(
    right_inner,
    text="",
    bg=BG_CARD,
    fg="#a9bce0",
    font=(FONT, 9, "bold")
)
takip_baslik.pack(anchor="w")

takip_durum_label = tk.Label(
    right_inner,
    textvariable=takip_var,
    bg=BG_CARD,
    fg=ACCENT_BLUE,
    font=(FONT, 18, "bold")
)
takip_durum_label.pack(anchor="w", pady=(8, 0))

# Kayıt klasörü kartı
info_card = tk.Frame(
    ana_frame,
    bg=BG_CARD_2,
    highlightthickness=1,
    highlightbackground=BORDER,
    bd=0
)
info_card.pack(fill="x", pady=(0, 14))

info_inner = tk.Frame(info_card, bg=BG_CARD_2)
info_inner.pack(fill="x", padx=20, pady=13)

log_baslik = tk.Label(
    info_inner,
    text="",
    bg=BG_CARD_2,
    fg="#a9bce0",
    font=(FONT, 9, "bold")
)
log_baslik.pack(anchor="w")

log_path_var = tk.StringVar(
    value=os.path.normpath(LOG_DIR)
)

tk.Label(
    info_inner,
    textvariable=log_path_var,
    bg=BG_CARD_2,
    fg=TEXT_MAIN,
    font=("Consolas", 9),
    anchor="w",
    justify="left"
).pack(anchor="w", pady=(5, 0))

# Ana butonlar
button_frame = tk.Frame(ana_frame, bg=BG_MAIN)
button_frame.pack(fill="x")

baslat_btn = PremiumButton(
    button_frame,
    "",
    BTN_BLUE,
    BTN_BLUE_HOVER,
    takibi_baslat,
    width=180,
    height=44,
    canvas_bg=BG_MAIN
)
baslat_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

durdur_btn = PremiumButton(
    button_frame,
    "",
    BTN_RED,
    BTN_RED_HOVER,
    takibi_durdur,
    width=180,
    height=44,
    canvas_bg=BG_MAIN
)
durdur_btn.pack(side="left", fill="x", expand=True, padx=6)

log_btn = PremiumButton(
    button_frame,
    "",
    BTN_GRAY,
    BTN_GRAY_HOVER,
    log_klasorunu_ac,
    width=180,
    height=44,
    canvas_bg=BG_MAIN
)
log_btn.pack(side="left", fill="x", expand=True, padx=(6, 0))

# Alt bilgi / G-SOFTWARE
footer_frame = tk.Frame(ana_frame, bg=BG_MAIN)
footer_frame.pack(fill="x", pady=(14, 0))

footer_line = tk.Frame(footer_frame, bg=BORDER, height=1)
footer_line.pack(fill="x", pady=(0, 8))

footer_label = tk.Label(
    footer_frame,
    text="",
    bg=BG_MAIN,
    fg=TEXT_DIM,
    font=(FONT, 8),
    justify="center"
)
footer_label.pack()

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# DİLİ ARAYÜZE UYGULA
# ============================================================

def dili_uygula():
    subtitle_label.config(text=t("subtitle"))
    ayar_btn.set_text(t("settings"))

    lang_btn.set_text(
        "TR" if settings["language"] == "tr" else "EN"
    )

    status_title.config(text=t("connection_status"))
    son_islem_baslik.config(text=t("last_action"))
    kesinti_baslik.config(text=t("today_outages"))
    takip_baslik.config(text=t("tracking_status"))
    log_baslik.config(text=t("log_folder"))
    reset_count_btn.set_text(t("reset_count"))

    baslat_btn.set_text(t("start"))
    durdur_btn.set_text(t("stop"))
    log_btn.set_text(t("open_logs"))

    footer_label.config(text=t("footer"))

    durum_render()
    takip_render()
    son_islem_render()

# G-SOFTWARE TARAFINDAN KODLANMIŞTIR. (www.g-software.org)
# DEVELOPED BY G-SOFTWARE. (www.g-software.org)
# ============================================================
# BAŞLANGIÇ
# ============================================================

dili_uygula()

# Program ilk açıldığında Stop aktif, Start pasif
baslat_btn.set_state("disabled")
durdur_btn.set_state("normal")

# Önce pencerenin çizilmesine fırsat ver; ardından arka plan servislerini başlat.
root.after(50, tray_baslat)

# Program açıldığında takip otomatik başlar.
root.after(100, takibi_baslat)

root.mainloop()
