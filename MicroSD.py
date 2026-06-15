import machine
import os
import sdcard

# 1. Setup SPI bus
# The SD card shares SPI with the display, so use the designated pins
spi = machine.SPI(2, baudrate=1000000, polarity=0, phase=0, 
                  sck=machine.Pin(18), mosi=machine.Pin(23), miso=machine.Pin(19))

# 2. Setup CS pin
cs = machine.Pin(4, machine.Pin.OUT)
print('cs = machine.Pin(4, machine.Pin.OUT)')
# 3. Initialize SD card
sd = sdcard.SDCard(spi, cs)
print('sd = sdcard.SDCard(spi, cs)')

# 4. Mount SD card
vfs = os.VfsFat(sd)
print('vfs = os.VfsFat(sd)')

os.mount(vfs, "/sd")
print('os.mount(vfs, "/sd")')

# 5. Perform file operations
print("Files:", os.listdir("/sd"))


# Example: Write a file
with open("/sd/test.txt", "w") as f:
    f.write("Hello from ESP32-2432S028")
    print('f.write...')

# Example: Read a file
with open("/sd/test.txt", "r") as f:
    print(f.read())

# 6. Unmount when done
# os.umount("/sd")
