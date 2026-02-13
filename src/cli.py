import asyncio
import os
import shutil
import time
import re
import img2pdf 
from getpass import getpass
from playwright.async_api import async_playwright

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def log(text, type="info"):
    prefix = "[*]"
    if type == "success": prefix = "[+]"
    elif type == "error": prefix = "[!]"
    elif type == "warn": prefix = "[?]"
    print(f"{prefix} {text}")

class RBVDownloader:
    def __init__(self):
        self.output_dir = ""
        self.current_bab_index = 0
        
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
                    msg = f"✔ Record: Page {nomor}"
                    
                    if os.path.exists(filepath):
                        old_size = os.path.getsize(filepath)
                        if len(buffer) > old_size:
                            msg = f"Upgrade HD: Page {nomor} ({(len(buffer)/1024):.0f} KB)"
                        else:
                            write_file = False 
                    
                    if write_file:
                        with open(filepath, "wb") as f:
                            f.write(buffer)
                        log(msg, "success")
        except Exception as e:
            pass 

    # === NEW WRAPPING FEATURE: MORE EFFICIENT ===
    async def create_pdf(self, source_folder, output_filename):
        images = sorted([os.path.join(source_folder, f) for f in os.listdir(source_folder) if f.endswith(".jpg")])
        if not images:
            log("Image not found.","warn")
            return

        log(f"Packing {len(images)} page...", "info")

        try:
            with open(output_filename, "wb") as f:
                f.write(img2pdf.convert(images))

            log(f"PDF file created: {output_filename}", "success")
        except Exception as e:
            log(f"Failed to create PDF file: {e}", "error")

    async def run(self):
        clear_screen()
        print("==========================================")
        print("   RBV DOWNLOADER CLI - PYTHON EDITION    ")
        print("==========================================")

        username = input("NIM / Email UT : ")
        if "@" not in username: username += "@ecampus.ut.ac.id"
        password = getpass("Password       : ")
        kode_mk  = input("Kode MK (cth: DAPU6209): ").upper()

        base_dir = os.path.join(os.getcwd(), kode_mk)
        temp_dir = os.path.join(os.getcwd(), f"temp_{kode_mk}")
        if os.path.exists(temp_dir):shutil.rmtree(temp_dir)
        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        self.output_dir = temp_dir

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
        print(f"\nError{e}")

if __name__ == "__main__":
    main()
