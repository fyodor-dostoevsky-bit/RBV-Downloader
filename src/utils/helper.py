import os
import shutil

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_login_id(input_val):
    """Automatically append @ecampus if user enters only NIM"""
    input_val = input_val.strip()
    if "@" not in input_val:
        return f"{input_val}@ecampus.ut.ac.id"
    return input_val

def prepare_directories(kode_mk):
    """Create output and temp folders, and clean old temp data if it exists"""
    base_dir = os.path.join(os.getcwd(), kode_mk)
    temp_dir = os.path.join(os.getcwd(), f"temp_{kode_mk}")
    
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"[!] Failed to remove temp folder: {e}")

    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    return base_dir, temp_dir

def cleanup_temp(temp_dir):
    """Remove temp folder after process is finished"""
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
