from playwright.async_api import async_playwright
import asyncio
import sys
import os

async def test_case():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # screenshots 디렉토리 생성
            os.makedirs('screenshots', exist_ok=True)
            
            # 채용 홈 진입
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            
            # 상단 GNB 영역에서 회원가입/로그인 버튼 찾기 및 클릭
            login_button = page.locator('a[href*="login"], button:has-text("로그인"), a:has-text("로그인"), [data-testid*="login"]').first
            await login_button.wait_for(state='visible', timeout=30000)
            await login_button.click()
            
            # 페이지 로드 대기
            await page.wait_for_load_state('networkidle')
            
            # 로그인 페이지 진입 확인
            current_url = page.url
            if 'id.wanted.co.kr/login' in current_url or 'login' in current_url:
                # 로그인 페이지 요소 확인
                await page.wait_for_selector('input[type="email"], input[name="email"], input[placeholder*="이메일"]', timeout=30000)
                await page.wait_for_selector('input[type="password"], input[name="password"], input[placeholder*="비밀번호"]', timeout=30000)
                
                await page.screenshot(path='screenshots/test_1_success.png')
                print("✅ 테스트 성공: 회원가입/로그인 페이지 정상 진입")
                return True
            else:
                raise Exception(f"로그인 페이지로 이동하지 않음. 현재 URL: {current_url}")
            
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            await page.screenshot(path='screenshots/test_1_error.png')
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_case())
    sys.exit(0 if result else 1)