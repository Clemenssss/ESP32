# hilbert.py
from machine import Pin, SPI
from ili9341 import Display, color565
import time, gc

spi = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(13))
display = Display(spi, dc=Pin(2), cs=Pin(15), rst=Pin(15),
                  width=320, height=240, rotation=0)
Pin(21, Pin.OUT).on()

W  = 320
H  = 240

SCHWARZ = color565(0, 0, 0)
FARBEN  = [
    color565(0,   0,   255),
    color565(0,   128, 255),
    color565(0,   255, 255),
    color565(0,   255, 128),
    color565(0,   255, 0  ),
    color565(128, 255, 0  ),
    color565(255, 255, 0  ),
    color565(255, 128, 0  ),
]

def hilbert_punkt(i, n):
    """Berechnet einen einzelnen Punkt on-the-fly — kein Array!"""
    x = 0
    y = 0
    s = 1
    t = i
    while s < n:
        rx = 1 if (t & 2) else 0
        ry = 1 if (t & 1) ^ rx else 0
        if ry == 0:
            if rx == 1:
                x = s - 1 - x
                y = s - 1 - y
            x, y = y, x
        x += s * rx
        y += s * ry
        t >>= 2
        s <<= 1
    return x, y

def kurve_zeichnen(ordnung, loeschen=False):
    n      = 2 ** ordnung
    gesamt = n * n

    # Auf volles Display strecken (nicht quadratisch!)
    scale_x = (W - 2) / (n - 1)
    scale_y = (H - 2) / (n - 1)

    # Ersten Punkt berechnen
    x0, y0 = hilbert_punkt(0, n)
    px0 = int(x0 * scale_x) + 1
    py0 = int(y0 * scale_y) + 1

    for i in range(1, gesamt):
        # Nächsten Punkt on-the-fly berechnen
        x1, y1 = hilbert_punkt(i, n)
        px1 = int(x1 * scale_x) + 1
        py1 = int(y1 * scale_y) + 1

        if loeschen:
            farbe = SCHWARZ
        else:
            farbe = FARBEN[(i * len(FARBEN) // gesamt) % len(FARBEN)]

        display.draw_line(px0, py0, px1, py1, farbe)

        px0, py0 = px1, py1

        # Alle 256 Punkte Garbage Collection
        if i % 256 == 0:
            gc.collect()

# ── Ordnung wählen ─────────────────────────────────────────
ORDNUNG = 6   # jetzt kein RAM-Problem mehr!

gc.collect()
print("RAM frei:", gc.mem_free())

for durchlauf in range(1):
    display.clear(SCHWARZ)

    print("Zeichne Ordnung {}...".format(ORDNUNG))
    kurve_zeichnen(ORDNUNG, loeschen=False)
    time.sleep(1)

    print("Lösche...")
    kurve_zeichnen(ORDNUNG, loeschen=True)
    time.sleep(1)

display.clear(SCHWARZ)
Pin(21, Pin.OUT).off()
print("hilbert.py fertig!")
### Was sich geändert hat:
#```
#Vorher:
#───────
#alle 4096 Punkte berechnen → Liste im RAM
#→ reicht nicht für Ordnung 6!
#
#Jetzt:
#──────
#hilbert_punkt(i, n) berechnet
#jeden Punkt einzeln on-the-fly
#→ nur 2 Punkte gleichzeitig im RAM!
#→ Ordnung 6, 7, 8 kein Problem mehr
#
#Seitenverhältnis:
#─────────────────
#Vorher: quadratisch (230×230)
#        → Rand links/rechts
#
#Jetzt:  scale_x und scale_y getrennt
#        → volles Display 320×240
#        → kein Rand mehr!