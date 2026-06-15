from machine import Pin
import utime

class LED:
    def __init__(self, r_pin=4, g_pin=16, b_pin=17):
        # Active LOW: value=1 = aus
        self.r = Pin(r_pin, Pin.OUT, value=1)
        self.g = Pin(g_pin, Pin.OUT, value=1)
        self.b = Pin(b_pin, Pin.OUT, value=1)
        self._off()
    
    def _off(self):
        self.r.value(1)
        self.g.value(1)
        self.b.value(1)
    
    def off(self):
        self._off()
    
    def on(self, color='green', ms=0):
        self._off()
        c = color.lower()
        # Active LOW: 0 = an
        if c == 'red':
            self.r.value(0)
        elif c == 'green':
            self.g.value(0)
        elif c == 'blue':
            self.b.value(0)
        elif c == 'yellow':
            self.r.value(0)
            self.g.value(0)
        elif c == 'white':
            self.r.value(0)
            self.g.value(0)
            self.b.value(0)
        
        if ms:
            utime.sleep_ms(ms)
            self._off()
    
    def blink(self, color='green', times=3, on_ms=150, off_ms=100):
        for _ in range(times):
            self.on(color)
            utime.sleep_ms(on_ms)
            self._off()
            utime.sleep_ms(off_ms)
    
    def sequence(self, colors, on_ms=200):
        """['red', 'blue', 'green'] nacheinander"""
        for color in colors:
            self.on(color, on_ms)

# Verwendung:
led = LED()

# Statt _display.draw_text8x8:
# led.on('red', 500)      # Rot 500ms
# led.blink('green', 1)   # Einmal grün blinken
# led.sequence(['red', 'blue', 'green'])  # Rot-Blau-Grün nacheinander