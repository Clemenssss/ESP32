from logger import logger
class DummyDisplay:
    def clear(self, color=0):
        pass
        
    def draw_text8x8(self, x, y, text, color=0, bg=0):
        # Gibt den Text im Terminal aus, um die Funktion zu simulieren
        print(f"[Dummy-Display] Text: '{text}'")
        logger.log(f"[Dummy-Display] Text: '{text}'")
        
    def fill_rectangle(self, x, y, width, height, color=0):
        pass