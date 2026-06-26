from machine import I2C, Pin
import math
import utime
import json

i2c = I2C(0, sda=Pin(27), scl=Pin(22), freq=400000)
ADS_ADDR   = 0x48
REG_CONV   = 0x00
REG_CONFIG = 0x01

GAIN_FACTOR = 0.0000625      
AMPERE_PER_VOLT = 50.0       

_MUX_DIFF = {0: 0x1000, 1: 0x2000, 2: 0x3000}
_dc_offsets = [0.0, 0.0, 0.0]
def init_ADS1115():
    """ 
    Zwingt den I2C-Bus und den ADS1115-Chip in einen definierten Zustand.
    Löst Blockaden nach unvollständigen Programmabbrüchen (Thonny Stop).
    """
    print("[SCT] Initialisiere und resette Hardware...")
    try:
        # 1. Bus-Cleanup: Sende eine leere Nachricht, um hängende Slaves freizugeben
        i2c.writeto(ADS_ADDR, b'')
        utime.sleep_ms(10)
    except OSError:
        pass

    try:
        # 2. General Call Reset an den I2C-Bus senden (Adresse 0x00, Daten 0x06)
        # Das startet die internen Register des ADS1115 komplett neu.
        i2c.writeto(0x00, b'\x06')
        utime.sleep_ms(50) # Dem Chip Zeit zum Booten geben
        print("[SCT] ADS1115 Hardware-Reset erfolgreich.")
    except OSError as e:
        print("[SCT] Hinweis beim Reset (General Call eventuell nicht quittiert):", e)
def save_calibration():
    with open('sct_cal.json', 'w') as f:
        json.dump(_dc_offsets, f)
        return str(_dc_offsets)

def load_calibration():
    global _dc_offsets
    try:
        with open('sct_cal.json') as f:
            _dc_offsets = json.load(f)
    except OSError:
        pass  

def _ads_read_diff(channel):
    config = (0x8000 | _MUX_DIFF[channel] | 0x0400 | 0x0080 | 0x00E0)
    i2c.writeto_mem(ADS_ADDR, REG_CONFIG, bytes([config >> 8, config & 0xFF]))
    utime.sleep_us(1300)  
    raw = i2c.readfrom_mem(ADS_ADDR, REG_CONV, 2)
    val = (raw[0] << 8) | raw[1]
    if val > 32767:
        val -= 65536
    return val * GAIN_FACTOR

def read_rms(channel, samples=800):
    """ Misst den rohen RMS-Wert ohne Offset (wird hier beibehalten) """
    # Da read_rms im normalen Betrieb seltener aufgerufen wird, lassen wir es,
    # wandeln es aber hier ebenfalls speicherschonend ohne Liste ab!
    summe = 0.0
    quadrat_summe = 0.0
    
    # 1. Durchlauf für den Mittelwert
    for _ in range(samples):
        summe += _ads_read_diff(channel)
    mean = summe / samples
    
    # Da wir differentiell messen und mean hier nachträglich berechnet wird, 
    # simulieren wir die RMS-Berechnung ohne großen Puffer:
    # (Wir lesen neu, was bei konstantem Signal statistisch fast identisch ist)
    for _ in range(samples):
        quadrat_summe += (_ads_read_diff(channel) - mean) ** 2
        
    rms = math.sqrt(quadrat_summe / samples) * AMPERE_PER_VOLT
    return max(rms, 0.0)

# --- 100% Speicherschonende Kalibrierung (Keine Listen mehr!) ---
def calibrate(samples=800):
    """ Ermittelt die exakte Null-Linie (DC-Fehler) ohne RAM-Belastung """
    global _dc_offsets
    print("--- Kalibrierung gestartet (Messe DC-Offsets)... ---")
    
    for ch in range(3):
        summe_spannung = 0.0
        for _ in range(samples):
            summe_spannung += _ads_read_diff(ch)
        
        # Durchschnitt direkt berechnen, ohne jemals eine Liste erstellt zu haben
        _dc_offsets[ch] = summe_spannung / samples
    print("Hardware-Spannungsoffsets gelernt:", str(_dc_offsets))    
    return "Hardware-Spannungsoffsets gelernt: "+ str(_dc_offsets)   
    

# --- 100% Speicherschonende RMS-Berechnung ---
def read_rms_calibrated(channel, samples=800):
    """ Berechnet RMS direkt im kontinuierlichen Datenstrom """
    offset = _dc_offsets[channel]
    
    # Um RMS mathematisch korrekt ohne Liste (Puffer) in einem Rutsch zu berechnen,
    # nutzen wir die Standardformel für Varianz: Var(X) = E[X^2] - (E[X])^2
    summe_spannung = 0.0
    summe_quadrate = 0.0
    
    for _ in range(samples):
        # Hardware-Fehler sofort abziehen
        v = _ads_read_diff(channel) - offset
        summe_spannung += v
        summe_quadrate += v * v
        
    # Mathematische Auswertung des RMS über die Summen
    mean = summe_spannung / samples
    mittleres_quadrat = summe_quadrate / samples
    varianz = mittleres_quadrat - (mean * mean)
    
    # Falls durch minimale Rundungsfehler unter Null, abfangen:
    if varianz < 0: 
        varianz = 0.0
        
    rms = math.sqrt(varianz) * AMPERE_PER_VOLT
    
    # Physikalischer Filter für das absolute Restrauschen im Äther
    if rms < 0.015:
        return 0.0
    return rms

def sct_values_get(calibrated=True):
    fn = read_rms_calibrated if calibrated else read_rms
    return fn(0), fn(1), fn(2)

def show_values(v1, v2, v3):
    from ili9341 import color565
    from main import get_display 
    
    BLACK  = color565(0, 0, 0)
    GREEN  = color565(0, 255, 0)
    YELLOW = color565(255, 255, 0)
    WHITE  = color565(255, 255, 255)
    
    display = get_display()
    if display:
        display.clear(BLACK)
        display.draw_text8x8(10, 20,  "Strommonitor",          WHITE,  BLACK)
        display.draw_text8x8(10, 60,  "L1: {:6.2f} A".format(v1), GREEN,  BLACK)
        display.draw_text8x8(10, 100, "L2: {:6.2f} A".format(v2), GREEN,  BLACK)
        display.draw_text8x8(10, 140, "L3: {:6.2f} A".format(v3), GREEN,  BLACK)
        display.draw_text8x8(10, 190, "Σ:  {:6.2f} A".format(v1+v2+v3), YELLOW, BLACK)