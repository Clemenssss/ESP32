import socket
import network

def _html(loginhalt):
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Log</title>
<style>body{{background:#111;color:#0f0;font-family:monospace;padding:20px;}}</style>
</head><body>
<h1>system_log.txt</h1>
<pre>{loginhalt}</pre>
</body></html>"""

def letzte_zeilen(pfad="system_log.txt", anzahl=10):
    try:
        with open(pfad, 'rb') as f:
            return [line.decode('utf-8').rstrip() 
                    for line in f.read().split(b'\n') if line.strip()][-anzahl:]
    except OSError as e:
        return [f"FEHLER: {e}"]

def run():
    if not network.WLAN(network.STA_IF).isconnected():
        return "WLAN nicht verbunden"
    
    ip = network.WLAN(network.STA_IF).ifconfig()[0]
    zeilen = letzte_zeilen()
    inhalt = '\n'.join(zeilen)
    
    html = _html(inhalt)
    response = html.encode('utf-8')
    
    header = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(response)}\r\n\r\n"
    
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('', 81))
    srv.listen(1)
    srv.settimeout(20)
    
    print(f"Warte auf http://{ip}:81")
    
    try:
        conn, _ = srv.accept()
        conn.recv(1024)
        conn.send(header.encode() + response)
        conn.close()
        print("Seite gesendet!")
        return "OK"
    except:
        return "Timeout"
    finally:
        srv.close()
# Direktstart aus Thonny
if __name__ == '__main__':
    ergebnis = run()
    print('Ergebnis:', ergebnis)