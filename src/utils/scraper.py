from utils.logger import Logger as log

async def get_chapter_list(page):
    """ Accurate Module Scraping without guesswork """
    log.log("Scanning Chapter List precisely...", "info")

    try:
        await page.wait_for_selector("a[href*='.pdf']", timeout=15000)
        daftar_bab = await page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll("a[href*='.pdf']"));
            return links.map(a => {
                const url = new URL(a.href, document.baseURI);
                let bid = url.searchParams.get("doc"); 
                
                if (!bid) { 
                    bid = a.href.split('/').pop().replace('.pdf', '');
                } 
                
                return { 
                    label: a.innerText.trim() || bid, 
                    id: bid 
                };
            });
        }""")

        clean_list = []
        seen = set()
        for bab in daftar_bab:
            bid = bab['id']
            if bid and bid not in seen and bid.strip() != "":
                seen.add(bid)
                clean_list.append(bab)
                
        return clean_list
        
    except Exception as e:
        log.log(f"Scraping failed: {e}", "error")
        return []
