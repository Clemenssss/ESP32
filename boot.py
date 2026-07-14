# This file is executed on every boot (including wake-boot from deepsleep)
# boot.py
import network
import time
from machine import Pin
from credentials import get_credentials
from logger import logger
time.sleep_ms(200)
# ── RGB-LED Pins (Cheap Yellow Display, active LOW: LOW = an, HIGH = aus)
LED_ROT   = Pin(4,  Pin.OUT, value=1)   # 1 = aus beim Start
LED_GRUEN = Pin(16, Pin.OUT, value=1)
LED_BLAU  = Pin(17, Pin.OUT, value=1)

def led_on(led):
    led.off()   # active low
def led_off(led):
    led.on()

def blink_led(led, count=1, on_ms=400, off_ms=400):
    for _ in range(count):
        led_on(led)
        time.sleep_ms(on_ms)
        led_off(led)
        time.sleep_ms(off_ms)
def log_connect_set_time():
    import ntptime
    ntptime.host = "fritz.box"
    try:
        # Manchmal braucht UDP/NTP direkt nach dem Connect noch 1-2 Sekunden
        time.sleep(1) 
        ntptime.settime()
        logger.log("NTP OK:" , str(time.localtime()))
        return True
    except Exception as e:
        logger.log("NTP Fehler: " ,  str(e))
        return False
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
    logger.log('credentiaLS read')
    if not wlan.isconnected():
        logger.log("Verbinde mit:",  str(ssid))
        wlan.connect(ssid, password)
        
        timeout = 15           # Sekunden
        start = time.time()
        logger.log('time received ', str(start))
        while not wlan.isconnected():
            logger.log('not wlan.isconnected()')
            if time.time() - start > timeout:
                break
            time.sleep(0.5)
            print('.', end='')
    # JETZT erst prüfen, ob wir wirklich drin sind, BEVOR NTP geladen wird
    if wlan.isconnected():
        # Erst Zeit holen...
        ntp_success = log_connect_set_time()
        
        # ...dann IP loggen
        logger.log("WLAN verbunden → IP: " ,  str(wlan.ifconfig()[0]))
        
        # Wenn NTP geklappt hat -> Grün. Wenn WLAN da, aber NTP tot -> Blau/Gelb/oder trotzdem Grün
        blink_led(LED_GRUEN, count=3, on_ms=800, off_ms=800)   
        
        # Wichtig: hostname setzen solange wlan aktiv ist
        wlan.config(dhcp_hostname='esp32')
    else:
        logger.log("WLAN-Verbindung fehlgeschlagen!")
        blink_led(LED_ROT, count=5, on_ms=200, off_ms=200)
        led_on(LED_ROT)          
else:
    logger.log("Keine gültigen Credentials gefunden!")
    blink_led(LED_ROT, count=4, on_ms=300, off_ms=700)   
    led_on(LED_ROT)
# Ende von boot.py → main.py wird automatisch gestartet (falls vorhanden)