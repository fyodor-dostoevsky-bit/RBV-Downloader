import os
import re
import asyncio
from . import log

class ImageInterceptor:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.current_bab_index = 0

    def set_bab(self, index):
        self.current_bab_index = index

    async def handle_response(self, response):
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
