import asyncio
import os
import sys
import shutil
import time
import re
from pathlib import Path
from getpass import getpass
from PIL import Image
from playwright.async_api import async_playwright

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def log(text, type="info"):
    prefix = "[*]"
    if type == "success": prefix = "[+]"
    elif type == "error": prefix = "[!]"
    elif type == "warn": prefix = "[?]"
    print(f"{prefix} {text}")

def detect_browsers():
    # User browser support
    browsers = {}
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

class RBVDownloader:
    def __init__(self):
        self.output_dir = ""
        self.current_bab_index = 0
        self.halaman_terekam = set()
        self.browser_path = ""
        self.browser_type = "" 
        
    async def wait_for_image(self, page, bab_index, page_num, timeout=10):
        start = time.time()
        filename = f"{str(bab_index).zfill(3)}_IMG_{str(page_num).zfill(3)}.jpg"
        filepath = os.path.join(self.output_dir, filename)
        
        while (time.time() - start) < timeout:
            if os.path.exists(filepath):
                if os.path.getsize(filepath) > 1000:
                    return True
            await asyncio.sleep(0.5)
        return False

    async def intercept_response(self, response):
        try:
            url = response.url
            if "page=" in url and ("image" in response.headers.get("content-type", "") or response.request.resource_type == "image"):
                
                match = re.search(r'page=(\d+)', url)
                if match:
                    nomor = match.group(1).zfill(3)
                    filename = f"{str(self.current_bab_index).zfill(3)}_IMG_{nomor}.jpg"
                    filepath = os.path.join(self.output_dir, filename)

                    buffer = await response.body()
                    
                    if len(buffer) < 20000: return 

                    write_file = True
                    msg = f"✔ Dapat: Hal {nomor}"
                    
                    if os.path.exists(filepath):
                        old_size = os.path.getsize(filepath)
                        if len(buffer) > old_size:
                            msg = f"Upgrade HD: Hal {nomor} ({(len(buffer)/1024):.0f} KB)"
                        else:
                            write_file = False 
                    
                    if write_file:
                        with open(filepath, "wb") as f:
                            f.write(buffer)
                        log(msg, "success")
                        
        except Exception as e:
            pass 

    async def create_pdf(self, source_folder, output_filename):
        # (HIGH QUALITY 300 DPI)
        images = sorted([f for f in os.listdir(source_folder) if f.endswith(".jpg")])
        if not images:
            return
            
        A4_WIDTH_PX = 1654 
        A4_HEIGHT_PX = 2339
        
        pdf_pages = []
        log(f"Processing {len(images)} page", "info")

        for img_file in images:
            img_path = os.path.join(source_folder, img_file)
            try:
                img = Image.open(img_path)
                
                page = Image.new('RGB', (A4_WIDTH_PX, A4_HEIGHT_PX), (255, 255, 255))
                
                MARGIN = 50
                avail_width = A4_WIDTH_PX - (MARGIN * 2)
                avail_height = A4_HEIGHT_PX - (MARGIN * 2)
                
                ratio = min(avail_width / img.width, avail_height / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                
                img_resized = img.resize(new_size, Image.Resampling.LANCZOS)
                
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
        print("          (Support User Browser)          ")
        print("==========================================")

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
            self.browser_path = ""

        username = input("NIM / Email UT : ")
        password = getpass("Password       : ")
        kode_mk  = input("Kode MK (cth: MKWI4201): ").upper()
        pisah_bab = input("Pisah per Bab? (y/n) : ").lower() == 'y'

        base_dir = os.path.join(os.getcwd(), kode_mk)
        temp_dir = os.path.join(os.getcwd(), f"temp_{kode_mk}")
        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        self.output_dir = temp_dir

        async with async_playwright() as p:
            log(f"Meluncurkan {self.browser_type}...", "info")
            
            launch_args = {
                "headless": True, 
                "executable_path": self.browser_path if self.browser_path else None,
                "args": ["--start-maximized", "--no-sandbox"]
            }

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

            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            log(f"Buka Pustaka UT: {kode_mk}...", "info")
            await page.goto(f"https://pustaka.ut.ac.id/reader/index.php?modul={kode_mk}")
            
            try:
                if await page.query_selector('input[type="email"]'):
                    log("Mencoba Login Otomatis...", "warn")
                    await page.fill('input[type="email"]', f"{username}@ecampus.ut.ac.id")
                    await page.press('input[type="email"]', "Enter")
                    
                    await page.wait_for_selector('input[type="password"]', state="visible", timeout=10000)
                    await asyncio.sleep(1)
                    await page.fill('input[type="password"]', password)
                    await page.press('input[type="password"]', "Enter")
                    
                    await page.wait_for_navigation(timeout=20000)
                    
                    if await page.query_selector('input[value="Yes"]'):
                        await page.click('input[value="Yes"]')
                        await page.wait_for_navigation()
            except:
                log("Auto login gagal/skip. Cek manual nanti.", "warn")

            is_logged_in = False
            try:
                if await page.query_selector('.flowpaper_lblTotalPages') or await page.query_selector("a[href*='.pdf']"):
                    is_logged_in = True
            except: pass

            if not is_logged_in:
                log("Belum login atau sesi habis. Buka mode GUI Manual...", "warn")
                await browser.close()
            
                exec_path = self.browser_path if self.browser_path and len(self.browser_path) > 0 else None

                if self.browser_type == "firefox":
                    browser = await p.firefox.launch_persistent_context(
                        user_data_dir=os.path.join(os.getcwd(), "rbv_cache"),
                        headless=False, 
                        executable_path=exec_path 
                    )
                else:
                    browser = await p.chromium.launch_persistent_context(
                        user_data_dir=os.path.join(os.getcwd(), "rbv_cache"),
                        headless=False, 
                        executable_path=exec_path, 
                        args=["--start-maximized"]
                    )
                
                page = browser.pages[0]
                await page.goto(f"https://pustaka.ut.ac.id/reader/index.php?modul={kode_mk}")
                
                log("Silakan login manual di browser yang muncul! (Maks 5 menit)", "warn")
                
                start_wait = time.time()
                while (time.time() - start_wait) < 300:
                    try:
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

                saved_cookies = await browser.cookies() 

                await browser.close()
                
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

                await browser.add_cookies(saved_cookies)

                page = browser.pages[0]
                await page.goto(f"https://pustaka.ut.ac.id/reader/index.php?modul={kode_mk}")

            log("Mengambil daftar bab...", "info")
            try:
                await page.wait_for_selector("a[href*='.pdf']", state="attached", timeout=10000)
            except: pass

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

            page.on("response", self.intercept_response)

            for i, bab in enumerate(daftar_bab):
                log(f"\n Bab {i+1}: {bab['label']}", "info")
                self.current_bab_index = i
                
                await page.evaluate(f"document.querySelector(`a[href*='{bab['file']}']`).click()")
                await asyncio.sleep(5) 
                
                try:
                    total_el = await page.query_selector(".flowpaper_lblTotalPages")
                    txt_total = await total_el.inner_text()
                    total_hal = int(re.search(r'\d+', txt_total).group())
                except:
                    log("Gagal baca total halaman, skip bab ini.", "error")
                    continue
                
                log(f" Total Halaman: {total_hal}", "info")

                for j in range(1, total_hal + 1):
                    try:
                        await page.evaluate(f"$FlowPaper('documentViewer').gotoPage({j})")
                        
                        await page.evaluate("$FlowPaper('documentViewer').setZoom(3.0)")
                        
                    except:
                        try:
                            await page.click('.flowpaper_txtPage', click_count=3)
                            await page.keyboard.type(str(j))
                            await page.keyboard.press("Enter")
                        except: pass
                
                    await asyncio.sleep(2) 
                    
                    ok = await self.wait_for_image(page, i, j, timeout=6)
                    if not ok:
                        try:
                            await page.evaluate("$FlowPaper('documentViewer').setZoom(2.0)")
                            await asyncio.sleep(2)
                        except: pass
                        log(f"Timeout halaman {j} (Mungkin koneksi ampas)", "warn")

            await browser.close()

            log("\n Packing PDF (Sabar, lagi nempel gambar)...", "info")
            
            if pisah_bab:
                files = sorted([f for f in os.listdir(self.output_dir) if f.endswith(".jpg")])
                grouped = {}
                for f in files:
                    prefix = f.split('_')[0]
                    if prefix not in grouped: grouped[prefix] = []
                    grouped[prefix].append(f)
                
                for prefix, file_list in grouped.items():
                    idx = int(prefix)
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
                output_name = os.path.join(base_dir, f"{kode_mk}-Full.pdf")
                await self.create_pdf(temp_dir, output_name)

            try: shutil.rmtree(temp_dir)
            except: pass
            
            log(f"✅ SELESAI BOS! Cek folder: {base_dir}", "success")

if __name__ == "__main__":
    try:
        downloader = RBVDownloader()
        asyncio.run(downloader.run())
    except KeyboardInterrupt:
        print("\n\nDibatalkan user. Yaudah sih.")
    except Exception as e:
        print(f"\nError Fatal: {e}")
