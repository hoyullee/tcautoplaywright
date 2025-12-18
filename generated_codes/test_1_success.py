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
            # 사전조건: 채용 홈 진입 상태
            await page.goto('https://www.wanted.co.kr/')
            await page.wait_for_load_state('networkidle')
            
            # 1. 상단 GNB 영역 > 회원가입/로그인 버튼 선택
            login_button = page.locator('a[href="/user/login"]').first
            await login_button.wait_for(state='visible')
            await login_button.click()
            
            # 2. 회원가입/로그인 페이지 진입 확인
            await page.wait_for_load_state('networkidle')
            await page.wait_for_url('**/user/login')
            
            # 기대결과: 회원가입/로그인 페이지 정상 진입 검증
            current_url = page.url
            assert '/user/login' in current_url, f"Expected login page, but got {current_url}"
            
            # 스크린샷 캡처
            await page.screenshot(path='test_login_page_access.png')
            
            print("✅ 테스트 성공: 회원가입/로그인 페이지 정상 진입")
            return True
            
        except Exception as e:
            print(f"❌ 테스트 실패: {str(e)}")
            await page.screenshot(path='error_screenshot.png')
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_case())