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
            await page.goto('https://www.wanted.co.kr/user/login')
            await page.wait_for_load_state('networkidle')
            
            email_continue_button = page.locator('button:has-text("이메일로 계속하기"), button:has-text("이메일"), [data-testid="email-login"], .email-login-btn')
            await email_continue_button.wait_for(state='visible', timeout=10000)
            await email_continue_button.click()
            
            await page.wait_for_load_state('networkidle')
            
            email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="이메일"]')
            await email_input.wait_for(state='visible', timeout=10000)
            
            current_url = page.url
            if 'login' in current_url and 'email' in current_url.lower():
                await page.screenshot(path='screenshot.png')
                print("✅ 테스트 성공: 이메일로 로그인 페이지 진입 확인")
                return True
            else:
                raise Exception("이메일 로그인 페이지로 이동되지 않음")
            
        except Exception as e:
            print(f"❌ 테스트 실패: {str(e)}")
            await page.screenshot(path='error_screenshot.png')
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_case())