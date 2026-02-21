import httpx
import os
import asyncio

class RBVDownloader:
  def __init__(self, cookie_dict):
    self_cookies = cookie_dict
    self.base_url = "https://pustaka.ut.ac.id/reader/services/view.php"
    self header = {
      "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      "Referer": "ttps://pustaka.ut.ac.id/reader/"
    }
    self.resolution = "800"

  async def download_page(self, doc_id, subfolder, page_num, output_folder):
    """
    Download 1 page async.
    """
    params = {
      "doc": doc_id
      "format": "jpg",
      "subfolder": subfolder,
      "page": page_num,
      "resolution": self.resolution
    }

    filename = os.path.join(output_folder, f"page_{page_num:03d}.jpg")
    
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
            print(f"Page {page_num} sudah ada. Skip.")
            return True

    async with httpx.AsyncClient(cookies=self.cookies, headers=self.headers, timeout=30.0) as client:
            try:
                response = await client.get(self.base_url, params=params)

                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if "image" in content_type:
                        with open(filename, "wb") as f:
                            f.write(response.content)
                        print(f"Page {page_num} OK.")
                        return True
                    else:
                        print(f"Page {page_num} is not an image (End of Module?).")
                        return False
                else:
                    print(f"Page {page_num} Error: Status {response.status_code}")
                    return False
            except Exception as e:
                print(f"Page {page_num} Exception: {e}")
                return False
