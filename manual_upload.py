from ftptrans import upload_and_clear
from logger import logger
def run():
    try:
        for f in ['messwerte.csv','system_log.txt']:
            result = upload_and_clear('manual ftp upload',f)
            print(result, f)
        return 'Manual Upload done'    
    except Exception as e:
        print('except Exception as e:',e,f)
        return 'Upload Fail '+f
    # Einzeltest aus Thonny erlauben
if __name__ == "__main__":
    run()
    