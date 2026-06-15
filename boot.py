# This file is executed on every boot (including wake-boot from deepsleep)
# boot.py
import network
import time
from machine import Pin
from credentials import get_credentials

# ── RGB-LED Pins (Cheap Yellow Display, active LOW: LOW = an, HIGH = aus)
LED_ROT   = Pin(4,  Pin.OUT, value=1)   # 1 = aus beim Start
LED_GRUEN = Pin(16, Pin.OUT, value=1)
LED_BLAU  = Pin(17, Pin.OUT, value=1)

def led_on(led):    led.off()   # active low
def led_off(led):   led.on()

def blink_led(led, count=1, on_ms=400, off_ms=400):
    for _ in range(count):
        led_on(led)
        time.sleep_ms(on_ms)
        led_off(led)
        time.sleep_ms(off_ms)

# Alle LEDs sicher aus
led_off(LED_ROT)
led_off(LED_GRUEN)
led_off(LED_BLAU)


# ── WLAN-Verbindung versuchen ──────────────────────────────────
print("boot.py → WLAN initialisieren")
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
ssid, password, _, _ = get_credentials('/credentials.txt')
print('ssid, password = ',ssid, password)
if ssid and password:
    if not wlan.isconnected():
        print("Verbinde mit:", ssid)
        wlan.connect(ssid, password)
        
        timeout = 12           # Sekunden
        start = time.time()
        
        while not wlan.isconnected():
            if time.time() - start > timeout:
                break
            time.sleep(0.5)
            print('.', end='')
        print()  # Zeilenumbruch
    
    if wlan.isconnected():
        print("WLAN verbunden → IP:", wlan.ifconfig()[0])
        blink_led(LED_GRUEN, count=3, on_ms=800, off_ms=800)   # Erfolg
        connected = True
        wlan = network.WLAN(network.STA_IF)
        wlan.config(dhcp_hostname='esp32')
    else:
        print("WLAN-Verbindung fehlgeschlagen!")
        # Fehleranzeige: 5× kurzes Blinken + rot dauerhaft an (als Warnung)
        blink_led(LED_ROT, count=5, on_ms=200, off_ms=200)
        led_on(LED_ROT)          # bleibt an als Dauer-Signal
        # KEINE while True !!!
else:
    print("Keine gültigen Credentials gefunden!")
    blink_led(LED_ROT, count=4, on_ms=300, off_ms=700)   # anderes Muster
    led_on(LED_ROT)   # bleibt an

# Ende von boot.py → main.py wird automatisch gestartet (falls vorhanden)