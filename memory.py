# speicherinfo.py — Zeigt Speicher und Dateien auf dem Display an
import os
from machine import Pin, SPI
from ili9341 import Display, color565
import time

# Globale Konstanten
W = 320
H = 240
SCHWARZ = color565(0, 0, 0)
WEISS   = color565(255, 255, 255)
GELB    = color565(0, 255, 255)
GRUEN   = color565(0, 255, 0)
ROT     = color565(0, 0, 255)

# Platzhalter fürs Display-Objekt
display = None

def run():
    global display
    
    # Hardware-Initialisierung bei jedem Start frisch
    spi = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(13))
    display = Display(spi, dc=Pin(2), cs=Pin(15), rst=Pin(15),
                      width=W, height=H, rotation=0)
    
    backlight = Pin(21, Pin.OUT)
    backlight.on()
    
    display.clear(SCHWARZ)

    # ── Speicherinfo ───────────────────────────────────────────
    fs     = os.statvfs('/')
    block  = fs[0]
    frei   = fs[3] * block
    gesamt = fs[2] * block
    belegt = gesamt - frei

    # Titel
    display.draw_text8x8(5, 5, "ESP32 Speicher", GELB, SCHWARZ)
    display.draw_hline(0, 16, W, GELB)

    # Übersicht
    display.draw_text8x8(5, 22, 
        "Gesamt: {:>6} KB".format(gesamt//1024), WEISS, SCHWARZ)
    display.draw_text8x8(5, 34, 
        "Belegt: {:>6} KB".format(belegt//1024), ROT,   SCHWARZ)
    display.draw_text8x8(5, 46, 
        "Frei:   {:>6} KB".format(frei//1024),   GRUEN, SCHWARZ)

    # Balken
    display.draw_hline(0, 58, W, WEISS)
    balken = int(W * belegt / gesamt)
    display.fill_rectangle(0,   60, balken,       10, ROT)
    display.fill_rectangle(balken, 60, W - balken, 10, GRUEN)
    display.draw_hline(0, 71, W, WEISS)

    # Dateiliste
    display.draw_text8x8(5, 75, "Dateien:", GELB, SCHWARZ)

    y = 87
    for f in sorted(os.listdir('/')):
        size = os.stat('/' + f)[6]
        zeile = "{:16s}{:>5}B".format(f[:16], size)
        display.draw_text8x8(5, y, zeile, WEISS, SCHWARZ)
        y += 12
        if y > 228:  # Display voll
            display.draw_text8x8(5, y, "... mehr Dateien", GELB, SCHWARZ)
            break

    print("speicherinfo.py fertig!")
    return 'memory shown on CYD'
    # HIER WICHTIG: 
    # Wenn die main.py sofort danach wieder die Kontrolle übernimmt, 
    # wollen wir das Backlight vermutlich AN lassen, damit man die Infos lesen kann!
    # Falls das Display gelöscht werden soll, nimm die Raute bei den Zeilen unten weg:
    # time.sleep(5)  # Zeige die Info für 5 Sekunden
    # display.clear(SCHWARZ)
    # backlight.off()

# Ermöglicht das Testen direkt aus Thonny
if __name__ == "__main__":
    run()