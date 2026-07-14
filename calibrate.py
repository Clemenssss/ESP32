#import sct
#sct.calibrate()
#sct.save_calibration()
#print('New calibration saved')
import sct
import sys
import time
from logger import logger

def run(sensor=None):
    # 1. Herausfinden, wer dieses Programm gestartet hat
    caller = "direkt/Thonny" if __name__ == "__main__" else "programm_starten"
    print(f"--- Kalibrierung gestartet (Aufruf durch: {caller}) ---")
    logger.log(f"--- Kalibrierung gestartet (Aufruf durch: {caller}) ---")
    time.sleep_ms(300)
    sct.init_ADS1115()
    logger.log("--- sct.init() processed ---")
    # 2. Den eigentlichen Kalibrierungsprozess ausführen
    try:
        logger.log(f"try: sct.calibrate(sensor={sensor})")
        sct.calibrate(sensor=sensor)
        logger.log('try: sct.save_calibration()')
        ctxt = sct.save_calibration()
        logger.log('New calibration saved',ctxt)
        return 'New calibration saved',ctxt        
    except Exception as e:
        print(f"Fehler bei der Kalibrierung: {e}")
        logger.log(f"Fehler bei der Kalibrierung: {e}")
        # Optional: Fehler direkt ins System-Log schreiben
        etxt=f"Kalibrierungs-Fehler via {caller}: {e}\n"
        print(etxt)
        logger.log(etxt)
        return etxt
# Dieser Block springt NUR an, wenn du die Datei direkt in Thonny startest.
# Wird sie über __import__() geladen, bleibt dieser Teil stumm.
if __name__ == "__main__":
    run()