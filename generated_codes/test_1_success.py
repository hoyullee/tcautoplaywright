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
        
        # 스크린샷 디렉토리 생성
        os.makedirs('screenshots', exist_ok=True)
        
        try:
            # 페이지 접속
            await page.goto('https://id.wanted.co.kr/login')
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            # 페이지 로드 확인을 위한 스크린샷
            await page.screenshot(path='screenshots/test_1_page_loaded.png')
            
            # 로그인 페이지 진입 확인
            page_title = await page.title()
            current_url = page.url
            
            # 로그인 페이지 요소 확인
            login_form = await page.wait_for_selector('form', timeout=30000)
            
            # 최종 스크린샷
            await page.screenshot(path='screenshots/test_1_final.png')
            
            # 결과 검증
            if 'login' in current_url.lower() and login_form:
                print("✅ 테스트 성공: 회원가입/로그인 페이지 정상 진입")
                return True
            else:
                print(f"❌ 테스트 실패: 로그인 페이지 진입 실패 - URL: {current_url}")
                return False
                
        except Exception as e:
            print(f"❌ 테스트 실패: {str(e)}")
            await page.screenshot(path='screenshots/test_1_error.png')
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_case())