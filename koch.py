# koch.py - Koch Schneeflocke mit Line Clipping
from machine import Pin, SPI
from ili9341 import Display, color565
import math, time, gc

# SPI und Display global initialisieren, damit es beim Import bereitsteht
spi = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(13))
display = Display(spi, dc=Pin(2), cs=Pin(15), rst=Pin(15),
                  width=320, height=240, rotation=0)

W = 320
H = 240
SCHWARZ = color565(0, 0, 0)
FARBEN  = [
    color565(0,   0,   255),
    color565(0,   255, 255),
    color565(0,   255, 0  ),
    color565(255, 0,   0  ),
    color565(255, 0,   255),
]

# ── Geometrie ──────────────────────────────────────────────
SEITE = 277
GX1   = (W - SEITE) // 2
GX2   = GX1 + SEITE
GY    = 239
HOEHE = int(SEITE * math.sqrt(3) / 2)
SPX   = W // 2
SPY   = GY - HOEHE

# ── Cohen-Sutherland Clipping ──────────────────────────────
INSIDE, LEFT, RIGHT, BOTTOM, TOP = 0, 1, 2, 4, 8
X_MIN, X_MAX, Y_MIN, Y_MAX = 0, 319, 0, 239

def region(x, y):
    code = INSIDE
    if   x < X_MIN: code |= LEFT
    elif x > X_MAX: code |= RIGHT
    if   y < Y_MIN: code |= TOP
    elif y > Y_MAX: code |= BOTTOM
    return code

def clip_line(x0, y0, x1, y1):
    c0, c1 = region(x0, y0), region(x1, y1)
    while True:
        if not (c0 | c1):
            return int(x0), int(y0), int(x1), int(y1)
        if c0 & c1:
            return None
        c = c0 if c0 else c1
        if c & BOTTOM:
            x = x0 + (x1-x0) * (Y_MAX-y0) / (y1-y0)
            y = Y_MAX
        elif c & TOP:
            x = x0 + (x1-x0) * (Y_MIN-y0) / (y1-y0)
            y = Y_MIN
        elif c & RIGHT:
            y = y0 + (y1-y0) * (X_MAX-x0) / (x1-x0)
            x = X_MAX
        elif c & LEFT:
            y = y0 + (y1-y0) * (X_MIN-x0) / (x1-x0)
            x = X_MIN
        if c == c0:
            x0, y0, c0 = x, y, region(x, y)
        else:
            x1, y1, c1 = x, y, region(x, y)

def draw_line_clipped(x0, y0, x1, y1, farbe):
    result = clip_line(x0, y0, x1, y1)
    if result:
        display.draw_line(*result, farbe)

# ── Hilfsfunktionen ────────────────────────────────────────
def zeige_dreieck(x1, y1, x2, y2, x3, y3, farbe):
    draw_line_clipped(x1, y1, x2, y2, farbe)
    draw_line_clipped(x2, y2, x3, y3, farbe)
    draw_line_clipped(x3, y3, x1, y1, farbe)

# ── Hilfsfunktion: Spitze berechnen (innen/außen) ────────────────────
def spitze_berechnen(ax, ay, bx, by, links=True):
    mx = (ax + bx) / 2
    my = (ay + by) / 2
    dx = bx - ax
    dy = by - ay
    laenge = math.sqrt(dx*dx + dy*dy)
    h = laenge * math.sqrt(3) / 2
    nx = -dy / laenge
    ny = dx / laenge
    if not links:
        nx = -nx
        ny = -ny
    return mx + nx * h, my + ny * h

# ── Koch: mit inneren und äußeren Dreiecken ab Stufe 2 ───────────────
def koch_neu(ax, ay, bx, by, tiefe, farbe):
    if tiefe == 0:
        return

    p1x = ax + (bx - ax) / 3
    p1y = ay + (by - ay) / 3
    p2x = ax + 2 * (bx - ax) / 3
    p2y = ay + 2 * (by - ay) / 3

    sx_aussen, sy_aussen = spitze_berechnen(p1x, p1y, p2x, p2y, links=True)
    sx_innen, sy_innen = spitze_berechnen(p1x, p1y, p2x, p2y, links=False)

    if tiefe == 1:
        draw_line_clipped(p1x, p1y, sx_aussen, sy_aussen, farbe)
        draw_line_clipped(sx_aussen, sy_aussen, p2x, p2y, farbe)
    else:
        koch_neu(ax, ay, p1x, p1y, tiefe-1, farbe)
        koch_neu(p1x, p1y, sx_aussen, sy_aussen, tiefe-1, farbe)
        koch_neu(sx_aussen, sy_aussen, p2x, p2y, tiefe-1, farbe)
        koch_neu(p2x, p2y, bx, by, tiefe-1, farbe)

        koch_neu(p1x, p1y, sx_innen, sy_innen, tiefe-1, farbe)
        koch_neu(sx_innen, sy_innen, p2x, p2y, tiefe-1, farbe)

    gc.collect()

# ── Launcher Interface ──────────────────────────────────────
def run():
    # Hintergrundbeleuchtung einschalten
    Pin(21, Pin.OUT).on()
    
    display.clear(SCHWARZ)
    print("Zeichne Ausgangsdreieck...")
    zeige_dreieck(GX1, GY, GX2, GY, SPX, SPY, FARBEN[0])

    for stufe in range(1, 5):
        farbe = FARBEN[stufe % len(FARBEN)]
        print("Stufe {}...".format(stufe))
        
        # input("Enter") <-- AUSKOMMENTIERT für automatischen Ablauf im Webserver
        
        # Linke Seite
        koch_neu(GX1, GY, SPX, SPY, stufe, farbe)
        # Rechte Seite
        koch_neu(SPX, SPY, GX2, GY, stufe, farbe)
        # Untere Seite
        koch_neu(GX1, GY, GX2, GY, stufe, farbe)
        
        # Kleine Pause zwischen den Stufen, damit man das Muster wachsen sieht
        time.sleep_ms(500)

    time.sleep(3)
    display.clear(SCHWARZ)
    
    # Hintergrundbeleuchtung ausschalten
    Pin(21, Pin.OUT).off()
    print("koch.py fertig!")
    
    return "Koch-Schneeflocke erfolgreich gezeichnet (Stufen 1-4)."
# Dieser Block springt NUR an, wenn du die Datei direkt in Thonny startest.
# Wird sie über __import__() geladen, bleibt dieser Teil stumm.
if __name__ == "__main__":
    run()