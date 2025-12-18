from playwright.sync_api import sync_playwright
import time

def test_case():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        try:
            # 사전조건: 회원가입/로그인 페이지 진입
            page.goto('https://career.saramin.co.kr/user/login')
            page.wait_for_load_state('networkidle')
            
            # 1. 이메일로 계속하기 버튼 선택
            email_login_button = page.locator('text=이메일로 계속하기')
            email_login_button.wait_for(state='visible')
            email_login_button.click()
            
            # 페이지 로딩 대기
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            # 2. 페이지 진입 확인
            # 이메일 입력 필드 존재 확인
            email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="이메일"]')
            email_input.wait_for(state='visible', timeout=10000)
            
            # 비밀번호 입력 필드 존재 확인
            password_input = page.locator('input[type="password"], input[name="password"]')
            password_input.wait_for(state='visible', timeout=10000)
            
            # URL 확인 (이메일 로그인 페이지로 이동되었는지)
            current_url = page.url
            assert 'login' in current_url.lower() or 'email' in current_url.lower()
            
            # 스크린샷 캡처
            page.screenshot(path='email_login_page_screenshot.png')
            
            print("✅ 테스트 성공: 이메일 로그인 페이지 진입 확인")
            return True
            
        except Exception as e:
            print(f"❌ 테스트 실패: {str(e)}")
            page.screenshot(path='error_screenshot.png')
            return False
            
        finally:
            browser.close()

if __name__ == "__main__":
    test_case()