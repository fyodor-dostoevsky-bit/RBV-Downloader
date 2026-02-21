import asyncio
from playwright.async_api import async_playwright

class RBVAuth:
    def __init__(self, username, password):
        self.username = username
        if "@" not in self.username:
            self.username += "@ecampus.ut.ac.id"
            
        self.password = password
        self.target_url = "https://pustaka.ut.ac.id/reader/index.php?modul=DAPU6209" 

    async def get_cookies(self):
        """
        Login via Microsoft SSO, wait for the reader to log in, then steal the cookie.
        """
        print(f"Starting SSO login process for: {self.username}...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True) 
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                await page.goto(self.target_url, timeout=60000)

                try:
                    sso_btn = page.get_by_text("Login dengan SSO O365-UT")
                    if await sso_btn.is_visible(timeout=5000):
                        print("Click the O365-UT SSO button...")
                        await sso_btn.click()
                    else:
                        print("The SSO button does not appear, maybe it goes directly to the login form or is already logged in.")
                except:
                    pass

                print("Input Email...")
                await page.wait_for_selector('input[type="email"]', state="visible", timeout=30000)
                await page.fill('input[type="email"]', self.username)
                await page.press('input[type="email"]', "Enter")
                
                await asyncio.sleep(2)

                print("Input Password...")
                await page.wait_for_selector('input[type="password"]', state="visible", timeout=30000)
                await page.fill('input[type="password"]', self.password)
                await page.press('input[type="password"]', "Enter")

                try:
                    print("question: Stay signed in? Looking for the button...")
                    await asyncio.sleep(2)
                    
                    yes_selectors = [
                        '#idSIButton9',      
                        'input[value="Yes"]', 
                        'input[value="Ya"]',  
                        'text=Yes',           
                        'text=Ya'             
                    ]
                    
                    clicked = False
                    for selector in yes_selectors:
                        if await page.locator(selector).is_visible():
                            await page.click(selector)
                            print(f"Click the Stay Signed In button via: {selector}")
                            clicked = True
                            break
                    
                    if not clicked:
                        print("The 'Stay Signed In' button doesn't appear, just continue.")
                        
                except Exception as e:
                    print(f"Skip 'Stay Signed In': {e}")
                    
                print("Waiting to enter Reader...")
                await page.wait_for_selector('.flowpaper_lblTotalPages', state="attached", timeout=60000)
                
                print("Login Successful! Enter the Reader Dashboard.")

                # Take Cookies
                cookies = await context.cookies()
                cookie_dict = {c['name']: c['value'] for c in cookies}
                
                if "PHPSESSID" in cookie_dict:
                    print(f"Session ID obtained: {cookie_dict['PHPSESSID'][:10]}...")
                    return cookie_dict
                else:
                    print("Login successful but PHPSESSID not found.")
                    return cookie_dict

            except Exception as e:
                print(f"Login Failed: {e}")
                await page.screenshot(path="debug_login_error.png")
                print("Check screenshot 'debug_login_error.png'")
                return None
            finally:
                await browser.close()
