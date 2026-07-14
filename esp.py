import serial
import time

PORT = "COM4"  # oder /dev/ttyUSB0
ser = serial.Serial(PORT, 115200, timeout=0.05)

# Reset auslösen über DTR/RTS (wie beim USB-Serial-Chip üblich)
ser.dtr = False
ser.rts = True
time.sleep(0.1)
ser.rts = False
time.sleep(0.05)

# Sofort und für ~2 Sekunden mit Ctrl-C fluten
end = time.time() + 2
while time.time() < end:
    ser.write(b'\x03')  # Ctrl-C
    time.sleep(0.01)

time.sleep(0.3)
print(ser.read(4000).decode(errors='replace'))
ser.close()