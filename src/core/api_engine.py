import aiohttp
import asyncio
import os
from src.utils.logger import Logger

class RocketDownloader:
    def __init__(self, cookies, output_dir, kode_mk):
        self.cookies = cookies
        self.output_dir = output_dir
        self.kode_mk = kode_mk
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://pustaka.ut.ac.id/"
        }
        self.base_url = "https://pustaka.ut.ac.id/reader/view.php"

    async def download_page(self, session, doc_id, page_num, bab_index):
        params = {
            "doc": doc_id,           # M1, M2, dst
            "format": "jpg",
            "subfolder": f"{self.kode_mk}/", 
            "page": page_num,
            "resolution": "300"      
        }

        try:
            async with session.get(self.base_url, params=params, ssl=False) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    if len(content) < 5000:
                        return False 

                    filename = f"{str(bab_index).zfill(3)}_IMG_{str(page_num).zfill(3)}.jpg"
                    filepath = os.path.join(self.output_dir, filename)
                    
                    with open(filepath, "wb") as f:
                        f.write(content)
                    
                    Logger.log(f"   [GET] {doc_id} Page {page_num} OK", "success")
                    return True
                else:
                    return False
        except Exception as e:
            Logger.log(f"   [ERR] Page {page_num}: {e}", "error")
            return False

    async def process_chapter(self, doc_id, bab_index):
        Logger.log(f"Downloading Chapter: {doc_id}...", "info")
        
        async with aiohttp.ClientSession(cookies=self.cookies, headers=self.headers) as session:
            page = 1
            consecutive_errors = 0
            tasks = []
            
            while True:
                batch_tasks = []
                for _ in range(10):
                    batch_tasks.append(self.download_page(session, doc_id, page, bab_index))
                    page += 1
                
                results = await asyncio.gather(*batch_tasks)
                
                if not any(results): 
                    break
                
               # So it's not considered a DDoS
                await asyncio.sleep(0.5)

        Logger.log(f"Chapter {doc_id} Done.", "success")
