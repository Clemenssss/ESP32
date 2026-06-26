#import sct
#sct.calibrate()
#sct.save_calibration()
#print('New calibration saved')
import sct
import sys
import time
from logger import log

def run():
    # 1. Herausfinden, wer dieses Programm gestartet hat
    caller = "direkt/Thonny" if __name__ == "__main__" else "programm_starten"
    print(f"--- Kalibrierung gestartet (Aufruf durch: {caller}) ---")
    log(f"--- Kalibrierung gestartet (Aufruf durch: {caller}) ---")
    time.sleep_ms(300)
    sct.init_ADS1115()
    log("--- sct.init() processed ---")
    # 2. Den eigentlichen Kalibrierungsprozess ausführen
    try:
        log('try: sct.calibrate()')
        sct.calibrate()
        log('try: sct.save_calibration()')
        ctxt = sct.save_calibration()
        log('New calibration saved '+ctxt)
        return 'New calibration saved '+ctxt        
    except Exception as e:
        print(f"Fehler bei der Kalibrierung: {e}")
        log(f"Fehler bei der Kalibrierung: {e}")
        # Optional: Fehler direkt ins System-Log schreiben
        etxt=f"Kalibrierungs-Fehler via {caller}: {e}\n"
        print(etxt)
        log(etxt)
        return etxt
# Dieser Block springt NUR an, wenn du die Datei direkt in Thonny startest.
# Wird sie über __import__() geladen, bleibt dieser Teil stumm.
if __name__ == "__main__":
    run()