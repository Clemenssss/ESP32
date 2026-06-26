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

# ── Feste Programmliste ────────────────────────────────────
PROGRAMME = [
    'calibrate.py',
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

# ── Programm ausfuehren ────────────────────────────────────
def programm_starten(dateiname):
    try:
        modul_name = dateiname.replace('/', '').replace('.py', '')
        print('[programm_starten] modul_name=', modul_name)

        if modul_name in sys.modules:
            del sys.modules[modul_name]
            print('[programm_starten] altes Modul aus sys.modules entfernt')

        gc.collect()
        print('[programm_starten] vor __import__ gc.mem_free()=', gc.mem_free())
        modul = __import__(modul_name)

        if hasattr(modul, "run"):
            print('[programm_starten] rufe run() auf')
            ergebnis = modul.run()
            print('[programm_starten] run() beendet, ergebnis=', ergebnis)
            return str(ergebnis) if ergebnis is not None else "(kein Rückgabewert)"
        else:
            msg = "Fehler: Keine run()-Funktion in {} gefunden.".format(dateiname)
            print('[programm_starten]', msg)
            return msg

    except Exception as e:
        import sys as _sys
        print('[programm_starten] Exception:', e)
        _sys.print_exception(e)
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
def html_dashboard():
    ip = wlan.ifconfig()[0]
    return (
        "<!DOCTYPE html><html>"
        "<head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Strommonitor</title>"
        "<style>"
        "body{background:#1a1a2e;color:#eee;font-family:sans-serif;"
        "text-align:center;padding:20px;margin:0}"
        "h1{color:#e94560;margin-bottom:0.5rem}"
        ".kwh{font-size:3.5rem;font-weight:bold;color:#2ecc71;line-height:1.1}"
        ".kwh-unit{font-size:1.2rem;color:#aaa;margin-left:4px}"
        ".kwh-label{font-size:0.8rem;color:#aaa;letter-spacing:0.1em;margin-bottom:0.25rem}"
        ".total{background:#16213e;border-radius:8px;padding:8px;margin:10px auto;"
        "width:90%;font-size:0.9rem;color:#aaa}"
        ".total span{color:#eee;font-weight:bold}"
        ".bars{display:flex;gap:16px;justify-content:center;"
        "align-items:flex-end;margin:16px auto;width:90%;height:200px}"
        ".bar-col{flex:1;display:flex;flex-direction:column;"
        "align-items:center;gap:4px;height:100%}"
        ".bar-outer{width:100%;flex:1;background:#16213e;border-radius:6px;"
        "display:flex;align-items:flex-end;overflow:hidden;"
        "border:1px solid #333;position:relative}"
        ".bar-inner{width:100%;border-radius:6px 6px 0 0;"
        "transition:height 0.6s ease}"
        ".l1{background:#2980b9}"
        ".l2{background:#27ae60}"
        ".l3{background:#e67e22}"
        ".bar-watt{font-size:0.85rem;font-weight:bold;color:#eee}"
        ".bar-amp{font-size:0.7rem;color:#aaa}"
        ".bar-name{font-size:0.8rem;color:#aaa}"
        ".scale{position:absolute;right:3px;top:0;bottom:0;"
        "display:flex;flex-direction:column;justify-content:space-between;"
        "padding:2px 0;pointer-events:none}"
        ".scale span{font-size:9px;color:#666;line-height:1}"
        ".status{font-size:0.75rem;color:#aaa;margin-top:8px}"
        ".dot{display:inline-block;width:8px;height:8px;"
        "border-radius:50%;background:#27ae60;margin-right:4px}"
        ".dot.err{background:#e74c3c}"
        ".back{display:inline-block;margin-top:1rem;padding:8px 20px;"
        "background:#27ae60;color:white;border-radius:8px;"
        "text-decoration:none;font-size:0.9rem}"
        "</style>"
        "</head>"
        "<body>"
        "<h1>&#9889; Strommonitor</h1>"
        "<div class='kwh-label'>TAGESVERBRAUCH</div>"
        "<div><span class='kwh' id='kwh'>–</span>"
        "<span class='kwh-unit'>kWh</span></div>"
        "<div class='total'>Gesamt: <span id='total'>–</span> W"
        " &nbsp;|&nbsp; Skala: <span id='scale-lbl'>–</span></div>"
        "<div class='bars'>"
        "<div class='bar-col'>"
        "<div class='bar-watt' id='w1'>– W</div>"
        "<div class='bar-amp' id='a1'>– A</div>"
        "<div class='bar-outer'>"
        "<div class='bar-inner l1' id='b1' style='height:0%'></div>"
        "<div class='scale' id='sc1'></div></div>"
        "<div class='bar-name'>L1</div></div>"
        "<div class='bar-col'>"
        "<div class='bar-watt' id='w2'>– W</div>"
        "<div class='bar-amp' id='a2'>– A</div>"
        "<div class='bar-outer'>"
        "<div class='bar-inner l2' id='b2' style='height:0%'></div>"
        "<div class='scale' id='sc2'></div></div>"
        "<div class='bar-name'>L2</div></div>"
        "<div class='bar-col'>"
        "<div class='bar-watt' id='w3'>– W</div>"
        "<div class='bar-amp' id='a3'>– A</div>"
        "<div class='bar-outer'>"
        "<div class='bar-inner l3' id='b3' style='height:0%'></div>"
        "<div class='scale' id='sc3'></div></div>"
        "<div class='bar-name'>L3</div></div>"
        "</div>"
        "<div class='status'>"
        "<span class='dot' id='dot'></span>"
        "<span id='stxt'>Verbinde...</span>"
        " &nbsp; <span id='upd'></span></div>"
        "<a class='back' href='/'>&#8592; Launcher</a>"
        "<p><small>IP: " + ip + "</small></p>"
        "<script>"
        "var SCALES=[500,2000,10000,15000];"
        "function pickScale(m){for(var i=0;i<SCALES.length;i++)if(m<=SCALES[i])return SCALES[i];return 15000;}"
        "function fmtScale(v){return v>=1000?(v/1000)+'k':String(v);}"
        "function setScale(id,scale){"
        "var el=document.getElementById(id);"
        "var steps=[scale,Math.round(scale*0.75),Math.round(scale*0.5),Math.round(scale*0.25),0];"
        "el.innerHTML=steps.map(function(v){return'<span>'+fmtScale(v)+'</span>';}).join('');}"
        "function update(d){"
        "var p1=d.p1||0,p2=d.p2||0,p3=d.p3||0;"
        "var mx=Math.max(p1,p2,p3,1);"
        "var sc=pickScale(mx);"
        "document.getElementById('kwh').textContent=(d.kwh||0).toFixed(3);"
        "document.getElementById('total').textContent=(p1+p2+p3).toFixed(0);"
        "document.getElementById('scale-lbl').textContent=fmtScale(sc)+(sc>=1000?'W':'W');"
        "[[p1,'b1','w1','a1','sc1'],[p2,'b2','w2','a2','sc2'],[p3,'b3','w3','a3','sc3']]"
        ".forEach(function(x){"
        "var pct=Math.min(100,(x[0]/sc)*100);"
        "document.getElementById(x[1]).style.height=pct+'%';"
        "document.getElementById(x[2]).textContent=x[0].toFixed(0)+' W';"
        "document.getElementById(x[3]).textContent=(x[0]/240).toFixed(2)+' A';"
        "setScale(x[4],sc);});"
        "document.getElementById('dot').className='dot';"
        "document.getElementById('stxt').textContent='Live';"
        "document.getElementById('upd').textContent=new Date().toLocaleTimeString('de-DE');}"
        "function fetchData(){"
        "fetch('/data').then(function(r){return r.json();})"
        ".then(update)"
        ".catch(function(){"
        "document.getElementById('dot').className='dot err';"
        "document.getElementById('stxt').textContent='Keine Verbindung';});}"
        "fetchData();setInterval(fetchData,2000);"
        "</script>"
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
    try:
        conn, addr = server.accept()
        print('Done conn, addr = server.accept()')
        gc.collect()
        print('while True: gc.mem_free()=', gc.mem_free())
        conn.settimeout(4.0)

        req = conn.recv(4096)
        if not req:
            conn.close()
            continue

        methode, pfad, body = parse_request(req)
        print('methode, pfad, body =', methode, pfad, body)

        if "favicon" in pfad:
            conn.sendall(b"HTTP/1.0 404 Not Found\r\nContent-Type: text/html\r\n\r\n<h1>No Favicon</h1>")
            conn.close()
            continue

        if methode == 'POST' and pfad == '/start':
            prog = parse_body(body)
            print('prog = parse_body(body):', prog)

            if prog:
                conn.settimeout(None)
                # Erst run() ausführen (blockiert bis fertig) – Browser wartet mit Sanduhr
                print("[INFO] Starte Modul:", prog, "gc.mem_free()=", gc.mem_free())
                gc.collect()
                ergebnis = programm_starten(prog)
                print("[INFO] Ergebnis:", ergebnis)
                # Dann Seite mit Ergebnis senden – Browser zeigt sie nach run()-Ende
                send_response(conn, html_seite(ergebnis=ergebnis))
                conn.close()
            else:
                send_response(conn, html_seite())
                conn.close()
        elif pfad == '/':
            conn.settimeout(None)
            t0 = time.ticks_ms()
            html = html_seite()
            print('html_seite() Dauer ms:', time.ticks_diff(time.ticks_ms(), t0))
            send_response(conn, html)
            conn.close()
        elif pfad == '/data':
            import sct
            import json
            v1, v2, v3 = sct.sct_values_get()
            p1 = round(v1 * 240, 1)
            p2 = round(v2 * 240, 1)
            p3 = round(v3 * 240, 1)
            try:
                with open('energy_state.json') as f:
                    state = json.load(f)
                kwh = round(state.get('kwh', 0.0), 4)
            except OSError:
                kwh = 0.0
            body = json.dumps({'p1': p1, 'p2': p2, 'p3': p3, 'kwh': kwh})
            send_response(conn, body, content_type='application/json')
            conn.close()
        elif pfad == '/dashboard':
            send_response(conn, html_dashboard())
            conn.close()            
        else:
            conn.close()

    except Exception as e:
        print("Serverfehler abgefangen:", e)
        try:
            conn.close()
        except:
            pass