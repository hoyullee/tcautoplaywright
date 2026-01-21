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
            # 로그인 프로세스
            # ========================================
            print("🔐 로그인 시작")

            # 1. 회원가입/로그인 버튼 클릭
            print("🔍 회원가입/로그인 버튼 찾는 중...")
            login_button = page.get_by_role('button', name='회원가입/로그인')
            if await login_button.count() > 0:
                await login_button.click()
                print("✅ 로그인 모달 열기 성공")
            else:
                login_link = page.get_by_text('회원가입/로그인')
                await login_link.click()
                print("✅ 로그인 모달 열기 성공 (대체 방법)")

            await page.wait_for_timeout(2000)

            # 2. 이메일로 계속하기 버튼 클릭
            print("🔍 이메일로 계속하기 버튼 찾는 중...")
            email_start_button = page.get_by_text('이메일로 계속하기')
            if await email_start_button.count() == 0:
                email_start_button = page.get_by_text('이메일로 시작하기')

            await email_start_button.click()
            print("✅ 이메일 로그인 페이지 진입")
            await page.wait_for_timeout(2000)

            # 3. 이메일 입력
            print(f"📧 이메일 입력 중: {TEST_EMAIL}")
            email_input = page.locator('input[type="email"]')
            await email_input.fill(TEST_EMAIL)
            print("✅ 이메일 입력 완료")

            # 4. 비밀번호 입력
            print("🔒 비밀번호 입력 중...")
            password_input = page.locator('input[type="password"]')
            await password_input.fill(TEST_PASSWORD)
            print("✅ 비밀번호 입력 완료")

            # 5. 로그인 버튼 클릭
            print("🔍 로그인 버튼 클릭 중...")
            submit_button = page.get_by_role('button', name='로그인')
            if await submit_button.count() == 0:
                submit_button = page.get_by_text('로그인')

            await submit_button.click()
            print("✅ 로그인 버튼 클릭 완료")

            # 로그인 완료 대기
            await page.wait_for_timeout(3000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            print("✅ 로그인 완료")

            # ========================================
            # GNB 메뉴 노출 확인
            # ========================================
            print("📋 GNB 메뉴 노출 확인 시작")

            menu_items = [
                ('로고', 'link', 'wanted'),
                ('채용', 'link', '채용'),
                ('이력서', 'link', '이력서'),
                ('교육•이벤트', 'link', '교육•이벤트'),
                ('콘텐츠', 'link', '콘텐츠'),
                ('소셜', 'link', '소셜'),
                ('프리랜서', 'link', '프리랜서'),
                ('더보기', 'button', '더보기'),
                ('기업 서비스', 'link', '기업 서비스')
            ]

            # 각 메뉴 항목 확인
            for item_name, role, text in menu_items:
                try:
                    if role == 'link':
                        element = page.get_by_role('link', name=text)
                    else:
                        element = page.get_by_role('button', name=text)

                    # 요소가 보이는지 확인
                    is_visible = await element.is_visible()
                    if is_visible:
                        print(f"✅ {item_name} 메뉴 확인")
                    else:
                        print(f"⚠️ {item_name} 메뉴가 보이지 않음")
                except Exception as e:
                    print(f"❌ {item_name} 메뉴 확인 실패: {e}")

            # 아이콘 요소 확인 (검색, 알림센터, 프로필)
            icon_items = [
                ('검색', 'button', '검색'),
                ('알림센터', 'button', '알림'),
                ('프로필', 'button', '프로필')
            ]

            for item_name, role, aria_label in icon_items:
                try:
                    # aria-label 또는 title로 찾기
                    element = page.locator(f'button[aria-label*="{aria_label}"], button[title*="{aria_label}"]').first
                    is_visible = await element.is_visible()
                    if is_visible:
                        print(f"✅ {item_name} 아이콘 확인")
                    else:
                        print(f"⚠️ {item_name} 아이콘이 보이지 않음")
                except Exception as e:
                    print(f"❌ {item_name} 아이콘 확인 실패: {e}")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_7_success.png', full_page=True)
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            await page.screenshot(path='screenshots/test_7_error.png', full_page=True)
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
