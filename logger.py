import os
import time
#gemini
LOG_FILE = "system_log.txt"
MAX_LOG_SIZE = 50 * 1024 # 50 KB maximal, damit der Flash nicht vollreitet

def log(message):
    """Schreibt eine Nachricht mit Zeitstempel in die Logdatei und ins Terminal."""
    # Zeitstempel generieren
    t = time.localtime(time.time() + 2 * 3600)
    timestamp = "[%04d-%02d-%02d %02d:%02d:%02d]" % (t[0], t[1], t[2], t[3], t[4], t[5])
    
    log_entry = timestamp + " " + str(message) + "\n"
    
    # Konsolen-Ausgabe (für Thonny, falls angeschlossen)
    print(log_entry.strip())
    
    # Dateigröße prüfen (Sicherheitsnetz)
    try:
        if os.stat(LOG_FILE)[6] > MAX_LOG_SIZE:
            # Wenn zu groß, Log rotieren oder löschen
            os.remove(LOG_FILE)
    except OSError:
        pass # Datei existiert noch nicht
        
    # In Datei schreiben
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Log-Schreibfehler: {e}")