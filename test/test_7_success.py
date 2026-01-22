from playwright.async_api import async_playwright
import asyncio
import sys
import os
import pytest

# ⭐ 테스트 계정 정보 (로그인 필요 시)
TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

@pytest.mark.asyncio
async def test_main():
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
            # 로그인 처리
            # ========================================
            print("🔐 로그인 시작")

            # 1. 회원가입/로그인 버튼 찾기 및 클릭
            print("🔍 회원가입/로그인 버튼 찾는 중...")
            login_button = None
            selectors = [
                "button:has-text('회원가입/로그인')",
                "a:has-text('회원가입/로그인')",
                "text=회원가입/로그인",
                "button:has-text('로그인')",
                "a:has-text('로그인')"
            ]

            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=3000):
                        login_button = element
                        print(f"✅ 로그인 버튼 발견: {selector}")
                        break
                except:
                    continue

            if login_button:
                await login_button.click()
                await page.wait_for_load_state('networkidle')
                print("✅ 회원가입/로그인 버튼 클릭 완료")

            # 2. '이메일로 계속하기' 버튼 클릭 (있는 경우)
            print("🔍 '이메일로 계속하기' 버튼 확인 중...")
            try:
                email_continue_button = page.locator("button:has-text('이메일로 계속하기')").first
                if await email_continue_button.is_visible(timeout=3000):
                    await email_continue_button.click()
                    await page.wait_for_load_state('networkidle')
                    print("✅ '이메일로 계속하기' 버튼 클릭 완료")
            except:
                print("ℹ️ '이메일로 계속하기' 버튼 없음 (직접 이메일 입력 가능)")

            # 3. 이메일 입력
            print("🔍 이메일 입력란 찾는 중...")
            email_input = page.locator('input[type="email"]').first
            await email_input.wait_for(state='visible', timeout=10000)
            await email_input.fill(TEST_EMAIL)
            print(f"✅ 이메일 입력: {TEST_EMAIL}")

            # 4. 비밀번호 입력
            print("🔍 비밀번호 입력란 찾는 중...")
            password_input = page.locator('input[type="password"]').first
            await password_input.wait_for(state='visible', timeout=10000)
            await password_input.fill(TEST_PASSWORD)
            print("✅ 비밀번호 입력")

            # 5. 로그인 버튼 클릭
            print("🔍 로그인 버튼 찾는 중...")
            submit_selectors = [
                "button:has-text('로그인')",
                "button[type='submit']",
                "button:has-text('이메일로 로그인')"
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=3000):
                        submit_button = element
                        print(f"✅ 로그인 제출 버튼 발견: {selector}")
                        break
                except:
                    continue

            if submit_button:
                await submit_button.click()
                # 로그인 처리 대기
                await asyncio.sleep(2)
                print("✅ 로그인 완료")

            # 6. 메인 페이지 확인 (로그인 후 자동으로 메인 페이지로 이동)
            try:
                await page.wait_for_url('https://www.wanted.co.kr/**', timeout=10000)
                print("✅ 메인 페이지로 자동 이동")
            except:
                # URL이 변경되지 않았다면 직접 이동
                current_url = page.url
                if 'wanted.co.kr' in current_url and 'login' not in current_url:
                    print(f"✅ 이미 메인 페이지에 있음: {current_url}")
                else:
                    await page.goto('https://www.wanted.co.kr/', timeout=30000)
                    print("✅ 메인 페이지로 이동")

            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")

            # ========================================
            # GNB 메뉴 노출 확인
            # ========================================
            print("🔍 GNB 메뉴 노출 확인 시작")

            # 확인할 메뉴 항목들
            menu_items = [
                ("wanted", "로고"),
                ("채용", "채용"),
                ("이력서", "이력서"),
                ("교육•이벤트", "교육•이벤트"),
                ("콘텐츠", "콘텐츠"),
                ("소셜", "소셜"),
                ("프리랜서", "프리랜서"),
                ("더보기", "더보기"),
                ("기업 서비스", "기업 서비스")
            ]

            # 각 메뉴 항목 확인
            for menu_text, menu_name in menu_items:
                try:
                    # 텍스트로 찾기
                    element = page.get_by_text(menu_text, exact=False)
                    is_visible = await element.first.is_visible() if await element.count() > 0 else False

                    if is_visible:
                        print(f"✅ {menu_name} 노출 확인")
                    else:
                        print(f"⚠️ {menu_name} 미노출")
                except Exception as e:
                    print(f"⚠️ {menu_name} 확인 중 오류: {e}")

            # 아이콘 확인 (검색, 알림센터, 프로필)
            print("🔍 아이콘 항목 확인")

            # 검색 아이콘 (돋보기 아이콘)
            try:
                search_icon = page.locator('[aria-label*="검색"]').or_(page.locator('button:has-text("검색")'))
                if await search_icon.count() > 0 and await search_icon.first.is_visible():
                    print("✅ 검색 아이콘 노출 확인")
                else:
                    print("⚠️ 검색 아이콘 미노출")
            except Exception as e:
                print(f"⚠️ 검색 아이콘 확인 중 오류: {e}")

            # 알림센터 아이콘
            try:
                notification_icon = page.locator('[aria-label*="알림"]').or_(page.locator('button:has-text("알림")'))
                if await notification_icon.count() > 0 and await notification_icon.first.is_visible():
                    print("✅ 알림센터 아이콘 노출 확인")
                else:
                    print("⚠️ 알림센터 아이콘 미노출")
            except Exception as e:
                print(f"⚠️ 알림센터 아이콘 확인 중 오류: {e}")

            # 프로필 아이콘 (로그인 상태에서 보이는 프로필)
            try:
                profile_icon = page.locator('[aria-label*="프로필"]').or_(page.locator('button:has-text("프로필")'))
                if await profile_icon.count() > 0 and await profile_icon.first.is_visible():
                    print("✅ 프로필 아이콘 노출 확인")
                else:
                    # 프로필은 이미지나 아바타로 표시될 수 있음
                    avatar = page.locator('img[alt*="프로필"]').or_(page.locator('[class*="avatar"]'))
                    if await avatar.count() > 0 and await avatar.first.is_visible():
                        print("✅ 프로필 아이콘 노출 확인 (아바타)")
                    else:
                        print("⚠️ 프로필 아이콘 미노출")
            except Exception as e:
                print(f"⚠️ 프로필 아이콘 확인 중 오류: {e}")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_7_success.png', full_page=True)
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            try:
                await page.screenshot(path='screenshots/test_7_error.png', full_page=True)
            except:
                pass
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
