# RBV-DL (RBV UT Downloader)

![PyPI - Version](https://img.shields.io/pypi/v/rbv-ut-downloader)
[![Python Versions](https://img.shields.io/pypi/pyversions/rbv-ut-downloader.svg)](https://pypi.org/project/rbv-ut-downloader/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**RBV-DL** is a powerful CLI tool to automate downloading modules from *Universitas Terbuka's Virtual Reading Room* (RBV). It handles login, scans chapters, captures pages in high quality, and stitches them into a readable PDF.

---

##  Prerequisites 

Before installing, you **must** have Python installed on your computer.

1.  **Download Python**: [python.org/downloads](https://www.python.org/downloads/)
2.  **Important**: When installing, make sure to check the box **"Add Python to PATH"**. (This is mandatory, if you forget it will result in an error).

---

##  Installation Guide

Choose your operating system below:

### For Windows Users (The Easy Way)

No need to open code editors. Just use the Command Prompt.

1.  Press the **Windows Key** on your keyboard.
2.  Type `cmd` and press **Enter**.
3.  Copy and paste this command into the black box, then press Enter:
    ```cmd
    pip install rbv-ut-downloader
    ```
4.  After that finishes, run this command to install the browser engine:
    ```cmd
    playwright install chromium
    ```

**Done!** You can now close the window.

### For macOS Users

1.  Press **Command (⌘) + Space** to open Spotlight Search.
2.  Type `Terminal` and press **Enter**.
3.  Paste this command and hit Enter:
    ```bash
    pip3 install rbv-ut-downloader
    ```
4.  Then, install the required browser:
    ```bash
    playwright install chromium
    ```

### For Linux Users (The Pro Way)

You know what to do. Use `pip`, `pipx`, or your preferred package manager.

```bash
# Recommended: install via pipx to keep your system clean
pipx install rbv-ut-downloader
playwright install chromium

# Or standard pip
pipx install rbv-ut-downloader
playwright install chromium
```
### How to Use

Once installed, open your terminal (Command Prompt / Terminal) anywhere and type:
```bash
rbv-dl
```

Follow the interactive prompts:

    NIM / Email: Enter your UT email.

    Password: Enter your E-Campus password (input will be hidden/invisible for security).

    Course Code: Enter the code (e.g., ADPU4433).

The tool will work its magic and save the PDF in a folder named after the course code.

### Troubleshooting

"Command not found" or "rbv-dl is not recognized"

    You likely forgot to check "Add Python to PATH" during installation. Reinstall Python and make sure to check that box.

"Login Failed"

    Ensure your E-Campus password is correct. Try logging in manually at the RBV website first to check your account status.

### Disclaimer

This tool is for educational and archival purposes only. Use it responsibly to back up your own learning materials. The author is not responsible for misuse.
