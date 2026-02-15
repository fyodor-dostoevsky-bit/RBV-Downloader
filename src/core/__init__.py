import os
import sys

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def log(text, type="info"):
    prefix = "[*]"
    if type == "success": prefix = "[+]"
    elif type == "error": prefix = "[!]"
    elif type == "warn": prefix = "[?]"
    print(f"{prefix} {text}")
