from machine import reset
from ili9341 import Display
from machine import Pin, SPI
import time
from machine import Pin
Pin(21, Pin.OUT).value(0)  # Backlight-Pin bei der CYD, ggf. anpassen (oft GPIO21 oder GPIO27)
reset()