import sct

def run():
    try:
        print("--- Kalibrierung gestartet ---")
        sct.calibrate()
        sct.save_calibration()
        print('New calibration saved')
        
        # Das wird an die Webseite zurückgegeben und dort angezeigt
        return "Kalibrierung erfolgreich durchgelaufen und gespeichert!"
        
    except Exception as e:
        # Falls in sct etwas schiefgeht, bricht nicht der Server ab
        return "Fehler bei der Kalibrierung: " + str(e)
# Dieser Block sorgt dafür, dass du das Skript trotzdem noch 
# direkt in Thonny mit "Run" starten kannst zum Testen!
if __name__ == "__main__":
    run()    