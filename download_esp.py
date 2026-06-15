import subprocess
import os
import re

LOCAL_DIR = r"C:\Users\Clemens Li\git\ESP32"
PORT = "COM3"

def mpremote(cmd):
    result = subprocess.run(
        f'mpremote connect {PORT} fs {cmd}',
        capture_output=True, text=True, shell=True
    )
    return result.stdout, result.stderr

def get_all_files():
    # Alle Dateien rekursiv auflisten
    stdout, _ = mpremote("ls -R /")
    
    files = []
    current_dir = ""
    
    for line in stdout.splitlines():
        line = line.strip()
        
        # Verzeichnis erkennen (z.B. "lib/:" oder "/:")
        if line.endswith(":"):
            current_dir = line.rstrip(":").rstrip("/")
            if current_dir == "/":
                current_dir = ""
            continue
        
        # Datei oder Ordner (Ordner haben keinen Punkt/Endung, aber wir prüfen)
        if line and not line.startswith("ls") and not line.startswith("-"):
            full_path = (current_dir + "/" + line).lstrip("/")
            files.append(full_path)
    
    return files

def download():
    files = get_all_files()
    
    for remote in files:
        local = os.path.join(LOCAL_DIR, *remote.split("/"))
        os.makedirs(os.path.dirname(local), exist_ok=True)
        
        print(f"Downloading: {remote}")
        _, err = mpremote(f"cp :/{remote} {local}")
        
        if err and "Is a directory" not in err:
            print(f"  Fehler: {err.strip()}")
        else:
            print(f"  OK")

if __name__ == "__main__":
    download()