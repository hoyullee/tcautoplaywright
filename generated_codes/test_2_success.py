from playwright.async_api import async_playwright
import asyncio

async def test_case():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            await page.goto(f'{base_url}/user/login')
            await page.wait_for_load_state('networkidle')
            
            email_continue_button = page.locator('text=이메일로 계속하기')
            await email_continue_button.wait_for(state='visible')
            await email_continue_button.click()
            
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)
            
            current_url = page.url
            if '/user/login' in current_url or 'email' in current_url:
                await page.screenshot(path='email_login_page.png')
                print("✅ 테스트 성공: 이메일로 로그인 페이지 진입 확인")
                return True
            else:
                raise Exception(f"예상하지 못한 페이지: {current_url}")
            
        except Exception as e:
            print(f"❌ 테스트 실패: {str(e)}")
            await page.screenshot(path='error_screenshot.png')
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_case())