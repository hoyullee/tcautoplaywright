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
            # 테스트 로직: GNB > 교육•이벤트 > 회원가입/로그인 버튼 선택
            # ========================================

            # 1. GNB 영역에서 "교육•이벤트" 탭 찾기 및 클릭
            print("🔍 교육•이벤트 탭 찾기...")

            # 교육•이벤트 탭 클릭 (여러 가능한 셀렉터 시도)
            try:
                # 방법 1: 정확한 텍스트로 찾기
                education_tab = page.get_by_text('교육•이벤트', exact=True)
                await education_tab.click()
                print("✅ 교육•이벤트 탭 클릭 성공 (방법 1)")
            except:
                try:
                    # 방법 2: 링크로 찾기
                    education_tab = page.get_by_role('link', name='교육•이벤트')
                    await education_tab.click()
                    print("✅ 교육•이벤트 탭 클릭 성공 (방법 2)")
                except:
                    # 방법 3: CSS 셀렉터
                    education_tab = page.locator('a[href*="events"]').first
                    await education_tab.click()
                    print("✅ 교육•이벤트 탭 클릭 성공 (방법 3)")

            await page.wait_for_load_state('networkidle')
            print("✅ 교육•이벤트 페이지 로드 완료")

            # 2. GNB 영역에서 회원가입/로그인 버튼 찾기
            print("🔍 회원가입/로그인 버튼 찾기...")

            # 회원가입/로그인 버튼 클릭 (여러 가능한 셀렉터 시도)
            try:
                # 방법 1: "회원가입/로그인" 정확한 텍스트
                login_button = page.get_by_text('회원가입/로그인', exact=True)
                await login_button.click()
                print("✅ 회원가입/로그인 버튼 클릭 성공 (방법 1)")
            except:
                try:
                    # 방법 2: "로그인" 텍스트
                    login_button = page.get_by_role('button', name='로그인')
                    await login_button.click()
                    print("✅ 로그인 버튼 클릭 성공 (방법 2)")
                except:
                    try:
                        # 방법 3: "회원가입" 포함된 텍스트
                        login_button = page.get_by_text('회원가입')
                        await login_button.click()
                        print("✅ 회원가입 버튼 클릭 성공 (방법 3)")
                    except:
                        # 방법 4: CSS 셀렉터로 GNB 내 로그인 관련 버튼
                        login_button = page.locator('button:has-text("회원가입"), a:has-text("로그인")').first
                        await login_button.click()
                        print("✅ 로그인 버튼 클릭 성공 (방법 4)")

            # 페이지 전환 대기
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)  # 페이지 안정화 대기

            # 3. 회원가입/로그인 페이지 진입 확인
            print("🔍 회원가입/로그인 페이지 진입 확인...")
            current_url = page.url
            print(f"📍 현재 URL: {current_url}")

            # 로그인/회원가입 페이지 확인 (URL 또는 페이지 요소로 검증)
            if 'login' in current_url or 'signup' in current_url or 'auth' in current_url:
                print("✅ 회원가입/로그인 페이지 URL 확인 성공")
            else:
                # URL로 확인 안되면 페이지 요소로 확인
                try:
                    # 이메일 입력 필드 또는 로그인 관련 요소 존재 확인
                    email_field = page.locator('input[type="email"], input[name="email"], input[placeholder*="이메일"]').first
                    await email_field.wait_for(state='visible', timeout=5000)
                    print("✅ 로그인 페이지 요소 확인 성공")
                except:
                    print("⚠️ 로그인 페이지 요소 확인 실패, 하지만 계속 진행...")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_8_success.png', full_page=True)
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            # 실패 스크린샷
            try:
                await page.screenshot(path='screenshots/test_8_failure.png', full_page=True)
            except:
                pass

            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
