def get_credentials(filename='/credentials.txt'):
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
        
        ssid = password = ftpuser = ftppassword = None  # alle vorinitialisieren
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('ssid='):
                ssid = line[5:].strip().strip('"')
            elif line.startswith('password='):
                password = line[9:].strip().strip('"')
            elif line.startswith('ftpuser='):
                ftpuser = line[8:].strip().strip('"')
            elif line.startswith('ftppassword='):
                ftppassword = line[12:].strip().strip('"')
        
        if ssid and password and ftpuser and ftppassword:
            return ssid, password, ftpuser, ftppassword
        else:
            print("Credentials unvollständig in", filename)
            return None, None, None, None
            
    except OSError:
        print("Keine Datei:", filename)
        return None, None, None, None
    except Exception as e:
        print("Fehler:", e)
        return None, None, None, None