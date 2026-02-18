import asyncio
import os
import shutil
import re
from getpass import getpass

import httpx 
import img2pdf
from playwright.async_api import async_playwright

try:
    from src.utils.logger import Logger as log 
    from src.utils.helper import clear_screen, prepare_directories
except ImportError:
    class MockLog:
        def log(self, text, type="info"): 
            icons = {"info": "ℹ️", "success": "✅", "error": "❌", "warn": "⚠️"}
            icon = icons.get(type, "*")
            print(f"[{icon}] {text}")
            
    log = MockLog()
    
    def clear_screen(): 
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def prepare_directories(kode): 
        os.makedirs(f"output/{kode}", exist_ok=True)
        return f"output/{kode}", f"temp_{kode}"

try:
    from core.auth import RBVAuth           # Engine Login SSO
    from core.network import RBVDownloader  # Engine Download HTTPX
except ImportError:
    print("Error: Folder 'core/' tidak ditemukan!")
    print("Pastikan file 'auth.py' dan 'network.py' ada di dalam folder 'core'.")
    exit()

class RBVEngine:
    def __init__(self):
        self.base_dir = ""
        self.temp_dir = ""
        self.cookies = None

    async def get_chapter_list(self, page):
        """
        Scraping daftar Modul (M1, M2, dst) dari sidebar RBV.
        """
        log.log("Scanning Chapter List (Daftar Isi)...", "info")
        
        try:
            await page.wait_for_selector("a[href*='.pdf']", timeout=15000)
            daftar_bab = await page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll("a[href*='.pdf']"));
                return links.map(a => ({
                    label: a.innerText.trim() || a.href.split('/').pop(),
                    # Ambil doc ID dari URL (misal: ...doc=M1&...)
                    doc_id: a.href.split('doc=').pop().split('&')[0] || a.href.split('/').pop().replace('.pdf','')
                }));
            }""")
        except:
            return []
        
        clean_list = []
        seen = set()
        for bab in daftar_bab:
            bid = bab['doc_id'].replace('.pdf', '')
            
            if bid not in seen and "doc" not in bid and bid.strip() != "":
                seen.add(bid)
                clean_list.append({
                    'label': bab['label'],
                    'id': bid
                })
        
        return clean_list

    async def start(self, username=None, password=None, kode_mk=None):
        clear_screen()
        log.log("=== RBV ENGINE V2 (HYBRID TURBO) ===", "info")
        
        if not username: username = input("NIM / Email UT : ")
        if not password: password = getpass("Password        : ")
        if not kode_mk:  kode_mk  = input("Kode MK         : ").upper()
            
        if "@" not in username: username += "@ecampus.ut.ac.id"

        self.base_dir, self.temp_dir = prepare_directories(kode_mk)

        log.log("🚀 Initiating Secure Login sequence...", "info")
        
        auth = RBVAuth(username, password)
        auth.target_url = f"https://pustaka.ut.ac.id/reader/index.php?modul={kode_mk}"
        
        self.cookies = await auth.get_cookies()

        if not self.cookies:
            log.log("Login Failed! Aborting.", "error")
            return

        chapters = []
        log.log("🔍 Fetching Module Metadata...", "info")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            await context.add_cookies([
                {'name': k, 'value': v, 'domain': 'pustaka.ut.ac.id', 'path': '/'} 
                for k, v in self.cookies.items()
            ])
            
            page = await context.new_page()
            await page.goto(f"https://pustaka.ut.ac.id/reader/index.php?modul={kode_mk}", timeout=60000)
            
            chapters = await self.get_chapter_list(page)
            
            if not chapters:
                log.log("Gagal baca sidebar, menggunakan mode asumsi standar (M1-M12)", "warn")
                chapters = [{'id': f'M{i}', 'label': f'Modul {i}'} for i in range(1, 13)]
            
            await browser.close()

        log.log(f"✅ Found {len(chapters)} Chapters. Switching to Turbo Engine.", "success")

        downloader = RBVDownloader(self.cookies)
        downloader.resolution = "800" 
        
        for idx, bab in enumerate(chapters):
            doc_id = bab['id']
            log.log(f"\n⚡ Processing: {bab['label']} (ID: {doc_id})", "info")
            
            bab_dir = os.path.join(self.temp_dir, doc_id)
            if not os.path.exists(bab_dir): os.makedirs(bab_dir)

            concurrency = 5       
            max_pages_guess = 100 
            consecutive_errors = 0
            total_downloaded = 0
            
            async def download_task(page_num):              
                return await downloader.download_page(doc_id, f"{kode_mk}/", page_num, bab_dir)

            for i in range(1, max_pages_guess + 1, concurrency):
                batch_indices = range(i, min(i + concurrency, max_pages_guess + 1))
                tasks = [download_task(p) for p in batch_indices]
                
                results = await asyncio.gather(*tasks)
                
                success_count = results.count(True)
                total_downloaded += success_count
                
                if success_count == 0:
                    consecutive_errors += 1
                else:
                    consecutive_errors = 0
                
                if consecutive_errors >= 2:
                    break
            
            log.log(f"   -> Downloaded {total_downloaded} pages.", "success")

        log.log("\nCompiling Full PDF...", "info")
        
        all_images = []
        for bab in chapters:
            bab_path = os.path.join(self.temp_dir, bab['id'])
            if os.path.exists(bab_path):
                imgs = sorted([os.path.join(bab_path, f) for f in os.listdir(bab_path) if f.endswith(".jpg")])
                all_images.extend(imgs)

        if all_images:
            output_pdf = os.path.join(self.base_dir, f"{kode_mk}-FullBook-HD.pdf")
            try:
                with open(output_pdf, "wb") as f:
                    f.write(img2pdf.convert(all_images))
                log.log(f"SUCCESS! File saved to: {output_pdf}", "success")
                
                try: shutil.rmtree(self.temp_dir)
                except: pass
                
            except Exception as e:
                log.log(f"PDF Error: {e}", "error")
        else:
            log.log("Zonk. Tidak ada gambar yang berhasil didownload.", "error")

if __name__ == "__main__":
    try:
        engine = RBVEngine()
        asyncio.run(engine.start())
    except KeyboardInterrupt:
        print("\nBye.")
    except Exception as e:
        print(f"\nCritical Error: {e}")
