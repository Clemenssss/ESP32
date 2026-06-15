# spirale.py
from machine import Pin, SPI
from ili9341 import Display, color565
import math, time

spi = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(13))
display = Display(spi, dc=Pin(2), cs=Pin(15), rst=Pin(15),
                  width=320, height=240, rotation=0)
Pin(21, Pin.OUT).on()

W  = 320
H  = 240
MX = W // 2
MY = H // 2

ABSTAND   = 1
WINDUNGEN = 12   # mehr Windungen damit Ecken sicher erreicht

# Bis zur Ecke = Diagonale
MAX_R = math.sqrt(MX**2 + MY**2) + 10  # +10 Puffer für Ecken

SCHWARZ = color565(0, 0, 0)

SPIRAL_FARBEN = [
    color565(0,   0,   255),
    color565(0,   128, 255),
    color565(0,   255, 255),
    color565(0,   255, 128),
    color565(0,   255, 0  ),
]

def spirale_zeichnen(loeschen=False):
    anzahl  = len(SPIRAL_FARBEN)
    a       = MAX_R / (WINDUNGEN * 2 * math.pi)
    schritte = int(WINDUNGEN * 2 * math.pi * 40)  # 40 Punkte pro Radian

    prev = [(MX, MY)] * anzahl

    for i in range(schritte + 1):
        winkel = (i / schritte) * WINDUNGEN * 2 * math.pi

        for s in range(anzahl):
            r = a * winkel + (s - anzahl // 2) * ABSTAND

            x = int(MX + r * math.cos(winkel))
            y = int(MY + r * math.sin(winkel))
            # kein Clipping → Display ignoriert Pixel außerhalb einfach

            farbe = SCHWARZ if loeschen else SPIRAL_FARBEN[s]
            display.draw_line(prev[s][0], prev[s][1], x, y, farbe)
            prev[s] = (x, y)

# ── 2 Durchläufe ──────────────────────────────────────────
for durchlauf in range(2):
    display.clear(SCHWARZ)
    spirale_zeichnen(loeschen=False)
    time.sleep(1)
    spirale_zeichnen(loeschen=True)
    time.sleep(1)

display.clear(SCHWARZ)
Pin(21, Pin.OUT).off()
print("spirale.py fertig!")