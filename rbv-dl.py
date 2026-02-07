import asyncio
import os
import sys
import shutil
import time
import re
from pathlib import Path
from getpass import getpass
from PIL import Image # pip install pillow
from playwright.async_api import async_playwright

# === KONFIGURASI DAN UTILITAS ===

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def log(text, type="info"):
    # Gaya log santai tapi informatif
    prefix = "[*]"
    if type == "success": prefix = "[+]"
    elif type == "error": prefix = "[!]"
    elif type == "warn": prefix = "[?]"
    print(f"{prefix} {text}")

def detect_browsers():
    # Cari browser yang terinstall di laptop kau (Windows & Linux Support)
    browsers = {}
    
    # Common paths buat Windows & Linux
    common_paths = {
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "/usr/bin/google-chrome", "/usr/bin/chrome"
        ],
        "brave": [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            "/usr/bin/brave-browser"
        ],
        "edge": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "/usr/bin/microsoft-edge"
        ],
        "firefox": [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            "/usr/bin/firefox"
        ]
    }

    for name, paths in common_paths.items():
        for p in paths:
            if os.path.exists(p):
                browsers[name] = p
                break
    
    return browsers

# === CLASS UTAMA (BIAR RAPI KAYAK CODINGAN ORANG PRO) ===

class RBVDownloader:
    def __init__(self):
        self.output_dir = ""
        self.current_bab_index = 0
        self.halaman_terekam = set()
        self.browser_path = ""
        self.browser_type = "" # chromium or firefox
        
    async def wait_for_image(self, page, bab_index, page_num, timeout=10):
        # Logic nunggu gambar, kalau file udah ada di disk berarti aman
        start = time.time()
        filename = f"{str(bab_index).zfill(3)}_IMG_{str(page_num).zfill(3)}.jpg"
        filepath = os.path.join(self.output_dir, filename)
        
        while (time.time() - start) < timeout:
            if os.path.exists(filepath):
                # Cek size dikit, takutnya file korup (0 byte)
                if os.path.getsize(filepath) > 1000:
                    return True
            await asyncio.sleep(0.5)
        return False

    async def intercept_response(self, response):
        # Ini jantungnya, nyerok gambar dari network
        try:
            url = response.url
            if "page=" in url and ("image" in response.headers.get("content-type", "") or response.request.resource_type == "image"):
                
                # Regex ambil nomor halaman
                match = re.search(r'page=(\d+)', url)
                if match:
                    nomor = match.group(1).zfill(3)
                    filename = f"{str(self.current_bab_index).zfill(3)}_IMG_{nomor}.jpg"
                    filepath = os.path.join(self.output_dir, filename)

                    buffer = await response.body()
                    
                    # Filter sampah
                    if len(buffer) < 20000: return 

                    # Logic Upgrade HD (Kalau file baru lebih gede, timpa!)
                    write_file = True
                    msg = f"✔ Dapat: Hal {nomor}"
                    
                    if os.path.exists(filepath):
                        old_size = os.path.getsize(filepath)
                        if len(buffer) > old_size:
                            msg = f"✨ Upgrade HD: Hal {nomor} ({(len(buffer)/1024):.0f} KB)"
                        else:
                            write_file = False # Gak usah simpan, file lama lebih bagus/sama
                    
                    if write_file:
                        with open(filepath, "wb") as f:
                            f.write(buffer)
                        log(msg, "success")
                        
        except Exception as e:
            pass # Silent aja, namanya juga interceptor

    async def create_pdf(self, source_folder, output_filename):
        # Packing gambar jadi PDF A4 (HIGH QUALITY 300 DPI)
        images = sorted([f for f in os.listdir(source_folder) if f.endswith(".jpg")])
        if not images:
            return

        # Ukuran A4 @ 300 DPI (Standar Cetak/HD) - Bukan 72 DPI lagi
        # 595 x 842 itu kecil kali, kita ganti ke pixel besar:
        # 2480 x 3508 itu 300 dpi besar kali anjing
        A4_WIDTH_PX = 1654 
        A4_HEIGHT_PX = 2339
        
        pdf_pages = []
        log(f"Memproses {len(images)} halaman menjadi PDF HD...", "info")

        for img_file in images:
            img_path = os.path.join(source_folder, img_file)
            try:
                img = Image.open(img_path)
                
                # Kita buat kanvas A4 Putih Resolusi Tinggi
                page = Image.new('RGB', (A4_WIDTH_PX, A4_HEIGHT_PX), (255, 255, 255))
                
                # Hitung skala gambar biar muat di A4 tapi tetap proporsional
                # Kita kasih margin dikit (misal 50px)
                MARGIN = 50
                avail_width = A4_WIDTH_PX - (MARGIN * 2)
                avail_height = A4_HEIGHT_PX - (MARGIN * 2)
                
                ratio = min(avail_width / img.width, avail_height / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                
                # Resize pakai LANCZOS (Algoritma paling tajam buat downscale/upscale)
                img_resized = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Posisi Center
                x = (A4_WIDTH_PX - new_size[0]) // 2
                y = (A4_HEIGHT_PX - new_size[1]) // 2
                
                page.paste(img_resized, (x, y))
                pdf_pages.append(page)
            except Exception as e:
                log(f"Gagal memproses gambar {img_file}: {e}", "error")

        if pdf_pages:
            pdf_pages[0].save(output_filename, save_all=True, append_images=pdf_pages[1:], resolution=300.0)
            log(f"File PDF HD Siap Bos: {output_filename}", "success")

    async def run(self):
        clear_screen()
        print("==========================================")
        print("   RBV DOWNLOADER CLI - PYTHON EDITION    ")
        print("   (Support Firefox, Brave, Chrome User)  ")
        print("==========================================")

        # 1. Pilih Browser
        detected = detect_browsers()
        print("\n[Browser Terdeteksi di Laptop Kau]:")
        opts = list(detected.keys())
        for i, browser in enumerate(opts):
            print(f"{i+1}. {browser.upper()} -> {detected[browser]}")
        
        choice = input("\nPilih nomor browser (1/2/..): ")
        try:
            browser_name = opts[int(choice)-1]
            self.browser_path = detected[browser_name]
            self.browser_type = "firefox" if "firefox" in browser_name.lower() else "chromium"
        except:
            log("Ah, salah input kau. Default ke Chrome/Chromium aja lah.", "error")
            self.browser_type = "chromium"
            self.browser_path = "" # Biar Playwright cari sendiri kalau ada

        # 2. Input Data
        username = input("NIM / Email UT : ")
        password = getpass("Password       : ")
        kode_mk  = input("Kode MK (cth: MKWI4201): ").upper()
        pisah_bab = input("Pisah per Bab? (y/n) : ").lower() == 'y'

        # Setup Folder
        base_dir = os.path.join(os.getcwd(), kode_mk)
        temp_dir = os.path.join(os.getcwd(), f"temp_{kode_mk}")
        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        self.output_dir = temp_dir

        async with async_playwright() as p:
            # Launch Browser User
            log(f"Meluncurkan {self.browser_type}...", "info")
            
            launch_args = {
                "headless": True, # Headless True biar gak ganggu
                "executable_path": self.browser_path if self.browser_path else None,
                "args": ["--start-maximized", "--no-sandbox"]
            }

            # Penting: Firefox beda engine di Playwright
            if self.browser_type == "firefox":
                browser = await p.firefox.launch_persistent_context(
                    user_data_dir=os.path.join(os.getcwd(), "rbv_cache"),
                    viewport={"width": 1600, "height": 2400}, # Resolusi Tinggi
                    device_scale_factor=3, # Paksa HD
                    **launch_args
                )
            else:
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir=os.path.join(os.getcwd(), "rbv_cache"),
                    viewport={"width": 1600, "height": 2400},
                    device_scale_factor=3,
                    **launch_args
                )

            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            # Login Flow
            log(f"Buka Pustaka UT: {kode_mk}...", "info")
            await page.goto(f"https://pustaka.ut.ac.id/reader/index.php?modul={kode_mk}")
            
            # Cek Login
            try:
                # Logic Auto Login Microsoft
                if await page.query_selector('input[type="email"]'):
                    log("Mencoba Login Otomatis...", "warn")
                    await page.fill('input[type="email"]', f"{username}@ecampus.ut.ac.id")
                    await page.press('input[type="email"]', "Enter")
                    
                    await page.wait_for_selector('input[type="password"]', state="visible", timeout=10000)
                    await asyncio.sleep(1)
                    await page.fill('input[type="password"]', password)
                    await page.press('input[type="password"]', "Enter")
                    
                    await page.wait_for_navigation(timeout=20000)
                    
                    # Handle 'Stay signed in'
                    if await page.query_selector('input[value="Yes"]'):
                        await page.click('input[value="Yes"]')
                        await page.wait_for_navigation()
            except:
                log("Auto login gagal/skip. Cek manual nanti.", "warn")

            # Cek apakah sudah masuk modul
            is_logged_in = False
            try:
                if await page.query_selector('.flowpaper_lblTotalPages') or await page.query_selector("a[href*='.pdf']"):
                    is_logged_in = True
            except: pass

            # FALLBACK MANUAL LOGIN (Kalo auto gagal)
            if not is_logged_in:
                log("Belum login atau sesi habis. Buka mode GUI Manual...", "warn")
                await browser.close()
                
                # FIX: Pastikan kalau path kosong, kirim None (biar Playwright pakai browser bawaan)
                exec_path = self.browser_path if self.browser_path and len(self.browser_path) > 0 else None

                # Buka browser mode terlihat (Headless False)
                if self.browser_type == "firefox":
                    browser = await p.firefox.launch_persistent_context(
                        user_data_dir=os.path.join(os.getcwd(), "rbv_cache"),
                        headless=False, # GUI MUNCUL
                        executable_path=exec_path # <-- Ini yang bikin error kemarin
                    )
                else:
                    browser = await p.chromium.launch_persistent_context(
                        user_data_dir=os.path.join(os.getcwd(), "rbv_cache"),
                        headless=False, # GUI MUNCUL
                        executable_path=exec_path, # <-- Ini yang bikin error kemarin
                        args=["--start-maximized"]
                    )
                
                page = browser.pages[0]
                await page.goto(f"https://pustaka.ut.ac.id/reader/index.php?modul={kode_mk}")
                
                log("Silakan login manual di browser yang muncul! (Maks 5 menit)", "warn")
                
                # Polling nunggu user login
                start_wait = time.time()
                while (time.time() - start_wait) < 300:
                    try:
                        # Cek indikator login
                        if await page.query_selector('.flowpaper_lblTotalPages') or await page.query_selector("a[href*='.pdf']"):
                            is_logged_in = True
                            break
                    except: pass
                    await asyncio.sleep(2)
                
                if not is_logged_in:
                    log("Kelamaan login kau. Bye.", "error")
                    await browser.close()
                    return
                
                log("Login berhasil! Restarting ke mode siluman (Headless)...", "success")

                # ### TAMBAHAN 1: CURI COOKIE  ###
                saved_cookies = await browser.cookies() 
                # #############################################################

                await browser.close()
                
                # Restart Headless Lagi (Cookie udah tersimpan di user_data_dir)
                # Kita reuse logic launch_args yang sudah aman di atas
                if self.browser_type == "firefox":
                    browser = await p.firefox.launch_persistent_context(
                        user_data_dir=os.path.join(os.getcwd(), "rbv_cache"),
                        viewport={"width": 1600, "height": 2400},
                        device_scale_factor=3,
                        **launch_args
                    )
                else:
                    browser = await p.chromium.launch_persistent_context(
                        user_data_dir=os.path.join(os.getcwd(), "rbv_cache"),
                        viewport={"width": 1600, "height": 2400},
                        device_scale_factor=3,
                        **launch_args
                    )

                # ### TAMBAHAN 2: SUNTIK COOKIE (Letak di sini sebelum goto) ###
                await browser.add_cookies(saved_cookies)
                # ##############################################################

                page = browser.pages[0]
                await page.goto(f"https://pustaka.ut.ac.id/reader/index.php?modul={kode_mk}")

            # === GET DAFTAR BAB === pakai logic js yang lama
            log("Mengambil daftar bab...", "info")
            try:
                await page.wait_for_selector("a[href*='.pdf']", state="attached", timeout=10000)
            except: pass

            # Pake JS murni biar solid
            daftar_bab = await page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll("a[href*='.pdf']"));
                return links.map(a => ({
                    label: a.innerText.trim() || a.href.split('/').pop(),
                    href: a.href,
                    file: a.href.split('/').pop()
                }));
            }""")

            if not daftar_bab:
                log("Gak ada bab yang kebaca. Cek modul.", "error")
                await browser.close()
                return
            
            log(f"Berhasil mendeteksi {len(daftar_bab)} bab.", "success")

            # Pasang penyadap (Interceptor)
            page.on("response", self.intercept_response)

            # === LOOP BAB ===
            for i, bab in enumerate(daftar_bab):
                log(f"\n📘 Bab {i+1}: {bab['label']}", "info")
                self.current_bab_index = i
                
                # Klik bab
                await page.evaluate(f"document.querySelector(`a[href*='{bab['file']}']`).click()")
                await asyncio.sleep(5) # Tunggu loading awal
                
                # Cek Total Halaman
                try:
                    total_el = await page.query_selector(".flowpaper_lblTotalPages")
                    txt_total = await total_el.inner_text()
                    total_hal = int(re.search(r'\d+', txt_total).group())
                except:
                    log("Gagal baca total halaman, skip bab ini.", "error")
                    continue
                
                log(f"📄 Total Halaman: {total_hal}", "info")

                # Loop Halaman
                for j in range(1, total_hal + 1):
                    # Navigasi
                    try:
                        # Paksa pindah halaman via API FlowPaper
                        await page.evaluate(f"$FlowPaper('documentViewer').gotoPage({j})")
                        
                        # HACK ZOOM: Ini kuncinya biar server kirim gambar HD
                        # Kita inject script JS buat maksa zoom 300%
                        await page.evaluate("$FlowPaper('documentViewer').setZoom(3.0)")
                        
                    except:
                        # Fallback barbar kalau API error: ketik di input box
                        try:
                            await page.click('.flowpaper_txtPage', click_count=3)
                            await page.keyboard.type(str(j))
                            await page.keyboard.press("Enter")
                        except: pass
                    
                    # Kasih napas buat server ngerender
                    # Waktu tunggu dipercepat! Dari 4 detik -> 2 detik.
                    # Karena kita udah zoom 3x, biasanya server respon lebih agresif.
                    await asyncio.sleep(2) 
                    
                    # Cek hasil download
                    # Timeout dikurangi dikit biar gak kelamaan nunggu halaman kosong
                    ok = await self.wait_for_image(page, i, j, timeout=6)
                    if not ok:
                        # Kalau gagal, coba 'senggol' dikit zoom-nya biar ngereload
                        try:
                            await page.evaluate("$FlowPaper('documentViewer').setZoom(2.0)")
                            await asyncio.sleep(2)
                        except: pass
                        log(f"Timeout halaman {j} (Mungkin koneksi ampas)", "warn")

            await browser.close()

            # === PACKING PDF ===
            log("\n📦 Packing PDF (Sabar, lagi nempel gambar)...", "info")
            
            if pisah_bab:
                # Grouping file per bab
                files = sorted([f for f in os.listdir(self.output_dir) if f.endswith(".jpg")])
                grouped = {}
                for f in files:
                    prefix = f.split('_')[0]
                    if prefix not in grouped: grouped[prefix] = []
                    grouped[prefix].append(f)
                
                for prefix, file_list in grouped.items():
                    idx = int(prefix)
                    # Bikin folder sementara per bab
                    bab_temp = os.path.join(temp_dir, prefix)
                    os.makedirs(bab_temp, exist_ok=True)
                    for f in file_list:
                        shutil.copy(os.path.join(temp_dir, f), os.path.join(bab_temp, f))
                    
                    judul_bab = daftar_bab[idx]['label'] if idx < len(daftar_bab) else f"Bab_{idx+1}"
                    judul_bersih = re.sub(r'[\\/*?:"<>|]', '_', judul_bab)
                    output_name = os.path.join(base_dir, f"{kode_mk}-{judul_bersih}.pdf")
                    
                    await self.create_pdf(bab_temp, output_name)
                    shutil.rmtree(bab_temp)
            else:
                # Gabung semua
                output_name = os.path.join(base_dir, f"{kode_mk}-Full.pdf")
                await self.create_pdf(temp_dir, output_name)

            # Bersih-bersih
            try: shutil.rmtree(temp_dir)
            except: pass
            
            log(f"✅ SELESAI BOS! Cek folder: {base_dir}", "success")

# === ENTRY POINT ===
if __name__ == "__main__":
    try:
        downloader = RBVDownloader()
        asyncio.run(downloader.run())
    except KeyboardInterrupt:
        print("\n\nDibatalkan user. Yaudah sih.")
    except Exception as e:
        print(f"\nError Fatal: {e}")
