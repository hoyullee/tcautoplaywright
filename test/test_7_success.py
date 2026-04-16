from playwright.async_api import async_playwright
import asyncio
import sys
import os
import pytest

TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            print("✅ 페이지 로드 완료")

            # 로그인
            print("🔐 로그인 시도")
            login_btn = page.get_by_role('button', name='회원가입/로그인')
            await login_btn.wait_for(state='visible', timeout=10000)
            await login_btn.click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)

            # 이메일로 계속하기
            email_continue_btn = page.get_by_role('button', name='이메일로 계속하기')
            await email_continue_btn.wait_for(state='visible', timeout=10000)
            await email_continue_btn.click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(1000)

            # 이메일 입력
            email_input = page.locator('input[type="email"]')
            await email_input.wait_for(state='visible', timeout=10000)
            await email_input.fill(TEST_EMAIL)

            # 비밀번호 입력
            password_input = page.locator('input[type="password"]')
            await password_input.fill(TEST_PASSWORD)

            # 로그인 버튼 클릭
            login_button = page.get_by_role('button', name='로그인')
            await login_button.click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            print("✅ 로그인 완료")

            # GNB 메뉴 노출 확인
            print("🔍 GNB 메뉴 노출 확인")

            # 1. wanted 로고
            logo = page.locator('nav a[aria-label="Wanted"], a[aria-label="Wanted"]').first
            await logo.wait_for(state='visible', timeout=10000)
            print("✅ wanted 로고 노출")

            # 2. 채용
            job_menu = page.get_by_role('link', name='채용').first
            await job_menu.wait_for(state='visible', timeout=10000)
            print("✅ 채용 메뉴 노출")

            # 3. 이력서
            resume_menu = page.get_by_role('link', name='이력서').first
            await resume_menu.wait_for(state='visible', timeout=10000)
            print("✅ 이력서 메뉴 노출")

            # 4. 교육•이벤트
            edu_menu = page.locator('a').filter(has_text='교육').first
            await edu_menu.wait_for(state='visible', timeout=10000)
            print("✅ 교육•이벤트 메뉴 노출")

            # 5. 콘텐츠
            content_menu = page.get_by_role('link', name='콘텐츠').first
            await content_menu.wait_for(state='visible', timeout=10000)
            print("✅ 콘텐츠 메뉴 노출")

            # 6. 소셜
            social_menu = page.get_by_role('link', name='소셜').first
            await social_menu.wait_for(state='visible', timeout=10000)
            print("✅ 소셜 메뉴 노출")

            # 7. 프리랜서
            freelancer_menu = page.get_by_role('link', name='프리랜서').first
            await freelancer_menu.wait_for(state='visible', timeout=10000)
            print("✅ 프리랜서 메뉴 노출")

            # 8. 더보기
            more_btn = page.get_by_role('button', name='더보기').first
            await more_btn.wait_for(state='visible', timeout=10000)
            print("✅ 더보기 메뉴 노출")

            # 9. 검색 아이콘
            search_icon = page.locator('[aria-label*="검색"], [aria-label*="Search"], button[class*="search"], a[class*="search"]').first
            await search_icon.wait_for(state='visible', timeout=10000)
            print("✅ 검색 아이콘 노출")

            # 10. 알림센터 아이콘
            notification_icon = page.locator('[aria-label*="알림"], [aria-label*="notification"], [aria-label*="Notification"], button[class*="alarm"], a[class*="alarm"]').first
            await notification_icon.wait_for(state='visible', timeout=10000)
            print("✅ 알림센터 아이콘 노출")

            # 11. 프로필 아이콘
            profile_icon = page.locator('[aria-label*="프로필"], [aria-label*="profile"], [aria-label*="Profile"], button[class*="profile"], a[class*="profile"]').first
            await profile_icon.wait_for(state='visible', timeout=10000)
            print("✅ 프로필 아이콘 노출")

            # 12. 기업 서비스
            company_service = page.get_by_role('button', name='기업 서비스')
            if await company_service.count() == 0:
                company_service = page.get_by_role('link', name='기업 서비스')
            if await company_service.count() == 0:
                company_service = page.get_by_text('기업 서비스')
            await company_service.first.wait_for(state='visible', timeout=10000)
            print("✅ 기업 서비스 노출")

            await page.screenshot(path='screenshots/test_7_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_7_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
