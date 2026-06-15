import gc
import sys
import os
print('running main')
print('Vor import network, socket, os, time  gc.mem_free()=', gc.mem_free())
import network, socket, os, time
print('Nach import network, socket, os, time gc.mem_free()=', gc.mem_free())

# ── WLAN bereits in boot.py verbunden ─────────────────────
wlan = network.WLAN(network.STA_IF)
if not wlan.isconnected():
    print("WLAN nicht verbunden - check boot.py!")
    try:
        from boot import blink_led, LED_ROT
        blink_led(LED_ROT, count=5)
    except:
        pass
else:
    print("IP:", wlan.ifconfig()[0])

# ── Display-Singleton ──────────────────────────────────────
_display = None
_backlight = None

def get_display():
    global _display, _backlight
    if _display is None:
        from machine import Pin, SPI
        from ili9341 import Display, color565
        spi = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(13))
        _display = Display(spi, dc=Pin(2), cs=Pin(15), rst=Pin(15),
                           width=320, height=240, rotation=0)
        _backlight = Pin(21, Pin.OUT)
        _backlight.on()
    return _display

# ── QR-Code auf Display zeigen ─────────────────────────────
def show_ip(ip):
    from ili9341 import color565
    import gc
    DISP_W = 320
    DISP_H = 240
    print('show_ip: gc.mem_free()=', gc.mem_free())
    display = get_display()
    display.clear(color565(0, 0, 0))
    gc.collect()
    try:
        import uQR
        gc.collect()
        url = 'http://' + str(ip)
        print('Generiere QR fuer:', url)
        qr = uQR.QRCode(error_correction=uQR.ERROR_CORRECT_L, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        modules = qr.get_matrix()
        gc.collect()
        module_count = len(modules)
        box_size = max(1, min(7, (DISP_W - 20) // module_count,
                                  (DISP_H - 20) // module_count))
        total_size = module_count * box_size
        start_x = (DISP_W - total_size) // 2
        start_y = (DISP_H - total_size) // 2
        print('module_count=%d box_size=%d total=%d sx=%d sy=%d' %
              (module_count, box_size, total_size, start_x, start_y))
        white = color565(255, 255, 255)
        black = color565(0, 0, 0)
        display.fill_rectangle(start_x - 4, start_y - 4,
                               total_size + 8, total_size + 8, white)
        for r in range(module_count):
            for c in range(module_count):
                if modules[r][c]:
                    display.fill_rectangle(
                        start_x + c * box_size,
                        start_y + r * box_size,
                        box_size, box_size, black)
        print('QR-Code fertig, gc.mem_free()=', gc.mem_free())
    except Exception as e:
        import sys
        print('Fehler in show_ip:', e)
        sys.print_exception(e)
        white = color565(255, 255, 255)
        black = color565(0, 0, 0)
        display.draw_text8x8(10, 60, 'QR Fehler:', white, black)
        display.draw_text8x8(10, 80, str(e)[:28], white, black)
    gc.collect()

# ── Programme auflisten ────────────────────────────────────
AUSNAHMEN = {'boot.py', 'main.py', 'ili9341.py', 'xglcd_font.py',
             'ads1x15.py', 'sdcard.py', 'credentials.txt', 'uQR.py'}

def programme_laden():
    return sorted(f for f in os.listdir('/')
                  if f.endswith('.py') and f not in AUSNAHMEN)

# ── Programm ausfuehren ────────────────────────────────────
import sys

def programm_starten(dateiname):
    try:
        # 1. Bereinigen: Schrägstriche entfernen und das ".py" abschneiden
        # "colorline.py" -> "colorline"
        # "/colorline.py" -> "colorline"
        modul_name = dateiname.replace('/', '').replace('.py', '')
        
        # 2. Altes Modul aus dem Speicher werfen für einen frischen Start
        if modul_name in sys.modules:
            del sys.modules[modul_name]
        
        # 3. Dynamischer Import via __import__()
        modul = __import__(modul_name)
        
        # 4. Die run()-Funktion ausführen
        if hasattr(modul, "run"):
            return modul.run() #das echte Ergebnis von run() zurückgeben
            
        else:
            return f"Fehler: Keine run()-Funktion in {dateiname} gefunden."
            
    except Exception as e:
        return "Fehler: " + str(e)
            
    except Exception as e:
        return "Fehler: " + str(e)

# ── HTML Seite ─────────────────────────────────────────────
def html_seite(meldung=""):
    programme = programme_laden()
    ip = wlan.ifconfig()[0]
    meldung_html = (
        "<div class='meldung'>" + meldung + "</div>" if meldung else "")
    buttons = ""
    for i in range(0, len(programme), 2):
        buttons += "<div class='row'>"
        for p in programme[i:i+2]:
            label = p[:-3] if p.endswith('.py') else p
            buttons += (
                "<form method='POST' action='/start' class='btnform'>"
                "<input type='hidden' name='programm' value='" + p + "'>"
                "<button type='submit'>" + label + "</button>"
                "</form>")
        buttons += "</div>"
    if not programme:
        buttons = "<p>Keine Programme gefunden</p>"
    return (
        "<!DOCTYPE html><html>"
        "<head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>ESP32 Launcher</title>"
        "<style>"
        "body{background:#1a1a2e;color:#eee;font-family:sans-serif;"
        "text-align:center;padding:20px}"
        "h1{color:#e94560}"
        ".row{display:flex;justify-content:center;gap:10px;margin:8px 0}"
        ".btnform{flex:1;max-width:45%}"
        ".btnform button{width:100%;padding:14px 6px;border-radius:8px;"
        "font-size:1em;border:none;cursor:pointer;"
        "background:#27ae60;color:white;transition:background 0.3s}"
        ".btnform button:active{background:#e67e22}"
        ".meldung{background:#16213e;border-radius:8px;padding:10px;"
        "margin:10px auto;width:80%;color:#2ecc71}"
        "</style>"
        "<script>"
        "document.addEventListener('click',function(e){"
        "var b=e.target.closest('button[type=submit]');"
        "if(b){b.style.background='#e67e22';"
        "b.textContent='\u23f3 '+b.textContent;}"
        "});"
        "</script>"
        "</head>"
        "<body>"
        "<h1>&#9889; ESP32 Launcher</h1>"
        + buttons
        + meldung_html +
        "<p><small>IP: " + ip + "</small></p>"
        "</body></html>"
    )

# ── Request parsen ─────────────────────────────────────────
def parse_request(req):
    try:
        req = req.decode('utf-8')
        zeilen = req.split('\r\n')
        methode, pfad, _ = zeilen[0].split(' ')
        body = req.split('\r\n\r\n')[1] if '\r\n\r\n' in req else ""
        return methode, pfad, body
    except:
        return 'GET', '/', ''

def send_response(conn, html):
    response = html.encode()
    header = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html\r\n"
        "Connection: close\r\n"
        "Content-Length: {}\r\n\r\n"
    ).format(len(response))
    conn.send(header.encode() + response)

def parse_body(body):
    try:
        for teil in body.split('&'):
            if '=' in teil:
                key, val = teil.split('=', 1)
                if key == 'programm':
                    return val.replace('+', ' ').replace('%2E', '.')
    except:
        pass
    return None

# ── Webserver starten ──────────────────────────────────────
server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('', 80))
server.listen(3)
print("Webserver: http://{}".format(wlan.ifconfig()[0]))
print('Vor show_ip gc.mem_free()=', gc.mem_free())
show_ip(wlan.ifconfig()[0])
print('Nach show_ip gc.mem_free()=', gc.mem_free())

# ── Hauptschleife ──────────────────────────────────────────
while True:
    try:
        gc.collect()
        conn, addr = server.accept()
        conn.settimeout(2.0) # Kurzes Timeout für den Request-Empfang
        
        req = conn.recv(4096)
        if not req:
            conn.close()
            continue
            
        methode, pfad, body = parse_request(req)
        print('methode, pfad, body = parse_request(req)', methode, pfad, body)
        
        if "favicon" in pfad:
            conn.close()
            continue
            
        if methode == 'POST' and pfad == '/start':
            prog = parse_body(body)
            print('prog = parse_body(body)', prog)
            
            if prog:
                # 1. Timeout abschalten für das finale Senden
                conn.settimeout(None)
                
                # 2. SOFORT die Antwort senden, BEVOR das Skript startet
                print(f"[INFO] Sende Start-Bestätigung für {prog} an den Browser...")
                send_response(conn, html_seite(f"&#9654; Starte Hintergrundprogramm: {prog}..."))
                conn.close() # Verbindung sauber zumachen, der Browser ist jetzt glücklich
                
                # 3. ERST JETZT das Skript ausführen (darf unendlich lang laufen)
                print(f"[INFO] Starte Modul {prog} jetzt dauerhaft...")
                gc.collect()
                ergebnis = programm_starten(prog)
                
                # Falls das Skript DOCH irgendwann zurückkehrt:
                print("Programm hat sich wider Erwarten beendet:", ergebnis)
                del prog
            else:
                send_response(conn, html_seite("Kein Programm gewaehlt"))
                conn.close()
                
        elif pfad == '/':
            send_response(conn, html_seite())
            conn.close()
            
        else:
            conn.close()
            
    except Exception as e:
        print("Serverfehler abgefangen:", e)
        try:
            conn.close()
        except:
            pass