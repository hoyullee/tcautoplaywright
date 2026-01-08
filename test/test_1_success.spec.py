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
            
            # 시작 URL로 이동
            await page.goto('https://id.wanted.co.kr/login')
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            # 초기 페이지 스크린샷
            await page.screenshot(path='screenshots/test_1_initial.png')
            
            # 페이지 진입 확인
            await page.wait_for_selector('body', timeout=30000)
            
            # 로그인 페이지 요소 확인
            login_form = await page.wait_for_selector('form, [data-testid="login-form"], .login-form, #loginForm', timeout=30000)
            if not login_form:
                raise Exception("로그인 폼을 찾을 수 없습니다")
            
            # 페이지 URL 확인
            current_url = page.url
            if 'login' not in current_url:
                raise Exception(f"로그인 페이지가 아닙니다. 현재 URL: {current_url}")
            
            # 최종 스크린샷
            await page.screenshot(path='screenshots/test_1_success.png')
            
            print("✅ 테스트 성공: 회원가입/로그인 페이지 정상 진입")
            return True
            
        except Exception as e:
            print(f"❌ 테스트 실패: {str(e)}")
            await page.screenshot(path='screenshots/test_1_error.png')
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_case())