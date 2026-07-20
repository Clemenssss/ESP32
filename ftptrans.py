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
#from logger import logger
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
ftp_active = False
# CYD-Pinout: GPIO 16 = Grün (active-low), GPIO 21 = Backlight
_led_gruen = Pin(16, Pin.OUT, value=1)   # 1 = aus (active-low)
_bl        = Pin(21, Pin.OUT, value=0)   # 0 = aus
# Platzhalter für globale Objekte
_display = None
led = None

def turn_off_and_get_dummy(display_instance, spi_instance):
    """
    Schaltet das Backlight aus und gibt das DummyDisplay zurück.
    Keine Hardware-Zerstörung, kein Löschen von sys.modules.
    """
    from dummy_display import DummyDisplay

    print("Schalte um auf Dummy-Display für REPL-Monitor...")
    
    try:
        # 1. Bildschirm schwärzen
        display_instance.fill_rectangle(0, 0, 320, 240, BLACK)
        print("Bildschirm schwärzen OK")
    except:
        pass
        
    try:
        # 2. Hintergrundbeleuchtung aus (GPIO 21)
        bl = Pin(21, Pin.OUT)
        bl.value(0)
        print("Hintergrundbeleuchtung aus (GPIO 21) OK")
    except:
        print("Hintergrundbeleuchtung aus (GPIO 21) FAIL-Restet")
        import machine
        machine.reset()
        
    # Wir löschen NUR die lokale Variable des echten Displays,
    # damit der Speicher vom GC freigegeben wird.
    del display_instance
    gc.collect()
    
    # 3. Dummy zurückgeben, damit show_values() brav in die REPL printet
    print('return DummyDisplay()')
    return DummyDisplay()
def show_values(v1, v2, v3, note,  display=None):
    return #Not needed for now
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
    #show_values(v1, v2, v3, note)
    
    line = f"{date_str};{time_str};{v1:.3f};{v2:.3f};{v3:.3f};{total_kwh:.4f}"
    print(line)
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
def blink(color='green', count=3, on_ms=200, off_ms=100):
    import time
    pin_green = Pin(16, Pin.OUT, value=1)
    try:
        pin_red = Pin(4, Pin.OUT, value=1)
    except:
        pin_red = None
    
    pin = pin_red if color == 'red' and pin_red else pin_green
    
    for _ in range(count):
        pin.value(0)
        time.sleep_ms(on_ms)
        pin.value(1)
        time.sleep_ms(off_ms)

def start_webserver(max_retries=5):
    import socket, time
    for attempt in range(max_retries):
        srv = socket.socket()
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind(('0.0.0.0', 80))
            srv.listen(3)
            print("Webserver auf Port 80 gestartet (Versuch" , str(attempt+1) , ")")
            blink('green', 3, 200, 100)
            return srv
        except OSError as e:
            print("Port 80 belegt, Versuch " , str(attempt+1) , "/" , str(max_retries))
            srv.close()
            time.sleep(1)
    
    print("Konnte Webserver nicht starten")
    blink('red', 3, 200, 100)
    return None

import errno
def handle_web(srv):
    print('handle_web srv')
    conn = None
    try:
        srv.settimeout(0.02)
        try:
            conn, addr = srv.accept()
            print('srv.accept()',conn, addr)
        except OSError as e:
            if e.args[0] in (11, 110, 111):
                #print(f"[WEB] ignore OSError: {e}")
                pass
            
            if e.args[0] in (110, 11):
                return
            raise e
        
        print(f"[WEB] Verbindung von {addr}")
        conn.settimeout(None)  # ← exakt wie in main.py, das funktioniert
        req = conn.recv(1024)
        print(f"[WEB] recv: {len(req)} Bytes")
        
        if not req:
            print("[WEB] Leerer Request, close")
            conn.close()
            return
        
        req_str = req.decode('utf-8', 'ignore')
        pfad = req_str.split(' ')[1] if ' ' in req_str else '/'
        print(f"[WEB] Pfad: {pfad}")
        
        if pfad in ['/', '/start', '/dashboard']:
            print("[WEB] Baue HTML...")
            html = html_dashboard()
            respo = html.encode('utf-8')
            header = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html; charset=utf-8\r\n"
                "Content-Length: {}\r\n"
                "Connection: close\r\n\r\n"
            ).format(len(respo)).encode('utf-8')
            conn.settimeout(10)
            print(f"[WEB] Vor sendall, {len(header)+len(respo)} Bytes", 'conn.settimeout(10)')
            # In deinem Code, vor und nach sendall:
            diagnose_socket(conn, "vor sendall")
            try:
                conn.sendall(header + respo)
                diagnose_socket(conn, "nach sendall")
                print("[WEB] sendall OK")
            except OSError as e:
                print(f"[WEB] sendall FEHLER: {e}")
                
        elif pfad == '/data':
            print("[WEB] Baue JSON...")
            try:
                with open('last_values.json', 'r') as f:
                    body = f.read()
            except OSError:
                body = '{"p1":0,"p2":0,"p3":0,"kwh":0}'
            body_bytes = body.encode('utf-8')
            header = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "Content-Length: {}\r\n"
                "Connection: close\r\n\r\n"
            ).format(len(body_bytes)).encode('utf-8')
            print(f"[WEB] Vor sendall data, {len(header)+len(body_bytes)} Bytes")
            try:
                conn.sendall(header + body_bytes)
                print("[WEB] sendall data OK")
            except OSError as e:
                print(f"[WEB] sendall data FEHLER: {e}")
                
        else:
            print("[WEB] 404")
            try:
                conn.sendall(b'HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n')
                print("[WEB] 404 OK")
            except OSError as e:
                print(f"[WEB] 404 FEHLER: {e}")
                
    except OSError as e:
        if e.args[0] not in (110, 11, 116):
            print(f"[WEB] Socket-Fehler: {e}")
    except Exception as e:
        print(f"[WEB] Unerwarteter Fehler: {e}")
    finally:
        if conn:
            print("[WEB] Schließe Verbindung")
            try:
                conn.close()
            except Exception as e:
                print(f"[WEB] close() Fehler: {e}")
def html_dashboard_x():
    import network
    ip = network.WLAN(network.STA_IF).ifconfig()[0]
    # Alles in einer einzigen, kompakten Zeile (keine Speicher-Fragmentierung durch String-Concat)
    return '<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Strom</title><style>body{background:#1a1a2e;color:#eee;font-family:sans-serif;text-align:center;margin:0;padding:10px}h1{color:#e94560;margin:0}.bar{display:flex;gap:10px;justify-content:center;height:200px;margin:10px 0}.b{flex:1;background:#16213e;border-radius:4px;display:flex;flex-direction:column;justify-content:flex-end;overflow:hidden}.i{width:100%;transition:height .3s}.l1{background:#2980b9}.l2{background:#27ae60}.l3{background:#e67e22}</style></head><body><h1>Strom</h1><div class="bar"><div class="b"><div id="b1" class="i l1" style="height:0%"></div></div><div class="b"><div id="b2" class="i l2" style="height:0%"></div></div><div class="b"><div id="b3" class="i l3" style="height:0%"></div></div></div><p id="t">-</p><small>IP: '+ip+'</small><script>function f(){fetch("/data").then(r=>r.json()).then(d=>{let m=Math.max(d.p1,d.p2,d.p3,1);document.getElementById("b1").style.height=(d.p1/m*100)+"%";document.getElementById("b2").style.height=(d.p2/m*100)+"%";document.getElementById("b3").style.height=(d.p3/m*100)+"%";document.getElementById("t").innerText=d.p1+d.p2+d.p3+"W";})}setInterval(f,1000);f();</script></body></html>'                
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
        ".kwh{font-size:2.5rem;font-weight:bold;color:#2ecc71;line-height:1.1}"
        ".kwh-unit{font-size:1rem;color:#aaa;margin-left:4px}"
        ".kwh-label{font-size:0.8rem;color:#aaa;letter-spacing:0.1em;margin-bottom:0.25rem}"
        ".time{font-size:2.5rem;font-weight:bold;color:#2ecc71;line-height:1.1;margin-left:20px}"
        ".header-row{display:flex;justify-content:center;align-items:baseline;gap:12px;margin:8px auto;width:90%}" 
        ".kwh-label{font-size:0.8rem;color:#aaa;letter-spacing:0.1em;margin-bottom:0.25rem;text-align:center}"  
        ".total{background:#16213e;border-radius:8px;padding:8px;margin:10px auto;width:90%;font-size:0.9rem;color:#aaa}"
        ".total span{color:#eee;font-weight:bold}"
        ".bars{display:flex;gap:16px;justify-content:center;align-items:flex-end;margin:16px auto;width:90%;height:400px}"
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
        "<div class='header-row'>"
        "<span class='time' id='zeit'>--:--:--</span>"
        "<span class='kwh' id='kwh'>–</span><span class='kwh-unit'>kWh</span>"
        "</div>"
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
        "<p><small>IP: " + ip + "</small></p>"
        "<script>"
        "var SCALES=[500,2000,10000,15000];"
        "function pickScale(m){for(var i=0;i<SCALES.length;i++)if(m<=SCALES[i])return SCALES[i];return 15000;}"
        "function update(d){"
        "var p1=d.p1||0,p2=d.p2||0,p3=d.p3||0,kwh=d.kwh||0;"
        "var total=p1+p2+p3,max=Math.max(p1,p2,p3,1),scale=pickScale(max);"
        "document.getElementById('kwh').textContent=kwh.toFixed(2);"
        "document.getElementById('total').textContent=total.toFixed(1);"
        "document.getElementById('scale-lbl').textContent=scale+' W';"
        "document.getElementById('w1').textContent=p1.toFixed(1)+' W';"
        "document.getElementById('w2').textContent=p2.toFixed(1)+' W';"
        "document.getElementById('w3').textContent=p3.toFixed(1)+' W';"
        "document.getElementById('a1').textContent=(p1/240).toFixed(2)+' A';"
        "document.getElementById('a2').textContent=(p2/240).toFixed(2)+' A';"
        "document.getElementById('a3').textContent=(p3/240).toFixed(2)+' A';"
        "document.getElementById('b1').style.height=Math.min(100,(p1/scale)*100).toFixed(1)+'%';"
        "document.getElementById('b2').style.height=Math.min(100,(p2/scale)*100).toFixed(1)+'%';"
        "document.getElementById('b3').style.height=Math.min(100,(p3/scale)*100).toFixed(1)+'%';"
        "document.getElementById('dot').className='dot';"
        "document.getElementById('stxt').textContent='Live';"
        "document.getElementById('upd').textContent=new Date().toLocaleTimeString('de-DE');"
        "var now=new Date();"
        "document.getElementById('zeit').textContent="
        "now.getHours().toString().padStart(2,'0')+':'+"
        "now.getMinutes().toString().padStart(2,'0')+':'+"
        "now.getSeconds().toString().padStart(2,'0');"
        "}"
        "function fetchData(){"
        "fetch('/data')"
        ".then(function(r){return r.json();})"
        ".then(update)"
        ".catch(function(){"
        "document.getElementById('dot').className='dot err';"
        "document.getElementById('stxt').textContent='Keine Verbindung';"
        "});"
        "}"
        "fetchData();setInterval(fetchData,500);"
        "</script>"
        "</body></html>"
    )
# --- SimpleFTP ---
class SimpleFTP:
    def __init__(self, host, user, password, port=21):
#         print('__init__(self, host, user, password, port=21)', host, user, port)
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.sock = None

    def _send(self, cmd):
        self.sock.send((cmd + "\r\n").encode())
        return self._read()

    def connect(self):
        try:
            self.sock = usocket.socket()
            self.sock.settimeout(10)
            addr = usocket.getaddrinfo(self.host, self.port)[0][-1]
            self.sock.connect(addr)
            print("FTP:", self._read().strip())
            print(self._send(f"USER {self.user}").strip())
            print(self._send(f"PASS {self.password}").strip())
            print('FTP: connected')
        except Exception as e:
            # Always close the socket on failure to avoid leaking lwIP resources
            try:
                self.sock.close()
            except Exception:
                pass
            raise

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


    def _pasv(self):
        try:
            resp = self._send("PASV")
            print("FTP: PASV Roh-Antwort vom Server:" , str(resp))

            # Sicherheitscheck: Kam überhaupt eine korrekte Antwort mit Klammern?
            if not resp or "(" not in resp or ")" not in resp:
                print("FTP Fehler: Unerwartete PASV Antwort:" , str(resp))
                return None

            nums = resp.split("(")[1].split(")")[0].split(",")

            # Sicherheitscheck: Haben wir wirklich alle 6 Zahlen für IP und Port?
            if len(nums) < 6:
                print("FTP Fehler: Ungültiges IP/Port Format in PASV:" , str(nums))
                return None

            data_ip   = ".".join(nums[:4])
            data_port = int(nums[4]) * 256 + int(nums[5])

            print("FTP: Datenverbindung aufbauen zu" + str(data_ip) , ":" , str(data_port))

            data_sock = usocket.socket()
            # Timeout für den Daten-Socket setzen (sehr wichtig!)
            data_sock.settimeout(10.0) 

            data_sock.connect(usocket.getaddrinfo(data_ip, data_port)[0][-1])
            print("FTP: Daten-Socket erfolgreich verbunden.")
            return data_sock

        except Exception as e:
            print("FTP: Schwerer Fehler in _pasv():" , str(e))
            return None
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
    _, _, FTP_USER, FTP_PASS = get_credentials()
    print('get_credentials()',FTP_USER, FTP_PASS)
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
    except Exception as e:
        print('ntptime.settime() exception',e)
        pass # Falls NTP mal zickt, nicht abstürzen

    # FTP ausführen
    success = False
    try:
        ftp = SimpleFTP(FTP_HOST, FTP_USER, FTP_PASS)
        print('ftp initialized, do connect')
        for attempt in range(3):
            try:
                ftp.connect()
                break
            except OSError as e:
                print(f"FTP connect attempt {attempt+1} failed:", e)
                time.sleep(2)
        else:
            print("FTP connect finally failed")
        print('ftp connected')
        ftp.cwd(FTP_DIR)
        print('ftp.cwd(FTP_DIR) OK')
        success = ftp.upload(localfile, remote_name)
        print('ftp.upload',localfile, remote_name,success)
        ftp.disconnect()
        
        # Wichtig: Das Objekt explizit zerstören, damit der RAM freigegeben werden kann
        del ftp
        print('del ftp OK')
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
# def blink_gruen(ms=500):
#     """Grüne LED für ms Millisekunden einschalten."""
#     _led_gruen.value(0)      # an (active-low)
#     time.sleep_ms(ms)
#     _led_gruen.value(1)      # aus

def blitz_backlight(ms=500):
    """Display-Backlight für ms Millisekunden voll einschalten.
    Hinweis: Überschreibt ggf. eine vorhandene PWM-Steuerung auf GPIO21."""
    _bl.value(1)
    time.sleep_ms(ms)
    _bl.value(0)
def diagnose_socket(conn, label=""):
    """Diagnose fuer LwIP-Sockets auf ESP32/MicroPython.
    getpeername/getsockname/fileno existieren hier NICHT (AttributeError!) -> weggelassen.
    """
    print(f"[DIAG] {label} ---")

    # Einziger zuverlaessiger "ist der Socket noch lebendig"-Test: send(b"")
    try:
        n = conn.send(b"")
        print(f"[DIAG] {label} Send-0: {n}")
    except OSError as e:
        print(f"[DIAG] {label} Send-0 Fehler: {e.args[0] if e.args else e}")
    except Exception as e:
        print(f"[DIAG] {label} Send-0 unerwartet: {e}")

    # select() statt recv(PEEK) - prueft read/write-Bereitschaft ohne zu blockieren
    try:
        import select
        r, w, x = select.select([conn], [conn], [conn], 0)
        print(f"[DIAG] {label} select: read={bool(r)} write={bool(w)} err={bool(x)}")
    except Exception as e:
        print(f"[DIAG] {label} select Fehler: {e}")

    # Heap-Status ist bei euch ohnehin relevant (Fragmentierung!)
    try:
        import gc
        print(f"[DIAG] {label} Heap free: {gc.mem_free()}")
    except Exception as e:
        print(f"[DIAG] {label} gc Fehler: {e}")
    
    print(f"[DIAG] {label} --- END")
# --- Hauptfunktion ---
def run():
    # Herausfinden, wer gestartet hat, via Namensraum
    caller = "direkt/main" if __name__ == "__main__" else "programm_starten"
    print('ftptrans caller:', caller)
    global _display, led
    
    led = LED()
    
    # Echte Hardware initialisieren
    _spi = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(13))
    _display = Display(_spi, dc=Pin(2), cs=Pin(15), rst=Pin(15),
                       width=320, height=240, rotation=0)
    Pin(21, Pin.OUT).on()
    
    _display.draw_text8x8(10, 20, "ntptime...", WHITE, BLACK)
    ntptime.host = "fritz.box"  # statt fritz.box
    print('ntptime.host = fritz.box, try ntptime.settime')
    import utime
    utime.sleep(2)  # Socket-Cleanup abwarten
    NTP_SERVERS = ["fritz.box", "192.168.178.1", "192.168.178.11",'192.168.178.31',"fritz.box", "192.168.178.1", "192.168.178.11"]  # deine IPs

    ntp_ok = False
    for host in NTP_SERVERS:
        try:
            ntptime.host = host
            ntptime.settime()
            _display.draw_text8x8(10, 40, "ntptime OK", GREEN, BLACK)
            print('ntptime.settime() success, host=' , host)
            ntp_ok = True
            break
        except Exception as e:
            print("NTP Fehler mit",host, str(e))
            gc.collect()
            print('memory',gc-memfree())
        continue

    if not ntp_ok:
        _display.draw_text8x8(10, 40, "NTP skip", RED, BLACK)
        print("NTP completely failed, no use to continue")
        import machine
        machine.soft_reset()
    t = time.localtime()
    last_day = t[2]
    _display.draw_text8x8(10, 60, "init OK   ", GREEN, BLACK)
    
    # Zugriff auf wlan-Objekt abfangen (falls es global in main.py existiert)
    # Wenn nicht verfügbar, erstellen wir ein Dummy-Objekt, um Abstürze zu verhindern
    # Echte WLAN-Schnittstelle direkt vom System holen (unabhängig von Namensräumen)
    import network
    wlan = network.WLAN(network.STA_IF)
    if not wlan:
        print('not wlan')
        import machine
        machine.reset()
    print('before switching off display wlan.isconnected()', str(wlan.isconnected()))
    gc.collect()
    print('free memory:', gc.mem_free())
    print('free memory:', str(gc.mem_free()))
    t = time.localtime(time.time() + 2 * 3600)
    last_day = t[2]
    last_date_str = "{:04d}{:02d}{:02d}".format(t[0], t[1], t[2])
    print(f"Flash total: {os.statvfs('/')[0] * os.statvfs('/')[2] // 1024} KB")
    print(f"Flash frei:  {free_bytes() // 1024} KB")
    
    # Jetzt auf DummyDisplay umschalten
    print('_display = turn_off_and_get_dummy(_display, _spi)')
    _display = turn_off_and_get_dummy(_display, _spi)
    gc.collect()
    
    i = 0
    ftp_active = False 
    load_calibration()
    time.sleep(5)
    srv = start_webserver()
    if not srv:
        return "Webserver not established"
    save_interval = 3
    interval_save = True
    # --- Hauptschleife ---
    while True:
        gc.collect()    
        print('row = append_row() ', str(i),' ', str(wlan.isconnected()), ' free memory: ', str(gc.mem_free()))
        if not ftp_active:  # Nur Webserver bedienen, wenn kein FTP läuft
             handle_web(srv)  # Non-blocking, kehrt sofort zurück
        t = time.localtime(time.time() + 2 * 3600)
        today = t[2]
        try:
            row = append_row(i)
            i += 1
            #handle_web(srv)   # non-blocking, kehrt sofort zurück
            time.sleep(2)
            if not ftp_active:  # Nur Webserver bedienen, wenn kein FTP läuft
                handle_web(srv)  # Non-blocking, kehrt sofort zurück
            blink()
            blitz_backlight()
        except OSError as e:
            print(f"[WARNUNG]: ADS Sensor temporär verloren ({e}). Starte I2C-Reset...")
            try:
                load_calibration() 
                print("-> Sensor erfolgreich reinitialisiert!")
            except Exception as reset_err:
                print("-> Reinitialisierung fehlgeschlagen:", reset_err)
            time.sleep(2)
            continue
            
        frei = free_bytes()
        if frei < FREE_MIN_BYTES:
            ftp_active = True
            for file in FILES:
                upload_and_clear("Speicher < 100 KB", file)
            ftp_active = False
            last_day = time.localtime()[2]
            last_date_str = "{:04d}{:02d}{:02d}".format(*time.localtime()[:3])
        elif today != last_day:
            ftp_active = True
            for file in FILES:
                upload_and_clear(f"Tageswechsel {last_date_str} → {'{:04d}{:02d}{:02d}'.format(*t[:3])}", file)
            last_day = today
            last_date_str = "{:04d}{:02d}{:02d}".format(*t[:3])
            
        elif i % save_interval == 0 and interval_save:
            reason = f"i % save_interval == 0 {last_date_str} → {'{:04d}{:02d}{:02d}'.format(*t[:3])}"
            print(reason,':',reason)
            ftp_active = True
            for file in FILES:
                upload_and_clear(reason, file)
        ftp_active = False    
        time.sleep(0.1)  # 100ms Pause
    # Einzeltest aus Thonny erlauben
if __name__ == "__main__":
    run()
