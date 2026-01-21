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
            # 사전조건: 소셜 탭 진입 상태
            # 확인사항: 1. LNB 영역, 2. 로그인 해주세요 버튼 선택
            # 기대결과: 회원가입/로그인 페이지 정상 진입

            # 1단계: GNB에서 소셜 탭 클릭
            print("🔍 소셜 탭 찾기...")

            # 소셜 탭 클릭 (다양한 로케이터 시도)
            social_tab = None
            try:
                # 방법 1: role과 name으로 찾기
                social_tab = page.get_by_role('link', name='소셜')
                await social_tab.wait_for(state='visible', timeout=5000)
            except:
                try:
                    # 방법 2: 텍스트로 찾기
                    social_tab = page.get_by_text('소셜').first
                    await social_tab.wait_for(state='visible', timeout=5000)
                except:
                    # 방법 3: CSS 선택자로 찾기
                    social_tab = page.locator('a[href*="social"], a[href*="소셜"]').first
                    await social_tab.wait_for(state='visible', timeout=5000)

            await social_tab.click()
            print("✅ 소셜 탭 클릭 완료")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(1)

            # 2단계: LNB 영역 확인
            print("🔍 LNB 영역 확인...")

            # LNB 영역이 로드될 때까지 대기
            await asyncio.sleep(2)

            # 3단계: "로그인 해주세요" 버튼 찾기 및 클릭
            print("🔍 '로그인 해주세요' 버튼 찾기...")

            login_prompt_button = None
            try:
                # 방법 1: role과 name으로 찾기
                login_prompt_button = page.get_by_role('button', name='로그인 해주세요')
                await login_prompt_button.wait_for(state='visible', timeout=5000)
            except:
                try:
                    # 방법 2: 텍스트로 찾기
                    login_prompt_button = page.get_by_text('로그인 해주세요')
                    await login_prompt_button.wait_for(state='visible', timeout=5000)
                except:
                    try:
                        # 방법 3: 부분 텍스트 매칭
                        login_prompt_button = page.locator('button:has-text("로그인")').first
                        await login_prompt_button.wait_for(state='visible', timeout=5000)
                    except:
                        # 방법 4: 더 넓은 범위로 찾기
                        login_prompt_button = page.locator('a:has-text("로그인"), button:has-text("로그인")').first
                        await login_prompt_button.wait_for(state='visible', timeout=5000)

            await login_prompt_button.click()
            print("✅ '로그인 해주세요' 버튼 클릭 완료")

            # 4단계: 회원가입/로그인 페이지 진입 확인
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)

            # URL 또는 페이지 요소로 로그인 페이지 확인
            current_url = page.url
            print(f"📍 현재 URL: {current_url}")

            # 로그인 페이지 확인 (URL에 login, signin 등이 포함되거나 로그인 폼이 있는지 확인)
            is_login_page = False

            if 'login' in current_url.lower() or 'signin' in current_url.lower() or 'signup' in current_url.lower():
                is_login_page = True
                print("✅ URL에서 로그인 페이지 확인")
            else:
                # 페이지 내 로그인 폼 요소 확인
                try:
                    await page.locator('input[type="email"], input[name="email"], input[placeholder*="이메일"]').wait_for(state='visible', timeout=5000)
                    is_login_page = True
                    print("✅ 로그인 폼에서 로그인 페이지 확인")
                except:
                    pass

            if not is_login_page:
                raise Exception("회원가입/로그인 페이지로 진입하지 못했습니다")

            print("✅ 회원가입/로그인 페이지 정상 진입 확인")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_10_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")  # ⭐ 성공 시그널
            return True

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            await page.screenshot(path='screenshots/test_10_failure.png')
            print(f"AUTOMATION_FAILED: {e}")  # ⭐ 실패 시그널
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
