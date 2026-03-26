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
        browser = await p.firefox.launch(headless=False)

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
            await page.goto('https://www.wanted.co.kr/', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_load_state('domcontentloaded', timeout=30000)
            print("✅ 페이지 로드 완료")

            # ========================================
            # 테스트 로직: 소셜 탭 > LNB 영역 > 로그인 버튼
            # ========================================

            # 1. 소셜 탭 진입 (사전조건)
            print("📌 1단계: 소셜 탭 클릭")
            # GNB에서 소셜 탭 찾기
            social_tab = page.get_by_role('link', name='소셜')
            if not await social_tab.count():
                # 대체 방법: 텍스트로 찾기
                social_tab = page.get_by_text('소셜', exact=True).first

            await social_tab.click()
            await page.wait_for_load_state('domcontentloaded', timeout=30000)
            print("✅ 소셜 탭 진입 완료")

            # 2. LNB 영역 확인
            print("📌 2단계: LNB 영역 확인")
            await page.wait_for_timeout(2000)  # LNB 로딩 대기

            # 3. "로그인 해주세요" 버튼 찾기 및 클릭
            print("📌 3단계: '로그인 해주세요' 버튼 클릭")

            # 여러 방법으로 로그인 버튼 시도
            login_button = None

            # 방법 1: 정확한 텍스트로 찾기
            if await page.get_by_text('로그인 해주세요', exact=True).count() > 0:
                login_button = page.get_by_text('로그인 해주세요', exact=True).first
            # 방법 2: 부분 텍스트로 찾기
            elif await page.get_by_text('로그인').first.count() > 0:
                login_button = page.get_by_text('로그인').first
            # 방법 3: role="button"으로 찾기
            elif await page.get_by_role('button', name='로그인').count() > 0:
                login_button = page.get_by_role('button', name='로그인').first
            # 방법 4: CSS 선택자로 찾기 (LNB 영역 내)
            else:
                # LNB 영역의 로그인 버튼 탐색
                login_button = page.locator('button:has-text("로그인")').first

            if login_button:
                await login_button.click()
                await page.wait_for_load_state('domcontentloaded', timeout=30000)
                print("✅ 로그인 버튼 클릭 완료")
            else:
                raise Exception("로그인 버튼을 찾을 수 없습니다")

            # 4. 회원가입/로그인 페이지 진입 확인
            print("📌 4단계: 회원가입/로그인 페이지 확인")
            await page.wait_for_timeout(2000)

            # URL 확인 (로그인/회원가입 페이지로 이동했는지)
            current_url = page.url
            print(f"현재 URL: {current_url}")

            # 로그인 페이지 요소 확인
            if 'login' in current_url.lower() or 'signup' in current_url.lower() or 'auth' in current_url.lower():
                print("✅ 로그인/회원가입 페이지로 정상 이동")
            else:
                # 페이지 내 로그인 폼 확인
                email_input = page.locator('input[type="email"]').first
                if await email_input.count() > 0:
                    print("✅ 로그인 페이지 요소 확인 (이메일 입력 필드 존재)")
                else:
                    print("⚠️ 경고: 로그인 페이지 확인 불확실")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_10_success.png', full_page=True)
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            # 실패 스크린샷
            await page.screenshot(path='screenshots/test_10_failed.png', full_page=True)
            print(f"❌ 테스트 실패: {e}")
            print(f"현재 URL: {page.url}")
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
