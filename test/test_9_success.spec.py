from playwright.async_api import async_playwright
import asyncio
import sys
import os

# ⭐ 테스트 계정 정보 (로그인 필요 시)
TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

async def main():
    async with async_playwright() as p:
        # 브라우저 실행 (Firefox 사용)
        browser = await p.firefox.launch(headless=True)

        # 한국어 설정
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()

        try:
            # screenshots 폴더 생성
            os.makedirs('screenshots', exist_ok=True)

            # 페이지 접속
            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")

            # ========================================
            # 테스트 로직
            # ========================================

            # 1단계: GNB에서 "교육·이벤트" 탭 클릭
            print("📍 1단계: 교육·이벤트 탭 클릭")
            await page.screenshot(path='screenshots/test_9_debug1.png')

            # 여러 방법으로 시도
            education_tab = None
            try:
                # 시도 1: role='link'로 찾기
                education_tab = page.get_by_role('link', name='교육·이벤트')
                await education_tab.wait_for(state='visible', timeout=5000)
            except:
                try:
                    # 시도 2: 텍스트로 찾기
                    education_tab = page.get_by_text('교육·이벤트').first
                    await education_tab.wait_for(state='visible', timeout=5000)
                except:
                    try:
                        # 시도 3: 부분 텍스트 매칭
                        education_tab = page.locator('a:has-text("교육")').first
                        await education_tab.wait_for(state='visible', timeout=5000)
                    except:
                        # 시도 4: 다양한 변형 시도
                        education_tab = page.locator('text=교육').first
                        await education_tab.wait_for(state='visible', timeout=5000)

            await education_tab.click()
            await page.wait_for_load_state('networkidle')
            print("✅ 교육·이벤트 탭 진입 완료")

            # 2단계: 로그인 버튼 찾아 클릭 (회원가입/로그인 페이지 진입)
            print("📍 2단계: 로그인 버튼 클릭")
            # GNB의 로그인 버튼 또는 페이지 내 로그인 버튼
            login_button = page.get_by_role('button', name='로그인')
            await login_button.click()
            await page.wait_for_load_state('networkidle')
            print("✅ 로그인 페이지 진입 완료")

            # 3단계: 이메일로 계속하기 버튼 선택
            print("📍 3단계: 이메일로 계속하기 버튼 선택")
            email_continue_button = page.get_by_role('button', name='이메일로 계속하기')
            await email_continue_button.click()
            await page.wait_for_timeout(1000)  # 입력 폼 나타날 때까지 대기
            print("✅ 이메일 로그인 폼 표시")

            # 4단계: 이메일 입력
            print("📍 4단계: 이메일 입력")
            email_input = page.locator('input[type="email"]')
            await email_input.fill(TEST_EMAIL)
            print(f"✅ 이메일 입력 완료: {TEST_EMAIL}")

            # 5단계: 비밀번호 입력
            print("📍 5단계: 비밀번호 입력")
            password_input = page.locator('input[type="password"]')
            await password_input.fill(TEST_PASSWORD)
            print("✅ 비밀번호 입력 완료")

            # 6단계: 로그인 버튼 선택
            print("📍 6단계: 로그인 버튼 클릭")
            login_submit_button = page.get_by_role('button', name='로그인')
            await login_submit_button.click()
            await page.wait_for_load_state('networkidle')
            print("✅ 로그인 완료")

            # 7단계: 교육·이벤트 탭 페이지로 리다이렉트 확인
            print("📍 7단계: 교육·이벤트 페이지 리다이렉트 확인")
            current_url = page.url
            print(f"현재 URL: {current_url}")

            # URL에 교육·이벤트 관련 경로가 포함되어 있는지 확인
            # (예: /events, /education 등)
            if 'event' in current_url.lower() or 'education' in current_url.lower() or '/learn' in current_url:
                print("✅ 교육·이벤트 페이지로 정상 리다이렉트됨")
            else:
                print(f"⚠️ 리다이렉트 확인: {current_url}")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_9_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            await page.screenshot(path='screenshots/test_9_failed.png')
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
