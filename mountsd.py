import os
from machine import Pin, SPI
import sdcard
import time

# Pins für das CYD
SCK_PIN  = 14
MOSI_PIN = 13
MISO_PIN = 12 # Wir bleiben erst mal bei 12
SD_CS    = 5
TFT_CS   = 15

print("--- CYD SD-Hardcore-Initialisierung ---")

# 1. WICHTIG: Alle CS Pins auf High setzen (Deaktivieren)
# Wenn TFT_CS auf Low steht, blockiert das Display den Bus!
tft_cs_pin = Pin(TFT_CS, Pin.OUT, value=1)
sd_cs_pin  = Pin(SD_CS, Pin.OUT, value=1)

# 2. SPI ganz langsam starten
spi = SPI(1, baudrate=100000, sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(MISO_PIN))

time.sleep(0.2) # Kurz warten, damit sich die Signale fangen

try:
    print("Versuche Mount...")
    sd = sdcard.SDCard(spi, sd_cs_pin)
    os.mount(sd, "/sd")
    print("ERFOLG! Karte gefunden.")
    print("Dateien:", os.listdir("/sd"))
    os.umount("/sd")
except Exception as e:
    print("Fehler:", e)
    print("\nTIPP: Falls 'Initialisierung fehlgeschlagen':")
    print("1. Karte nochmal neu in FAT32 formatieren (kein Schnellformat).")
    print("2. Karte im Slot festdrücken (die billigen Slots leiern schnell aus).")
    print("3. Sicherstellen, dass die SD-Karte max. 32GB groß ist (SDHC).")