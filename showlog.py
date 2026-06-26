# showlog.py — Zeigt /system_log.txt als Webseite auf Port 81
# Startbar aus main.py (run()-Technik) oder direkt aus Thonny

import socket
import network

LOG_FILE = '/system_log.txt'
PORT = 81

def _read_log():
    try:
        with open(LOG_FILE, 'r') as f:
            inhalt = f.read()
        if not inhalt.strip():
            return '(Datei ist leer)'
        return inhalt
    except OSError:
        return f'Fehler: {LOG_FILE} nicht gefunden.'

def _html(inhalt):
    return (
        "<!DOCTYPE html><html>"
        "<head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>system_log.txt</title>"
        "<style>"
        "body{background:#1a1a2e;color:#eee;font-family:monospace;"
        "padding:16px;margin:0}"
        "h2{color:#e94560;margin-bottom:8px}"
        "pre{background:#0f0f1a;border:1px solid #333;border-radius:6px;"
        "padding:12px;white-space:pre-wrap;word-break:break-all;"
        "font-size:0.85em;line-height:1.5em;max-height:80vh;overflow-y:auto}"
        "small{color:#888}"
        "</style>"
        "</head>"
        "<body>"
        "<h2>&#128196; system_log.txt</h2>"
        "<pre>" + inhalt + "</pre>"
        "<p><small>Einmalige Anzeige – Verbindung wird danach geschlossen.</small></p>"
        "</body></html>"
    )

def run():
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        return 'WLAN nicht verbunden.'

    ip = wlan.ifconfig()[0]
    inhalt = _read_log()
    html = _html(inhalt)
    response = html.encode('utf-8')
    header = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "Connection: close\r\n"
        "Content-Length: {}\r\n\r\n"
    ).format(len(response))

    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('', PORT))
    srv.listen(1)
    srv.settimeout(30)  # 30 Sek warten, dann aufgeben

    print(f'showlog: Warte auf Verbindung: http://{ip}:{PORT}')
    print(f'         Log-Größe: {len(inhalt)} Zeichen')

    try:
        conn, addr = srv.accept()
        conn.settimeout(5)
        try:
            conn.recv(1024)  # Request lesen (wegwerfen)
        except:
            pass
        conn.send(header.encode() + response)
        conn.close()
        print('showlog: Seite ausgeliefert, fertig.')
        return f'Log angezeigt ({len(inhalt)} Zeichen). http://{ip}:{PORT}'
    except OSError:
        return 'showlog: Timeout – niemand hat sich verbunden (30 Sek).'
    finally:
        srv.close()

# Direktstart aus Thonny
if __name__ == '__main__':
    ergebnis = run()
    print('Ergebnis:', ergebnis)