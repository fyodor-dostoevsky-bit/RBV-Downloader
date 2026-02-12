# RBV-Downloader
A powerful, automated CLI tool to download modules from Universitas Terbuka's Virtual Reading Room (RBV) and convert them into high-quality PDF files. Built with Python and Playwright for seamless automation.

---

## Installation

Tool ini bisa kau install di OS apa pun (Windows, Linux, macOS) asalkan ada Python 3.9 ke atas.

### 1. Install via Pip (Recommended)
Masuk ke folder project kau, terus hajar perintah ini:
```bash
pip install rbv-dl
```

### 2. Setup Playwright (Wajib!)

Karena tool ini pakai browser headless, kau harus download binary Chromium-nya sekali aja:
Bash
```bash
playwright install chromium
```

### How to Use

Setelah instalasi sukses, kau bisa langsung panggil perintah ini di terminal mana aja:
```bash
rbv-dl
```
Kau tinggal masukkan NIM/Email UT, password SSO, dan Kode Matakuliah (contoh: DAPU6209). Sisanya biarkan tool ini yang kerja keras buat kau.
