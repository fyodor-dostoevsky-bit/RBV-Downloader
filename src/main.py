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
        def log(self, text, type="info")
            icons = {
                "info": "[*]",
                "success": "[+]",
                "error": "[-]",
                "warn": "[!]"
            }
            icon = icons.get(type, "[?]")
            print(f"[{icon}] {text}")
    
    log = MockLog()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def prepare_directories(kode):
    base_dir = f"output/{kode}"
    temp_dir = f"temp/{kode}"
    os.makedirs(base_dir, exist_ok=True)
    return base_dir, temp_dir

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
        daftar_bar = await page.evaluate("""() => {
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
    
    async def start(self, username=None, password=None, kode_mk=None, ):
        clear_screen()
        print("==========================================")
        print("   RBV DOWNLOADER CLI - PYTHON EDITION    ")
        print("==========================================")

        if not username:
            username = input("NIM / Email UT : ")
        if not password:
            password = getpass("Password       : ")
        if not kode_mk:
            kode_mk  = input("Kode MK (cth: DAPU6209): ").upper()

        if "@" not in username:
            username += "@ecampus.ut.ac.id"

        self.base_dir, self.temp_dir = prepare_directories(kode_mk)

        log.log ("Initialing Secure Login squence...", "info")
        auth = RBVauth(username, password)
        auth.target_url = f"https://pustaka.ut.ac.id/reader/index.php?modul={kode_mk}"

        self.cookies = await auth.get_cookies()
        if not self.cookies:
            log.log("Login Failed! Aborting." "error")
            return

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
                chapters = [{'id': f'M{i}', 'label': f'Modul {i}'} for i in range(1, 13)]chapters = [{}]
                
            await browser.close()
            
        log.log(f"✅ Found {len(chapters)} Chapters. Switching to Turbo Engine.", "success")
        ## Here
        ## Here
        ## Here
            try: await page.wait_for_selector("a[href*='.pdf']", timeout=10000)
            except: pass

            daftar_bab = await page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll("a[href*='.pdf']"));
                return links.map(a => ({
                    label: a.innerText.trim() || a.href.split('/').pop(),
                    file: a.href.split('/').pop()
                }));
            }""")

            if not daftar_bab:
                log("Failed to read.", "error")
                await browser.close()
                return
            
            log(f"Found {len(daftar_bab)} Bab.", "success")
            page.on("response", self.intercept_response)

            for i, bab in enumerate(daftar_bab):
                log(f"\n Bab {i+1}: {bab['label']}", "info")
                self.current_bab_index = i
                
                try: await page.evaluate(f"document.querySelector(`a[href*='{bab['file']}']`).click()")
                except: continue
                
                await asyncio.sleep(4) 
                
                try:
                    total_txt = await page.inner_text(".flowpaper_lblTotalPages")
                    total_hal = int(re.search(r'\d+', total_txt).group())
                except:
                    total_hal = 0
                
                log(f" Hal: {total_hal}", "info")
                
                for j in range(1, total_hal + 1):
                    try: await page.evaluate(f"$FlowPaper('documentViewer').gotoPage({j}); $FlowPaper('documentViewer').setZoom(3.0);")
                    except: pass
                    
                    await asyncio.sleep(1.5) 
                    
                    if not await self.wait_for_image(page, i, j, timeout=5):
                        log(f"Timeout Hal {j}", "warn")

            await browser.close()

            output_name = os.path.join(base_dir, f"{kode_mk}-FullBook.pdf")
            await self.create_pdf(temp_dir, output_name)

            shutil.rmtree(temp_dir)
            log(f"\nSuccessful! File dir: {kode_mk}", "success")

def main():
    try:
        downloader = RBVDownloader()
        asyncio.run(downloader.run())
    except KeyboardInterrupt:
        print("\nBye.")
    except Exception as e:
        print(f"\nError: {e}")
        
if __name__ == "__main__":
    main()
