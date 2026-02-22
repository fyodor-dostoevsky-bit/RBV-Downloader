import os
import re
import shutil
from pathlib import Path

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_login_id(input_val):
    """Automatically append @ecampus if user enters only NIM"""
    input_val = input_val.strip()
    if "@" not in input_val:
        return f"{input_val}@ecampus.ut.ac.id"
    return input_val

def prepare_directories(kode_mk: str):
    """Create output and temp folders, and clean old temp data if it exists"""
    base_dir = Path("output") / kode_mk)
    temp_dir = Path(f"temp_{kode_mk}")
    
    if temp_dir.exists():
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"[!] Failed to remove temp folder: {e}")

    base_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    return str(base_dir), str(temp_dir)

def ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)

def sanitize_filename(text: str):
    """
    Removes illegal characters from file names.
    """
    return re.sub(r'[\\/*?:"<>|]', "", text)

def collect_images(folder):
    """
    Take all jpgs from the folder and sort them.
    """
    if not os.path.exists(folder):
        return []

    files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(".jpg")
    ]

    return sorted(files)

def collect_images_recursive(root_folder):
    """
    Ambil semua gambar dari subfolder.
    Berguna untuk compile PDF full book.
    """
    all_images = []

    for root, _, files in os.walk(root_folder):
        for f in files:
            if f.lower().endswith(".jpg"):
                all_images.append(os.path.join(root, f))

    return sorted(all_images)
