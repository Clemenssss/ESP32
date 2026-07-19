import time
import os

class Logger:
    def __init__(self, filename="system_log.txt"):
        self.filename = filename
        try:
            self.file = open(self.filename, "a")
        except OSError:
            self.file = None

    def _is_daylight_saving(self, t):
        # t = (year, month, mday, hour, ...)
        year, month, mday, hour = t[0], t[1], t[2], t[3]
        if month < 3 or month > 10: return False
        if month > 3 and month < 10: return True
        
        # Berechnung des letzten Sonntags ohne 'calendar'-Modul
        # Wochentag von Tag 31 (bzw 30/28) bestimmen: 
        # Zeller's Kongruenz oder einfacher:
        # Wir nehmen den 31. (bzw. 30.) und gehen rückwärts zum Sonntag
        last_day = 31 if month == 3 else 30
        t_last = time.mktime((year, month, last_day, 0, 0, 0, 0, 0))
        weekday = time.localtime(t_last)[6] # 0=Mon, 6=Son
        last_sunday = last_day - weekday
        
        if month == 3:
            return mday > last_sunday or (mday == last_sunday and hour >= 1)
        else: # month == 10
            return mday < last_sunday or (mday == last_sunday and hour < 1)
    def log(self, *args):
        # Zeitstempel berechnen
        now = time.time()
        t_utc = time.localtime(now)
        offset = 7200 if self._is_daylight_saving(t_utc) else 3600
        t = time.localtime(now + offset)
        
        timestamp = "[%04d-%02d-%02d %02d:%02d:%02d]" % t[0:6]
        
        # 1. Konsole (wichtig für Echtzeit-Debugging)
        print(timestamp, *args)
        
        # 2. Datei-Schreibvorgang
        if self.file:
            self.file.write(timestamp + " ")
            for arg in args:
                self.file.write(str(arg))
                self.file.write(" ")
            self.file.write("\n")
            self.file.flush()

# Globale Instanz erstellen
logger = Logger()