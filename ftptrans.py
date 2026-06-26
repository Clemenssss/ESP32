# ftp_monior.py — Misst Werte, speichert sie und lädt sie per FTP hoch
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
LOCAL_LOGFILE  = "system_log.txt"
FILES          = [LOCAL_FILE,LOCAL_LOGFILE]
FREE_MIN_BYTES = 100 * 1024  # 100 KB
RED            = color565(255, 0, 0)
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
    global last_time_in_seconds, total_kwh
    
    ts = get_timestamp()
    date_str = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"
    time_str = f"{ts[8:10]}:{ts[10:12]}:{ts[12:14]}"
    
    # 1. Uhrzeit in absolute Tagessekunden umrechnen
    h = int(ts[8:10])
    m = int(ts[10:12])
    s = int(ts[12:14])
    current_seconds = h * 3600 + m * 60 + s
    
    # 2. JSON-Check: Falls Variablen im RAM "None/0" sind, versuchen wir aus der Datei zu laden
    # ("globals()" prüft sauber, ob die Variablen im Skript überhaupt schon existieren)
    if 'last_time_in_seconds' not in globals() or last_time_in_seconds is None:
        try:
            import json
            with open('energy_state.json', 'r') as f:
                daten = json.load(f)
                last_time_in_seconds = daten.get("last_sec", current_seconds)
                total_kwh = daten.get("kwh", 0.0)
            print(f"[Energy] Stand geladen: {total_kwh:.4f} kWh")
        except OSError:
            # Datei existiert noch nicht -> Initialisierung mit aktuellen Werten
            last_time_in_seconds = current_seconds
            total_kwh = 0.0
            print("[Energy] Keine State-Datei gefunden. Initialisiere neu.")

    v1, v2, v3 = sct_values_get()
    
    # 3. kWh-Berechnung (Ergibt beim allerersten Aufruf korrekte 0,0 Leistung, da delta_t = 0)
    delta_t = (current_seconds - last_time_in_seconds) % 86400
    if delta_t > 0:
        power_w = (v1 + v2 + v3) * 240.0
        total_kwh += (power_w * delta_t) / 3600000.0
        
    # Aktuelle Zeit für den nächsten Durchlauf im RAM merken
    last_time_in_seconds = current_seconds
    
    # 4. Aktuellen Zustand im JSON abspeichern (Sicherung für den nächsten Reboot)
    try:
        import json
        with open('energy_state.json', 'w') as f:
            json.dump({"last_sec": last_time_in_seconds, "kwh": total_kwh}, f)
    except OSError as e:
        print("[Energy] Fehler beim Sichern des Zustands:", e)

    # Rest deiner originalen Funktion
    note = f"{i} {date_str} {time_str} ({total_kwh:.3f}kWh)"
    show_values(v1, v2, v3, note)
    
    line = f"{date_str};{time_str};{v1:.3f};{v2:.3f};{v3:.3f};{total_kwh:.4f}\n"
    with open(LOCAL_FILE, "a") as f:
        f.write(line.replace(".", ","))
# In append_row() nach der Messung:
    with open('last_values.json', 'w') as f:
        json.dump({'p1': round(v1*240,1), 'p2': round(v2*240,1), 
                   'p3': round(v3*240,1), 'kwh': total_kwh}, f)        
    return line.strip()
def file_size(file=LOCAL_FILE):
    try:
        return os.stat(file)[6]
    except:
        return 0
def start_webserver():
    import socket
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('0.0.0.0', 80))
    srv.listen(3)
    srv.setblocking(False)
    return srv

def handle_web(srv):
    try:
        conn, addr = srv.accept()
        conn.settimeout(4)          # ← neu
        req = conn.recv(1024).decode('utf-8', 'ignore')
        pfad = req.split(' ')[1] if ' ' in req else '/'
        print('[WEB] handle_web Request:', pfad)  # ← neu
        if pfad == '/data':
            import json
            try:
                with open('last_values.json') as f:
                    body = f.read()
            except OSError:
                body = '{"p1":0,"p2":0,"p3":0,"kwh":0}'
            conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n')
            conn.sendall(body.encode())

        elif pfad == '/dashboard':
            print('[WEB] elif pfad ==  /dashboard Request: /dashboard')
            
            html = html_dashboard()
            resp = html.encode('utf-8')
            length = len(resp)
            
            print(' Connection: close sagt dem Browser: "Danach ist Feierabend!"')
            header = f"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {length}\r\nConnection: close\r\n\r\n"
            
            try:
                print('# 1. Header senden')
                conn.sendall(header.encode('utf-8'))
                print('# 2. HTML senden')
                conn.sendall(resp)
                print('[WEB] Dashboard erfolgreich gesendet!')
            except Exception as e:
                # Falls Chrome mittendrin abbricht, fangen wir das ab, ohne dass der ESP32 abstürzt
                print('[WEB] Senden abgebrochen durch Browser/Timeout:', e)
            conn.close()
    except OSError:
        pass  # kein Request da    

def html_dashboard():
    import network
    ip = network.WLAN(network.STA_IF).ifconfig()[0]
    return (
        "<!DOCTYPE html><html>"
        "<head>"
        "<link rel='icon' href='data:;base64,iVBORw0Kgo='>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Strommonitor</title>"
        "<style>"
        "body{background:#1a1a2e;color:#eee;font-family:sans-serif;text-align:center;padding:20px;margin:0}"
        "h1{color:#e94560;margin-bottom:0.5rem}"
        ".kwh{font-size:3.5rem;font-weight:bold;color:#2ecc71;line-height:1.1}"
        ".kwh-unit{font-size:1.2rem;color:#aaa;margin-left:4px}"
        ".kwh-label{font-size:0.8rem;color:#aaa;letter-spacing:0.1em;margin-bottom:0.25rem}"
        ".total{background:#16213e;border-radius:8px;padding:8px;margin:10px auto;width:90%;font-size:0.9rem;color:#aaa}"
        ".total span{color:#eee;font-weight:bold}"
        ".bars{display:flex;gap:16px;justify-content:center;align-items:flex-end;margin:16px auto;width:90%;height:600px}"
        ".bar-col{flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;height:100%}"
        ".bar-outer{width:100%;flex:1;background:#16213e;border-radius:6px;display:flex;align-items:flex-end;overflow:hidden;border:1px solid #333;position:relative}"
        ".bar-inner{width:100%;border-radius:6px 6px 0 0;transition:height 0.6s ease}"
        ".l1{background:#2980b9}.l2{background:#27ae60}.l3{background:#e67e22}"
        ".bar-watt{font-size:0.85rem;font-weight:bold;color:#eee}"
        ".bar-amp{font-size:0.7rem;color:#aaa}"
        ".bar-name{font-size:0.8rem;color:#aaa}"
        ".scale{position:absolute;right:3px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:space-between;padding:2px 0;pointer-events:none}"
        ".scale span{font-size:9px;color:#666;line-height:1}"
        ".status{font-size:0.75rem;color:#aaa;margin-top:8px}"
        ".dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#27ae60;margin-right:4px}"
        ".dot.err{background:#e74c3c}"
        "</style>"
        "</head>"
        "<body>"
        "<h1>&#9889; Strommonitor</h1>"
        "<div class='kwh-label'>TAGESVERBRAUCH</div>"
        "<div><span class='kwh' id='kwh'>–</span><span class='kwh-unit'>kWh</span></div>"
        "<div class='total'>Gesamt: <span id='total'>–</span> W &nbsp;|&nbsp; Skala: <span id='scale-lbl'>–</span></div>"
        "<div class='bars'>"
        "<div class='bar-col'><div class='bar-watt' id='w1'>– W</div><div class='bar-amp' id='a1'>– A</div>"
        "<div class='bar-outer'><div class='bar-inner l1' id='b1' style='height:0%'></div>"
        "<div class='scale' id='sc1'></div></div><div class='bar-name'>L1</div></div>"
        "<div class='bar-col'><div class='bar-watt' id='w2'>– W</div><div class='bar-amp' id='a2'>– A</div>"
        "<div class='bar-outer'><div class='bar-inner l2' id='b2' style='height:0%'></div>"
        "<div class='scale' id='sc2'></div></div><div class='bar-name'>L2</div></div>"
        "<div class='bar-col'><div class='bar-watt' id='w3'>– W</div><div class='bar-amp' id='a3'>– A</div>"
        "<div class='bar-outer'><div class='bar-inner l3' id='b3' style='height:0%'></div>"
        "<div class='scale' id='sc3'></div></div><div class='bar-name'>L3</div></div>"
        "</div>"
        "<div class='status'><span class='dot' id='dot'></span><span id='stxt'>Verbinde...</span>"
        " &nbsp; <span id='upd'></span></div>"
        "<p><small>IP: " + ip + ":8080</small></p>"
        "<script>"
        "var SCALES=[500,2000,10000,15000];"
        "function pickScale(m){for(var i=0;i<SCALES.length;i++)if(m<=SCALES[i])return SCALES[i];return 15000;}"
        # ... restliche Funktionen ...
        "function fetchData(){"
        "fetch('/data')"
        ".then(function(r){return r.json();})"
        ".then(update)"
        ".catch(function(){"
        "document.getElementById('dot').className='dot err';"
        "document.getElementById('stxt').textContent='Keine Verbindung';"
        "document.getElementById('upd').textContent=`${new Date().toLocaleDateString('de-DE')} ${new Date().toLocaleTimeString('de-DE')}`;"
        "})"          // Korrektur
        "}"           // Ende fetchData
        "fetchData();setInterval(fetchData,500);"
        "</script>"
        "</body></html>"
    )
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

def upload_and_clear(reason,localfile=LOCAL_FILE):
    # 1. Sofort alten Müll (vom vorherigen FTP-Lauf) löschen, BEVOR wir irgendwas tun!
    import gc
    gc.collect() 
    _, _, FTP_USER, FTP_PASS = get_credentials('/credentials.txt')
    _display.draw_text8x8(10, 150, "atempt to ts = get_timestamp()", YELLOW, BLACK)    
    # 2. Erst jetzt, im frisch aufgeräumten RAM, den Zeitstempel generieren
    ts = get_timestamp()
    remote_name = f"{ts}_{localfile}"
    
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
        success = ftp.upload(localfile, remote_name)
        ftp.disconnect()
        
        # Wichtig: Das Objekt explizit zerstören, damit der RAM freigegeben werden kann
        del ftp 
    except Exception as e:
        print("    FTP-Fehler während der Übertragung:", e)

    if success:
        try:
            os.remove(localfile)
            print(f"{localfile} lokal gelöscht. Frei nachher: {free_bytes()} B")
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
    ntptime.host = "fritz.box"  # statt fritz.box
    log('ntptime.host = fritz.box, try ntptime.settime')
    try:
        ntptime.settime()
        _display.draw_text8x8(10, 40, "ntptime OK", GREEN, BLACK)
    except Exception as e:
        print("NTP Fehler:", str(e))
        log("NTP Fehler: "+ str(e))
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
    t = time.localtime(time.time() + 2 * 3600)
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
    srv = start_webserver()
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
            handle_web(srv)   # non-blocking, kehrt sofort zurück
            time.sleep(2)
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
        if frei < FREE_MIN_BYTES:
            for file in FILES:
                upload_and_clear("Speicher < 100 KB", file)
            last_day = time.localtime()[2]
            last_date_str = "{:04d}{:02d}{:02d}".format(*time.localtime()[:3])

        elif today != last_day:
            for file in FILES:
                upload_and_clear(f"Tageswechsel {last_date_str} → {'{:04d}{:02d}{:02d}'.format(*t[:3])}", file)
            last_day = today
            last_date_str = "{:04d}{:02d}{:02d}".format(*t[:3])
            
        elif i % save_interval == 0:
            _display.draw_text8x8(10, 200, "vor upload_and_clear(f", WHITE, BLACK)
            reason = f"i % save_interval == 0 {last_date_str} → {'{:04d}{:02d}{:02d}'.format(*t[:3])}"
            log(reason+': '+reason)
            for file in FILES:
                upload_and_clear(reason, file)

# Einzeltest aus Thonny erlauben
if __name__ == "__main__":
    run()