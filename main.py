import gc
import sys
import os
print('running main')
print('Vor import network, socket, os, time  gc.mem_free()=', gc.mem_free())
import network, socket, os, time
print('Nach import network, socket, os, time gc.mem_free()=', gc.mem_free())
from display_utils import turn_off_and_get_dummy
ergebnis = ""
def meminfo():
    import micropython
    import gc
# 1. Sammle zuerst den Müll
    gc.collect()
# 2. Zeige die detaillierte Speicherübersicht
    micropython.mem_info(1)    
def release_display():
    global _display # Falls dein Display global definiert ist
    print("Geben Display-Ressourcen frei...")
    
    # 1. Backlight aus
    try:
        Pin(21, Pin.OUT).off()
    except:
        pass
        
    # 2. Referenz löschen
    _display = None
    
    # 3. Garbage Collector zwingen, den Framebuffer freizugeben
    gc.collect()
def send_redirect(conn, location="/"):
    header = (
        "HTTP/1.1 303 See Other\r\n"
        "Location: {}\r\n"
        "Connection: close\r\n\r\n"
    ).format(location)
    conn.sendall(header.encode())
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

# ── Feste Programmliste ────────────────────────────────────
PROGRAMME = [
    'calibrate.py',
    'calibrate_l0.py',
    'calibrate_l1.py',
    'calibrate_l2.py',
    'colorline.py',
    'ftptrans.py',
    'hilbert.py',
    'koch.py',
    'ls_l.py',
    'memory.py',
    'showlog.py',
    'spirale.py',
]

# ── Display-Singleton ──────────────────────────────────────
_display = None
_backlight = None
_spi = None

def get_display():
    global _display, _backlight, _spi
    if _display is None:
        from machine import Pin, SPI
        from ili9341 import Display, color565
        _spi = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(13))
        _display = Display(_spi, dc=Pin(2), cs=Pin(15), rst=Pin(15),
                           width=320, height=240, rotation=0)
        _backlight = Pin(21, Pin.OUT)
        _backlight.on()
    return _display, _spi

# ── QR-Code auf Display zeigen ─────────────────────────────
def show_ip(ip):
    from ili9341 import color565
    import gc
    DISP_W = 320
    DISP_H = 240
    print('show_ip: gc.mem_free()=', gc.mem_free())
    display, spi = get_display()
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
        log('Fehler in show_ip: '+ str(e))
        sys.print_exception(e)
        white = color565(255, 255, 255)
        black = color565(0, 0, 0)
        display.draw_text8x8(10, 60, 'QR Fehler:', white, black)
        display.draw_text8x8(10, 80, str(e)[:28], white, black)
    gc.collect()

# ── Programm ausfuehren ────────────────────────────────────
def programm_starten(dateiname):
#     # 1. Snapshot der aktuellen Module machen
#     vorherige_module = set(sys.modules.keys())
    try:
        modul_name = dateiname.replace('/', '').replace('.py', '')
        print('[programm_starten] modul_name=', modul_name)

#        if modul_name in sys.modules:
#            del sys.modules[modul_name]
#            print('[programm_starten] altes Modul aus sys.modules entfernt')

        gc.collect()
        print('[programm_starten] vor __import__ gc.mem_free()=', gc.mem_free())
        modul = __import__(modul_name)
        print('Imported',modul_name)
        if hasattr(modul, "run"):
            print('[programm_starten] rufe run() auf')
            ergebnis = modul.run()
            print('[programm_starten] run() beendet)', ergebnis)
            meminfo()
            return str(ergebnis) if ergebnis is not None else "(kein Rückgabewert)"
        else:
            msg = "Fehler: Keine run()-Funktion in {} gefunden.".format(dateiname)
            print('[programm_starten]', msg)
            return msg
    except Exception as e:
        log('[programm_starten] Exception: '+ str(e))
        sys.print_exception(e)
        return "Fehler: " + str(e)
# ── HTML Seite ─────────────────────────────────────────────
def html_seite(ergebnis=""):
    ip = wlan.ifconfig()[0]
    buttons = ""
    for i in range(0, len(PROGRAMME), 2):
        buttons += "<div class='row'>"
        for p in PROGRAMME[i:i+2]:
            label = p[:-3] if p.endswith('.py') else p
            buttons += (
                "<form method='POST' action='/start' class='btnform'>"
                "<input type='hidden' name='programm' value='" + p + "'>"
                "<button type='submit'>" + label + "</button>"
                "</form>")
        buttons += "</div>"

    # Ergebnis-div: nur anzeigen wenn Text vorhanden
    ergebnis_html = (
        "<div id='ergebnis'>" + ergebnis + "</div>"
        if ergebnis else "<div id='ergebnis' style='display:none'></div>")

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
        "#ergebnis{background:#16213e;border-radius:8px;padding:10px;"
        "margin:14px auto;width:90%;color:#2ecc71;"
        "word-break:break-word}"
        "</style>"
        "<script>"
        # Sanduhr auf Button beim Klick – verschwindet wenn neue Seite lädt
        "document.addEventListener('click',function(e){"
        "  var b=e.target.closest('button[type=submit]');"
        "  if(b){"
        "    b.dataset.label=b.textContent;"
        "    b.style.background='#e67e22';"
        "    b.textContent='\u23f3 '+b.dataset.label;"
        "  }"
        "});"
        "</script>"
        "</head>"
        "<body>"
        "<h1>&#9889; ESP32 Launcher</h1>"
        + buttons
        + ergebnis_html +
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

def send_response(conn, html, content_type='text/html; charset=utf-8'):
    response = html.encode()
    header = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: {}\r\n"
        "Connection: close\r\n"
        "Content-Length: {}\r\n\r\n"
    ).format(content_type, len(response))
    conn.sendall(header.encode() + response)

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
def unload_module(name):
    to_remove = [k for k in sys.modules if k == name or k.startswith(name + '.')]
    for k in to_remove:
        del sys.modules[k]
    gc.collect()
# ── Webserver starten ──────────────────────────────────────
server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('', 80))
server.listen(3)
print("Webserver: http://{}".format(wlan.ifconfig()[0]))
print('Vor show_ip gc.mem_free()=', gc.mem_free())
show_ip(wlan.ifconfig()[0])
print('Nach show_ip gc.mem_free()=', gc.mem_free())
gc.collect()
print('gc.collect() gc.mem_free()=', gc.mem_free())

# ── Hauptschleife ──────────────────────────────────────────
while True:
    conn = None
    try:
        conn, addr = server.accept()
        print('Verbindung von', addr)
        
        # WICHTIG: Kurzer Timeout für den Request-Empfang
        conn.settimeout(5)
        
        req = conn.recv(4096)
        if not req:
            conn.close()
            continue

        methode, pfad, body = parse_request(req)
        print('Request:', methode, pfad)

        if "favicon" in pfad:
            conn.sendall(b"HTTP/1.0 404 Not Found\r\n\r\n")
            conn.close()
            continue

        # === POST /start ===
        if methode == 'POST' and pfad == '/start':
            prog = parse_body(body)
            print('Programm:', prog)

            if prog:
                # Timeout aufheben für längere Operationen
                conn.settimeout(None)
                
                # SONDERFALL: ftptrans
                if 'ftptrans' in prog:
                    print("[INFO] Starte ftptrans...")
                    try:
                        conn.close()
                    except:
                        pass
                    try:
                        server.close()
                    except:
                        pass
                    
                    gc.collect()
                    modul = __import__('ftptrans')
                    print('modul.run()',prog)
                    modul.run()
                    sys.exit()

                # NORMALER ABLAUF
                print("[INFO] Starte:", prog)
                gc.collect()
                
                try:
                    ergebnis = programm_starten(prog)
                    print('programm_starten',prog,'returned',ergebnis)
                except Exception as e:
                    ergebnis = "Fehler in programm_starten: " + str(e)
                    print("[FEHLER]", ergebnis)
                
                # Modul aufräumen
                modul_name = prog[:-3] if prog.endswith('.py') else prog
                unload_module(modul_name)
                gc.collect()
                
                # Antwort senden
                try:
                    send_response(conn, html_seite(ergebnis=ergebnis))
                except Exception as e:
                    print("[WEB] Sendefehler:", e)
                finally:
                    try:
                        conn.close()
                    except:
                        pass
            else:
                send_response(conn, html_seite())
                conn.close()

        # === GET / (Hauptseite) ===
        elif pfad == '/':
            conn.settimeout(None)
            t0 = time.ticks_ms()
            
            # Ergebnis anzeigen und SOFORT zurücksetzen
            aktuelles_ergebnis = ergebnis
            ergebnis = ""  # ← Sofort zurücksetzen!
            gc.collect()
            html = html_seite(ergebnis=aktuelles_ergebnis)
            gc.collect()
            print('HTML generiert in', time.ticks_diff(time.ticks_ms(), t0), 'ms')
            
            try:
                send_response(conn, html)
                if _display:
                    release_display()
                gc.collect()
            except Exception as e:
                print("[WEB] Sendefehler:", e)
            finally:
                try:
                    conn.close()
                except:
                    pass

        # === Alles andere ===
        else:
            send_response(conn, html_seite())
            conn.close()

    except OSError as e:
        # Timeout oder Socket-Fehler
        print("OS-Fehler:", e)
        if conn:
            try:
                conn.close()
            except:
                pass
        gc.collect()
        
    except Exception as e:
        print("Serverfehler:", e)
        sys.print_exception(e)
        if conn:
            try:
                conn.close()
            except:
                pass
        gc.collect()