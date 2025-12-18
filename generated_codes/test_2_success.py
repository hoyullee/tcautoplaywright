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
            # 사전조건: 회원가입/로그인 페이지 진입
            await page.goto('https://id.wanted.co.kr/login')
            await page.wait_for_load_state('networkidle')
            
            # 1. 이메일로 계속하기 버튼 선택
            email_button = page.locator('button:has-text("이메일로 계속하기"), button:has-text("이메일"), a:has-text("이메일로 계속하기")')
            await email_button.wait_for(state='visible', timeout=10000)
            await email_button.click()
            
            # 2. 페이지 진입 확인
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)
            
            # 이메일 로그인 페이지 요소 확인
            email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="이메일"]')
            await email_input.wait_for(state='visible', timeout=10000)
            
            # 스크린샷 캡처
            await page.screenshot(path='email_login_page.png')
            
            print("✅ 테스트 성공: 이메일 로그인 페이지 진입 확인")
            return True
            
        except Exception as e:
            print(f"❌ 테스트 실패: {str(e)}")
            await page.screenshot(path='error_screenshot.png')
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_case())