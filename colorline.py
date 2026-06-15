# ringe.py — läuft durch und kehrt zurück
from machine import Pin, SPI
from ili9341 import Display, color565
import time

# Globale Konstanten können oben stehen bleiben
W = 320
H = 240
FARBEN = [
    color565(0,   0,   255),
    color565(0,   255, 0  ),
    color565(255, 0,   0  ),
    color565(0,   255, 255),
    color565(255, 0,   255),
    color565(255, 255, 0  ),
]
SCHWARZ = color565(0, 0, 0)
max_ringe = min(W, H) // 2

# Die Display-Variable definieren wir als None, sie wird in run() initialisiert
display = None

def zeichne_ring(r, farbe):
    # Zugriff auf das globale Display-Objekt
    x0, y0 = r, r
    x1, y1 = W - r - 1, H - r - 1
    display.draw_hline(x0, y0, x1 - x0, farbe)
    display.draw_hline(x0, y1, x1 - x0, farbe)
    display.draw_vline(x0, y0, y1 - y0, farbe)
    display.draw_vline(x1, y0, y1 - y0, farbe)

# Die Hauptfunktion, die von deiner main.py aufgerufen wird
def run():
    global display
    
    # Hardware-Initialisierung (passiert jetzt bei jedem Start frisch)
    spi = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(13))
    display = Display(spi, dc=Pin(2), cs=Pin(15), rst=Pin(15),
                      width=320, height=240, rotation=0)
    
    backlight = Pin(21, Pin.OUT)
    backlight.on()

    # ── 1x Durchlauf ──────────────────────────────────────────
    for durchlauf in range(1):
        # Von außen nach innen
        for r in range(max_ringe):
            farbe = FARBEN[(r // 3) % len(FARBEN)]
            zeichne_ring(r, farbe)
            time.sleep_ms(15)
        time.sleep(1)

        # Von innen nach außen löschen
        for r in range(max_ringe - 1, -1, -1):
            zeichne_ring(r, SCHWARZ)
            time.sleep_ms(15)
        time.sleep(1)

    # ── Fertig → Display leer lassen ──────────────────────────
    display.clear(SCHWARZ)
    backlight.off()  # Hintergrundlicht aus
    print("colorline.py fertig!")
    return "colorline.py fertig!"
# Dieser Block sorgt dafür, dass du das Skript trotzdem noch 
# direkt in Thonny mit "Run" starten kannst zum Testen!
if __name__ == "__main__":
    run()