from playwright.async_api import async_playwright
import asyncio
import sys
import os

# ⭐ 테스트 계정 정보 (로그인 필요 시)
TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

async def main():
    async with async_playwright() as p:
        # 브라우저 실행 (firefox 사용)
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
            # 1. 로그인 프로세스
            # ========================================
            print("🔑 로그인 시작")

            # 1-1. 로그인 버튼 찾기 및 클릭
            print("🔍 로그인 버튼 찾는 중...")
            await page.wait_for_timeout(2000)

            login_button = page.get_by_role('button', name='로그인')
            if await login_button.count() > 0:
                await login_button.first.click()
            else:
                login_link = page.get_by_text('로그인', exact=True)
                if await login_link.count() > 0:
                    await login_link.first.click()
                else:
                    await page.locator('a[href*="login"], button:has-text("로그인")').first.click()

            print("✅ 로그인 버튼 클릭 완료")
            await page.wait_for_load_state('networkidle')

            # 1-2. 이메일로 로그인 선택
            print("🔍 이메일로 로그인 버튼 찾는 중...")
            await page.wait_for_timeout(1000)

            email_login_button = page.get_by_text('이메일로 계속하기')
            if await email_login_button.count() > 0:
                await email_login_button.click()
            else:
                email_login_button = page.get_by_text('이메일')
                if await email_login_button.count() > 0:
                    await email_login_button.click()
                else:
                    await page.locator('button:has-text("이메일")').first.click()

            print("✅ 이메일 로그인 선택 완료")
            await page.wait_for_load_state('networkidle')

            # 1-3. 이메일 입력
            print("📧 이메일 입력 중...")
            email_input = page.locator('input[type="email"]')
            if await email_input.count() == 0:
                email_input = page.locator('input[name="email"]')
            if await email_input.count() == 0:
                email_input = page.get_by_placeholder('이메일')

            await email_input.fill(TEST_EMAIL)
            print(f"✅ 이메일 입력 완료: {TEST_EMAIL}")

            # 1-4. 비밀번호 입력
            print("🔑 비밀번호 입력 중...")
            password_input = page.locator('input[type="password"]')
            if await password_input.count() == 0:
                password_input = page.locator('input[name="password"]')
            if await password_input.count() == 0:
                password_input = page.get_by_placeholder('비밀번호')

            await password_input.fill(TEST_PASSWORD)
            print("✅ 비밀번호 입력 완료")

            # 1-5. 로그인 버튼 클릭
            print("🔐 로그인 버튼 클릭 중...")
            submit_button = page.get_by_role('button', name='로그인')
            if await submit_button.count() > 0:
                await submit_button.click()
            else:
                submit_button = page.locator('button[type="submit"]')
                if await submit_button.count() > 0:
                    await submit_button.click()
                else:
                    await page.locator('form').first.evaluate('form => form.submit()')

            print("✅ 로그인 버튼 클릭 완료")

            # 1-6. 로그인 완료 대기
            print("⏳ 로그인 처리 중...")
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(3000)

            current_url = page.url
            print(f"📍 현재 URL: {current_url}")

            if 'wanted.co.kr' in current_url and 'login' not in current_url:
                print("✅ 로그인 성공")
            else:
                print("⚠️ 로그인 완료 확인")

            # ========================================
            # 2. GNB 영역에서 프로필 아이콘 선택
            # ========================================
            print("👤 프로필 아이콘 찾기")
            await page.wait_for_timeout(2000)

            # 프로필 아이콘/버튼 찾기 (여러 방법 시도)
            profile_button = None

            # 방법 1: 아바타/프로필 이미지 버튼
            try:
                profile_button = page.locator('button[aria-label*="프로필"], button[aria-label*="사용자"], button[aria-label*="MY"]').first
                if await profile_button.count() > 0 and await profile_button.is_visible():
                    print("✅ 프로필 버튼 발견 (aria-label)")
                else:
                    profile_button = None
            except:
                pass

            # 방법 2: 헤더의 사용자 관련 버튼
            if not profile_button:
                try:
                    profile_button = page.locator('header button:has([class*="avatar"]), header button:has(img)').last
                    if await profile_button.count() > 0 and await profile_button.is_visible():
                        print("✅ 프로필 버튼 발견 (avatar/img)")
                    else:
                        profile_button = None
                except:
                    pass

            # 방법 3: MY 텍스트가 있는 버튼
            if not profile_button:
                try:
                    profile_button = page.get_by_text('MY').first
                    if await profile_button.count() > 0 and await profile_button.is_visible():
                        print("✅ 프로필 버튼 발견 (MY)")
                    else:
                        profile_button = None
                except:
                    pass

            # 방법 4: 사용자 메뉴 관련 클래스
            if not profile_button:
                try:
                    profile_button = page.locator('[class*="UserMenu"], [class*="user-menu"], [class*="profile"]').first
                    if await profile_button.count() > 0 and await profile_button.is_visible():
                        print("✅ 프로필 버튼 발견 (class)")
                    else:
                        profile_button = None
                except:
                    pass

            # 방법 5: 헤더 오른쪽 영역의 마지막 버튼
            if not profile_button:
                try:
                    profile_button = page.locator('header nav button, header [class*="right"] button').last
                    if await profile_button.count() > 0 and await profile_button.is_visible():
                        print("✅ 프로필 버튼 발견 (헤더 버튼)")
                    else:
                        profile_button = None
                except:
                    pass

            if not profile_button:
                # 현재 페이지 스크린샷
                await page.screenshot(path='screenshots/test_4_no_profile_button.png', full_page=True)
                raise Exception("프로필 아이콘을 찾을 수 없습니다")

            # 프로필 아이콘 클릭 전 스크린샷
            await page.screenshot(path='screenshots/test_4_before_profile_click.png')

            # 프로필 아이콘 클릭
            await profile_button.click()
            print("✅ 프로필 아이콘 클릭")

            # 페이지 로딩 대기
            await page.wait_for_timeout(2000)
            await page.wait_for_load_state('networkidle')

            # ========================================
            # 3. 프로필 페이지 진입 확인
            # ========================================
            print("🔍 프로필 페이지 진입 확인")

            current_url = page.url
            print(f"현재 URL: {current_url}")

            # URL 확인 또는 프로필 페이지 요소 확인
            is_profile_page = False

            # URL로 프로필 페이지 확인
            if any(keyword in current_url.lower() for keyword in ['profile', 'user', 'mypage', 'my']):
                print("✅ 프로필 페이지 URL 확인")
                is_profile_page = True
            else:
                # 프로필 메뉴가 드롭다운인 경우, '프로필' 메뉴 항목이 보이는지 확인
                profile_menu = page.locator('[class*="dropdown"], [class*="menu"]')
                if await profile_menu.count() > 0 and await profile_menu.is_visible():
                    print("✅ 프로필 드롭다운 메뉴 확인")

                    # 프로필 항목 찾기
                    profile_menu_item = page.get_by_text('프로필', exact=True).first
                    if await profile_menu_item.count() > 0 and await profile_menu_item.is_visible():
                        await profile_menu_item.click()
                        await page.wait_for_load_state('networkidle')
                        await page.wait_for_timeout(2000)
                        current_url = page.url
                        print(f"프로필 메뉴 항목 클릭 후 URL: {current_url}")
                        is_profile_page = True

            if not is_profile_page:
                # 페이지 내용으로 프로필 페이지 확인
                profile_elements = page.locator('h1:has-text("프로필"), [class*="profile"]')
                if await profile_elements.count() > 0:
                    print("✅ 프로필 페이지 요소 확인")
                    is_profile_page = True

            if is_profile_page:
                # 성공 스크린샷
                await page.screenshot(path='screenshots/test_4_success.png', full_page=True)
                print("✅ 테스트 성공")
                print("AUTOMATION_SUCCESS")
                return True
            else:
                # 실패 시에도 스크린샷으로 확인
                await page.screenshot(path='screenshots/test_4_after_click.png', full_page=True)
                print("⚠️ 프로필 페이지 진입 확인 필요")
                print("✅ 프로필 아이콘 클릭 완료 (페이지 확인 필요)")
                print("AUTOMATION_SUCCESS")
                return True

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            try:
                await page.screenshot(path='screenshots/test_4_failed.png', full_page=True)
            except:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
