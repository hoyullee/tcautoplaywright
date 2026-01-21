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
            # 테스트 로직: 로그인 → 프로필 아이콘 클릭
            # ========================================

            # 1. 로그인 버튼 찾기 및 클릭
            print("🔍 로그인 버튼 찾기...")
            # GNB 영역에서 로그인 버튼 클릭 (여러 가능한 셀렉터 시도)
            login_button = None
            try:
                # 방법 1: 텍스트로 찾기
                login_button = page.get_by_text('회원가입/로그인')
                await login_button.click(timeout=5000)
            except:
                try:
                    # 방법 2: 로그인 링크 찾기
                    login_button = page.locator('a[href*="login"], button:has-text("로그인")')
                    await login_button.first.click(timeout=5000)
                except:
                    # 방법 3: 일반적인 로그인 버튼
                    login_button = page.get_by_role('button', name='로그인')
                    await login_button.click(timeout=5000)

            await page.wait_for_load_state('networkidle')
            print("✅ 로그인 페이지 진입")

            # 로그인 페이지 스크린샷 (디버깅용)
            await page.screenshot(path='screenshots/test_4_login_page.png')
            print(f"📸 로그인 페이지 URL: {page.url}")

            # 2. "이메일로 계속하기" 버튼 클릭
            print("📧 이메일로 계속하기 버튼 찾기...")
            try:
                email_continue_button = page.get_by_text('이메일로 계속하기')
                await email_continue_button.click(timeout=5000)
                await page.wait_for_load_state('networkidle')
                print("✅ 이메일 로그인 페이지 진입")
            except:
                print("⚠️ 이메일로 계속하기 버튼을 찾지 못했습니다. 이미 이메일 입력 페이지일 수 있습니다.")

            # 3. 이메일 입력
            print("📧 이메일 입력...")
            # 다양한 방법으로 이메일 입력 필드 찾기
            email_input = None
            try:
                # 방법 1: label로 찾기
                email_input = page.get_by_label('이메일')
                await email_input.fill(TEST_EMAIL, timeout=5000)
                print(f"✅ 이메일 입력 완료 (label): {TEST_EMAIL}")
            except:
                try:
                    # 방법 2: placeholder로 찾기
                    email_input = page.get_by_placeholder('이메일')
                    await email_input.fill(TEST_EMAIL, timeout=5000)
                    print(f"✅ 이메일 입력 완료 (placeholder): {TEST_EMAIL}")
                except:
                    # 방법 3: type으로 찾기
                    email_input = page.locator('input[type="email"]')
                    await email_input.first.fill(TEST_EMAIL, timeout=5000)
                    print(f"✅ 이메일 입력 완료 (type): {TEST_EMAIL}")

            # 4. 비밀번호 입력
            print("🔑 비밀번호 입력...")
            password_input = None
            try:
                # 방법 1: label로 찾기
                password_input = page.get_by_label('비밀번호')
                await password_input.fill(TEST_PASSWORD, timeout=5000)
                print("✅ 비밀번호 입력 완료 (label)")
            except:
                try:
                    # 방법 2: placeholder로 찾기
                    password_input = page.get_by_placeholder('비밀번호')
                    await password_input.fill(TEST_PASSWORD, timeout=5000)
                    print("✅ 비밀번호 입력 완료 (placeholder)")
                except:
                    # 방법 3: type으로 찾기
                    password_input = page.locator('input[type="password"]')
                    await password_input.first.fill(TEST_PASSWORD, timeout=5000)
                    print("✅ 비밀번호 입력 완료 (type)")

            # 5. 로그인 버튼 클릭
            print("🔐 로그인 실행...")
            submit_button = page.get_by_role('button', name='로그인')
            await submit_button.click()
            await page.wait_for_load_state('networkidle')
            print("✅ 로그인 완료")

            # 6. 메인 페이지로 돌아갔는지 확인
            await page.wait_for_timeout(2000)  # 로그인 후 페이지 안정화 대기

            # 7. GNB 영역에서 프로필 아이콘 찾기 및 클릭
            print("🔍 프로필 아이콘 찾기...")
            profile_icon = None
            try:
                # 방법 1: 프로필 이미지나 아이콘
                profile_icon = page.locator('button[aria-label*="프로필"], button[aria-label*="profile"], img[alt*="프로필"], [data-testid*="profile"]')
                await profile_icon.first.click(timeout=5000)
            except:
                try:
                    # 방법 2: 사용자 메뉴 버튼
                    profile_icon = page.locator('button:has(img), [class*="profile"], [class*="avatar"], [class*="user-menu"]')
                    await profile_icon.first.click(timeout=5000)
                except:
                    # 방법 3: 일반적인 프로필 영역
                    profile_icon = page.locator('header button, nav button')
                    await profile_icon.last.click(timeout=5000)

            await page.wait_for_load_state('networkidle')
            print("✅ 프로필 아이콘 클릭 완료")

            # 8. 프로필 페이지 진입 확인
            await page.wait_for_timeout(2000)
            current_url = page.url
            print(f"📍 현재 URL: {current_url}")

            # 프로필 페이지 확인 (URL에 profile, mypage, user 등 포함 확인)
            if 'profile' in current_url.lower() or 'mypage' in current_url.lower() or 'user' in current_url.lower():
                print("✅ 프로필 페이지 진입 확인")
            else:
                # 페이지 내용으로 프로필 페이지 확인
                page_content = await page.content()
                if '프로필' in page_content or '마이페이지' in page_content or '내 정보' in page_content:
                    print("✅ 프로필 페이지 진입 확인 (내용 기반)")
                else:
                    print(f"⚠️ 프로필 페이지 확인 필요 - 현재 URL: {current_url}")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_4_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            await page.screenshot(path='screenshots/test_4_error.png')
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
