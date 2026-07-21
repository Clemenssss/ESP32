# boot.py
import network
import time
import gc
from machine import Pin
from credentials import get_credentials
from logger import logger

def run_boot():
    time.sleep_ms(200)
    
    # LEDs lokal definieren (werden nach Funktionsende automatisch gelöscht)
    led_rot   = Pin(4,  Pin.OUT, value=1)
    led_gruen = Pin(16, Pin.OUT, value=1)
    led_blau  = Pin(17, Pin.OUT, value=1)

    # Inline-Hilfsfunktionen sparen globalen RAM
    def blink(led, count, on_ms, off_ms):
        for _ in range(count):
            led.off() # active low = an
            time.sleep_ms(on_ms)
            led.on()  # aus
            time.sleep_ms(off_ms)

    print("boot.py → WLAN initialisieren")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    # Tupel-Entpacken optimieren (Vermeidung von Dummy-Variablen)
    ssid, password = get_credentials('/credentials.txt')[:2]
    
    if not (ssid and password):
        logger.log("Keine gültigen Credentials gefunden!")
        blink(led_rot, 4, 300, 700)
        led_rot.off()
        return

    logger.log('credentials read')
    
    if not wlan.isconnected():
        # F-Strings (ab MicroPython 1.12+) oder %-Formatierung nutzen statt str()-Verkettung
        logger.log("Verbinde mit: %s" % ssid)
        wlan.connect(ssid, password)
        
        timeout = 15
        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > timeout:
                break
            time.sleep_ms(500) # sleep_ms verbraucht weniger Ressourcen als sleep
            print('.', end='')
            
    if wlan.isconnected():
        # NTP-Logik direkt hier einbetten (spart Funktions-Overhead)
        import ntptime
        ntptime.host = "fritz.box"
        time.sleep(1) 
        try:
            ntptime.settime()
            logger.log("NTP OK: %s" % str(time.localtime()))
        except Exception as e:
            logger.log("NTP Fehler: %s" % e)
            
        logger.log("WLAN verbunden → IP: %s" % wlan.ifconfig()[0])
        wlan.config(dhcp_hostname='esp32')
        blink(led_gruen, 3, 800, 800)
    else:
        logger.log("WLAN-Verbindung fehlgeschlagen!")
        blink(led_rot, 5, 200, 200)
        led_rot.off()

# 1. Boot-Logik in geschütztem Namensraum ausführen
run_boot()

# 2. Die Funktion und nicht mehr benötigte Imports rigoros aus dem RAM löschen
del run_boot
if 'ntptime' in globals(): del ntptime

# 3. Speicher sofort defragmentieren, BEVOR main.py startet
gc.collect()