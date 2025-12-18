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
            await page.goto('{base_url}')
            await page.wait_for_load_state('networkidle')
            
            login_button = page.locator('text=회원가입/로그인').or_(
                page.locator('[href*="login"]')
            ).or_(
                page.locator('a:has-text("로그인")')
            ).or_(
                page.locator('button:has-text("로그인")')
            ).first()
            
            await login_button.wait_for(state='visible')
            await login_button.click()
            await page.wait_for_load_state('networkidle')
            
            current_url = page.url
            if '/user/login' in current_url:
                print("✅ 테스트 성공: 회원가입/로그인 페이지 정상 진입")
                await page.screenshot(path='login_page_success.png')
                return True
            else:
                raise Exception(f"페이지 이동 실패. 현재 URL: {current_url}")
            
        except Exception as e:
            print(f"❌ 테스트 실패: {str(e)}")
            await page.screenshot(path='error_screenshot.png')
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_case())