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
            
            # 로그인 페이지 접속
            await page.goto('https://id.wanted.co.kr/login')
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            # 페이지 진입 확인을 위한 스크린샷
            await page.screenshot(path='screenshots/test_2_page_loaded.png')
            
            # 이메일로 계속하기 버튼 찾기 및 클릭
            email_button = page.locator('button:has-text("이메일로 계속하기")')
            await email_button.wait_for(state='visible', timeout=30000)
            await email_button.click()
            
            # 페이지 전환 대기
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            # 이메일 로그인 페이지 진입 확인
            # 이메일 입력 필드 존재 확인
            email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="이메일"]')
            await email_input.wait_for(state='visible', timeout=30000)
            
            # 페이지 URL 확인
            current_url = page.url
            print(f"현재 페이지 URL: {current_url}")
            
            await page.screenshot(path='screenshots/test_2_success.png')
            print("✅ 테스트 성공: 이메일로 로그인 페이지 진입 확인")
            return True
            
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            await page.screenshot(path='screenshots/test_2_error.png')
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_case())
    sys.exit(0 if result else 1)