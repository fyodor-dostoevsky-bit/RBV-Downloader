import asyncio
import os
import shutil
from getpass import getpass
from playwright.async_api import async_playwright

from . import log, clear_screen
from .interceptor import ImageInterceptor
from .pdf_engine import create_pdf

class RBVBrowser:
    def __init__(self):
        self.base_dir = ""
        self.temp_dir = ""
        self.interceptor = None

    async def wait_for_image(self, page, bab_index, page_num, timeout=10):
        start = time.time()
        filename = f"{str(bab_index).zfill(3)}_IMG_{str(page_num).zfill(3)}.jpg"
        filepath = os.path.join(self.temp_dir, filename)
        
        while (time.time() - start) < timeout:
            if os.path.exists(filepath):
                if os.path.getsize(filepath) > 1000:
                    return True
            await asyncio.sleep(0.5)
        return False

    async def start(self):
        clear_screen()
        print("=== RBV DOWNLOADER CLI ===")
        
        username = input("NIM / Email UT : ")
        if "@" not in username: username += "@ecampus.ut.ac.id"
        password = getpass("Password       : ")
        kode_mk  = input("Kode MK (cth: DAPU6209): ").upper()

        self.base_dir = os.path.join(os.getcwd(), kode_mk)
        self.temp_dir = os.path.join(os.getcwd(), f"temp_{kode_mk}")
        if os.path.exists(self.temp_dir): shutil.rmtree(self.temp_dir)
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

        self.interceptor = ImageInterceptor(self.temp_dir)

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

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            log(f"Login to the modul: {kode_mk}...", "info")
            try:
                await page.goto(f"https://pustaka.ut.ac.id/reader/index.php?modul={kode_mk}", timeout=60000)
            
                log("Looking for the SSO Login button...", "info")
                try:
                    await page.wait_for_selector('text=Login dengan SSO O365-UT', timeout=10000)
                    await page.click('text=Login dengan SSO O365-UT')
                except:
                    log("SSO skip/already logged in button.", "warn")

                await page.wait_for_selector('input[type="email"]', timeout=30000)
                await page.fill('input[type="email"]', username)
                await page.press('input[type="email"]', "Enter")
                
                await page.wait_for_selector('input[type="password"]', state="visible", timeout=10000)
                await asyncio.sleep(1) 
                
                await page.fill('input[type="password"]', password)
                await page.press('input[type="password"]', "Enter")

                try:
                    await page.wait_for_selector('input[value="Yes"]', timeout=5000)
                    await page.click('input[value="Yes"]')
                except: pass

                log("Loading modul...", "info")
                await page.wait_for_selector('.flowpaper_lblTotalPages', state="attached", timeout=60000)
                log("Login Successful! Modul open.", "success")

            except Exception as e:
                log(f"Login Error: {e}", "error")
                await browser.close()
                return

            log("Scan daftar isi...", "info")
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
            page.on("response", self.interceptor.handle_response)

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
                
                log(f" Found Page: {total_hal}", "info")
                
                for j in range(1, total_hal + 1):
                    try: await page.evaluate(f"$FlowPaper('documentViewer').gotoPage({j}); $FlowPaper('documentViewer').setZoom(3.0);")
                    except: pass
                    
                    await asyncio.sleep(1.5) 
                    
                    if not await self.wait_for_image(page, i, j, timeout=5):
                        log(f"Timeout Hal {j}", "warn")

            await browser.close()

            output_name = os.path.join(self.base_dir, f"{kode_mk}-FullBook.pdf")
            await create_pdf(self.temp_dir, output_name)
            
            shutil.rmtree(self.temp_dir)
            log("Done.", "success")
