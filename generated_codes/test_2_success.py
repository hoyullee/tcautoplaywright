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
            # 사전조건: 회원가입/로그인 페이지 진입
            await page.goto('https://id.wanted.co.kr/login')
            await page.wait_for_load_state('networkidle')
            
            # 초기 페이지 스크린샷
            await page.screenshot(path='screenshots/test_2_initial.png')
            
            # 1. 이메일로 계속하기 버튼 선택
            email_continue_button = page.locator('text=이메일로 계속하기')
            await email_continue_button.wait_for(state='visible', timeout=30000)
            await email_continue_button.click()
            
            # 2. 페이지 진입 확인
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # 이메일 로그인 페이지 확인
            email_input = page.locator('input[type="email"]')
            await email_input.wait_for(state='visible', timeout=30000)
            
            # 기대결과 검증: 이메일로 로그인 페이지 진입 확인
            current_url = page.url
            assert 'login' in current_url, f"로그인 페이지가 아닙니다: {current_url}"
            
            # 이메일 입력 필드가 존재하는지 확인
            email_field_visible = await email_input.is_visible()
            assert email_field_visible, "이메일 입력 필드가 보이지 않습니다"
            
            # 최종 스크린샷
            await page.screenshot(path='screenshots/test_2_success.png')
            
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