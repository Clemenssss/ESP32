# ftp_monitor.py — Misst Werte, speichert sie und lädt sie per FTP hoch
import os
import time
import random
import ntptime
import usocket
import gc
import sys
from credentials import get_credentials
from sct import sct_values_get, load_calibration
from machine import Pin, SPI
from ili9341 import Display, color565
from led import LED
from dummy_display import DummyDisplay
from logger import log
# --- Globale Konfiguration & Konstanten ---
FTP_HOST       = "fritz.box"
FTP_DIR        = "/ESP32"
LOCAL_FILE     = "messwerte.csv"
FREE_MIN_BYTES = 100 * 1024  # 100 KB
BLACK          = color565(0, 0, 0)
GREEN          = color565(0, 255, 0)
YELLOW         = color565(255, 255, 0)
WHITE          = color565(255, 255, 255)

# Platzhalter für globale Objekte
_display = None
led = None

def turn_off_and_get_dummy(display_instance, spi_instance):
    """
    Schaltet das Backlight aus und gibt das DummyDisplay zurück.
    Keine Hardware-Zerstörung, kein Löschen von sys.modules.
    """
    print("Schalte um auf Dummy-Display für REPL-Monitor...")
    log("Schalte um auf Dummy-Display für REPL-Monitor...")
    
    try:
        # 1. Bildschirm schwärzen
        display_instance.fill_rectangle(0, 0, 320, 240, BLACK)
    except:
        pass
        
    try:
        # 2. Hintergrundbeleuchtung aus (GPIO 21)
        bl = Pin(21, Pin.OUT)
        bl.value(0)
    except:
        pass
        
    # Wir löschen NUR die lokale Variable des echten Displays,
    # damit der Speicher vom GC freigegeben wird.
    del display_instance
    gc.collect()
    
    # 3. Dummy zurückgeben, damit show_values() brav in die REPL printet
    return DummyDisplay()
def show_values(v1, v2, v3, note,  display=None):
    if display is None:
        display = _display  # Wird beim AUFRUF aufgelöst    
    display.clear(BLACK)
    display.draw_text8x8(10, 20,  "Strommonitor "+note,               WHITE,  BLACK)
    display.draw_text8x8(10, 60,  "L1: {:6.2f} A".format(v1),  GREEN,  BLACK)
    display.draw_text8x8(10, 100, "L2: {:6.2f} A".format(v2),  GREEN,  BLACK)
    display.draw_text8x8(10, 140, "L3: {:6.2f} A".format(v3),  GREEN,  BLACK)
    display.draw_text8x8(10, 190, "Σ:  {:6.2f} A".format(v1+v2+v3), YELLOW, BLACK)

def free_bytes():
    s = os.statvfs('/')
    return s[0] * s[3]

def get_timestamp(offset_hours=2):
    t = time.localtime(time.time() + offset_hours * 3600)
    return "{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )

def append_row(i):
    ts = get_timestamp()
    date_str = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"
    time_str = f"{ts[8:10]}:{ts[10:12]}:{ts[12:14]}"
    
    v1, v2, v3 = sct_values_get()
    note = f"{i} {date_str} {time_str}"
    show_values(v1, v2, v3, note)
    
    line = f"{date_str};{time_str};{v1:.3f};{v2:.3f};{v3:.3f}\n"
    with open(LOCAL_FILE, "a") as f:
        f.write(line.replace(".", ","))
    return line.strip()

def file_size():
    try:
        return os.stat(LOCAL_FILE)[6]
    except:
        return 0

# --- SimpleFTP ---
class SimpleFTP:
    def __init__(self, host, user, password, port=21):
        print('__init__(self, host, user, password, port=21)', host, user, port)
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.sock = None

    def _send(self, cmd):
        self.sock.send((cmd + "\r\n").encode())
        return self._read()

    def _read(self):
        resp = b""
        self.sock.settimeout(3)
        while True:
            try:
                chunk = self.sock.recv(512)
                if not chunk:
                    break
                resp += chunk
            except:
                break
        return resp.decode()

    def connect(self):
        self.sock = usocket.socket()
        addr = usocket.getaddrinfo(self.host, self.port)[0][-1]
        self.sock.connect(addr)
        print("FTP:", self._read().strip())
        print(self._send(f"USER {self.user}").strip())
        print(self._send(f"PASS {self.password}").strip())

    def _pasv(self):
        resp = self._send("PASV")
        nums = resp.split("(")[1].split(")")[0].split(",")
        data_ip   = ".".join(nums[:4])
        data_port = int(nums[4]) * 256 + int(nums[5])
        data_sock = usocket.socket()
        data_sock.connect(usocket.getaddrinfo(data_ip, data_port)[0][-1])
        return data_sock

    def upload(self, local_path, remote_filename):
        time.sleep_ms(200)
        _display.draw_text8x8(10, 200, "vor self._send(", WHITE, BLACK)
        time.sleep_ms(200)
        self._send("TYPE I")
        time.sleep_ms(200)
        _display.draw_text8x8(10, 200, "vor self._pasv()", WHITE, BLACK)
        data_sock = self._pasv()
        time.sleep_ms(200)
        print("STOR:", self._send(f"STOR {remote_filename}").strip())
        with open(local_path, "rb") as f:
            while True:
                chunk = f.read(512)
                if not chunk:
                    break
                data_sock.send(chunk)
        data_sock.close()
        r = self._read()
        print("Transfer:", r.strip())
        return r.startswith("226")

    def cwd(self, path):
        print("CWD:", self._send(f"CWD {path}").strip())

    def disconnect(self):
        try:
            self._send("QUIT")
        except:
            pass
        if self.sock:
            try:
                self.sock.close()
                print("FTP: Control-Socket geschlossen.")
            except:
                pass
            self.sock = None

def upload_and_clear(reason):
    # 1. Sofort alten Müll (vom vorherigen FTP-Lauf) löschen, BEVOR wir irgendwas tun!
    import gc
    gc.collect() 
    _, _, FTP_USER, FTP_PASS = get_credentials('/credentials.txt')
    _display.draw_text8x8(10, 150, "atempt to ts = get_timestamp()", YELLOW, BLACK)    
    # 2. Erst jetzt, im frisch aufgeräumten RAM, den Zeitstempel generieren
    ts = get_timestamp()
    remote_name = f"{ts}_messwerte.csv"
    print(f"\n>>> Trigger: {reason}")
    print(f"    Upload als '{remote_name}' | Dateigröße: {file_size()} B | Frei: {free_bytes()} B")

    # Sicherheitshalber auch hier aufräumen
    gc.collect()

    try:
        ntptime.settime()
    except:
        pass # Falls NTP mal zickt, nicht abstürzen

    # FTP ausführen
    success = False
    try:
        ftp = SimpleFTP(FTP_HOST, FTP_USER, FTP_PASS)
        ftp.connect()
        ftp.cwd(FTP_DIR)
        success = ftp.upload(LOCAL_FILE, remote_name)
        ftp.disconnect()
        
        # Wichtig: Das Objekt explizit zerstören, damit der RAM freigegeben werden kann
        del ftp 
    except Exception as e:
        print("    FTP-Fehler während der Übertragung:", e)

    if success:
        try:
            os.remove(LOCAL_FILE)
            print(f"    Lokal gelöscht. Frei nachher: {free_bytes()} B")
        except:
            pass
    else:
        print("    Upload fehlgeschlagen – lokale Datei bleibt!")

    # Nach dem FTP-Lauf sofort wieder saubermachen für die nächsten Messungen
    gc.collect()
    return success
# --- Hauptfunktion ---
def run():
    # Herausfinden, wer gestartet hat, via Namensraum
    caller = "direkt/main" if __name__ == "__main__" else "programm_starten"
    print('ftptrans caller: '+ caller)
    log('ftptrans caller: '+ caller)
    global _display, led
    
    led = LED()
    
    # Echte Hardware initialisieren
    _spi = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(13))
    _display = Display(_spi, dc=Pin(2), cs=Pin(15), rst=Pin(15),
                       width=320, height=240, rotation=0)
    Pin(21, Pin.OUT).on()
    
    _display.draw_text8x8(10, 20, "ntptime...", WHITE, BLACK)
    ntptime.host = "fritz.box"
    log('ntptime.host = fritz.box, try ntptime.settime')
    try:
        ntptime.settime()
        _display.draw_text8x8(10, 40, "ntptime OK", GREEN, BLACK)
    except Exception as e:
        print("NTP Fehler:", e)
        log("NTP Fehler: "+ e)
        _display.draw_text8x8(10, 40, "NTP Fehler", RED, BLACK)
        
    t = time.localtime()
    last_day = t[2]
    _display.draw_text8x8(10, 60, "init OK   ", GREEN, BLACK)
    
    # Zugriff auf wlan-Objekt abfangen (falls es global in main.py existiert)
    # Wenn nicht verfügbar, erstellen wir ein Dummy-Objekt, um Abstürze zu verhindern
    global wlan
    if 'wlan' not in globals():
        class DummyWlan:
            def isconnected(self): return True
        wlan = DummyWlan()

    print('before switching off display wlan.isconnected()', wlan.isconnected())
    log('before switching off display wlan.isconnected()'+ str(wlan.isconnected()))
    gc.collect()
    print('free memory:', gc.mem_free())
    log('free memory:'+ str(gc.mem_free()))
    t = time.localtime()
    last_day = t[2]
    last_date_str = "{:04d}{:02d}{:02d}".format(t[0], t[1], t[2])

    print(f"Flash total: {os.statvfs('/')[0] * os.statvfs('/')[2] // 1024} KB")
    print(f"Flash frei:  {free_bytes() // 1024} KB")
    log(f"Flash total: {os.statvfs('/')[0] * os.statvfs('/')[2] // 1024} KB")
    log(f"Flash frei:  {free_bytes() // 1024} KB")
    
    # Jetzt auf DummyDisplay umschalten
    log('_display = turn_off_and_get_dummy(_display, _spi)')
    _display = turn_off_and_get_dummy(_display, _spi)
    gc.collect()
    
    i = 0
    load_calibration() 
    
    # --- Hauptschleife ---
    while True:
        gc.collect()    
        print('row = append_row()', i, wlan.isconnected(), 'free memory:', gc.mem_free())
        log('row = append_row() '+ str(i)+' '+ str(wlan.isconnected())+ ' free memory: '+ str(gc.mem_free()))
        
        t = time.localtime(time.time() + 2 * 3600)
        today = t[2]
        
        try:
            row = append_row(i)
            i += 1
        except OSError as e:
            print(f"\n[WARNUNG]: ADS Sensor temporär verloren ({e}). Starte I2C-Reset...")
            log(f"\n[WARNUNG]: ADS Sensor temporär verloren ({e}). Starte I2C-Reset...")
            try:
                load_calibration() 
                print("-> Sensor erfolgreich reinitialisiert!")
            except Exception as reset_err:
                print("-> Reinitialisierung fehlgeschlagen:", reset_err)
            time.sleep(2)
            continue
            
        frei = free_bytes()
        save_interval = 5
        if i % save_interval == 0:
            print(f"[{i:5d}] Datei: {file_size():7d} B | Frei: {frei:7d} B | {get_timestamp()}")

        if frei < FREE_MIN_BYTES:
            upload_and_clear("Speicher < 100 KB")
            last_day = time.localtime()[2]
            last_date_str = "{:04d}{:02d}{:02d}".format(*time.localtime()[:3])

        elif today != last_day:
            upload_and_clear(f"Tageswechsel {last_date_str} → {'{:04d}{:02d}{:02d}'.format(*t[:3])}")
            last_day = today
            last_date_str = "{:04d}{:02d}{:02d}".format(*t[:3])
            
        elif i % save_interval == 0:
            _display.draw_text8x8(10, 200, "vor upload_and_clear(f", WHITE, BLACK)
            reason = f"i % save_interval == 0 {last_date_str} → {'{:04d}{:02d}{:02d}'.format(*t[:3])}"
            log(reason+': '+reason)
            upload_and_clear(reason)

# Einzeltest aus Thonny erlauben
if __name__ == "__main__":
    run()