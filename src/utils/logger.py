import datetime

class Logger:
    _gui_callback = None 

    @staticmethod
    def attach_gui(callback_func):
        """Call this later from the GUI file to connect logging output"""
        Logger._gui_callback = callback_func

    @staticmethod
    def log(text, type="info"):
        """
        type: info, success, error, warn
        """
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        prefix = "[*]"
        color = "" 
        
        if type == "success": prefix = "[+]"
        elif type == "error": prefix = "[-]"
        elif type == "warn": prefix = "[!]"

        full_msg = f"{prefix} {text}"

        print(full_msg)

        if Logger._gui_callback:
            Logger._gui_callback(f"[{timestamp}] {text}", type)
