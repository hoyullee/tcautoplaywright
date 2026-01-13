from playwright.async_api import async_playwright
import asyncio
import os

async def test_case():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        try:
            # 스크린샷 디렉토리 생성
            os.makedirs('screenshots', exist_ok=True)
            
            # 로그인 페이지 접속
            await page.goto('https://id.wanted.co.kr/login')
            await page.wait_for_load_state('networkidle')
            
            # 초기 페이지 스크린샷
            await page.screenshot(path='screenshots/test_2_initial.png')
            
            # 이메일로 계속하기 버튼 찾기 및 클릭
            email_button = page.locator('button:has-text("이메일로 계속하기")')
            await email_button.wait_for(state='visible', timeout=30000)
            await email_button.click()
            
            # 페이지 로딩 대기
            await page.wait_for_load_state('networkidle')
            
            # 이메일 로그인 페이지 진입 확인
            email_input = page.locator('input[type="email"]')
            await email_input.wait_for(state='visible', timeout=30000)
            
            # 결과 스크린샷
            await page.screenshot(path='screenshots/test_2_email_login.png')
            
            print("✅ 테스트 성공: 이메일로 로그인 페이지 진입 확인")
            return True
            
        except Exception as e:
            print(f"❌ 테스트 실패: {str(e)}")
            await page.screenshot(path='screenshots/test_2_error.png')
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_case())