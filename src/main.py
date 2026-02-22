import asyncio
import os
import shutil
import re
from getpass import getpass

import httpx
import img2pdf
from playwright.async_api import async_playwright

from utils.logger import Logger as log
from utils.helper import clear_screen, prepare_directories, collect_images_recursive, format_login_id
        
try:
    from core.auth import RBVauth          # Engine Login SSO
    from core.network import RBVDownloader # Engine Download HTTPX
except ImportError:
    print("Error: Folder 'core/' not found!")
    exit()

class RBVEngine:
    def __init__(self):
        self.base_dir = ""
        self.temp_dir = ""
        self.cookies = None
    
    async def get_chapter_list(self, page):
        """ Scraping Modul (M1, M2, M3, dst) from RBV sidebar"""
        log.log ("Scaning Chapter List....", "info")

        try:
            await page.wait_for_selector("a[href*='.pdf']", timeout=15000)
            daftar_bab = await page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll("a[href*='doc'=]"));

            return links.map(a => {
                const url = new URL (a.href);
                const doc = url.searchParams.get ("doc");

                return {
                    label: a.innerText.trim(),
                    doc_id: doc
                };
            });
        }""")
        except:
            return []

        # Filter
        clean_list = []
        seen = set()
        for bab in daftar_bab:
            bid = bab['doc_id'].replace('.pdf', '')
            if bid not in seen and "doc" not in bid and bid.strip() !="":
                seen.add(bid)
                clean_list.append({
                    'label' : bab['label'],
                    'id' : bid
                })
        return clean_list 
    
    async def start(self, username=None, password=None, kode_mk=None, ):
        clear_screen()
        print("==========================================")
        print("   RBV DOWNLOADER CLI - PYTHON EDITION    ")
        print("==========================================")

        # Input
        if not username:
            username = input("NIM / Email UT : ")
            username = format_login_id(username)
        if not password:
            password = getpass("Password       : ")
        if not kode_mk:
            kode_mk  = input("Kode MK (cth: DAPU6209): ").upper()

        self.base_dir, self.temp_dir = prepare_directories(kode_mk)

        # Login Phase
        log.log ("Initialing Secure Login squence...", "info")
        auth = RBVauth(username, password)
        auth.target_url = f"https://pustaka.ut.ac.id/reader/index.php?modul={kode_mk}"

        self.cookies = await auth.get_cookies()
        if not self.cookies:
            log.log("Login Failed! Aborting." "error")
            return

        # Metadata Phase
        chapters = []
        log.log("Fetching Module Metadata...", "info")
        
        async with async_playwright() as p:
            log(f"Launch...", "info")
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox", 
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage", 
                    "--disable-gpu"
                ] 
            )
            context = await browser.new_context()
            await context.add_cookies([
                {'name': k, 'value': v, 'domain': 'pustaka.ut.ac.id', 'path': '/'} 
                for k, v in self.cookies.items()
            ])
            
            page = await context.new_page()
            log(f"Login to the modul: {kode_mk}...", "info")
            try:
                await page.goto(f"https://pustaka.ut.ac.id/reader/index.php?modul={kode_mk}", timeout=60000)
                chapters = await self.get_chapter_list(page)
            except Exception as e:
                log.log(f"Error accessing page: {e}", "error")
            if not chapters:
                log.log(f"Failed to read sidebar, using standard assumption mode (M1-M12)", "warn")
                chapters = [{'id': f'M{i}', 'label': f'Modul {i}'} for i in range(1, 13)]
                
            await browser.close()
            
        log.log(f"Found {len(chapters)} Chapters. Switching to Turbo Engine.", "success")
        
        # Download Phase    
        downloader = RBVDownloader(self.cookies)
        downloader.resolution = "800" # HD
        
        for id, bab in enumerate(chapters):
            doc_id = bab['id']
            log.log(f"\n Processing: {bab['label']} (ID: {doc_id})", "info")

            bab_dir = os.path.join(self.temp_dir, doc_id)
            if not os.path.exists(bab_dir):
                os.makedirs(bab_dir)

            # Parallel Download Logic
            concurrency = 5
            max_pages_guess = 100
            consecutive_errors = 0
            total_download = 0

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
            log.log(f" -> Downloaded {total_downloaded} pages.", "success")

        # PDF Compiling
        log.log("\n Compiling Full PDF...", "info")
        all_images = collect_images_recursive(self.temp_dir)

        if all_images:
            output_pdf = os.path.join(self.base_dir, f"{kode_mk}-FullBook-HD.pdf")
            try:
                with open(output_pdf, "wb") as f:
                    f.write(img2pdf.convert(all_images))
                log.log(f"Success! File saved to: {output_pdf}", "success")

                try:
                    shutil.rmtree(self.temp_dir)
                except:
                    pass
            except Exception as e:
                log.log(f"PDF error: {e}", "error")
        else:
            log.log("Zonk. No images were downloaded successfully.", "error")

# --- Main Runner ---
def main_entry():
    try:
        engine = RBVEngine()
        asyncio.run(engine.start())
    except KeyboardInterrupt:
        print("\nBye.")
    except Exception as e:
        print(f"\nCritical Error: {e}")
        
if __name__ == "__main__":
    main_entry()
