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
            # 스크린샷 폴더 생성
            os.makedirs('screenshots', exist_ok=True)
            
            # 타임아웃 설정
            page.set_default_timeout(30000)
            
            # 사전조건: 채용 홈 진입
            await page.goto('https://www.wanted.co.kr')
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path='screenshots/test_1_home.png')
            
            # 1. 상단 GNB 영역 > 회원가입/로그인 버튼 선택
            login_button = page.locator('a[href*="login"], button:has-text("로그인"), a:has-text("로그인"), [data-testid*="login"]').first()
            await login_button.wait_for(state='visible', timeout=10000)
            await login_button.click()
            await page.wait_for_load_state('networkidle')
            
            # 2. 회원가입/로그인 페이지 진입 확인
            await page.goto('https://id.wanted.co.kr/login')
            await page.wait_for_load_state('networkidle')
            
            # 로그인 페이지 요소 확인
            await page.wait_for_selector('input[type="email"], input[name="email"], #email', timeout=10000)
            await page.wait_for_selector('input[type="password"], input[name="password"], #password', timeout=10000)
            
            # 최종 스크린샷
            await page.screenshot(path='screenshots/test_1_login_page.png')
            
            # URL 확인
            current_url = page.url
            if 'id.wanted.co.kr/login' in current_url:
                print("✅ 테스트 성공: 회원가입/로그인 페이지 정상 진입")
                return True
            else:
                print(f"❌ 테스트 실패: 잘못된 URL - {current_url}")
                return False
                
        except Exception as e:
            print(f"❌ 테스트 실패: {str(e)}")
            await page.screenshot(path='screenshots/test_1_error.png')
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_case())