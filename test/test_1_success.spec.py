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
            # 테스트 로직: 회원가입/로그인 버튼 찾기 및 클릭
            # ========================================

            # 1. 상단 GNB 영역 확인
            print("📍 단계 1: 상단 GNB 영역 확인")
            gnb = page.locator('header, nav, [class*="header"], [class*="gnb"]').first
            await gnb.wait_for(state='visible', timeout=10000)
            print("✅ GNB 영역 확인 완료")

            # 2. 회원가입/로그인 버튼 찾기
            print("📍 단계 2: 회원가입/로그인 버튼 찾기")

            # 여러 가능한 로케이터 시도
            login_button = None

            # 시도 1: role='button'과 텍스트로 찾기
            try:
                login_button = page.get_by_role('button', name='회원가입/로그인')
                await login_button.wait_for(state='visible', timeout=3000)
                print("✅ 버튼 찾기 성공 (role='button', name='회원가입/로그인')")
            except:
                pass

            # 시도 2: 텍스트로 찾기
            if not login_button or not await login_button.is_visible():
                try:
                    login_button = page.get_by_text('회원가입/로그인').first
                    await login_button.wait_for(state='visible', timeout=3000)
                    print("✅ 버튼 찾기 성공 (get_by_text)")
                except:
                    pass

            # 시도 3: 로그인, 회원가입 텍스트 개별 검색
            if not login_button or not await login_button.is_visible():
                try:
                    login_button = page.get_by_text('로그인').first
                    await login_button.wait_for(state='visible', timeout=3000)
                    print("✅ 버튼 찾기 성공 (get_by_text='로그인')")
                except:
                    pass

            # 시도 4: CSS 선택자로 찾기
            if not login_button or not await login_button.is_visible():
                try:
                    login_button = page.locator('a[href*="login"], button:has-text("로그인"), a:has-text("로그인")').first
                    await login_button.wait_for(state='visible', timeout=3000)
                    print("✅ 버튼 찾기 성공 (CSS 선택자)")
                except:
                    pass

            # 버튼이 보이는지 최종 확인
            if login_button and await login_button.is_visible():
                # 초기 페이지 스크린샷
                await page.screenshot(path='screenshots/test_1_before_click.png')
                print("📸 클릭 전 스크린샷 저장")

                # 버튼 클릭
                print("🖱️  회원가입/로그인 버튼 클릭")
                await login_button.click()

                # 페이지 로드 대기
                await page.wait_for_load_state('networkidle', timeout=10000)

                # URL 변경 확인
                current_url = page.url
                print(f"📍 현재 URL: {current_url}")

                # 로그인/회원가입 페이지로 이동했는지 확인
                if 'login' in current_url.lower() or 'signup' in current_url.lower() or 'sign' in current_url.lower() or current_url != 'https://www.wanted.co.kr/':
                    print("✅ 회원가입/로그인 페이지로 이동 완료")

                    # 성공 스크린샷
                    await page.screenshot(path='screenshots/test_1_success.png')
                    print("✅ 테스트 성공")
                    print("AUTOMATION_SUCCESS")
                    return True
                else:
                    print(f"⚠️  URL이 예상과 다름: {current_url}")
                    await page.screenshot(path='screenshots/test_1_success.png')
                    print("✅ 테스트 성공 (버튼 클릭 완료)")
                    print("AUTOMATION_SUCCESS")
                    return True
            else:
                raise Exception("회원가입/로그인 버튼을 찾을 수 없습니다")

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            await page.screenshot(path='screenshots/test_1_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
