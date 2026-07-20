from machine import Pin
def turn_off_and_get_dummy(display_instance, spi_instance):
    """
    Schaltet das Backlight aus und gibt das DummyDisplay zurück.
    Keine Hardware-Zerstörung, kein Löschen von sys.modules.
    """
    print("Schalte um auf Dummy-Display für REPL-Monitor...")
    
    try:
        # 1. Bildschirm schwärzen
        display_instance.fill_rectangle(0, 0, 320, 240, BLACK)
        print("Bildschirm schwärzen OK")
    except:
        pass
        
    try:
        # 2. Hintergrundbeleuchtung aus (GPIO 21)
        bl = Pin(21, Pin.OUT)
        bl.value(0)
        print("Hintergrundbeleuchtung aus (GPIO 21) OK")
    except Exception as e:
        print("Hintergrundbeleuchtung aus (GPIO 21) FAIL-Reset in turn_off_and_get_dummy(", e)
        sys.print_exception(e)
        import machine
        machine.reset()
        
    # Wir löschen NUR die lokale Variable des echten Displays,
    # damit der Speicher vom GC freigegeben wird.
    del display_instance
   
    # 3. Dummy zurückgeben, damit show_values() brav in die REPL printet
    print('return DummyDisplay()')
    return DummyDisplay()
